"""Track 2 Step 1: extract risk topics from ONE filing year's text (LLM).

Deliberately does not compare two years in one call -- narrowing the LLM's
job to single-document extraction keeps it auditable. Comparison happens
separately in topic_diff.py, deterministically.

Topics are classified into a fixed taxonomy (schemas.RiskCategory) rather
than given free-invented names, so that topic_diff.py can match topics
across years by exact category equality instead of fuzzy name matching --
free-form naming caused topic granularity/wording to drift between runs
even at temperature=0, which made the diff unstable run-to-run. The
"Emerging or unanticipated risk" category is the deliberate exception: a
risk that doesn't fit any fixed category still gets an LLM-invented name,
preserving Track 2B's original purpose of catching a risk topic the analyst
didn't think to look for -- see docs/architecture.md.
"""
from edgar_risk_screener.schemas import RiskTopicExtraction, RISK_TAXONOMY, EMERGING_CATEGORY

MAX_CONTEXT_CHARS = 100_000

_TAXONOMY_LIST = "\n".join(f"- {category}" for category in RISK_TAXONOMY)

PROMPT_TEMPLATE = f"""You are analyzing the Risk Factors section of a 10-K
filing. Classify the risks discussed into the following fixed categories:

{_TAXONOMY_LIST}
- {EMERGING_CATEGORY}

Rules:
- Use one of the fixed categories above whenever a risk reasonably fits it.
  Only use "{EMERGING_CATEGORY}" if a risk genuinely does not fit any fixed
  category.
- Output AT MOST ONE topic per fixed category: if multiple passages discuss
  the same category, combine them into a single topic entry and add their
  mention counts together.
- Under "{EMERGING_CATEGORY}", you may list multiple distinct topics, each
  with its own short, specific, invented name (e.g. "Quantum computing
  security risk"), since these don't share a predefined category.
- Do not invent a fixed-category topic that has zero supporting passages:
  only include a category if the text actually discusses it.

For each topic, provide:
- category: one of the fixed categories above, exactly as written.
- topic_name: for a fixed category, restate the category name. For
  "{EMERGING_CATEGORY}", give a short specific name for the risk.
- mention_count: roughly how many separate passages discuss it.
- summary: one sentence describing how the filing frames the risk.
- source_quote: one short (under 20 words) verbatim quote as evidence.

Text:
{{risk_factors_text}}
"""


def extract_risk_topics(risk_factors_text: str) -> RiskTopicExtraction:
    """Run the LLM extraction on one filing year's Risk Factors text.

    The LLM provider import is local to this function (not module-level),
    so this module can be imported for its prompt/constants without
    requiring langchain_openai/langchain_anthropic to be installed.
    """
    from edgar_risk_screener.llm_provider import get_llm

    llm = get_llm()
    structured_llm = llm.with_structured_output(RiskTopicExtraction)

    prompt = PROMPT_TEMPLATE.format(risk_factors_text=risk_factors_text[:MAX_CONTEXT_CHARS])
    return structured_llm.invoke(prompt)
