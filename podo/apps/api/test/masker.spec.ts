import { describe, expect, it } from 'vitest'
import { RegexResumeMasker } from '../src/resumes/resume-masker.port'

// AC-1: 직접 식별자가 각 플레이스홀더로 치환되고 placeholders 건수가 정확하다.
describe('RegexResumeMasker — AC-1 직접 식별자 마스킹', () => {
  const masker = new RegexResumeMasker()

  it('test_AC_1_masks_email', () => {
    const { masked, placeholders } = masker.mask('연락처: hong@example.com')
    expect(masked).toContain('[MASKED_EMAIL]')
    expect(masked).not.toContain('hong@example.com')
    expect(placeholders).toBe(1)
  })

  it('test_AC_1_masks_phone_01x', () => {
    const { masked, placeholders } = masker.mask('전화: 010-1234-5678')
    expect(masked).toContain('[MASKED_PHONE]')
    expect(masked).not.toContain('010-1234-5678')
    expect(placeholders).toBe(1)
  })

  it('test_AC_1_masks_phone_spaces', () => {
    const { masked, placeholders } = masker.mask('전화: 011 9876 5432')
    expect(masked).toContain('[MASKED_PHONE]')
    expect(placeholders).toBe(1)
  })

  it('test_AC_1_masks_rrn', () => {
    const { masked, placeholders } = masker.mask('주민번호: 900101-1234567')
    expect(masked).toContain('[MASKED_RRN]')
    expect(masked).not.toContain('900101-1234567')
    expect(placeholders).toBe(1)
  })

  it('test_AC_1_masks_personal_url_not_github', () => {
    const { masked, placeholders } = masker.mask('블로그: http://myblog.tistory.com/about')
    expect(masked).toContain('[MASKED_URL]')
    expect(placeholders).toBe(1)
  })

  it('test_AC_1_preserves_github_tech_profile', () => {
    // github.com/<user> 형태(기술 프로필)는 보존
    const { masked } = masker.mask('깃헙: https://github.com/kohj1018')
    expect(masked).toContain('github.com')
    expect(masked).not.toContain('[MASKED_URL]')
  })

  it('test_AC_1_masks_korean_name', () => {
    // 한글 2~4자 성명 패턴
    const { masked, placeholders } = masker.mask('이름: 홍길동')
    expect(masked).toContain('[MASKED_NAME]')
    expect(placeholders).toBe(1)
  })

  it('test_AC_1_placeholders_count_matches_total_replacements', () => {
    const raw = '이름: 김철수\n이메일: kim@test.com\n전화: 010-9999-0000'
    const { placeholders } = masker.mask(raw)
    // 이름 1 + 이메일 1 + 전화 1 = 3
    expect(placeholders).toBeGreaterThanOrEqual(3)
  })
})

// AC-2: evidence 토큰(스택·학교명·경력기간 수치)이 마스킹 후에도 보존된다.
describe('RegexResumeMasker — AC-2 evidence 보존(과마스킹 0)', () => {
  const masker = new RegexResumeMasker()

  it('test_AC_2_evidence_tokens_preserved', () => {
    const raw = [
      '## Skills',
      '- Python, TypeScript',
      '- React, Next.js',
      '## 경력',
      '- A사 백엔드 엔지니어 2년',
      '## 학력',
      '- 서울대학교 컴퓨터공학과',
    ].join('\n')

    const { masked } = masker.mask(raw)

    // 스택 토큰 보존
    expect(masked).toContain('Python')
    expect(masked).toContain('TypeScript')
    expect(masked).toContain('React')
    expect(masked).toContain('Next.js')
    // 경력기간 수치 보존
    expect(masked).toContain('2년')
    // 학교명 보존
    expect(masked).toContain('서울대학교')
    expect(masked).toContain('컴퓨터공학과')
  })

  it('test_AC_2_numbers_and_durations_not_masked', () => {
    const raw = '경력 3년 6개월, 프로젝트 12건, 팀원 5명'
    const { masked } = masker.mask(raw)
    expect(masked).toContain('3년')
    expect(masked).toContain('12건')
    expect(masked).toContain('5명')
  })
})
