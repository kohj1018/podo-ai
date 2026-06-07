"""T-063 run_sources 테스트 — AC-1, AC-2.

AC-1: registry_seed의 active 소스 수집 → job_postings upsert + source_crawl_status 갱신.
AC-2: gate 실패(HTTP 403) 소스는 blocked 상태로 기록, 나머지 소스는 정상 수집(부분 실패 격리).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# AC-1: 소스 수집 → job_postings upsert + source_crawl_status 갱신
# ---------------------------------------------------------------------------


def test_AC_1_sources_upsert_and_coverage_status() -> None:
    """AC-1: registry_seed active 소스 3개 이상 수집 → upsert + source_crawl_status 기록.

    fixture mock 사용(실 DB/네트워크 불요).
    """
    from crawler.run_sources import run_all_sources

    # Arrange: 3개 소스 mock (1 greenhouse + 1 toss + 1 greeting)
    mock_jobs_by_source = {
        "daangn": [
            {
                "job_id": "d-1",
                "company": "daangn",
                "title": "엔지니어",
                "url": "https://gh.io/d-1",
                "raw_text": "JD",
            }
        ],
        "toss": [
            {
                "job_id": "t-1",
                "company": "toss",
                "title": "백엔드",
                "url": "https://toss.im/1",
                "raw_text": "JD",
            }
        ],
        "coupang": [
            {
                "job_id": "c-1",
                "company": "coupang",
                "title": "SWE",
                "url": "https://coupang.jobs/1",
                "raw_text": "JD",
            }
        ],
    }
    # gate_check 모두 성공
    gate_ok = MagicMock()
    gate_ok.ok = True
    gate_ok.reason = "ok"

    upserted: dict[str, list] = {}
    crawl_statuses: dict[str, dict] = {}

    def mock_upsert(conn: object, source: str, jobs: list, *, now: object) -> dict:
        upserted[source] = jobs
        return {"new": len(jobs), "kept": 0, "closed": 0}

    def mock_record_status(
        conn: object,
        source_id: str,
        *,
        status: str,
        last_success_at: object | None = None,
        last_error: str | None = None,
        tier: str = "",
        method: str = "",
    ) -> None:
        crawl_statuses[source_id] = {
            "status": status,
            "last_success_at": last_success_at,
            "last_error": last_error,
        }

    with (
        patch("crawler.run_sources.upsert_jobs", side_effect=mock_upsert),
        patch(
            "crawler.run_sources.record_source_crawl_status",
            side_effect=mock_record_status,
        ),
        patch("crawler.run_sources._build_adapter") as mock_build,
        patch("crawler.run_sources._get_connection") as mock_conn,
    ):
        mock_conn.return_value.__enter__ = lambda s: MagicMock()
        mock_conn.return_value.__exit__ = MagicMock(return_value=False)

        def build_adapter(spec: object) -> MagicMock:
            a = MagicMock()
            a.gate_check.return_value = gate_ok
            a.fetch_jobs.return_value = mock_jobs_by_source.get(
                getattr(spec, "company", ""), []
            )
            return a

        mock_build.side_effect = build_adapter

        result = run_all_sources(sources=list(mock_jobs_by_source.keys()))

    # Assert: 3개 소스 모두 upsert + coverage status 갱신
    assert set(upserted.keys()) == set(mock_jobs_by_source.keys()), (
        f"upsert 누락 소스: {set(mock_jobs_by_source.keys()) - set(upserted.keys())}"
    )
    assert set(crawl_statuses.keys()) == set(mock_jobs_by_source.keys()), (
        f"status 갱신 누락: {set(mock_jobs_by_source.keys()) - set(crawl_statuses.keys())}"
    )

    for source_id, stat in crawl_statuses.items():
        assert stat["status"] == "active", (
            f"{source_id}: expected active, got {stat['status']}"
        )
        assert stat["last_success_at"] is not None, f"{source_id}: last_success_at 없음"
        assert stat["last_error"] is None, (
            f"{source_id}: 성공인데 last_error={stat['last_error']}"
        )

    assert result["collected"] == 3
    assert result["failed"] == 0


# ---------------------------------------------------------------------------
# AC-2: 부분 실패 격리 — gate 실패 소스만 blocked, 나머지 정상 수집
# ---------------------------------------------------------------------------


def test_AC_2_partial_failure_isolation() -> None:
    """AC-2: 소스 A=403 gate 실패, 소스 B·C=정상 → A만 blocked, B·C는 active 수집.

    부분 실패가 전체를 오염하지 않음을 검증.
    """
    from crawler.run_sources import run_all_sources

    gate_blocked = MagicMock()
    gate_blocked.ok = False
    gate_blocked.reason = "HTTP 403 blocked"

    gate_ok = MagicMock()
    gate_ok.ok = True
    gate_ok.reason = "ok"

    sources_gates = {
        "bad_source": gate_blocked,
        "good_source_1": gate_ok,
        "good_source_2": gate_ok,
    }
    sources_jobs = {
        "bad_source": [],
        "good_source_1": [
            {
                "job_id": "g1-1",
                "company": "good1",
                "title": "SWE",
                "url": "https://good1.com/1",
                "raw_text": "",
            }
        ],
        "good_source_2": [
            {
                "job_id": "g2-1",
                "company": "good2",
                "title": "BE",
                "url": "https://good2.com/1",
                "raw_text": "",
            }
        ],
    }

    upserted: dict[str, list] = {}
    crawl_statuses: dict[str, dict] = {}

    def mock_upsert(conn: object, source: str, jobs: list, *, now: object) -> dict:
        upserted[source] = jobs
        return {"new": len(jobs), "kept": 0, "closed": 0}

    def mock_record_status(
        conn: object,
        source_id: str,
        *,
        status: str,
        last_success_at: object | None = None,
        last_error: str | None = None,
        tier: str = "",
        method: str = "",
    ) -> None:
        crawl_statuses[source_id] = {
            "status": status,
            "last_success_at": last_success_at,
            "last_error": last_error,
        }

    with (
        patch("crawler.run_sources.upsert_jobs", side_effect=mock_upsert),
        patch(
            "crawler.run_sources.record_source_crawl_status",
            side_effect=mock_record_status,
        ),
        patch("crawler.run_sources._build_adapter") as mock_build,
        patch("crawler.run_sources._get_connection") as mock_conn,
    ):
        mock_conn.return_value.__enter__ = lambda s: MagicMock()
        mock_conn.return_value.__exit__ = MagicMock(return_value=False)

        def build_adapter(spec: object) -> MagicMock:
            a = MagicMock()
            company = getattr(spec, "company", "")
            a.gate_check.return_value = sources_gates.get(company, gate_ok)
            a.fetch_jobs.return_value = sources_jobs.get(company, [])
            return a

        mock_build.side_effect = build_adapter

        result = run_all_sources(sources=list(sources_gates.keys()))

    # bad_source: gate 실패 → blocked, upsert 호출 안 됨
    assert crawl_statuses["bad_source"]["status"] == "blocked", (
        f"bad_source status={crawl_statuses['bad_source']['status']}"
    )
    assert "bad_source" not in upserted, "gate 실패 소스가 upsert되면 안 됨"

    # good_source_1·2: 정상 수집
    for src in ("good_source_1", "good_source_2"):
        assert crawl_statuses[src]["status"] == "active", (
            f"{src}: expected active, got {crawl_statuses[src]['status']}"
        )
        assert src in upserted, f"{src}: upsert 호출 안 됨"

    assert result["collected"] == 2
    assert result["failed"] == 1
