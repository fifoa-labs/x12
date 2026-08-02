"""
src/x12/__init__.py

Stable public API for generic ANSI X12 processing.

The top-level package exposes the primary interfaces for tokenizing, parsing,
inspecting, and working with transaction-neutral X12 structures. Implementation
details live in :mod:`x12.core`, while transaction-specific support belongs in
:mod:`x12.transactions`.
"""

from __future__ import annotations

from .core.envelopes import (
    X12FunctionalGroup,
    X12Interchange,
    X12TransactionSet,
)
from .core.exceptions import (
    X12EnvelopeError,
    X12Error,
    X12SegmentError,
    X12SeparatorError,
    X12TokenizerError,
)
from .core.inspection import (
    X12FunctionalGroupInspection,
    X12InspectionResult,
    X12SegmentFrequency,
    X12TransactionInspection,
)
from .core.inspector import inspect_x12_interchange
from .core.parser import parse_x12_interchange
from .core.segments import X12Document, X12Segment
from .core.separators import X12Separators, derive_x12_separators
from .core.tokenizer import tokenize_x12

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
