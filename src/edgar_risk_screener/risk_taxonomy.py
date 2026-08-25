"""Fixed risk category taxonomy for paragraph-level classification.

This is the taxonomy actually in use in the deployed repo (confirmed
against real MSFT test output: "Cloud and AI strategy risk", "Export
control and sanctions risk", "Third-party and vendor dependency risk"
all appeared in real runs).

Used by paragraph_classifier.py for Option A's redesign: classifying one
paragraph at a time into exactly one of these categories, rather than
having the LLM invent/name topics and estimate mention counts over a
whole document in one pass (the design that produced run-to-run
instability -- see docs/architecture.md).
"""
from typing import Literal, get_args

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

RISK_CATEGORIES: list[str] = list(get_args(RiskCategory))
