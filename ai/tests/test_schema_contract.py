"""Schema contract tests — placeholder until DB schema is finalized.

Real column validation is a follow-up task (Worker-dependent columns).
See ARCHITECTURE_OVERVIEW §3-2 / task T-001 §2.
"""

import pytest


@pytest.mark.skip(reason="Placeholder — DB schema not yet finalized (T-001 §2)")
def test_AC_schema_contract_worker_columns() -> None:
    """Verify Worker-dependent columns exist in DB schema.

    WHY skipped: schema is not finalized; this stub satisfies the R6 guard
    placeholder requirement. A follow-up task will implement real validation.
    """
    raise NotImplementedError("implement after Prisma schema is finalized")
