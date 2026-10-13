# web-app Specification

## Purpose

화면 6종이 퍼블리싱 디자인 그대로 보이고, 같은 서버에서 API 와 함께 제공되며, 로그인 상태와 오류를 한 가지 방식으로 다룬다.

## Requirements

### Requirement: 화면 제공 경로
<!-- 근거: H-01 · I-01 · publish/index.html --> 시스템은 API 와 같은 서버에서 `/login.html` · `/meetings.html` · `/detail.html` · `/todos.html` · `/team.html` · `/profile.html` 과 `/theme.js` 를 제공하고, `/` 는 `/login.html` 로 보내야 한다 (SHALL).

#### Scenario: 화면 파일
- GIVEN 로컬 서버가 떠 있다
- WHEN `GET /todos.html` 을 부른다
- THEN 200 과 HTML 을 받는다

#### Scenario: 루트
- GIVEN 로컬 서버가 떠 있다
- WHEN `GET /` 를 부른다
- THEN `/login.html` 로 이동한다

### Requirement: 퍼블리싱 디자인 그대로
<!-- 근거: G-01 · publish/*.html · publish/theme.js --> 시스템은 화면 6종의 마크업 구조와 클래스 문자열을 `publish/` 의 같은 이름 파일과 같게 두고, `theme.js` 의 색과 규격만 써야 한다 (SHALL). STATE 바와 목업 데이터는 넣지 않고, 데이터는 API 응답으로 채운다.

#### Scenario: STATE 바 없음
- GIVEN 구현된 화면 6종
- WHEN 각 파일에서 `stateBar` 호출을 찾는다
- THEN 한 곳도 없다

#### Scenario: 새 색 없음
- GIVEN 구현된 화면 6종
- WHEN `theme.js` 에 없는 색 값(`#` 으로 시작하는 hex 나 tailwind 기본 팔레트 색)을 찾는다
- THEN 한 곳도 없다

### Requirement: 토큰 보관과 세션 만료
<!-- 근거: B-03 · B-04 · login.html --> 시스템은 로그인 · 가입으로 받은 JWT 를 localStorage 에 두고 모든 API 호출에 싣고, 어느 화면에서든 401 `TOKEN_EXPIRED` 를 받으면 토큰을 지우고 「세션이 만료되었습니다」 를 띄운 로그인 화면으로 보내야 한다 (SHALL).

#### Scenario: 만료 후 이동
- GIVEN localStorage 에 만료된 토큰
- WHEN `/meetings.html` 을 연다
- THEN 토큰이 지워지고 로그인 화면에 세션 만료 문구가 보인다

### Requirement: 로그인 후 팀 유무로 분기
<!-- 근거: B-04 · B-11 · F-02 · login.html · team.html --> 시스템은 로그인이나 가입 뒤 소속 팀이 없으면 팀 설정 화면의 팀 만들기 · 합류 상태로, 있으면 회의록 목록으로 보내야 한다 (SHALL). 가입 때 넣은 초대코드가 틀리면 계정은 유지한 채 팀 설정 화면에 그 오류를 띄운다. 소속 팀이 없으면 다른 화면으로 넘어가지 못한다.

#### Scenario: 틀린 초대코드로 가입
- GIVEN 회원가입 화면에 없는 초대코드를 넣었다
- WHEN 가입한다
- THEN 로그인된 채 팀 설정 화면으로 가고 「없는 초대코드」 알림이 보인다

### Requirement: 제출 전 입력 검사와 두 번 누름 방지
<!-- 근거: B-06 · B-07 · B-08 · B-10 · J-03 · J-05 · login.html · profile.html --> 시스템은 이메일 형식 · 비밀번호 8자 · 비밀번호 확인 일치를 제출할 때 화면에서 먼저 검사하고, 요청이 끝날 때까지 제출 버튼을 잠가야 한다 (SHALL). 입력하는 동안에는 오류를 띄우지 않는다.

#### Scenario: 비밀번호 확인 불일치
- GIVEN 내 정보 화면에서 두 비밀번호를 다르게 넣었다
- WHEN 저장을 누른다
- THEN 「두 비밀번호가 다름」 이 보이고 서버로 요청이 가지 않는다

### Requirement: 칸반 끌어서 옮기기
<!-- 근거: E-03 · E-04 · E-05 · todos.html --> 시스템은 칸반 카드를 포인터 이벤트로 끌어 옮기고, 놓는 순간 상태 변경 API 를 한 번만 부르며, 실패하면 카드를 원래 칸으로 되돌려야 한다 (SHALL). HTML5 draggable 은 쓰지 않고, 좁은 화면에서는 카드를 눌러 대기 · 진행 · 완료 중 칸을 고른다.

#### Scenario: 놓을 때 한 번 호출
- GIVEN 대기 칸의 카드
- WHEN 완료 칸으로 끌어 놓는다
- THEN `PUT /api/todos/{id}` 가 한 번만 불린다

#### Scenario: 실패 시 복귀
- GIVEN 서버가 오류를 돌려준다
- WHEN 카드를 다른 칸에 놓는다
- THEN 카드가 원래 칸으로 돌아간다

### Requirement: 화면 쪽 표시 규칙
<!-- 근거: E-07 · E-08 · C-01 · F-01 · todos.html · meetings.html · team.html --> 시스템은 담당자 필터를 서버를 다시 부르지 않고 화면에서 거르고, 완료가 아닌 할 일 중 기한이 지난 것에 붉은 띠를 그려야 한다 (SHALL). 회의록 카드 띠는 목록 순서대로 blue · green · orange · purple · red 를 돌려 쓰고, 활동 띠는 kind 로 고른다.

#### Scenario: 활동 띠 색
- GIVEN `todo_done` 활동
- WHEN 팀 설정 화면이 활동을 그린다
- THEN 그 항목의 띠는 green 이다

### Requirement: 360px 반응형
<!-- 근거: N-01 · meetings.html · detail.html · todos.html --> 시스템은 화면 폭 360px 에서 가로 스크롤 없이, 회의록 카드는 한 열로, 상세 세 항목과 칸반 칸은 세로로 쌓아 보여야 한다 (SHALL).

#### Scenario: 좁은 화면
- GIVEN 브라우저 폭 360px
- WHEN 화면 6종을 차례로 연다
- THEN 어느 화면에도 가로 스크롤이 생기지 않고 글자가 잘리지 않는다
