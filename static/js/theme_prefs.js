(function () {
    const THEME_KEY = 'vybe_theme_vars';
    const RETRO_KEY = 'vybe_feed_retro_2011';
    const USER_THEMES = 'vybe_user_themes';
    const UI_KEY = 'vybe_theme_ui_open';

    const PRESETS = {
        orange_gloss: {
            '--bg': '#0a0810', '--line': 'rgba(255,173,117,.20)', '--brand1': '#ff9a3d', '--brand2': '#ff6a00', '--brand3': '#ff4800'
        },
        midnight_gangsta: {
            '--bg': '#09070f', '--line': 'rgba(169,122,255,.28)', '--brand1': '#7a2cff', '--brand2': '#a855f7', '--brand3': '#22d3ee'
        },
        neon_street: {
            '--bg': '#070b12', '--line': 'rgba(72,255,206,.28)', '--brand1': '#00ffa3', '--brand2': '#0ea5e9', '--brand3': '#8b5cf6'
        },
        gold_ice: {
            '--bg': '#0c0d12', '--line': 'rgba(255,209,102,.30)', '--brand1': '#ffd166', '--brand2': '#f59e0b', '--brand3': '#93c5fd'
        },
        blackout_fire: {
            '--bg': '#050507', '--line': 'rgba(255,120,120,.24)', '--brand1': '#ff4d6d', '--brand2': '#ff6a00', '--brand3': '#fb7185'
        },
        facebook_2011_blue: {
            '--bg': '#e9ebee', '--line': 'rgba(59,89,152,.28)', '--brand1': '#3b5998', '--brand2': '#4c70ba', '--brand3': '#8b9dc3'
        },
        sunset_orange_glass: {
            '--bg': '#2a1303', '--line': 'rgba(255,154,61,.36)', '--brand1': '#ffb15f', '--brand2': '#ff7a1f', '--brand3': '#ff4f00'
        },
        ocean_breeze: {
            '--bg': '#071421', '--line': 'rgba(103,232,249,.34)', '--brand1': '#22d3ee', '--brand2': '#0ea5e9', '--brand3': '#38bdf8'
        },
        grape_night: {
            '--bg': '#11091f', '--line': 'rgba(196,181,253,.32)', '--brand1': '#8b5cf6', '--brand2': '#a855f7', '--brand3': '#c084fc'
        },
        mint_frost: {
            '--bg': '#081611', '--line': 'rgba(110,231,183,.34)', '--brand1': '#34d399', '--brand2': '#10b981', '--brand3': '#6ee7b7'
        },
        ruby_pulse: {
            '--bg': '#18090b', '--line': 'rgba(251,113,133,.34)', '--brand1': '#fb7185', '--brand2': '#f43f5e', '--brand3': '#ef4444'
        },
        amber_smoke: {
            '--bg': '#1a1208', '--line': 'rgba(251,191,36,.34)', '--brand1': '#fbbf24', '--brand2': '#f59e0b', '--brand3': '#f97316'
        },
        cyber_lime: {
            '--bg': '#091109', '--line': 'rgba(163,230,53,.34)', '--brand1': '#a3e635', '--brand2': '#84cc16', '--brand3': '#bef264'
        },
        molten_sunset: {
            '--bg': '#1a0d07', '--line': 'rgba(255,144,80,.32)', '--brand1': '#ffb36b', '--brand2': '#ff7a1f', '--brand3': '#ff4a00'
        },
        arctic_midnight: {
            '--bg': '#07101a', '--line': 'rgba(148,210,255,.30)', '--brand1': '#7dd3fc', '--brand2': '#38bdf8', '--brand3': '#0ea5e9'
        },
        electric_orchid: {
            '--bg': '#130a1f', '--line': 'rgba(196,132,252,.32)', '--brand1': '#c084fc', '--brand2': '#a855f7', '--brand3': '#7c3aed'
        },
        tropical_heat: {
            '--bg': '#10110a', '--line': 'rgba(253,224,71,.30)', '--brand1': '#fde047', '--brand2': '#facc15', '--brand3': '#f97316'
        },
        deep_crimson: {
            '--bg': '#17090d', '--line': 'rgba(252,165,165,.30)', '--brand1': '#fb7185', '--brand2': '#ef4444', '--brand3': '#be123c'
        },
        graphite_glow: {
            '--bg': '#0a0a0c', '--line': 'rgba(212,212,216,.28)', '--brand1': '#d4d4d8', '--brand2': '#a1a1aa', '--brand3': '#71717a'
        },
        mint_night_drive: {
            '--bg': '#07120f', '--line': 'rgba(134,239,172,.30)', '--brand1': '#86efac', '--brand2': '#34d399', '--brand3': '#10b981'
        },
        solar_flare: {
            '--bg': '#190f06', '--line': 'rgba(251,191,36,.32)', '--brand1': '#fcd34d', '--brand2': '#f59e0b', '--brand3': '#ea580c'
        },
        neon_ember: {
            '--bg': '#0b0f0d', '--line': 'rgba(74,222,128,.30)', '--brand1': '#4ade80', '--brand2': '#22c55e', '--brand3': '#f97316'
        },
        vybeflow_transparent: {
            '--bg': 'rgba(10,8,16,.55)', '--line': 'rgba(255,173,117,.12)', '--brand1': '#ff9a3d', '--brand2': '#ff6a00', '--brand3': '#ff4800'
        },
        vybeflow_glossy: {
            '--bg': '#0e0a18', '--line': 'rgba(255,200,140,.30)', '--brand1': '#ffb86c', '--brand2': '#ff9a3d', '--brand3': '#ff6a00'
        },
        /* ── Pastel & Soft ── */
        pastel_dream: {
            '--bg': '#1a161e', '--line': 'rgba(253,186,219,.28)', '--brand1': '#f9a8d4', '--brand2': '#c084fc', '--brand3': '#93c5fd'
        },
        cotton_candy: {
            '--bg': '#170e18', '--line': 'rgba(244,114,182,.30)', '--brand1': '#f472b6', '--brand2': '#e879f9', '--brand3': '#c4b5fd'
        },
        lavender_haze: {
            '--bg': '#120e1a', '--line': 'rgba(196,181,253,.30)', '--brand1': '#c4b5fd', '--brand2': '#a78bfa', '--brand3': '#818cf8'
        },
        peach_sorbet: {
            '--bg': '#1a1310', '--line': 'rgba(253,186,116,.34)', '--brand1': '#fdba74', '--brand2': '#fb923c', '--brand3': '#f9a8d4'
        },
        baby_blue: {
            '--bg': '#0b111a', '--line': 'rgba(147,197,253,.30)', '--brand1': '#93c5fd', '--brand2': '#60a5fa', '--brand3': '#a5b4fc'
        },
        /* ── Dark Mode Variants ── */
        abyss_black: {
            '--bg': '#020204', '--line': 'rgba(100,100,120,.20)', '--brand1': '#64748b', '--brand2': '#475569', '--brand3': '#334155'
        },
        shadow_carbon: {
            '--bg': '#0a0a0b', '--line': 'rgba(148,163,184,.22)', '--brand1': '#94a3b8', '--brand2': '#64748b', '--brand3': '#475569'
        },
        void_neon: {
            '--bg': '#010108', '--line': 'rgba(99,255,174,.24)', '--brand1': '#63ffae', '--brand2': '#00d4ff', '--brand3': '#ff006e'
        },
        dark_cherry: {
            '--bg': '#0c0509', '--line': 'rgba(190,18,60,.34)', '--brand1': '#e11d48', '--brand2': '#be123c', '--brand3': '#f43f5e'
        },
        dark_emerald: {
            '--bg': '#030c08', '--line': 'rgba(16,185,129,.30)', '--brand1': '#10b981', '--brand2': '#059669', '--brand3': '#047857'
        },
        /* ── Gradient & Neon ── */
        synthwave: {
            '--bg': '#0c0017', '--line': 'rgba(236,72,153,.34)', '--brand1': '#ec4899', '--brand2': '#8b5cf6', '--brand3': '#06b6d4'
        },
        vaporwave: {
            '--bg': '#14081a', '--line': 'rgba(232,121,249,.30)', '--brand1': '#e879f9', '--brand2': '#67e8f9', '--brand3': '#f9a8d4'
        },
        aurora_borealis: {
            '--bg': '#040d12', '--line': 'rgba(45,212,191,.30)', '--brand1': '#2dd4bf', '--brand2': '#38bdf8', '--brand3': '#a78bfa'
        },
        neon_tokyo: {
            '--bg': '#06020e', '--line': 'rgba(255,0,110,.30)', '--brand1': '#ff006e', '--brand2': '#8338ec', '--brand3': '#3a86ff'
        },
        laser_grid: {
            '--bg': '#060812', '--line': 'rgba(56,189,248,.24)', '--brand1': '#38bdf8', '--brand2': '#818cf8', '--brand3': '#e879f9'
        },
        /* ── Warm & Golden ── */
        warm_copper: {
            '--bg': '#110b08', '--line': 'rgba(194,120,73,.32)', '--brand1': '#c27849', '--brand2': '#a16635', '--brand3': '#e8a065'
        },
        gold_rush: {
            '--bg': '#0e0c06', '--line': 'rgba(253,224,71,.34)', '--brand1': '#fde047', '--brand2': '#eab308', '--brand3': '#ca8a04'
        },
        campfire: {
            '--bg': '#120a04', '--line': 'rgba(251,146,60,.32)', '--brand1': '#fb923c', '--brand2': '#ea580c', '--brand3': '#fbbf24'
        },
        /* ── Seasonal ── */
        autumn_leaves: {
            '--bg': '#130b06', '--line': 'rgba(234,88,12,.30)', '--brand1': '#ea580c', '--brand2': '#dc2626', '--brand3': '#fbbf24'
        },
        winter_frost: {
            '--bg': '#0a0e14', '--line': 'rgba(186,230,253,.28)', '--brand1': '#bae6fd', '--brand2': '#7dd3fc', '--brand3': '#e0e7ff'
        },
        spring_bloom: {
            '--bg': '#0d100b', '--line': 'rgba(134,239,172,.28)', '--brand1': '#86efac', '--brand2': '#f9a8d4', '--brand3': '#fde047'
        },
        summer_sunset: {
            '--bg': '#140b08', '--line': 'rgba(253,164,175,.28)', '--brand1': '#fda4af', '--brand2': '#fb923c', '--brand3': '#fde047'
        },
        /* ── Monochrome ── */
        pure_white: {
            '--bg': '#f0f0f0', '--line': 'rgba(30,30,30,.12)', '--brand1': '#1e293b', '--brand2': '#334155', '--brand3': '#0f172a'
        },
        newspaper: {
            '--bg': '#e8e2d8', '--line': 'rgba(30,30,30,.16)', '--brand1': '#292524', '--brand2': '#44403c', '--brand3': '#78716c'
        },
        /* ── Special ── */
        vybeflow_pride: {
            '--bg': '#0a0818', '--line': 'rgba(244,114,182,.30)', '--brand1': '#f472b6', '--brand2': '#facc15', '--brand3': '#34d399'
        },
        matrix_code: {
            '--bg': '#010701', '--line': 'rgba(0,255,65,.24)', '--brand1': '#00ff41', '--brand2': '#008f11', '--brand3': '#003b00'
        }
    };

    const DEFAULT_EXTRAS = {
        '--vf-glow': '0.18',
        '--vf-blur': '14',
        '--vf-radius': '18',
        '--vf-contrast': '1.05',
        '--vf-noise': '0.06',
        '--vf-vibe': 'street'
    };

    function applyVars(vars) {
        if (!vars) return;
        Object.keys(vars).forEach((key) => {
            document.documentElement.style.setProperty(key, vars[key]);
        });
        applyVisualFX();
    }

    function saveVars(vars) {
        localStorage.setItem(THEME_KEY, JSON.stringify(vars));
        applyVars(vars);
    }

    function loadVars() {
        try {
            const raw = localStorage.getItem(THEME_KEY);
            if (!raw) return null;
            return JSON.parse(raw);
        } catch {
            return null;
        }
    }

    function setRetro(enabled) {
        if (!document.body) return;
        document.body.classList.toggle('retro-2011', !!enabled);
        localStorage.setItem(RETRO_KEY, enabled ? '1' : '0');
    }

    function loadRetro() {
        return localStorage.getItem(RETRO_KEY) === '1';
    }

    function getUserThemes() {
        try {
            return JSON.parse(localStorage.getItem(USER_THEMES) || '[]');
        } catch {
            return [];
        }
    }

    function setUserThemes(list) {
        localStorage.setItem(USER_THEMES, JSON.stringify(list || []));
    }

    function sanitizeThemeName(name) {
        return (name || '').trim().slice(0, 32) || 'My Theme';
    }

    function getCurrentVars() {
        const saved = loadVars() || {};
        return { ...DEFAULT_EXTRAS, ...saved };
    }

    function saveAsUserTheme(name) {
        const list = getUserThemes();
        const now = new Date().toISOString();
        const vars = getCurrentVars();
        const theme = {
            id: cryptoId(),
            name: sanitizeThemeName(name),
            vars,
            created_at: now
        };
        list.unshift(theme);
        setUserThemes(list.slice(0, 30));
        return theme;
    }

    function deleteUserTheme(id) {
        const list = getUserThemes().filter((t) => t.id !== id);
        setUserThemes(list);
    }

    function applyUserTheme(id) {
        const theme = getUserThemes().find((t) => t.id === id);
        if (!theme) return;
        saveVars(theme.vars);
    }

    function exportTheme() {
        const vars = getCurrentVars();
        const payload = btoa(unescape(encodeURIComponent(JSON.stringify(vars))));
        return `VYBE_THEME::${payload}`;
    }

    function importTheme(code) {
        try {
            const trimmed = (code || '').trim();
            if (!trimmed.startsWith('VYBE_THEME::')) return false;
            const payload = trimmed.split('VYBE_THEME::')[1];
            const json = decodeURIComponent(escape(atob(payload)));
            const vars = JSON.parse(json);
            saveVars(vars);
            return true;
        } catch {
            return false;
        }
    }

    function randomizeTheme() {
        const keys = Object.keys(PRESETS);
        const pick = PRESETS[keys[Math.floor(Math.random() * keys.length)]];
        const extras = {
            '--vf-glow': (Math.random() * 0.35 + 0.12).toFixed(2),
            '--vf-blur': String(Math.floor(Math.random() * 10 + 10)),
            '--vf-radius': String(Math.floor(Math.random() * 12 + 14)),
            '--vf-contrast': (Math.random() * 0.15 + 1.00).toFixed(2),
            '--vf-noise': (Math.random() * 0.10 + 0.04).toFixed(2),
            '--vf-vibe': ['street', 'clean', 'retro', 'luxe'][Math.floor(Math.random() * 4)]
        };
        saveVars({ ...extras, ...pick });
    }

    function applyVisualFX() {
        const root = getComputedStyle(document.documentElement);
        const glow = parseFloat(root.getPropertyValue('--vf-glow')) || 0.18;
        const blur = parseInt(root.getPropertyValue('--vf-blur'), 10) || 14;
        const contrast = parseFloat(root.getPropertyValue('--vf-contrast')) || 1.05;
        const noise = parseFloat(root.getPropertyValue('--vf-noise')) || 0.06;

        let noiseEl = document.getElementById('vf-noise');
        if (!noiseEl) {
            noiseEl = document.createElement('div');
            noiseEl.id = 'vf-noise';
            noiseEl.style.cssText = `
                pointer-events:none; position:fixed; inset:0; z-index:0;
                opacity:${noise}; mix-blend-mode: overlay;
                background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='260' height='260'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.8' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='260' height='260' filter='url(%23n)' opacity='.4'/%3E%3C/svg%3E");
            `;
            document.body.appendChild(noiseEl);
        } else {
            noiseEl.style.opacity = String(noise);
        }

        document.documentElement.style.filter = `contrast(${contrast})`;
        document.documentElement.style.setProperty('--vf-glow-alpha', String(glow));
        document.documentElement.style.setProperty('--vf-blur-px', String(blur));
    }

    function mountUI() {
        if (document.body && (document.body.classList.contains('login-page') || document.body.classList.contains('register-page'))) {
            const existing = document.getElementById('vf-theme-garage');
            if (existing) existing.remove();
            return;
        }
        if (document.getElementById('vf-theme-garage')) return;

        const wrap = document.createElement('div');
        wrap.id = 'vf-theme-garage';
        wrap.innerHTML = `
            <style>
                #vf-theme-garage{ position:fixed; right:16px; bottom:16px; z-index:9999; font-family:system-ui, -apple-system, Segoe UI, Roboto, Arial; }
                .vf-g-btn{ width:56px; height:56px; border-radius:18px; cursor:pointer; border:1px solid rgba(255,255,255,.14); background: linear-gradient(135deg, var(--brand1), var(--brand2), var(--brand3)); color:#0b0f17; font-weight:900; box-shadow: 0 18px 40px rgba(0,0,0,.45); }
                .vf-g-panel{ width: 340px; max-height: 72vh; overflow:auto; margin-bottom: 10px; border-radius: 20px; border: 1px solid rgba(255,255,255,.14); background: rgba(10,10,14,.78); backdrop-filter: blur(calc(var(--vf-blur, 14) * 1px)); box-shadow: 0 18px 55px rgba(0,0,0,.55); color: rgba(255,255,255,.92); display:none; }
                .vf-g-panel.open{ display:block; }
                .vf-g-head{ padding: 12px 12px 10px; display:flex; align-items:center; justify-content:space-between; gap:10px; border-bottom: 1px solid rgba(255,255,255,.10); }
                .vf-g-title{ font-weight: 900; letter-spacing:.2px; }
                .vf-g-sub{ font-size: 12px; color: rgba(255,255,255,.65); margin-top: 2px; }
                .vf-g-x{ width:36px; height:36px; border-radius:14px; cursor:pointer; border:1px solid rgba(255,255,255,.14); background: rgba(255,255,255,.06); color: rgba(255,255,255,.92); }
                .vf-g-body{ padding: 12px; }
                .vf-row{ display:flex; gap:10px; }
                .vf-pill{ flex:1; height: 40px; border-radius: 14px; border: 1px solid rgba(255,255,255,.14); background: rgba(255,255,255,.06); color: rgba(255,255,255,.92); cursor:pointer; font-weight: 800; }
                .vf-pill:hover{ transform: translateY(-1px); }
                .vf-grid{ display:grid; grid-template-columns: 1fr 1fr; gap:10px; margin-top: 10px; }
                .vf-card{ border-radius: 16px; border:1px solid rgba(255,255,255,.12); background: rgba(255,255,255,.05); padding: 10px; cursor:pointer; transition:.15s ease; }
                .vf-card:hover{ transform: translateY(-2px); border-color: rgba(255,255,255,.20); }
                .vf-swatch{ height: 30px; border-radius: 12px; background: linear-gradient(135deg, var(--brand1), var(--brand2), var(--brand3)); box-shadow: 0 14px 28px rgba(0,0,0,.35); margin-bottom: 8px; }
                .vf-label{ font-weight: 900; font-size: 13px; }
                .vf-small{ font-size: 12px; color: rgba(255,255,255,.62); margin-top: 2px; }
                .vf-divider{ height:1px; background: rgba(255,255,255,.10); margin: 12px 0; }
                .vf-field{ display:flex; flex-direction:column; gap:6px; margin-top: 10px; }
                .vf-field label{ font-size:12px; color: rgba(255,255,255,.70); }
                .vf-field input[type="range"]{ width:100%; }
                .vf-field input[type="text"], .vf-field textarea{ border-radius: 14px; border:1px solid rgba(255,255,255,.12); background: rgba(255,255,255,.06); color: rgba(255,255,255,.92); padding: 10px 10px; outline:none; }
                .vf-field textarea{ min-height: 64px; resize: vertical; }
                .vf-mini{ display:flex; gap:8px; align-items:center; justify-content:space-between; padding: 10px; border-radius: 14px; border:1px solid rgba(255,255,255,.10); background: rgba(255,255,255,.04); margin-top: 10px; }
                .vf-mini button{ height: 34px; padding:0 10px; border-radius: 12px; cursor:pointer; border:1px solid rgba(255,255,255,.12); background: rgba(255,255,255,.06); color: rgba(255,255,255,.92); font-weight: 800; }
                .vf-mini button:hover{ transform: translateY(-1px); }
                .vf-tag{ display:inline-flex; align-items:center; gap:6px; padding: 6px 10px; border-radius: 999px; border: 1px solid rgba(255,255,255,.14); background: rgba(255,255,255,.06); font-size: 12px; font-weight: 900; }
                .vf-danger{ border-color: rgba(255,90,90,.28)!important; }
            </style>

            <div class="vf-g-panel" id="vf-g-panel">
                <div class="vf-g-head">
                    <div>
                        <div class="vf-g-title">Theme Garage 🔥</div>
                        <div class="vf-g-sub">Pick a preset, tweak the glow, save & share your “vybe”.</div>
                    </div>
                    <button class="vf-g-x" id="vf-g-close" title="Close">✕</button>
                </div>

                <div class="vf-g-body">
                    <div class="vf-row">
                        <button class="vf-pill" id="vf-random">🎲 Random</button>
                        <button class="vf-pill" id="vf-reset">↺ Reset</button>
                    </div>

                    <div class="vf-grid" id="vf-preset-grid"></div>

                    <div class="vf-divider"></div>

                    <div class="vf-tag">AI Theme Designer</div>
                    <div class="vf-field">
                        <textarea id="vf-ai-prompt" placeholder="Describe your vibe (e.g. cyberpunk sunset with warm neon glow)"></textarea>
                        <button class="vf-pill" id="vf-ai-generate">🤖 Generate Theme</button>
                    </div>

                    <div class="vf-divider"></div>

                    <div class="vf-tag">Extra Sauce (more fun than FB/IG)</div>

                    <div class="vf-field">
                        <label>Glow (beat aura)</label>
                        <input id="vf-glow" type="range" min="0" max="0.60" step="0.01" />
                    </div>

                    <div class="vf-field">
                        <label>Blur (glass)</label>
                        <input id="vf-blur" type="range" min="6" max="22" step="1" />
                    </div>

                    <div class="vf-field">
                        <label>Radius (roundness)</label>
                        <input id="vf-radius" type="range" min="10" max="26" step="1" />
                    </div>

                    <div class="vf-field">
                        <label>Contrast (pop)</label>
                        <input id="vf-contrast" type="range" min="0.90" max="1.20" step="0.01" />
                    </div>

                    <div class="vf-field">
                        <label>Noise (film grit)</label>
                        <input id="vf-noise" type="range" min="0" max="0.18" step="0.01" />
                    </div>

                    <div class="vf-mini">
                        <div>
                            <div style="font-weight:900;">Retro 2011 feed</div>
                            <div style="font-size:12px;color:rgba(255,255,255,.65);">Only affects feed page</div>
                        </div>
                        <button id="vf-retro">Toggle</button>
                    </div>

                    <div class="vf-divider"></div>

                    <div class="vf-field">
                        <label>Save this theme as</label>
                        <input id="vf-theme-name" type="text" placeholder="e.g. Orange Hustle" />
                        <button class="vf-pill" id="vf-save" style="margin-top:8px;">💾 Save</button>
                    </div>

                    <div class="vf-divider"></div>

                    <div class="vf-tag">Share your theme code</div>
                    <div class="vf-field">
                        <textarea id="vf-share" readonly></textarea>
                        <div class="vf-row">
                            <button class="vf-pill" id="vf-copy">📋 Copy</button>
                            <button class="vf-pill" id="vf-refresh">🔄 Refresh Code</button>
                        </div>
                    </div>

                    <div class="vf-divider"></div>

                    <div class="vf-tag">Import a theme code</div>
                    <div class="vf-field">
                        <textarea id="vf-import" placeholder="Paste VYBE_THEME::... here"></textarea>
                        <button class="vf-pill" id="vf-import-btn">⬇️ Import</button>
                    </div>

                    <div class="vf-divider"></div>

                    <div class="vf-tag">Your saved themes</div>
                    <div id="vf-user-themes"></div>
                </div>
            </div>

            <button class="vf-g-btn" id="vf-g-open" title="Themes">VF</button>
        `;

        document.body.appendChild(wrap);

        const panel = document.getElementById('vf-g-panel');
        const openBtn = document.getElementById('vf-g-open');
        const closeBtn = document.getElementById('vf-g-close');

        function setOpen(isOpen) {
            panel.classList.toggle('open', !!isOpen);
            localStorage.setItem(UI_KEY, isOpen ? '1' : '0');
        }

        openBtn.addEventListener('click', () => setOpen(!panel.classList.contains('open')));
        closeBtn.addEventListener('click', () => setOpen(false));

        if (localStorage.getItem(UI_KEY) === '1') setOpen(true);

        const grid = document.getElementById('vf-preset-grid');
        grid.innerHTML = Object.keys(PRESETS).map((key) => {
            const label = key.replace(/_/g, ' ');
            return `
                <div class="vf-card" data-preset="${key}">
                    <div class="vf-swatch" style="--brand1:${PRESETS[key]['--brand1']};--brand2:${PRESETS[key]['--brand2']};--brand3:${PRESETS[key]['--brand3']};"></div>
                    <div class="vf-label">${label}</div>
                    <div class="vf-small">tap to apply</div>
                </div>
            `;
        }).join('');

        grid.addEventListener('click', (e) => {
            const card = e.target.closest('.vf-card');
            if (!card) return;
            const presetKey = card.getAttribute('data-preset');
            const current = getCurrentVars();
            saveVars({ ...current, ...PRESETS[presetKey] });
            refreshShare();
        });

        const glowEl = document.getElementById('vf-glow');
        const blurEl = document.getElementById('vf-blur');
        const radEl = document.getElementById('vf-radius');
        const conEl = document.getElementById('vf-contrast');
        const noiEl = document.getElementById('vf-noise');

        function syncSliders() {
            const vars = getCurrentVars();
            glowEl.value = parseFloat(vars['--vf-glow'] ?? DEFAULT_EXTRAS['--vf-glow']);
            blurEl.value = parseInt(vars['--vf-blur'] ?? DEFAULT_EXTRAS['--vf-blur'], 10);
            radEl.value = parseInt(vars['--vf-radius'] ?? DEFAULT_EXTRAS['--vf-radius'], 10);
            conEl.value = parseFloat(vars['--vf-contrast'] ?? DEFAULT_EXTRAS['--vf-contrast']);
            noiEl.value = parseFloat(vars['--vf-noise'] ?? DEFAULT_EXTRAS['--vf-noise']);
        }

        function onSliderChange() {
            const vars = getCurrentVars();
            vars['--vf-glow'] = String(glowEl.value);
            vars['--vf-blur'] = String(blurEl.value);
            vars['--vf-radius'] = String(radEl.value);
            vars['--vf-contrast'] = String(conEl.value);
            vars['--vf-noise'] = String(noiEl.value);
            saveVars(vars);
            refreshShare();
        }

        [glowEl, blurEl, radEl, conEl, noiEl].forEach((el) => el.addEventListener('input', onSliderChange));

        document.getElementById('vf-random').addEventListener('click', () => {
            randomizeTheme();
            syncSliders();
            refreshShare();
        });

        document.getElementById('vf-reset').addEventListener('click', () => {
            const base = { ...DEFAULT_EXTRAS, ...PRESETS.orange_gloss };
            saveVars(base);
            syncSliders();
            refreshShare();
        });

        document.getElementById('vf-retro').addEventListener('click', () => {
            setRetro(!loadRetro());
        });

        function hashText(text) {
            let h = 0;
            const value = String(text || 'vybeflow');
            for (let i = 0; i < value.length; i += 1) {
                h = (h << 5) - h + value.charCodeAt(i);
                h |= 0;
            }
            return Math.abs(h);
        }

        function hslToHex(h, s, l) {
            const sat = s / 100;
            const lit = l / 100;
            const chroma = (1 - Math.abs(2 * lit - 1)) * sat;
            const x = chroma * (1 - Math.abs((h / 60) % 2 - 1));
            const m = lit - chroma / 2;
            let r = 0, g = 0, b = 0;

            if (h < 60) { r = chroma; g = x; b = 0; }
            else if (h < 120) { r = x; g = chroma; b = 0; }
            else if (h < 180) { r = 0; g = chroma; b = x; }
            else if (h < 240) { r = 0; g = x; b = chroma; }
            else if (h < 300) { r = x; g = 0; b = chroma; }
            else { r = chroma; g = 0; b = x; }

            const toHex = (v) => Math.round((v + m) * 255).toString(16).padStart(2, '0');
            return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
        }

        function generateThemeFromPrompt(prompt) {
            const p = String(prompt || '').toLowerCase();
            const seed = hashText(p || 'orange gloss');
            let hue = seed % 360;
            if (p.includes('orange') || p.includes('sunset') || p.includes('warm')) hue = 24;
            if (p.includes('blue') || p.includes('ocean') || p.includes('ice')) hue = 202;
            if (p.includes('purple') || p.includes('orchid') || p.includes('violet')) hue = 278;
            if (p.includes('green') || p.includes('mint') || p.includes('lime')) hue = 142;
            if (p.includes('red') || p.includes('crimson') || p.includes('ruby')) hue = 350;

            const bgHue = (hue + 8) % 360;
            const bg = hslToHex(bgHue, 38, 8);
            const b1 = hslToHex(hue, 92, 63);
            const b2 = hslToHex((hue + 18) % 360, 94, 54);
            const b3 = hslToHex((hue + 34) % 360, 90, 48);
            return {
                '--bg': bg,
                '--brand1': b1,
                '--brand2': b2,
                '--brand3': b3,
                '--line': 'rgba(255,173,117,.20)'
            };
        }

        const aiBtn = document.getElementById('vf-ai-generate');
        const aiPrompt = document.getElementById('vf-ai-prompt');
        if (aiBtn && aiPrompt) {
            aiBtn.addEventListener('click', () => {
                const vars = {
                    ...getCurrentVars(),
                    ...generateThemeFromPrompt(aiPrompt.value)
                };
                saveVars(vars);
                syncSliders();
                refreshShare();
                toast('AI vibe generated ✨');
            });
        }

        document.getElementById('vf-save').addEventListener('click', () => {
            const name = document.getElementById('vf-theme-name').value;
            saveAsUserTheme(name);
            document.getElementById('vf-theme-name').value = '';
            renderUserThemes();
        });

        const shareBox = document.getElementById('vf-share');
        function refreshShare() {
            shareBox.value = exportTheme();
        }

        document.getElementById('vf-refresh').addEventListener('click', refreshShare);
        document.getElementById('vf-copy').addEventListener('click', async () => {
            try {
                await navigator.clipboard.writeText(shareBox.value);
                toast('Copied. Send that code to your people 🔥');
            } catch {
                toast('Copy failed. Select text and copy manually.');
            }
        });

        document.getElementById('vf-import-btn').addEventListener('click', () => {
            const code = document.getElementById('vf-import').value;
            const ok = importTheme(code);
            if (ok) {
                syncSliders();
                refreshShare();
                toast('Theme imported. You just stole the drip 😤');
            } else {
                toast('Bad code. Needs to start with VYBE_THEME::');
            }
        });

        function renderUserThemes() {
            const host = document.getElementById('vf-user-themes');
            const list = getUserThemes();
            if (!list.length) {
                host.innerHTML = '<div class="vf-small" style="margin-top:10px;">No saved themes yet. Save one.</div>';
                return;
            }
            host.innerHTML = list.map((t) => `
                <div class="vf-mini">
                    <div style="min-width:0;">
                        <div style="font-weight:900; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${escapeHtml(t.name)}</div>
                        <div class="vf-small">${new Date(t.created_at).toLocaleString()}</div>
                    </div>
                    <div style="display:flex; gap:8px;">
                        <button data-act="apply" data-id="${t.id}">Use</button>
                        <button class="vf-danger" data-act="del" data-id="${t.id}">Del</button>
                    </div>
                </div>
            `).join('');
        }

        document.getElementById('vf-user-themes').addEventListener('click', (e) => {
            const btn = e.target.closest('button');
            if (!btn) return;
            const id = btn.getAttribute('data-id');
            const act = btn.getAttribute('data-act');
            if (act === 'apply') {
                applyUserTheme(id);
                syncSliders();
                refreshShare();
            }
            if (act === 'del') {
                deleteUserTheme(id);
                renderUserThemes();
            }
        });

        syncSliders();
        refreshShare();
        renderUserThemes();
    }

    function cryptoId() {
        return 't_' + Math.random().toString(16).slice(2) + Date.now().toString(16);
    }

    function escapeHtml(str) {
        return String(str || '')
            .replaceAll('&', '&amp;').replaceAll('<', '&lt;')
            .replaceAll('>', '&gt;').replaceAll('"', '&quot;')
            .replaceAll("'", '&#039;');
    }

    function toast(msg) {
        let el = document.getElementById('vf-toast');
        if (!el) {
            el = document.createElement('div');
            el.id = 'vf-toast';
            el.style.cssText = `
                position:fixed; left:50%; bottom:18px; transform:translateX(-50%);
                z-index:10000; padding:10px 14px; border-radius:999px;
                border:1px solid rgba(255,255,255,.14);
                background: rgba(10,10,14,.85); backdrop-filter: blur(12px);
                color: rgba(255,255,255,.92); font-weight: 800;
                box-shadow: 0 18px 40px rgba(0,0,0,.55);
                opacity:0; transition: .2s ease;
            `;
            document.body.appendChild(el);
        }
        el.textContent = msg;
        el.style.opacity = '1';
        clearTimeout(el._t);
        el._t = setTimeout(() => { el.style.opacity = '0'; }, 1700);
    }

    function init() {
        const saved = loadVars();
        if (saved) {
            applyVars(saved);
        } else {
            saveVars({ ...DEFAULT_EXTRAS, ...PRESETS.orange_gloss });
        }

        if (loadRetro()) setRetro(true);

        const showGarage = document.body && document.body.classList.contains('profile-page');
        if (!showGarage) {
            const existing = document.getElementById('vf-theme-garage');
            if (existing) existing.remove();
            return;
        }

        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => mountUI());
        } else {
            mountUI();
        }
    }

    window.VybeTheme = {
        presets: PRESETS,
        saveVars,
        applyVars,
        setRetro,
        loadRetro,
        exportTheme,
        importTheme,
        randomizeTheme,
        saveAsUserTheme,
        getUserThemes
    };

    init();
})();
