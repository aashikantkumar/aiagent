const todoList = document.getElementById('todo-list');
const todoInput = document.getElementById('todo-input');
const addTodoBtn = document.getElementById('add-todo-btn');

addTodoBtn.addEventListener('click', async () => {
  const desc = todoInput.value;
  const response = await fetch('/api/todos', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ desc })
  });
  const todo = await response.json();
  todoInput.value = '';
  renderTodos();
});

async function renderTodos() {
  const response = await fetch('/api/todos');
  const todos = await response.json();
  const todoHtml = todos.map(todo => {
    return `
      <li>
        <span>${todo.desc}</span>
        <button class="toggle-btn" data-id="${todo.id}">Toggle</button>
      </li>
    `;
  }).join('');
  todoList.innerHTML = todoHtml;
  const toggleBtns = document.querySelectorAll('.toggle-btn');
  toggleBtns.forEach(btn => {
    btn.addEventListener('click', async () => {
      const id = btn.dataset.id;
      await fetch(`/api/todos/${id}/toggle`, { method: 'POST' });
      renderTodos();
    });
  });
}

renderTodos();