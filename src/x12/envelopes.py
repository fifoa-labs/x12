"""
src/x12/envelopes.py

Immutable structural models for parsed ANSI X12 envelopes.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .segments import X12Document, X12Segment


def _parse_count(value: bytes | None) -> int | None:
    """Return a non-negative decimal count, or ``None`` when invalid."""
    if value is None or not value.isdigit():
        return None

    return int(value)


@dataclass(frozen=True, slots=True)
class X12TransactionSet:
    """One transaction set delimited by ST and SE segments.

    Attributes:
        header: Opening ST segment.
        segments: Ordered segments between ST and SE.
        trailer: Closing SE segment.
    """

    header: X12Segment
    segments: tuple[X12Segment, ...]
    trailer: X12Segment

    def __post_init__(self) -> None:
        """Validate transaction-set boundary tags and segment order."""
        if self.header.tag != "ST":
            msg = (
                "X12 transaction-set header must be an ST segment; "
                f"found {self.header.tag!r}."
            )
            raise ValueError(msg)

        if self.trailer.tag != "SE":
            msg = (
                "X12 transaction-set trailer must be an SE segment; "
                f"found {self.trailer.tag!r}."
            )
            raise ValueError(msg)

        _validate_segment_order(self.all_segments, envelope_name="transaction set")

    @property
    def transaction_set_code(self) -> bytes | None:
        """Return ST01, which identifies the transaction-set type."""
        return self.header.element(1)

    @property
    def control_number(self) -> bytes | None:
        """Return ST02, which identifies this transaction set."""
        return self.header.element(2)

    @property
    def trailer_control_number(self) -> bytes | None:
        """Return SE02, which should match ST02."""
        return self.trailer.element(2)

    @property
    def declared_segment_count(self) -> int | None:
        """Return SE01 as an integer when present and decimal."""
        return _parse_count(self.trailer.element(1))

    @property
    def actual_segment_count(self) -> int:
        """Return the number of segments from ST through SE, inclusive."""
        return len(self.segments) + 2

    @property
    def all_segments(self) -> tuple[X12Segment, ...]:
        """Return all transaction-set segments from ST through SE."""
        return (
            self.header,
            *self.segments,
            self.trailer,
        )


@dataclass(frozen=True, slots=True)
class X12FunctionalGroup:
    """One functional group delimited by GS and GE segments.

    Attributes:
        header: Opening GS segment.
        transactions: Ordered transaction sets within the group.
        trailer: Closing GE segment.
    """

    header: X12Segment
    transactions: tuple[X12TransactionSet, ...]
    trailer: X12Segment

    def __post_init__(self) -> None:
        """Validate functional-group boundary tags and segment order."""
        if self.header.tag != "GS":
            msg = (
                "X12 functional-group header must be a GS segment; "
                f"found {self.header.tag!r}."
            )
            raise ValueError(msg)

        if self.trailer.tag != "GE":
            msg = (
                "X12 functional-group trailer must be a GE segment; "
                f"found {self.trailer.tag!r}."
            )
            raise ValueError(msg)

        _validate_segment_order(self.all_segments, envelope_name="functional group")

    @property
    def functional_identifier_code(self) -> bytes | None:
        """Return GS01, which identifies the functional-group type."""
        return self.header.element(1)

    @property
    def application_sender_code(self) -> bytes | None:
        """Return GS02, the application sender's code."""
        return self.header.element(2)

    @property
    def application_receiver_code(self) -> bytes | None:
        """Return GS03, the application receiver's code."""
        return self.header.element(3)

    @property
    def control_number(self) -> bytes | None:
        """Return GS06, which identifies this functional group."""
        return self.header.element(6)

    @property
    def trailer_control_number(self) -> bytes | None:
        """Return GE02, which should match GS06."""
        return self.trailer.element(2)

    @property
    def implementation_version(self) -> bytes | None:
        """Return GS08, the implementation version when present."""
        return self.header.element(8)

    @property
    def declared_transaction_count(self) -> int | None:
        """Return GE01 as an integer when present and decimal."""
        return _parse_count(self.trailer.element(1))

    @property
    def actual_transaction_count(self) -> int:
        """Return the number of parsed transaction sets."""
        return len(self.transactions)

    @property
    def all_segments(self) -> tuple[X12Segment, ...]:
        """Return all functional-group segments from GS through GE."""
        return (
            self.header,
            *(
                segment
                for transaction in self.transactions
                for segment in transaction.all_segments
            ),
            self.trailer,
        )


