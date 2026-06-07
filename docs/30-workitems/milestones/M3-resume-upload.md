# M3-resume-upload

## 0. Status
draft

## 1. 목적
M2가 "검증된 알고리즘 → 도는 서비스(로컬 E2E)"를 만들면서 **합성 seed 이력서**(config/seed, SPEC §9-4 USER_DOMAINS 방식)로 대체해 둔 이력서 입력을, 단일 사용자가 **자신의 실제 이력서를 업로드**해 스코어링받는 경로로 교체한다. 즉 "수집 → worker 스코어링 → DB → API → feed"의 *입력 소스*를 합성에서 **실 이력서**로 바꾸고, 그 과정에서 **실 PII가 어디에도 raw로 남지 않도록**(업로드 직후 메모리에서 직접 식별자 제거 → 마스킹본만 DB·LLM·cache·result·log에 흐름) 책임 있게 다룬다 — M3의 핵심 리스크는 ranking 정확도가 아니라 *개인정보가 어디에 남는가*다. **새 스코어링 로직은 0** — 알고리즘 본체([SCORING_PIPELINE_SPEC](../../20-system/SCORING_PIPELINE_SPEC.md))는 SSOT 불변이고, 기존 `parse_resume` 파싱 경로를 *실 업로드 텍스트*로 먹이는 것이 핵심이다. 결정론(GS-1)·grounding(GS-2) 게이트는 실 이력서 입력 위에서도 보존된다. (Charter §4 G4 / §8 흐름2)

> **배포·auth·멀티유저는 M3 비범위 → M4.** M3 done-line은 여전히 *로컬 E2E*(M2와 동일한 done 경계). 실 PII raw는 영속하지 않으며(마스킹본만 로컬 DB에 저장), 공개 노출(Vercel)·인증·멀티유저는 다음 마일스톤. (사용자 판단 2026-06-06 — "제품 확장 = UI 이력서 업로드 + 실 PII, 배포는 M4".)

> **reconcile 부채 흡수 (사용자 판단 2026-06-06):** IMPROVEMENT_GUIDE가 "M3 전 회수 권장"으로 박은 DISCOVERY/Charter doc reconcile(용어 통일·Insight promote·status 정리)을 **M3 첫 feature(F-012)로 흡수**한다. 별도 선행 라운드 대신 M3 안에서 처리.

## 2. 범위
M2 §4가 *비범위로 선고지*한 **"UI 이력서 업로드 + 실 PII 영속/마스킹"**(M2 §4 2번)을 닫고, 그 전제인 M1→M2 누적 doc reconcile 부채를 회수한다. 알고리즘 본체·스코어링 캐시 키·feed projection 구조는 불변 — 새 스코어링 로직 0.
- **doc reconcile (선행, F-012)** — 용어 divergence("적합도 5단계" ↔ "합격가능성 밴드", Charter 6×·DISCOVERY 12×) 통일 + DISCOVERY §15 Insight I-1/2/3 `open→planned/done` promote + DISCOVERY/Charter/DESIGN `status` 정리 + globals.css token SSOT 동기 + ADR-104 backref 6건. (`/discover-product --update` → `/bootstrap-project --apply` 경유 — DISCOVERY=SSOT, ADR-035.) **정합만 — 제품 전략 재작성·새 기능 범위 재정의는 비범위**(M3가 문서작업에 잡아먹히지 않도록).
- **이력서 업로드 API** — NestJS 업로드 엔드포인트(입력: `.txt`/`.md` 파일 + 텍스트 붙여넣기(paste)만 — PDF/docx는 비범위 §4) + `resumes` 영속(스키마 확장). [ARCH §7-1]
- **이력서 파싱 + PII 마스킹** — 업로드 직후 메모리에서 **직접 식별자(이름·이메일·전화·생년·주소·민감 URL)** 제거 → **마스킹본만** 기존 `parse_resume` 경로로 파싱·저장·LLM 전송. **raw PII가 DB(`resumes`, `content`=마스킹본)·`ranking_runs.result`·`recommendations`·로그·LLM cache(`.cache/llm`·커밋 웜캐시) 어디에도 흐르지 않는다**(M3 안전 불변식). 마스킹은 **regex/rule-based**이며 **raw를 외부(스코어링) LLM에 보내는 PII 탐지는 금지**(이름은 regex 한계상 best-effort → preview 사용자 확인으로 보완). 학교·회사·프로젝트·스택·경력기간·성과 수치는 *evidence로 유지*(과마스킹은 grounding/GS-2 약화). *새 결정 영역 → ADR-105(PII 정책) 신설.*
- **이력서 업로드 UI** — Next.js 업로드 화면 + 마스킹본 preview + 분석 시작 + 기존 스코어링·feed 흐름 연결(상세 §3 F-015). 합성 seed는 dev fixture로 격하. [ARCH §7-4]
- **스키마 확장** — `resumes` 테이블에 실 이력서 메타(마스킹 적용 여부·업로드 출처·포맷 등) 필드 추가. **raw 원문 컬럼은 두지 않는다**(`content`=마스킹본). Prisma DDL = 폴리글랏 계약 SSOT(ARCH §3-2), schema-contract test 동반 갱신.

