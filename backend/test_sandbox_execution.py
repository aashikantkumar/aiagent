import asyncio
import time
from runtime import DockerRuntime
from agent.schema import CmdRunAction, FileWriteAction

async def run_test():
    session_id = "test-crud-session"
    print(f"1. Spawning Docker Sandbox for session '{session_id}'...")
    
    # 1. Initialize the Docker Sandbox (this is what the backend does when a session starts)
    runtime = DockerRuntime.get(session_id)
    
    # Give it a second to boot the bash shell
    await asyncio.sleep(2)
    
    # 2. Run a standard bash command (like the agent checking where it is)
    print("\n2. AI Agent checking environment (running 'pwd' and 'node -v')...")
    obs1 = await runtime.execute(CmdRunAction(command="pwd"))
    obs2 = await runtime.execute(CmdRunAction(command="node -v"))
    print(f"   [Terminal Output] pwd: {obs1['output']}")
    print(f"   [Terminal Output] node -v: {obs2['output']}")

    # 3. Create the CRUD HTML/JS/CSS files
    print("\n3. AI Agent creating the simple CRUD App files via Docker Terminal...")
    
    index_html = """<!DOCTYPE html>
<html>
<head>
    <title>Simple CRUD App</title>
    <style>body { font-family: sans-serif; padding: 20px; }</style>
</head>
<body>
    <h1>Simple CRUD App</h1>
    <input type="text" id="itemInput" placeholder="Add an item...">
    <button onclick="addItem()">Add</button>
    <ul id="itemList"></ul>
    
    <script>
        const list = document.getElementById('itemList');
        function addItem() {
            const input = document.getElementById('itemInput');
            if(input.value) {
                const li = document.createElement('li');
                li.innerText = input.value;
                list.appendChild(li);
                input.value = '';
            }
        }
    </script>
</body>
</html>"""

    # The AI uses the FileWriteAction which tar-pipes the file directly into the sandbox
    write_obs = await runtime.execute(FileWriteAction(path="index.html", content=index_html))
    print(f"   [Terminal Output] {write_obs['output']}")

    # 4. Verify the file exists in the Docker terminal using 'ls' and 'cat'
    print("\n4. AI Agent verifying the file creation with 'ls -la'...")
    ls_obs = await runtime.execute(CmdRunAction(command="ls -la index.html"))
    print(f"   [Terminal Output] {ls_obs['output']}")
    
    # 5. Start a Python HTTP Server to serve the CRUD app inside the sandbox
    print("\n5. AI Agent starting web server on port 8000 inside Docker...")
    # Using background execution just like the agent would to prevent blocking
    await runtime.execute(CmdRunAction(command="python3 -m http.server 8000 &"))
    
    # Give the server a second to start
    await asyncio.sleep(2)
    
    # 6. Check the health of the container on port 8000
    print("\n6. Backend running Health Check on the exposed port...")
    health = await runtime.health_check(port=8000)
    print(f"   [Health Check Result] Healthy: {health.get('healthy')} | URL: {health.get('url')}")
    
    # Cleanup
    print("\n7. Test complete. Cleaning up Docker container...")
    runtime.cleanup()
    print("   [Success] Container destroyed.")

if __name__ == "__main__":
    asyncio.run(run_test())
