"""Option A core: classify ONE paragraph into ONE fixed risk category.

This replaces topic_extraction.py's whole-document synthesis (which
produced different topic sets across repeated runs -- see
docs/architecture.md) with a much narrower decision per call: given one
paragraph and a fixed list of categories, pick the single best fit.

Classification is inherently more stable than open-ended synthesis. Some
residual run-to-run variance is still expected for genuinely ambiguous
paragraphs near a category boundary -- but a handful of paragraphs
flipping category moves a count by one or two, not a topic silently
appearing or vanishing across an entire document.
"""
from pydantic import BaseModel
from edgar_risk_screener.risk_taxonomy import RiskCategory

CLASSIFY_PROMPT = """Classify the following paragraph from a 10-K Risk
Factors section into exactly ONE of the fixed risk categories provided to
you. Choose the single best-fitting category, even if the paragraph
touches on more than one theme. If genuinely none of the categories fit,
use "Emerging or unanticipated risk".

Paragraph:
{paragraph}
"""


class ParagraphClassification(BaseModel):
    category: RiskCategory


def classify_paragraph(paragraph: str) -> ParagraphClassification:
    """Classify a single paragraph. LLM provider import is local to this
    function so the module stays importable without langchain installed.
    """
    from edgar_risk_screener.llm_provider import get_llm

    llm = get_llm()
    structured_llm = llm.with_structured_output(ParagraphClassification)

    prompt = CLASSIFY_PROMPT.format(paragraph=paragraph)
    return structured_llm.invoke(prompt)


def classify_all_paragraphs(paragraphs: list[str]) -> list[ParagraphClassification]:
    """Classify every paragraph in a filing section. One LLM call per
    paragraph -- more calls than the old whole-document approach, but
    each call is narrow and independently auditable. Batching/concurrency
    is a reasonable follow-up if latency becomes a problem; not addressed
    here to keep this change reviewable as one thing at a time.
    """
    return [classify_paragraph(p) for p in paragraphs]
