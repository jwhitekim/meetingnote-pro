# Tasks

## 1. 뼈대

- [ ] 1.1 `requirements.txt` · `.env.example` · `.gitignore`(`.env` · `meetingnote.db` · `.venv/`) 를 만들고 `.venv` 에 설치한다. 확인: `pip install -r requirements.txt` 성공 (근거: 화면 제공 경로)
- [ ] 1.2 `backend/app/` 의 config · db · models(7테이블) · errors · main 을 만들고 `/` → `/login.html` 이동과 StaticFiles 를 건다. 확인: `uvicorn` 기동 후 `GET /` 가 `/login.html` 로 간다 (근거: 화면 제공 경로)
- [ ] 1.3 오류 핸들러로 모든 오류를 `{code, msg}` 로, 검증 오류를 400 `VALIDATION_ERROR` 로 낸다. `tests/conftest.py`(임시 SQLite · 가짜 ai · 사용자 fixture)를 만든다. 확인: `tests/test_errors.py` 통과 (근거: 오류 응답 형식 문서화)

## 2. 인증 API

- [ ] 2.1 bcrypt · JWT 발급과 검증, Swagger `HTTPBearer` 스킴을 만든다. 확인: 만료 · 없음 · 위조 토큰이 401 `TOKEN_EXPIRED` 인 테스트 통과 (근거: 토큰 검증)
- [ ] 2.2 `POST /api/auth/signup` · `POST /api/auth/login` 을 만든다. 확인: `tests/test_auth.py` 의 가입 4개 · 로그인 2개 시나리오 통과 (근거: 회원가입, 로그인)
- [ ] 2.3 `GET /api/auth/me` · `PUT /api/auth/me` · `POST /api/auth/logout` 을 만든다. 확인: 내 정보 조회 · 수정 3개 · 로그아웃 시나리오 통과 (근거: 내 정보 조회, 내 정보 수정, 로그아웃)

## 3. 팀 API

- [ ] 3.1 `activity.py`(kind 5종 · 완성 문장)를 만든다. 확인: kind 밖 값이면 예외가 나는 테스트 통과 (근거: 활동 종류는 다섯 가지)
- [ ] 3.2 `POST /api/teams` · `GET /api/teams` 를 만든다. 확인: 팀 생성 · 이미 팀 있음 · 소속 팀 없음 시나리오 통과 (근거: 팀 생성, 내 팀 목록)
- [ ] 3.3 `POST /api/teams/join` 을 만든다. 확인: 합류 성공 · 없는 코드 · 정원 초과 시나리오와 `member_join` 기록 통과 (근거: 초대코드로 합류)
- [ ] 3.4 `GET /api/teams/{id}/members` · `PUT /api/teams/{id}/code` · `PUT /api/teams/{id}` 를 만든다. 확인: todo_count · 다른 팀 403 · 재발급 후 옛 코드 404 · OWNER_ONLY 시나리오 통과 (근거: 멤버 목록, 초대코드 재발급, 팀 이름 변경)

## 4. 회의록 API

- [ ] 4.1 `ai.py` 에 OpenAI 받아쓰기와 세 항목 구분을 만든다. 확인: SDK 호출부를 가짜로 바꾼 테스트에서 JSON 결과가 summary · decisions · todos 로 풀리고, 깨진 JSON 이면 빈 결과가 나온다 (근거: 회의록 생성과 세 항목 구분, 구분 실패 시에도 저장)
- [ ] 4.2 `POST /api/teams/{id}/meetings` 를 만든다. 확인: 저장하며 구분 · 필수 항목 · 다른 팀 · 팀에 없는 이름 · 결정 없음 · AI 실패 시나리오 통과 (근거: 회의록 생성과 세 항목 구분, 구분 결과의 할 일 담당자와 기한, 구분 실패 시에도 저장)
- [ ] 4.3 `GET /api/teams/{id}/meetings` 에 집계 · 정렬 · `q` · `from`/`to` 를 만든다. 확인: body 없음 · 집계 · 빈 팀 · 참석자 검색 · 본문만 일치 · 기간 시나리오 통과 (근거: 회의록 목록, 회의록 검색과 기간)
- [ ] 4.4 `GET` · `PUT` · `DELETE /api/meetings/{id}` 를 만든다. 확인: 단건 · 없는 회의록 · 수정 · 남의 수정 · 함께 삭제 · 남의 삭제 시나리오 통과 (근거: 회의록 단건, 회의록 수정, 회의록 삭제)
- [ ] 4.5 `POST /api/upload` 에 내용 기준 형식 판정과 25MB 상한을 만든다. 확인: wav · 확장자만 mp3 · 용량 초과 · 받아쓰기 실패 시나리오 통과 (근거: 녹취 업로드와 받아쓰기)

## 5. 할 일 · 댓글 · 활동 API

