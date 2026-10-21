"""Agents: explainer + verifier (Daniel); persona, narrator, language QA (Posh)."""

from agents.explainer import TemplateExplainer
from agents.foundry import FoundryExplainer, make_explainer
from agents.verifier import ClaimVerifier, VerificationResult

__all__ = [
    "TemplateExplainer",
    "FoundryExplainer",
    "make_explainer",
    "ClaimVerifier",
    "VerificationResult",
]
