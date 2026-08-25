"""Pydantic schemas for the risk screener."""
from typing import List, Literal, get_args
from pydantic import BaseModel, Field

# Fixed taxonomy for topic classification. Comparing topics across years by
# category equality (deterministic) instead of LLM-invented free-text names
# fixes the run-to-run instability free-form naming caused in topic_diff.py's
# matching -- see docs/architecture.md. "Emerging or unanticipated risk" is
# the deliberate escape hatch: a risk that doesn't fit any fixed category
# still gets an LLM-invented name and is matched by name similarity, same as
# before, so genuinely novel risks (the whole point of Track 2B) can still
# surface -- just with less run-to-run stability than the fixed categories.
RiskCategory = Literal[
    # Strategic & competitive
    "Competition and market risk",
    "Innovation and product development risk",
    "Business model disruption risk",
    "Strategic partnership and alliance risk",
    "Acquisitions and integration risk",
    "Divestiture and restructuring risk",
    "Customer concentration risk",
    "Customer acquisition and retention risk",
    "Pricing and margin pressure risk",

    # Financial
    "Liquidity and capital resources risk",
    "Indebtedness and leverage risk",
    "Credit and counterparty risk",
    "Interest rate risk",
    "Foreign currency and exchange rate risk",
    "Commodity price risk",
    "Goodwill and asset impairment risk",
    "Pension and employee benefit obligation risk",
    "Access to capital markets and financing risk",
    "Credit rating risk",
    "Insurance coverage adequacy risk",

    # Operational
    "Infrastructure and supply chain risk",
    "Manufacturing and production risk",
    "Service reliability risk",
    "Business continuity and disaster recovery risk",
    "Third-party and vendor dependency risk",
    "Seasonality and demand cyclicality risk",
    "Real estate and facilities risk",
    "Inventory management risk",

    # Technology
    "Cloud and AI strategy risk",
    "AI-specific risk",
    "Cybersecurity risk",
    "Data privacy risk",
    "Platform abuse and content risk",
    "Technology obsolescence risk",

    # Legal & regulatory
    "Regulatory and compliance risk",
    "Litigation risk",
    "Government contracts risk",
    "Tax risk",
    "Intellectual property risk",
    "Antitrust and competition-law risk",
    "Anti-corruption and trade-compliance risk",
    "Export control and sanctions risk",
    "Environmental regulation risk",
    "Product liability and safety risk",
    "Healthcare regulatory and clinical trial risk",

    # Human capital
    "Talent and labor risk",
    "Labor union and collective bargaining risk",
    "Executive succession and key-person risk",
    "Workplace safety risk",

    # Market & macro
    "Macroeconomic and market conditions risk",
    "Geopolitical and catastrophic events risk",
    "Public health and pandemic risk",
    "Climate change physical risk",
    "Climate transition and decarbonization risk",

    # Governance & ownership
    "Corporate governance risk",
    "Ownership concentration and controlling shareholder risk",
    "Internal controls and financial reporting risk",
    "Stock price volatility and dilution risk",
    "Activist investor and shareholder activism risk",

    # Reputation
    "Reputation and brand risk",

    # Catch-all
    "Emerging or unanticipated risk",
]

EMERGING_CATEGORY: str = "Emerging or unanticipated risk"
RISK_TAXONOMY: tuple[str, ...] = tuple(c for c in get_args(RiskCategory) if c != EMERGING_CATEGORY)


class RiskTopic(BaseModel):
    category: RiskCategory = Field(
        description=(
            "One of the fixed risk categories. Use 'Emerging or unanticipated risk' "
            "only if the risk genuinely does not fit any other category."
        )
    )
    topic_name: str = Field(
        description=(
            "For a fixed category, restate the category name. For 'Emerging or "
            "unanticipated risk', a short specific invented name for the risk, "
            "e.g. 'Quantum computing security risk'."
        )
    )
    mention_count: int = Field(description="Approximate number of distinct passages discussing this topic in the text")
    summary: str = Field(description="One sentence describing how the filing frames this risk")
    source_quote: str = Field(description="A short (under 20 words) verbatim quote from the text supporting this topic")


class RiskTopicExtraction(BaseModel):
    topics: List[RiskTopic] = Field(description="All distinct risk topics found in the text")


class FlaggedTopic(BaseModel):
    topic_name: str
    category: str
    status: str              # "NEW" or "EXPANDED"
    current_mentions: int
    prior_mentions: int
    source_quote: str
    quote_verified: bool
    prior_source_quote: str | None = None   # None for NEW topics -- no prior-year match to quote
    prior_quote_verified: bool = False
    low_confidence: bool = False   # thin evidence (a single incidental mention) -- see topic_diff.py


class KPIChange(BaseModel):
    metric_name: str          # "Revenue", "GrossMarginPct", "NetIncome"
    current_value: float
    prior_value: float
    pct_change: float
    unusual: bool
