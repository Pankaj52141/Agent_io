"""
RBAC Enforcer — Enforces role-based access control at the data layer.
Filters chunks BEFORE they reach the LLM, and validates responses for data leakage.
"""
import re
from typing import List, Tuple, Set
from backend.config import ROLE_RESTRICTIONS, DATA_CATEGORIES
from backend.rbac.models import DataChunk


def filter_chunks_for_role(chunks: list, role: str) -> list:
    """
    Filter chunks based on role restrictions.
    Works with both DataChunk objects and plain dicts.
    This is the PRIMARY RBAC enforcement — data is filtered BEFORE the LLM sees it.
    """
    restricted = get_restricted_categories(role)
    if not restricted:
        return chunks  # CEO gets everything

    filtered = []
    for chunk in chunks:
        if isinstance(chunk, dict):
            category = chunk.get("data_category", "general")
        else:
            category = chunk.data_category
        if category not in restricted:
            filtered.append(chunk)

    return filtered


def get_allowed_categories(role: str) -> Set[str]:
    """Returns the set of allowed data categories for a role."""
    restricted = get_restricted_categories(role)
    return {category for category in DATA_CATEGORIES if category not in restricted}


def get_restricted_categories(role: str) -> Set[str]:
    """Returns the restricted categories for a role."""
    return set(ROLE_RESTRICTIONS.get(role, set()))


def is_category_allowed(category: str, role: str) -> bool:
    """Check if a single category is allowed for a role."""
    return category not in get_restricted_categories(role)


# ─── Leakage Detection Keywords ─────────────────────────
# These are checked against LLM output as a second line of defense.
# The primary defense is pre-retrieval filtering (above).
_LEAKAGE_KEYWORDS = {
    "cto": [
        # Headcount
        r'\b\d[\d,]*\s*employees\b',
        r'\bheadcount\b',
        r'\bworkforce\s+size\b',
        r'\bnumber\s+of\s+employees\b',
        r'\bfull[- ]time\s+employees\b',
        # Compensation
        r'\bbase\s+salary\b',
        r'\bstock\s+(?:options?|awards?|compensation)\b',
        r'\bRSU(?:s)?\b',
        r'\bexecutive\s+compensation\b',
        r'\bcompensation\s+(?:package|plan|committee)\b',
        r'\bannual\s+(?:bonus|incentive)\b',
        r'\bseverance\b',
        r'\bpay\s+ratio\b',
    ],
    "cfo": [
        # Strategy
        r'\bstrategic\s+(?:plan|initiative|direction|priority)\b',
        r'\bgrowth\s+strategy\b',
        r'\bcompetitive\s+strategy\b',
        # R&D specific projects
        r'\bR&D\s+project\b',
        r'\bresearch\s+(?:initiative|program|project)\b',
        r'\bproduct\s+(?:pipeline|roadmap)\b',
        r'\bupcoming\s+product\b',
        r'\bfuture\s+product\b',
        # Legal
        r'\blitigation\b',
        r'\blawsuit\b',
        r'\blegal\s+(?:proceedings?|action|settlement|dispute)\b',
        r'\bcourt\s+(?:ruling|order|case)\b',
        r'\bpatent\s+(?:infringement|dispute)\b',
    ],
}


def validate_response_for_leakage(
    response_text: str, role: str
) -> Tuple[bool, str]:
    """
    Secondary defense: Check if the LLM's response contains restricted information.

    Returns (is_safe, text). If not safe, returns a version with restricted
    content flagged, NOT a full redaction — so the orchestrator can re-generate.
    """
    if role == "ceo":
        return True, response_text  # CEO has full access

    keywords = _LEAKAGE_KEYWORDS.get(role, [])
    if not keywords:
        return True, response_text

    flagged = []
    for pattern in keywords:
        matches = re.findall(pattern, response_text, re.IGNORECASE)
        if matches:
            flagged.extend(matches)

    if flagged:
        # Don't fully redact — flag it for the orchestrator to re-generate
        return False, response_text

    return True, response_text
