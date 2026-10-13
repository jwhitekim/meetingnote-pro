"""화면 파일 정적 검사 - 화면 제공 경로 · 퍼블리싱 디자인 그대로."""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PAGES = ["login", "meetings", "detail", "todos", "team", "profile"]
SCRIPTS = re.compile(r"<script>\n(.*?)</script>", re.S)


def page_text(name):
    return (ROOT / "frontend" / f"{name}.html").read_text()


def markup_only(html):
    return SCRIPTS.sub("", html)


@pytest.mark.parametrize("name", PAGES)
def test_page_served(client, name):
    r = client.get(f"/{name}.html")
    assert r.status_code == 200 and "text/html" in r.headers["content-type"]


def test_theme_and_api_js_served(client):
    assert client.get("/theme.js").status_code == 200
    assert client.get("/api.js").status_code == 200


def test_theme_js_same_as_publish():
    assert (ROOT / "frontend/theme.js").read_bytes() == (ROOT / "publish/theme.js").read_bytes()


@pytest.mark.parametrize("name", PAGES)
def test_no_state_bar_or_mock(name):
    html = page_text(name)
    assert "stateBar(" not in html
    assert 'id="note"' not in html
    assert "STATES" not in html and "SAMPLE" not in html


@pytest.mark.parametrize("name", PAGES)
def test_markup_same_as_publish_except_notes(name):
    """스크립트 밖 마크업은 퍼블리싱과 같다. 다른 줄은 api.js 로드와 퍼블리싱 확인용 메모 삭제뿐."""
    pub = markup_only((ROOT / "publish" / f"{name}.html").read_text()).splitlines()
    mine = markup_only(page_text(name)).splitlines()
    added = [l for l in mine if l not in pub]
    removed = [l for l in pub if l not in mine]
    assert added == ['<script src="api.js"></script>']
    assert all("퍼블리싱 확인용" in l or 'id="note"' in l or "단건 조회에만 body" in l for l in removed), removed


def test_no_html5_draggable():
    html = page_text("todos")
    assert "draggable" not in html and "dragstart" not in html
    assert "pointerdown" in html and "pointerup" in html


HEX = re.compile(r"#[0-9a-fA-F]{3,8}\b")
TW_PALETTE = re.compile(r"\b(?:bg|text|border|ring)-(?:slate|gray|zinc|neutral|stone|amber|yellow|lime|emerald|teal|cyan|sky|indigo|violet|fuchsia|pink|rose)-\d{2,3}\b")


@pytest.mark.parametrize("name", PAGES + ["api"])
def test_no_new_colors(name):
    path = ROOT / "frontend" / (f"{name}.js" if name == "api" else f"{name}.html")
    text = path.read_text()
    assert not HEX.findall(text)
    assert not TW_PALETTE.findall(text)
