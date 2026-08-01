"""
src/x12/__init__.py

Public API for generic ANSI X12 structural parsing.
"""

from __future__ import annotations

from .envelopes import (
    X12FunctionalGroup,
    X12Interchange,
    X12TransactionSet,
)
from .exceptions import (
    X12EnvelopeError,
    X12Error,
    X12SegmentError,
    X12SeparatorError,
    X12TokenizerError,
)
from .inspection import (
    X12FunctionalGroupInspection,
    X12InspectionResult,
    X12SegmentFrequency,
    X12TransactionInspection,
)
from .inspector import inspect_x12_interchange
from .parser import parse_x12_interchange
from .segments import X12Document, X12Segment
from .separators import X12Separators, derive_x12_separators
from .tokenizer import tokenize_x12

__all__ = [
    "X12Document",
    "X12EnvelopeError",
    "X12Error",
    "X12FunctionalGroup",
    "X12FunctionalGroupInspection",
    "X12InspectionResult",
    "X12Interchange",
    "X12Segment",
    "X12SegmentError",
    "X12SegmentFrequency",
    "X12SeparatorError",
    "X12Separators",
    "X12TokenizerError",
    "X12TransactionInspection",
    "X12TransactionSet",
    "derive_x12_separators",
    "inspect_x12_interchange",
    "parse_x12_interchange",
    "tokenize_x12",
]
