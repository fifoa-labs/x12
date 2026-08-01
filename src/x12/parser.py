"""
src/x12/parser.py

Parse tokenized ANSI X12 documents into validated interchange envelopes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .envelopes import (
    X12FunctionalGroup,
    X12Interchange,
    X12TransactionSet,
)
from .exceptions import X12EnvelopeError

if TYPE_CHECKING:
    from .segments import X12Document, X12Segment


def parse_x12_interchange(document: X12Document) -> X12Interchange:
    """Parse and validate one complete X12 interchange document."""
    if document.first_segment.tag != "ISA":
        msg = "X12 interchange must begin with an ISA segment."
        raise X12EnvelopeError(msg)

    if document.last_segment.tag != "IEA":
        msg = "X12 interchange must end with an IEA segment."
        raise X12EnvelopeError(msg)

    header = document.first_segment
    _require_element_count(
        header,
        expected=16,
    )

    groups: list[X12FunctionalGroup] = []
    cursor = 1

    while True:
        segment = document.segments[cursor]

        if segment.tag == "IEA":
            break

        if segment.tag != "GS":
            msg = (
                f"Expected GS or IEA at segment index {segment.index}, "
                f"found {segment.tag!r}."
            )
            raise X12EnvelopeError(msg)

        group, cursor = _parse_functional_group(
            document.segments,
            cursor,
        )
        groups.append(group)

    trailer = document.segments[cursor]

    if cursor != len(document.segments) - 1:
        trailing = document.segments[cursor + 1]

        msg = (
            f"Unexpected segment {trailing.tag!r} appears after IEA "
            f"at segment index {trailing.index}."
        )
        raise X12EnvelopeError(msg)

    _require_element_count(
        trailer,
        expected=2,
    )

    interchange = X12Interchange(
        document=document,
        header=header,
        groups=tuple(groups),
        trailer=trailer,
    )

    _validate_interchange(interchange)

    return interchange


def _parse_functional_group(
    segments: tuple[X12Segment, ...],
    start: int,
) -> tuple[X12FunctionalGroup, int]:
    """Parse one GS/GE-delimited functional group."""
    header = segments[start]
    _require_element_count(
        header,
        expected=8,
    )

    transactions: list[X12TransactionSet] = []
    cursor = start + 1

    while True:
        segment = segments[cursor]

        if segment.tag == "GE":
            break

        if segment.tag != "ST":
            msg = (
                f"Expected ST or GE inside functional group at segment "
                f"index {segment.index}, found {segment.tag!r}."
            )
            raise X12EnvelopeError(msg)

        transaction, cursor = _parse_transaction_set(
            segments,
            cursor,
        )
        transactions.append(transaction)

    trailer = segments[cursor]

    _require_element_count(
        trailer,
        expected=2,
    )

    group = X12FunctionalGroup(
        header=header,
        transactions=tuple(transactions),
        trailer=trailer,
    )

    _validate_functional_group(group)

    return group, cursor + 1


def _parse_transaction_set(
    segments: tuple[X12Segment, ...],
    start: int,
) -> tuple[X12TransactionSet, int]:
    """Parse one ST/SE-delimited transaction set."""
    header = segments[start]
    _require_element_count(
        header,
        expected=2,
    )

    body: list[X12Segment] = []
    cursor = start + 1

    while True:
        segment = segments[cursor]

        if segment.tag == "SE":
            break

        if segment.tag in {
            "ISA",
            "GS",
            "ST",
            "GE",
            "IEA",
        }:
            msg = (
                f"Unexpected envelope segment {segment.tag!r} inside "
                f"transaction set beginning at segment index "
                f"{header.index}."
            )
            raise X12EnvelopeError(msg)

        body.append(segment)
        cursor += 1

    trailer = segments[cursor]

    _require_element_count(
        trailer,
        expected=2,
    )

    transaction = X12TransactionSet(
        header=header,
        segments=tuple(body),
        trailer=trailer,
    )

    _validate_transaction_set(transaction)

    return transaction, cursor + 1


def _validate_transaction_set(
    transaction: X12TransactionSet,
) -> None:
    """Validate one ST/SE transaction-set envelope."""
    header_control_number = _require_element(
        transaction.header,
        position=2,
        name="ST02",
    )
    trailer_control_number = _require_element(
        transaction.trailer,
        position=2,
        name="SE02",
    )

    if header_control_number != trailer_control_number:
        msg = (
            "ST02 and SE02 transaction-set control numbers do not match: "
            f"{header_control_number!r} != "
            f"{trailer_control_number!r}."
        )
        raise X12EnvelopeError(msg)

    _require_element(
        transaction.header,
        position=1,
        name="ST01",
    )

    declared_count = _require_positive_integer(
        transaction.trailer,
        position=1,
        name="SE01",
    )

    if declared_count != transaction.actual_segment_count:
        msg = (
            "SE01 transaction segment count does not match the actual "
            f"number of segments: declared {declared_count}, "
            f"actual {transaction.actual_segment_count}."
        )
        raise X12EnvelopeError(msg)


def _validate_functional_group(
    group: X12FunctionalGroup,
) -> None:
    """Validate one GS/GE functional-group envelope."""
    header_control_number = _require_element(
        group.header,
        position=6,
        name="GS06",
    )
    trailer_control_number = _require_element(
        group.trailer,
        position=2,
        name="GE02",
    )

    if header_control_number != trailer_control_number:
        msg = (
            "GS06 and GE02 functional-group control numbers do not match: "
            f"{header_control_number!r} != "
            f"{trailer_control_number!r}."
        )
        raise X12EnvelopeError(msg)

    declared_count = _require_nonnegative_integer(
        group.trailer,
        position=1,
        name="GE01",
    )

    if declared_count != group.actual_transaction_count:
        msg = (
            "GE01 transaction-set count does not match the actual "
            f"number of transaction sets: declared {declared_count}, "
            f"actual {group.actual_transaction_count}."
        )
        raise X12EnvelopeError(msg)


def _validate_interchange(
    interchange: X12Interchange,
) -> None:
    """Validate the outer ISA/IEA interchange envelope."""
    header_control_number = _require_element(
        interchange.header,
        position=13,
        name="ISA13",
    )
    trailer_control_number = _require_element(
        interchange.trailer,
        position=2,
        name="IEA02",
    )

    if header_control_number != trailer_control_number:
        msg = (
            "ISA13 and IEA02 interchange control numbers do not match: "
            f"{header_control_number!r} != "
            f"{trailer_control_number!r}."
        )
        raise X12EnvelopeError(msg)

    declared_count = _require_nonnegative_integer(
        interchange.trailer,
        position=1,
        name="IEA01",
    )

    if declared_count != interchange.actual_group_count:
        msg = (
            "IEA01 functional-group count does not match the actual "
            f"number of groups: declared {declared_count}, "
            f"actual {interchange.actual_group_count}."
        )
        raise X12EnvelopeError(msg)


def _require_element_count(
    segment: X12Segment,
    *,
    expected: int,
) -> None:
    """Require a segment to contain the expected number of elements."""
    actual = len(segment.elements)

    if actual != expected:
        msg = (
            f"{segment.tag} segment at index {segment.index} must contain "
            f"exactly {expected} elements; found {actual}."
        )
        raise X12EnvelopeError(msg)


def _require_element(
    segment: X12Segment,
    *,
    position: int,
    name: str,
) -> bytes:
    """Return one required, nonempty segment element."""
    value = segment.element(position)

    if value is None or value == b"":
        msg = f"{name} is required in {segment.tag} segment at index {segment.index}."
        raise X12EnvelopeError(msg)

    return value


def _require_positive_integer(
    segment: X12Segment,
    *,
    position: int,
    name: str,
) -> int:
    """Return one required integer greater than zero."""
    value = _require_nonnegative_integer(
        segment,
        position=position,
        name=name,
    )

    if value < 1:
        msg = f"{name} must be greater than zero; found {value}."
        raise X12EnvelopeError(msg)

    return value


def _require_nonnegative_integer(
    segment: X12Segment,
    *,
    position: int,
    name: str,
) -> int:
    """Return one required integer greater than or equal to zero."""
    raw_value = _require_element(
        segment,
        position=position,
        name=name,
    )

    if not raw_value.isdigit():
        msg = f"{name} must contain only ASCII digits; found {raw_value!r}."
        raise X12EnvelopeError(msg)

    return int(raw_value)


__all__ = [
    "parse_x12_interchange",
]
