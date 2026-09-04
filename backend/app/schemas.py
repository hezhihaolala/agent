from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class AuthResponse(BaseModel):
    username: str
    csrf_token: str
