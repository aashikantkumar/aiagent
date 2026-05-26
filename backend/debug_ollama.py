import asyncio
from litellm import completion

async def test_ollama():
    try:
        print("Testing Ollama connection...")
        response = completion(
            model="ollama/qwen2.5-coder:7b",
            messages=[{"role": "user", "content": "Say hello"}],
            api_base="http://localhost:11434"
        )
        print("SUCCESS:", response.choices[0].message.content)
    except Exception as e:
        print("ERROR:", str(e))
        import traceback
        traceback.print_exc()

asyncio.run(test_ollama())
