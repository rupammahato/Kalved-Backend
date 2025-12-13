"""Custom error definitions for API exceptions."""
from fastapi import HTTPException
from starlette import status


class Unauthorized(HTTPException):
    def __init__(self, detail: str = "Unauthorized"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


class InvalidCredentialsError(HTTPException):
    def __init__(self, detail: str = "Invalid credentials"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


class UserNotFoundError(HTTPException):
    def __init__(self, detail: str = "User not found"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class UserAlreadyExistsError(HTTPException):
    def __init__(self, detail: str = "User already exists"):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


class OTPExpiredError(HTTPException):
    def __init__(self, detail: str = "OTP expired"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class InvalidOTPError(HTTPException):
    def __init__(self, detail: str = "Invalid OTP"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class UserNotVerifiedError(HTTPException):
    def __init__(self, detail: str = "User email not verified"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)
