"""
tests/test_exceptions.py

Tests for the public X12 exception hierarchy.
"""

from __future__ import annotations

import pytest

from x12.exceptions import (
    X12EnvelopeError,
    X12Error,
    X12SegmentError,
    X12SeparatorError,
    X12TokenizerError,
)


@pytest.mark.parametrize(
    ("exception_class", "expected_parent"),
    [
        (X12TokenizerError, X12Error),
        (X12EnvelopeError, X12Error),
        (X12SeparatorError, X12EnvelopeError),
        (X12SegmentError, X12TokenizerError),
    ],
)
def test_exception_inheritance(
    exception_class: type[X12Error],
    expected_parent: type[X12Error],
) -> None:
    """Specialized exceptions should inherit from their documented parent."""
    assert issubclass(exception_class, expected_parent)


@pytest.mark.parametrize(
    "exception_class",
    [
        X12Error,
        X12TokenizerError,
        X12EnvelopeError,
        X12SeparatorError,
        X12SegmentError,
    ],
)
def test_exception_preserves_message(
    exception_class: type[X12Error],
) -> None:
    """Every X12 exception should preserve its supplied message."""
    exception = exception_class("Malformed X12 document.")

    assert str(exception) == "Malformed X12 document."


@pytest.mark.parametrize(
    "exception",
    [
        X12TokenizerError("Tokenizer failure."),
        X12EnvelopeError("Envelope failure."),
        X12SeparatorError("Separator failure."),
        X12SegmentError("Segment failure."),
    ],
)
def test_specialized_exceptions_are_caught_as_x12_error(
    exception: X12Error,
) -> None:
    """Every specialized exception should be catchable as X12Error."""
    with pytest.raises(X12Error) as exc_info:
        raise exception

    assert exc_info.value is exception
