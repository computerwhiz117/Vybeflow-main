/* ═══════════════════════════════════════════════════════════
   ANIMATED 3D EMOJI SYSTEM — VybeFlow
   Generates SVG-based emojis with animated eyes/faces
   ═══════════════════════════════════════════════════════════ */

(function() {
  'use strict';

  /* ── Gradient definitions shared across all emojis ── */
  const SHARED_DEFS = `
    <defs>
      <radialGradient id="emojiYellow" cx="40%" cy="35%" r="60%">
        <stop offset="0%" stop-color="#FFE562"/>
        <stop offset="50%" stop-color="#FFD93D"/>
        <stop offset="100%" stop-color="#F5B800"/>
      </radialGradient>
      <radialGradient id="emojiRed" cx="40%" cy="35%" r="60%">
        <stop offset="0%" stop-color="#FF5555"/>
        <stop offset="50%" stop-color="#E82020"/>
        <stop offset="100%" stop-color="#CC0000"/>
      </radialGradient>
      <radialGradient id="emojiBlue" cx="40%" cy="35%" r="60%">
        <stop offset="0%" stop-color="#74C0FC"/>
        <stop offset="50%" stop-color="#4AA3DF"/>
        <stop offset="100%" stop-color="#2B8CD4"/>
      </radialGradient>
      <radialGradient id="emojiPink" cx="40%" cy="35%" r="60%">
        <stop offset="0%" stop-color="#FF9ED8"/>
        <stop offset="50%" stop-color="#FF6CB5"/>
        <stop offset="100%" stop-color="#E84393"/>
      </radialGradient>
      <radialGradient id="emojiGreen" cx="40%" cy="35%" r="60%">
        <stop offset="0%" stop-color="#7BED9F"/>
        <stop offset="50%" stop-color="#2ED573"/>
        <stop offset="100%" stop-color="#1CAD50"/>
      </radialGradient>
      <radialGradient id="emojiOrange" cx="40%" cy="35%" r="60%">
        <stop offset="0%" stop-color="#FFAD75"/>
        <stop offset="50%" stop-color="#FF8C42"/>
        <stop offset="100%" stop-color="#E66B00"/>
      </radialGradient>
      <radialGradient id="emojiFaceHighlight" cx="35%" cy="25%" r="50%">
        <stop offset="0%" stop-color="rgba(255,255,255,0.5)"/>
        <stop offset="100%" stop-color="rgba(255,255,255,0)"/>
      </radialGradient>
      <filter id="emojiShadow">
        <feDropShadow dx="0" dy="2" stdDeviation="2" flood-color="#00000033"/>
      </filter>
    </defs>
  `;

  /* ── Standard eye builder ── */
  function makeEyes(lx, ly, rx, ry, pupilSize, whiteW, whiteH) {
    pupilSize = pupilSize || 3.5;
    whiteW = whiteW || 5;
    whiteH = whiteH || 6;
    return `
      <g class="eye-group">
        <ellipse cx="${lx}" cy="${ly}" rx="${whiteW}" ry="${whiteH}" fill="white" stroke="#4a3728" stroke-width="0.3"/>
        <circle class="eye-pupil" cx="${lx}" cy="${ly+0.5}" r="${pupilSize}" fill="#3d2b1f"/>
        <circle cx="${lx-1.2}" cy="${ly-1.5}" r="1.5" fill="white" opacity="0.85"/>
      </g>
      <g class="eye-group" style="animation-delay:-0.3s">
        <ellipse cx="${rx}" cy="${ry}" rx="${whiteW}" ry="${whiteH}" fill="white" stroke="#4a3728" stroke-width="0.3"/>
        <circle class="eye-pupil" cx="${rx}" cy="${ry+0.5}" r="${pupilSize}" fill="#3d2b1f"/>
        <circle cx="${rx-1.2}" cy="${ry-1.5}" r="1.5" fill="white" opacity="0.85"/>
      </g>
    `;
  }

  /* ── The emoji SVG map ── */
  const EMOJI_SVG = {
    /* ══ GRINNING / HAPPY ══ */
    '😀': {
      cls: '',
      svg: `<circle cx="20" cy="20" r="18" fill="url(#emojiYellow)" filter="url(#emojiShadow)"/>
            <circle cx="20" cy="20" r="18" fill="url(#emojiFaceHighlight)"/>
            ${makeEyes(14, 16, 26, 16)}
            <path d="M11 22 Q20 32 29 22" fill="#A0522D" stroke="#8B4513" stroke-width="0.5"/>
            <path d="M11 22 Q20 26 29 22" fill="white"/>
            <circle cx="9" cy="22" r="3" fill="#FFB3B3" opacity="0.35"/><circle cx="31" cy="22" r="3" fill="#FFB3B3" opacity="0.35"/>`
    },

    /* ══ CRYING/SOBBING ══ */
    '😭': {
      cls: '',
      svg: `<circle cx="20" cy="20" r="18" fill="url(#emojiYellow)" filter="url(#emojiShadow)"/>
            <circle cx="20" cy="20" r="18" fill="url(#emojiFaceHighlight)"/>
            <g class="eye-group">
              <path d="M10 15 Q14 12 18 15" fill="none" stroke="#5a3e2b" stroke-width="1.8" stroke-linecap="round"/>
              <circle class="eye-pupil" cx="14" cy="14" r="1" fill="#5a3e2b"/>
            </g>
            <g class="eye-group" style="animation-delay:-0.3s">
              <path d="M22 15 Q26 12 30 15" fill="none" stroke="#5a3e2b" stroke-width="1.8" stroke-linecap="round"/>
              <circle class="eye-pupil" cx="26" cy="14" r="1" fill="#5a3e2b"/>
            </g>
            <ellipse cx="20" cy="27" rx="5" ry="4" fill="#A0522D" stroke="#8B4513" stroke-width="0.5"/>
            <rect class="tear" x="10" y="17" width="3" height="8" rx="1.5" fill="#4AA3DF" opacity="0.7"/>
            <rect class="tear" x="27" y="17" width="3" height="8" rx="1.5" fill="#4AA3DF" opacity="0.7"/>`
    },

    /* ══ ANGRY ══ */
    '😡': {
      cls: 'vybe-emoji--angry',
      svg: `<circle cx="20" cy="20" r="18" fill="url(#emojiRed)" filter="url(#emojiShadow)"/>
            <circle cx="20" cy="20" r="18" fill="url(#emojiFaceHighlight)"/>
            <g class="eye-group">
              <line x1="9" y1="12" x2="17" y2="15" stroke="#5a2e0e" stroke-width="2.5" stroke-linecap="round"/>
              <circle class="eye-pupil" cx="14" cy="16" r="2.5" fill="white"/>
              <circle cx="14" cy="16" r="1.5" fill="#2d1a0e"/>
            </g>
            <g class="eye-group" style="animation-delay:-0.3s">
              <line x1="31" y1="12" x2="23" y2="15" stroke="#5a2e0e" stroke-width="2.5" stroke-linecap="round"/>
              <circle class="eye-pupil" cx="26" cy="16" r="2.5" fill="white"/>
              <circle cx="26" cy="16" r="1.5" fill="#2d1a0e"/>
            </g>
            <path d="M13 28 Q20 24 27 28" fill="none" stroke="#5a2e0e" stroke-width="2" stroke-linecap="round"/>`
    },

    /* ══ HEART EYES ══ */
    '😍': {
      cls: 'vybe-emoji--heart-eyes',
      svg: `<circle cx="20" cy="20" r="18" fill="url(#emojiYellow)" filter="url(#emojiShadow)"/>
            <circle cx="20" cy="20" r="18" fill="url(#emojiFaceHighlight)"/>
            <g class="heart-eye">
              <path d="M10 15 C10 11, 14 10, 14 14 C14 10, 18 11, 18 15 C18 19, 14 22, 14 22 C14 22, 10 19, 10 15Z" fill="#FF3366"/>
            </g>
            <g class="heart-eye" style="animation-delay:-0.4s">
              <path d="M22 15 C22 11, 26 10, 26 14 C26 10, 30 11, 30 15 C30 19, 26 22, 26 22 C26 22, 22 19, 22 15Z" fill="#FF3366"/>
            </g>
            <path d="M12 26 Q20 33 28 26" fill="#A0522D" stroke="#8B4513" stroke-width="0.5"/>
            <path d="M12 26 Q20 29 28 26" fill="white"/>`
    },

    /* ══ PINK HEART FACE ══ */
    '🥰': {
      cls: 'vybe-emoji--heart-eyes',
      svg: `<circle cx="20" cy="20" r="18" fill="url(#emojiYellow)" filter="url(#emojiShadow)"/>
            <circle cx="20" cy="20" r="18" fill="url(#emojiFaceHighlight)"/>
            ${makeEyes(14, 16, 26, 16, 3)}
            <path d="M13 24 Q20 30 27 24" fill="none" stroke="#A0522D" stroke-width="1.5" stroke-linecap="round"/>
            <circle cx="9" cy="22" r="3.5" fill="#FFB3B3" opacity="0.5"/><circle cx="31" cy="22" r="3.5" fill="#FFB3B3" opacity="0.5"/>
            <g class="heart-eye"><path d="M3 8 C3 5,6 4,6 7 C6 4,9 5,9 8 C9 11,6 13,6 13 C6 13,3 11,3 8Z" fill="#FF6B9D" opacity="0.8"/></g>
            <g class="heart-eye" style="animation-delay:-0.5s"><path d="M30 5 C30 2,33 1,33 4 C33 1,36 2,36 5 C36 8,33 10,33 10 C33 10,30 8,30 5Z" fill="#FF6B9D" opacity="0.8"/></g>
            <g class="heart-eye" style="animation-delay:-1s"><path d="M17 3 C17 1,19 0,19 2 C19 0,21 1,21 3 C21 5,19 6,19 6 C19 6,17 5,17 3Z" fill="#FF3366" opacity="0.7"/></g>`
    },

    /* ══ LAUGHING WITH TEARS ══ */
    '😂': {
      cls: 'vybe-emoji--laughing',
      svg: `<circle cx="20" cy="20" r="18" fill="url(#emojiYellow)" filter="url(#emojiShadow)"/>
            <circle cx="20" cy="20" r="18" fill="url(#emojiFaceHighlight)"/>
            <g class="eye-group">
              <path d="M10 15 Q14 11 18 15" fill="none" stroke="#5a3e2b" stroke-width="2" stroke-linecap="round"/>
            </g>
            <g class="eye-group" style="animation-delay:-0.3s">
              <path d="M22 15 Q26 11 30 15" fill="none" stroke="#5a3e2b" stroke-width="2" stroke-linecap="round"/>
            </g>
            <path d="M11 22 Q20 33 29 22" fill="#A0522D" stroke="#8B4513" stroke-width="0.5"/>
            <path d="M11 22 Q20 26 29 22" fill="white"/>
            <path class="tear" d="M9 16 Q8 20 9 24" fill="none" stroke="#4AA3DF" stroke-width="2" stroke-linecap="round" opacity="0.7"/>
            <path class="tear" d="M31 16 Q32 20 31 24" fill="none" stroke="#4AA3DF" stroke-width="2" stroke-linecap="round" opacity="0.7"/>`
    },

    /* ══ WOW / SURPRISED ══ */
    '😮': {
      cls: '',
      svg: `<circle cx="20" cy="20" r="18" fill="url(#emojiBlue)" filter="url(#emojiShadow)"/>
            <circle cx="20" cy="20" r="18" fill="url(#emojiFaceHighlight)"/>
            ${makeEyes(14, 14, 26, 14, 4, 5.5, 7)}
            <ellipse cx="20" cy="28" rx="4" ry="5" fill="#3d6e99" stroke="#2a5580" stroke-width="0.5"/>`
    },

    /* ══ SLEEPING / ZZZ ══ */
    '😴': {
      cls: 'vybe-emoji--sleeping',
      svg: `<circle cx="20" cy="20" r="18" fill="url(#emojiYellow)" filter="url(#emojiShadow)"/>
            <circle cx="20" cy="20" r="18" fill="url(#emojiFaceHighlight)"/>
            <path d="M10 16 Q14 18 18 16" fill="none" stroke="#5a3e2b" stroke-width="2" stroke-linecap="round"/>
            <path d="M22 16 Q26 18 30 16" fill="none" stroke="#5a3e2b" stroke-width="2" stroke-linecap="round"/>
            <ellipse cx="20" cy="27" rx="3" ry="2.5" fill="#D4956A" stroke="#B8784F" stroke-width="0.5"/>
            <circle cx="9" cy="22" r="3" fill="#FFB3B3" opacity="0.35"/><circle cx="31" cy="22" r="3" fill="#FFB3B3" opacity="0.35"/>
            <text class="zzz" x="28" y="10" font-size="5" font-weight="bold" fill="#8B5CF6" opacity="0.8">z</text>
            <text class="zzz" x="32" y="6" font-size="7" font-weight="bold" fill="#8B5CF6" opacity="0.6">Z</text>
            <text class="zzz" x="35" y="1" font-size="9" font-weight="bold" fill="#8B5CF6" opacity="0.4">Z</text>`
    },

    /* ══ COOL / SUNGLASSES ══ */
    '😎': {
      cls: 'vybe-emoji--cool',
      svg: `<circle cx="20" cy="20" r="18" fill="url(#emojiYellow)" filter="url(#emojiShadow)"/>
            <circle cx="20" cy="20" r="18" fill="url(#emojiFaceHighlight)"/>
            <rect x="7" y="12" width="12" height="9" rx="3" fill="#1a1a2e" stroke="#111" stroke-width="0.5"/>
            <rect x="21" y="12" width="12" height="9" rx="3" fill="#1a1a2e" stroke="#111" stroke-width="0.5"/>
            <line x1="19" y1="15" x2="21" y2="15" stroke="#1a1a2e" stroke-width="1.5"/>
            <line x1="7" y1="15" x2="4" y2="13" stroke="#1a1a2e" stroke-width="1.5"/>
            <line x1="33" y1="15" x2="36" y2="13" stroke="#1a1a2e" stroke-width="1.5"/>
            <rect class="glint" x="9" y="13" width="4" height="2" rx="1" fill="white" opacity="0"/>
            <rect class="glint" x="23" y="13" width="4" height="2" rx="1" fill="white" opacity="0" style="animation-delay:-1.5s"/>
            <path d="M13 26 Q20 31 27 26" fill="none" stroke="#A0522D" stroke-width="1.5" stroke-linecap="round"/>`
    },

    /* ══ DIZZY / SPIRAL EYES ══ */
    '😵': {
      cls: 'vybe-emoji--dizzy',
      svg: `<circle cx="20" cy="20" r="18" fill="url(#emojiYellow)" filter="url(#emojiShadow)"/>
            <circle cx="20" cy="20" r="18" fill="url(#emojiFaceHighlight)"/>
            <g class="spiral-eye">
              <circle cx="13" cy="16" r="5" fill="none" stroke="#6C5CE7" stroke-width="1.5"/>
              <circle cx="13" cy="16" r="2.5" fill="none" stroke="#6C5CE7" stroke-width="1.5"/>
            </g>
            <g class="spiral-eye" style="animation-delay:-1s">
              <circle cx="27" cy="16" r="5" fill="none" stroke="#6C5CE7" stroke-width="1.5"/>
              <circle cx="27" cy="16" r="2.5" fill="none" stroke="#6C5CE7" stroke-width="1.5"/>
            </g>
            <path d="M15 27 Q20 24 25 27" fill="none" stroke="#A0522D" stroke-width="1.5" stroke-linecap="round"/>`
    },

    /* ══ KISS / BLOWING KISS ══ */
    '😘': {
      cls: 'vybe-emoji--kiss',
      svg: `<circle cx="20" cy="20" r="18" fill="url(#emojiYellow)" filter="url(#emojiShadow)"/>
            <circle cx="20" cy="20" r="18" fill="url(#emojiFaceHighlight)"/>
            ${makeEyes(14, 16, 26, 16, 3)}
            <g class="eye-group"><path d="M23 14 L27 12" fill="none" stroke="#5a3e2b" stroke-width="0.8" stroke-linecap="round"/></g>
            <circle cx="20" cy="26" r="2.5" fill="#E84393"/>
            <path class="floating-heart" d="M30 16 C30 14,32 13,32 15 C32 13,34 14,34 16 C34 18,32 20,32 20 C32 20,30 18,30 16Z" fill="#FF3366" opacity="0.9"/>
            <circle cx="9" cy="22" r="3" fill="#FFB3B3" opacity="0.35"/>`
    },

    /* ══ SAD ══ */
    '😢': {
      cls: '',
      svg: `<circle cx="20" cy="20" r="18" fill="url(#emojiYellow)" filter="url(#emojiShadow)"/>
            <circle cx="20" cy="20" r="18" fill="url(#emojiFaceHighlight)"/>
            ${makeEyes(14, 16, 26, 16, 3.5)}
            <path d="M13 27 Q20 23 27 27" fill="none" stroke="#A0522D" stroke-width="1.5" stroke-linecap="round"/>
            <path class="tear" d="M27 20 Q28 24 27 28" fill="none" stroke="#4AA3DF" stroke-width="2" stroke-linecap="round" opacity="0.7"/>`
    },

    /* ══ FIRE ══ */
    '🔥': {
      cls: '',
      svg: `<path d="M20 4 C20 4, 10 16, 12 24 C14 32, 26 32, 28 24 C30 16, 20 4, 20 4Z" fill="url(#emojiOrange)" filter="url(#emojiShadow)"/>
            <path d="M20 10 C20 10, 14 18, 16 24 C17 28, 23 28, 24 24 C26 18, 20 10, 20 10Z" fill="#FFD93D"/>
            <path d="M20 16 C20 16, 17 22, 18 26 C19 28, 21 28, 22 26 C23 22, 20 16, 20 16Z" fill="#FFF3B0"/>
            ${makeEyes(16, 20, 24, 20, 2, 3, 3.5)}`
    },

    /* ══ THUMBS UP ══ */
    '👍': {
      cls: '',
      svg: `<path d="M14 16 L14 33 L24 33 L24 16 Z" fill="url(#emojiYellow)" rx="3" filter="url(#emojiShadow)"/>
            <path d="M24 20 L28 20 C31 20, 33 18, 31 15 L28 10 C27 8, 25 8, 24 10 L24 16" fill="url(#emojiYellow)"/>
            <path d="M14 33 L10 33 C8 33, 7 31, 7 29 L7 22 C7 20, 8 18, 10 18 L14 18" fill="url(#emojiYellow)"/>
            <rect x="6" y="22" width="9" height="12" rx="3" fill="#F5B800" opacity="0.4"/>`
    },

    /* ══ CLAPPING ══ */
    '👏': {
      cls: '',
      svg: `<circle cx="20" cy="20" r="18" fill="url(#emojiYellow)" filter="url(#emojiShadow)"/>
            <circle cx="20" cy="20" r="18" fill="url(#emojiFaceHighlight)"/>
            ${makeEyes(14, 15, 26, 15, 3)}
            <path d="M12 24 Q20 30 28 24" fill="#A0522D" stroke="#8B4513" stroke-width="0.5"/>
            <path d="M12 24 Q20 27 28 24" fill="white"/>
            <line x1="8" y1="6" x2="10" y2="10" stroke="#FFD93D" stroke-width="2" stroke-linecap="round"/>
            <line x1="20" y1="3" x2="20" y2="7" stroke="#FFD93D" stroke-width="2" stroke-linecap="round"/>
            <line x1="32" y1="6" x2="30" y2="10" stroke="#FFD93D" stroke-width="2" stroke-linecap="round"/>`
    },

    /* ══ 100 ══ */
    '💯': {
      cls: '',
      svg: `<text x="20" y="28" text-anchor="middle" font-size="22" font-weight="900" fill="url(#emojiRed)" filter="url(#emojiShadow)" font-family="Arial Black, sans-serif">💯</text>`
    },

    /* ══ SPARKLE ══ */
    '✨': {
      cls: '',
      svg: `<polygon points="20,4 23,15 34,15 25,22 28,33 20,26 12,33 15,22 6,15 17,15" fill="url(#emojiYellow)" filter="url(#emojiShadow)"/>
            <polygon points="20,8 22,15 29,15 23,20 25,28 20,23 15,28 17,20 11,15 18,15" fill="#FFF3B0"/>
            ${makeEyes(17, 17, 23, 17, 1.5, 2.5, 2.5)}`
    },

    /* ══ PARTY ══ */
    '🎉': {
      cls: '',
      svg: `<circle cx="20" cy="20" r="18" fill="url(#emojiYellow)" filter="url(#emojiShadow)"/>
            <circle cx="20" cy="20" r="18" fill="url(#emojiFaceHighlight)"/>
            ${makeEyes(14, 15, 26, 15, 3)}
            <path d="M11 24 Q20 32 29 24" fill="#A0522D" stroke="#8B4513" stroke-width="0.5"/>
            <path d="M11 24 Q20 28 29 24" fill="white"/>
            <circle cx="8" cy="8" r="2" fill="#FF3366"/><circle cx="32" cy="6" r="1.5" fill="#6C5CE7"/>
            <circle cx="14" cy="4" r="1.2" fill="#00B894"/><circle cx="28" cy="4" r="1.8" fill="#FDCB6E"/>
            <rect x="5" y="12" width="3" height="1.5" rx="0.75" fill="#E17055" transform="rotate(-20 6 12)"/>
            <rect x="32" y="10" width="3" height="1.5" rx="0.75" fill="#0984E3" transform="rotate(15 33 10)"/>`
    },

    /* ══ SKULL ══ */
    '💀': {
      cls: '',
      svg: `<ellipse cx="20" cy="18" rx="15" ry="16" fill="white" filter="url(#emojiShadow)"/>
            <ellipse cx="20" cy="18" rx="15" ry="16" fill="url(#emojiFaceHighlight)"/>
            <g class="eye-group">
              <ellipse cx="14" cy="16" rx="4" ry="4.5" fill="#1a1a2e"/>
              <circle class="eye-pupil" cx="14" cy="16" r="1.5" fill="#555"/>
            </g>
            <g class="eye-group" style="animation-delay:-0.3s">
              <ellipse cx="26" cy="16" rx="4" ry="4.5" fill="#1a1a2e"/>
              <circle class="eye-pupil" cx="26" cy="16" r="1.5" fill="#555"/>
            </g>
            <ellipse cx="20" cy="22" rx="2" ry="1.5" fill="#bbb"/>
            <g>
              <line x1="15" y1="28" x2="15" y2="32" stroke="#ccc" stroke-width="1"/>
              <line x1="20" y1="28" x2="20" y2="32" stroke="#ccc" stroke-width="1"/>
              <line x1="25" y1="28" x2="25" y2="32" stroke="#ccc" stroke-width="1"/>
            </g>`
    },

    /* ══ EYES ══ */
    '👀': {
      cls: '',
      svg: `<g>
              <ellipse cx="13" cy="20" rx="8" ry="10" fill="white" filter="url(#emojiShadow)" stroke="#ddd" stroke-width="0.5"/>
              <g class="eye-group">
                <circle class="eye-pupil" cx="15" cy="20" r="5" fill="#5a3e2b"/>
                <circle cx="13" cy="18" r="2" fill="white" opacity="0.85"/>
              </g>
            </g>
            <g>
              <ellipse cx="28" cy="20" rx="8" ry="10" fill="white" filter="url(#emojiShadow)" stroke="#ddd" stroke-width="0.5"/>
              <g class="eye-group" style="animation-delay:-0.3s">
                <circle class="eye-pupil" cx="30" cy="20" r="5" fill="#5a3e2b"/>
                <circle cx="28" cy="18" r="2" fill="white" opacity="0.85"/>
              </g>
            </g>`
    },

    /* ══ RAISE HANDS ══ */
    '🙌': {
      cls: '',
      svg: `<circle cx="20" cy="22" r="16" fill="url(#emojiYellow)" filter="url(#emojiShadow)"/>
            <circle cx="20" cy="22" r="16" fill="url(#emojiFaceHighlight)"/>
            ${makeEyes(15, 20, 25, 20, 2.5, 3.5, 4)}
            <path d="M14 28 Q20 32 26 28" fill="none" stroke="#A0522D" stroke-width="1.2" stroke-linecap="round"/>
            <ellipse cx="8" cy="10" rx="5" ry="6" fill="url(#emojiYellow)" stroke="#F5B800" stroke-width="0.5"/>
            <ellipse cx="32" cy="10" rx="5" ry="6" fill="url(#emojiYellow)" stroke="#F5B800" stroke-width="0.5"/>
            <line x1="5" y1="4" x2="8" y2="6" stroke="#FFD93D" stroke-width="1.5" stroke-linecap="round"/>
            <line x1="11" y1="3" x2="10" y2="6" stroke="#FFD93D" stroke-width="1.5" stroke-linecap="round"/>
            <line x1="29" y1="3" x2="30" y2="6" stroke="#FFD93D" stroke-width="1.5" stroke-linecap="round"/>
            <line x1="35" y1="4" x2="32" y2="6" stroke="#FFD93D" stroke-width="1.5" stroke-linecap="round"/>`
    },

    /* ══ MIND BLOWN ══ */
    '🤯': {
      cls: '',
      svg: `<circle cx="20" cy="22" r="16" fill="url(#emojiYellow)" filter="url(#emojiShadow)"/>
            <circle cx="20" cy="22" r="16" fill="url(#emojiFaceHighlight)"/>
            ${makeEyes(15, 20, 25, 20, 4, 5, 6)}
            <ellipse cx="20" cy="30" rx="3" ry="4" fill="#A0522D" stroke="#8B4513" stroke-width="0.5"/>
            <path d="M8 12 Q12 2 16 8" fill="none" stroke="#FF6B6B" stroke-width="2" stroke-linecap="round"/>
            <path d="M24 8 Q28 2 32 12" fill="none" stroke="#FFD93D" stroke-width="2" stroke-linecap="round"/>
            <circle cx="12" cy="5" r="2" fill="#FF6B6B"/><circle cx="28" cy="5" r="2" fill="#FFD93D"/>
            <circle cx="20" cy="3" r="1.5" fill="#6C5CE7"/><circle cx="16" cy="7" r="1" fill="#00B894"/>
            <circle cx="24" cy="6" r="1.2" fill="#E17055"/>`
    },

    /* ══ HEART (❤️) ══ */
    '❤️': {
      cls: 'vybe-emoji--heart-eyes',
      svg: `<path d="M20 34 C20 34, 5 24, 5 14 C5 8, 10 4, 14 4 C17 4, 19 6, 20 8 C21 6, 23 4, 26 4 C30 4, 35 8, 35 14 C35 24, 20 34, 20 34Z" fill="url(#emojiPink)" filter="url(#emojiShadow)"/>
            <path d="M20 34 C20 34, 5 24, 5 14 C5 8, 10 4, 14 4 C17 4, 19 6, 20 8 C21 6, 23 4, 26 4 C30 4, 35 8, 35 14 C35 24, 20 34, 20 34Z" fill="url(#emojiFaceHighlight)"/>
            <g class="heart-eye">${makeEyes(15, 16, 25, 16, 2, 3, 3)}</g>`
    },

    /* ══ WINK ══ */
    '😉': {
      cls: '',
      svg: `<circle cx="20" cy="20" r="18" fill="url(#emojiYellow)" filter="url(#emojiShadow)"/>
            <circle cx="20" cy="20" r="18" fill="url(#emojiFaceHighlight)"/>
            <g class="eye-group">
              <ellipse cx="14" cy="16" rx="5" ry="6" fill="white" stroke="#4a3728" stroke-width="0.3"/>
              <circle class="eye-pupil" cx="14" cy="16.5" r="3.5" fill="#3d2b1f"/>
              <circle cx="12.8" cy="14.5" r="1.5" fill="white" opacity="0.85"/>
            </g>
            <path d="M23 16 Q26 14 29 16" fill="none" stroke="#5a3e2b" stroke-width="2" stroke-linecap="round"/>
            <path d="M13 25 Q20 31 27 25" fill="none" stroke="#A0522D" stroke-width="1.5" stroke-linecap="round"/>
            <circle cx="9" cy="22" r="3" fill="#FFB3B3" opacity="0.35"/><circle cx="31" cy="22" r="3" fill="#FFB3B3" opacity="0.35"/>`
    },

    /* ══ DEVIL/IMP ══ */
    '😈': {
      cls: '',
      svg: `<circle cx="20" cy="22" r="16" fill="#8B5CF6" filter="url(#emojiShadow)"/>
            <circle cx="20" cy="22" r="16" fill="url(#emojiFaceHighlight)"/>
            <path d="M8 12 L6 2 L14 10Z" fill="#7C3AED"/>
            <path d="M32 12 L34 2 L26 10Z" fill="#7C3AED"/>
            ${makeEyes(15, 20, 25, 20, 3)}
            <path d="M13 28 Q20 34 27 28" fill="#6D28D9" stroke="#5B21B6" stroke-width="0.5"/>
            <path d="M13 28 Q20 31 27 28" fill="white"/>`
    },

    /* ══ PLEADING ══ */
    '🥺': {
      cls: '',
      svg: `<circle cx="20" cy="20" r="18" fill="url(#emojiYellow)" filter="url(#emojiShadow)"/>
            <circle cx="20" cy="20" r="18" fill="url(#emojiFaceHighlight)"/>
            ${makeEyes(14, 16, 26, 16, 4.5, 6, 7)}
            <circle cx="14" cy="16" r="6" fill="rgba(255,255,255,0.15)"/>
            <circle cx="26" cy="16" r="6" fill="rgba(255,255,255,0.15)"/>
            <path d="M15 27 Q20 24 25 27" fill="none" stroke="#A0522D" stroke-width="1.3" stroke-linecap="round"/>
            <circle cx="9" cy="22" r="3" fill="#FFB3B3" opacity="0.4"/><circle cx="31" cy="22" r="3" fill="#FFB3B3" opacity="0.4"/>`
    },

    /* ══ NERD ══ */
    '🤓': {
      cls: '',
      svg: `<circle cx="20" cy="20" r="18" fill="url(#emojiYellow)" filter="url(#emojiShadow)"/>
            <circle cx="20" cy="20" r="18" fill="url(#emojiFaceHighlight)"/>
            ${makeEyes(14, 16, 26, 16, 3)}
            <circle cx="14" cy="16" r="6.5" fill="none" stroke="#5a3e2b" stroke-width="1.5"/>
            <circle cx="26" cy="16" r="6.5" fill="none" stroke="#5a3e2b" stroke-width="1.5"/>
            <line x1="20" y1="15" x2="20" y2="17" stroke="#5a3e2b" stroke-width="1.5"/>
            <path d="M14 26 Q20 30 26 26" fill="none" stroke="#A0522D" stroke-width="1.5" stroke-linecap="round"/>
            <rect x="12" y="26" width="4" height="2" rx="1" fill="white"/>`
    },

    /* ══ STAR-STRUCK ══ */
    '🤩': {
      cls: 'vybe-emoji--heart-eyes',
      svg: `<circle cx="20" cy="20" r="18" fill="url(#emojiYellow)" filter="url(#emojiShadow)"/>
            <circle cx="20" cy="20" r="18" fill="url(#emojiFaceHighlight)"/>
            <g class="heart-eye">
              <polygon points="14,10 15.5,14.5 20,14.5 16.5,17.5 18,22 14,19 10,22 11.5,17.5 8,14.5 12.5,14.5" fill="#FFD93D" stroke="#F5B800" stroke-width="0.3"/>
            </g>
            <g class="heart-eye" style="animation-delay:-0.4s">
              <polygon points="26,10 27.5,14.5 32,14.5 28.5,17.5 30,22 26,19 22,22 23.5,17.5 20,14.5 24.5,14.5" fill="#FFD93D" stroke="#F5B800" stroke-width="0.3"/>
            </g>
            <path d="M12 26 Q20 33 28 26" fill="#A0522D" stroke="#8B4513" stroke-width="0.5"/>
            <path d="M12 26 Q20 29 28 26" fill="white"/>`
    },

    /* ══ THINKING ══ */
    '🤔': {
      cls: '',
      svg: `<circle cx="20" cy="20" r="18" fill="url(#emojiYellow)" filter="url(#emojiShadow)"/>
            <circle cx="20" cy="20" r="18" fill="url(#emojiFaceHighlight)"/>
            ${makeEyes(14, 15, 26, 15, 3)}
            <path d="M10 11 L17 14" fill="none" stroke="#5a3e2b" stroke-width="1.8" stroke-linecap="round"/>
            <path d="M30 11 L23 14" fill="none" stroke="#5a3e2b" stroke-width="1.8" stroke-linecap="round"/>
            <path d="M15 26 Q20 24 25 26" fill="none" stroke="#A0522D" stroke-width="1.5" stroke-linecap="round"/>
            <ellipse cx="28" cy="30" rx="5" ry="4" fill="url(#emojiYellow)" stroke="#F5B800" stroke-width="0.5"/>
            <path d="M25 28 Q27 26 29 28" fill="none" stroke="#D4956A" stroke-width="1" stroke-linecap="round"/>`
    },

    /* ══ ROLLING EYES ══ */
    '🙄': {
      cls: '',
      svg: `<circle cx="20" cy="20" r="18" fill="url(#emojiYellow)" filter="url(#emojiShadow)"/>
            <circle cx="20" cy="20" r="18" fill="url(#emojiFaceHighlight)"/>
            <g class="eye-group">
              <ellipse cx="14" cy="16" rx="5" ry="6" fill="white" stroke="#4a3728" stroke-width="0.3"/>
              <circle class="eye-pupil" cx="14" cy="13" r="3.5" fill="#3d2b1f"/>
            </g>
            <g class="eye-group" style="animation-delay:-0.3s">
              <ellipse cx="26" cy="16" rx="5" ry="6" fill="white" stroke="#4a3728" stroke-width="0.3"/>
              <circle class="eye-pupil" cx="26" cy="13" r="3.5" fill="#3d2b1f"/>
            </g>
            <path d="M15 27 Q20 25 25 27" fill="none" stroke="#A0522D" stroke-width="1.5" stroke-linecap="round"/>`
    },

    /* ══ SMIRK ══ */
    '😏': {
      cls: '',
      svg: `<circle cx="20" cy="20" r="18" fill="url(#emojiYellow)" filter="url(#emojiShadow)"/>
            <circle cx="20" cy="20" r="18" fill="url(#emojiFaceHighlight)"/>
            ${makeEyes(14, 16, 26, 16, 3)}
            <path d="M14 26 Q22 30 28 24" fill="none" stroke="#A0522D" stroke-width="1.8" stroke-linecap="round"/>`
    },

    /* ══ PLEADING / PUPPY ══ */
    '😊': {
      cls: '',
      svg: `<circle cx="20" cy="20" r="18" fill="url(#emojiYellow)" filter="url(#emojiShadow)"/>
            <circle cx="20" cy="20" r="18" fill="url(#emojiFaceHighlight)"/>
            <g class="eye-group">
              <path d="M10 16 Q14 12 18 16" fill="none" stroke="#5a3e2b" stroke-width="2" stroke-linecap="round"/>
            </g>
            <g class="eye-group" style="animation-delay:-0.3s">
              <path d="M22 16 Q26 12 30 16" fill="none" stroke="#5a3e2b" stroke-width="2" stroke-linecap="round"/>
            </g>
            <path d="M13 24 Q20 30 27 24" fill="none" stroke="#A0522D" stroke-width="1.5" stroke-linecap="round"/>
            <circle cx="9" cy="22" r="3.5" fill="#FFB3B3" opacity="0.45"/><circle cx="31" cy="22" r="3.5" fill="#FFB3B3" opacity="0.45"/>`
    },

    /* ══ SHUSHING ══ */
    '🤫': {
      cls: '',
      svg: `<circle cx="20" cy="20" r="18" fill="url(#emojiYellow)" filter="url(#emojiShadow)"/>
            <circle cx="20" cy="20" r="18" fill="url(#emojiFaceHighlight)"/>
            ${makeEyes(14, 15, 26, 15, 3)}
            <ellipse cx="20" cy="26" rx="3" ry="2" fill="#D4956A"/>
            <rect x="18" y="22" width="4" height="8" rx="2" fill="url(#emojiYellow)" stroke="#F5B800" stroke-width="0.3"/>`
    }
  };

  /* ── Create an animated SVG emoji element ── */
  function createAnimatedEmoji(emoji, size) {
    size = size || 40;
    const data = EMOJI_SVG[emoji];
    if (!data) return null;

    const wrap = document.createElement('span');
    wrap.className = 'vybe-emoji' + (data.cls ? ' ' + data.cls : '');
    wrap.style.width = size + 'px';
    wrap.style.height = size + 'px';
    wrap.style.fontSize = size + 'px';
    wrap.setAttribute('data-emoji', emoji);
    wrap.title = emoji;

    wrap.innerHTML = `<svg viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg">${SHARED_DEFS}${data.svg}</svg>`;
    
    /* Eye tracking — move pupils toward mouse */
    wrap.addEventListener('mousemove', function(e) {
      const rect = wrap.getBoundingClientRect();
      const cx = rect.left + rect.width / 2;
      const cy = rect.top + rect.height / 2;
      const dx = (e.clientX - cx) / rect.width;
      const dy = (e.clientY - cy) / rect.height;
      const maxMove = 2.5;
      const pupils = wrap.querySelectorAll('.eye-pupil');
      pupils.forEach(function(p) {
        p.style.transform = 'translate(' + (dx * maxMove) + 'px, ' + (dy * maxMove) + 'px)';
        p.style.animation = 'none';
      });
    });
    wrap.addEventListener('mouseleave', function() {
      const pupils = wrap.querySelectorAll('.eye-pupil');
      pupils.forEach(function(p) {
        p.style.transform = '';
        p.style.animation = '';
      });
    });

    return wrap;
  }

  /* ── Get emoji HTML string for inline use ── */
  function getAnimatedEmojiHTML(emoji, size) {
    const el = createAnimatedEmoji(emoji, size);
    if (!el) return emoji; // fallback to text
    return el.outerHTML;
  }

  /* ── Check if an emoji has an animated version ── */
  function hasAnimatedEmoji(emoji) {
    return !!EMOJI_SVG[emoji];
  }

  /* ── Get all supported animated emojis ── */
  function getSupportedEmojis() {
    return Object.keys(EMOJI_SVG);
  }

  /* Expose globally */
  window.VybeEmoji = {
    create: createAnimatedEmoji,
    getHTML: getAnimatedEmojiHTML,
    has: hasAnimatedEmoji,
    supported: getSupportedEmojis,
    SVG_DATA: EMOJI_SVG,
    DEFS: SHARED_DEFS
  };

})();
