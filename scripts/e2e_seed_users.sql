-- E2E 테스트 사용자 2명(A·B) 시드 — 멀티유저 격리·계정 PII 스캔용(T-052).
-- 고정 id로 test-session 우회(/auth/test-session {userId})와 매칭. 계정 식별자(email·display_name)는
-- 식별 목적이라 마스킹 안 함(ADR-105 Amend1) — 단, 스코어링 경로(ranking_runs.result·캐시·로그) 미유입을
-- e2e_account_pii_scan.py가 검증한다. 멱등(ON CONFLICT) — 재실행 안전.
INSERT INTO users (id, provider, provider_account_id, email, display_name)
VALUES
  ('e2e-user-a', 'test', 'e2e-acct-a', 'e2e-acct-a@example.test', 'E2E Account Alpha'),
  ('e2e-user-b', 'test', 'e2e-acct-b', 'e2e-acct-b@example.test', 'E2E Account Bravo')
ON CONFLICT (id) DO NOTHING;
