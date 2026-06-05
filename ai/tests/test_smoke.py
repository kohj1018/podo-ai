"""Smoke tests — AC-1 (pytest collects and passes) / AC-2 (all packages import)."""


def test_AC_1_pytest_collects() -> None:
    """AC-1: pytest가 이 테스트를 수집하고 통과해야 한다."""
    assert True


def test_AC_2_packages_import() -> None:
    """AC-2: 네 패키지 모두 ImportError 없이 로드되어야 한다."""
    import core  # noqa: F401
    import crawler  # noqa: F401
    import eval as eval_pkg  # noqa: F401
    import worker  # noqa: F401
