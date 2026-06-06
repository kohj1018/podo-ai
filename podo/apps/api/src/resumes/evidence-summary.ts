// parse_resume.extract_skills_evidence의 비-LLM 헤딩 파싱을 경량 이식(T-034 §3 step4d).
// 업로드 즉시 결정적으로 스킬 불릿 수 / 경력 불릿 수를 센다(LLM 없음 — preview용 요약).
// 전체 evidence(LLM 기반)는 분석-후 feed에서 계산.

export interface EvidenceSummary {
  skills: number
  experiences: number
}

// 헤딩 인식(per-line, IGNORECASE). parse_resume._SKILLS_HEADING_RE와 동치.
const SKILLS_HEADING =
  /^#{1,6}\s*(Skills?|기술스택|기술\s*스택|기술\s*및\s*도구|기술|Tech(?:nical)?\s*(?:Skills?|Stack))/i
const EXPERIENCE_HEADING = /^#{1,6}\s*(경력|경험|Work\s*Experience|Experience|프로젝트|Projects?)/i
const SECTION_HEADING = /^#{1,6}\s+/ // parse_resume._SECTION_HEADING_RE 동치
const BULLET = /^\s*[-*•·]\s+\S/ // parse_resume._BULLET_RE 동치

// 대상 헤딩 섹션(다음 섹션 헤딩 전까지) 안의 불릿 라인 수를 센다.
function countBulletsUnder(text: string, heading: RegExp): number {
  let count = 0
  let active = false
  for (const line of text.split(/\r?\n/)) {
    if (SECTION_HEADING.test(line)) {
      active = heading.test(line)
      continue
    }
    if (active && BULLET.test(line)) count += 1
  }
  return count
}

export function summarizeEvidence(text: string): EvidenceSummary {
  return {
    skills: countBulletsUnder(text, SKILLS_HEADING),
    experiences: countBulletsUnder(text, EXPERIENCE_HEADING),
  }
}