- [ ] 5.1 `GET /api/teams/{id}/todos` · `GET /api/me/todos` 를 만든다. 확인: 회의록 제목 · 정렬 · 빈 목록 · 내 것만 시나리오 통과 (근거: 팀 할 일 목록, 내 할 일 목록)
- [ ] 5.2 `PUT /api/todos/{id}` · `DELETE /api/todos/{id}` 를 만든다. 확인: 완료 이동 · 되돌리기 · 없는 상태 · 배정 · 미정 · 팀 밖 사용자 · owner/member 삭제 시나리오 통과 (근거: 할 일 상태 변경, 담당자와 기한 변경, 할 일 삭제)
- [ ] 5.3 댓글 `POST` · `GET /api/meetings/{id}/comments` · `DELETE /api/comments/{id}` 를 만든다. 확인: 등록 · 501자 · can_delete · 빈 목록 · 남의 삭제 · owner 삭제 시나리오 통과 (근거: 댓글 등록, 댓글 목록, 댓글 삭제)
- [ ] 5.4 `GET /api/teams/{id}/activities` · `GET /api/me/activities` 를 만든다. 확인: 완성 문장 · 50건 상한 · 합류 직후 · 남의 활동 제외 · 내 정보 수정은 기록 안 함 시나리오 통과 (근거: 팀 활동 목록, 내 활동 목록, 활동 종류는 다섯 가지)

## 6. Swagger UI

- [ ] 6.1 라우터마다 tags 를 달고 `/docs` 를 켠다. 확인: `/openapi.json` 의 `/api/` 경로 · 메서드 쌍이 26개, bearer 스킴이 `/api/auth/me` 에 걸림, `GET /docs` 200 테스트 통과 (근거: Swagger UI 제공, Swagger UI 에서 인증 API 시험)

## 7. 화면

- [ ] 7.1 `publish/` 의 화면 6종과 `theme.js` 를 `frontend/` 로 복사하고 `api.js`(토큰 · fetch · 401 처리 · 팀 유무 분기 · 머리글)를 만든다. 확인: `diff publish/theme.js frontend/theme.js` 차이 없음 (근거: 퍼블리싱 디자인 그대로, 토큰 보관과 세션 만료)
- [ ] 7.2 `login.html` 을 가입 · 로그인 · 초대코드 합류 API 에 연결한다(목업 · STATE 바 제거). 확인: 상태 11종의 문구가 퍼블리싱과 같다 (근거: 로그인 후 팀 유무로 분기, 제출 전 입력 검사와 두 번 누름 방지)
- [ ] 7.3 `meetings.html` 을 목록 · 검색 · 기간 · 업로드 · 저장 API 에 연결한다. 확인: 업로드 후 본문 칸이 채워지고 저장 뒤 목록 맨 위에 붙는다 (근거: 회의록 목록, 녹취 업로드와 받아쓰기, 화면 쪽 표시 규칙)
- [ ] 7.4 `detail.html` 을 단건 · 수정 · 삭제 · 할 일 변경 · 댓글 API 에 연결한다. 확인: 없는 회의록이면 목록으로 간다 (근거: 회의록 단건, 회의록 수정, 회의록 삭제, 댓글 등록)
- [ ] 7.5 `todos.html` 을 할 일 API 에 연결하고 포인터 이벤트로 끌어 옮기기와 좁은 화면 칸 고르기를 만든다. 확인: 파일에 `draggable` 이 없고, 놓을 때 PUT 이 한 번만 나간다 (근거: 칸반 끌어서 옮기기, 화면 쪽 표시 규칙)
- [ ] 7.6 `team.html` · `profile.html` 을 팀 · 내 정보 · 활동 API 에 연결한다. 확인: member 로 들어가면 owner 전용 조작이 잠긴다 (근거: 팀 이름 변경, 내 정보 수정, 팀 활동 목록, 내 활동 목록)
- [ ] 7.7 화면 정적 검사 테스트를 만든다. 확인: `tests/test_frontend.py` 가 6개 화면 200 응답, `stateBar(` 없음, `draggable` 없음, `theme.js` 밖 hex 색 없음을 통과 (근거: 화면 제공 경로, 퍼블리싱 디자인 그대로)

## 8. 통합 확인

- [ ] 8.1 `pytest -q` 전체를 돌리고 결과를 보고한다. 확인: 실패 0 (근거: 전 Requirement)
- [ ] 8.2 시나리오 1(리더 가입 > 팀 생성 > 멤버 합류 > 회의록 저장 > 할 일 배정)과 시나리오 2(팀원이 완료로 이동 > 활동 기록)를 API 로 잇는 테스트를 만든다. 확인: `tests/test_flow.py` 통과, 회의록 목록 · 할 일 목록 응답이 로컬에서 100ms 이내 (근거: 회의록 생성과 세 항목 구분, 할 일 상태 변경, 팀 활동 목록)
- [ ] 8.3 [사람 확인] 실제 `STT_API_KEY` 를 넣고 서버를 띄운 뒤, 브라우저로 화면 6종을 라이트 · 다크 · 360px 폭에서 스토리보드 상태와 대조한다 - 가입 > 팀 생성 > 녹취 업로드 > 세 항목 확인 > 담당자 배정 > 칸반 이동 > 활동 기록, 그리고 `/docs` 에서 Authorize 후 `GET /api/auth/me` 가 200. 확인: 사람이 눈으로 보고 통과라고 적는다 (근거: 퍼블리싱 디자인 그대로, 360px 반응형, Swagger UI 에서 인증 API 시험)
