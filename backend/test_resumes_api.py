import httpx
import json
import os

API_URL = "http://localhost:8000/api/resumes/screen"
PDF_PATH = r"C:\Users\admin\Downloads\oatsada_chatthong_update.pdf"

def test_screen_resume():
    print(f"Testing API endpoint: {API_URL}")
    print(f"Using PDF file: {PDF_PATH}")
    
    if not os.path.exists(PDF_PATH):
        print("ERROR: PDF file not found!")
        return

    with open(PDF_PATH, "rb") as f:
        files = {"file": ("test_resume.pdf", f, "application/pdf")}
        data = {"job_id": 1}
        
        print("Sending POST request...")
        with httpx.Client(timeout=120.0) as client:
            response = client.post(API_URL, files=files, data=data)
        
        print(f"Status Code: {response.status_code}")
        
        try:
            result = response.json()
            print("\nResponse JSON:")
            print(json.dumps(result, indent=2))
        except Exception as e:
            print(f"Failed to parse JSON response: {e}")
            print(f"Raw text: {response.text}")

if __name__ == "__main__":
    test_screen_resume()
