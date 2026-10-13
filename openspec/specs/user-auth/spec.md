# user-auth Specification

## Purpose

이메일과 비밀번호로 계정을 만들고 로그인해, 팀 회의록 기능을 쓸 토큰을 받는다. 내 이름과 비밀번호를 고친다.

## Requirements

### Requirement: 회원가입
<!-- 근거: B-05 · B-08 · B-09 · B-10 · login.html --> 시스템은 `POST /api/auth/signup` 으로 이메일 · 비밀번호 · 이름을 받아 계정을 만들고, 201 과 함께 JWT 와 사용자 정보를 돌려줘야 한다 (SHALL). 비밀번호는 bcrypt 해시로만 저장한다.

#### Scenario: 정상 가입
- GIVEN 가입된 적 없는 이메일 `kim@example.com`
- WHEN 비밀번호 8자 이상과 이름으로 가입을 요청한다
- THEN 201 과 `token` · `user`(id · name · email · role) 를 받고, DB 의 password_hash 는 평문과 다르다

#### Scenario: 이메일 형식 오류
- GIVEN 가입 화면
- WHEN 이메일을 `kim-at-example` 로 보낸다
- THEN 400 `{code: "EMAIL_INVALID", msg}` 를 받는다

#### Scenario: 중복 이메일
- GIVEN `kim@example.com` 으로 가입된 계정이 있다
- WHEN 같은 이메일로 다시 가입을 요청한다
- THEN 409 `EMAIL_DUPLICATED` 를 받는다

#### Scenario: 약한 비밀번호
- GIVEN 가입 화면
- WHEN 7자 비밀번호로 가입을 요청한다
- THEN 400 `PASSWORD_TOO_WEAK` 를 받고 계정은 만들어지지 않는다

### Requirement: 로그인
<!-- 근거: B-01 · B-02 · B-04 · login.html --> 시스템은 `POST /api/auth/login` 이 맞는 이메일과 비밀번호를 받으면 200 과 24시간 유효한 JWT 를 돌려줘야 한다 (SHALL). 틀리면 이메일 존재 여부를 드러내지 않는 한 가지 오류를 돌려준다.

#### Scenario: 로그인 성공
- GIVEN 가입된 계정
- WHEN 맞는 이메일과 비밀번호로 로그인한다
- THEN 200 과 `token` 을 받고, 토큰의 만료 시각은 발급 후 24시간이다

#### Scenario: 없는 이메일과 틀린 비밀번호가 같은 응답
- GIVEN 가입된 계정 하나
- WHEN 없는 이메일로 한 번, 틀린 비밀번호로 한 번 로그인한다
- THEN 두 번 모두 401 `INVALID_CREDENTIALS` 와 같은 msg 를 받는다

### Requirement: 토큰 검증
<!-- 근거: B-03 · login.html --> 시스템은 `/api/auth/signup` · `/api/auth/login` 을 뺀 모든 API 에서 `Authorization: Bearer <JWT>` 를 검사하고, 토큰이 없거나 만료되거나 위조됐으면 401 `TOKEN_EXPIRED` 를 돌려줘야 한다 (SHALL). 토큰 갱신은 없다.

#### Scenario: 만료된 토큰
- GIVEN 발급 후 24시간이 지난 토큰
- WHEN `GET /api/auth/me` 를 부른다
- THEN 401 `TOKEN_EXPIRED` 를 받는다

#### Scenario: 토큰 없음
- GIVEN 로그인하지 않은 상태
- WHEN `GET /api/teams` 를 부른다
- THEN 401 `TOKEN_EXPIRED` 를 받는다

### Requirement: 내 정보 조회
<!-- 근거: J-01 · profile.html --> 시스템은 `GET /api/auth/me` 로 id · name · email 과 소속 팀에서의 role 을 돌려줘야 한다 (SHALL). 소속 팀이 없으면 role 은 null 이다.

#### Scenario: owner 의 내 정보
- GIVEN 팀을 만든 사용자
- WHEN `GET /api/auth/me` 를 부른다
- THEN 200 과 `role: "owner"` 를 받는다

### Requirement: 내 정보 수정
<!-- 근거: J-02 · J-04 · J-06 · profile.html --> 시스템은 `PUT /api/auth/me` 로 이름과 새 비밀번호를 받아 보낸 값만 바꿔야 한다 (SHALL). 이메일은 바꾸지 않고, 이 변경은 활동 기록에 남기지 않는다.

#### Scenario: 이름만 변경
- GIVEN 로그인한 사용자
- WHEN `{name: "김수석"}` 만 보낸다
- THEN 200 과 바뀐 이름을 받고, 이전 비밀번호로 계속 로그인된다

#### Scenario: 약한 새 비밀번호
- GIVEN 로그인한 사용자
- WHEN 새 비밀번호를 7자로 보낸다
- THEN 400 `PASSWORD_TOO_WEAK` 를 받고 비밀번호는 그대로다

#### Scenario: 이메일은 바뀌지 않음
- GIVEN 로그인한 사용자
- WHEN `{email: "new@example.com", name: "김수석"}` 을 보낸다
- THEN 이름만 바뀌고 email 은 그대로다

### Requirement: 로그아웃
<!-- 근거: B-03 · meetings.html --> 시스템은 `POST /api/auth/logout` 에 200 만 돌려줘야 한다 (SHALL). 서버는 토큰 블랙리스트를 두지 않고, 화면이 토큰을 지운다.

#### Scenario: 로그아웃
- GIVEN 로그인한 사용자
- WHEN `POST /api/auth/logout` 을 부른다
- THEN 200 을 받는다
