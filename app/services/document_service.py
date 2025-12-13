class DocumentService:
    async def upload(self, user_id: str, file_obj) -> dict:
        return {"status": "uploaded"}

    async def verify(self, document_id: str) -> dict:
        return {"status": "verified"}
