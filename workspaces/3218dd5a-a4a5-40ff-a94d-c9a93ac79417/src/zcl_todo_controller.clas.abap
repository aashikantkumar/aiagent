CLASS zcl_todo_controller DEFINITION.
  PUBLIC SECTION.
    TYPES: BEGIN OF ty_todo,
             id   TYPE i,
             desc TYPE string,
           END OF ty_todo.
    TYPES: tt_todos TYPE STANDARD TABLE OF ty_todo.

    METHODS: get_all
      RETURNING VALUE(rt_todos) TYPE tt_todos,
      add_task
        IMPORTING
          iv_desc TYPE string,
      toggle_task
        IMPORTING
          iv_id TYPE i.
ENDCLASS.

CLASS zcl_todo_controller IMPLEMENTATION.
  DATA: mt_todos TYPE tt_todos.

  METHOD get_all.
    rt_todos = mt_todos.
  ENDMETHOD.

  METHOD add_task.
    DATA: ls_todo TYPE ty_todo.
    ls_todo-id = lines( mt_todos ) + 1.
    ls_todo-desc = iv_desc.
    INSERT ls_todo INTO TABLE mt_todos.
  ENDMETHOD.

  METHOD toggle_task.
    FIELD-SYMBOLS: <fs_todo> LIKE LINE OF mt_todos.
    LOOP AT mt_todos ASSIGNING <fs_todo>.
      IF <fs_todo>-id = iv_id.
        " toggle task logic here
        RETURN.
      ENDIF.
    ENDLOOP.
  ENDMETHOD.
ENDCLASS.