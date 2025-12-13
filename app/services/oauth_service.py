class OAuthService:
    async def verify_google_token(self, token: str) -> dict:
        return {"email": None}
