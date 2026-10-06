# Spec Delta

## Purpose

팀이 회의록을 올리고 찾는다. 녹취 파일을 받아쓰고, 저장할 때 본문을 요약 · 결정사항 · 할 일 세 항목으로 나눈다.

## ADDED Requirements

### Requirement: 회의록 생성과 세 항목 구분
<!-- 근거: C-05 · C-10 · C-11 · meetings.html --> 시스템은 팀 멤버가 `POST /api/teams/{id}/meetings` 로 제목 · 회의 시각 · 참석자 · 본문을 보내면, 본문을 AI 로 요약 · 결정사항 · 할 일로 나눠 함께 저장하고 201 과 저장된 회의록을 돌려줘야 한다 (SHALL). 제목 · 회의 시각 · 본문은 필수다.

#### Scenario: 저장하며 세 항목 구분
- GIVEN 팀 멤버와, 할 일 2건과 결정 1건이 담긴 본문
- WHEN 회의록을 저장한다
- THEN 201 과 summary · decisions 를 받고, 그 회의록에 OPEN 상태 할 일 2건이 생기고, `meeting_add` 활동이 남는다

#### Scenario: 필수 항목 빠짐
- GIVEN 팀 멤버
- WHEN 본문 없이 저장한다
- THEN 400 `VALIDATION_ERROR` 를 받고 아무것도 저장되지 않는다

#### Scenario: 다른 팀에 저장
- GIVEN 다른 팀 소속 사용자
- WHEN 이 팀에 회의록을 저장한다
- THEN 403 `FORBIDDEN` 을 받는다

### Requirement: 구분 결과의 할 일 담당자와 기한
<!-- 근거: D-03 · D-06 · E-09 · detail.html · todos.html --> 시스템은 AI 가 뽑은 할 일의 담당자 이름이 팀 멤버 이름과 정확히 같을 때만 그 멤버를 담당자로 넣어야 한다 (SHALL). 그 밖에는 담당자를 비워 미정으로 두고, 기한은 본문에 나온 글자 그대로 두며 없으면 비운다. 지어내지 않는다.

#### Scenario: 팀에 없는 이름
- GIVEN 팀 멤버에 `최선임` 이 없다
- WHEN AI 가 담당자를 `최선임` 으로 뽑는다
- THEN 그 할 일의 assignee_id 는 null 이다

#### Scenario: 결정이 없는 회의
- GIVEN 논의만 하고 정하지 않은 본문
- WHEN 저장한다
- THEN decisions 는 빈 글자이고 decision_count 는 0 이다

### Requirement: 구분 실패 시에도 저장
<!-- 근거: C-10 · meetings.html --> 시스템은 AI 호출이 실패하거나 키가 없으면 회의록을 본문과 함께 저장하고 summary · decisions 를 비우고 할 일은 만들지 않아야 한다 (SHALL). 사용자가 쓴 본문을 잃지 않는다.

#### Scenario: AI 실패
- GIVEN AI 호출이 오류를 낸다
- WHEN 회의록을 저장한다
- THEN 201 을 받고 body 는 저장되며 summary 는 빈 글자, 할 일은 0건이다

### Requirement: 회의록 목록
<!-- 근거: C-01 · C-02 · meetings.html --> 시스템은 `GET /api/teams/{id}/meetings` 로 id · title · met_at · attendees · summary · created_at · todo_done_count · todo_total_count · decision_count 를 met_at 내림차순으로 돌려줘야 한다 (SHALL). body 는 싣지 않는다.

#### Scenario: 목록에 body 없음
- GIVEN 회의록 2건이 있는 팀
- WHEN 목록을 부른다
- THEN 두 항목 모두 body 키가 없고, met_at 이 늦은 것이 먼저 온다

#### Scenario: 집계 값
- GIVEN 할 일 3건 중 1건이 DONE 이고 결정사항이 빈 줄을 빼고 2줄인 회의록
- WHEN 목록을 부른다
- THEN todo_done_count 1 · todo_total_count 3 · decision_count 2 를 받는다

#### Scenario: 빈 팀
- GIVEN 회의록이 없는 팀
- WHEN 목록을 부른다
- THEN 200 과 빈 배열을 받는다

### Requirement: 회의록 검색과 기간
<!-- 근거: C-03 · C-04 · meetings.html --> 시스템은 `?q=` 를 제목과 참석자에만 부분 일치로 적용하고, `?from=&to=`(ISO 날짜)를 met_at 에 양 끝 포함으로 적용해야 한다 (SHALL). 본문은 검색하지 않고, 결과가 없으면 200 과 빈 배열이다.