@dataclass(frozen=True, slots=True)
class X12Interchange:
    """One interchange delimited by ISA and IEA segments.

    Attributes:
        document: Tokenized source document for this interchange.
        header: Opening ISA segment.
        groups: Ordered functional groups within the interchange.
        trailer: Closing IEA segment.
    """

    document: X12Document
    header: X12Segment
    groups: tuple[X12FunctionalGroup, ...]
    trailer: X12Segment

    def __post_init__(self) -> None:
        """Validate interchange boundaries, order, and source consistency."""
        if self.header.tag != "ISA":
            msg = (
                "X12 interchange header must be an ISA segment; "
                f"found {self.header.tag!r}."
            )
            raise ValueError(msg)

        if self.trailer.tag != "IEA":
            msg = (
                "X12 interchange trailer must be an IEA segment; "
                f"found {self.trailer.tag!r}."
            )
            raise ValueError(msg)

        all_segments = self.all_segments
        _validate_segment_order(all_segments, envelope_name="interchange")

        if self.document.segments != all_segments:
            msg = (
                "X12 interchange segments must exactly match the segments "
                "in its source document."
            )
            raise ValueError(msg)

    @property
    def authorization_information_qualifier(self) -> bytes | None:
        """Return ISA01, the authorization-information qualifier."""
        return self.header.element(1)

    @property
    def security_information_qualifier(self) -> bytes | None:
        """Return ISA03, the security-information qualifier."""
        return self.header.element(3)

    @property
    def sender_qualifier(self) -> bytes | None:
        """Return ISA05, the interchange sender qualifier."""
        return self.header.element(5)

    @property
    def sender_identifier(self) -> bytes | None:
        """Return ISA06 without altering its fixed-width bytes."""
        return self.header.element(6)

    @property
    def receiver_qualifier(self) -> bytes | None:
        """Return ISA07, the interchange receiver qualifier."""
        return self.header.element(7)

    @property
    def receiver_identifier(self) -> bytes | None:
        """Return ISA08 without altering its fixed-width bytes."""
        return self.header.element(8)

    @property
    def interchange_version(self) -> bytes | None:
        """Return ISA12, the interchange-control version."""
        return self.header.element(12)

    @property
    def control_number(self) -> bytes | None:
        """Return ISA13, which identifies this interchange."""
        return self.header.element(13)

    @property
    def trailer_control_number(self) -> bytes | None:
        """Return IEA02, which should match ISA13."""
        return self.trailer.element(2)

    @property
    def usage_indicator(self) -> bytes | None:
        """Return ISA15, which indicates test or production usage."""
        return self.header.element(15)

    @property
    def declared_group_count(self) -> int | None:
        """Return IEA01 as an integer when present and decimal."""
        return _parse_count(self.trailer.element(1))

    @property
    def actual_group_count(self) -> int:
        """Return the number of parsed functional groups."""
        return len(self.groups)

    @property
    def all_segments(self) -> tuple[X12Segment, ...]:
        """Return all interchange segments from ISA through IEA."""
        return (
            self.header,
            *(segment for group in self.groups for segment in group.all_segments),
            self.trailer,
        )


def _validate_segment_order(
    segments: tuple[X12Segment, ...],
    *,
    envelope_name: str,
) -> None:
    """Ensure an envelope's segments are ordered and contiguous."""
    for previous, current in itertools.pairwise(segments):
        expected_index = previous.index + 1

        if current.index != expected_index:
            msg = (
                f"X12 {envelope_name} segments must be contiguous; "
                f"expected segment index {expected_index}, found "
                f"{current.index}."
            )
            raise ValueError(msg)


__all__ = [
    "X12FunctionalGroup",
    "X12Interchange",
    "X12TransactionSet",
]
