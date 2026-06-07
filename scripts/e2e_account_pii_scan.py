"""scripts/e2e_account_pii_scan.py — 계정 PII 미유입 스캔 (T-052 AC-3 / F-016 FAC-6).

계정 식별자(이메일·표시이름)가 *스코어링 경로*(ranking_runs.result·.cache/llm)에
유입되지 않았는지 실 DB·캐시에서 검증한다(ADR-105 Amend1). 계정 PII는 식별 목적이라
users엔 마스킹 없이 저장하지만, 스코어링 표면엔 절대 들어가면 안 된다. 0건이어야 통과.

출력은 순수 ASCII — Windows cp949 콘솔 인코딩 에러 회피.
호출: DATABASE_URL=... uv run python scripts/e2e_account_pii_scan.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from core.db import fetch_all

# e2e_seed_users.sql의 계정 식별자 — 스코어링 경로에서 0건이어야 한다.
ACCOUNT_PII = [
    "e2e-acct-a@example.test",
    "e2e-acct-b@example.test",
    "E2E Account Alpha",
    "E2E Account Bravo",
]

_DEFAULT_CACHE = Path(__file__).resolve().parent.parent / "ai/worker/fixtures/llm_cache"
CACHE_DIR = Path(os.environ.get("LLM_CACHE_DIR", str(_DEFAULT_CACHE)))


def main() -> int:
    leaks: list[str] = []

    # ranking_runs.result — worker가 쓰는 opaque JSONB(주 누출 표면).
    for rid, text in fetch_all("SELECT id, result::text FROM ranking_runs"):
        for pii in ACCOUNT_PII:
            if pii in (text or ""):
                leaks.append(f"ranking_runs[{rid}].result <- {pii!r}")

    # .cache/llm — LLM 프롬프트/응답 캐시(계정 PII가 프롬프트에 새면 여기 남는다).
    if CACHE_DIR.exists():
        for f in CACHE_DIR.glob("*.json"):
            txt = f.read_text(encoding="utf-8", errors="ignore")
            for pii in ACCOUNT_PII:
                if pii in txt:
                    leaks.append(f"{f.name} <- {pii!r}")

    if leaks:
        print("[account-pii-scan] FAIL: account PII found in scoring path:")
        for leak in leaks:
            print(f"  - {leak}")
        return 1

    print(
        f"[account-pii-scan] OK: 0 account PII across ranking_runs.result + .cache/llm "
        f"({len(ACCOUNT_PII)} literals)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
