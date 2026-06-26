import sys
import os
import pytest
from unittest.mock import AsyncMock, MagicMock

# Add parent directory to path to import agent modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.nodes import update_tasks_todo
from agent.schema import CmdRunAction, FileWriteAction

@pytest.mark.anyio
async def test_update_tasks_todo_create_and_modify():
    # Setup mock runtime
    runtime = MagicMock()
    runtime.execute = AsyncMock()
    
    # Mock return value for runtime.execute for file check (CmdRunAction)
    # File exists check returns exit_code=0
    runtime.execute.return_value = {"exit_code": 0, "output": ""}
    
    # State with plan having one create and one modify step
    state = {
        'plan': '{"project": "test-project", "description": "test-desc", "steps": [{"file": "src/App.jsx", "action": "modify", "description": "Modify App"}, {"file": "src/NewFile.jsx", "action": "create", "description": "Create NewFile"}]}',
        'modified_files': []
    }
    
    # Call update_tasks_todo
    await update_tasks_todo(runtime, "session-123", state)
    
    # Check that FileWriteAction was called to write tasks_todo.md
    assert runtime.execute.call_count >= 1
    # Find the FileWriteAction call
    write_call = None
    for call in runtime.execute.call_args_list:
        action = call[0][0]
        if isinstance(action, FileWriteAction) and action.path == "tasks_todo.md":
            write_call = action
            break
            
    assert write_call is not None
    content = write_call.content
    # Since modified_files is empty, the "modify" step (src/App.jsx) should be [ ]
    # The "create" step (src/NewFile.jsx) should be [x] because file exists (exists=True)
    assert "- [ ] **MODIFY** `src/App.jsx`" in content
    assert "- [x] **CREATE** `src/NewFile.jsx`" in content
    
    # Now simulate modified_files contains src/App.jsx
    state['modified_files'] = ['src/App.jsx']
    runtime.execute.reset_mock()
    runtime.execute.return_value = {"exit_code": 0, "output": ""}
    
    await update_tasks_todo(runtime, "session-123", state)
    
    write_call = None
    for call in runtime.execute.call_args_list:
        action = call[0][0]
        if isinstance(action, FileWriteAction) and action.path == "tasks_todo.md":
            write_call = action
            break
            
    assert write_call is not None
    content = write_call.content
    # Now the "modify" step should be [x]
    assert "- [x] **MODIFY** `src/App.jsx`" in content
    assert "- [x] **CREATE** `src/NewFile.jsx`" in content


@pytest.mark.anyio
async def test_update_tasks_todo_boilerplate_create():
    # Setup mock runtime
    runtime = MagicMock()
    runtime.execute = AsyncMock()
    
    # Mock return value for file check to exist
    runtime.execute.return_value = {"exit_code": 0, "output": ""}
    
    # State with plan having standard boilerplate file under "create" action
    state = {
        'plan': '{"project": "test-project", "description": "test-desc", "steps": [{"file": "src/App.jsx", "action": "create", "description": "Create App"}]}',
        'modified_files': []
    }
    
    # Call update_tasks_todo
    await update_tasks_todo(runtime, "session-123", state)
    
    # Check that FileWriteAction was called
    write_call = None
    for call in runtime.execute.call_args_list:
        action = call[0][0]
        if isinstance(action, FileWriteAction) and action.path == "tasks_todo.md":
            write_call = action
            break
            
    assert write_call is not None
    content = write_call.content
    # Since it is a boilerplate file and modified_files is empty, it must be [ ] (incomplete)
    # even though action is "create" and file exists.
    assert "- [ ] **CREATE** `src/App.jsx`" in content
    
    # Now add to modified_files
    state['modified_files'] = ['src/App.jsx']
    runtime.execute.reset_mock()
    runtime.execute.return_value = {"exit_code": 0, "output": ""}
    await update_tasks_todo(runtime, "session-123", state)
    
    write_call = None
    for call in runtime.execute.call_args_list:
        action = call[0][0]
        if isinstance(action, FileWriteAction) and action.path == "tasks_todo.md":
            write_call = action
            break
            
    assert write_call is not None
    content = write_call.content
    # Now it should be [x]
    assert "- [x] **CREATE** `src/App.jsx`" in content
