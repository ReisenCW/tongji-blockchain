from openai import OpenAI
import os
from settings import DASHSCOPE_API_KEY, DASHSCOPE_BASE_URL

try:
    print(f"API Key: {DASHSCOPE_API_KEY}")
    print(f"Base URL: {DASHSCOPE_BASE_URL}")
    client = OpenAI(
        api_key=DASHSCOPE_API_KEY,
        base_url=DASHSCOPE_BASE_URL,
    )
    print("Client initialized successfully")
except Exception as e:
    print(f"Error initializing client: {e}")
