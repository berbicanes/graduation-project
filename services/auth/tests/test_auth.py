import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


USER_DATA = {
    "email": "test@example.com",
    "password": "securepass123",
    "full_name": "Test User",
    "role": "patient",
}


async def register_user(client: AsyncClient, data: dict | None = None) -> dict:
    response = await client.post("/auth/register", json=data or USER_DATA)
    return response.json()


async def login_user(
    client: AsyncClient, email: str = USER_DATA["email"], password: str = USER_DATA["password"]
) -> dict:
    response = await client.post("/auth/login", json={"email": email, "password": password})
    return response.json()


class TestRegister:
    async def test_register_success(self, client: AsyncClient):
        response = await client.post("/auth/register", json=USER_DATA)
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == USER_DATA["email"]
        assert data["full_name"] == USER_DATA["full_name"]
        assert data["role"] == "patient"
        assert data["is_active"] is True
        assert "id" in data

    async def test_register_duplicate_email(self, client: AsyncClient):
        await client.post("/auth/register", json=USER_DATA)
        response = await client.post("/auth/register", json=USER_DATA)
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    async def test_register_invalid_email(self, client: AsyncClient):
        data = {**USER_DATA, "email": "not-an-email"}
        response = await client.post("/auth/register", json=data)
        assert response.status_code == 422

    async def test_register_short_password(self, client: AsyncClient):
        data = {**USER_DATA, "email": "short@test.com", "password": "short"}
        response = await client.post("/auth/register", json=data)
        assert response.status_code == 422

    async def test_register_invalid_role(self, client: AsyncClient):
        data = {**USER_DATA, "email": "role@test.com", "role": "superadmin"}
        response = await client.post("/auth/register", json=data)
        assert response.status_code == 422


class TestLogin:
    async def test_login_success(self, client: AsyncClient):
        await register_user(client)
        response = await client.post(
            "/auth/login", json={"email": USER_DATA["email"], "password": USER_DATA["password"]}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password(self, client: AsyncClient):
        await register_user(client)
        response = await client.post("/auth/login", json={"email": USER_DATA["email"], "password": "wrongpassword"})
        assert response.status_code == 401
        assert "Invalid email or password" in response.json()["detail"]

    async def test_login_nonexistent_user(self, client: AsyncClient):
        response = await client.post("/auth/login", json={"email": "noone@test.com", "password": "whatever123"})
        assert response.status_code == 401


class TestRefresh:
    async def test_refresh_success(self, client: AsyncClient):
        await register_user(client)
        tokens = await login_user(client)

        response = await client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        # New refresh token should differ (rotation)
        assert data["refresh_token"] != tokens["refresh_token"]

    async def test_refresh_invalid_token(self, client: AsyncClient):
        response = await client.post("/auth/refresh", json={"refresh_token": "invalid.token.here"})
        assert response.status_code == 401

    async def test_refresh_reuse_revoked_token(self, client: AsyncClient):
        await register_user(client)
        tokens = await login_user(client)

        # Use refresh token once (it gets rotated/deleted)
        await client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})

        # Try to reuse the old refresh token
        response = await client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
        assert response.status_code == 401


class TestMe:
    async def test_me_success(self, client: AsyncClient):
        await register_user(client)
        tokens = await login_user(client)

        response = await client.get("/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == USER_DATA["email"]
        assert data["full_name"] == USER_DATA["full_name"]

    async def test_me_no_token(self, client: AsyncClient):
        response = await client.get("/auth/me")
        assert response.status_code == 403

    async def test_me_invalid_token(self, client: AsyncClient):
        response = await client.get("/auth/me", headers={"Authorization": "Bearer invalid.token.here"})
        assert response.status_code == 401


class TestHealth:
    async def test_health(self, client: AsyncClient):
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}
