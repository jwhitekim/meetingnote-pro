# Design

## Context

- `todos.due_text` 는 `String(100)` 하나뿐이다. AI 프롬프트(`backend/app/ai.py` `PROMPT`)는 「본문에 나온 기한 글자 그대로」 만 받고, 회의 일시를 모른다.
- 할 일 정렬은 `ORDER BY status 순, due_text, id` 라 「다음 주」 와 「수요일」 이 글자 순으로 섞인다.
- 지남 판정은 `frontend/api.js` 의 `isLate` 가 화면에서만 한다. 「어제」 · `YYYY-MM-DD` · `M월 D일` 꼴 말고는 늘 false 다.
- 스키마는 `Base.metadata.create_all` 로만 만든다. 마이그레이션 도구가 없고, `create_all` 은 이미 있는 테이블에 칸을 더하지 않는다.
- 같은 코드가 로컬 SQLite 와 Vercel 의 Neon Postgres 양쪽에서 돈다.

## Goals / Non-Goals

**Goals:**
- 기한 날짜를 DB 에 날짜형으로 두고, 지남 판정을 서버 한 곳에서 한다
- 추가 AI 호출 없이 기존 세 항목 구분 한 번에 날짜까지 받는다
- 이미 데이터가 있는 DB(로컬 SQLite · Neon)를 지우지 않고 칸을 더한다

**Non-Goals:**
- Alembic 같은 마이그레이션 도구 도입. 칸 하나라 시작 시 점검으로 충분하다
- 기존 `due_text` 를 날짜로 되짚는 일괄 변환 (proposal Out of Scope)

## Decisions

### 1. `due_date DATE NULL` 칸을 더하고 `due_text` 는 그대로 둔다
원문(「다음 주 금요일」)은 회의 맥락이라 남긴다. 판정과 정렬은 `due_date` 만 쓴다.
- 대안: `due_text` 를 없애고 날짜만 둔다 → 「이번 달 안」 같은 말이 사라지고, 날짜로 못 바꾼 기한이 「미정」 이 된다. 사용자도 유지 쪽을 골랐다.

### 2. 날짜 변환은 세 항목 구분 AI 가 회의 날짜를 받아 한다
`split(body, member_names, met_on)` 으로 회의 날짜(한국 시간, `YYYY-MM-DD (요일)`)를 프롬프트에 넣고, 할 일마다 `"due_date": "YYYY-MM-DD 또는 빈 글자"` 를 받는다. `parse_split` 은 `date.fromisoformat` 이 받는 값만 남기고 나머지는 빈 값으로 둔다(지어낸 꼴은 버림).
- 대안: 서버 규칙 파서 → 「다음 주 금요일」 · 「월말」 같은 한국어 상대 표현을 다 못 덮는다.
- 대안: 사람이 매번 고름 → 지적의 핵심(사람이 직접 확인)이 그대로 남는다.

### 3. 지남 판정은 서버가 고정 +09:00 으로 한다
`today_kst() = datetime.now(timezone(timedelta(hours=9))).date()`, `is_overdue = status != "DONE" and due_date is not None and due_date < today_kst()`. `todo_out` 한 곳에서 계산하므로 할 일을 돌려주는 모든 응답(회의록 단건의 `todos` 포함)이 같은 값을 쓴다. 테스트는 `today_kst` 를 바꿔 끼워 날짜를 고정한다.
- `zoneinfo("Asia/Seoul")` 대신 고정 오프셋: 한국은 서머타임이 없고, 서버리스 런타임의 tz 데이터베이스 유무에 기대지 않는다.
- 대안: 화면이 비교 → 브라우저 시간대마다 결과가 달라지고, API 를 쓰는 다른 클라이언트가 같은 규칙을 다시 짜야 한다.

### 4. 정렬은 `status 순, due_date IS NULL, due_date, id`
SQLite 는 ASC 에서 NULL 이 앞, Postgres 는 뒤라 `due_date IS NULL` 을 먼저 정렬 키로 둬 두 DB 결과를 맞춘다.

### 5. 기존 DB 에 칸 더하기 - 시작 시 점검
`db.init_db` 에서 `create_all` 뒤에 `inspect(engine).get_columns("todos")` 로 `due_date` 가 없으면 `ALTER TABLE todos ADD COLUMN due_date DATE` 를 한 번 부른다. SQLite · Postgres 모두 같은 문장이 돈다. 이미 있으면 아무것도 안 한다.
- 대안: Postgres 의 `ADD COLUMN IF NOT EXISTS` → SQLite 가 지원하지 않는다.

### 6. API 입력 - `due_date: date | None`
Pydantic `date` 로 받아 `YYYY-MM-DD` 가 아니면 기존 검증 오류 경로로 400 `VALIDATION_ERROR` 가 된다. 응답은 `isoformat()` 문자열 또는 null.

### 7. 화면 - `<input type="date">` 와 서버 값 표시
칸반 · 상세의 기한 배지를 누르면 contentEditable 대신 날짜 칸을 띄운다. 배지 글자는 `due_date` → `M월 D일`, 없으면 `due_text`, 없으면 「미정」. 붉은 띠 · 배지는 `t.is_overdue` 만 본다. `API.isLate` 와 `LATE_WORDS` 를 지운다. `due_text` 를 손으로 고치는 길은 없앤다(원문은 회의록 본문 수정으로만 바뀐다).

## Risks / Trade-offs

- [AI 가 날짜를 틀리게 계산한다 (예: 「다음 주 금요일」 을 이번 주로)] → 원문 `due_text` 를 함께 보여 사람이 비교할 수 있고, 배지를 눌러 바로 고친다. 프롬프트에 회의 날짜의 요일까지 적어 계산 근거를 준다
- [시작할 때마다 컬럼 점검 쿼리가 한 번 돈다 (서버리스 콜드 스타트)] → `inspect` 한 번이라 수 ms. 점검은 `init_db` 안에서만 한다
- [기존 할 일은 `due_date` 가 비어 지남 표시가 사라진다 (전에는 `YYYY-MM-DD` 글자면 화면이 붉게 칠했다)] → 상세 · 칸반에서 날짜를 골라 채운다. 일괄 변환은 범위 밖
- [`due_text` 를 화면에서 못 고친다] → API 로는 여전히 받는다. 화면에서 원문을 고칠 일이 생기면 다음 변경에서 다룬다

## Migration Plan

1. 배포하면 `init_db` 가 `todos.due_date` 칸을 더한다. 로컬 SQLite 는 서버를 다시 띄우면 된다
2. 되돌리기: 이전 코드로 되돌려도 남은 `due_date` 칸은 읽히지 않을 뿐 동작에 지장이 없다. 칸 삭제는 하지 않는다
