# Spec Delta

## Purpose

회의록의 결정사항에 팀원이 의견을 단다. 쓴 사람과 owner 만 지운다.

## ADDED Requirements

### Requirement: 댓글 등록
<!-- 근거: D-09 · D-10 · detail.html --> 시스템은 팀 멤버가 `POST /api/meetings/{id}/comments` 로 1~500자 내용을 보내면 댓글을 저장하고 `comment_add` 활동을 남긴 뒤 201 과 댓글을 돌려줘야 한다 (SHALL). 비었거나 500자를 넘으면 400 이다.

#### Scenario: 댓글 등록
- GIVEN 팀 멤버와 회의록
- WHEN 「받아쓰기 실패는 구분 실패로 표시」 를 보낸다
- THEN 201 을 받고 `comment_add` 활동이 생긴다

#### Scenario: 501자
- GIVEN 팀 멤버
- WHEN 501자 댓글을 보낸다
- THEN 400 `VALIDATION_ERROR` 를 받는다

### Requirement: 댓글 목록
<!-- 근거: D-11 · D-12 · detail.html --> 시스템은 `GET /api/meetings/{id}/comments` 로 id · user_id · user_name · content · created_at · can_delete 를 created_at 오름차순으로 돌려줘야 한다 (SHALL). can_delete 는 부른 사람이 쓴 사람이거나 owner 일 때 true 다.

#### Scenario: can_delete 판정
- GIVEN member A 가 쓴 댓글
- WHEN member B 와 owner 가 각각 목록을 부른다
- THEN B 에게는 false, owner 에게는 true 로 온다

#### Scenario: 댓글 없음
- GIVEN 댓글이 없는 회의록
- WHEN 목록을 부른다
- THEN 200 과 빈 배열을 받는다

### Requirement: 댓글 삭제
<!-- 근거: D-12 · detail.html --> 시스템은 쓴 사람이나 owner 가 `DELETE /api/comments/{id}` 를 부르면 댓글을 지우고 204 를 돌려줘야 한다 (SHALL). 그 밖의 멤버는 403 `FORBIDDEN` 이다.

#### Scenario: 남의 댓글 삭제
- GIVEN member A 가 쓴 댓글
- WHEN member B 가 지운다
- THEN 403 `FORBIDDEN` 을 받는다

#### Scenario: owner 의 삭제
- GIVEN member A 가 쓴 댓글
- WHEN owner 가 지운다
- THEN 204 를 받는다
