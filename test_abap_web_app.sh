#!/bin/bash

# Test script to build the Live ABAP Web Application using the agent API

# Step 1: Create a session
echo "Creating session..."
SESSION_RESPONSE=$(curl -s -X POST http://localhost:8001/api/agent/sessions)
SESSION_ID=$(echo $SESSION_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['session_id'])")
echo "Session ID: $SESSION_ID"

# Step 2: Send the SRS document to build the app
echo -e "\nSending build request..."

SRS_TEXT="Build a Live To-Do Web Application powered by the ABAP programming language on the backend.
Since this is running locally, you MUST use the Open-ABAP transpiler ecosystem to convert ABAP to JS.

Please scaffold and build the following architecture:

1. package.json:
   - Must use \"type\": \"module\"
   - Install dependencies: @abaplint/runtime, express
   - Install devDependencies: @abaplint/cli, @abaplint/transpiler-cli
   - \"build\" script: \"rm -rf output && abap_transpile abap_transpile.json\"
   - \"start\" script: \"npm run build && node src/server.js\"

2. abaplint.json: Configured for syntax v702
3. abap_transpile.json: Configured to read from \"src\" and output to \"output\"

4. src/zcl_todo_controller.clas.abap:
   - An ABAP Class that defines a ty_todo structure and a standard table (mt_todos).
   - Methods: get_all(), add_task(iv_desc), toggle_task(iv_id).

5. src/server.js:
   - An Express server on port 3000.
   - Serves static files from 'public'.
   - IMPORTANT: Imports the ABAP runtime 'import \"../output/init.mjs\";'
   - Dynamically imports the transpiled class 'await import(\"../output/zcl_todo_controller.clas.mjs\"); const zcl_todo_controller = abap.Classes[\"ZCL_TODO_CONTROLLER\"];'
   - Wraps the ABAP methods in standard REST API endpoints (GET /api/todos, POST /api/todos, POST /api/todos/:id/toggle).
   - After starting the server, console.log exactly: 'Validation: App is running and accessible at http://localhost:3000'

6. public/index.html:
   - A beautiful frontend UI (dark mode, glassmorphism) using fetch() to talk to the Express API.

Run 'npm install' and 'npm start' to start the application in the background and leave it running."

# Use WebSocket to stream the response
echo "Connect to WebSocket at: ws://localhost:8001/api/agent/stream/$SESSION_ID"
echo ""
echo "Or use the web interface at: http://localhost:5173"
echo ""
echo "Paste this in the chat:"
echo "---"
echo "$SRS_TEXT"
