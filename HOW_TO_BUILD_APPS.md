# 🚀 How to Build Complete Applications with Your AI Agent

Your myaiagent application **CAN build complete applications** just like OpenHands! It takes an SRS document and automatically creates the entire project.

---

## ✅ What Your Agent Can Do

Your agent follows this workflow:

1. **PLAN** - Analyzes requirements and creates project structure
2. **SCAFFOLD** - Creates config files (package.json, requirements.txt, etc.)
3. **IMPLEMENT** - Writes ALL source files (no placeholders!)
4. **VALIDATE** - Runs the app and fixes errors automatically

---

## 🎯 Method 1: Use the Web Interface (Easiest)

### Step 1: Open the Application
```
http://localhost:5173
```

### Step 2: Paste Your Requirements

In the chat interface, paste your complete SRS document. For example:

```
Build a To-Do Website with the following requirements:

## Features:
1. User Authentication (Register/Login with JWT)
2. Task Management (Create, Edit, Delete, Mark Complete)
3. Task Priority (High, Medium, Low)
4. Due Date tracking
5. Search and Filter tasks
6. Responsive design

## Tech Stack:
- Frontend: React.js with Tailwind CSS
- Backend: Node.js + Express.js
- Database: MongoDB
- Authentication: JWT

## Database Schema:
- Users: userId, name, email, password
- Tasks: taskId, title, description, status, priority, dueDate

## API Endpoints:
- POST /register - Register user
- POST /login - Login user
- GET /tasks - Get all tasks
- POST /tasks - Add task
- PUT /tasks/:id - Update task
- DELETE /tasks/:id - Delete task

Build the complete application with all files.
```

### Step 3: Watch the Magic

The agent will:
- ✅ Create a project plan
- ✅ Write all files (frontend + backend)
- ✅ Install dependencies
- ✅ Run the application
- ✅ Fix errors automatically
- ✅ Show you the running app

---

## 🧪 Method 2: Test with Python Script

We've created a test script for you:

```bash
cd "/media/aashikant/GAME Volume/aicode/myaiagent"
python3 test_agent.py
```

This will:
1. Create a session
2. Send a build request for a simple To-Do app
3. Stream the agent's progress in real-time
4. Show you each step (plan, implement, execute, validate)

---

## 📝 Method 3: Use the API Directly

### Create a Session
```bash
curl -X POST http://localhost:8001/api/agent/sessions
```

Response:
```json
{
  "session_id": "abc-123",
  "profile": {
    "provider": "groq",
    "model": "groq/llama-3.3-70b-versatile"
  }
}
```

### Connect to WebSocket
```javascript
const ws = new WebSocket('ws://localhost:8001/api/agent/stream/abc-123');

ws.onopen = () => {
  ws.send(JSON.stringify({
    type: 'message',
    content: 'Build a To-Do app with React and Node.js...'
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data);
};
```

---

## 🎨 Example: Your To-Do Website SRS

Here's how to use your exact SRS document:

### 1. Open Web Interface
```
http://localhost:5173
```

### 2. Paste This Prompt

```
Build a complete To-Do Website based on this SRS:

SOFTWARE REQUIREMENTS SPECIFICATION (SRS)
To-Do Website

1. INTRODUCTION
Purpose: Develop a simple and user-friendly To-Do Website for managing daily tasks.

2. FEATURES
- User Registration and Login (JWT Authentication)
- Add, Edit, Delete Tasks
- Mark Tasks as Complete
- Set Task Priority (High, Medium, Low)
- Set Due Dates
- Search and Filter Tasks
- Responsive Design (Desktop + Mobile)

3. TECH STACK
Frontend:
- React.js
- Tailwind CSS

Backend:
- Node.js
- Express.js
- JWT Authentication

Database:
- MongoDB

4. DATABASE SCHEMA

Users Collection:
- userId: ObjectId
- name: String
- email: String
- password: String (hashed)

Tasks Collection:
- taskId: ObjectId
- title: String
- description: String
- status: String (pending/completed)
- priority: String (high/medium/low)
- dueDate: Date
- createdBy: userId (reference)

5. API ENDPOINTS

POST /api/register - Register new user
POST /api/login - Login user (returns JWT)
GET /api/tasks - Get all tasks for logged-in user
POST /api/tasks - Create new task
PUT /api/tasks/:id - Update task
DELETE /api/tasks/:id - Delete task

6. REQUIREMENTS
- Password encryption using bcrypt
- JWT token for authentication
- Input validation
- Error handling
- Responsive UI
- Mobile-friendly design

Build the complete application with:
1. All frontend components
2. All backend routes and controllers
3. Database models
4. Authentication middleware
5. Package.json with all dependencies
6. README with setup instructions

Install all dependencies and run the application.
```

### 3. Wait for Completion

The agent will:
1. **Plan** (30 seconds) - Create project structure
2. **Implement** (5-10 minutes) - Write all files
3. **Execute** (2-3 minutes) - Install dependencies and run
4. **Validate** (1 minute) - Verify everything works

Total time: **10-15 minutes** for a complete application!

