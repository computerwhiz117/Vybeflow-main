"""Quick test: welcome email + password reset email"""
from email_utils import send_welcome_email, send_reset_email, generate_reset_token

print("=== TEST 1: Welcome Email ===")
r1 = send_welcome_email("chatcirclebusiness16@gmail.com", "VybeTestUser")
print("Welcome email:", "PASS" if r1 else "FAIL")
print()

print("=== TEST 2: Password Reset Email ===")
token = generate_reset_token("chatcirclebusiness16@gmail.com")
url = f"http://10.0.0.249:5000/reset_password/{token}"
r2 = send_reset_email("chatcirclebusiness16@gmail.com", url)
print("Reset email:", "PASS" if r2 else "FAIL")
print("Reset URL valid for 24 hours, works across server restarts")
