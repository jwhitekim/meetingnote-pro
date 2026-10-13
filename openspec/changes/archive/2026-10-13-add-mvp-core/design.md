# Design

## Context

저장소에는 코드가 없고 `docs/` PDF 3종과 `publish/` 만 있다. 무엇을 만드는지는 proposal.md 와 specs/ 8개, 문서끼리 어긋난 자리의 결정은 `docs/결정기록.md` 를 따른다.

- 기술 스택은 프로그램정의서 9절로 고정: FastAPI + SQLAlchemy, 로컬 SQLite, Vanilla JS + Tailwind CDN
- 화면이 쓰는 API 는 스토리보드 I-01 통합매핑표가 기준이다 (로그인 화면 3개 · 회의록 목록 5개 · 상세 7개 · 칸반 4개 · 팀 설정 7개 · 내 정보 4개)
- 머신의 Python 은 3.13

## Goals / Non-Goals

**Goals:**
- `uvicorn` 한 번으로 화면 · API · Swagger UI 가 같은 주소(`http://127.0.0.1:8000`)에서 뜬다
- AI 키 없이 pytest 전부가 돈다
- 화면은 퍼블리싱 파일과 비교했을 때 데이터 채우는 JS 와 STATE 바 제거 말고는 차이가 없다

**Non-Goals:**
- Vercel 배포 설정(`pyproject.toml` 의 `[tool.vercel]`), Neon 연결 확인 - 다음 변경. 다만 `DATABASE_URL` 분기는 코드에 둔다
- 브라우저 자동화 테스트. 화면은 tasks 맨 아래 육안 수락 항목으로 확인한다

## Decisions

### 폴더 구조

```
backend/app/
  main.py          FastAPI 앱 · 라우터 등록 · StaticFiles · 오류 핸들러 · CORS
  config.py        .env 읽기 (JWT_SECRET · STT_API_KEY · DATABASE_URL · CORS_ORIGINS · 모델 이름)
  db.py            엔진 · 세션. DATABASE_URL 있으면 그것, 없으면 sqlite:///meetingnote.db
  models.py        7테이블
  schemas.py       요청 · 응답 모델 (응답 필드는 프로그램정의서 7-1 그대로)
  security.py      bcrypt · JWT 발급과 검증 · 현재 사용자 · 팀 멤버 확인
  errors.py        ApiError(status, code, msg) 와 {code, msg} 응답
  activity.py      활동 남기기와 완성 문장 만들기
  ai.py            받아쓰기 · 세 항목 구분 (Gemini). 테스트가 갈아끼우는 자리
  routers/         auth · teams · meetings · todos · comments · activities
frontend/          publish 의 화면 6종 + theme.js + api.js
tests/             pytest
```

대안: 단일 `main.py`. 26개 경로와 권한 검사가 한 파일에 몰려 읽기 어렵다.

### 화면은 publish 를 복사해서 시작

`publish/*.html` 을 `frontend/` 로 복사한 뒤 목업 배열 · `STATES` · `stateBar` 호출만 걷어내고 API 결과로 채운다. 마크업과 클래스는 고치지 않는다(결정기록 1). `theme.js` 는 그대로 복사한다 - `stateBar` 정의가 남지만 부르지 않는다. `publish/index.html` 은 퍼블리싱 목차라 옮기지 않는다.

공통 동작은 새 파일 `frontend/api.js` 하나에 둔다: 토큰 보관, `fetch` 래퍼(`Authorization` 헤더 · `{code,msg}` 해석 · 401 이면 토큰 삭제 후 `/login.html?expired=1`), 소속 팀 확인과 이동, 머리글의 팀 이름 · 로그아웃. 화면이 새 클래스 조합을 만들어야 할 때는 같은 화면 퍼블리싱에 있는 문자열을 가져다 쓴다.

대안: 화면을 `window.UI` 로 다시 짜기. 결정기록 1 에서 버렸다.

### 인증

- bcrypt 직접 사용(passlib 은 bcrypt 4 이상과 경고가 난다). 비밀번호 검사는 비용 12 기본값, 테스트는 비용 4 로 낮춰 속도를 맞춘다
- PyJWT HS256, `exp` = 발급 + 24시간, `sub` = user id. 키는 `JWT_SECRET`
- 토큰이 없음 · 만료 · 위조 모두 401 `TOKEN_EXPIRED`. 문서의 오류 코드 목록에 「인증 없음」 이 따로 없고, 화면 동작(토큰 지우고 로그인으로)이 셋 모두 같다
- Swagger Authorize 는 FastAPI `HTTPBearer(auto_error=False)` 로 보안 스킴을 선언해 얻는다. `auto_error=False` 로 두고 직접 401 `TOKEN_EXPIRED` 를 낸다 (기본값이면 403 이 나간다)

### 오류 형식

`ApiError` 하나와 예외 핸들러 셋(ApiError · RequestValidationError · HTTPException)으로 모든 오류를 `{code, msg}` 로 낸다. 검증 오류는 400 `VALIDATION_ERROR`. 이메일 형식과 비밀번호 길이는 라우터에서 먼저 검사해 `EMAIL_INVALID` · `PASSWORD_TOO_WEAK` 로 낸다.

| 상황 | 상태 | code |
|---|---|---|
| 팀 멤버 아님 · 쓴 사람/owner 아님 | 403 | FORBIDDEN |
| owner 전용 (팀 이름 · 코드 재발급 · 할 일 삭제) | 403 | OWNER_ONLY |
| 없는 회의록 | 404 | MEETING_NOT_FOUND |
| 없는 할 일 · 댓글 · 팀 | 404 | NOT_FOUND |
| 정원 6명 | 409 | TEAM_FULL |
| 받아쓰기 실패 · 60초 초과 | 502 | TRANSCRIBE_FAILED |

