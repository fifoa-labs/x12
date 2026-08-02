"""
src/x12/core/exceptions.py

Exception hierarchy for X12 parsing, tokenization, and envelope validation.
"""

from __future__ import annotations


class X12Error(Exception):
    """Base exception for all errors raised by the :mod:`x12` package."""


class X12TokenizerError(X12Error):
    """Raised when raw X12 data cannot be tokenized safely."""


class X12EnvelopeError(X12Error):
    """Raised when an X12 interchange envelope is missing or malformed."""


class X12SeparatorError(X12EnvelopeError):
    """Raised when separators cannot be derived from the ISA segment."""


class X12SegmentError(X12TokenizerError):
    """Raised when an individual X12 segment cannot be parsed safely."""


__all__ = [
    "X12EnvelopeError",
    "X12Error",
    "X12SegmentError",
    "X12SeparatorError",
    "X12TokenizerError",
]
