"""Provider-agnostic LLM factory. Same pattern as edgar_10k_research_agent:
depending on this abstraction rather than importing a provider class
directly means swapping providers is a config change, not a rewrite.
"""
import os


def get_llm(provider: str | None = None, temperature: float = 0):
    provider = provider or os.environ.get("LLM_PROVIDER", "azure_openai")

    if provider == "azure_openai":
        from langchain_openai import AzureChatOpenAI
        return AzureChatOpenAI(
            azure_deployment=os.environ["AZURE_OPENAI_DEPLOYMENT"],
            api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-08-01-preview"),
            temperature=temperature,
        )
    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model="claude-sonnet-4-5", temperature=temperature)
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")
