document.addEventListener('DOMContentLoaded', function () {
    // Navigation toggle
    document.querySelector('.navbar-toggle').addEventListener('click', function () {
        var nav = document.querySelector('.navbar-collapse');
        nav.style.display = nav.style.display === 'block' ? 'none' : 'block';
    });

    // Topic selection
    var topicBtns = document.querySelectorAll('[data-topic]');
    topicBtns.forEach(function (btn) {
        btn.addEventListener('click', function () {
            topicBtns.forEach(function (b) { b.classList.remove('checked'); });
            this.classList.add('checked');
        });
    });

    // Sex selection
    var sexBtns = document.querySelectorAll('[data-sex]');
    sexBtns.forEach(function (btn) {
        btn.addEventListener('click', function () {
            sexBtns.forEach(function (b) { b.classList.remove('checked'); });
            this.classList.add('checked');
        });
    });

    // Age selection
    var ageBtns = document.querySelectorAll('[data-age]');
    ageBtns.forEach(function (btn) {
        btn.addEventListener('click', function () {
            ageBtns.forEach(function (b) { b.classList.remove('checked'); });
            this.classList.add('checked');
        });
    });

    // Start search button
    document.getElementById('searchCompanyBtn').addEventListener('click', function () {
        document.querySelector('.main_step').style.display = 'none';
        document.querySelector('.chat_step').style.display = 'block';
        document.getElementById('sendMessageBtn').disabled = false;
    });

    // Send message
    document.getElementById('sendMessageBtn').addEventListener('click', function () {
        var input = document.getElementById('message_input');
        var text = input.innerText.trim();
        if (text) {
            addMessage(text, 'self');
            input.innerText = '';
            input.focus();
        }
    });

    // Enter to send
    document.getElementById('message_input').addEventListener('keydown', function (e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            document.getElementById('sendMessageBtn').click();
        }
    });

    // Enable/disable send button based on input
    document.getElementById('message_input').addEventListener('input', function () {
        var btn = document.getElementById('sendMessageBtn');
        btn.disabled = !this.innerText.trim();
    });

    // New chat / change params
    document.getElementById('newChatBtn').addEventListener('click', function () {
        document.querySelector('.chat_step').style.display = 'none';
        document.querySelector('.main_step').style.display = 'block';
        document.getElementById('talk_over').style.display = 'none';
    });

    document.getElementById('changeParamsBtn').addEventListener('click', function () {
        document.querySelector('.chat_step').style.display = 'none';
        document.querySelector('.main_step').style.display = 'block';
        document.getElementById('talk_over').style.display = 'none';
    });

    document.getElementById('change_params_but').addEventListener('click', function () {
        document.querySelector('.chat_step').style.display = 'none';
        document.querySelector('.main_step').style.display = 'block';
    });

    function addMessage(text, type) {
        var container = document.getElementById('chat_messages');
        var time = new Date().toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });

        var block = document.createElement('div');
        block.className = 'mess_block ' + type;

        var inner = document.createElement('div');
        inner.style.cssText = 'position: relative; overflow: hidden;';

        var bubble = document.createElement('div');
        bubble.className = 'window_chat_dialog_text';
        bubble.textContent = text;

        var tri = document.createElement('div');
        tri.className = 'tri';

        var timeSpan = document.createElement('div');
        timeSpan.className = 'window_chat_dialog_time';
        timeSpan.textContent = time;

        bubble.appendChild(tri);
        inner.appendChild(bubble);
        inner.appendChild(timeSpan);
        block.appendChild(inner);
        container.appendChild(block);

        container.scrollTop = container.scrollHeight;
    }
});