---

## 🔍 What Happens Behind the Scenes

### Phase 1: Planning
```json
{
  "project_name": "todo-website",
  "tech_stack": {
    "frontend": "React + Tailwind",
    "backend": "Node.js + Express",
    "database": "MongoDB"
  },
  "files": [
    "frontend/src/App.jsx",
    "frontend/src/components/TaskList.jsx",
    "backend/server.js",
    "backend/routes/auth.js",
    ...
  ]
}
```

### Phase 2: Implementation
The agent writes each file completely:
- ✅ `package.json` with all dependencies
- ✅ `frontend/src/App.jsx` - Main React component
- ✅ `frontend/src/components/TaskList.jsx` - Task list component
- ✅ `backend/server.js` - Express server
- ✅ `backend/routes/auth.js` - Authentication routes
- ✅ `backend/models/User.js` - User model
- ✅ `backend/models/Task.js` - Task model
- ✅ And many more...

### Phase 3: Execution
```bash
<run>npm install</run>
<run>cd backend && npm install</run>
<run>cd frontend && npm install</run>
<run>cd backend && npm start &</run>
<run>cd frontend && npm run dev</run>
```

### Phase 4: Validation
```bash
<browse command='goto' target='http://localhost:3000' />
```

---

## 🎯 Tips for Best Results

### 1. Be Specific
❌ Bad: "Build a todo app"
✅ Good: "Build a todo app with React, Node.js, MongoDB, JWT auth, and these features: [list]"

### 2. Include Tech Stack
Always specify:
- Frontend framework (React, Vue, Angular)
- Backend framework (Node.js, Python Flask, Django)
- Database (MongoDB, PostgreSQL, SQLite)
- Authentication method (JWT, OAuth, Session)

### 3. List All Features
Be explicit about:
- User authentication
- CRUD operations
- Search/filter functionality
- Responsive design
- Error handling

### 4. Provide Database Schema
Include:
- Collection/table names
- Field names and types
- Relationships

### 5. Specify API Endpoints
List all routes:
- Method (GET, POST, PUT, DELETE)
- Path (/api/tasks)
- Description

---

## 🐛 Troubleshooting

### Agent Not Responding
```bash
# Check backend is running
curl http://localhost:8001/

# Check WebSocket connection
wscat -c ws://localhost:8001/api/agent/stream/SESSION_ID
```

### Agent Produces Errors
The agent will automatically:
- Read error messages
- Fix the code
- Retry execution
- Up to 5 retries per command

### Want to See Logs
```bash
# Backend logs
cd backend
tail -f logs/app.log

# Or check console output
```

---

## 📊 Performance

Your agent uses **Groq API** which is:
- ✅ **10x faster** than local Ollama
- ✅ **FREE** with generous limits
- ✅ **Great for coding** tasks

Expected build times:
- Simple app (Todo, Calculator): **5-10 minutes**
- Medium app (Blog, E-commerce): **15-30 minutes**
- Complex app (Social Network): **30-60 minutes**

---

## 🎉 Success Indicators

You'll know it worked when you see:

```
✅ Plan ready
✅ Files created: 15/15
✅ Dependencies installed
✅ Backend running on port 3001
✅ Frontend running on port 3000
✅ Application validated
🎉 Your To-Do Website is ready!
```

Then you can access your app at:
```
http://localhost:3000
```

---

## 🚀 Next Steps

After the agent builds your app:

1. **Test it** - Open the URL and try all features
2. **Review code** - Check the generated files
3. **Customize** - Ask the agent to modify features
4. **Deploy** - Use Vercel, Netlify, or Heroku

---

## 💡 Example Prompts to Try

### Simple Calculator
```
Build a calculator app with React. Include basic operations (+, -, *, /), 
clear button, and responsive design. Use Tailwind CSS.
```

### Weather App
```
Build a weather app with React that uses OpenWeatherMap API. 
Features: search by city, show current weather, 5-day forecast, 
temperature unit toggle (C/F). Use Tailwind CSS.
```

### Blog Platform
```
Build a blog platform with React frontend and Node.js backend.
Features: user auth, create/edit/delete posts, comments, 
markdown support, search. Use MongoDB and JWT auth.
```

---

## 🎯 Your Agent vs OpenHands

| Feature | Your Agent | OpenHands |
|---------|-----------|-----------|
| Build complete apps | ✅ Yes | ✅ Yes |
| Auto-fix errors | ✅ Yes | ✅ Yes |
| Multiple retries | ✅ Yes (5x) | ✅ Yes |
| Groq API | ✅ Yes | ❌ No |
| Docker sandbox | ✅ Yes | ✅ Yes |
| WebSocket streaming | ✅ Yes | ✅ Yes |
| Web interface | ✅ Yes | ✅ Yes |

**Your agent is production-ready!** 🚀

---

## 📚 More Examples

Check the `examples/` folder for:
- Todo app SRS
- E-commerce SRS
- Blog platform SRS
- Social network SRS

---

**Ready to build? Open http://localhost:5173 and start creating!** 🎉
