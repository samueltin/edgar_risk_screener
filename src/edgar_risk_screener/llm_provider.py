"""Provider-agnostic LLM factory. Same pattern as edgar_10k_research_agent:
depending on this abstraction rather than importing a provider class
directly means swapping providers is a config change, not a rewrite.

"ollama" runs a local model on your own hardware -- no per-call API cost,
which is the whole point of adding it here (Azure OpenAI cost during
active development was the reason). Real trade-offs though, not a free
swap: see the ollama branch below, and edgar_10k_research_agent's
docs/architecture.md for the fuller real-hardware findings this default
is based on (a real llama3.1:8b run on an 8GB GPU reported a 4096-token
context window with no demonstrated VRAM headroom).

NOT YET TESTED against this specific pipeline: diff_subtopic_content()
(subtopic_diff.py) is the only caller of get_llm() here, and it's scoped
per individual risk sub-topic, not the whole document -- generally safer
than edgar_10k_research_agent's whole-MD&A-text calls. But some real
sub-topics (e.g. a company's longest risk category) can still be large.
No context-overflow problem has been confirmed here the way it was for
edgar_10k_research_agent -- worth watching for on a real run, not
something pre-emptively "fixed" without real evidence it's needed.

load_dotenv() ensures .env is actually read -- without it, os.environ
only sees variables already present in the shell/process environment,
so a filled-in .env file would silently have no effect.
"""
import os

from dotenv import load_dotenv


def get_llm(provider: str | None = None, temperature: float = 0):
    load_dotenv()
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
    elif provider == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(
            base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
            model=os.environ.get("OLLAMA_MODEL", "llama3.1:8b"),
            temperature=temperature,
            num_ctx=int(os.environ.get("OLLAMA_NUM_CTX", "4096")),
        )
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")
