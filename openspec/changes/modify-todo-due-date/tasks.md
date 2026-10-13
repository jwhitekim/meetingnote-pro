# Tasks

## 1. 데이터 - 기한 날짜 칸

- [ ] 1.1 `models.Todo` 에 `due_date: date | None` (`Date`, nullable) 를 더한다. 확인: 새 임시 DB 에서 `inspect(engine).get_columns("todos")` 에 `due_date` 가 있다 (근거: 팀 할 일 목록)
- [ ] 1.2 `db.init_db` 에서 `create_all` 뒤 `todos.due_date` 가 없으면 `ALTER TABLE todos ADD COLUMN due_date DATE` 를 부른다. 확인: `due_date` 없이 만든 SQLite 파일로 `init_db` 를 두 번 불러도 오류 없이 칸이 하나 생기는 테스트 통과, 기존 행은 `due_date` 가 null (근거: design 5)

## 2. 서버 - 판정 · 응답 · 정렬 · 변경

- [ ] 2.1 `today_kst()`(고정 +09:00)와 `todo_out` 의 `due_date`(isoformat 또는 null) · `is_overdue` 를 만든다. 확인: `today_kst` 를 2026-10-13 으로 고정한 `tests/test_todos.py` 에서 어제 기한 DOING true · 당일 false · DONE false · 글만 「어제」 false 시나리오 통과, 그리고 UTC 2026-10-12 16:00 에 `today_kst()` 가 2026-10-13 인 단위 테스트 통과 (근거: 기한 지남 판정)
- [ ] 2.2 할 일 정렬을 `status 순, due_date IS NULL, due_date, id` 로 바꾼다. 확인: OPEN 셋(10-20 · null · 10-15)이 10-15 · 10-20 · null 순인 테스트 통과, 기존 정렬 테스트 통과 (근거: 팀 할 일 목록)
- [ ] 2.3 `TodoIn` 에 `due_date: date | None` 을 더하고 `PUT /api/todos/{id}` 에서 보낸 경우에만 바꾼다. 확인: 날짜 지정(due_text 그대로) · null 로 비움(is_overdue false) · 「다음 주」 400 `VALIDATION_ERROR` 테스트 통과 (근거: 담당자와 기한 변경)
- [ ] 2.4 회의록 단건 응답의 `todos` 도 같은 `todo_out` 필드를 쓰는지 맞춘다. 확인: `GET /api/meetings/{id}` 의 todos 항목에 `due_date` · `is_overdue` 가 있는 테스트 통과 (근거: 기한 지남 판정)

## 3. AI - 회의 날짜 기준 기한 변환

- [ ] 3.1 `ai.PROMPT` 에 회의 날짜(`YYYY-MM-DD (요일)`)와 할 일별 `due_date` 출력을 더하고, `split(body, member_names, met_on)` 으로 받는다. `parse_split` 은 `date.fromisoformat` 이 받는 값만 남긴다. 확인: `tests/test_ai.py` 에서 프롬프트에 회의 날짜가 들어가고, `"2026-10-23"` 은 남고 「금요일」 · 빈 값 · 숫자는 빈 값이 되는 테스트 통과 (근거: 구분 결과의 할 일 담당자와 기한)
- [ ] 3.2 `POST /api/teams/{id}/meetings` 가 `met_at` 의 한국 날짜를 넘기고 결과의 `due_date` 를 저장한다. `tests/conftest.py` 의 `FakeAI.split` 시그니처를 맞춘다. 확인: 가짜 AI 가 `due_date: "2026-10-23"` 을 주면 저장된 할 일에 그 날짜가 있고, 「금요일」 을 주면 null 이며 201 인 테스트 통과, 회의 일시 UTC 2026-10-11 16:00 이 `2026-10-12` 로 넘어가는 테스트 통과 (근거: 구분 결과의 할 일 담당자와 기한)

## 4. 화면 - 서버 판정 표시와 날짜 고르기

- [ ] 4.1 `frontend/api.js` 에서 `isLate` · `LATE_WORDS` 를 지우고 기한 배지 글자 함수(`due_date` → `M월 D일`, 없으면 `due_text`, 없으면 「미정」)를 둔다. 칸반 · 상세 · 내 정보의 붉은 띠와 배지는 `t.is_overdue` 만 본다. 확인: `tests/test_frontend.py` 에 `isLate` 가 화면 파일 어디에도 없고 `is_overdue` 를 쓰는 테스트 통과 (근거: 화면 쪽 표시 규칙)
- [ ] 4.2 `todos.html` · `detail.html` 의 기한 고치기를 `<input type="date">` 로 바꿔 `{due_date}` 를 보낸다. 비우면 `null`. 퍼블리싱 클래스는 배지 그대로 쓴다. 확인: `test_frontend.py` 의 퍼블리싱 마크업 일치 테스트 통과, 로컬 서버에서 날짜를 골라 배지가 「10월 31일」 이 되고 새로고침 뒤에도 남는다 (근거: 기한 날짜 고르기)
- [ ] 4.3 README 의 칸반 · 상세 설명과 API 요약에 `due_date` · `is_overdue` 를 반영한다. 확인: README 에 두 필드와 「한국 시간 기준」 이 적혀 있다 (근거: 화면 쪽 표시 규칙)

## 5. 통합 확인

- [ ] 5.1 전체 테스트와 스펙 검사를 돌린다. 확인: `python -m pytest -q` 전부 통과, `openspec validate modify-todo-due-date` 통과
- [ ] 5.2 [사람 확인] 실제 `STT_API_KEY` 로 「다음 주 금요일」 이 든 회의록을 저장해 due_date 가 회의 날짜 기준으로 맞는지, 지난 날짜로 바꾼 카드에 붉은 띠가 생기는지 화면에서 본다. 확인: 사람이 눈으로 보고 통과라고 적는다 (근거: 구분 결과의 할 일 담당자와 기한, 화면 쪽 표시 규칙)
