"""Quick test to verify Anthropic API and Citations work."""
import os
from dotenv import load_dotenv
import anthropic

load_dotenv()

api_key = os.getenv("ANTHROPIC_API_KEY")
print(f"API Key: {api_key[:20]}...{api_key[-10:]}")

client = anthropic.Anthropic(api_key=api_key)

# Test available models
models_to_try = [
    "claude-sonnet-4-5-20250929",
    "claude-3-haiku-20240307",
    "claude-3-opus-20240229",
    "claude-sonnet-4-5-20250514",
]

for model in models_to_try:
    print(f"\n=== Testing model: {model} ===")
    try:
        response = client.messages.create(
            model=model,
            max_tokens=50,
            messages=[{"role": "user", "content": "Say hi"}]
        )
        print(f"SUCCESS! Model {model} works.")
        print(f"Response: {response.content[0].text}")
        break
    except Exception as e:
        print(f"Failed: {type(e).__name__}")

# Test 1: Simple message (no citations)
print("\n=== Test 1: Simple message ===")
try:
    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=100,
        messages=[{"role": "user", "content": "Say hello in 10 words or less."}]
    )
    print(f"Success: {response.content[0].text}")
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")

# Test 2: With document citations
print("\n=== Test 2: Document with citations ===")
try:
    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=200,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "document",
                    "source": {
                        "type": "text",
                        "media_type": "text/plain",
                        "data": "Article 125 of S.L. 65.11 states that the fine for speeding is 500 euro."
                    },
                    "title": "S.L. 65.11, Article 125",
                    "citations": {"enabled": True}
                },
                {
                    "type": "text",
                    "text": "What is the fine for speeding?"
                }
            ]
        }]
    )
    print(f"Success!")
    for block in response.content:
        print(f"  Block type: {block.type}")
        if hasattr(block, 'text'):
            print(f"  Text: {block.text[:100]}...")
        if hasattr(block, 'citations') and block.citations:
            print(f"  Citations: {len(block.citations)}")
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")

print("\n=== Done ===")
