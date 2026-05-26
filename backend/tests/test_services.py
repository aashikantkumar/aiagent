import pytest
from unittest.mock import MagicMock, patch
from services.secrets_service import SecretsService
from core.config import get_settings

def test_secrets_service_initialization():
    service = SecretsService()
    assert service is not None

@patch("services.secrets_service.SecretsService.get_secret")
def test_get_secret(mock_get_secret):
    mock_get_secret.return_value = "secret_value"
    service = SecretsService()
    val = service.get_secret("test_key")
    assert val == "secret_value"
    mock_get_secret.assert_called_with("test_key")

@patch("services.secrets_service.SecretsService.store_secret")
def test_store_secret(mock_store_secret):
    mock_store_secret.return_value = True
    service = SecretsService()
    success = service.store_secret("test_key", "secret_value")
    assert success is True
    mock_store_secret.assert_called_with("test_key", "secret_value")
