# Guide: Building an ABAP To-Do Application with the AI Agent

Since ABAP is traditionally run inside proprietary SAP NetWeaver Application Servers, a full SAP stack cannot be run locally in the agent's lightweight Docker sandbox. 

However, we can use the **Open-ABAP ecosystem** (specifically `@abaplint/transpiler-cli` and `@abaplint/runtime`) which allows the AI agent to write standard ABAP code, transpile it to JavaScript, and run/validate it directly in the Node.js environment of the sandbox!

---

## 🛠️ What is Needed in the Workspace

To compile and run ABAP code, the AI agent needs to set up the following files in the project directory:

### 1. `package.json`
Specifies the transpiler CLI, compiler lint tools, and runtime dependencies.
```json
{
  "name": "abap-todo-app",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "build": "rm -rf output && abap_transpile abap_transpile.json",
    "start": "npm run build && node src/index.js"
  },
  "dependencies": {
    "@abaplint/runtime": "^2.12.32"
  },
  "devDependencies": {
    "@abaplint/cli": "^2.115.27",
    "@abaplint/transpiler-cli": "^2.12.32"
  }
}
```

### 2. `abaplint.json`
Configures the syntax checker and defines the target ABAP version (e.g., standard `v702` or `v750` statements).
```json
{
  "global": {
    "files": "/src/**/*.abap"
  },
  "dependencies": [],
  "syntax": {
    "version": "v702",
    "errorNamespace": "."
  },
  "rules": {
    "parser_error": true,
    "unknown_types": true
  }
}
```

### 3. `abap_transpile.json`
Tells the transpiler where to find the source `.abap` files and where to output the transpiled JavaScript.
```json
{
  "input_folder": "src",
  "input_filter": [],
  "output_folder": "output",
  "libs": [],
  "write_unit_tests": false,
  "write_source_map": false,
  "options": {
    "ignoreSyntaxCheck": false,
    "addFilenames": false,
    "addCommonJS": false,
    "unknownTypes": "runtimeError"
  }
}
```

### 4. `src/z_todo_app.prog.abap`
The core ABAP program implementing the To-Do logic (adding, displaying, and completing tasks).
```abap
REPORT z_todo_app.

TYPES: BEGIN OF ty_todo,
         id          TYPE i,
         description TYPE string,
         completed   TYPE abap_bool,
       END OF ty_todo.

DATA: lt_todos TYPE TABLE OF ty_todo,
      ls_todo  TYPE ty_todo.

* 1. Add some initial To-Do tasks
CLEAR ls_todo.
ls_todo-id = 1.
ls_todo-description = 'Learn ABAP on Node.js'.
ls_todo-completed = abap_false.
APPEND ls_todo TO lt_todos.

CLEAR ls_todo.
ls_todo-id = 2.
ls_todo-description = 'Build To-Do App with AI Agent'.
ls_todo-completed = abap_true.
APPEND ls_todo TO lt_todos.

* 2. Print the Header
WRITE: / '--- ABAP TO-DO LIST ---'.

* 3. Loop through tasks and display their status
LOOP AT lt_todos INTO ls_todo.
  DATA: lv_status TYPE string.
  IF ls_todo-completed = abap_true.
    lv_status = '[X] Completed'.
  ELSE.
    lv_status = '[ ] Pending'.
  ENDIF.
  
  WRITE: / 'ID:', ls_todo-id, '| Task:', ls_todo-description, '| Status:', lv_status.
ENDLOOP.

WRITE: / '-----------------------'.
```

### 5. `src/index.js`
The entry point script that imports the transpiled ABAP class/program and executes it under Node.js.
```javascript
import { FileManager } from "@abaplint/runtime";
// The transpiler outputs files as modules in the output folder.
// We load and run the entry point of the transpiled code.
await import("../output/z_todo_app.prog.mjs");
```

---

## 🚀 How to Prompt Your AI Agent to Build This

To make your AI agent build this project automatically from the Web Interface (or via API):

1. Start a **New Session** at `http://localhost:5173`.
2. Paste the following prompt into the chat window:

```text
Build a To-Do Console Application written in the ABAP programming language. 
To run ABAP code locally in the sandbox, we will use the Open-ABAP transpiler ecosystem.

Please scaffold and build the following files:
1. package.json:
   - Configure to use "type": "module"
   - Install @abaplint/runtime, @abaplint/cli, and @abaplint/transpiler-cli
   - Add a start script: "npm run build && node src/index.js"
   - Add a build script: "abap_transpile abap_transpile.json"
2. abaplint.json: Configure syntax check version to "v702"
3. abap_transpile.json: Configured to read from "src" folder and output to "output"
4. src/z_todo_app.prog.abap: An ABAP program that defines a structured internal table for To-Dos (id, description, completed status), appends multiple tasks to it, and prints the list using WRITE statements.
5. src/index.js: Imports the transpiled mjs file (../output/z_todo_app.prog.mjs) and executes it.

After writing the files, run "npm install" and "npm start" to verify the output in the console.
```

---

## 🔍 How the Agent Validates It
1. The agent will plan the structure and write all the files.
2. It will call `<run>npm install</run>`.
3. It will call `<run>npm start</run>`.
4. The output will print:
   ```text
   --- ABAP TO-DO LIST ---
   ID: 1 | Task: Learn ABAP on Node.js | Status: [ ] Pending
   ID: 2 | Task: Build To-Do App with AI Agent | Status: [X] Completed
   -----------------------
   ```
5. The agent will analyze the exit code and complete the task successfully.
