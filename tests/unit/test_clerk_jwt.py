"""Tests for Clerk JWT verification (mocked JWKS)."""

from unittest.mock import MagicMock, patch

from backend.auth.clerk_jwt import verify_clerk_token


@patch("backend.auth.clerk_jwt._get_jwk_client")
@patch("backend.auth.clerk_jwt.jwt.decode")
def test_verify_clerk_token_valid(mock_decode, mock_jwk_client):
    mock_client = MagicMock()
    mock_client.get_signing_key_from_jwt.return_value = MagicMock(key="secret")
    mock_jwk_client.return_value = mock_client
    mock_decode.return_value = {"sub": "user_abc", "email": "user@test.com"}

    with patch("backend.auth.clerk_jwt.settings") as mock_settings:
        mock_settings.clerk_jwks_url = "https://example.com/jwks"
        result = verify_clerk_token("fake.jwt.token")

    assert result is not None
    assert result.user_id == "user_abc"
    assert result.email == "user@test.com"


def test_verify_clerk_token_no_jwks_url():
    with patch("backend.auth.clerk_jwt.settings") as mock_settings:
        mock_settings.clerk_jwks_url = ""
        assert verify_clerk_token("token") is None
