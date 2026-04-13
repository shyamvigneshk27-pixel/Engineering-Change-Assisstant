import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
key1 = "AIzaSyDmrXKptbJSOoRyLLrzzlq-dN2Drp-Qidc"
key2 = "AIzaSyBS5l7U4Mv01PildSF0X4xwse2QRkXTYaU"

def test_key(k, name):
    try:
        genai.configure(api_key=k)
        model = genai.GenerativeModel('gemini-2.5-flash')
        model.generate_content('Hi')
        print(f"{name} WORKING!")
    except Exception as e:
        print(f"{name} FAILED: {str(e)[:100]}")

test_key(key1, "KEY_FROM_DISK")
test_key(key2, "KEY_FROM_USER")
