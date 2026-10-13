# api-docs Specification

## Purpose

개발자와 검수자가 화면을 거치지 않고 브라우저에서 API 26개를 직접 불러 보며 동작을 확인한다.

## Requirements

### Requirement: Swagger UI 제공
<!-- 근거: I-01 · publish/index.html --> 시스템은 로컬 서버의 `/docs` 에 Swagger UI 를 띄우고, `/api/` 경로 26개를 기능 묶음(Auth · Team · Meeting · Todo · Comment · Activity)별로 보여야 한다 (SHALL).

#### Scenario: 26개 경로
- GIVEN 로컬 서버가 떠 있다
- WHEN `/openapi.json` 의 `/api/` 경로와 메서드 쌍을 센다
- THEN 26개다

#### Scenario: Swagger UI 화면
- GIVEN 로컬 서버가 떠 있다
- WHEN `GET /docs` 를 부른다
- THEN 200 과 Swagger UI HTML 을 받는다

### Requirement: Swagger UI 에서 인증 API 시험
<!-- 근거: B-04 · login.html --> 시스템은 Swagger UI 의 Authorize 에 로그인으로 받은 JWT 를 넣으면 인증이 필요한 API 호출에 `Authorization: Bearer` 헤더를 실어야 한다 (SHALL).

#### Scenario: 토큰 넣고 내 정보
- GIVEN Swagger UI 에서 login 을 불러 받은 토큰
- WHEN Authorize 에 토큰을 넣고 `GET /api/auth/me` 를 실행한다
- THEN 200 과 내 정보를 받는다

#### Scenario: 보안 스킴 선언
- GIVEN 로컬 서버가 떠 있다
- WHEN `/openapi.json` 의 `components.securitySchemes` 를 본다
- THEN bearer 방식 스킴이 있고 `/api/auth/me` 에 걸려 있다

### Requirement: 오류 응답 형식 문서화
<!-- 근거: B-02 · publish/login.html --> 시스템은 모든 오류 응답을 `{code, msg}` 본문으로 돌려주고, FastAPI 기본 검증 오류(422 · detail)도 400 `VALIDATION_ERROR` 로 바꿔야 한다 (SHALL).

#### Scenario: 검증 오류 형식
- GIVEN 로컬 서버
- WHEN `POST /api/auth/login` 에 빈 본문을 보낸다
- THEN 400 과 `{code: "VALIDATION_ERROR", msg}` 를 받는다
