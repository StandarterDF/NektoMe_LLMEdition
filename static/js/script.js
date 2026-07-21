document.addEventListener('DOMContentLoaded', function () {
    var navToggle = document.querySelector('.navbar-toggle');
    var navCollapse = document.querySelector('.navbar-collapse');

    navToggle.addEventListener('click', function () {
        navCollapse.style.display = navCollapse.style.display === 'block' ? 'none' : 'block';
    });

    document.querySelectorAll('.btnradio').forEach(function (btn) {
        btn.addEventListener('click', function () {
            var group = this.closest('.btn-group');
            if (!group) return;
            group.querySelectorAll('.btnradio').forEach(function (b) {
                b.classList.remove('checked');
            });
            this.classList.add('checked');
        });
    });

    document.querySelectorAll('.btncheck').forEach(function (btn) {
        btn.addEventListener('click', function () {
            this.classList.toggle('checked');
        });
    });

    document.getElementById('searchCompanyBtn').addEventListener('click', function () {
        document.querySelector('.main_step').style.display = 'none';
        document.querySelector('.chat_step').style.display = 'block';
        document.getElementById('sendMessageBtn').disabled = false;
        document.getElementById('message_input').focus();
        document.getElementById('headerChatMode').style.display = 'none';
        document.getElementById('headerSearchMode').style.display = 'block';
    });

    var sendBtn = document.getElementById('sendMessageBtn');
    var msgInput = document.getElementById('message_input');
    var chatMessages = document.getElementById('chat_messages');

    function addMessage(text, type) {
        var time = new Date().toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
        var block = document.createElement('div');
        block.className = 'mess_block ' + type;
        var inner = document.createElement('div');
        var bubble = document.createElement('div');
        bubble.className = 'window_chat_dialog_text';
        var tri = document.createElement('div');
        tri.className = 'tri';
        bubble.appendChild(tri);
        bubble.appendChild(document.createTextNode(text));
        var timeSpan = document.createElement('div');
        timeSpan.className = 'window_chat_dialog_time';
        timeSpan.textContent = time;
        inner.appendChild(bubble);
        inner.appendChild(timeSpan);
        block.appendChild(inner);
        chatMessages.appendChild(block);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    sendBtn.addEventListener('click', function () {
        var text = msgInput.innerText.trim();
        if (text) {
            addMessage(text, 'self');
            msgInput.innerText = '';
            msgInput.focus();
            sendBtn.disabled = true;
        }
    });

    msgInput.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendBtn.click();
        }
    });

    msgInput.addEventListener('input', function () {
        sendBtn.disabled = !this.innerText.trim();
    });

    function showSearchStep() {
        document.querySelector('.chat_step').style.display = 'none';
        document.querySelector('.main_step').style.display = 'block';
        document.getElementById('talk_over').style.display = 'none';
        document.getElementById('headerChatMode').style.display = 'block';
        document.getElementById('headerSearchMode').style.display = 'none';
    }

    document.getElementById('newChatBtn').addEventListener('click', showSearchStep);
    document.getElementById('changeParamsBtn').addEventListener('click', showSearchStep);

    document.querySelectorAll('.topicRow .btnradio').forEach(function (btn) {
        btn.addEventListener('click', function () {
            var isAdult = this.textContent.trim() === 'Флирт 18+';
            var header = document.getElementById('headerChat');
            var step = document.querySelector('.main_step');
            if (isAdult) {
                header.classList.add('adult_topic');
                step.classList.add('adult_topic_search');
            } else {
                header.classList.remove('adult_topic');
                step.classList.remove('adult_topic_search');
            }
        });
    });
});
