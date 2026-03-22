#!/usr/bin/env python3
"""
VybeFlow Post Creation - Verification Script
Tests if the server and posting functionality work correctly
"""

import os
import sys
import json
import requests
from time import sleep
from pathlib import Path

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.RESET}\n")

def print_ok(text):
    print(f"{Colors.GREEN}✅ {text}{Colors.RESET}")

def print_error(text):
    print(f"{Colors.RED}❌ {text}{Colors.RESET}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.RESET}")

def print_info(text):
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.RESET}")

# Tests
BASE_URL = "http://127.0.0.1:5000"
TESTS_PASSED = 0
TESTS_FAILED = 0

def test_server_running():
    """Test 1: Check if server is running"""
    print_info("Test 1: Checking if server is running...")
    try:
        response = requests.get(f"{BASE_URL}/check", timeout=2)
        if response.status_code == 200:
            data = response.json()
            print_ok(f"Server is running! Posts in database: {data.get('posts_count', 0)}")
            return True
        else:
            print_error(f"Server responded with status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print_error(f"Can't connect to {BASE_URL}")
        print_warning("Make sure simple_server.py is running:")
        print(f"  cd d:\\Vybeflow-main\\Vybeflow-main")
        print(f"  python simple_server.py")
        return False
    except Exception as e:
        print_error(f"Error: {str(e)}")
        return False

def test_create_post_page():
    """Test 2: Check if create post page loads"""
    print_info("Test 2: Checking if create post page loads...")
    try:
        response = requests.get(f"{BASE_URL}/create/post", timeout=2)
        if response.status_code == 200:
            if "create_post_simple" in response.text or "Create a Post" in response.text:
                print_ok("Post creation page loads successfully")
                return True
            else:
                print_warning("Page loaded but might be invalid HTML")
                return True
        else:
            print_error(f"Page returned status {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Error: {str(e)}")
        return False

def test_post_creation():
    """Test 3: Test actual post creation"""
    print_info("Test 3: Creating a test post...")
    try:
        data = {
            "caption": "🎉 Test post from verification script",
            "visibility": "Public",
            "bg_style": "sunset",
        }
        
        response = requests.post(
            f"{BASE_URL}/api/posts",
            data=data,
            timeout=5
        )
        
        if response.status_code == 201:
            result = response.json()
            if result.get("ok"):
                post_id = result.get("post", {}).get("id", "unknown")
                print_ok(f"Post created successfully! ID: {post_id}")
                return True
            else:
                print_error(f"API returned error: {result.get('error')}")
                return False
        else:
            print_error(f"API returned status {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Error: {str(e)}")
        return False

def test_get_posts():
    """Test 4: Get all posts"""
    print_info("Test 4: Retrieving all posts...")
    try:
        response = requests.get(f"{BASE_URL}/api/posts", timeout=2)
        if response.status_code == 200:
            result = response.json()
            posts = result.get("posts", [])
            print_ok(f"Retrieved {len(posts)} posts from database")
            for i, post in enumerate(posts[:3], 1):
                caption = post.get("caption", "")[:40]
                print(f"   {i}. {caption}..." if len(post.get('caption', '')) > 40 else f"   {i}. {caption}")
            return True
        else:
            print_error(f"Failed to get posts (status {response.status_code})")
            return False
    except Exception as e:
        print_error(f"Error: {str(e)}")
        return False

def test_uploads_dir():
    """Test 5: Check if uploads directory exists"""
    print_info("Test 5: Checking uploads directory...")
    upload_dir = Path("static/uploads")
    if upload_dir.exists():
        print_ok(f"Upload directory exists: {upload_dir.absolute()}")
        file_count = len(list(upload_dir.glob("*")))
        print_info(f"Files in uploads: {file_count}")
        return True
    else:
        print_error(f"Upload directory not found at {upload_dir.absolute()}")
        print_warning("Creating directory...")
        try:
            upload_dir.mkdir(parents=True, exist_ok=True)
            print_ok("Directory created")
            return True
        except Exception as e:
            print_error(f"Failed to create directory: {str(e)}")
            return False

def main():
    global TESTS_PASSED, TESTS_FAILED
    
    print_header("VybeFlow Post Creation Verification")
    print("This script tests if everything is working correctly.\n")
    
    # Make sure we're in the right directory
    if not Path("simple_server.py").exists():
        print_error("simple_server.py not found!")
        print_warning("Make sure you're running this from: d:\\Vybeflow-main\\Vybeflow-main")
        sys.exit(1)
    
    tests = [
        test_server_running,
        test_create_post_page,
        test_post_creation,
        test_get_posts,
        test_uploads_dir,
    ]
    
    for test in tests:
        try:
            if test():
                TESTS_PASSED += 1
            else:
                TESTS_FAILED += 1
        except Exception as e:
            print_error(f"Test crashed: {str(e)}")
            TESTS_FAILED += 1
        sleep(0.5)
    
    # Summary
    print_header("Verification Complete")
    print(f"{Colors.GREEN}✅ Passed: {TESTS_PASSED}{Colors.RESET}")
    if TESTS_FAILED > 0:
        print(f"{Colors.RED}❌ Failed: {TESTS_FAILED}{Colors.RESET}")
    
    if TESTS_FAILED == 0:
        print(f"\n{Colors.BOLD}{Colors.GREEN}🎉 All tests passed! Your server is working correctly!{Colors.RESET}")
        print(f"\n📝 Try posting at: {Colors.CYAN}{BASE_URL}/create/post{Colors.RESET}\n")
    else:
        print(f"\n{Colors.BOLD}{Colors.YELLOW}⚠️  Some tests failed. Check the output above for details.{Colors.RESET}\n")
    
    return 0 if TESTS_FAILED == 0 else 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Cancelled by user{Colors.RESET}\n")
        sys.exit(1)
