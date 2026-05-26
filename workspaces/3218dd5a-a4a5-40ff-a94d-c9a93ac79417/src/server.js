const express = require('express');
const app = express();
const port = 3000;

app.use(express.static('public'));

import('../output/init.mjs');
const zcl_todo_controller = await import('../output/zcl_todo_controller.clas.mjs');
const todoController = new zcl_todo_controller.ZCL_TODO_CONTROLLER();

app.get('/api/todos', async (req, res) => {
  const todos = await todoController.get_all();
  res.json(todos);
});

app.post('/api/todos', async (req, res) => {
  const { desc } = req.body;
  todoController.add_task(desc);
  res.send('Task added successfully');
});

app.post('/api/todos/:id/toggle', async (req, res) => {
  const id = req.params.id;
  todoController.toggle_task(id);
  res.send('Task toggled successfully');
});

app.listen(port, () => {
  console.log(`Server started on port ${port}`);
  console.log('Validation: App is running and accessible at http://localhost:3000');
});