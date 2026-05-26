import pytest
from agent.context_manager import ContextManager

def test_resolve_limit_exact():
    cm = ContextManager(model="groq/llama-3.3-70b-versatile")
    assert cm.budget.max_tokens == 128_000

def test_resolve_limit_clean():
    cm = ContextManager(model="llama-3.3-70b-versatile")
    assert cm.budget.max_tokens == 128_000

def test_resolve_limit_substring():
    # "llama-4-scout" is clean, "meta-llama/llama-4-scout-17b-16e-instruct" contains it
    cm = ContextManager(model="groq/llama-4-scout")
    assert cm.budget.max_tokens == 128_000

def test_resolve_limit_unknown():
    cm = ContextManager(model="unknown-model-name")
    assert cm.budget.max_tokens == 8_192

def test_resolve_limit_gemini():
    cm = ContextManager(model="gemini/gemini-2.5-flash")
    assert cm.budget.max_tokens == 128_000
