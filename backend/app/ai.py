"""받아쓰기와 세 항목 구분 - Gemini (docs/결정기록.md 2). 테스트는 transcribe · split 을 갈아끼운다."""
import io
import json
import logging

from . import config

log = logging.getLogger(__name__)

TIMEOUT_SEC = 60  # ACME Constraints: 받아쓰기 60초 이내
DEFAULT_MODEL = "gemini-3.1-flash-lite"
# 요청 본문에 바로 싣는 오디오 상한. 넘으면 Files API 로 먼저 올린다 (요청 전체 20MB 제한)
INLINE_LIMIT = 15 * 1024 * 1024
MIME = {"wav": "audio/wav", "mp3": "audio/mp3"}


# 도구를 쓰지 않으므로 자동 함수 호출을 끈다 (켜 두면 호출마다 SDK 경고가 찍힌다)
NO_AFC = {"disable": True}


class AIError(Exception):
    pass


def _client():
    key = config.env("STT_API_KEY")
    if not key:
        raise AIError("STT_API_KEY 가 없습니다")
    from google import genai
    from google.genai import types
    return genai.Client(api_key=key, http_options=types.HttpOptions(timeout=TIMEOUT_SEC * 1000))


TRANSCRIBE_PROMPT = """이 회의 녹음을 한국어로 받아써라.
말한 내용만 그대로 적고, 요약하거나 덧붙이지 않는다. 화자 구분은 하지 않는다. 받아쓴 글만 출력한다."""


def transcribe(data: bytes, kind: str) -> str:
    """kind 는 내용으로 판정한 형식 (wav | mp3)."""
    try:
        from google.genai import types
        client = _client()
        mime = MIME[kind]
        if len(data) <= INLINE_LIMIT:
            audio = types.Part.from_bytes(data=data, mime_type=mime)
        else:
            audio = client.files.upload(file=io.BytesIO(data), config={"mime_type": mime})
        r = client.models.generate_content(
            model=config.env("STT_MODEL", DEFAULT_MODEL),
            contents=[TRANSCRIBE_PROMPT, audio],
            config=types.GenerateContentConfig(automatic_function_calling=NO_AFC),
        )
        text = (r.text or "").strip()
        if not text:
            raise AIError("받아쓴 글이 비었습니다")
        return text
    except AIError:
        raise
    except Exception as e:  # 공급자 오류 · 시간 초과
        log.warning("받아쓰기 실패: %s", e)
        raise AIError(str(e)) from e


PROMPT = """다음은 한국어 회의 녹취 본문이다. 세 항목으로 나눠 JSON 하나만 출력하라.
{"summary": "3~5줄 요약, 줄바꿈 구분",
 "decisions": ["합의가 끝난 결정사항만. 논의만 하고 정하지 않은 것은 넣지 않는다"],
 "todos": [{"what": "할 일", "assignee": "본문에 나온 담당자 이름 그대로, 없으면 빈 글자", "due": "본문에 나온 기한 글자 그대로, 없으면 빈 글자"}]}
담당자와 기한을 지어내지 않는다. 결정이나 할 일이 없으면 빈 배열로 둔다.
팀 멤버 이름: {names}

본문:
"""


def parse_split(raw: str) -> dict:
    """모델 출력(JSON)을 검증해 {summary, decisions, todos} 로 푼다. 깨졌으면 AIError."""
    try:
        d = json.loads(raw)
    except (TypeError, json.JSONDecodeError) as e:
        raise AIError("구분 결과가 JSON 이 아닙니다") from e
    if not isinstance(d, dict):
        raise AIError("구분 결과 형식이 다릅니다")
    summary = d.get("summary") if isinstance(d.get("summary"), str) else ""
    decisions = [s.strip() for s in d.get("decisions") or [] if isinstance(s, str) and s.strip()]
    todos = []
    for t in d.get("todos") or []:
        if isinstance(t, dict) and isinstance(t.get("what"), str) and t["what"].strip():
            todos.append({
                "what": t["what"].strip(),
                "assignee": (t.get("assignee") or "").strip() if isinstance(t.get("assignee"), str) else "",
                "due": (t.get("due") or "").strip() if isinstance(t.get("due"), str) else "",
            })
    return {"summary": summary.strip(), "decisions": decisions, "todos": todos}


def split(body: str, member_names: list[str]) -> dict:
    try:
        from google.genai import types
        # 클라이언트를 변수에 붙잡아 둔다. 임시 객체로 쓰면 요청 전에 정리되며 연결이 닫힌다
        client = _client()
        r = client.models.generate_content(
            model=config.env("LLM_MODEL", DEFAULT_MODEL),
            contents=PROMPT.replace("{names}", ", ".join(member_names)) + body,
            config=types.GenerateContentConfig(response_mime_type="application/json", automatic_function_calling=NO_AFC),
        )
        raw = r.text
    except AIError:
        raise
    except Exception as e:
        log.warning("세 항목 구분 실패: %s", e)
        raise AIError(str(e)) from e
    return parse_split(raw)
