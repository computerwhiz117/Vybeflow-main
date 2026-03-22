"""
Quick Story & Reel Demo
Create, test playback, and remove story and reel
"""
from test_story_reel_suite import StoryReelTester

def quick_demo():
    print("\n🎬 QUICK STORY & REEL DEMO")
    print("="*60)
    
    tester = StoryReelTester()
    
    # Create user
    print("\n1️⃣  Creating test user...")
    tester.create_test_user()
    
    # Create story
    print("\n2️⃣  Creating story with animated stickers & music...")
    story_id = tester.create_test_story()
    
    if story_id:
        print("\n3️⃣  Testing story playback...")
        tester.test_story_playback(story_id)
    
    # Create reel
    print("\n4️⃣  Creating rich Instagram-style reel...")
    reel_id = tester.create_test_reel()
    
    if reel_id:
        print("\n5️⃣  Testing reel playback...")
        tester.test_reel_playback(reel_id)
    
    # Cleanup
    print("\n6️⃣  Removing test story...")
    if story_id:
        tester.delete_test_story(story_id)
    
    print("\n7️⃣  Removing test reel...")
    if reel_id:
        tester.delete_test_reel(reel_id)
    
    print("\n" + "="*60)
    print("✅ DEMO COMPLETE!")
    print("="*60)
    print("\nKey Features Demonstrated:")
    print("  ✨ Animated stickers (Lottie animations)")
    print("  😀 Massive emoji library (100+ emojis)")
    print("  🔤 Rich font library (9+ styles)")
    print("  🎵 Music integration")
    print("  📹 Video playback (stories & reels)")
    print("  🎨 Instagram-quality effects")
    print("  🗑️  Create and delete functionality")

if __name__ == '__main__':
    quick_demo()
