"""모든 오류를 {code, msg} 로 낸다."""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class ApiError(Exception):
    def __init__(self, status: int, code: str, msg: str):
        self.status, self.code, self.msg = status, code, msg


def _body(status: int, code: str, msg: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"code": code, "msg": msg})


_HTTP_CODES = {401: "TOKEN_EXPIRED", 403: "FORBIDDEN", 404: "NOT_FOUND", 405: "NOT_FOUND"}


def install(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api(_: Request, e: ApiError):
        return _body(e.status, e.code, e.msg)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, e: RequestValidationError):
        first = e.errors()[0] if e.errors() else {}
        where = ".".join(str(p) for p in first.get("loc", []) if p != "body")
        return _body(400, "VALIDATION_ERROR", f"입력값을 확인해 주세요 ({where})" if where else "입력값을 확인해 주세요")

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, e: StarletteHTTPException):
        return _body(e.status_code, _HTTP_CODES.get(e.status_code, "VALIDATION_ERROR"), str(e.detail))
