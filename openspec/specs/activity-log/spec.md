# activity-log Specification

## Purpose

팀에서 누가 언제 무엇을 했는지 남겨, 리더와 신규 합류자가 팀 흐름을 한 화면에서 본다.

## Requirements

### Requirement: 활동 종류는 다섯 가지
<!-- 근거: F-01 · J-06 · team.html · profile.html --> 시스템은 활동 kind 로 `meeting_add` · `todo_assign` · `todo_done` · `comment_add` · `member_join` 다섯 값만 남겨야 한다 (SHALL). 내 정보 수정 · 회의록 수정과 삭제 · 댓글 삭제 · 팀 이름 변경 · 코드 재발급은 남기지 않는다.

#### Scenario: 내 정보 수정은 기록 안 함
- GIVEN 활동이 0건인 팀의 사용자
- WHEN 이름을 바꾼다
- THEN 팀 활동은 여전히 0건이다

### Requirement: 팀 활동 목록
<!-- 근거: F-01 · team.html --> 시스템은 `GET /api/teams/{id}/activities` 로 최근 50건을 created_at 내림차순으로, 각 항목에 id · kind · actor_name · text · created_at 을 담아 돌려줘야 한다 (SHALL). text 는 서버가 만든 완성 문장이다. 팀 멤버가 아니면 403 이다.

#### Scenario: 완성 문장
- GIVEN 김대리가 회의록 「2차 스프린트」 를 올렸다
- WHEN 팀 활동을 부른다
- THEN kind `meeting_add` 항목의 text 에 「김대리」 와 「2차 스프린트」 가 들어 있다

#### Scenario: 50건 상한
- GIVEN 활동이 60건인 팀
- WHEN 팀 활동을 부른다
- THEN 가장 최근 50건만 최근순으로 받는다

### Requirement: 내 활동 목록
<!-- 근거: J-01 · J-07 · profile.html --> 시스템은 `GET /api/me/activities` 로 로그인한 사용자가 행위자인 활동만 팀 활동 목록과 같은 필드 · 순서 · 상한으로 돌려줘야 한다 (SHALL).

#### Scenario: 합류 직후
- GIVEN 방금 팀을 만들어 활동이 없는 owner
- WHEN 내 활동을 부른다
- THEN 200 과 빈 배열을 받는다

#### Scenario: 남의 활동 제외
- GIVEN 나의 댓글 1건과 다른 멤버의 댓글 1건
- WHEN 내 활동을 부른다
- THEN `comment_add` 1건만 받는다
