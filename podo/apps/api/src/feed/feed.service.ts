import { Injectable } from '@nestjs/common'
// 처리완료 정리 규칙의 단일 출처(applications 도메인 소유) — feed/meta가 동일 action을 제외(드리프트 방지).
import { CLEARED_ACTIONS } from '../applications/applications.service'
// NestJS DI: value import 필수(import type은 emitDecoratorMetadata에서 erase → DI 실패).
import { PrismaService } from '../prisma/prisma.service'

export interface FeedItem {
  posting: unknown
  fit_level: number | null
  rank_position: number
  status: string
  // ranking_runs.result — opaque evidence. 파싱·분기 금지(§3-2 규칙3 / ARCH §7-1).
  evidence: unknown
}

export interface FeedPage {
  items: FeedItem[]
  nextCursor: number | null
}

// T-065 coarse 섹션 항목 — 후보 밖(deep 분석 전) 공고. **fit_level 없음**(ADR-108 D3·Guardrail 1).
export interface CoarseItem {
  posting: unknown
  similarity_rank: number
}

export interface CoarsePage {
  items: CoarseItem[]
  nextCursor: number | null
}

// 이력서 도메인 자동 분류 결과(T-066 worker 산출 — read-only 서빙, T-067 직군 탭 소비).
export interface ResumeDomainsDto {
  primary_domains: string[]
  secondary_domains: string[]
  confidence: string
  classifier_version: string
}

// 피드 셸 메타 — 8-상태 분기(F-018)용. items와 분리(getFeed는 커서 페이지네이션, meta는 1회).
export interface FeedMeta {
  has_resume: boolean
  scoring_status: 'queued' | 'running' | 'done' | 'failed' | null
  diff_summary: { new_count: number; expiring_count: number }
  total_pending_count: number // 현재 run의 held(보류) 공고 수
  visible_count: number // 처리완료 정리 후 피드에 보이는 공고 수(ready/empty/all-processed 판별)
  resume_domains: ResumeDomainsDto | null // T-066: 직군 분류(T-067 탭 소비)
}

@Injectable()
export class FeedService {
  constructor(private readonly prisma: PrismaService) {}

  // 피드 진입 8-상태 분기 메타(F-018, T-046). 사용자 활성 이력서·채점 상태·신규/마감 diff·보류 수.
  async getFeedMeta(userId?: string): Promise<FeedMeta> {
    const empty: FeedMeta = {
      has_resume: false,
      scoring_status: null,
      diff_summary: { new_count: 0, expiring_count: 0 },
      total_pending_count: 0,
      visible_count: 0,
      resume_domains: null,
    }
    if (!userId) {
      return empty
    }

    const resume = await this.prisma.resume.findFirst({
      where: { user_id: userId },
      select: { id: true },
    })
    if (!resume) {
      return empty
    }

    // T-066: 이력서 도메인 분류 결과(worker 산출) read-only 서빙 — T-067 직군 탭 소비.
    const domainsRow = await this.prisma.resumeDomains.findUnique({
      where: { resume_id: resume.id },
      select: {
        primary_domains: true,
        secondary_domains: true,
        confidence: true,
        classifier_version: true,
      },
    })
    const resume_domains: ResumeDomainsDto | null = domainsRow ?? null

    // 최신 scoring_job 상태 + ranking_run join 기반 done 판정(T-045 §8).
    const job = await this.prisma.scoringJob.findFirst({
      where: { resume: { user_id: userId } },
      orderBy: { created_at: 'desc' },
      select: { status: true },
    })
    const run = await this.prisma.rankingRun.findFirst({
      where: { resume: { user_id: userId } },
      orderBy: [{ created_at: 'desc' }, { id: 'desc' }],
      select: { id: true },
    })
    // scoring_jobs.status는 DB scalar(string) — 계약 union으로 좁힘(값은 queued/running/done/failed).
    let scoring_status: FeedMeta['scoring_status'] =
      (job?.status as FeedMeta['scoring_status']) ?? null
    if (run) {
      scoring_status = 'done'
    }

    if (!run) {
      return { ...empty, has_resume: true, scoring_status, resume_domains }
    }

    // 처리완료(applied/skipped) 제외 — getFeed와 동일 규칙.
    const processed = await this.prisma.applicationEvent.findMany({
      where: { user_id: userId, action: { in: CLEARED_ACTIONS } },
      select: { job_posting_id: true },
    })
    const excluded = new Set(processed.map((p) => p.job_posting_id))

    const recs = await this.prisma.recommendation.findMany({
      where: { run_id: run.id },
      select: { status: true, job_posting: { select: { diff_status: true, id: true } } },
    })

    let new_count = 0
    let expiring_count = 0
    let total_pending_count = 0
    let visible_count = 0
    for (const r of recs) {
      if (excluded.has(r.job_posting.id)) {
        continue
      }
      visible_count++
      if (r.status === 'held') {
        total_pending_count++
      }
      if (r.job_posting.diff_status === 'new') {
        new_count++
      } else if (r.job_posting.diff_status === 'expiring') {
        expiring_count++
      }
    }

    return {
      has_resume: true,
      scoring_status,
      diff_summary: { new_count, expiring_count },
      total_pending_count,
      visible_count,
      resume_domains,
    }
  }

