# Spec Delta

## Purpose

팀을 만들고 초대코드 하나로 멤버를 모은다. 사용자는 팀 하나에만 속하고, 권한은 owner 와 member 둘뿐이다.

## ADDED Requirements

### Requirement: 팀 생성
<!-- 근거: F-02 · team.html --> 시스템은 소속 팀이 없는 사용자가 `POST /api/teams` 로 팀 이름을 보내면 팀을 만들고, 그 사용자를 owner 로 넣고, `MN-` 뒤에 대문자와 숫자 4자를 붙인 초대코드를 발급해야 한다 (SHALL).

#### Scenario: 팀 생성
- GIVEN 소속 팀이 없는 사용자
- WHEN `{name: "기획팀"}` 으로 팀을 만든다
- THEN 201 과 id · name · invite_code(`^MN-[A-Z0-9]{4}$`) · role `owner` 를 받는다

#### Scenario: 이미 팀이 있음
- GIVEN 팀에 속한 사용자
- WHEN 팀을 하나 더 만든다
- THEN 400 `VALIDATION_ERROR` 를 받는다

### Requirement: 내 팀 목록
<!-- 근거: F-01 · F-02 · team.html --> 시스템은 `GET /api/teams` 로 사용자가 속한 팀을 0건 또는 1건의 배열로 돌려줘야 한다 (SHALL). 각 항목은 id · name · invite_code · role · member_count 를 담는다.

#### Scenario: 소속 팀 없음
- GIVEN 가입만 하고 팀이 없는 사용자
- WHEN `GET /api/teams` 를 부른다
- THEN 200 과 빈 배열을 받는다

### Requirement: 초대코드로 합류
<!-- 근거: B-11 · F-03 · F-06 · login.html · team.html --> 시스템은 `POST /api/teams/join` 으로 초대코드를 받아 사용자를 member 로 넣고 `member_join` 활동을 남겨야 한다 (SHALL). 코드가 없으면 404, 팀이 6명이면 409 를 돌려주고, 두 경우 모두 계정은 그대로 둔다.

#### Scenario: 합류 성공
- GIVEN 3명인 팀의 초대코드 `MN-7K2D` 와 소속 팀이 없는 사용자
- WHEN 그 코드로 합류한다
- THEN 200 과 팀 정보를 받고 멤버가 4명이 된다

#### Scenario: 없는 초대코드
- GIVEN 소속 팀이 없는 사용자
- WHEN `MN-0000` 으로 합류한다
- THEN 404 `INVITE_NOT_FOUND` 를 받고 계정은 그대로 로그인된다

#### Scenario: 정원 초과
- GIVEN 6명인 팀의 초대코드
- WHEN 7번째 사용자가 합류한다
- THEN 409 `TEAM_FULL` 을 받는다

### Requirement: 멤버 목록
<!-- 근거: F-01 · team.html --> 시스템은 `GET /api/teams/{id}/members` 로 팀 멤버마다 id · name · email · role · todo_count 를 돌려줘야 한다 (SHALL). todo_count 는 그 사람이 담당인 할 일 수다. 팀 멤버가 아니면 403 이다.

#### Scenario: 멤버별 할 일 수
- GIVEN 김대리에게 할 일 2건이 배정된 팀
- WHEN 멤버 목록을 부른다
- THEN 김대리 항목의 todo_count 는 2 다

#### Scenario: 다른 팀 사용자
- GIVEN 다른 팀 소속 사용자
- WHEN 이 팀의 멤버 목록을 부른다
- THEN 403 `FORBIDDEN` 을 받는다

### Requirement: 초대코드 재발급
<!-- 근거: F-05 · F-08 · team.html --> 시스템은 owner 가 `PUT /api/teams/{id}/code` 를 부르면 새 초대코드를 발급하고 앞의 코드는 폐기해야 한다 (SHALL). 이미 합류한 멤버는 그대로 둔다. member 가 부르면 403 `OWNER_ONLY` 다.

#### Scenario: 재발급 후 옛 코드
- GIVEN owner 가 코드를 재발급했다
- WHEN 옛 코드로 합류한다
- THEN 404 `INVITE_NOT_FOUND` 를 받고, 새 코드로는 합류된다

#### Scenario: member 의 재발급
- GIVEN member 인 사용자
- WHEN 재발급을 부른다
- THEN 403 `OWNER_ONLY` 를 받는다

### Requirement: 팀 이름 변경
<!-- 근거: F-07 · F-08 · team.html --> 시스템은 owner 가 `PUT /api/teams/{id}` 로 보낸 이름으로 팀 이름을 바꿔야 한다 (SHALL). member 가 부르면 403 `OWNER_ONLY` 다.

#### Scenario: owner 의 이름 변경
- GIVEN owner 인 사용자
- WHEN `{name: "제품팀"}` 을 보낸다
- THEN 200 과 바뀐 이름을 받는다

#### Scenario: member 의 이름 변경
- GIVEN member 인 사용자
- WHEN 팀 이름을 바꾼다
- THEN 403 `OWNER_ONLY` 를 받고 이름은 그대로다
