"""Opens every dashboard page with Streamlit's test runner and fails on any exception.
Needs exported data (data/marts/manifest.json); skipped otherwise."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
pytest.importorskip("streamlit")
pytestmark = pytest.mark.skipif(not (ROOT / "data/marts/manifest.json").exists(), reason="no exported marts")

sys.path.insert(0, str(ROOT / "app"))
PAGES = sorted((ROOT / "app" / "views").glob("*.py"))


def test_main_app_runs():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(ROOT / "app/streamlit_app.py"), default_timeout=60).run()
    assert not at.exception


@pytest.mark.parametrize("page", PAGES, ids=[p.stem for p in PAGES])
def test_page_runs(page):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(page), default_timeout=60).run()
    assert not at.exception, at.exception
