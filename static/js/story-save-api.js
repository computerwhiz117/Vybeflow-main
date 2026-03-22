/**
 * VybeFlow Story Save API Client
 * Example usage for /api/story/save endpoint
 */

// Example 1: Save story draft with basic content
async function saveStoryBasic(storyId, content) {
    try {
        const response = await fetch("/api/story/save", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                story_id: storyId,
                content: content
            })
        });
        
        const data = await response.json();
        
        if (data.ok) {
            console.log("✓ Story saved at:", data.saved_at);
            return data;
        } else {
            console.error("✗ Save failed:", data.error);
            throw new Error(data.error);
        }
    } catch (error) {
        console.error("Network error:", error);
        throw error;
    }
}

// Example 2: Save complete story with all fields
async function saveStoryComplete(storyData) {
    try {
        const response = await fetch("/api/story/save", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            credentials: "same-origin", // Include session cookies
            body: JSON.stringify({
                story_id: storyData.id,
                content: storyData.content,
                caption: storyData.caption,
                media_url: storyData.mediaUrl,
                overlays_json: storyData.overlays,
                music_track: storyData.musicTrack
            })
        });
        
        if (!response.ok) {
            if (response.status === 401) {
                throw new Error("Not logged in. Please login first.");
            }
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        return data;
        
    } catch (error) {
        console.error("Failed to save story:", error.message);
        throw error;
    }
}

// Example 3: Auto-save with debouncing (saves 2 seconds after user stops editing)
class StoryAutoSaver {
    constructor(storyId, saveInterval = 2000) {
        this.storyId = storyId;
        this.saveInterval = saveInterval;
        this.saveTimeout = null;
        this.isSaving = false;
    }
    
    // Queue a save (debounced)
    queueSave(storyData) {
        // Clear previous timeout
        if (this.saveTimeout) {
            clearTimeout(this.saveTimeout);
        }
        
        // Queue new save
        this.saveTimeout = setTimeout(() => {
            this.save(storyData);
        }, this.saveInterval);
    }
    
    // Immediate save
    async save(storyData) {
        if (this.isSaving) {
            console.log("Save already in progress, skipping...");
            return;
        }
        
        this.isSaving = true;
        
        try {
            const response = await fetch("/api/story/save", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                credentials: "same-origin",
                body: JSON.stringify({
                    story_id: this.storyId,
                    ...storyData
                })
            });
            
            const data = await response.json();
            
            if (data.ok) {
                console.log("✓ Auto-saved:", new Date(data.saved_at).toLocaleTimeString());
                this.showSaveIndicator("Saved");
            } else {
                throw new Error(data.error);
            }
            
        } catch (error) {
            console.error("Auto-save failed:", error);
            this.showSaveIndicator("Save failed", true);
        } finally {
            this.isSaving = false;
        }
    }
    
    showSaveIndicator(message, isError = false) {
        // Update UI to show save status
        const indicator = document.getElementById("save-status");
        if (indicator) {
            indicator.textContent = message;
            indicator.className = isError ? "error" : "success";
            
            // Hide after 2 seconds
            setTimeout(() => {
                indicator.textContent = "";
            }, 2000);
        }
    }
}

// Usage Examples:

// 1. Simple save
saveStoryBasic("temp-abc123", "My story content")
    .then(data => console.log("Saved!", data))
    .catch(err => console.error(err));

// 2. Complete save with all fields
saveStoryComplete({
    id: "story-456",
    content: "Full story text...",
    caption: "Check out my new story!",
    mediaUrl: "/static/uploads/stories/video.mp4",
    overlays: {
        stickers: [
            { type: "emoji", value: "🔥", x: 100, y: 200 }
        ]
    },
    musicTrack: "song.mp3"
});

// 3. Auto-save setup (saves every 2 seconds after user stops typing)
const autoSaver = new StoryAutoSaver("story-789");

// In your story editor, call this on every change:
document.getElementById("story-editor").addEventListener("input", (e) => {
    autoSaver.queueSave({
        content: e.target.value,
        caption: document.getElementById("caption").value
    });
});

// Force save before leaving page
window.addEventListener("beforeunload", () => {
    autoSaver.save({
        content: document.getElementById("story-editor").value
    });
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { saveStoryBasic, saveStoryComplete, StoryAutoSaver };
}
