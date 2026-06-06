// paste 경로 입력 바디. 빈값/크기 검증은 컨트롤러(크기)·서비스(RESUME_EMPTY)에서 수동 수행한다
// (class-validator 미설치 — manual validation, ADR-006 시스템 경계 검증 원칙).
export class CreateResumeDto {
  text?: string
}
