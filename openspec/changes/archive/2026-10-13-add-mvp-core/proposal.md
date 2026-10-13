# Proposal

## Why

`docs/` 의 프로그램정의서 · 스토리보드 · 디자인시스템과 `publish/` 퍼블리싱 HTML 로 MeetingNote Pro 의 1회차 범위(기능 6종 · API 26개 · DB 7테이블 · 화면 6종 · 상태 62종)가 확정됐다. 저장소에는 아직 코드가 없다. 확정된 문서 그대로 동작하는 로컬 앱을 만들어, 팀이 회의록을 올리고 할 일을 칸반으로 추적하게 한다. 

## What Changes

- FastAPI 백엔드를 새로 만든다. `/api/` 아래 26개 경로를 스토리보드 I-01 통합매핑표대로 구현한다
- 회원가입 · 로그인(JWT 24시간 · bcrypt), 팀 생성 · 초대코드 합류(팀당 6명), 회의록 CRUD · 검색 · 녹취 업로드를 만든다
- 업로드한 녹취(mp3 · wav · 25MB 이하)는 Gemini API 로 받아쓰고, 저장할 때 같은 공급자로 요약 · 결정사항 · 할 일 세 항목을 나눈다
- 할 일 칸반(대기 · 진행 · 완료), 댓글, 활동 기록 5종을 만든다
- `publish/` 의 화면 6종을 마크업과 클래스 그대로 옮기고, 목업 데이터와 STATE 바를 걷어낸 뒤 API 에 연결한다
- FastAPI 가 화면 파일까지 함께 제공한다(로컬 일체형). DB 는 로컬 SQLite, `DATABASE_URL` 이 있으면 그 DB 를 쓴다
- Swagger UI(`/docs`)를 켠다. Authorize 에 JWT 를 넣어 인증이 필요한 API 도 화면에서 시험할 수 있게 한다
- pytest 로 API 를 검증한다. 외부 AI 호출은 가짜로 바꿔 키 없이 돈다

## Out of Scope

프로그램정의서 4절과 `docs/결정기록.md` 를 따른다.

- 실시간 녹음, 화자 자동 구분, 캘린더 · 메일 연동, 푸시 알림
- owner / member 외의 권한 등급
- 25MB 초과 파일과 분할 업로드
- Vercel + Neon 배포와, 배포 환경의 업로드 방식(Vercel 함수 요청 상한 4.5MB) - 다음 변경
- 한 사용자가 여러 팀에 속하는 것 - 퍼블리싱에 팀 전환이 없다

## Capabilities

### New Capabilities

- `user-auth`: 회원가입 · 로그인 · 토큰 검증 · 내 정보 조회와 수정 · 로그아웃
- `team-membership`: 팀 생성 · 초대코드 발급과 재발급 · 합류 · 멤버 목록 · 팀 이름 변경, owner / member 권한
- `meeting-notes`: 회의록 생성 · 목록 · 검색 · 단건 · 수정 · 삭제, 녹취 업로드와 받아쓰기, 세 항목 구분
- `todo-board`: 팀 할 일 · 내 할 일 목록, 상태 · 담당자 · 기한 변경, 삭제
- `meeting-comments`: 회의록 댓글 등록 · 목록 · 삭제
- `activity-log`: 팀 활동 · 내 활동 기록 5종
- `web-app`: 화면 6종의 공통 동작 - 토큰 보관과 세션 만료, 퍼블리싱 디자인 준수, 끌어서 옮기기, 360px 반응형
- `api-docs`: Swagger UI 로 API 를 시험하는 화면

### Modified Capabilities

없음 (첫 변경)

## Impact

- 새 코드: `backend/`(FastAPI 앱), `frontend/`(화면 6종 + `theme.js`), `tests/`(pytest)
- 의존성: FastAPI · uvicorn · SQLAlchemy · PyJWT · bcrypt · python-multipart · google-genai · python-dotenv · pytest · httpx
- 설정: `.env` 의 `JWT_SECRET` · `STT_API_KEY` · `DATABASE_URL`(선택) · `CORS_ORIGINS`. `.env` 와 `meetingnote.db` 는 git 에서 뺀다
- 외부 시스템: Gemini API (받아쓰기 · 세 항목 구분)
