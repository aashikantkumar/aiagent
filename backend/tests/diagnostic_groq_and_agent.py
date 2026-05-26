import asyncio
import sys
import time
from langchain_core.messages import HumanMessage
from core.config import get_settings
from agent.llm import LLMFactory

async def test_roles():
    print("=" * 60)
    print("TESTING INDIVIDUAL AGENT ROLES AND MODELS ON GROQ")
    print("=" * 60)
    
    settings = get_settings()
    keys = settings.get_groq_keys()
    
    if not keys:
        print("[ERROR] No Groq API keys found.")
        sys.exit(1)
        
    factory = LLMFactory()
    
    # The roles configured in agent/llm.py:
    # - planner: groq/llama-3.3-70b-versatile
    # - coder: groq/llama-4-scout
    # - validator: groq/llama-3.1-8b-instant
    roles_to_test = [
        {"role": "planner", "model": "groq/llama-3.3-70b-versatile"},
        {"role": "coder", "model": "groq/meta-llama/llama-4-scout-17b-16e-instruct"},
        {"role": "validator", "model": "groq/llama-3.1-8b-instant"},
    ]
    
    all_ok = True
    
    for r in roles_to_test:
        role = r["role"]
        model = r["model"]
        print(f"\nTesting Role: {role.upper()} (Model: {model})")
        
        try:
            # Instantiate LLM for this role
            llm = factory.create(role=role, temperature=0.1)
            
            start_time = time.time()
            # Invoke the LLM with a simple request
            response = await llm.ainvoke([HumanMessage(content="Respond with 'OK' and nothing else.")])
            latency = time.time() - start_time
            content = response.content.strip()
            
            print(f"  [SUCCESS] Response: {repr(content)} (Latency: {latency:.2f}s)")
        except Exception as e:
            print(f"  [FAILED] Failed to invoke role {role}: {e}")
            all_ok = False
            
    print("\n" + "=" * 60)
    if all_ok:
        print("ALL AGENT ROLES AND MODELS ARE READY & FUNCTIONAL!")
    else:
        print("SOME AGENT ROLES FAILED. Please see the errors above.")
    print("=" * 60)
    return all_ok

if __name__ == "__main__":
    success = asyncio.run(test_roles())
    sys.exit(0 if success else 1)
