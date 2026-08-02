"""
src/x12/core/separators.py

Separator definitions and ISA-based separator discovery for ANSI X12 data.
"""

from __future__ import annotations

from dataclasses import dataclass

from .exceptions import X12EnvelopeError, X12SeparatorError

ISA_SEGMENT_LENGTH = 106
ISA_TAG = b"ISA"

ISA_ELEMENT_SEPARATOR_INDEX = 3
ISA_REPETITION_SEPARATOR_INDEX = 82
ISA_VERSION_START_INDEX = 84
ISA_VERSION_END_INDEX = 89
ISA_COMPONENT_SEPARATOR_INDEX = 104
ISA_SEGMENT_TERMINATOR_INDEX = 105

ISA_ELEMENT_SEPARATOR_INDICES = (
    3,
    6,
    17,
    20,
    31,
    34,
    50,
    53,
    69,
    76,
    81,
    83,
    89,
    99,
    101,
    103,
)

REPETITION_SEPARATOR_MINIMUM_VERSION = 402


@dataclass(frozen=True, slots=True)
class X12Separators:
    """Single-byte separators discovered from an ISA interchange header.

    Attributes:
        element: Separator between data elements.
        component: Separator between component elements.
        segment: Terminator marking the end of each segment.
        repetition: Separator between repeated elements for version 00402
            and later, or ``None`` for earlier interchange versions.
    """

    element: bytes
    component: bytes
    segment: bytes
    repetition: bytes | None = None

    def __post_init__(self) -> None:
        """Validate separator types, lengths, and uniqueness."""
        configured = {
            "element": self.element,
            "component": self.component,
            "segment": self.segment,
            "repetition": self.repetition,
        }

        for name, separator in configured.items():
            if separator is None:
                continue

            if not isinstance(separator, bytes):
                msg = f"{name.capitalize()} separator must be bytes."
                raise TypeError(msg)

            if len(separator) != 1:
                msg = f"{name.capitalize()} separator must contain exactly one byte."
                raise X12SeparatorError(msg)

        required = {
            self.element,
            self.component,
            self.segment,
        }

        if len(required) != 3:  # noqa: PLR2004
            msg = "Element, component, and segment separators must be distinct."
            raise X12SeparatorError(msg)

        if self.repetition is not None and self.repetition in required:
            msg = (
                "Repetition separator must be distinct from the element, "
                "component, and segment separators."
            )
            raise X12SeparatorError(msg)


def derive_x12_separators(payload: bytes) -> X12Separators:
    """Derive separators from the payload's initial ISA segment.

    The ISA interchange header has a fixed length of 106 bytes, including its
    segment terminator. Its fixed-width layout makes it possible to locate and
    validate separators without examining transaction-set content.

    For interchange version 00402 and later, ISA11 contains the repetition
    separator. In earlier versions, ISA11 has a different meaning, so
    ``repetition`` is returned as ``None``.

    Args:
        payload: Complete or partial X12 payload beginning with ISA.

    Returns:
        Separators derived from the ISA header.

    Raises:
        X12EnvelopeError: If the ISA header is missing, incomplete, or does
            not conform to its required fixed-width layout.
        X12SeparatorError: If discovered separators are invalid or overlap.
    """
    if len(payload) < ISA_SEGMENT_LENGTH:
        msg = "X12 payload is too short to contain the complete 106-byte ISA segment."
        raise X12EnvelopeError(msg)

    if not payload.startswith(ISA_TAG):
        msg = "X12 payload must begin with an ISA interchange header."
        raise X12EnvelopeError(msg)

    element_separator = payload[
        ISA_ELEMENT_SEPARATOR_INDEX : ISA_ELEMENT_SEPARATOR_INDEX + 1
    ]

    for index in ISA_ELEMENT_SEPARATOR_INDICES:
        candidate = payload[index : index + 1]

        if candidate != element_separator:
            msg = (
                "ISA segment does not follow the required fixed-width layout: "
                f"expected element separator {element_separator!r} at byte "
                f"offset {index}, found {candidate!r}."
            )
            raise X12EnvelopeError(msg)

    version = _parse_isa_version(payload)

    repetition_separator = None
    if version >= REPETITION_SEPARATOR_MINIMUM_VERSION:
        repetition_separator = payload[
            ISA_REPETITION_SEPARATOR_INDEX : ISA_REPETITION_SEPARATOR_INDEX + 1
        ]

    component_separator = payload[
        ISA_COMPONENT_SEPARATOR_INDEX : ISA_COMPONENT_SEPARATOR_INDEX + 1
    ]
    segment_terminator = payload[
        ISA_SEGMENT_TERMINATOR_INDEX : ISA_SEGMENT_TERMINATOR_INDEX + 1
    ]

    return X12Separators(
        element=element_separator,
        component=component_separator,
        segment=segment_terminator,
        repetition=repetition_separator,
    )


def _parse_isa_version(payload: bytes) -> int:
    """Parse ISA12 into a comparable integer such as ``402`` or ``705``."""
    raw_version = payload[ISA_VERSION_START_INDEX:ISA_VERSION_END_INDEX]

    if not raw_version.isdigit():
        msg = f"ISA12 contains an invalid interchange version: {raw_version!r}."
        raise X12EnvelopeError(msg)

    return int(raw_version)


__all__ = [
    "X12Separators",
    "derive_x12_separators",
]
