(function () {
    if (!document.body.classList.contains('feed-page')) return;

    const storyButtons = Array.from(document.querySelectorAll('.story-view'));
    const viewer = document.getElementById('story-viewer');
    const closeViewerBtn = document.getElementById('close-story-viewer');
    const progressBar = document.getElementById('story-progress-bar');
    const storyImage = document.getElementById('story-image');
    const storyUser = document.getElementById('story-user');
    const storyCaption = document.getElementById('story-caption');
    const autoFixBtn = document.getElementById('auto-fix-feed');
    const status = document.getElementById('feed-fix-status');

    let activeStoryIndex = -1;
    let storyTimer = null;

    function setStatus(message) {
        if (!status) return;
        status.textContent = message;
    }

    function closeViewer() {
        if (!viewer) return;
        viewer.hidden = true;
        document.body.style.overflow = '';
        if (storyTimer) {
            window.clearTimeout(storyTimer);
            storyTimer = null;
        }
    }

    function openStoryAt(index) {
        if (!viewer || !storyButtons.length) return;
        activeStoryIndex = index;
        const story = storyButtons[index];
        if (!story) return;

        const image = story.dataset.storyImage || '';
        const user = story.dataset.storyUser || 'Story';
        const caption = story.dataset.storyCaption || 'Latest update.';

        storyImage.src = image;
        storyImage.alt = `${user} story`;
        storyUser.textContent = user;
        storyCaption.textContent = caption;

        viewer.hidden = false;
        document.body.style.overflow = 'hidden';

        progressBar.style.transition = 'none';
        progressBar.style.width = '0';
        window.requestAnimationFrame(function () {
            progressBar.style.transition = 'width 4s linear';
            progressBar.style.width = '100%';
        });

        if (storyTimer) window.clearTimeout(storyTimer);
        storyTimer = window.setTimeout(function () {
            const nextIndex = activeStoryIndex + 1;
            if (nextIndex < storyButtons.length) {
                openStoryAt(nextIndex);
            } else {
                closeViewer();
            }
        }, 4000);
    }

    storyButtons.forEach(function (button, index) {
        button.addEventListener('click', function () {
            openStoryAt(index);
        });
    });

    if (closeViewerBtn) {
        closeViewerBtn.addEventListener('click', closeViewer);
    }

    if (viewer) {
        viewer.addEventListener('click', function (event) {
            if (event.target === viewer) {
                closeViewer();
            }
        });
    }

    document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape' && viewer && !viewer.hidden) {
            closeViewer();
        }
    });

    document.querySelectorAll('.post-action-btn').forEach(function (button) {
        button.addEventListener('click', function () {
            const action = button.dataset.action;
            button.classList.toggle('active');

            if (action === 'like') {
                const countNode = button.querySelector('.count');
                if (countNode) {
                    const current = parseInt(countNode.textContent, 10) || 0;
                    countNode.textContent = button.classList.contains('active') ? current + 1 : Math.max(current - 1, 0);
                }
            }

            if (action === 'comment') {
                window.alert('Comments are now enabled in UI mode. Backend threading can be added next.');
            }

            if (action === 'share') {
                const shareUrl = window.location.href;
                if (navigator.clipboard && navigator.clipboard.writeText) {
                    navigator.clipboard.writeText(shareUrl).then(function () {
                        setStatus('Post link copied to clipboard.');
                    }).catch(function () {
                        setStatus('Share action is active. Copy this URL manually.');
                    });
                } else {
                    setStatus('Share action is active. Copy this URL manually.');
                }
            }
        });
    });

    function applyAutoFixes() {
        let fixes = 0;

        storyButtons.forEach(function (story) {
            if (!story.dataset.storyUser) {
                story.dataset.storyUser = 'Story';
                fixes += 1;
            }
            if (!story.dataset.storyCaption) {
                story.dataset.storyCaption = 'Latest update.';
                fixes += 1;
            }
            if (!story.dataset.storyImage) {
                story.dataset.storyImage = '/static/VFlogo_clean.png';
                fixes += 1;
            }
        });

        document.querySelectorAll('img').forEach(function (img) {
            img.addEventListener('error', function () {
                if (!img.dataset.fallbackApplied) {
                    img.dataset.fallbackApplied = 'true';
                    img.src = '/static/VFlogo_clean.png';
                }
            });
        });

        document.querySelectorAll('.post-action-btn').forEach(function (button) {
            if (button.getAttribute('type') !== 'button') {
                button.setAttribute('type', 'button');
                fixes += 1;
            }
        });

        setStatus(fixes > 0 ? `Auto Fix complete: ${fixes} feed issue(s) repaired.` : 'Auto Fix complete: no feed issues detected.');
    }

    if (autoFixBtn) {
        autoFixBtn.addEventListener('click', applyAutoFixes);
    }
})();
