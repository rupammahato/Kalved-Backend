"""User endpoints minimal tests."""

import pytest


@pytest.mark.asyncio
async def test_users_me_placeholder(async_client):
    r = await async_client.get("/users/me")
    assert r.status_code == 200
    assert "msg" in r.json()