`TRANSCRIBE_FAILED` 는 문서의 14종에 없는 코드라 새로 더한다. 외부 서비스 실패를 `VALIDATION_ERROR` 로 내면 사용자가 자기 입력이 틀렸다고 읽는다.

### 권한 확인

사용자당 팀은 하나(결정기록). 모든 팀 범위 경로는 `memberships` 에서 (team_id, user_id) 를 찾아 없으면 403. 회의록 · 할 일 · 댓글 경로는 대상의 team_id 를 거슬러 찾은 뒤 같은 검사를 한다. 회의록 수정은 문서가 정하지 않아 삭제와 같게 「쓴 사람 + owner」 로 둔다.

### 받아쓰기와 세 항목 구분 (결정기록 2)

- `ai.py` 에 함수 둘: `transcribe(bytes, filename) -> str`, `split(body, member_names) -> {summary, decisions: [str], todos: [{what, assignee, due}]}`
- Gemini API, SDK 는 `google-genai` (결정기록 2, 2026-10-06 OpenAI 에서 변경). 받아쓰기 모델 `STT_MODEL` · 구분 모델 `LLM_MODEL` 모두 기본 `gemini-3.1-flash-lite`. 키는 `STT_API_KEY` 하나. 모델 이름을 환경변수로 뺀 것은 공급자 쪽 모델 교체가 잦아서다
- 받아쓰기는 오디오를 `generate_content` 에 넣어 전문을 받는다. 15MB 이하는 요청에 바로 싣고(`Part.from_bytes`), 넘으면 Files API 로 먼저 올린다 - 요청 전체 20MB 제한 때문
- 형식(wav · mp3)은 업로드 판정 결과를 그대로 넘겨 mime type 으로 쓴다
- 구분은 JSON 출력(`response_mime_type=application/json`) + 결과 검증. 담당자는 팀 멤버 이름과 정확히 같을 때만 연결하고 나머지는 null
- 구분이 실패하면 세 항목을 비우고 저장한다(본문은 잃지 않음). 받아쓰기는 HTTP 타임아웃 60초
- 테스트는 `ai.transcribe` · `ai.split` 을 가짜로 바꾼다. 실제 호출 시험은 수락 항목에서 키를 넣고 한 번 한다

### 업로드 판정

- 크기: 본문을 25MB + 1바이트까지만 읽어 넘으면 413
- 형식: 앞 바이트로 판정. wav = `RIFF....WAVE`, mp3 = `ID3` 또는 프레임 동기 `0xFFE0` 마스크. 확장자와 content-type 은 보지 않는다

### 데이터와 집계

- 7테이블은 프로그램정의서 6절 그대로. `todos.status` 는 `OPEN|DOING|DONE`, `meetings.decisions` 는 줄바꿈 TEXT, 시각은 UTC ISO 8601
- 회의록 삭제 시 딸린 todos · comments 는 ORM cascade 로 함께 지운다. activities 는 `target` 에 글자로만 남아 영향 없다
- 목록 집계(todo_done_count 등)는 회의록 목록 쿼리 한 번에 서브쿼리로 붙인다. 회의록마다 따로 세면 100ms 기준을 넘길 수 있다
- 정렬은 프로그램정의서 7-1. 할 일의 status 순서는 OPEN · DOING · DONE
- 테이블은 앱 시작 때 `create_all`. 마이그레이션 도구는 첫 판이라 두지 않는다

### 활동 문장

`activity.py` 가 kind 별 문장 틀을 가진다. 예: `meeting_add` → 「김대리님이 회의록 「2차 스프린트」 를 올렸습니다」. 행위자 이름은 남길 때 문장에 넣어 저장한다(나중에 이름을 바꿔도 지난 기록은 그대로).

### Swagger UI (결정기록 4)

FastAPI 기본 `/docs` 를 켜고, 라우터마다 `tags`(Auth · Team · Meeting · Todo · Comment · Activity)를 단다. 배포가 이번 범위 밖이라 켜고 끄는 설정은 두지 않는다. 배포 변경에서 정한다.

### 테스트

pytest + FastAPI `TestClient`. 테스트마다 임시 SQLite 파일, `ai` 함수는 fixture 로 가짜. 시나리오 하나가 테스트 하나가 되도록 specs 의 Scenario 를 따라 짠다. 회원가입 · 로그인을 묶은 fixture(owner · member · 다른 팀 사용자)로 반복을 줄인다.

## Risks / Trade-offs

- [AI 가 담당자 이름을 다르게 적음(「김 대리」)] → 정확히 같을 때만 연결하고 나머지는 미정. 사람이 상세 화면에서 배정한다
- [AI 구분 품질은 pytest 로 못 잰다] → 수락 항목에서 실제 키로 한 번 확인
- [퍼블리싱 그대로라 디자인시스템 규칙(버튼 높이 · 모서리 · 인라인 style)을 어김] → 결정기록 1 로 의도된 것. 디자인시스템과 맞추는 일은 따로 정한다
- [SQLite 와 Postgres 차이(대소문자 검색 등)] → 검색은 `ilike` 로 써서 양쪽 같게. Postgres 실행 확인은 배포 변경에서
- [25MB 를 메모리로 읽음] → 동시 50명 전제에서 허용. 분할 업로드는 범위 외

## Migration Plan

첫 변경이라 옮길 데이터가 없다. 로컬 실행:

1. `python -m venv .venv && .venv/bin/pip install -r requirements.txt`
2. `.env.example` 를 `.env` 로 복사해 `JWT_SECRET` · `STT_API_KEY` 를 채운다
3. `.venv/bin/uvicorn backend.app.main:app --reload`
4. 되돌리기: `meetingnote.db` 를 지우면 빈 상태로 돌아간다
