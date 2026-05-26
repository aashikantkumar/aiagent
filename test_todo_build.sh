#!/bin/bash

# Test script to build the To-Do application using the agent API

# Step 1: Create a session
echo "Creating session..."
SESSION_RESPONSE=$(curl -s -X POST http://localhost:8001/api/agent/sessions)
SESSION_ID=$(echo $SESSION_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['session_id'])")
echo "Session ID: $SESSION_ID"

# Step 2: Send the SRS document to build the app
echo -e "\nSending build request..."

SRS_TEXT="Build a complete To-Do Website application with the following requirements:

## Features Required:
1. User Authentication (Register/Login with JWT)
2. Task Management (Create, Edit, Delete, Mark Complete)
3. Task Priority (High, Medium, Low)
4. Due Date tracking
5. Search and Filter tasks
6. Responsive design (mobile + desktop)

## Tech Stack:
- Frontend: React.js with Tailwind CSS
- Backend: Node.js + Express.js
- Database: MongoDB
- Authentication: JWT

## Database Schema:
- Users: userId, name, email, password (hashed)
- Tasks: taskId, title, description, status, priority, dueDate, createdBy

## API Endpoints:
- POST /register - Register user
- POST /login - Login user
- GET /tasks - Get all tasks
- POST /tasks - Add task
- PUT /tasks/:id - Update task
- DELETE /tasks/:id - Delete task

Build the complete application with all files, install dependencies, and run it."

# Use WebSocket to stream the response
echo "Connect to WebSocket at: ws://localhost:8001/api/agent/stream/$SESSION_ID"
echo ""
echo "Or use the web interface at: http://localhost:5173"
echo ""
echo "Paste this in the chat:"
echo "---"
echo "$SRS_TEXT"
