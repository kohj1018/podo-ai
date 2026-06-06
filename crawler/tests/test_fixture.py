"""crawler fixture 모드 — load_fixture 파싱·그룹핑 (DB 불요, E2E 재현 경로 가드).

graduation §5 #3: fresh-clone E2E가 네트워크 없이 결정적 공고 집합을 쓰도록
crawler/fixtures/seed_jobs.txt를 채널별로 그룹핑한다. 이 fixture가 깨지면
무키 E2E의 캐시 키(JD raw_text 기반)가 흔들리므로 형태를 고정 검증한다.
"""

from __future__ import annotations

from pathlib import Path

from crawler.__main__ import load_fixture

_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "seed_jobs.txt"

_CHANNELS = {"toss", "daangn"}
_REQUIRED = ("job_id", "company", "title", "url", "raw_text")


def test_seed_fixture_groups_by_channel() -> None:
    """커밋된 seed fixture가 toss·당근 두 채널로 그룹핑되고 양쪽 모두 공고를 가진다."""
    grouped = load_fixture(str(_FIXTURE))

    assert set(grouped) == _CHANNELS
    assert grouped["toss"], "toss 채널 fixture 공고 없음"
    assert grouped["daangn"], "daangn 채널 fixture 공고 없음"


def test_seed_fixture_jobs_have_required_fields() -> None:
    """모든 fixture 공고가 필수 필드 + 비어있지 않은 raw_text(=evidence haystack)를 가진다."""
    grouped = load_fixture(str(_FIXTURE))
    jobs = [j for channel_jobs in grouped.values() for j in channel_jobs]

    assert len(jobs) >= 4  # 5단계 배지 spread를 위한 최소 다양성
    for job in jobs:
        for key in _REQUIRED:
            assert job.get(key), f"{job.get('job_id', '?')}: {key} 누락/빈값"
        assert job["company"] in _CHANNELS  # 그룹 키가 알려진 채널


def test_seed_fixture_job_ids_unique() -> None:
    """job_id 중복 없음 — upsert/캐시 키 결정성 전제."""
    grouped = load_fixture(str(_FIXTURE))
    ids = [j["job_id"] for channel_jobs in grouped.values() for j in channel_jobs]

    assert len(ids) == len(set(ids)), f"중복 job_id: {ids}"
