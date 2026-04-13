import os
import time
from dotenv import load_dotenv

load_dotenv(override=True)
print(f"Configured Model: {os.getenv('GEMINI_MODEL')}")

try:
    from engine.key_manager import key_pool
    print(f"KeyManager loaded. Total keys: {key_pool.stats()['total_keys']}")
    k1 = key_pool.get_key()
    k2 = key_pool.get_key(force_rotate=True)
    print(f"Key 1: {k1[:8]}...")
    print(f"Key 2: {k2[:8]}...")
    
    from agents.agent1_interpreter import Agent1Interpreter
    agent = Agent1Interpreter()
    print("Agent1Interpreter initialized successfully.")
except Exception as e:
    print(f"Error: {e}")