#### Scenario: 참석자 검색
- GIVEN 참석자에 `박과장` 이 있는 회의록과 없는 회의록
- WHEN `?q=박과장` 으로 부른다
- THEN 있는 회의록만 받는다

#### Scenario: 본문만 일치
- GIVEN 본문에만 `인터뷰` 가 들어간 회의록
- WHEN `?q=인터뷰` 로 부른다
- THEN 200 과 빈 배열을 받는다

#### Scenario: 기간
- GIVEN met_at 이 9월 10일과 9월 24일인 회의록
- WHEN `?from=2026-09-20&to=2026-09-30` 으로 부른다
- THEN 9월 24일 회의록만 받는다

### Requirement: 회의록 단건
<!-- 근거: D-01 · D-07 · D-13 · detail.html --> 시스템은 `GET /api/meetings/{id}` 로 목록 필드에 body · decisions · author_id · author_name 과 그 회의록의 할 일 배열을 더해 돌려줘야 한다 (SHALL). 없는 회의록은 404 `MEETING_NOT_FOUND`, 다른 팀 회의록은 403 이다.

#### Scenario: 단건에 body 와 할 일
- GIVEN 할 일 3건이 있는 회의록
- WHEN 단건을 부른다
- THEN body 와 todos 3건을 받는다

#### Scenario: 없는 회의록
- GIVEN 팀 멤버
- WHEN `GET /api/meetings/9999` 를 부른다
- THEN 404 `MEETING_NOT_FOUND` 를 받는다

### Requirement: 회의록 수정
<!-- 근거: D-02 · detail.html --> 시스템은 쓴 사람이나 owner 가 `PUT /api/meetings/{id}` 로 보낸 제목 · 회의 시각 · 참석자 · 본문만 바꿔야 한다 (SHALL). 세 항목을 다시 구분하지 않는다. 그 밖의 멤버는 403 `FORBIDDEN` 이다.

#### Scenario: 제목 수정
- GIVEN 회의록을 쓴 사람
- WHEN `{title: "3차 스프린트"}` 를 보낸다
- THEN 200 과 바뀐 제목을 받고 summary 와 할 일은 그대로다

#### Scenario: 남의 회의록 수정
- GIVEN 쓴 사람도 owner 도 아닌 member
- WHEN 수정을 보낸다
- THEN 403 `FORBIDDEN` 을 받는다

### Requirement: 회의록 삭제
<!-- 근거: D-08 · detail.html --> 시스템은 쓴 사람이나 owner 가 `DELETE /api/meetings/{id}` 를 부르면 그 회의록과 딸린 할 일 · 댓글을 함께 지우고 204 를 돌려줘야 한다 (SHALL). 활동 기록은 지우지 않는다.

#### Scenario: 딸린 할 일 함께 삭제
- GIVEN 할 일 3건과 댓글 1건이 있는 회의록
- WHEN 쓴 사람이 삭제한다
- THEN 204 를 받고 그 할 일과 댓글은 팀 목록에서 사라진다

#### Scenario: 남의 회의록 삭제
- GIVEN 쓴 사람도 owner 도 아닌 member
- WHEN 삭제를 부른다
- THEN 403 `FORBIDDEN` 을 받는다

### Requirement: 녹취 업로드와 받아쓰기
<!-- 근거: C-06 · C-07 · C-08 · C-09 · meetings.html --> 시스템은 `POST /api/upload` 로 받은 파일이 내용 기준 mp3 나 wav 이고 25MB 이하이면 받아쓴 본문 글자를 돌려줘야 한다 (SHALL). 저장은 하지 않는다. 형식이 다르면 415, 크면 413 이다.

#### Scenario: wav 받아쓰기
- GIVEN 4MB wav 파일
- WHEN 업로드한다
- THEN 200 과 `{text}` 를 받고 회의록은 생기지 않는다

#### Scenario: 확장자만 mp3
- GIVEN 이름은 `a.mp3` 이지만 내용은 mp4 인 파일
- WHEN 업로드한다
- THEN 415 `UNSUPPORTED_MEDIA_TYPE` 를 받는다

#### Scenario: 용량 초과
- GIVEN 25MB 를 넘는 wav 파일
- WHEN 업로드한다
- THEN 413 `PAYLOAD_TOO_LARGE` 를 받는다

#### Scenario: 받아쓰기 실패
- GIVEN AI 받아쓰기가 오류를 내거나 60초를 넘긴다
- WHEN 업로드한다
- THEN 502 `TRANSCRIBE_FAILED` 를 받는다
