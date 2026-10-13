# Spec Delta

## MODIFIED Requirements

### Requirement: 구분 결과의 할 일 담당자와 기한
<!-- 근거: D-03 · D-06 · E-09 · detail.html · todos.html --> 시스템은 AI 가 뽑은 할 일의 담당자 이름이 팀 멤버 이름과 정확히 같을 때만 그 멤버를 담당자로 넣어야 한다 (SHALL). 그 밖에는 담당자를 비워 미정으로 두고, 기한은 본문에 나온 글자 그대로 due_text 에 두며 없으면 비운다. 지어내지 않는다. 시스템은 회의 일시(met_at, 한국 시간 날짜)를 기준으로 그 기한 글자를 날짜로 바꿔 due_date 에 넣어야 한다 (SHALL). 날짜 하나로 정할 수 없거나 기한 글자가 없으면 due_date 는 null 이고, 날짜 꼴(`YYYY-MM-DD`)이 아닌 결과도 null 로 둔다.

#### Scenario: 팀에 없는 이름
- GIVEN 팀 멤버에 `최선임` 이 없다
- WHEN AI 가 담당자를 `최선임` 으로 뽑는다
- THEN 그 할 일의 assignee_id 는 null 이다

#### Scenario: 결정이 없는 회의
- GIVEN 논의만 하고 정하지 않은 본문
- WHEN 저장한다
- THEN decisions 는 빈 글자이고 decision_count 는 0 이다

#### Scenario: 상대 기한을 회의 날짜 기준으로
- GIVEN 회의 일시가 2026-10-12(월) 이고 본문에 「다음 주 금요일까지」 가 있다
- WHEN 저장한다
- THEN 그 할 일의 due_text 는 「다음 주 금요일」 이고 due_date 는 "2026-10-23" 이다

#### Scenario: 날짜로 정할 수 없는 기한
- GIVEN 본문에 「나중에 여유 될 때」 가 기한으로 나온다
- WHEN 저장한다
- THEN due_text 는 그 글자이고 due_date 는 null 이다

#### Scenario: AI 가 날짜 꼴이 아닌 값을 준다
- GIVEN AI 가 due_date 로 「금요일」 을 돌려준다
- WHEN 저장한다
- THEN 그 할 일의 due_date 는 null 이고 회의록은 201 로 저장된다
