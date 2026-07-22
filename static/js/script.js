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

        updateTopicColors();
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
            if (this.classList.contains('disabled')) return;
            var scope = this.closest('.topicRow, .threeBtns, .colorRow, .s-age') || this.closest('.btn-group');
            if (!scope) return;
            scope.querySelectorAll('.btnradio').forEach(function (b) {
                if (b !== btn) b.classList.remove('checked');
            });
            this.classList.add('checked');
            saveFilters();
            // Own gender change → toggle own age
            if (scope.classList.contains('threeBtns') && scope.parentElement.classList.contains('sexRow')) {
                updateOwnAgeState();
            }
        });
    });

    function updateOwnAgeState() {
        var ownGender = document.querySelector('.threeBtns:first-of-type .btnradio.checked');
        var isAny = ownGender && ownGender.getAttribute('data-gender') === 'any';
        var topicBtn = document.querySelector('.topicRow .btnradio.checked');
        var topic = topicBtn ? topicBtn.getAttribute('data-topic') : 'chat';
        document.querySelectorAll('#ownAgeGroup .btnradio').forEach(function (b) {
            if (isAny) {
                b.classList.add('disabled');
                b.classList.remove('checked');
            } else {
                b.classList.remove('disabled');
                // Re-apply flirt restriction (teen disabled for 18+)
                if (topic === 'flirt' && b.getAttribute('data-age') === 'teen') {
                    b.classList.add('disabled');
                    b.classList.remove('checked');
                }
            }
        });
        // Ensure at least one age is checked when re-enabled
        if (!isAny && !document.querySelector('#ownAgeGroup .btnradio.checked')) {
            var young = document.querySelector('#ownAgeGroup button[data-age="young"]');
            if (young) young.classList.add('checked');
        }
    }

    // Topic buttons color the main menu + age restrictions for 18+
    function updateTopicColors() {
        var topicBtn = document.querySelector('.topicRow .btnradio.checked');
        var topic = topicBtn ? topicBtn.getAttribute('data-topic') : 'chat';
        var step = document.querySelector('.main_step');
        step.classList.remove('adult_topic_search', 'roles_topic_search');
        if (topic === 'flirt') {
            step.classList.add('adult_topic_search');
        } else if (topic === 'rp') {
            step.classList.add('roles_topic_search');
        }
        // Age restrictions: flirt = no under 18
        var ownTeen = document.querySelector('#ownAgeGroup button[data-age="teen"]');
        var partnerTeen = document.querySelector('#partnerAgeGroup button[data-age="teen"]');
        if (topic === 'flirt') {
            // Disable teen buttons
            if (ownTeen) { ownTeen.classList.add('disabled'); ownTeen.classList.remove('checked'); }
            if (partnerTeen) { partnerTeen.classList.add('disabled'); partnerTeen.classList.remove('checked'); }
            // Switch own age to young if it was teen
            var ownChecked = document.querySelector('#ownAgeGroup .btnradio.checked');
            if (!ownChecked || ownChecked.getAttribute('data-age') === 'teen') {
                var youngBtn = document.querySelector('#ownAgeGroup button[data-age="young"]');
                if (youngBtn) { youngBtn.classList.add('checked'); }
            }
        } else {
            if (ownTeen) ownTeen.classList.remove('disabled');
            if (partnerTeen) partnerTeen.classList.remove('disabled');
        }
    }

    document.querySelectorAll('.topicRow .btnradio').forEach(function (btn) {
        btn.addEventListener('click', function () {
            updateTopicColors();
            updateOwnAgeState();
        });
    });

    // Check buttons
    document.querySelectorAll('.btncheck').forEach(function (btn) {
        btn.addEventListener('click', function () {
            if (this.classList.contains('disabled')) return;
            this.classList.toggle('checked');
            saveFilters();
        });
    });

    // Restore saved filters on load
    restoreFilters();
    updateOwnAgeState();

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

    function scrollChatToBottom() {
        var chatMessages = document.getElementById('chat_messages');
        if (chatMessages && chatMessages.offsetParent !== null) {
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
    }

    if (window.visualViewport) {
        window.visualViewport.addEventListener('resize', function () {
            scrollChatToBottom();
        });
    }

    var msgInput = document.getElementById('message_input');
    if (msgInput) {
        msgInput.addEventListener('focus', function () {
            setTimeout(function () {
                scrollChatToBottom();
            }, 300);
        });
    }

    function showAgentDisconnected() {
        var chatMessages = document.getElementById('chat_messages');
        var block = document.createElement('div');
        block.className = 'mess_block system';
        var inner = document.createElement('div');
        inner.style.cssText = 'text-align:center;color:var(--night-chat-message-time-color);font-size:12px;padding:10px 0;';
        inner.textContent = '✕ Собеседник отключился';
        block.appendChild(inner);
        chatMessages.appendChild(block);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        showTalkOver();
        sendBtn.disabled = true;
        stopAgentPolling();
    }

    function showAgentReconnected() {
        showInput();
        sendBtn.disabled = false;
    }

    var agentPollInterval = null;

    function startAgentPolling() {
        stopAgentPolling();
        agentPollInterval = setInterval(function () {
            var token = currentChar ? currentChar._token : '';
            if (!token) return;
            fetch('/api/agent/poll', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token: token })
            })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (data.reconnected) {
                    showAgentReconnected();
                    addMessage(data.message, 'nekto');
                }
            })
            .catch(function () {});
        }, 5000);
    }

    function stopAgentPolling() {
        if (agentPollInterval) {
            clearInterval(agentPollInterval);
            agentPollInterval = null;
        }
    }

    function showAgentMessagesSequentially(messages, index, done) {
        if (!messages || index >= messages.length) {
            if (done) done();
            return;
        }
        var typing = document.getElementById('typing_indicator');
        if (typing) typing.style.display = 'block';
        chatMessages.scrollTop = chatMessages.scrollHeight;
        var delay = 800 + Math.random() * 1200;
        setTimeout(function () {
            if (typing) typing.style.display = 'none';
            addMessage(messages[index], 'nekto');
            setTimeout(function () {
                showAgentMessagesSequentially(messages, index + 1, done);
            }, 500 + Math.random() * 1000);
        }, delay);
    }

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
        return block;
    }

    function getSearchDelay(partnerAgeGroups) {
        // partnerAgeGroups: array of age labels like ['до 17', 'от 18 до 21', ...]
        var count = partnerAgeGroups.length;

        // If only mature (36+) selected — very slow
        if (count === 1 && partnerAgeGroups[0] === 'старше 36') {
            return 10000 + Math.random() * 8000;
        }

        // Base delay depends on how many age groups selected
        var baseDelays = {
            0: 4000,    // none selected (shouldn't happen)
            1: 3500,
            2: 2000,
            3: 1200,
            4: 600,
        };
        var base = baseDelays[count] || 600;

        // Add randomness
        return base + Math.random() * 1500;
    }

    var searchCancelled = false;

    // Search button
    function startSearch() {
        searchCancelled = false;

        var topicBtn = document.querySelector('.topicRow .btnradio.checked');
        var topic = topicBtn ? topicBtn.getAttribute('data-topic') : 'chat';
        var isAdult = topic === 'flirt';
        var isRp = topic === 'rp';

        var header = document.getElementById('headerChat');
        header.classList.remove('adult_topic', 'roles_topic');
        if (isAdult) {
            header.classList.add('adult_topic');
        } else if (isRp) {
            header.classList.add('roles_topic');
        }

        document.getElementById('headerChatMode').style.display = 'none';
        document.getElementById('headerSearchMode').style.display = 'none';
        showStep('connectingStep');

        // Collect filters
        var ownGenderBtn = document.querySelector('.threeBtns:first-of-type .btnradio.checked');
        var ownGender = ownGenderBtn ? ownGenderBtn.getAttribute('data-gender') : 'any';

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
                own_gender: ownGender,
                partner_gender: partnerGender,
                partner_age: partnerAges,
                topic: topic
            })
        })
        .then(function (r) { return r.json(); })
        .then(function (char) {
            if (searchCancelled) return;
            currentChar = char;

            var delay = getSearchDelay(partnerAges);
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
                stopAgentPolling();

                // Show typing indicator, then opener(s)
                var openers = [];
                if (char._openers_count > 1) {
                    // Multi-part opener — split by [NEXT]
                    var raw = char.chat_opener || 'Привет!';
                    openers = raw.split('[NEXT]').map(function (s) { return s.trim(); }).filter(function (s) { return s; });
                } else {
                    openers = [char.chat_opener || 'Привет!'];
                }
                var typing = document.getElementById('typing_indicator');
                if (typing) typing.style.display = 'block';
                setTimeout(function () {
                    if (!searchCancelled) {
                        if (typing) typing.style.display = 'none';
                        var oi = 0;
                        function showNextOpener() {
                            if (oi >= openers.length) {
                                if (char.agent_mode) startAgentPolling();
                                return;
                            }
                            addMessage(openers[oi], 'nekto');
                            oi++;
                            if (oi < openers.length) {
                                setTimeout(showNextOpener, 600 + Math.random() * 800);
                            } else {
                                if (char.agent_mode) startAgentPolling();
                            }
                        }
                        showNextOpener();
                    }
                }, 1200 + Math.random() * 800);
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
        stopAgentPolling();
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

            // Main reply
            if (data.reply) {
                addMessage(data.reply, 'nekto');
            }

            // Agent's additional messages (one by one with typing indicator)
            if (data.agent_messages && data.agent_messages.length > 0) {
                showAgentMessagesSequentially(data.agent_messages, 0, function () {
                    if (data.agent_disconnected) {
                        showAgentDisconnected();
                    }
                });
            } else if (data.agent_disconnected) {
                showAgentDisconnected();
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
        var cm = document.getElementById('chat_messages');
        if (cm) cm.scrollTop = cm.scrollHeight;
    }

    // Talk over buttons
    function showSearchStep() {
        showInput();
        document.getElementById('headerChatMode').style.display = 'block';
        document.getElementById('headerSearchMode').style.display = 'none';
        showStep('searchStep');
        document.getElementById('chat_box').classList.remove('chat-mode');
        startOnlinePolling();
        stopAgentPolling();
    }

    // End chat modal
    document.getElementById('endChatBtn').addEventListener('click', function () {
        document.getElementById('endChatModal').style.display = 'flex';
    });

    document.getElementById('modalEndYes').addEventListener('click', function () {
        document.getElementById('endChatModal').style.display = 'none';
        showTalkOver();
        document.getElementById('sendMessageBtn').disabled = true;
        stopAgentPolling();
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
