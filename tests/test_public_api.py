"""
tests/test_public_api.py

Tests for the public :mod:`x12` package API.
"""

from __future__ import annotations

import inspect
from typing import get_type_hints

import x12
from x12.core.envelopes import (
    X12FunctionalGroup,
    X12Interchange,
    X12TransactionSet,
)
from x12.core.exceptions import (
    X12EnvelopeError,
    X12Error,
    X12SegmentError,
    X12SeparatorError,
    X12TokenizerError,
)
from x12.core.inspection import (
    X12FunctionalGroupInspection,
    X12InspectionResult,
    X12SegmentFrequency,
    X12TransactionInspection,
)
from x12.core.inspector import inspect_x12_interchange
from x12.core.parser import parse_x12_interchange
from x12.core.segments import X12Document, X12Segment
from x12.core.separators import X12Separators, derive_x12_separators
from x12.core.tokenizer import tokenize_x12

EXPECTED_PUBLIC_API = {
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
}


def test_public_api_exports_expected_names() -> None:
    """The package should expose exactly its documented public API."""
    assert set(x12.__all__) == EXPECTED_PUBLIC_API


def test_public_api_does_not_contain_duplicate_names() -> None:
    """The public API declaration should not contain duplicate names."""
    assert len(x12.__all__) == len(set(x12.__all__))


def test_public_api_is_sorted() -> None:
    """The public API declaration should remain alphabetically sorted."""
    assert x12.__all__ == sorted(x12.__all__)


def test_public_model_exports_reference_implementations() -> None:
    """Public model exports should reference their defining implementations."""
    assert x12.X12Document is X12Document
    assert x12.X12FunctionalGroup is X12FunctionalGroup
    assert x12.X12FunctionalGroupInspection is X12FunctionalGroupInspection
    assert x12.X12InspectionResult is X12InspectionResult
    assert x12.X12Interchange is X12Interchange
    assert x12.X12Segment is X12Segment
    assert x12.X12SegmentFrequency is X12SegmentFrequency
    assert x12.X12Separators is X12Separators
    assert x12.X12TransactionInspection is X12TransactionInspection
    assert x12.X12TransactionSet is X12TransactionSet


def test_public_exception_exports_reference_implementations() -> None:
    """Public exception exports should reference their defining classes."""
    assert x12.X12Error is X12Error
    assert x12.X12EnvelopeError is X12EnvelopeError
    assert x12.X12SegmentError is X12SegmentError
    assert x12.X12SeparatorError is X12SeparatorError
    assert x12.X12TokenizerError is X12TokenizerError


def test_public_service_exports_reference_implementations() -> None:
    """Public service exports should reference their defining functions."""
    assert x12.derive_x12_separators is derive_x12_separators
    assert x12.inspect_x12_interchange is inspect_x12_interchange
    assert x12.parse_x12_interchange is parse_x12_interchange
    assert x12.tokenize_x12 is tokenize_x12


def test_public_services_are_callable() -> None:
    """Every public service should be callable."""
    assert callable(x12.derive_x12_separators)
    assert callable(x12.inspect_x12_interchange)
    assert callable(x12.parse_x12_interchange)
    assert callable(x12.tokenize_x12)


def test_every_declared_public_name_exists() -> None:
    """Every name listed in __all__ should exist on the package."""
    assert all(hasattr(x12, name) for name in x12.__all__)


def test_declared_public_names_do_not_include_private_names() -> None:
    """The public API should not expose private-style names."""
    assert all(not name.startswith("_") for name in x12.__all__)


def test_public_annotations_are_runtime_resolvable() -> None:
    """Public annotations should resolve through ``typing.get_type_hints``."""
    for name in x12.__all__:
        public_object = getattr(x12, name)

        if inspect.isclass(public_object) or inspect.isfunction(public_object):
            get_type_hints(public_object)
