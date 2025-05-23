import os
from crewai import LLM

# Test different configurations
print("Testing Azure LLM configurations...")

# Check environment variables
print("\nEnvironment variables:")
print(f"AZURE_API_KEY: {os.getenv('AZURE_API_KEY')[:10]}..." if os.getenv('AZURE_API_KEY') else "AZURE_API_KEY: Not set")
print(f"AZURE_API_BASE: {os.getenv('AZURE_API_BASE')}")
print(f"AZURE_API_VERSION: {os.getenv('AZURE_API_VERSION')}")
print(f"AZURE_OPENAI_API_KEY: {os.getenv('AZURE_OPENAI_API_KEY')[:10]}..." if os.getenv('AZURE_OPENAI_API_KEY') else "AZURE_OPENAI_API_KEY: Not set")

# Try creating LLM with proper Azure format
try:
    # Format for Azure: azure/<deployment_name>
    llm = LLM(
        model="azure/gpt-4o",
        api_key=os.getenv("AZURE_API_KEY") or os.getenv("AZURE_OPENAI_API_KEY"),
        base_url=os.getenv("AZURE_API_BASE") or f"https://{os.getenv('AZURE_OPENAI_API_INSTANCE_NAME')}.openai.azure.com/",
        api_version=os.getenv("AZURE_API_VERSION") or os.getenv("AZURE_OPENAI_API_VERSION")
    )
    
    print("\n✅ LLM created successfully!")
    
    # Try a simple call
    response = llm.call([
        {"role": "user", "content": "Say 'test successful' if you can read this."}
    ])
    print(f"Response: {response}")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    print(f"Error type: {type(e).__name__}") 