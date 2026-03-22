(function () {
    const LANGUAGE_KEY = 'vybe_lang';
    const REMEMBERED_USERS_KEY = 'vybe_remembered_users';
    const PASSWORD_SUGGESTIONS = [
        'Use 3 random words + number + symbol',
        'Try 14+ characters with mixed case',
        'Avoid names, birthdays, and repeated patterns',
        'Use a unique password for VybeFlow only'
    ];

    const I18N = {
        en: {
            language: 'Language',
            login_title: 'Login to VybeFlow', login_btn: 'Login', forgot_password: 'Forgot password?', need_account: 'Need an account?', sign_up_here: 'Sign up here',
            signup_title: 'Sign Up for VybeFlow', create_account: 'Create Account', already_have: 'Already have an account?', login_here: 'Login here',
            create_new_password: 'Create New Password', update_password: 'Update Password', back_to: 'Back to',
            regular: 'Regular', professional: 'Professional',
            strength_start: 'Start typing to check password strength.',
            strength_tip: 'Use 12+ chars, uppercase, lowercase, numbers, and symbols to harden your password.',
            suggestion: 'Suggestion',
            email_or_username: 'Email or Username', password: 'Password', username: 'Username', email: 'Email',
            new_password: 'New Password', confirm_password: 'Confirm Password'
        },
        es: {
            language: 'Idioma',
            login_title: 'Inicia sesión en VybeFlow', login_btn: 'Iniciar sesión', forgot_password: '¿Olvidaste tu contraseña?', need_account: '¿Necesitas una cuenta?', sign_up_here: 'Regístrate aquí',
            signup_title: 'Regístrate en VybeFlow', create_account: 'Crear cuenta', already_have: '¿Ya tienes cuenta?', login_here: 'Inicia sesión aquí',
            create_new_password: 'Crear nueva contraseña', update_password: 'Actualizar contraseña', back_to: 'Volver a',
            regular: 'Regular', professional: 'Profesional',
            strength_start: 'Empieza a escribir para verificar la seguridad.',
            strength_tip: 'Usa 12+ caracteres, mayúsculas, minúsculas, números y símbolos.',
            suggestion: 'Sugerencia',
            email_or_username: 'Correo o usuario', password: 'Contraseña', username: 'Usuario', email: 'Correo',
            new_password: 'Nueva contraseña', confirm_password: 'Confirmar contraseña'
        },
        fr: {
            language: 'Langue',
            login_title: 'Connexion à VybeFlow', login_btn: 'Se connecter', forgot_password: 'Mot de passe oublié ?', need_account: 'Besoin d’un compte ?', sign_up_here: 'Inscris-toi ici',
            signup_title: 'Inscription à VybeFlow', create_account: 'Créer un compte', already_have: 'Déjà un compte ?', login_here: 'Connecte-toi ici',
            create_new_password: 'Créer un nouveau mot de passe', update_password: 'Mettre à jour le mot de passe', back_to: 'Retour à',
            regular: 'Standard', professional: 'Professionnel',
            strength_start: 'Commence à saisir pour vérifier la robustesse.',
            strength_tip: 'Utilise 12+ caractères, majuscules, minuscules, chiffres et symboles.',
            suggestion: 'Suggestion',
            email_or_username: 'E-mail ou nom d’utilisateur', password: 'Mot de passe', username: 'Nom d’utilisateur', email: 'E-mail',
            new_password: 'Nouveau mot de passe', confirm_password: 'Confirmer le mot de passe'
        },
        pt: {
            language: 'Idioma',
            login_title: 'Entrar no VybeFlow', login_btn: 'Entrar', forgot_password: 'Esqueceu a senha?', need_account: 'Precisa de conta?', sign_up_here: 'Cadastre-se aqui',
            signup_title: 'Criar conta no VybeFlow', create_account: 'Criar conta', already_have: 'Já tem conta?', login_here: 'Entre aqui',
            create_new_password: 'Criar nova senha', update_password: 'Atualizar senha', back_to: 'Voltar para',
            regular: 'Regular', professional: 'Profissional',
            strength_start: 'Digite para verificar a força da senha.',
            strength_tip: 'Use 12+ caracteres, maiúsculas, minúsculas, números e símbolos.',
            suggestion: 'Sugestão',
            email_or_username: 'E-mail ou usuário', password: 'Senha', username: 'Usuário', email: 'E-mail',
            new_password: 'Nova senha', confirm_password: 'Confirmar senha'
        },
        sw: {
            language: 'Lugha',
            login_title: 'Ingia VybeFlow', login_btn: 'Ingia', forgot_password: 'Umesahau nenosiri?', need_account: 'Unahitaji akaunti?', sign_up_here: 'Jisajili hapa',
            signup_title: 'Jisajili kwenye VybeFlow', create_account: 'Fungua Akaunti', already_have: 'Una akaunti tayari?', login_here: 'Ingia hapa',
            create_new_password: 'Tengeneza nenosiri jipya', update_password: 'Sasisha nenosiri', back_to: 'Rudi kwa',
            regular: 'Kawaida', professional: 'Kitaalamu',
            strength_start: 'Anza kuandika kuangalia uimara wa nenosiri.',
            strength_tip: 'Tumia herufi 12+, kubwa, ndogo, namba na alama.',
            suggestion: 'Pendekezo',
            email_or_username: 'Barua pepe au jina', password: 'Nenosiri', username: 'Jina la mtumiaji', email: 'Barua pepe',
            new_password: 'Nenosiri jipya', confirm_password: 'Thibitisha nenosiri'
        }
    };

    function evaluatePassword(password) {
        let score = 0;
        if (!password) return { score: 0, label: 'Empty', advice: 'Enter a password.' };
        if (password.length >= 8) score += 1;
        if (password.length >= 12) score += 1;
        if (/[A-Z]/.test(password) && /[a-z]/.test(password)) score += 1;
        if (/\d/.test(password)) score += 1;
        if (/[^A-Za-z0-9]/.test(password)) score += 1;

        if (score <= 1) return { score: 1, label: 'Weak', advice: 'Add length and more character variety.' };
        if (score === 2 || score === 3) return { score: 2, label: 'Fair', advice: 'Add symbols, numbers, and more length.' };
        if (score === 4) return { score: 3, label: 'Good', advice: 'Almost there. Increase length to 12+.' };
        return { score: 4, label: 'Strong', advice: 'Great. Keep this password unique.' };
    }

    function bindStrengthMeter(container) {
        const inputId = container.getAttribute('data-strength-for');
        const input = document.getElementById(inputId);
        if (!input) return;

        const bars = Array.from(container.querySelectorAll('.strength-bars span'));
        const text = container.querySelector('.strength-text');
        const hint = container.querySelector('.strength-hint');

        function update() {
            const result = evaluatePassword(input.value || '');
            bars.forEach((bar, idx) => {
                bar.classList.remove('active', 'weak', 'fair', 'good', 'strong');
                if (idx < result.score) {
                    bar.classList.add('active');
                    if (result.label === 'Weak') bar.classList.add('weak');
                    if (result.label === 'Fair') bar.classList.add('fair');
                    if (result.label === 'Good') bar.classList.add('good');
                    if (result.label === 'Strong') bar.classList.add('strong');
                }
            });
            if (text) text.textContent = `Strength: ${result.label}`;
            if (hint) hint.textContent = `Tip: ${result.advice}`;
        }

        input.addEventListener('input', update);
        update();
    }

    function bindPasswordSuggestion(container) {
        const inputId = container.getAttribute('data-suggestion-for');
        const input = document.getElementById(inputId);
        if (!input) return;

        function update() {
            const length = (input.value || '').length;
            let tip = PASSWORD_SUGGESTIONS[0];
            if (length >= 6 && length < 12) tip = PASSWORD_SUGGESTIONS[1];
            if (length >= 12) tip = PASSWORD_SUGGESTIONS[2];
            if (length >= 16) tip = PASSWORD_SUGGESTIONS[3];

            const selectedLang = window.localStorage.getItem(LANGUAGE_KEY) || 'en';
            const dict = I18N[selectedLang] || I18N.en;
            const label = dict.suggestion || I18N.en.suggestion;
            container.textContent = label + ': ' + tip;
        }

        input.addEventListener('input', update);
        update();
    }

    function applyLanguage(langCode) {
        const dict = I18N[langCode] || I18N.en;
        document.documentElement.lang = langCode;
        window.localStorage.setItem(LANGUAGE_KEY, langCode);

        document.querySelectorAll('.lang-chip-btn').forEach(function (button) {
            button.classList.toggle('chip-active', button.getAttribute('data-lang') === langCode);
        });

        document.querySelectorAll('[data-i18n]').forEach(function (node) {
            const key = node.getAttribute('data-i18n');
            if (dict[key]) node.textContent = dict[key];
        });

        document.querySelectorAll('[data-i18n-placeholder]').forEach(function (node) {
            const key = node.getAttribute('data-i18n-placeholder');
            if (dict[key]) node.setAttribute('placeholder', dict[key]);
        });

        document.querySelectorAll('.password-suggestion[data-suggestion-for]').forEach(function (node) {
            const event = new Event('input');
            const inputId = node.getAttribute('data-suggestion-for');
            const input = document.getElementById(inputId);
            if (input) input.dispatchEvent(event);
        });
    }

    function bindLanguageButtons() {
        const buttons = document.querySelectorAll('.lang-chip-btn');
        if (!buttons.length) return;

        buttons.forEach(function (button) {
            button.addEventListener('click', function () {
                applyLanguage(button.getAttribute('data-lang') || 'en');
            });
        });

        applyLanguage(window.localStorage.getItem(LANGUAGE_KEY) || 'en');
    }

    function loadRememberedUsers() {
        try {
            const raw = window.localStorage.getItem(REMEMBERED_USERS_KEY);
            const parsed = raw ? JSON.parse(raw) : [];
            return Array.isArray(parsed) ? parsed : [];
        } catch (error) {
            return [];
        }
    }

    function saveRememberedUsers(users) {
        const cleaned = Array.from(new Set((users || []).map(function (user) {
            return String(user || '').trim();
        }).filter(Boolean))).slice(0, 50);
        window.localStorage.setItem(REMEMBERED_USERS_KEY, JSON.stringify(cleaned));
    }

    function addRememberedUser(userIdentifier) {
        const value = String(userIdentifier || '').trim();
        if (!value) return;
        const users = loadRememberedUsers();
        users.unshift(value);
        saveRememberedUsers(users);
    }

    function bindRememberedUsers() {
        const users = loadRememberedUsers();
        const datalist = document.getElementById('remembered-users');
        if (datalist) {
            datalist.innerHTML = '';
            users.forEach(function (user) {
                const option = document.createElement('option');
                option.value = user;
                datalist.appendChild(option);
            });

            const loginField = document.getElementById('login-identifier');
            if (loginField && !loginField.value && users.length) {
                loginField.value = users[0];
            }
        }

        const loginForm = document.querySelector('form[data-remember-users="login"]');
        if (loginForm) {
            loginForm.addEventListener('submit', function () {
                const identifierInput = loginForm.querySelector('input[name="username"]');
                if (identifierInput && identifierInput.value) {
                    addRememberedUser(identifierInput.value);
                }
            });
        }

        const registerForm = document.querySelector('form[data-remember-users="register"]');
        if (registerForm) {
            registerForm.addEventListener('submit', function () {
                const usernameInput = registerForm.querySelector('input[name="username"]');
                const emailInput = registerForm.querySelector('input[name="email"]');
                if (usernameInput && usernameInput.value) {
                    addRememberedUser(usernameInput.value);
                }
                if (emailInput && emailInput.value) {
                    addRememberedUser(emailInput.value);
                }
            });
        }
    }

    document.querySelectorAll('.password-strength').forEach(bindStrengthMeter);
    document.querySelectorAll('.password-suggestion').forEach(bindPasswordSuggestion);
    bindLanguageButtons();
    bindRememberedUsers();
})();
