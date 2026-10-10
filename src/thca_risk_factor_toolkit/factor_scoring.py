"""Numerical parsing and composite evidence-score primitives.

These functions reproduce, in a self-contained way, the scoring logic from the
original pipeline's ``backend/db_export`` modules.  The composite evidence score
is defined in the manuscript as::

    Score = W_num * Z[log(n_paper)]
          + W_size * Z[log(n_sample)]
          + W_statsig * Z(S_statsig)
          + W_evigrade * Z(E_evigrade)

with structural weights ``W_num=2``, ``W_size=1``, ``W_statsig=1`` and
``W_evigrade=2``.  All four components are Z-score standardized across the full
factor table before the weighted sum.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Iterable, Tuple

# Year bins used by the manuscript; both endpoints inclusive.
YEAR_BINS = ["before_2000", "2001_2010", "2011_2015", "2016_2020", "2021_2025"]
YEAR_BIN_UPPER = [2000, 2010, 2015, 2020, 2025]

W_NUM = 2.0
W_SIZE = 1.0
W_STATSIG = 1.0
W_EVIGRADE = 2.0

_RE_FLOAT = re.compile(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")


def parse_float_maybe(text: object) -> float | None:
    """Extract the first numeric token from arbitrary text, or ``None``."""
    if text is None:
        return None
    s = str(text).strip()
    if not s:
        return None
    match = _RE_FLOAT.search(s)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def p_value_to_significance_grade(p_value_num: float | None) -> float:
    """Map a p-value to a significance weight (1.0 / 0.5 / 0.1 / 0.0)."""
    if p_value_num is None or (isinstance(p_value_num, float) and math.isnan(p_value_num)):
        return 0.0
    if p_value_num < 0.01:
        return 1.0
    if p_value_num < 0.05:
        return 0.5
    return 0.1


def evidence_grade_to_numeric(evidence_grade: object) -> float:
    """Map a GRADE-informed level to High=4 / Moderate=3 / Low=2 / Very low=1."""
    s = str(evidence_grade).strip().casefold()
    if not s or s == "unspecified":
        return 0.0
    s = s.replace("_", " ").replace("-", " ")
    s = re.sub(r"\s+", " ", s).strip()
    mapping = {
        "high": 4.0,
        "moderate": 3.0,
        "low": 2.0,
        "very low": 1.0,
        "verylow": 1.0,
    }
    return float(mapping.get(s, 0.0))


def parse_sample_size_to_int(sample_size: object) -> int:
    """Extract the largest integer from a sample-size string (legacy heuristic)."""
    if sample_size is None:
        return 0
    s = str(sample_size).strip()
    if not s:
        return 0
    numbers = re.findall(r"\d+", s.replace("–", "-"))
    if not numbers:
        return 0
    try:
        return int(max(int(x) for x in numbers))
    except ValueError:
        return 0


def safe_log(x: float) -> float:
    if x <= 0:
        return 0.0
    return float(math.log(x))


def _zscore(value: float, mean: float, std: float) -> float:
    if std <= 0 or (isinstance(std, float) and math.isnan(std)):
        return 0.0
    if isinstance(value, float) and math.isnan(value):
        return 0.0
    return float((value - mean) / std)


def compute_global_score_stats(factor_table) -> Tuple[float, ...]:
    """Return (mean, std) for each of the four log/numeric components.

    Uses ``ddof=0`` for the population standard deviation, matching the
    original scoring routine.
    """
    import pandas as pd

    frame = factor_table.copy()
    frame["num_publish_paper"] = frame["num_publish_paper"].fillna(0).astype(float)
    frame["total_sample_size"] = frame["total_sample_size"].fillna(0).astype(float)
    frame["avg_statsig_grade"] = frame["avg_statsig_grade"].fillna(0).astype(float)
    frame["avg_evigrade"] = frame["avg_evigrade"].fillna(0).astype(float)

    log_num = frame["num_publish_paper"].clip(lower=1.0).map(lambda x: safe_log(float(x)))
    log_size = frame["total_sample_size"].clip(lower=1.0).map(lambda x: safe_log(float(x)))

    def _mean_std(series) -> Tuple[float, float]:
        clean = series.replace([math.inf, -math.inf], math.nan).dropna()
        if len(clean) == 0:
            return 0.0, 0.0
        return float(clean.mean()), float(clean.std(ddof=0))

    m_log_num, sd_log_num = _mean_std(log_num)
    m_log_size, sd_log_size = _mean_std(log_size)
    m_statsig, sd_statsig = _mean_std(frame["avg_statsig_grade"])
    m_ev, sd_ev = _mean_std(frame["avg_evigrade"])
    return m_log_num, sd_log_num, m_log_size, sd_log_size, m_statsig, sd_statsig, m_ev, sd_ev


# --- Normalization helpers reused by synonym and geographic grouping ---------

def to_key(value: object) -> str:
    """Normalize a categorical value for grouping; empty/unspecified -> MISSING."""
    s = str(value).strip()
    if not s or s.strip().lower() == "unspecified":
        return "MISSING"
    return s


def normalize_geo(value: object) -> str:
    """Normalize a country/continent string for geographic analysis."""
    s = str(value).strip()
    if not s:
        return "MISSING"
    lowered = s.lower()
    if lowered == "unspecified":
        return "MISSING"
    if "|" in s:
        return "international"
    if lowered in {"usa", "u.s.a.", "u.s.", "united states", "united states of america"}:
        return "United States"
    return s


def canonicalize_group_terms(terms: Iterable[str]) -> Tuple[str, ...]:
    """Canonicalize a synonym group: strip, dedup, sort by (length, term)."""
    uniq = {str(term).strip(): str(term).strip() for term in terms if str(term).strip()}
    return tuple(sorted(uniq.values(), key=lambda x: (len(x), x)))


def factor_id_from_key(factor_key: list) -> str:
    """SHA-256 of the canonical factor key, used as the stable factor id."""
    canonical = list(canonicalize_group_terms(factor_key))
    return hashlib.sha256(json.dumps(canonical, ensure_ascii=False).encode("utf-8")).hexdigest()


def year_number(value: object) -> float:
    try:
        number = float(str(value).strip())
        return number if number.is_integer() and 1 <= number <= 9999 else float("nan")
    except (ValueError, OverflowError):
        return float("nan")


def year_to_bin(value: object) -> str:
    year = year_number(value)
    if math.isnan(year):
        return "MISSING"
    for upper, name in zip(YEAR_BIN_UPPER, YEAR_BINS):
        if year <= upper:
            return name
    return "other_year"
