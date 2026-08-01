"""
src/x12/segments.py

Immutable structural models produced by the X12 tokenizer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

    from .separators import X12Separators


@dataclass(frozen=True, slots=True)
class X12Segment:
    """One tokenized X12 segment.

    Attributes:
        index: Zero-based position of the segment within the document.
        tag: ASCII segment identifier, such as ``ISA``, ``GS``, or ``ST``.
        elements: Element values in their original byte representation,
            excluding the segment tag.
        raw: Original segment bytes, excluding the segment terminator and any
            formatting whitespace between segments.
    """

    index: int
    tag: str
    elements: tuple[bytes, ...]
    raw: bytes

    def __post_init__(self) -> None:
        """Validate invariants required by a tokenized segment."""
        if self.index < 0:
            msg = "X12 segment index cannot be negative."
            raise ValueError(msg)

        if not self.tag:
            msg = "X12 segment tag cannot be empty."
            raise ValueError(msg)

        if not self.tag.isascii() or not self.tag.isalnum():
            msg = "X12 segment tag must be ASCII alphanumeric."
            raise ValueError(msg)

        if not self.raw:
            msg = "X12 segment raw data cannot be empty."
            raise ValueError(msg)

    def element(self, position: int) -> bytes | None:
        """Return an element by its one-based X12 position.

        X12 specifications number data elements beginning with one. For
        example, ``segment.element(1)`` returns the first element following
        the segment tag.

        Args:
            position: One-based element position.

        Returns:
            The element bytes, or ``None`` when the requested position is
            beyond the available elements.

        Raises:
            ValueError: If ``position`` is less than one.
        """
        if position < 1:
            msg = "X12 element positions are one-based."
            raise ValueError(msg)

        index = position - 1

        if index >= len(self.elements):
            return None

        return self.elements[index]


@dataclass(frozen=True, slots=True)
class X12Document:
    """A tokenized X12 document with its original byte representation.

    Attributes:
        raw: Original, unmodified X12 payload.
        separators: Separators derived from the document's ISA segment.
        segments: Ordered tokenized segments.
    """

    raw: bytes
    separators: X12Separators
    segments: tuple[X12Segment, ...]

    def __post_init__(self) -> None:
        """Validate document-level structural invariants."""
        if not self.raw:
            msg = "X12 document raw data cannot be empty."
            raise ValueError(msg)

        if not self.segments:
            msg = "X12 document must contain at least one segment."
            raise ValueError(msg)

        for expected_index, segment in enumerate(self.segments):
            if segment.index != expected_index:
                msg = (
                    "X12 segment indexes must be contiguous and match their "
                    f"document positions; expected {expected_index}, found "
                    f"{segment.index}."
                )
                raise ValueError(msg)

    def __iter__(self) -> Iterator[X12Segment]:
        """Iterate over segments in document order."""
        return iter(self.segments)

    def __len__(self) -> int:
        """Return the number of segments in the document."""
        return len(self.segments)

    def find_segments(self, tag: str) -> tuple[X12Segment, ...]:
        """Return all segments whose tag exactly matches ``tag``."""
        return tuple(segment for segment in self.segments if segment.tag == tag)

    @property
    def first_segment(self) -> X12Segment:
        """Return the first segment in the document."""
        return self.segments[0]

    @property
    def last_segment(self) -> X12Segment:
        """Return the final segment in the document."""
        return self.segments[-1]


__all__ = [
    "X12Document",
    "X12Segment",
]
