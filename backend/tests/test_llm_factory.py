import pytest
from unittest.mock import MagicMock
from agent.llm import LLMFactory

@pytest.fixture
def mock_secrets_service():
    service = MagicMock()
    service.get_secret.return_value = "mock_secret_key"
    return service

def test_llm_factory_initialization(mock_secrets_service):
    factory = LLMFactory(secrets_service=mock_secrets_service)
    assert factory.secrets_service == mock_secrets_service

def test_create_groq_llm(mock_secrets_service):
    factory = LLMFactory(secrets_service=mock_secrets_service)
    llm = factory.create(provider="groq", model_name="test-model")
    
    assert llm is not None
    # ChatLiteLLM properties
    assert llm.model == "groq/test-model"

def test_create_unknown_provider():
    factory = LLMFactory()
    with pytest.raises(ValueError):
        factory.create(provider="unknown")

def test_resolve_secret_success(mock_secrets_service):
    factory = LLMFactory(secrets_service=mock_secrets_service)
    secret = factory._resolve_secret("groq", "fallback")
    assert secret == "mock_secret_key"
    mock_secrets_service.get_secret.assert_called_with("groq")

def test_resolve_secret_fallback():
    mock_service = MagicMock()
    mock_service.get_secret.side_effect = Exception("Not found")
    factory = LLMFactory(secrets_service=mock_service)
    secret = factory._resolve_secret("groq", "fallback")
    assert secret == "fallback"


def test_create_gemini_llm_single_key(mock_secrets_service):
    from core.config import get_settings
    settings = get_settings()
    original_key = settings.GEMINI_API_KEY
    original_keys = settings.GEMINI_API_KEYS
    try:
        settings.GEMINI_API_KEY = "key1"
        settings.GEMINI_API_KEYS = None
        
        factory = LLMFactory(secrets_service=mock_secrets_service)
        llm = factory.create(provider="gemini", model_name="gemini-2.5-flash")
        
        assert llm is not None
        assert llm.api_keys == ["key1"]
    finally:
        settings.GEMINI_API_KEY = original_key
        settings.GEMINI_API_KEYS = original_keys


def test_create_gemini_llm_multiple_keys(mock_secrets_service):
    from core.config import get_settings
    settings = get_settings()
    original_key = settings.GEMINI_API_KEY
    original_keys = settings.GEMINI_API_KEYS
    try:
        settings.GEMINI_API_KEY = "key1"
        settings.GEMINI_API_KEYS = "key2, key3"
        
        factory = LLMFactory(secrets_service=mock_secrets_service)
        llm = factory.create(provider="gemini", model_name="gemini-2.5-flash")
        
        assert llm is not None
        assert "key2" in llm.api_keys
        assert "key3" in llm.api_keys
        assert "key1" in llm.api_keys
        assert len(llm.api_keys) == 3
    finally:
        settings.GEMINI_API_KEY = original_key
        settings.GEMINI_API_KEYS = original_keys
