import pytest
import json
from unittest.mock import patch, AsyncMock
from agent.research_node import research_node
from langchain_core.messages import AIMessage

@pytest.mark.anyio
@patch('agent.research_node.search_and_extract')
@patch('agent.research_node._resolve_research_llm')
async def test_research_node_html_css_js(mock_resolve_llm, mock_search_and_extract):
    # Mock search response
    mock_response = AsyncMock()
    mock_result = AsyncMock()
    mock_result.title = "React & Vite App Tutorial"
    mock_result.url = "https://example.com/react-vite"
    mock_result.snippet = "This is a React Vite app tutorial. Learn how to setup react vite."
    mock_result.content = "To build a react-vite app, run npm create vite@latest."
    mock_response.results = [mock_result]
    mock_response.error = ""
    mock_search_and_extract.return_value = mock_response

    # Mock LLM response
    mock_llm = AsyncMock()
    mock_message = AIMessage(content="Structured reference sheet: Vanilla HTML/CSS/JS with no frameworks, run via python -m http.server 3000.")
    mock_llm.return_value = mock_message
    mock_llm.ainvoke.return_value = mock_message
    mock_resolve_llm.return_value = mock_llm

    # Input state with html_css_js tech stack
    state = {
        "session_id": "test_session",
        "plan": json.dumps({
            "project": "TaskFlow",
            "tech_stack": {
                "frontend": "html_css_js",
                "backend": "none",
                "database": "none"
            },
            "description": "Vanilla To-Do List Application"
        })
    }

    result = await research_node(state)
    
    assert "research_context" in result
    assert "Vanilla HTML/CSS/JS" in result["research_context"]
    assert "React" not in result["research_context"]
