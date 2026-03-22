/**
 * VybeFlow App-Wide Internationalization (i18n)
 * Works alongside auth.js — translates ALL app pages (feed, settings, games, stories, etc.)
 * Uses the same localStorage key "vybe_lang" and same .lang-chip-btn buttons.
 */
(function () {
  'use strict';
  var LANG_KEY = 'vybe_lang';

  var T = {
    /* ════════════════════════════════════════════════
       ENGLISH
       ════════════════════════════════════════════════ */
    en: {
      /* — Nav / Topbar — */
      search_placeholder: 'Search VybeFlow',
      retro_mode: '2011 Mode',
      nav_home: 'Home', nav_explore: 'Explore', nav_create: 'Create',
      nav_messenger: 'Messenger', nav_live: 'Live', nav_account: 'Account',
      nav_settings: 'Settings', nav_logout: 'Logout',

      /* — Sidebar — */
      sidebar_you: 'You', sidebar_shortcuts: 'Shortcuts',
      sidebar_quick_actions: 'Quick Actions', sidebar_your_vybes: 'Your Vybes',
      sidebar_home: 'Home', sidebar_explore: 'Explore', sidebar_create: 'Create',
      sidebar_view_account: 'View Account', sidebar_upload: 'Upload Media',
      sidebar_messenger: 'Messenger', sidebar_live_hub: 'Live Hub',
      sidebar_search: 'Search', sidebar_settings: 'Settings', sidebar_signout: 'Sign Out',
      sidebar_trap: 'Trap', sidebar_rnb: 'R&B', sidebar_sports: 'Sports', sidebar_hustle: 'Hustle',

      /* — Stories — */
      your_story: 'Your story', stories: 'Stories',

      /* — Vibe Energy — */
      vibe_energy: 'Live Vibe Energy', vibe_calculating: 'Calculating vibe...',
      vibe_posts_today: '0 posts today',

      /* — Composer — */
      whats_on_mind: "What's on your mind?",
      composer_placeholder: 'Share your post, drop a note, or ask a question...',
      bg_default: 'Background: Default', bg_sunset: 'Background: Sunset',
      bg_neon: 'Background: Neon', bg_glass: 'Background: Glass',
      vis_public: 'Visibility: Public', vis_followers: 'Visibility: Followers',
      vis_private: 'Visibility: Only me (Draft)',
      publish: 'Publish',
      photo_video: 'Photo / video', emoji_stickers: 'Emoji / stickers', add_vybe: 'Add a Vybe',

      /* — Vibe Check moods — */
      vibe_check: 'Vibe Check:', mood_lit: 'Lit', mood_grinding: 'Grinding',
      mood_chill: 'Chill', mood_vibing: 'Vibing', mood_feels: 'Feels',
      mood_winning: 'Winning', mood_savage: 'Savage',

      /* — Confession — */
      confession_mode: 'Confession Mode',
      confession_desc: 'Post anonymously — your identity stays hidden',

      /* — Poll — */
      create_poll: 'Create Poll', ask_question: 'Ask a question...',
      option_a: 'Option A', option_b: 'Option B',
      option_c: 'Option C (optional)', option_d: 'Option D (optional)',

      /* — Music panel — */
      search_music: 'Search Music', close: 'Close',
      music_search_placeholder: 'Search any song, artist, genre…',
      search_btn: 'Search', remove: 'Remove', clear: 'Clear', upload: 'Upload',

      /* — Emoji panel — */
      emoji_panel_title: 'Emoji, stickers & GIFs',
      gif_library: 'GIF Library', powered_tenor: 'Powered by Tenor',

      /* — Reels — */
      reels: 'Vibe Snaps', reels_sub: 'Tap to flex • Hover to preview • Drop heat 🔥',
      for_you: 'For You', chaos: 'Chaos', no_reels: 'No reels yet — be the first to drop one.',

      /* — Post actions — */
      like: 'Like', share: 'Share', comment: 'Comment', save: 'Save',

      /* — Settings — */
      settings_title: 'Settings',
      tab_account: 'Account', tab_privacy: 'Privacy', tab_security: 'Security',
      tab_notifications: 'Notifications', tab_appearance: 'Appearance',
      tab_profile_music: 'Profile Music', tab_delete_account: 'Delete Account',
      display_name: 'Display Name', ai_assist: 'AI Assist on Feed',
      mode_2011: '2011 Mode (classic)', post_visibility: 'Default Post Visibility',
      public: 'Public', followers: 'Followers', private: 'Private',
      bio_label: 'Profile Bio', bio_placeholder: 'Write your real profile bio...',
      safe_mode: 'Safe Mode',
      safe_mode_desc: 'Safe Mode hides sensitive content from your feed.',
      who_sees_posts: 'Who can see your posts', only_me: 'Only Me',
      change_vis_note: 'Change default post visibility on the Account tab.',
      security_title: 'Security & Profile Images',
      change_bg_img: 'Change Profile Background Image',
      bg_img_tip: 'Use a clean photo so your profile stands out.',
      update_avatar: 'Update Profile Picture',
      zoom: 'Zoom', move_x: 'Move X', move_y: 'Move Y',
      notifications_title: 'Notifications',
      email_notif: 'Email Notifications', live_invites: 'Live Collaboration Invites',
      auto_captions: 'Auto Captions (beta)',
      theme_title: 'Theme & Profile Preview', theme_preset: 'Theme Preset',
      apply_theme: 'Apply Theme Now',
      profile_preview: 'Profile Preview', preview_note: 'This updates live before you save.',
      creator: 'Creator', live_label: 'Live',
      profile_music_title: 'Profile Music',
      profile_music_desc: 'Pick a song clip that plays when people visit your profile.',
      pm_search_placeholder: 'Search any song, artist…',
      currently_set: 'Currently set:', searching: 'Searching…',
      no_results: 'No results.', search_failed: 'Search failed.',
      save_settings: 'Save Settings', back_profile: 'Back to profile', back_feed: 'Back to feed',
      delete_title: 'Delete Account',
      delete_desc: 'This permanently deletes your profile data from this VybeFlow app instance.',
      type_delete: 'Type DELETE to confirm', delete_btn: 'Delete Account',

      /* — Story create — */
      story_create: 'Create story',
      story_composer_desc: 'Instagram-style story composer',
      story_tap_type: 'Tap to type on your story...',
      story_share: 'Share to story', story_draft: 'Save as draft',
      story_back: 'Back to feed',
      st_stickers: 'Stickers', st_search_stickers: 'Search stickers...',
      st_add_music: 'Add Music',
      st_location: 'Location', st_mention: 'Mention', st_hashtag: 'Hashtag',
      st_questions: 'Questions', st_avatar: 'Avatar', st_music: 'Music',
      st_emoji: 'Emoji', st_poll: 'Poll', st_quiz: 'Quiz', st_link: 'Link',
      st_countdown: 'Countdown', st_gif: 'GIF', st_vibe_check: 'Vibe Check',
      st_challenge: 'Challenge', st_dare: 'Dare', st_rating: 'Rating',
      st_timestamp: 'Timestamp', st_weather: 'Weather', st_shoutout: 'Shoutout',
      st_confession: 'Confession', st_mood: 'Mood', st_slider: 'Slider',
      st_collab: 'Collab', st_throwback: 'Throwback', st_aura: 'Aura',
      st_voice_note: 'Voice Note', st_trophy: 'Trophy', st_reaction: 'Reaction',
      st_quote: 'Quote', st_palette: 'Palette', st_todo: 'To-Do',
      st_gift: 'Gift', st_event: 'Event', st_spin: 'Spin', st_tip: 'Tip',
      st_this_or_that: 'This or That',
      tool_text: 'Text', tool_stickers: 'Stickers', tool_music: 'Music',
      tool_restyle: 'Restyle', tool_mention: 'Mention', tool_effects: 'Effects',
      tool_draw: 'Draw', tool_save: 'Save', tool_more: 'More',
      font_neon: 'Neon', font_typewriter: 'Typewriter', font_modern: 'Modern',
      font_strong: 'Strong', font_classic: 'Classic',
      draw_title: 'Draw on story', clear_doodle: 'Clear doodle', save_doodle: 'Save doodle',
      photo_btn: 'Photo / Video', selfie_btn: 'Selfie',
      open_camera: 'Open Camera', snap_photo: 'Snap Photo',
      mode_create: 'Create', mode_boomerang: 'Boomerang', mode_ai: 'AI Images',
      mode_layout: 'Layout', mode_handsfree: 'Hands-free',
      story_rail_title: 'Stories',
      story_rail_sub: 'Tap • Hold • Remix • Drop a beat',

      /* — Games — */
      games_title: 'VybeFlow Games',
      games_subtitle: 'Play classic and retro games right in your browser. Compete with friends!',
      games_back: 'Back to Feed',
      games_play: 'Play Now',
      games_all: 'All Games', games_fighting: 'Fighting', games_arcade: 'Arcade',
      games_puzzle: 'Puzzle', games_sports: 'Sports', games_retro: 'Retro',
      games_leaderboard: 'Top VybeFlow Gamers',
      games_escape: 'Press Escape to close',
      games_controls: 'Arrow keys / WASD to play',
      games_shoot: 'Space to shoot',

      /* — Base / shared — */
      language_label: 'Language:',
      play: 'Play', pause: 'Pause',
    },

    /* ════════════════════════════════════════════════
       ESPAÑOL (Spanish)
       ════════════════════════════════════════════════ */
    es: {
      search_placeholder: 'Buscar en VybeFlow',
      retro_mode: 'Modo 2011',
      nav_home: 'Inicio', nav_explore: 'Explorar', nav_create: 'Crear',
      nav_messenger: 'Mensajes', nav_live: 'En Vivo', nav_account: 'Cuenta',
      nav_settings: 'Ajustes', nav_logout: 'Salir',

      sidebar_you: 'Tú', sidebar_shortcuts: 'Atajos',
      sidebar_quick_actions: 'Acciones Rápidas', sidebar_your_vybes: 'Tus Vibes',
      sidebar_home: 'Inicio', sidebar_explore: 'Explorar', sidebar_create: 'Crear',
      sidebar_view_account: 'Ver Cuenta', sidebar_upload: 'Subir Medios',
      sidebar_messenger: 'Mensajes', sidebar_live_hub: 'Centro En Vivo',
      sidebar_search: 'Buscar', sidebar_settings: 'Ajustes', sidebar_signout: 'Cerrar Sesión',
      sidebar_trap: 'Trap', sidebar_rnb: 'R&B', sidebar_sports: 'Deportes', sidebar_hustle: 'Grind',

      your_story: 'Tu historia', stories: 'Historias',
      vibe_energy: 'Energía Vibe en Vivo', vibe_calculating: 'Calculando vibe...',
      vibe_posts_today: '0 publicaciones hoy',
      whats_on_mind: '¿Qué tienes en mente?',
      composer_placeholder: 'Comparte tu publicación, nota o pregunta...',
      bg_default: 'Fondo: Predeterminado', bg_sunset: 'Fondo: Atardecer',
      bg_neon: 'Fondo: Neón', bg_glass: 'Fondo: Cristal',
      vis_public: 'Visibilidad: Público', vis_followers: 'Visibilidad: Seguidores',
      vis_private: 'Visibilidad: Solo yo (Borrador)',
      publish: 'Publicar',
      photo_video: 'Foto / video', emoji_stickers: 'Emoji / stickers', add_vybe: 'Agregar Vybe',
      vibe_check: 'Chequeo Vibe:', mood_lit: 'Fuego', mood_grinding: 'Enfocado',
      mood_chill: 'Relajado', mood_vibing: 'Vibrando', mood_feels: 'Sentimientos',
      mood_winning: 'Ganando', mood_savage: 'Salvaje',
      confession_mode: 'Modo Confesión',
      confession_desc: 'Publica de forma anónima — tu identidad permanece oculta',
      create_poll: 'Crear Encuesta', ask_question: 'Haz una pregunta...',
      option_a: 'Opción A', option_b: 'Opción B',
      option_c: 'Opción C (opcional)', option_d: 'Opción D (opcional)',
      search_music: 'Buscar Música', close: 'Cerrar',
      music_search_placeholder: 'Busca cualquier canción, artista, género…',
      search_btn: 'Buscar', remove: 'Eliminar', clear: 'Limpiar', upload: 'Subir',
      emoji_panel_title: 'Emoji, stickers y GIFs',
      gif_library: 'Biblioteca GIF', powered_tenor: 'Con tecnología Tenor',
      reels: 'Vibe Snaps', reels_sub: 'Toca • Vista previa • Lanza fuego 🔥',
      for_you: 'Para Ti', chaos: 'Caos', no_reels: 'Sin reels aún — sé el primero.',
      like: 'Me gusta', share: 'Compartir', comment: 'Comentar', save: 'Guardar',

      settings_title: 'Ajustes',
      tab_account: 'Cuenta', tab_privacy: 'Privacidad', tab_security: 'Seguridad',
      tab_notifications: 'Notificaciones', tab_appearance: 'Apariencia',
      tab_profile_music: 'Música de Perfil', tab_delete_account: 'Eliminar Cuenta',
      display_name: 'Nombre para Mostrar', ai_assist: 'Asistente IA en Feed',
      mode_2011: 'Modo 2011 (clásico)', post_visibility: 'Visibilidad Predeterminada',
      public: 'Público', followers: 'Seguidores', private: 'Privado',
      bio_label: 'Biografía de Perfil', bio_placeholder: 'Escribe tu biografía real...',
      safe_mode: 'Modo Seguro',
      safe_mode_desc: 'Modo Seguro oculta contenido sensible de tu feed.',
      who_sees_posts: 'Quién puede ver tus publicaciones', only_me: 'Solo Yo',
      change_vis_note: 'Cambia la visibilidad en la pestaña Cuenta.',
      security_title: 'Seguridad e Imágenes de Perfil',
      change_bg_img: 'Cambiar Imagen de Fondo del Perfil',
      bg_img_tip: 'Usa una foto limpia para que tu perfil destaque.',
      update_avatar: 'Actualizar Foto de Perfil',
      zoom: 'Zoom', move_x: 'Mover X', move_y: 'Mover Y',
      notifications_title: 'Notificaciones',
      email_notif: 'Notificaciones por Email', live_invites: 'Invitaciones en Vivo',
      auto_captions: 'Subtítulos Automáticos (beta)',
      theme_title: 'Tema y Vista Previa del Perfil', theme_preset: 'Tema Preestablecido',
      apply_theme: 'Aplicar Tema Ahora',
      profile_preview: 'Vista Previa del Perfil', preview_note: 'Se actualiza en vivo antes de guardar.',
      creator: 'Creador', live_label: 'En Vivo',
      profile_music_title: 'Música de Perfil',
      profile_music_desc: 'Elige un clip de canción que se reproduce cuando la gente visita tu perfil.',
      pm_search_placeholder: 'Busca cualquier canción, artista…',
      currently_set: 'Actualmente:', searching: 'Buscando…',
      no_results: 'Sin resultados.', search_failed: 'Búsqueda fallida.',
      save_settings: 'Guardar Ajustes', back_profile: 'Volver al perfil', back_feed: 'Volver al feed',
      delete_title: 'Eliminar Cuenta',
      delete_desc: 'Esto elimina permanentemente tus datos de esta instancia de VybeFlow.',
      type_delete: 'Escribe DELETE para confirmar', delete_btn: 'Eliminar Cuenta',

      story_create: 'Crear historia',
      story_composer_desc: 'Compositor de historias estilo Instagram',
      story_tap_type: 'Toca para escribir en tu historia...',
      story_share: 'Compartir historia', story_draft: 'Guardar borrador',
      story_back: 'Volver al feed',
      st_stickers: 'Stickers', st_search_stickers: 'Buscar stickers...',
      st_add_music: 'Agregar Música',
      st_location: 'Ubicación', st_mention: 'Mención', st_hashtag: 'Hashtag',
      st_questions: 'Preguntas', st_avatar: 'Avatar', st_music: 'Música',
      st_emoji: 'Emoji', st_poll: 'Encuesta', st_quiz: 'Quiz', st_link: 'Enlace',
      st_countdown: 'Cuenta Regresiva', st_gif: 'GIF', st_vibe_check: 'Chequeo Vibe',
      st_challenge: 'Desafío', st_dare: 'Reto', st_rating: 'Calificación',
      st_timestamp: 'Hora', st_weather: 'Clima', st_shoutout: 'Shoutout',
      st_confession: 'Confesión', st_mood: 'Ánimo', st_slider: 'Deslizador',
      st_collab: 'Colaboración', st_throwback: 'Recuerdo', st_aura: 'Aura',
      st_voice_note: 'Nota de Voz', st_trophy: 'Trofeo', st_reaction: 'Reacción',
      st_quote: 'Cita', st_palette: 'Paleta', st_todo: 'Pendiente',
      st_gift: 'Regalo', st_event: 'Evento', st_spin: 'Girar', st_tip: 'Consejo',
      st_this_or_that: 'Esto o Aquello',
      tool_text: 'Texto', tool_stickers: 'Stickers', tool_music: 'Música',
      tool_restyle: 'Redibujar', tool_mention: 'Mención', tool_effects: 'Efectos',
      tool_draw: 'Dibujar', tool_save: 'Guardar', tool_more: 'Más',
      font_neon: 'Neón', font_typewriter: 'Máquina', font_modern: 'Moderno',
      font_strong: 'Fuerte', font_classic: 'Clásico',
      draw_title: 'Dibujar en historia', clear_doodle: 'Borrar dibujo', save_doodle: 'Guardar dibujo',
      photo_btn: 'Foto / Video', selfie_btn: 'Selfie',
      open_camera: 'Abrir Cámara', snap_photo: 'Tomar Foto',
      mode_create: 'Crear', mode_boomerang: 'Boomerang', mode_ai: 'Imágenes IA',
      mode_layout: 'Diseño', mode_handsfree: 'Manos Libres',
      story_rail_title: 'Historias',
      story_rail_sub: 'Toca • Mantén • Remix • Lanza un beat',

      games_title: 'Juegos VybeFlow',
      games_subtitle: 'Juega clásicos y retro directamente en tu navegador. ¡Compite con amigos!',
      games_back: 'Volver al Feed',
      games_play: 'Jugar Ahora',
      games_all: 'Todos', games_fighting: 'Lucha', games_arcade: 'Arcade',
      games_puzzle: 'Puzzle', games_sports: 'Deportes', games_retro: 'Retro',
      games_leaderboard: 'Mejores Jugadores de VybeFlow',
      games_escape: 'Presiona Escape para cerrar',
      games_controls: 'Flechas / WASD para jugar',
      games_shoot: 'Espacio para disparar',

      language_label: 'Idioma:',
      play: 'Reproducir', pause: 'Pausar',
    },

    /* ════════════════════════════════════════════════
       FRANÇAIS (French)
       ════════════════════════════════════════════════ */
    fr: {
      search_placeholder: 'Rechercher sur VybeFlow',
      retro_mode: 'Mode 2011',
      nav_home: 'Accueil', nav_explore: 'Explorer', nav_create: 'Créer',
      nav_messenger: 'Messages', nav_live: 'Direct', nav_account: 'Compte',
      nav_settings: 'Paramètres', nav_logout: 'Déconnexion',

      sidebar_you: 'Vous', sidebar_shortcuts: 'Raccourcis',
      sidebar_quick_actions: 'Actions Rapides', sidebar_your_vybes: 'Tes Vybes',
      sidebar_home: 'Accueil', sidebar_explore: 'Explorer', sidebar_create: 'Créer',
      sidebar_view_account: 'Voir le Compte', sidebar_upload: 'Uploader des Médias',
      sidebar_messenger: 'Messages', sidebar_live_hub: 'Hub Direct',
      sidebar_search: 'Rechercher', sidebar_settings: 'Paramètres', sidebar_signout: 'Se Déconnecter',
      sidebar_trap: 'Trap', sidebar_rnb: 'R&B', sidebar_sports: 'Sports', sidebar_hustle: 'Hustle',

      your_story: 'Votre story', stories: 'Stories',
      vibe_energy: 'Énergie Vibe en Direct', vibe_calculating: 'Calcul du vibe...',
      vibe_posts_today: '0 publications aujourd\'hui',
      whats_on_mind: 'Quoi de neuf ?',
      composer_placeholder: 'Partagez votre publication, note ou question...',
      bg_default: 'Fond : Par défaut', bg_sunset: 'Fond : Coucher de soleil',
      bg_neon: 'Fond : Néon', bg_glass: 'Fond : Verre',
      vis_public: 'Visibilité : Public', vis_followers: 'Visibilité : Abonnés',
      vis_private: 'Visibilité : Moi seul (Brouillon)',
      publish: 'Publier',
      photo_video: 'Photo / vidéo', emoji_stickers: 'Emoji / stickers', add_vybe: 'Ajouter un Vybe',
      vibe_check: 'Vibe Check :', mood_lit: 'Feu', mood_grinding: 'Focus',
      mood_chill: 'Zen', mood_vibing: 'En vibration', mood_feels: 'Émotion',
      mood_winning: 'Victoire', mood_savage: 'Sauvage',
      confession_mode: 'Mode Confession',
      confession_desc: 'Publiez anonymement — votre identité reste cachée',
      create_poll: 'Créer un Sondage', ask_question: 'Posez une question...',
      option_a: 'Option A', option_b: 'Option B',
      option_c: 'Option C (facultatif)', option_d: 'Option D (facultatif)',
      search_music: 'Rechercher Musique', close: 'Fermer',
      music_search_placeholder: 'Recherchez chanson, artiste, genre…',
      search_btn: 'Rechercher', remove: 'Supprimer', clear: 'Effacer', upload: 'Uploader',
      emoji_panel_title: 'Emoji, stickers et GIFs',
      gif_library: 'Bibliothèque GIF', powered_tenor: 'Propulsé par Tenor',
      reels: 'Vibe Snaps', reels_sub: 'Appuyez • Aperçu • Lâchez le feu 🔥',
      for_you: 'Pour Vous', chaos: 'Chaos', no_reels: 'Pas de reels encore — soyez le premier.',
      like: 'J\'aime', share: 'Partager', comment: 'Commenter', save: 'Sauvegarder',

      settings_title: 'Paramètres',
      tab_account: 'Compte', tab_privacy: 'Confidentialité', tab_security: 'Sécurité',
      tab_notifications: 'Notifications', tab_appearance: 'Apparence',
      tab_profile_music: 'Musique du Profil', tab_delete_account: 'Supprimer le Compte',
      display_name: 'Nom affiché', ai_assist: 'Assistant IA sur le fil',
      mode_2011: 'Mode 2011 (classique)', post_visibility: 'Visibilité par défaut',
      public: 'Public', followers: 'Abonnés', private: 'Privé',
      bio_label: 'Bio du Profil', bio_placeholder: 'Écrivez votre vraie bio...',
      safe_mode: 'Mode Sûr',
      safe_mode_desc: 'Le Mode Sûr masque le contenu sensible de votre fil.',
      who_sees_posts: 'Qui voit vos publications', only_me: 'Moi seul',
      change_vis_note: 'Changez la visibilité dans l\'onglet Compte.',
      security_title: 'Sécurité et Images du Profil',
      change_bg_img: 'Changer l\'image de fond du profil',
      bg_img_tip: 'Utilisez une photo nette pour que votre profil se démarque.',
      update_avatar: 'Mettre à jour la photo de profil',
      zoom: 'Zoom', move_x: 'Déplacer X', move_y: 'Déplacer Y',
      notifications_title: 'Notifications',
      email_notif: 'Notifications par email', live_invites: 'Invitations en direct',
      auto_captions: 'Sous-titres auto (bêta)',
      theme_title: 'Thème et Aperçu du Profil', theme_preset: 'Thème prédéfini',
      apply_theme: 'Appliquer le Thème',
      profile_preview: 'Aperçu du Profil', preview_note: 'Se met à jour en direct.',
      creator: 'Créateur', live_label: 'Direct',
      profile_music_title: 'Musique du Profil',
      profile_music_desc: 'Choisissez un extrait qui joue quand on visite votre profil.',
      pm_search_placeholder: 'Recherchez chanson, artiste…',
      currently_set: 'Actuellement :', searching: 'Recherche…',
      no_results: 'Aucun résultat.', search_failed: 'Échec de la recherche.',
      save_settings: 'Enregistrer', back_profile: 'Retour au profil', back_feed: 'Retour au fil',
      delete_title: 'Supprimer le Compte',
      delete_desc: 'Ceci supprime définitivement vos données de cette instance VybeFlow.',
      type_delete: 'Tapez DELETE pour confirmer', delete_btn: 'Supprimer le Compte',

      story_create: 'Créer une story',
      story_composer_desc: 'Compositeur de stories style Instagram',
      story_tap_type: 'Appuyez pour écrire sur votre story...',
      story_share: 'Partager la story', story_draft: 'Sauver en brouillon',
      story_back: 'Retour au fil',
      st_stickers: 'Stickers', st_search_stickers: 'Rechercher stickers...',
      st_add_music: 'Ajouter Musique',
      st_location: 'Lieu', st_mention: 'Mention', st_hashtag: 'Hashtag',
      st_questions: 'Questions', st_avatar: 'Avatar', st_music: 'Musique',
      st_emoji: 'Emoji', st_poll: 'Sondage', st_quiz: 'Quiz', st_link: 'Lien',
      st_countdown: 'Compte à Rebours', st_gif: 'GIF', st_vibe_check: 'Vibe Check',
      st_challenge: 'Défi', st_dare: 'Oser', st_rating: 'Note',
      st_timestamp: 'Heure', st_weather: 'Météo', st_shoutout: 'Shoutout',
      st_confession: 'Confession', st_mood: 'Humeur', st_slider: 'Curseur',
      st_collab: 'Collab', st_throwback: 'Souvenir', st_aura: 'Aura',
      st_voice_note: 'Note Vocale', st_trophy: 'Trophée', st_reaction: 'Réaction',
      st_quote: 'Citation', st_palette: 'Palette', st_todo: 'À Faire',
      st_gift: 'Cadeau', st_event: 'Événement', st_spin: 'Tourner', st_tip: 'Astuce',
      st_this_or_that: 'Ceci ou Cela',
      tool_text: 'Texte', tool_stickers: 'Stickers', tool_music: 'Musique',
      tool_restyle: 'Restyler', tool_mention: 'Mention', tool_effects: 'Effets',
      tool_draw: 'Dessiner', tool_save: 'Sauver', tool_more: 'Plus',
      font_neon: 'Néon', font_typewriter: 'Machine', font_modern: 'Moderne',
      font_strong: 'Fort', font_classic: 'Classique',
      draw_title: 'Dessiner sur la story', clear_doodle: 'Effacer', save_doodle: 'Sauver dessin',
      photo_btn: 'Photo / Vidéo', selfie_btn: 'Selfie',
      open_camera: 'Ouvrir Caméra', snap_photo: 'Prendre Photo',
      mode_create: 'Créer', mode_boomerang: 'Boomerang', mode_ai: 'Images IA',
      mode_layout: 'Mise en page', mode_handsfree: 'Mains Libres',
      story_rail_title: 'Stories',
      story_rail_sub: 'Appuyez • Maintenez • Remix • Un beat',

      games_title: 'Jeux VybeFlow',
      games_subtitle: 'Jouez aux classiques et rétro directement dans votre navigateur. Défiez vos amis !',
      games_back: 'Retour au Fil',
      games_play: 'Jouer',
      games_all: 'Tous', games_fighting: 'Combat', games_arcade: 'Arcade',
      games_puzzle: 'Puzzle', games_sports: 'Sports', games_retro: 'Rétro',
      games_leaderboard: 'Meilleurs Joueurs VybeFlow',
      games_escape: 'Appuyez sur Échap pour fermer',
      games_controls: 'Flèches / WASD pour jouer',
      games_shoot: 'Espace pour tirer',

      language_label: 'Langue :',
      play: 'Lecture', pause: 'Pause',
    },

    /* ════════════════════════════════════════════════
       PORTUGUÊS (Portuguese)
       ════════════════════════════════════════════════ */
    pt: {
      search_placeholder: 'Buscar no VybeFlow',
      retro_mode: 'Modo 2011',
      nav_home: 'Início', nav_explore: 'Explorar', nav_create: 'Criar',
      nav_messenger: 'Mensagens', nav_live: 'Ao Vivo', nav_account: 'Conta',
      nav_settings: 'Configurações', nav_logout: 'Sair',

      sidebar_you: 'Você', sidebar_shortcuts: 'Atalhos',
      sidebar_quick_actions: 'Ações Rápidas', sidebar_your_vybes: 'Seus Vybes',
      sidebar_home: 'Início', sidebar_explore: 'Explorar', sidebar_create: 'Criar',
      sidebar_view_account: 'Ver Conta', sidebar_upload: 'Enviar Mídia',
      sidebar_messenger: 'Mensagens', sidebar_live_hub: 'Hub Ao Vivo',
      sidebar_search: 'Buscar', sidebar_settings: 'Configurações', sidebar_signout: 'Sair da Conta',
      sidebar_trap: 'Trap', sidebar_rnb: 'R&B', sidebar_sports: 'Esportes', sidebar_hustle: 'Corre',

      your_story: 'Seu story', stories: 'Stories',
      vibe_energy: 'Energia Vibe Ao Vivo', vibe_calculating: 'Calculando vibe...',
      vibe_posts_today: '0 publicações hoje',
      whats_on_mind: 'O que está pensando?',
      composer_placeholder: 'Compartilhe sua publicação, nota ou pergunta...',
      bg_default: 'Fundo: Padrão', bg_sunset: 'Fundo: Pôr do Sol',
      bg_neon: 'Fundo: Neon', bg_glass: 'Fundo: Vidro',
      vis_public: 'Visibilidade: Público', vis_followers: 'Visibilidade: Seguidores',
      vis_private: 'Visibilidade: Só eu (Rascunho)',
      publish: 'Publicar',
      photo_video: 'Foto / vídeo', emoji_stickers: 'Emoji / stickers', add_vybe: 'Adicionar Vybe',
      vibe_check: 'Vibe Check:', mood_lit: 'Fogo', mood_grinding: 'Focado',
      mood_chill: 'De boa', mood_vibing: 'Vibrando', mood_feels: 'Sentimentos',
      mood_winning: 'Vencendo', mood_savage: 'Selvagem',
      confession_mode: 'Modo Confissão',
      confession_desc: 'Publique anonimamente — sua identidade fica oculta',
      create_poll: 'Criar Enquete', ask_question: 'Faça uma pergunta...',
      option_a: 'Opção A', option_b: 'Opção B',
      option_c: 'Opção C (opcional)', option_d: 'Opção D (opcional)',
      search_music: 'Buscar Música', close: 'Fechar',
      music_search_placeholder: 'Busque qualquer música, artista, gênero…',
      search_btn: 'Buscar', remove: 'Remover', clear: 'Limpar', upload: 'Enviar',
      emoji_panel_title: 'Emoji, stickers e GIFs',
      gif_library: 'Biblioteca GIF', powered_tenor: 'Powered by Tenor',
      reels: 'Vibe Snaps', reels_sub: 'Toque • Prévia • Solte o fogo 🔥',
      for_you: 'Para Você', chaos: 'Caos', no_reels: 'Sem reels ainda — seja o primeiro.',
      like: 'Curtir', share: 'Compartilhar', comment: 'Comentar', save: 'Salvar',

      settings_title: 'Configurações',
      tab_account: 'Conta', tab_privacy: 'Privacidade', tab_security: 'Segurança',
      tab_notifications: 'Notificações', tab_appearance: 'Aparência',
      tab_profile_music: 'Música do Perfil', tab_delete_account: 'Excluir Conta',
      display_name: 'Nome de Exibição', ai_assist: 'Assistente IA no Feed',
      mode_2011: 'Modo 2011 (clássico)', post_visibility: 'Visibilidade Padrão',
      public: 'Público', followers: 'Seguidores', private: 'Privado',
      bio_label: 'Bio do Perfil', bio_placeholder: 'Escreva sua bio real...',
      safe_mode: 'Modo Seguro',
      safe_mode_desc: 'Modo Seguro oculta conteúdo sensível do seu feed.',
      who_sees_posts: 'Quem pode ver seus posts', only_me: 'Só Eu',
      change_vis_note: 'Altere a visibilidade na aba Conta.',
      security_title: 'Segurança e Imagens do Perfil',
      change_bg_img: 'Alterar Imagem de Fundo do Perfil',
      bg_img_tip: 'Use uma foto limpa para seu perfil se destacar.',
      update_avatar: 'Atualizar Foto de Perfil',
      zoom: 'Zoom', move_x: 'Mover X', move_y: 'Mover Y',
      notifications_title: 'Notificações',
      email_notif: 'Notificações por Email', live_invites: 'Convites Ao Vivo',
      auto_captions: 'Legendas Automáticas (beta)',
      theme_title: 'Tema e Prévia do Perfil', theme_preset: 'Tema Predefinido',
      apply_theme: 'Aplicar Tema Agora',
      profile_preview: 'Prévia do Perfil', preview_note: 'Atualiza ao vivo antes de salvar.',
      creator: 'Criador', live_label: 'Ao Vivo',
      profile_music_title: 'Música do Perfil',
      profile_music_desc: 'Escolha um trecho que toca quando visitam seu perfil.',
      pm_search_placeholder: 'Busque música, artista…',
      currently_set: 'Atualmente:', searching: 'Buscando…',
      no_results: 'Sem resultados.', search_failed: 'Busca falhou.',
      save_settings: 'Salvar Configurações', back_profile: 'Voltar ao perfil', back_feed: 'Voltar ao feed',
      delete_title: 'Excluir Conta',
      delete_desc: 'Isso exclui permanentemente seus dados desta instância VybeFlow.',
      type_delete: 'Digite DELETE para confirmar', delete_btn: 'Excluir Conta',

      story_create: 'Criar story',
      story_composer_desc: 'Compositor de stories estilo Instagram',
      story_tap_type: 'Toque para escrever no story...',
      story_share: 'Compartilhar story', story_draft: 'Salvar rascunho',
      story_back: 'Voltar ao feed',
      st_stickers: 'Stickers', st_search_stickers: 'Buscar stickers...',
      st_add_music: 'Adicionar Música',
      st_location: 'Local', st_mention: 'Menção', st_hashtag: 'Hashtag',
      st_questions: 'Perguntas', st_avatar: 'Avatar', st_music: 'Música',
      st_emoji: 'Emoji', st_poll: 'Enquete', st_quiz: 'Quiz', st_link: 'Link',
      st_countdown: 'Contagem Regressiva', st_gif: 'GIF', st_vibe_check: 'Vibe Check',
      st_challenge: 'Desafio', st_dare: 'Ousa', st_rating: 'Avaliação',
      st_timestamp: 'Hora', st_weather: 'Clima', st_shoutout: 'Shoutout',
      st_confession: 'Confissão', st_mood: 'Humor', st_slider: 'Slider',
      st_collab: 'Collab', st_throwback: 'Memória', st_aura: 'Aura',
      st_voice_note: 'Nota de Voz', st_trophy: 'Troféu', st_reaction: 'Reação',
      st_quote: 'Citação', st_palette: 'Paleta', st_todo: 'Pendência',
      st_gift: 'Presente', st_event: 'Evento', st_spin: 'Girar', st_tip: 'Dica',
      st_this_or_that: 'Isso ou Aquilo',
      tool_text: 'Texto', tool_stickers: 'Stickers', tool_music: 'Música',
      tool_restyle: 'Restylar', tool_mention: 'Menção', tool_effects: 'Efeitos',
      tool_draw: 'Desenhar', tool_save: 'Salvar', tool_more: 'Mais',
      font_neon: 'Neon', font_typewriter: 'Máquina', font_modern: 'Moderno',
      font_strong: 'Forte', font_classic: 'Clássico',
      draw_title: 'Desenhar no story', clear_doodle: 'Limpar desenho', save_doodle: 'Salvar desenho',
      photo_btn: 'Foto / Vídeo', selfie_btn: 'Selfie',
      open_camera: 'Abrir Câmera', snap_photo: 'Tirar Foto',
      mode_create: 'Criar', mode_boomerang: 'Boomerang', mode_ai: 'Imagens IA',
      mode_layout: 'Layout', mode_handsfree: 'Sem Mãos',
      story_rail_title: 'Stories',
      story_rail_sub: 'Toque • Segure • Remix • Solte o beat',

      games_title: 'Jogos VybeFlow',
      games_subtitle: 'Jogue clássicos e retrô direto no navegador. Compita com amigos!',
      games_back: 'Voltar ao Feed',
      games_play: 'Jogar Agora',
      games_all: 'Todos', games_fighting: 'Luta', games_arcade: 'Arcade',
      games_puzzle: 'Puzzle', games_sports: 'Esportes', games_retro: 'Retrô',
      games_leaderboard: 'Melhores Jogadores VybeFlow',
      games_escape: 'Pressione Escape para fechar',
      games_controls: 'Setas / WASD para jogar',
      games_shoot: 'Espaço para atirar',

      language_label: 'Idioma:',
      play: 'Reproduzir', pause: 'Pausar',
    },

    /* ════════════════════════════════════════════════
       KISWAHILI (Swahili)
       ════════════════════════════════════════════════ */
    sw: {
      search_placeholder: 'Tafuta kwenye VybeFlow',
      retro_mode: 'Hali ya 2011',
      nav_home: 'Nyumbani', nav_explore: 'Chunguza', nav_create: 'Tengeneza',
      nav_messenger: 'Ujumbe', nav_live: 'Moja kwa Moja', nav_account: 'Akaunti',
      nav_settings: 'Mipangilio', nav_logout: 'Ondoka',

      sidebar_you: 'Wewe', sidebar_shortcuts: 'Njia za Mkato',
      sidebar_quick_actions: 'Vitendo vya Haraka', sidebar_your_vybes: 'Vybes Zako',
      sidebar_home: 'Nyumbani', sidebar_explore: 'Chunguza', sidebar_create: 'Tengeneza',
      sidebar_view_account: 'Angalia Akaunti', sidebar_upload: 'Pakia Medianathi',
      sidebar_messenger: 'Ujumbe', sidebar_live_hub: 'Kituo cha Moja kwa Moja',
      sidebar_search: 'Tafuta', sidebar_settings: 'Mipangilio', sidebar_signout: 'Ondoka',
      sidebar_trap: 'Trap', sidebar_rnb: 'R&B', sidebar_sports: 'Michezo', sidebar_hustle: 'Hustle',

      your_story: 'Hadithi yako', stories: 'Hadithi',
      vibe_energy: 'Nishati ya Vibe', vibe_calculating: 'Inahesabu vibe...',
      vibe_posts_today: '0 machapisho leo',
      whats_on_mind: 'Una nini akilini?',
      composer_placeholder: 'Shiriki chapisho, maelezo au swali...',
      bg_default: 'Mandhari: Chaguo msingi', bg_sunset: 'Mandhari: Machweo',
      bg_neon: 'Mandhari: Neon', bg_glass: 'Mandhari: Kioo',
      vis_public: 'Mwonekano: Umma', vis_followers: 'Mwonekano: Wafuasi',
      vis_private: 'Mwonekano: Mimi tu (Rasimu)',
      publish: 'Chapisha',
      photo_video: 'Picha / video', emoji_stickers: 'Emoji / stickers', add_vybe: 'Ongeza Vybe',
      vibe_check: 'Vibe Check:', mood_lit: 'Moto', mood_grinding: 'Kuchapa',
      mood_chill: 'Relax', mood_vibing: 'Vibe', mood_feels: 'Hisia',
      mood_winning: 'Kushinda', mood_savage: 'Mkali',
      confession_mode: 'Hali ya Kukiri',
      confession_desc: 'Chapisha kwa faragha — utambulisho wako unafichwa',
      create_poll: 'Unda Kura', ask_question: 'Uliza swali...',
      option_a: 'Chaguo A', option_b: 'Chaguo B',
      option_c: 'Chaguo C (hiari)', option_d: 'Chaguo D (hiari)',
      search_music: 'Tafuta Muziki', close: 'Funga',
      music_search_placeholder: 'Tafuta wimbo, msanii, aina…',
      search_btn: 'Tafuta', remove: 'Ondoa', clear: 'Futa', upload: 'Pakia',
      emoji_panel_title: 'Emoji, stickers na GIFs',
      gif_library: 'Maktaba ya GIF', powered_tenor: 'Kwa Tenor',
      reels: 'Vibe Snaps', reels_sub: 'Gusa • Hakiki • Tupa moto 🔥',
      for_you: 'Kwako', chaos: 'Chaos', no_reels: 'Hakuna reels bado — kuwa wa kwanza.',
      like: 'Penda', share: 'Shiriki', comment: 'Toa maoni', save: 'Hifadhi',

      settings_title: 'Mipangilio',
      tab_account: 'Akaunti', tab_privacy: 'Faragha', tab_security: 'Usalama',
      tab_notifications: 'Arifa', tab_appearance: 'Mwonekano',
      tab_profile_music: 'Muziki wa Profaili', tab_delete_account: 'Futa Akaunti',
      display_name: 'Jina la Kuonyesha', ai_assist: 'Msaidizi wa AI kwenye Feed',
      mode_2011: 'Hali ya 2011 (klasiki)', post_visibility: 'Mwonekano wa Chapisho',
      public: 'Umma', followers: 'Wafuasi', private: 'Binafsi',
      bio_label: 'Bio ya Profaili', bio_placeholder: 'Andika bio yako halisi...',
      safe_mode: 'Hali Salama',
      safe_mode_desc: 'Hali Salama inaficha maudhui nyeti kutoka feed yako.',
      who_sees_posts: 'Nani anaweza kuona machapisho yako', only_me: 'Mimi Tu',
      change_vis_note: 'Badilisha mwonekano kwenye kichupo cha Akaunti.',
      security_title: 'Usalama na Picha za Profaili',
      change_bg_img: 'Badilisha Picha ya Mandhari ya Profaili',
      bg_img_tip: 'Tumia picha safi ili profaili yako ionekane vizuri.',
      update_avatar: 'Sasisha Picha ya Profaili',
      zoom: 'Kukuza', move_x: 'Sogeza X', move_y: 'Sogeza Y',
      notifications_title: 'Arifa',
      email_notif: 'Arifa za Email', live_invites: 'Mialiko ya Moja kwa Moja',
      auto_captions: 'Manukuu ya Kiotomatiki (beta)',
      theme_title: 'Mandhari na Hakiki ya Profaili', theme_preset: 'Mandhari Iliyowekwa',
      apply_theme: 'Tumia Mandhari Sasa',
      profile_preview: 'Hakiki ya Profaili', preview_note: 'Inasasishwa moja kwa moja.',
      creator: 'Muundaji', live_label: 'Moja kwa Moja',
      profile_music_title: 'Muziki wa Profaili',
      profile_music_desc: 'Chagua kipande cha wimbo kinachochezwa watu wanapokutemblea.',
      pm_search_placeholder: 'Tafuta wimbo, msanii…',
      currently_set: 'Sasa hivi:', searching: 'Inatafuta…',
      no_results: 'Hakuna matokeo.', search_failed: 'Tafuta imeshindikana.',
      save_settings: 'Hifadhi Mipangilio', back_profile: 'Rudi kwenye profaili', back_feed: 'Rudi kwenye feed',
      delete_title: 'Futa Akaunti',
      delete_desc: 'Hii inafuta data yako kabisa kutoka kwenye VybeFlow.',
      type_delete: 'Andika DELETE kuthibitisha', delete_btn: 'Futa Akaunti',

      story_create: 'Unda hadithi',
      story_composer_desc: 'Muundaji wa hadithi mtindo wa Instagram',
      story_tap_type: 'Gusa kuandika hadithi yako...',
      story_share: 'Shiriki hadithi', story_draft: 'Hifadhi rasimu',
      story_back: 'Rudi kwenye feed',
      st_stickers: 'Stickers', st_search_stickers: 'Tafuta stickers...',
      st_add_music: 'Ongeza Muziki',
      st_location: 'Mahali', st_mention: 'Tajwa', st_hashtag: 'Hashtag',
      st_questions: 'Maswali', st_avatar: 'Avatar', st_music: 'Muziki',
      st_emoji: 'Emoji', st_poll: 'Kura', st_quiz: 'Jaribio', st_link: 'Kiungo',
      st_countdown: 'Kuhesabu Chini', st_gif: 'GIF', st_vibe_check: 'Vibe Check',
      st_challenge: 'Changamoto', st_dare: 'Thubutu', st_rating: 'Ukadiriaji',
      st_timestamp: 'Muda', st_weather: 'Hali ya Hewa', st_shoutout: 'Shoutout',
      st_confession: 'Kukiri', st_mood: 'Hali', st_slider: 'Slider',
      st_collab: 'Ushirikiano', st_throwback: 'Kumbukumbu', st_aura: 'Aura',
      st_voice_note: 'Ujumbe wa Sauti', st_trophy: 'Tuzo', st_reaction: 'Majibu',
      st_quote: 'Nukuu', st_palette: 'Palette', st_todo: 'Ya Kufanya',
      st_gift: 'Zawadi', st_event: 'Tukio', st_spin: 'Zungusha', st_tip: 'Kidokezo',
      st_this_or_that: 'Hii au Ile',
      tool_text: 'Maandishi', tool_stickers: 'Stickers', tool_music: 'Muziki',
      tool_restyle: 'Pamba', tool_mention: 'Tajwa', tool_effects: 'Athari',
      tool_draw: 'Chora', tool_save: 'Hifadhi', tool_more: 'Zaidi',
      font_neon: 'Neon', font_typewriter: 'Taipraita', font_modern: 'Kisasa',
      font_strong: 'Nguvu', font_classic: 'Klasiki',
      draw_title: 'Chora kwenye hadithi', clear_doodle: 'Futa mchoro', save_doodle: 'Hifadhi mchoro',
      photo_btn: 'Picha / Video', selfie_btn: 'Selfie',
      open_camera: 'Fungua Kamera', snap_photo: 'Piga Picha',
      mode_create: 'Tengeneza', mode_boomerang: 'Boomerang', mode_ai: 'Picha za AI',
      mode_layout: 'Mpangilio', mode_handsfree: 'Bila Mikono',
      story_rail_title: 'Hadithi',
      story_rail_sub: 'Gusa • Shika • Remix • Beat',

      games_title: 'Michezo ya VybeFlow',
      games_subtitle: 'Cheza michezo ya zamani kwenye kivinjari chako. Shindana na marafiki!',
      games_back: 'Rudi Feed',
      games_play: 'Cheza Sasa',
      games_all: 'Yote', games_fighting: 'Mapigano', games_arcade: 'Arcade',
      games_puzzle: 'Fumbo', games_sports: 'Michezo', games_retro: 'Retro',
      games_leaderboard: 'Wachezaji Bora wa VybeFlow',
      games_escape: 'Bonyeza Escape kufunga',
      games_controls: 'Mishale / WASD kucheza',
      games_shoot: 'Nafasi kupiga risasi',

      language_label: 'Lugha:',
      play: 'Cheza', pause: 'Simamisha',
    }
  };

  /* ──────────────────────────────────────────────
     Apply translations to page
     ────────────────────────────────────────────── */
  function applyAppLang(lang) {
    var dict = T[lang] || T.en;
    var fallback = T.en;

    /* data-i18n → textContent */
    document.querySelectorAll('[data-i18n]').forEach(function (el) {
      var key = el.getAttribute('data-i18n');
      if (dict[key] !== undefined) {
        el.textContent = dict[key];
      } else if (fallback[key] !== undefined) {
        el.textContent = fallback[key];
      }
    });

    /* data-i18n-placeholder → placeholder attr */
    document.querySelectorAll('[data-i18n-placeholder]').forEach(function (el) {
      var key = el.getAttribute('data-i18n-placeholder');
      if (dict[key] !== undefined) {
        el.setAttribute('placeholder', dict[key]);
      } else if (fallback[key] !== undefined) {
        el.setAttribute('placeholder', fallback[key]);
      }
    });

    /* data-i18n-title → title attr */
    document.querySelectorAll('[data-i18n-title]').forEach(function (el) {
      var key = el.getAttribute('data-i18n-title');
      if (dict[key] !== undefined) {
        el.setAttribute('title', dict[key]);
      } else if (fallback[key] !== undefined) {
        el.setAttribute('title', fallback[key]);
      }
    });

    /* data-i18n-aria → aria-label attr */
    document.querySelectorAll('[data-i18n-aria]').forEach(function (el) {
      var key = el.getAttribute('data-i18n-aria');
      if (dict[key] !== undefined) {
        el.setAttribute('aria-label', dict[key]);
      } else if (fallback[key] !== undefined) {
        el.setAttribute('aria-label', fallback[key]);
      }
    });

    /* data-i18n-dataph → data-placeholder attr (CSS content: attr(data-placeholder)) */
    document.querySelectorAll('[data-i18n-dataph]').forEach(function (el) {
      var key = el.getAttribute('data-i18n-dataph');
      if (dict[key] !== undefined) {
        el.setAttribute('data-placeholder', dict[key]);
      } else if (fallback[key] !== undefined) {
        el.setAttribute('data-placeholder', fallback[key]);
      }
    });

    /* data-i18n-html → innerHTML (for emoji prefixed strings) */
    document.querySelectorAll('[data-i18n-html]').forEach(function (el) {
      var key = el.getAttribute('data-i18n-html');
      var ico = el.getAttribute('data-i18n-icon') || '';
      if (dict[key] !== undefined) {
        el.innerHTML = ico ? (ico + ' ' + dict[key]) : dict[key];
      } else if (fallback[key] !== undefined) {
        el.innerHTML = ico ? (ico + ' ' + fallback[key]) : fallback[key];
      }
    });

    /* data-i18n-value → option.textContent for <option> inside <select> */
    document.querySelectorAll('option[data-i18n]').forEach(function (opt) {
      var key = opt.getAttribute('data-i18n');
      if (dict[key] !== undefined) {
        opt.textContent = dict[key];
      } else if (fallback[key] !== undefined) {
        opt.textContent = fallback[key];
      }
    });

    /* Update <html lang=""> */
    document.documentElement.lang = lang;

    /* Highlight active chip */
    document.querySelectorAll('.lang-chip-btn').forEach(function (btn) {
      btn.classList.toggle('chip-active', btn.getAttribute('data-lang') === lang);
    });
  }

  /* ──────────────────────────────────────────────
     Boot: read stored lang & apply
     ────────────────────────────────────────────── */
  function boot() {
    var lang = window.localStorage.getItem(LANG_KEY) || 'en';
    applyAppLang(lang);

    /* Hook into existing language chip buttons */
    document.querySelectorAll('.lang-chip-btn').forEach(function (btn) {
      btn.addEventListener('click', function (e) {
        e.preventDefault();
        var chosen = btn.getAttribute('data-lang') || 'en';
        window.localStorage.setItem(LANG_KEY, chosen);
        applyAppLang(chosen);
      });
    });
  }

  /* Run on DOM ready */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }

  /* Expose for programmatic use */
  window.VybeI18N = { apply: applyAppLang, translations: T };
})();