  // worker 산출 recommendations를 current run 한정 + rank_position 커서로 서빙(read-only).
  // userId 주어지면 그 사용자 이력서의 run으로 범위 격리(멀티유저, T-042). 미지정 시 전역(하위호환).
  async getFeed(cursor: number, userId?: string, take = 20): Promise<FeedPage> {
    // (a) current run = (해당 사용자) 최신 ranking_runs (run 간 stale 혼입 차단 — cross-LLM P1)
    const currentRun = await this.prisma.rankingRun.findFirst({
      where: userId ? { resume: { user_id: userId } } : undefined,
      // 동일 ms 두 run insert 시 tie 비결정 방지 — id desc 보조 정렬(QA-M2-006).
      orderBy: [{ created_at: 'desc' }, { id: 'desc' }],
      select: { id: true },
    })
    if (!currentRun) {
      return { items: [], nextCursor: null }
    }

    // (a-2) 처리완료 정리(F-019): 사용자가 applied/skipped 처리한 공고는 기본 피드에서 제외.
    // 즐겨찾기·되돌리기(favorite/unfavorite/unskip)는 제외 대상 아님(최신 action 기준 upsert 1행).
    let excludedJobIds: number[] = []
    if (userId) {
      const processed = await this.prisma.applicationEvent.findMany({
        where: { user_id: userId, action: { in: CLEARED_ACTIONS } },
        select: { job_posting_id: true },
      })
      excludedJobIds = processed.map((p) => p.job_posting_id)
    }

    // (b) current run 한정 + rank_position > cursor 오름차순. held(fit_level null) 포함.
    const recs = await this.prisma.recommendation.findMany({
      where: {
        run_id: currentRun.id,
        rank_position: { gt: cursor },
        ...(excludedJobIds.length ? { job_posting_id: { notIn: excludedJobIds } } : {}),
      },
      orderBy: { rank_position: 'asc' },
      take,
      include: { job_posting: true, run: { select: { result: true } } },
    })

    const seen = new Set<number>()
    const items: FeedItem[] = []
    for (const r of recs) {
      // 방어적 dedup — 불변식은 recommendations @@unique([run_id, job_posting_id])가 DB 보장(QA-M2-002).
      if (seen.has(r.job_posting_id)) continue
      seen.add(r.job_posting_id)
      items.push({
        posting: r.job_posting,
        fit_level: r.fit_level,
        rank_position: r.rank_position,
        status: r.status,
        evidence: r.run.result, // opaque pass-through (파싱 X)
      })
    }

    const nextCursor = recs.length === take ? recs[recs.length - 1].rank_position : null
    return { items, nextCursor }
  }

  // T-065 coarse 섹션 — 후보 밖 공고를 유사도 rank 순으로 서빙(read-only, fit_level 없음).
  // resume_id 범위(현재 run — 이력서 교체 시 이전 coarse 미혼입, M5-repair-38). deep와 별도 cursor.
  // vector 쿼리 0줄 — worker가 materialize한 coarse_candidates를 읽기만 한다(ADR-108 D3).
  async getCoarseFeed(cursor: number, userId?: string, take = 20): Promise<CoarsePage> {
    const resume = userId
      ? await this.prisma.resume.findFirst({
          where: { user_id: userId },
          orderBy: [{ created_at: 'desc' }, { id: 'desc' }],
          select: { id: true },
        })
      : null
    if (!resume) {
      return { items: [], nextCursor: null }
    }

    const offset = cursor < 0 ? 0 : cursor
    const rows = await this.prisma.coarseCandidate.findMany({
      where: { resume_id: resume.id },
      // 결정적 순서: 유사도 desc → job_posting_id asc(tie-break).
      orderBy: [{ similarity_rank: 'desc' }, { job_posting_id: 'asc' }],
      skip: offset,
      take,
      include: { job_posting: true },
    })

    const items: CoarseItem[] = rows.map((r) => ({
      posting: r.job_posting,
      similarity_rank: r.similarity_rank,
      // fit_level 의도적 부재 — coarse는 deep 분석 전(거짓 점수 금지, Guardrail 1).
    }))
    const nextCursor = rows.length === take ? offset + take : null
    return { items, nextCursor }
  }
}
