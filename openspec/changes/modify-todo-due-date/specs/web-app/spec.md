# Spec Delta

## MODIFIED Requirements

### Requirement: 화면 쪽 표시 규칙
<!-- 근거: E-07 · E-08 · C-01 · F-01 · todos.html · meetings.html · team.html --> 시스템은 담당자 필터를 서버를 다시 부르지 않고 화면에서 거르고, 서버가 is_overdue 를 true 로 준 할 일에만 붉은 띠와 붉은 기한 배지를 그려야 한다 (SHALL). 화면은 기한 글자를 읽어 지남 여부를 따로 추측하지 않는다. 기한 배지는 due_date 가 있으면 그 날짜(`M월 D일`)를, 없으면 due_text 를, 둘 다 없으면 「미정」 을 보인다. 회의록 카드 띠는 목록 순서대로 blue · green · orange · purple · red 를 돌려 쓰고, 활동 띠는 kind 로 고른다.

#### Scenario: 활동 띠 색
- GIVEN `todo_done` 활동
- WHEN 팀 설정 화면이 활동을 그린다
- THEN 그 항목의 띠는 green 이다

#### Scenario: 서버 판정만 따른다
- GIVEN due_text 가 「어제」 이고 is_overdue 가 false 인 할 일
- WHEN 칸반이 카드를 그린다
- THEN 그 카드에는 붉은 띠가 없다

#### Scenario: 지난 기한
- GIVEN is_overdue 가 true 인 할 일
- WHEN 칸반이 카드를 그린다
- THEN 그 카드에 붉은 띠가 있고 기한 배지가 붉다

## ADDED Requirements

### Requirement: 기한 날짜 고르기
<!-- 근거: D-03 · E-09 · detail.html · todos.html --> 시스템은 칸반과 회의록 상세에서 기한 배지를 누르면 날짜 고르기 칸을 열고, 고른 날짜를 `PUT /api/todos/{id}` 의 due_date 로 저장해야 한다 (SHALL). 날짜를 지우면 due_date 를 null 로 보낸다. 저장한 뒤에는 서버가 돌려준 is_overdue 로 다시 그린다.

#### Scenario: 날짜 골라 저장
- GIVEN 칸반의 할 일 카드
- WHEN 기한 배지를 누르고 2026-10-31 을 고른다
- THEN `PUT /api/todos/{id}` 에 `{due_date: "2026-10-31"}` 이 가고, 배지는 「10월 31일」 이 된다

#### Scenario: 날짜 지우기
- GIVEN due_date 가 있는 할 일
- WHEN 날짜 고르기 칸을 비우고 닫는다
- THEN `{due_date: null}` 이 가고 배지는 due_text 나 「미정」 을 보인다
