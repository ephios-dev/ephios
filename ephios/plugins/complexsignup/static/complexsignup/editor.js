import {createApp, ref} from 'vue'

createApp({
    setup() {
        // give each todo a unique id
        const currentBlock = ref(null);

        function addTodo() {
            // ...
            newTodo.value = ''
        }

        function removeTodo(todo) {
            // ...
        }

        return {
            newTodo,
            todos,
            addTodo,
            removeTodo
        }
    }
}).mount('#app')