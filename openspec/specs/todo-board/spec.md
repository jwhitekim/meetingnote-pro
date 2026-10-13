# todo-board Specification

## Purpose

회의에서 나온 할 일을 대기 · 진행 · 완료 세 칸으로 추적하고 담당자와 기한을 붙인다.

## Requirements

### Requirement: 팀 할 일 목록
<!-- 근거: E-02 · E-12 · todos.html --> 시스템은 `GET /api/teams/{id}/todos` 로 팀 회의록에 딸린 할 일마다 id · what · assignee_id · assignee_name · due_text · status · meeting_id · meeting_title 을 status(OPEN · DOING · DONE 순) 다음 due_text 순으로 돌려줘야 한다 (SHALL). 완료한 할 일도 포함한다.

#### Scenario: 회의록 제목 포함
- GIVEN 회의록 「2차 스프린트」 에서 나온 할 일
- WHEN 팀 할 일 목록을 부른다
- THEN 그 항목의 meeting_title 은 「2차 스프린트」 다

#### Scenario: 정렬
- GIVEN DONE · OPEN · DOING 할 일 하나씩
- WHEN 목록을 부른다
- THEN OPEN · DOING · DONE 순으로 받는다

#### Scenario: 할 일 없음
- GIVEN 할 일이 없는 팀
- WHEN 목록을 부른다
- THEN 200 과 빈 배열을 받는다

### Requirement: 내 할 일 목록
<!-- 근거: E-01 · J-01 · todos.html · profile.html --> 시스템은 `GET /api/me/todos` 로 로그인한 사용자가 담당인 할 일만 팀 할 일 목록과 같은 필드와 순서로 돌려줘야 한다 (SHALL).

#### Scenario: 내 것만
- GIVEN 나에게 2건, 다른 멤버에게 1건 배정된 팀
- WHEN 내 할 일을 부른다
- THEN 2건만 받는다

### Requirement: 할 일 상태 변경
<!-- 근거: D-04 · E-04 · E-05 · E-10 · detail.html · todos.html --> 시스템은 팀 멤버가 `PUT /api/todos/{id}` 로 status 를 OPEN · DOING · DONE 중 하나로 바꾸게 해야 한다 (SHALL). 되돌리기도 허용하고, DONE 으로 바뀌는 순간 `todo_done` 활동을 남긴다. 그 밖의 값은 400 이다.

#### Scenario: 완료로 이동
- GIVEN DOING 상태 할 일
- WHEN `{status: "DONE"}` 을 보낸다
- THEN 200 을 받고 `todo_done` 활동이 하나 생긴다

#### Scenario: 되돌리기
- GIVEN DONE 상태 할 일
- WHEN `{status: "OPEN"}` 을 보낸다
- THEN 200 을 받고 status 는 OPEN 이다

#### Scenario: 없는 상태 값
- GIVEN 할 일
- WHEN `{status: "LATER"}` 를 보낸다
- THEN 400 `VALIDATION_ERROR` 를 받는다

### Requirement: 담당자와 기한 변경
<!-- 근거: D-03 · E-06 · E-09 · detail.html · todos.html --> 시스템은 `PUT /api/todos/{id}` 로 assignee_id(팀 멤버 id 또는 null=미정)와 due_text 를 바꾸게 해야 한다 (SHALL). 담당자가 사람으로 바뀌면 `todo_assign` 활동을 남기고, 팀 밖 사용자 id 는 400 이다.

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

### Requirement: 할 일 삭제
<!-- 근거: E-11 · F-08 · todos.html --> 시스템은 owner 만 `DELETE /api/todos/{id}` 로 할 일을 지우게 하고 204 를 돌려줘야 한다 (SHALL). member 가 부르면 403 `OWNER_ONLY` 다.

#### Scenario: owner 의 삭제
- GIVEN owner 인 사용자
- WHEN 할 일을 지운다
- THEN 204 를 받고 목록에서 사라진다

#### Scenario: member 의 삭제
- GIVEN member 인 사용자
- WHEN 할 일을 지운다
- THEN 403 `OWNER_ONLY` 를 받는다
