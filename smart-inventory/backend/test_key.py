import os
from dotenv import load_dotenv
load_dotenv()
from anthropic import Anthropic

client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
try:
    r = client.messages.create(
        model="claude-sonnet-4-6", max_tokens=50,
        messages=[{"role": "user", "content": "Say hello in one word."}])
    print("SUCCESS:", r.content[0].text)
except Exception as e:
    print("ERROR:", type(e).__name__, "-", e)