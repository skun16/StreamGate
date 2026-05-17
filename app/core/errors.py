from fastapi import HTTPException, status


class StreamGateError(Exception):
    """
    StreamGate 业务异常基类。

    用于表示后端业务逻辑中的可预期错误。
    """

    def __init__(
        self,
        message: str,
        code: int = 500,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        data: dict | None = None,
    ) -> None:
        self.message = message
        self.code = code
        self.status_code = status_code
        self.data = data or {}

        super().__init__(message)

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "message": self.message,
            "data": self.data,
        }


class UnauthorizedError(StreamGateError):
    """
    未认证。
    """

    def __init__(self, message: str = "未认证，请先登录") -> None:
        super().__init__(
            message=message,
            code=401,
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


class ForbiddenError(StreamGateError):
    """
    无权限。
    """

    def __init__(self, message: str = "无权限访问该资源") -> None:
        super().__init__(
            message=message,
            code=403,
            status_code=status.HTTP_403_FORBIDDEN,
        )


class RagflowError(StreamGateError):
    """
    RAGFlow 调用异常。
    """

    def __init__(
        self,
        message: str = "RAGFlow 调用失败",
        data: dict | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=2001,
            status_code=status.HTTP_502_BAD_GATEWAY,
            data=data,
        )


def to_http_exception(error: StreamGateError) -> HTTPException:
    """
    将 StreamGateError 转成 FastAPI HTTPException。
    """

    return HTTPException(
        status_code=error.status_code,
        detail=error.to_dict(),
    )