document.addEventListener('DOMContentLoaded', function () {
    var currentChar = null;

    // Radio buttons
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

    // Check buttons
    document.querySelectorAll('.btncheck').forEach(function (btn) {
        btn.addEventListener('click', function () {
            this.classList.toggle('checked');
        });
    });

    function showStep(stepId) {
        document.querySelectorAll('.step_chatbox').forEach(function (s) {
            s.style.display = 'none';
        });
        var step = document.getElementById(stepId);
        if (step) step.style.display = 'block';
    }

    function addMessage(text, type) {
        var chatMessages = document.getElementById('chat_messages');
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

    // Search button
    document.getElementById('searchCompanyBtn').addEventListener('click', function () {
        var topicBtn = document.querySelector('.topicRow .btnradio.checked');
        var topic = topicBtn ? topicBtn.getAttribute('data-topic') : 'chat';
        var isAdult = topic === 'flirt';

        var header = document.getElementById('headerChat');
        if (isAdult) {
            header.classList.add('adult_topic');
        } else {
            header.classList.remove('adult_topic');
        }

        // Switch to chat view immediately
        showStep('chatStep');
        document.getElementById('headerChatMode').style.display = 'none';
        document.getElementById('headerSearchMode').style.display = 'block';
        document.getElementById('sendMessageBtn').disabled = true;
        document.getElementById('talk_over').style.display = 'none';

        var chatMessages = document.getElementById('chat_messages');
        chatMessages.innerHTML = '';
        chatMessages.innerHTML +=
            '<div class="window_chat_dialog_write" id="typing_indicator" style="display:none;"><span>Собеседник печатает...</span></div>';

        addMessage('Поиск собеседника...', 'nekto');

        // Collect filters
        var partnerGenderBtn = document.querySelector('.wishSex .btnradio.checked');
        var partnerGender = partnerGenderBtn ? partnerGenderBtn.getAttribute('data-partner') : 'any';

        var ageChecks = document.querySelectorAll('.s-age .btncheck.checked');
        var partnerAges = [];
        ageChecks.forEach(function (b) {
            var age = b.getAttribute('data-age');
            if (age === 'teen') partnerAges.push('до 17');
            else if (age === 'young') partnerAges.push('от 18 до 21');
            else if (age === 'adult') { partnerAges.push('от 22 до 25'); partnerAges.push('от 26 до 35'); }
            else if (age === 'mature') partnerAges.push('старше 36');
        });

        fetch('/api/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                partner_gender: partnerGender,
                partner_age: partnerAges,
                topic: topic
            })
        })
        .then(function (r) { return r.json(); })
        .then(function (char) {
            currentChar = char;
            document.getElementById('partnerName').textContent = char.name || 'Nekto';
            document.getElementById('sendMessageBtn').disabled = false;
            document.getElementById('message_input').focus();

            // Clear loading message and add welcome
            chatMessages.innerHTML = '';
            chatMessages.innerHTML +=
                '<div class="window_chat_dialog_write" id="typing_indicator" style="display:none;"><span>Собеседник печатает...</span></div>';

            addMessage('Собеседник найден!', 'nekto');

            // Send opener after brief delay
            setTimeout(function () {
                var opener = char.chat_opener || 'Привет!';
                addMessage(opener, 'nekto');
            }, 700);
        })
        .catch(function () {
            chatMessages.innerHTML = '';
            addMessage('Ошибка поиска. Попробуйте снова.', 'nekto');
            document.getElementById('sendMessageBtn').disabled = false;
        });
    });

    // --- CHAT ---
    var sendBtn = document.getElementById('sendMessageBtn');
    var msgInput = document.getElementById('message_input');
    var chatMessages = document.getElementById('chat_messages');

    function sendMessage() {
        var text = msgInput.innerText.trim();
        if (!text) return;

        addMessage(text, 'self');
        msgInput.innerText = '';
        msgInput.focus();
        sendBtn.disabled = true;

        // Show typing indicator
        var typing = document.getElementById('typing_indicator');
        if (typing) typing.style.display = 'block';
        chatMessages.scrollTop = chatMessages.scrollHeight;

        fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: text,
                token: currentChar ? currentChar._token : ''
            })
        })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            if (typing) typing.style.display = 'none';
            if (data.reply) {
                addMessage(data.reply, 'nekto');
            }
            sendBtn.disabled = false;
            msgInput.focus();
        })
        .catch(function () {
            if (typing) typing.style.display = 'none';
            sendBtn.disabled = false;
        });
    }

    sendBtn.addEventListener('click', sendMessage);

    msgInput.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (!sendBtn.disabled) sendBtn.click();
        }
    });

    msgInput.addEventListener('input', function () {
        sendBtn.disabled = !this.innerText.trim();
    });

    // Color theme toggle
    document.querySelectorAll('.colorRow .btnradio').forEach(function (btn) {
        btn.addEventListener('click', function () {
            var theme = this.getAttribute('data-theme');
            var body = document.body;
            if (theme === 'light') {
                body.classList.remove('night_theme');
                body.classList.add('light_theme');
            } else {
                body.classList.remove('light_theme');
                body.classList.add('night_theme');
            }
        });
    });

    // Talk over buttons
    function showSearchStep() {
        document.getElementById('headerChatMode').style.display = 'block';
        document.getElementById('headerSearchMode').style.display = 'none';
        document.getElementById('talk_over').style.display = 'none';
        showStep('searchStep');
    }

    document.getElementById('newChatBtn').addEventListener('click', function () {
        // Trigger search with same params
        document.getElementById('searchCompanyBtn').click();
    });

    document.getElementById('changeParamsBtn').addEventListener('click', showSearchStep);
});