> **불변 유지:** `RankingRun` 복합 unique 캐시 키(`resume_id` 포함)·`Recommendation` projection·`ranking_runs.result` opaque JSONB는 M2 구조 그대로. 실 이력서는 `resume_id`로 들어가므로 캐시 키 설계가 그대로 GS-1-through-DB를 보존한다.

## 3. 포함되는 기능 (F-012 ~ F-015, 잠정)
> 아래 F-NNN은 `/plan-workitem M3`가 정식 분해한다. 번호·경계는 plan 단계에서 조정 가능. `=M2 §4`는 닫는 비범위 경계.
- **F-012 (doc-reconcile)** — *technical-enabler / doc*. M3 **첫 작업**. 용어 통일·Insight promote·status 정리·token SSOT·ADR-104 backref. scaffold 의존 0 → 즉시 착수. (IMPROVEMENT_GUIDE M2 P1 #5 / cross-stabilize 회귀 신호 회수.)
- **F-013 (resume-upload-api)** — NestJS 업로드 엔드포인트(`.txt`/`.md`/paste) + `resumes` 영속(확장 스키마) + schema-contract test 갱신. [M2 §4-2] [ARCH §7-1]
- **F-014 (resume-parse-pii)** — 직접 식별자 마스킹(메모리) → 마스킹본만 `parse_resume`·저장·LLM. raw PII 미영속·미전송 불변식(DB·result·cache·log). 마스킹=regex/rule-based(raw→외부 LLM 탐지 금지)·이름 best-effort. ADR-105 신설. = Charter §4 G4(이력서↔JD 매핑 입력 신뢰). [M2 §4-2]
- **F-015 (resume-upload-ui)** — Next.js 업로드 화면 + **마스킹본 preview + 추출 evidence 개수·핵심 skills/경력 요약 + "이 이력서로 분석 시작" 버튼** + 스코어링/feed 연결. preview는 *안전 통제*도 겸함 — 누락 PII를 사용자가 직접 가리고 분석 시작. **행단위 evidence(스킬·경력) 편집 UI는 비범위.** 합성 seed → dev fixture 격하. [ARCH §7-4]

## 4. 제외되는 기능
- **공개 배포(Vercel) + auth + 멀티유저** — M4. Charter §5 "멀티유저" 비목표 유지(M4에서 다루려면 ADR로 범위 변경 선결). M3 done-line은 *로컬 E2E*.
- **자소서·이력서 자동작성/첨삭** — Charter §5 비목표. 업로드·파싱·스코어링까지만.
- **이력서 버전 관리/히스토리 비교·다중 이력서 A/B** — YAGNI. 단일 활성 이력서로 시작.
- **이력서 evidence 행단위 편집 UI** — preview·확인까지만(F-015). 편집은 원문 재업로드/재paste로 대체. YAGNI.
- **PDF/docx 업로드·텍스트 추출 일체** — `.txt`/`.md`/paste만으로 M3를 닫는다. 바이너리 포맷 추출(인코딩·표·다단·헤더/푸터 edge case)은 M4 이후. M3 목표는 "업로드 경로가 scoring loop에 연결되는가"이지 포맷 호환이 아니다.
- **raw 원문 PII 영속·암호화 저장** — M3는 마스킹본만 저장. raw 보관(암호화 포함)은 M4(배포·auth와 함께 재검토).
- **새 스코어링 로직·캐시 키 재설계·직군 분기 모델** — SPEC SSOT 불변, 단일 모델 유지(A-7 의존).
- **7개+ 다채널 풀커버리지** — 토스·당근 유지(Charter §5).

## 5. 완료 기준 (graduation checklist)
> sprint contract: 외부 검증 가능한 "done" 기준 (ADR-014).
- [ ] 모든 task status: done
- [ ] 통합 validate Pass (ruff·mypy strict·pytest + Biome/Vitest + schema-contract green)
- [ ] **E2E Pass** — fresh clone → `docker compose up` + `prisma migrate dev` + **이력서(`.txt`/paste) 업로드** → 마스킹 → 파싱 → crawl→score→feed 완주. `localhost:3000`에서 *업로드 이력서 기준* 적합도 5단계 배지 + 근거(JD 인용) + 커버리지 패널 렌더. **무키 결정성 경로는 *합성/마스킹된 fixture 이력서* + 재생성 웜캐시로 보존** — 커밋 웜캐시는 *실 PII 이력서로 생성 금지*(PII Safety Pass와 정합). 실 이력서 live score는 `OPENAI_API_KEY` 보유 시.
- [ ] AC 매핑 100% (validation report 기준)
- [ ] P0 severity finding 0건 (QA_FINDINGS의 M3 헤더 기준)
- [ ] **doc reconcile 완료** — DISCOVERY/Charter/DESIGN 용어·status·Insight 정합(F-012). DISCOVERY=SSOT 갱신 + Charter snapshot sync 확인.
- [ ] **PII Safety Pass (필수)** — raw PII(이름·이메일·전화·생년·주소 등 직접 식별자)가 **`resumes`·`ranking_runs.result`·`recommendations`·애플리케이션 로그·LLM cache(`.cache/llm`·커밋 웜캐시) 어디에도 남지 않음**을 검증 — **fixture 기반 literal scan**(알려진 PII 값: 이름·email·phone·생년·주소·개인 URL을 위 표면에서 스캔 → 0건). 실 이력서 업로드가 M3 핵심이므로 안전성은 *선택이 아닌 졸업 게이트*. ADR-105 정책대로.
- [ ] (선택) **GS-1-through-DB (실 이력서):** 동일 (실 이력서, JD)를 DB 경로로 2회 채점 → 저장된 band/score/evidence 변동 0(캐시 hit).

## 6. 관련 문서
- Charter: [PROJECT_CHARTER](../../10-charter/PROJECT_CHARTER.md) (§4 G4 이력서↔JD 매핑, §5 비목표, §8 흐름2)
- Discovery (SSOT): [DISCOVERY](../../10-charter/DISCOVERY.md) (§7 F7 스코어링 입력 투명성, §15 Insight I-1/2/3 promote 대상)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md) (§3-2 폴리글랏 매핑·schema-contract, §7-1 API, §7-4 프론트)
- Algorithm SSOT: [SCORING_PIPELINE_SPEC](../../20-system/SCORING_PIPELINE_SPEC.md) (§9-4 이력서 주입 — 합성→실, parse_resume 경로 불변)
- 선행 마일스톤: [M2-service-wiring](M2-service-wiring.md) (§4 비범위 = M3 범위 정의)
- 개선 부채: [IMPROVEMENT_GUIDE](../../40-validation/IMPROVEMENT_GUIDE.md) (M2 P1 #5 doc reconcile = F-012 / cross-stabilize 회귀 신호)
- ADR: [ADR-035](../../90-decisions/boilerplate/ADR-035-continuous-discovery.md) (DISCOVERY=SSOT reconcile 경로) · ADR-105(가칭, PII 정책 — F-014 plan에서 신설 후보)

## 7. 열린 질문
> 입력 포맷(`.txt`/`.md`/paste)·raw 미영속·마스킹 대상(직접 식별자)·안전 게이트(§5)는 초안에서 safety/scope 판단으로 선결. 아래는 ADR-105/plan에서 확정. **굵게 = 현 권장 기본값.**
- **마스킹 방식 (확정)** — **regex/rule-based만**. **raw를 외부(스코어링) LLM에 보내는 PII 탐지는 금지**(raw가 LLM/cache에 흐르면 안전 불변식 위반) — 로컬·인메모리 NER은 M3 비범위(필요 시 후속). 이름은 regex 한계상 best-effort → preview에서 사용자 확인/수정으로 보완. 놓친 PII 허용선 = PII Safety Pass(§5) fixture scan **0건**. (정규식 세트·필드 형식은 ADR-105. Charter §5/§7에 PII 정책 부재 → 신규.)
- **간접 재식별 방어 경계** — 직접 식별자를 지워도 *학교+회사+재직기간* 조합으로 재식별될 수 있음(직접 식별자만 마스킹하는 정책의 잔여 리스크). **M3는 직접 식별자 제거까지만 책임지고, 간접 재식별/익명화는 M4(공개 배포 시) 재검토**로 명시할지 — 로컬 단일 사용자(본인 이력서) 맥락에선 수용 가능 판단.
- **합성 seed 처리** — **dev fixture로 유지(완전 제거 X)** — M2 무키 E2E(`scripts/e2e.mjs`·커밋 웜캐시)가 seed에 의존하므로 보존. F-013/F-015에서 의존성 끊기지 않는지 확인만.
- **용어 reconcile 최종 표기** — **"적합도 5단계"로 통일**(DISCOVERY "합격가능성 밴드"는 폐기/과거표현으로). F-012에서 사용자 최종 확정 — UI·문서 일괄 영향.

## 8. 회고 (stabilize 자동 채움)
> `/stabilize-milestone M3` (2026-06-07)가 채움. (status(## 0) 전이는 본 skill 책임 아님 — ADR-014. **졸업 가능 = NO(초판)**, 단일 차단 §5 #3.)
> **[Fix round 2026-06-07, 커밋 `f1f17df`]** 단일 차단 §5 #3 **closed** — `scripts/e2e.mjs`를 업로드 경로(업로드→마스킹→`resume_id` 채점→feed)로 재배선 + `e2e_pii_scan.py`(실 masker end-to-end PII scan) + 업로드 fixture 웜캐시 재생성. 무키 `pnpm e2e` exit 0 실측(scored 6/held 0, PII 0건).
> **[정식 재grade 2026-06-07]** `/stabilize-milestone M3` 재실행 — **졸업 가능 = YES**. graduation §5 필수 7항 충족 *본 세션 실측*: ① 10/10 task done · ② validate exit 0(TS 32 passed[api 17/web 15, 4 jsdom-skip] · ruff/mypy strict clean · Python 134 passed/17 DB-skip) · ③ `pnpm e2e` exit 0(업로드 `resume_id=14` → NestJS 마스킹 placeholders=5 → 웜캐시 채점 `ranking_run id=19` → 실 masker PII scan `resumes.content`+`ranking_runs.result` 0건/5 literal → feed scored 6/held 0/toss+daangn) · ④ AC 21/21 · ⑤ QA_FINDINGS 코드결함 P0 0 · ⑥ doc reconcile(제품표면 용어 grep 0·ADR-105 accepted·Insight I-1 done/I-2·I-3 planned) · ⑦ PII Safety Pass(실 masker end-to-end). **QA-M3-006(오라클 갭) closed**(업로드 E2E + `e2e_pii_scan.py`로 실 NestJS masker→DB surface-1 실증). §5 #8(선택 GS-1-through-DB)는 웜캐시 hit 결정성 경로로 보존(Fix round byte-stability 패턴). **status(## 0) 전이는 본 skill 책임 아님(ADR-014) — 사용자가 `## 0. Status`→done 전환.**

**목표 달성도:** 검증된 알고리즘 본체(SPEC SSOT 불변, 새 스코어링 로직 0) 위에서 *입력 소스를 합성 seed→실 업로드 이력서로 교체*하는 경로를 구축했다 — F-013(NestJS 업로드 API + `resumes` 스키마 확장 + schema-contract), F-014(rule-based 마스킹 + ADR-105 정책 + parse_resume 연결), F-015(업로드 UI + 마스킹 preview + 분석시작→feed), F-012(M1→M2 누적 doc 부채 회수). 10/10 task done · 통합 validate exit 0 · AC 21/21·FAC 17/17(100%) · **PII Safety Pass green**(하류 6표면 literal scan 0, 웜캐시 무오염) · 용어 reconcile 핵심표면 0. **단 §5 #3 미충족으로 졸업 미달**: done-line의 UI 종단(업로드→마스킹→`resume_id` 채점→feed 적합도 배지)이 `scripts/e2e.mjs`에 미배선(phase 4가 seed 경로로만 채점) → M3 핵심("업로드 경로가 scoring loop에 연결되는가")이 자동 게이트로 미실증. 해소=업로드 E2E 배선 + 마스킹 fixture 웜캐시 재생성 후 재grade(M2-E2E-001 동형). **[재grade closed 2026-06-07]** 위 단일 차단은 Fix round(`f1f17df`)로 해소 — 본 정식 재grade에서 `pnpm e2e` exit 0 *본 세션 실측*(업로드→마스킹→`resume_id` 채점→PII scan 0→feed scored 6/held 0)으로 M3 핵심 경로가 자동 게이트로 실증됨 → **졸업 가능 YES, graduation §5 필수 7/7 충족.**

**scope creep:** 거의 없음. write_set 이탈은 전부 문서화·정당(globals.css 토큰 enabling[T-038/T-041]·worker-runner.port/module DI 배선[T-037]·evidence-summary 헬퍼 분리[T-034]). T-036 구현 중 builder의 `class-validator`/`class-transformer` 추가(미사용)는 메인 세션이 `git checkout`으로 즉시 시정(YAGNI/ADR-006). 마스킹은 순수 regex로 신규 런타임 의존성 0.

**비목표 위반:** 없음. PDF/docx 추출·auth·멀티유저·공개 배포·raw PII 영속·암호화·새 스코어링 로직·캐시 키 재설계·다채널 풀커버리지 전부 비범위 유지. **안전 불변식 준수**: `resumes`에 raw 원문 컬럼 미도입(`content`=마스킹본 전용), raw PII가 DB·result·recommendations·로그·LLM cache·웜캐시 어디에도 미잔류(T-040 실증).

**핵심 학습 (≤3):**
1. **report-only stabilize가 못 닫는 E2E 배선** — M2와 동형. 업로드 done-line의 자동 게이트화는 *코드 작업*(e2e.mjs 재배선 + 마스킹 fixture 웜캐시 재생성, 사용자 키 1회 필요)이라 stabilize skill 경계 밖 → 별도 main-session Fix round/`/repair-workitem` 후 재grade가 정규 패턴. task §4의 "stabilize 책임" 표기는 *phase*(surface+후속 round)와 *skill*(report-only)을 혼동시킴.
2. **polyglot 마스킹 게이트의 oracle 이연** — T-040은 *하류 표면*(주 누출면) 안전을 실증하나 실 TS masker→DB surface-1 링크는 known-value 오라클로 치환 → 실 masker end-to-end는 업로드 E2E가 *완성*한다(QA-M3-006). 안전 게이트와 done-line E2E가 같은 배선으로 동시에 닫힌다.
3. **F-012가 patterned doc-drift를 실제로 끊음** — M1·M2가 반복 *권고만* 하던 doc reconcile(용어 divergence·Insight promote·token SSOT·ADR-104 backref)을 milestone 첫 feature로 흡수하니 cross-stabilize 회귀 신호 4종이 해소(잔존 회귀는 deferred [Dependency] 1종). *권고는 다음 milestone의 task로 박아야 닫힌다*는 실증 — graduation checklist 확장보다 plan 회수 강제가 유효.
