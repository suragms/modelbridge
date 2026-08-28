from __future__ import annotations


class ModelBridgeError(Exception):
    pass


class AuthenticationError(ModelBridgeError):
    pass


class APIError(ModelBridgeError):
    def __init__(self, message: str, status_code: int | None = None, code: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
