# Proposal

## Why

할 일 기한이 `due_text` 자유 문자열(「다음 주 금요일」 · 「이번 달 안」)이라 시스템이 날짜로 비교할 수 없다. 기한이 지났는지는 지금 화면의 `API.isLate` 가 「어제」 · `YYYY-MM-DD` · `M월 D일` 몇 가지 꼴만 추측하고, 나머지는 사람이 글을 읽고 직접 따져야 한다. add-mvp-core 를 마친 뒤 이 점이 지적됐다.

## What Changes

- 할 일에 `due_date`(날짜, 비어 있을 수 있음)를 더한다. 회의에서 나온 말은 `due_text` 에 그대로 남겨 원문을 잃지 않는다
- 회의록을 저장할 때 세 항목 구분 AI 에 회의 일시(`met_at`)를 함께 주고, 할 일마다 원문 기한과 함께 그 날짜로 바꾼 `due` 날짜를 받는다. 날짜로 정할 수 없는 말(「이번 달 안」은 말일로 정할 수 있지만 「나중에」는 못 한다)은 비운다. 지어내지 않는다
- 할 일 API 응답(`GET /api/teams/{id}/todos` · `GET /api/me/todos` · `PUT /api/todos/{id}` · 회의록 단건의 `todos`)에 `due_date` 와 `is_overdue` 를 더한다. `is_overdue` 는 완료가 아니고 `due_date` 가 한국 시간(Asia/Seoul) 오늘보다 앞일 때 참이다
- `PUT /api/todos/{id}` 로 `due_date` 를 바꾸거나 비울 수 있게 한다. 날짜 꼴이 아니면 400
- 할 일 정렬을 상태 다음 `due_date` 이른 순(없으면 뒤), 그다음 id 로 바꾼다
- 화면(칸반 · 회의록 상세 · 내 정보)의 기한 고치기를 날짜 고르기로 바꾸고, 기한 지남 표시는 서버의 `is_overdue` 만 따른다. 화면 쪽 추측 함수 `API.isLate` 는 걷어낸다
- 이미 만든 로컬 DB 에 `due_date` 칸을 더하는 처리를 서버 시작 때 넣는다. 기존 할 일의 `due_date` 는 비어 있다

## Out of Scope

- 기존 할 일의 `due_text` 를 날짜로 되짚어 채우는 일괄 변환
- 기한 임박 · 지남 알림 (메일 · 푸시)
- 사용자 · 팀별 시간대 설정. 이번에는 Asia/Seoul 하나로 판정한다
- 시각 단위 기한. 날짜까지만 다룬다

## Capabilities

### New Capabilities

없음

### Modified Capabilities

- `todo-board`: 할 일 목록 필드와 정렬에 `due_date` · `is_overdue` 추가, 기한 변경에 `due_date` 추가
- `meeting-notes`: 세 항목 구분이 회의 일시를 기준으로 기한 날짜를 함께 뽑는다
- `web-app`: 기한 지남 표시는 서버 판정을 따르고, 기한은 날짜로 고른다

## Impact

- 코드: `backend/app/models.py`(Todo.due_date), `backend/app/db.py`(기존 DB 칸 추가), `backend/app/ai.py`(프롬프트 · 파싱), `backend/app/routers/meetings.py` · `todos.py`(저장 · 응답 · 정렬 · 검증), `frontend/api.js` · `todos.html` · `detail.html` · `profile.html`
- API: 응답에 필드 두 개가 늘고 `PUT /api/todos/{id}` 가 `due_date` 를 받는다. 기존 필드는 그대로라 깨지는 변경은 없다
- DB: `todos` 테이블에 `due_date DATE NULL` 칸 추가. 로컬 SQLite 와 Neon Postgres 둘 다 해당
- 테스트: `tests/test_ai.py` · `test_meetings.py` · `test_todos.py` · `test_frontend.py` 에 경우 추가
