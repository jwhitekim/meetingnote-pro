"""ai.py 를 Gemini SDK 호출부만 가짜로 바꿔 검증한다."""
import json
from types import SimpleNamespace

import pytest

from backend.app import ai


class FakeGemini:
    def __init__(self, text=None, error=None):
        self.calls, self.uploads = [], []

        def generate_content(**kw):
            self.calls.append(kw)
            if error:
                raise error
            return SimpleNamespace(text=text)

        def upload(file, config):
            self.uploads.append(config)
            return "uploaded-file"

        self.models = SimpleNamespace(generate_content=generate_content)
        self.files = SimpleNamespace(upload=upload)


def use(monkeypatch, fake):
    monkeypatch.setattr(ai, "_client", lambda: fake)
    return fake


def test_split_parses_json(monkeypatch):
    content = json.dumps({
        "summary": "스프린트 계획을 다뤘다.",
        "decisions": ["검색은 제목과 참석자", " ", "업로드 25MB"],
        "todos": [{"what": "목록 구현", "assignee": "김대리", "due": "다음 주 금요일"},
                  {"what": "인터뷰", "assignee": "", "due": ""},
                  {"what": "  "}],
    }, ensure_ascii=False)
    fake = use(monkeypatch, FakeGemini(text=content))
    r = ai.split("본문", ["김대리", "박과장"])
    assert r["summary"] == "스프린트 계획을 다뤘다."
    assert r["decisions"] == ["검색은 제목과 참석자", "업로드 25MB"]
    assert r["todos"] == [{"what": "목록 구현", "assignee": "김대리", "due": "다음 주 금요일"},
                          {"what": "인터뷰", "assignee": "", "due": ""}]
    call = fake.calls[0]
    assert "김대리, 박과장" in call["contents"] and call["contents"].endswith("본문")
    assert call["config"].response_mime_type == "application/json"
    assert call["model"] == "gemini-3.1-flash-lite"


def test_split_broken_json_raises(monkeypatch):
    use(monkeypatch, FakeGemini(text="요약: ..."))
    with pytest.raises(ai.AIError):
        ai.split("본문", [])


def test_split_provider_error_raises(monkeypatch):
    use(monkeypatch, FakeGemini(error=TimeoutError("timeout")))
    with pytest.raises(ai.AIError):
        ai.split("본문", [])


def test_transcribe_inline_audio(monkeypatch):
    fake = use(monkeypatch, FakeGemini(text=" 받아쓴 글 "))
    assert ai.transcribe(b"RIFF....WAVE", "wav") == "받아쓴 글"
    prompt, part = fake.calls[0]["contents"]
    assert "받아써라" in prompt
    assert part.inline_data.mime_type == "audio/wav" and part.inline_data.data == b"RIFF....WAVE"
    assert fake.uploads == []


def test_transcribe_large_audio_uses_files_api(monkeypatch):
    fake = use(monkeypatch, FakeGemini(text="받아쓴 글"))
    ai.transcribe(b"\x00" * (ai.INLINE_LIMIT + 1), "mp3")
    assert fake.uploads == [{"mime_type": "audio/mp3"}]
    assert fake.calls[0]["contents"][1] == "uploaded-file"


def test_transcribe_empty_text_raises(monkeypatch):
    use(monkeypatch, FakeGemini(text=""))
    with pytest.raises(ai.AIError):
        ai.transcribe(b"RIFF", "wav")


def test_model_from_env(monkeypatch):
    monkeypatch.setenv("STT_MODEL", "gemini-x")
    fake = use(monkeypatch, FakeGemini(text="글"))
    ai.transcribe(b"RIFF", "wav")
    assert fake.calls[0]["model"] == "gemini-x"


def test_no_key_raises(monkeypatch):
    monkeypatch.setenv("STT_API_KEY", "")
    with pytest.raises(ai.AIError):
        ai.transcribe(b"", "wav")
