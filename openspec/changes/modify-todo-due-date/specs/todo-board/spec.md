# Spec Delta

## MODIFIED Requirements

### Requirement: 팀 할 일 목록
<!-- 근거: E-02 · E-12 · todos.html --> 시스템은 `GET /api/teams/{id}/todos` 로 팀 회의록에 딸린 할 일마다 id · what · assignee_id · assignee_name · due_text · due_date · is_overdue · status · meeting_id · meeting_title 을 돌려줘야 한다 (SHALL). due_date 는 `YYYY-MM-DD` 문자열이거나 null 이다. 순서는 status(OPEN · DOING · DONE 순), 그다음 due_date 이른 순(null 은 뒤), 그다음 id 순이다. 완료한 할 일도 포함한다.

#### Scenario: 회의록 제목 포함
- GIVEN 회의록 「2차 스프린트」 에서 나온 할 일
- WHEN 팀 할 일 목록을 부른다
- THEN 그 항목의 meeting_title 은 「2차 스프린트」 다

#### Scenario: 정렬
- GIVEN DONE · OPEN · DOING 할 일 하나씩
- WHEN 목록을 부른다
- THEN OPEN · DOING · DONE 순으로 받는다

#### Scenario: 같은 상태 안에서 기한 순
- GIVEN OPEN 할 일 셋 - due_date 2026-10-20, null, 2026-10-15
- WHEN 목록을 부른다
- THEN 2026-10-15 · 2026-10-20 · null 순으로 받는다

#### Scenario: 할 일 없음
- GIVEN 할 일이 없는 팀
- WHEN 목록을 부른다
- THEN 200 과 빈 배열을 받는다

### Requirement: 담당자와 기한 변경
<!-- 근거: D-03 · E-06 · E-09 · detail.html · todos.html --> 시스템은 `PUT /api/todos/{id}` 로 assignee_id(팀 멤버 id 또는 null=미정), due_text, due_date(`YYYY-MM-DD` 또는 null=미정)를 바꾸게 해야 한다 (SHALL). 보내지 않은 필드는 그대로 둔다. 담당자가 사람으로 바뀌면 `todo_assign` 활동을 남기고, 팀 밖 사용자 id 와 날짜 꼴이 아닌 due_date 는 400 이다. 응답은 바뀐 할 일을 목록과 같은 필드로 돌려준다.

#### Scenario: 담당자 배정
- GIVEN 담당자 미정 할 일
- WHEN 팀 멤버 id 와 `due_text: "이번 달 안"` 을 보낸다
- THEN 200 과 assignee_name 을 받고 `todo_assign` 활동이 생긴다

#### Scenario: 미정으로 되돌림
- GIVEN 담당자가 있는 할 일
- WHEN `{assignee_id: null}` 을 보낸다
- THEN 200 을 받고 assignee_id 는 null 이다

#### Scenario: 팀 밖 사용자
- GIVEN 다른 팀 사용자의 id
- WHEN 그 id 로 담당자를 바꾼다
- THEN 400 `VALIDATION_ERROR` 를 받는다

#### Scenario: 기한 날짜 지정
- GIVEN due_date 가 null 인 할 일
- WHEN `{due_date: "2026-10-31"}` 을 보낸다
- THEN 200 을 받고 due_date 는 "2026-10-31" 이며 due_text 는 그대로다

#### Scenario: 기한 날짜 비움
- GIVEN due_date 가 있는 할 일
- WHEN `{due_date: null}` 을 보낸다
- THEN 200 을 받고 due_date 는 null, is_overdue 는 false 다

#### Scenario: 날짜 꼴이 아닌 기한
- GIVEN 할 일
- WHEN `{due_date: "다음 주"}` 를 보낸다
- THEN 400 `VALIDATION_ERROR` 를 받는다

## ADDED Requirements

### Requirement: 기한 지남 판정
<!-- 근거: E-07 · E-08 · todos.html · detail.html --> 시스템은 할 일을 돌려주는 모든 응답(팀 할 일 · 내 할 일 · 할 일 변경 · 회의록 단건의 todos)에서 is_overdue 를 직접 정해 줘야 한다 (SHALL). is_overdue 는 status 가 DONE 이 아니고 due_date 가 한국 시간(Asia/Seoul) 기준 오늘보다 앞일 때만 true 다. 기한 당일은 지난 것이 아니다. due_date 가 null 이면 due_text 가 무엇이든 false 다.

#### Scenario: 어제가 기한인 진행 중 할 일
- GIVEN 한국 시간 오늘이 2026-10-13 이고 due_date 2026-10-12 인 DOING 할 일
- WHEN 팀 할 일 목록을 부른다
- THEN 그 항목의 is_overdue 는 true 다

#### Scenario: 기한 당일
- GIVEN 한국 시간 오늘이 2026-10-13 이고 due_date 2026-10-13 인 OPEN 할 일
- WHEN 목록을 부른다
- THEN is_overdue 는 false 다

#### Scenario: 완료한 할 일
- GIVEN due_date 가 지난 DONE 할 일
- WHEN 목록을 부른다
- THEN is_overdue 는 false 다

#### Scenario: 날짜 없이 글만 있는 기한
- GIVEN due_text 「어제」, due_date null 인 OPEN 할 일
- WHEN 목록을 부른다
- THEN is_overdue 는 false 다

#### Scenario: UTC 와 한국 날짜가 다른 시각
- GIVEN UTC 2026-10-12 16:00 (한국 2026-10-13 01:00) 이고 due_date 2026-10-12 인 OPEN 할 일
- WHEN 목록을 부른다
- THEN is_overdue 는 true 다
