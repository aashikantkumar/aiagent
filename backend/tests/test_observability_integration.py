import os
import unittest
from core.config import Settings

class TestObservabilityIntegration(unittest.TestCase):
    def setUp(self):
        # Save original env
        self.original_env = {
            "LANGCHAIN_TRACING_V2": os.environ.get("LANGCHAIN_TRACING_V2"),
            "LANGCHAIN_API_KEY": os.environ.get("LANGCHAIN_API_KEY"),
            "LANGCHAIN_PROJECT": os.environ.get("LANGCHAIN_PROJECT"),
            "LANGCHAIN_ENDPOINT": os.environ.get("LANGCHAIN_ENDPOINT"),
        }
        # Clean up env for test
        for k in self.original_env:
            if k in os.environ:
                del os.environ[k]

    def tearDown(self):
        # Restore env
        for k, v in self.original_env.items():
            if v is None:
                if k in os.environ:
                    del os.environ[k]
            else:
                os.environ[k] = v

    def test_settings_default_values(self):
        settings = Settings()
        self.assertFalse(settings.LANGCHAIN_TRACING_V2)
        self.assertIsNone(settings.LANGCHAIN_API_KEY)
        self.assertEqual(settings.LANGCHAIN_PROJECT, "ai-agent-builder")
        self.assertEqual(settings.LANGCHAIN_ENDPOINT, "https://api.smith.langchain.com")

    def test_export_to_env_enabled(self):
        settings = Settings(
            LANGCHAIN_TRACING_V2=True,
            LANGCHAIN_API_KEY="test-key-12345",
            LANGCHAIN_PROJECT="test-project",
            LANGCHAIN_ENDPOINT="https://test.endpoint.com"
        )
        settings.export_to_env()
        
        self.assertEqual(os.environ.get("LANGCHAIN_TRACING_V2"), "true")
        self.assertEqual(os.environ.get("LANGCHAIN_API_KEY"), "test-key-12345")
        self.assertEqual(os.environ.get("LANGCHAIN_PROJECT"), "test-project")
        self.assertEqual(os.environ.get("LANGCHAIN_ENDPOINT"), "https://test.endpoint.com")

    def test_export_to_env_disabled(self):
        settings = Settings(
            LANGCHAIN_TRACING_V2=False,
            LANGCHAIN_API_KEY="test-key-12345",
        )
        settings.export_to_env()
        
        # Should NOT be in os.environ because tracing is disabled
        self.assertNotIn("LANGCHAIN_TRACING_V2", os.environ)
        self.assertNotIn("LANGCHAIN_API_KEY", os.environ)
