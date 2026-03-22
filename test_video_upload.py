"""
Test video upload via API
"""
import requests

def test_video_upload():
    """Upload a test video to the API"""
    url = "http://127.0.0.1:5000/api/posts/create"
    
    # Prepare the file and form data
    files = {
        'media': ('test_video.mp4', open('static/uploads/test_video.mp4', 'rb'), 'video/mp4')
    }
    data = {
        'caption': 'Uploaded via API test! 🎬 #APITest #VideoUpload'
    }
    
    print("📤 Uploading video via API...")
    response = requests.post(url, files=files, data=data)
    
    if response.status_code == 201 or response.status_code == 200:
        result = response.json()
        print(f"✓ Video uploaded successfully!")
        print(f"📊 Post ID: {result.get('post_id')}")
        print(f"📝 Caption: {data['caption']}")
        return result.get('post_id')
    else:
        print(f"❌ Upload failed with status {response.status_code}")
        print(f"Response: {response.text}")
        return None

if __name__ == '__main__':
    post_id = test_video_upload()
    
    if post_id:
        print(f"\n✅ Test complete! Created post ID: {post_id}")
        print(f"To delete this test post, run:")
        print(f"  curl -X POST http://127.0.0.1:5000/api/posts/delete -H 'Content-Type: application/json' -d '{{\"id\":{post_id}}}'")
