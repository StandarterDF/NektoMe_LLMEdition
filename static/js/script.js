document.addEventListener('DOMContentLoaded', function () {
    var currentChar = null;
    var LS_KEY = 'nektome_filters';

    function saveFilters() {
        var data = {
            topic: document.querySelector('.topicRow .btnradio.checked')?.getAttribute('data-topic') || 'chat',
            ownGender: document.querySelector('.threeBtns:first-of-type .btnradio.checked')?.getAttribute('data-gender') || 'any',
            partnerGender: document.querySelector('.wishSex .btnradio.checked')?.getAttribute('data-partner') || 'any',
            ownAge: document.querySelector('#ownAgeGroup .btnradio.checked')?.getAttribute('data-age') || 'young',
            partnerAges: Array.from(document.querySelectorAll('#partnerAgeGroup .btncheck.checked')).map(function (b) { return b.getAttribute('data-age'); }),
            theme: document.querySelector('.colorRow .btnradio.checked')?.getAttribute('data-theme') || 'dark',
        };
        try { localStorage.setItem(LS_KEY, JSON.stringify(data)); } catch (e) {}
    }

    function restoreFilters() {
        var raw;
        try { raw = localStorage.getItem(LS_KEY); } catch (e) {}
        if (!raw) return;
        var data;
        try { data = JSON.parse(raw); } catch (e) { return; }
        if (!data) return;

        // Topic — clear group first
        document.querySelectorAll('.topicRow .btnradio').forEach(function (b) { b.classList.remove('checked'); });
        var topicBtn = document.querySelector('.topicRow button[data-topic="' + data.topic + '"]');
        if (topicBtn) topicBtn.classList.add('checked');

        // Own gender
        document.querySelectorAll('.threeBtns:first-of-type .btnradio').forEach(function (b) { b.classList.remove('checked'); });
        var ogBtn = document.querySelector('.threeBtns:first-of-type button[data-gender="' + data.ownGender + '"]');
        if (ogBtn) ogBtn.classList.add('checked');

        // Partner gender
        document.querySelectorAll('.wishSex .btnradio').forEach(function (b) { b.classList.remove('checked'); });
        var pgBtn = document.querySelector('.wishSex button[data-partner="' + data.partnerGender + '"]');
        if (pgBtn) pgBtn.classList.add('checked');

        // Own age
        document.querySelectorAll('#ownAgeGroup .btnradio').forEach(function (b) { b.classList.remove('checked'); });
        var oaBtn = document.querySelector('#ownAgeGroup button[data-age="' + data.ownAge + '"]');
        if (oaBtn) oaBtn.classList.add('checked');

        // Partner ages
        document.querySelectorAll('#partnerAgeGroup .btncheck').forEach(function (b) {
            var age = b.getAttribute('data-age');
            if (data.partnerAges && data.partnerAges.indexOf(age) !== -1) {
                b.classList.add('checked');
            } else {
                b.classList.remove('checked');
            }
        });

        // Theme
        document.querySelectorAll('.colorRow .btnradio').forEach(function (b) { b.classList.remove('checked'); });
        var themeBtn = document.querySelector('.colorRow button[data-theme="' + data.theme + '"]');
        if (themeBtn) themeBtn.classList.add('checked');
        applyTheme(data.theme);
    }

    function applyTheme(theme) {
        var body = document.body;
        if (theme === 'light') {
            body.classList.remove('night_theme');
            body.classList.add('light_theme');
        } else {
            body.classList.remove('light_theme');
            body.classList.add('night_theme');
        }
    }

    // Radio buttons — grouped by common parent container
    document.querySelectorAll('.btnradio').forEach(function (btn) {
        btn.addEventListener('click', function () {
            // Determine the radio group scope
            var scope = this.closest('.topicRow, .threeBtns, .colorRow') || this.closest('.btn-group');
            if (!scope) {
                scope = document.getElementById('ownAgeGroup');
                if (!scope || !scope.contains(this)) return;
            }
            scope.querySelectorAll('.btnradio').forEach(function (b) {
                if (b !== btn) b.classList.remove('checked');
            });
            this.classList.add('checked');
            saveFilters();
        });
    });

    // Check buttons
    document.querySelectorAll('.btncheck').forEach(function (btn) {
        btn.addEventListener('click', function () {
            this.classList.toggle('checked');
            saveFilters();
        });
    });

    // Restore saved filters on load
    restoreFilters();

    // Online counter — fetches from server, animates smoothly
    var currentCount = 2000;
    var targetCount = 2000;

    function fetchOnlineTarget() {
        fetch('/api/online')
            .then(function (r) { return r.json(); })
            .then(function (data) {
                targetCount = data.total;
            })
            .catch(function () {});
    }

    function animateOnline() {
        var diff = targetCount - currentCount;
        if (Math.abs(diff) < 0.5) {
            currentCount = targetCount;
        } else {
            currentCount += diff * 0.05;
        }
        document.getElementById('onlineCount').textContent = Math.round(currentCount);
        requestAnimationFrame(animateOnline);
    }

    var onlineInterval = setInterval(fetchOnlineTarget, 3000);

    function stopOnlinePolling() {
        clearInterval(onlineInterval);
    }

    function startOnlinePolling() {
        clearInterval(onlineInterval);
        fetchOnlineTarget();
        onlineInterval = setInterval(fetchOnlineTarget, 3000);
    }

    fetchOnlineTarget();
    animateOnline();

    function showStep(stepId) {
        document.querySelectorAll('.step_chatbox').forEach(function (s) {
            s.style.display = 'none';
            s.classList.remove('visible');
        });
        var step = document.getElementById(stepId);
        if (step) {
            step.style.display = '';
            requestAnimationFrame(function () {
                step.classList.add('visible');
            });
        }
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

    function getSearchDelay() {
        var hour = new Date().getHours();
        if (hour >= 8 && hour < 24) {
            return 300 + Math.random() * 1700;
        }
        return 500 + Math.random() * 4500;
    }

    var searchCancelled = false;

    // Search button
    function startSearch() {
        searchCancelled = false;

        var topicBtn = document.querySelector('.topicRow .btnradio.checked');
        var topic = topicBtn ? topicBtn.getAttribute('data-topic') : 'chat';
        var isAdult = topic === 'flirt';

        var header = document.getElementById('headerChat');
        if (isAdult) {
            header.classList.add('adult_topic');
        } else {
            header.classList.remove('adult_topic');
        }

        document.getElementById('headerChatMode').style.display = 'none';
        document.getElementById('headerSearchMode').style.display = 'none';
        showStep('connectingStep');

        // Collect filters
        var partnerGenderBtn = document.querySelector('.wishSex .btnradio.checked');
        var partnerGender = partnerGenderBtn ? partnerGenderBtn.getAttribute('data-partner') : 'any';

        var ageChecks = document.querySelectorAll('#partnerAgeGroup .btncheck.checked');
        var partnerAges = [];
        ageChecks.forEach(function (b) {
            var age = b.getAttribute('data-age');
            if (age === 'teen') partnerAges.push('до 17');
            else if (age === 'young') partnerAges.push('от 18 до 21');
            else if (age === 'adult') { partnerAges.push('от 22 до 25'); partnerAges.push('от 26 до 35'); }
            else if (age === 'mature') partnerAges.push('старше 36');
        });

        var searchStart = Date.now();

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
            if (searchCancelled) return;
            currentChar = char;

            var delay = getSearchDelay();
            var elapsed = Date.now() - searchStart;
            var wait = Math.max(0, delay - elapsed);

            setTimeout(function () {
                if (searchCancelled) return;

                // Switch to chat
                showInput();
                document.getElementById('chat_box').classList.add('chat-mode');
                showStep('chatStep');
                stopOnlinePolling();
                document.getElementById('headerSearchMode').style.display = 'block';
                document.getElementById('sendMessageBtn').disabled = false;
                document.getElementById('message_input').focus();
                document.getElementById('endChatBtn').style.display = '';

                var chatMessages = document.getElementById('chat_messages');
                chatMessages.innerHTML = '';

                // Show opener after brief delay
                var opener = char.chat_opener || 'Привет!';
                setTimeout(function () {
                    if (!searchCancelled) addMessage(opener, 'nekto');
                }, 300);
            }, wait);
        })
        .catch(function () {
            if (searchCancelled) return;
            showStep('searchStep');
            document.getElementById('headerSearchMode').style.display = 'none';
            document.getElementById('headerChatMode').style.display = 'block';
            document.getElementById('endChatBtn').style.display = 'none';
            startOnlinePolling();
        });
    }

    document.getElementById('searchCompanyBtn').addEventListener('click', startSearch);

    // Cancel search
    document.getElementById('cancelSearchBtn').addEventListener('click', function () {
        searchCancelled = true;
        document.getElementById('chat_box').classList.remove('chat-mode');
        document.getElementById('headerSearchMode').style.display = 'none';
        document.getElementById('headerChatMode').style.display = 'block';
        showStep('searchStep');
        startOnlinePolling();
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
            applyTheme(theme);
            saveFilters();
        });
    });

    function showInput() {
        document.getElementById('talk_over').style.display = 'none';
        document.getElementById('message_input').setAttribute('contenteditable', 'true');
        document.getElementById('message_input').focus();
    }

    function showTalkOver() {
        document.getElementById('talk_over').style.display = '';
        document.getElementById('message_input').setAttribute('contenteditable', 'false');
        document.getElementById('message_input').blur();
    }

    // Talk over buttons
    function showSearchStep() {
        showInput();
        document.getElementById('headerChatMode').style.display = 'block';
        document.getElementById('headerSearchMode').style.display = 'none';
        showStep('searchStep');
        document.getElementById('chat_box').classList.remove('chat-mode');
        startOnlinePolling();
    }

    // End chat modal
    document.getElementById('endChatBtn').addEventListener('click', function () {
        document.getElementById('endChatModal').style.display = 'flex';
    });

    document.getElementById('modalEndYes').addEventListener('click', function () {
        document.getElementById('endChatModal').style.display = 'none';
        showTalkOver();
        document.getElementById('sendMessageBtn').disabled = true;
    });

    document.getElementById('modalEndNo').addEventListener('click', function () {
        document.getElementById('endChatModal').style.display = 'none';
    });

    document.getElementById('newChatBtn').addEventListener('click', function () {
        showInput();
        startSearch();
    });

    document.getElementById('changeParamsBtn').addEventListener('click', function () {
        showInput();
        showSearchStep();
    });
});
