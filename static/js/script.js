document.addEventListener('DOMContentLoaded', function () {
    var navToggle = document.querySelector('.navbar-toggle');
    var navCollapse = document.querySelector('.navbar-collapse');
    if (navToggle && navCollapse) {
        navToggle.addEventListener('click', function () {
            navCollapse.style.display = navCollapse.style.display === 'block' ? 'none' : 'block';
        });
    }

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

    // State
    var currentChar = null;

    // Show/hide steps
    function showStep(stepId) {
        document.querySelectorAll('.step_chatbox').forEach(function (s) {
            s.style.display = 'none';
        });
        var step = document.getElementById(stepId);
        if (step) step.style.display = 'block';
    }

    // Toggle section
    window.toggleSection = function (el) {
        var section = el.closest('.char-section');
        if (section) {
            section.classList.toggle('collapsed');
        }
    };

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

        // Show loading in char card
        showStep('charCardStep');
        document.getElementById('charSections').innerHTML =
            '<div class="char-loading"><div class="spinner"></div><div>Ищем собеседника...</div></div>';

        // Collect filters
        var partnerGenderBtn = document.querySelector('.wishSex .btnradio.checked');
        var partnerGender = partnerGenderBtn ? partnerGenderBtn.getAttribute('data-partner') : 'any';

        var ageChecks = document.querySelectorAll('.s-age .btncheck.checked');
        var partnerAges = [];
        ageChecks.forEach(function (b) {
            var age = b.getAttribute('data-age');
            if (age) {
                var labels = { 'teen': 'до 17', 'young': 'от 18 до 21', 'adult': 'от 22 до 25', 'mature': 'старше 36' };
                partnerAges.push(labels[age] || age);
            }
        });

        generateCharacter(partnerGender, partnerAges, topic);
    });

    function generateCharacter(partnerGender, partnerAges, topic) {
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
            renderCharCard(char);
        })
        .catch(function () {
            document.getElementById('charSections').innerHTML =
                '<div style="text-align:center;padding:20px;color:#cc1212;">Ошибка генерации. Попробуйте снова.</div>';
        });
    }

    function renderCharCard(char) {
        // Avatar
        var avatar = document.getElementById('charAvatar');
        avatar.textContent = char.name ? char.name[0] : '?';

        // Name
        document.getElementById('charNameTitle').textContent = char.name + ' ' + char.surname;
        document.getElementById('charSubtitle').textContent =
            (char.age || '?') + ' лет, ' + (char.zodiac || '') + ' — ' + char.city;

        // Tags
        var tagsContainer = document.getElementById('charTags');
        var tags = [char.archetype, char.temperament, char.mbti_code, char.social_style, char.body_size, char.beauty];
        tagsContainer.innerHTML = tags.filter(Boolean).map(function (t) {
            return '<span class="char-tag">' + t + '</span>';
        }).join('');

        // Sections
        document.getElementById('charAbout').innerHTML = formatAbout(char);
        document.getElementById('charAppearance').innerHTML = formatAppearance(char);
        document.getElementById('charPsychology').innerHTML = formatPsychology(char);
        document.getElementById('charPersonality').innerHTML = formatPersonality(char);
        document.getElementById('charInterests').innerHTML = formatInterests(char);
        document.getElementById('charBackstory').innerHTML = formatBackstory(char);

        // Collapse all sections by default except "О себе"
        var sections = document.querySelectorAll('.char-section');
        sections.forEach(function (s, i) {
            if (i > 0) s.classList.add('collapsed');
        });

        // Show header with name
        document.getElementById('headerChatMode').style.display = 'none';
        document.getElementById('headerSearchMode').style.display = 'block';
        document.getElementById('partnerName').textContent = char.name || 'Nekto';

        showStep('charCardStep');
    }

    function formatAbout(char) {
        var archetypeData = '';
        archetypeData += '<span class="char-label">Архетип</span><span class="char-value">' + char.archetype + ' (' + char.archetype_desire + ')</span>';
        archetypeData += '<span class="char-label">Цель</span><span class="char-value">' + (char.archetype_goal || '') + '</span>';
        archetypeData += '<span class="char-label">Талант</span><span class="char-value">' + (char.archetype_talent || '') + '</span>';
        archetypeData += '<span class="char-label">Темперамент</span><span class="char-value">' + char.temperament + ' · ' + char.mbti_code + ' (' + char.mbti_name + ')</span>';
        archetypeData += '<span class="char-label">Социальность</span><span class="char-value">' + char.social_style + '</span>';

        var aboutExtra = '';
        aboutExtra += '<span class="char-label">Профессия</span><span class="char-value">' + (char.profession || '') + '</span>';
        aboutExtra += '<span class="char-label">Достаток</span><span class="char-value">' + char.wealth_label + '</span>';
        aboutExtra += '<span class="char-label">Образование</span><span class="char-value">' + (char.education || '') + '</span>';
        var rel = char.relationship_status || '';
        aboutExtra += '<span class="char-label">Отношения</span><span class="char-value">' + rel + '</span>';

        return archetypeData + aboutExtra;
    }

    function formatAppearance(char) {
        return '<div class="char-value">' + (char.appearance_description || '') + '</div>';
    }

    function formatPsychology(char) {
        var t = char.trauma_name ? '<span class="char-label">Травма</span><span class="char-value">' + char.trauma_name + '</span>' : '';
        t += char.trauma_consequence ? '<span class="char-label">Последствие</span><span class="char-value">' + char.trauma_consequence + '</span>' : '';
        t += char.trauma_defense ? '<span class="char-label">Защита</span><span class="char-value">' + char.trauma_defense + '</span>' : '';
        t += char.trauma_belief ? '<span class="char-label">Убеждение</span><span class="char-value">' + char.trauma_belief + '</span>' : '';
        t += '<span class="char-label">Страхи</span><span class="char-value">' + (char.fears || []).join(', ') + '</span>';
        t += '<span class="char-label">Мечты</span><span class="char-value">' + (char.dreams || []).join(', ') + '</span>';
        t += '<span class="char-label">Ценности</span><span class="char-value">' + (char.relationship_values || []).join(', ') + '</span>';
        return t;
    }

    function formatPersonality(char) {
        var pos = (char.positive_traits || []).map(function (t) { return '<span class="char-attr-item">' + t + '</span>'; }).join('');
        var neg = (char.negative_traits || []).map(function (t) { return '<span class="char-attr-item">' + t + '</span>'; }).join('');
        var h = (char.habits || []).map(function (t) { return '<span class="char-attr-item">' + t + '</span>'; }).join('');

        var out = '';
        out += '<span class="char-label">Положительные черты</span><div class="char-attr-list">' + pos + '</div>';
        out += '<span class="char-label">Отрицательные черты</span><div class="char-attr-list">' + neg + '</div>';
        out += '<span class="char-label">Привычки</span><div class="char-attr-list">' + h + '</div>';

        // Spice blocks
        var spiceFields = [
            ['Жилище', 'housing'], ['Финансы', 'financial_habit'], ['Еда', 'eating_habit'],
            ['Питомец', 'pet'], ['Криптонит', 'cryptonite'], ['Талант', 'useless_talent'],
            ['Язык тела', 'body_language_tell'], ['Юмор', 'humor_style'],
            ['Самая большая ложь', 'biggest_lie'], ['Бесит', 'anger_trigger'],
            ['Враг', 'enemy'], ['Тип сна', 'sleep_type'], ['Запах', 'personal_scent'],
            ['Здоровье', 'health_issue'], ['Верования', 'supernatural_belief']
        ];
        spiceFields.forEach(function (pair) {
            var val = char[pair[1]];
            if (val && (typeof val === 'string' || (Array.isArray(val) && val.length))) {
                var v = Array.isArray(val) ? val.join(', ') : val;
                out += '<span class="char-label">' + pair[0] + '</span><span class="char-value">' + v + '</span>';
            }
        });

        return out;
    }

    function formatInterests(char) {
        var out = '';
        if (char.hobbies && char.hobbies.length) {
            out += '<span class="char-label">Увлечения</span><span class="char-value">' + char.hobbies.join(', ') + '</span>';
        }
        if (char.favorite_colors && char.favorite_colors.length) {
            out += '<span class="char-label">Цвета</span><span class="char-value">' + char.favorite_colors.join(', ') + '</span>';
        }
        if (char.favorite_foods && char.favorite_foods.length) {
            out += '<span class="char-label">Еда</span><span class="char-value">' + char.favorite_foods.join(', ') + '</span>';
        }
        if (char.favorite_drinks && char.favorite_drinks.length) {
            out += '<span class="char-label">Напитки</span><span class="char-value">' + char.favorite_drinks.join(', ') + '</span>';
        }
        if (char.favorite_music_genres && char.favorite_music_genres.length) {
            out += '<span class="char-label">Музыка</span><span class="char-value">' + char.favorite_music_genres.join(', ') + '</span>';
        }
        if (char.favorite_music_artists && char.favorite_music_artists.length) {
            out += '<span class="char-label">Исполнители</span><span class="char-value">' + char.favorite_music_artists.join(', ') + '</span>';
        }
        if (char.favorite_movie_genres && char.favorite_movie_genres.length) {
            out += '<span class="char-label">Фильмы</span><span class="char-value">' + (char.favorite_movie_titles || []).join(', ') + '</span>';
        }
        if (char.favorite_book_genres && char.favorite_book_genres.length) {
            out += '<span class="char-label">Книги</span><span class="char-value">' + (char.favorite_book_titles || []).join(', ') + '</span>';
        }
        if (char.fetishes && char.fetishes.length) {
            out += '<span class="char-label">Фетиши</span><span class="char-value">' + char.fetishes.join(', ') + '</span>';
        }
        return out;
    }

    function formatBackstory(char) {
        return '<div class="char-value">' + (char.backstory || '') + '</div>';
    }

    function formatChatProfile(char) {
        var out = '';
        out += '<span class="char-label">Стиль письма</span><span class="char-value">' + (char.writing_style || '') + '</span>';
        if (char.rp_ability) {
            out += '<span class="char-label">Ролевая игра</span><span class="char-value">Да</span>';
        }
        out += '<span class="char-label">Первое сообщение</span><span class="char-value">' + (char.chat_opener || '') + '</span>';
        out += '<span class="char-label">Юмор</span><span class="char-value">' + (char.humor_style || '') + '</span>';
        out += '<span class="char-label">Любимые темы</span><span class="char-value">' + (char.fav_topics || []).join(', ') + '</span>';
        out += '<span class="char-label">Табу</span><span class="char-value">' + (char.taboo_topics || []).join(', ') + '</span>';
        out += '<span class="char-label">Скип-факторы</span><span class="char-value">' + (char.skip_factors || []).join(', ') + '</span>';
        out += '<span class="char-label">На хамство</span><span class="char-value">' + (char.harassment_reaction || '') + '</span>';
        out += '<span class="char-label">Ложь</span><span class="char-value">' + (char.lying_tendency || '') + '</span>';
        out += '<span class="char-label">Откровенность</span><span class="char-value">' + char.oversharing_level + '/10</span>';
        return out;
    }

    // --- CHAT ---
    function startChat() {
        var char = currentChar;
        if (!char) return;

        showStep('chatStep');

        document.getElementById('headerChatMode').style.display = 'none';
        document.getElementById('headerSearchMode').style.display = 'block';
        document.getElementById('partnerName').textContent = char.name || 'Nekto';
        document.getElementById('sendMessageBtn').disabled = false;
        document.getElementById('talk_over').style.display = 'none';

        var chatMessages = document.getElementById('chat_messages');
        chatMessages.innerHTML = '';
        chatMessages.innerHTML +=
            '<div class="window_chat_dialog_write" id="typing_indicator" style="display:none;"><span>Собеседник печатает...</span></div>';

        addMessage('Собеседник найден! Это ' + char.name + ', ' + char.age + ' лет.', 'nekto');
        document.getElementById('message_input').focus();

        // Send opener
        setTimeout(function () {
            var opener = char.chat_opener || 'Привет!';
            addMessage(opener, 'nekto');
        }, 800);
    }

    // Char card buttons
    document.getElementById('charStartChatBtn').addEventListener('click', startChat);
    document.getElementById('charRegenerateBtn').addEventListener('click', function () {
        document.getElementById('headerChatMode').style.display = 'block';
        document.getElementById('headerSearchMode').style.display = 'none';
        showStep('searchStep');
    });

    // Chat UI
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

    function sendMessage() {
        var text = msgInput.innerText.trim();
        if (!text) return;

        addMessage(text, 'self');
        msgInput.innerText = '';
        msgInput.focus();
        sendBtn.disabled = true;

        // Show typing
        var typing = document.getElementById('typing_indicator');
        if (typing) typing.style.display = 'block';
        chatMessages.scrollTop = chatMessages.scrollHeight;

        fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text, token: currentChar._token })
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
            sendBtn.click();
        }
    });

    msgInput.addEventListener('input', function () {
        sendBtn.disabled = !this.innerText.trim();
    });

    // New chat / change params
    function showSearchStep() {
        document.getElementById('headerChatMode').style.display = 'block';
        document.getElementById('headerSearchMode').style.display = 'none';
        document.getElementById('talk_over').style.display = 'none';
        showStep('searchStep');
    }

    document.getElementById('newChatBtn').addEventListener('click', function () {
        generateCharacter('any', ['от 18 до 21', 'от 22 до 25', 'от 26 до 35', 'старше 36'], 'chat');
    });

    document.getElementById('changeParamsBtn').addEventListener('click', showSearchStep);
});
