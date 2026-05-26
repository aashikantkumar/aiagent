#!/usr/bin/env python3
"""
Test script to verify the AI agent can build applications
"""
import asyncio
import websockets
import json
import requests

BACKEND_URL = "http://localhost:8001"

async def test_build_todo_app():
    """Test building a To-Do application"""
    
    # Step 1: Create a session
    print("📝 Creating session...")
    response = requests.post(f"{BACKEND_URL}/api/agent/sessions")
    session_data = response.json()
    session_id = session_data['session_id']
    print(f"✅ Session created: {session_id}")
    print(f"   Using LLM: {session_data['profile']['provider']} - {session_data['profile']['model']}")
    
    # Step 2: Connect to WebSocket
    ws_url = f"ws://localhost:8001/api/agent/stream/{session_id}"
    print(f"\n🔌 Connecting to WebSocket...")
    
    srs_text = """Build a simple To-Do application with these features:

1. Task Management:
   - Add new tasks with title and description
   - Mark tasks as complete
   - Delete tasks
   - List all tasks

2. Tech Stack:
   - Frontend: Simple HTML + CSS + JavaScript
   - Backend: Python Flask
   - Database: SQLite

3. Requirements:
   - Create a single-page application
   - Store tasks in SQLite database
   - RESTful API endpoints
   - Responsive design

Build the complete application, install dependencies, and run it on port 5000."""

    try:
        async with websockets.connect(ws_url) as websocket:
            print("✅ Connected to WebSocket")
            
            # Send the build request
            print(f"\n🚀 Sending build request...")
            await websocket.send(json.dumps({
                "type": "message",
                "content": srs_text
            }))
            print("✅ Request sent")
            
            print("\n📡 Streaming agent responses:\n")
            print("=" * 80)
            
            # Receive and print responses
            message_count = 0
            async for message in websocket:
                try:
                    data = json.loads(message)
                    message_count += 1
                    
                    if data.get('type') == 'event':
                        event_type = data.get('event')
                        content = data.get('content', '')
                        
                        if event_type == 'plan':
                            print(f"\n📋 PLAN:\n{content}\n")
                        elif event_type == 'action':
                            print(f"\n⚡ ACTION: {content}")
                        elif event_type == 'observation':
                            print(f"👁️  OBSERVATION: {content[:200]}...")
                        elif event_type == 'finish':
                            print(f"\n✅ FINISHED: {content}")
                            break
                        elif event_type == 'error':
                            print(f"\n❌ ERROR: {content}")
                            break
                    
                    elif data.get('type') == 'status':
                        status = data.get('status')
                        print(f"📊 Status: {status}")
                        
                except json.JSONDecodeError:
                    print(f"Raw message: {message}")
                    
            print("=" * 80)
            print(f"\n✅ Received {message_count} messages")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure:")
        print("  1. Backend is running: PORT=8001 python main.py")
        print("  2. GROQ_API_KEY is set in backend/.env")
        print("  3. Docker is running for sandbox")

if __name__ == "__main__":
    print("🤖 AI Agent Application Builder Test")
    print("=" * 80)
    asyncio.run(test_build_todo_app())
