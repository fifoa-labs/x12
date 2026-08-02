"""
tests/core/test_inspector.py

Tests for structural X12 interchange inspection services.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from x12 import parse_x12_interchange, tokenize_x12
from x12.core.inspection import (
    X12FunctionalGroupInspection,
    X12InspectionResult,
    X12SegmentFrequency,
    X12TransactionInspection,
)
from x12.core.inspector import inspect_x12_interchange

if TYPE_CHECKING:
    from x12.core.envelopes import X12Interchange

FIXTURES_DIRECTORY = Path(__file__).parent / "fixtures"
SAMPLE_MESSAGE_FIXTURE = FIXTURES_DIRECTORY / "sample_message"


def build_isa_segment(  # noqa: PLR0913
    *,
    control_number: bytes = b"000000001",
    usage_indicator: bytes = b"T",
    element: bytes = b"*",
    repetition: bytes = b"^",
    component: bytes = b":",
    terminator: bytes = b"~",
) -> bytes:
    """Build a generic, valid, fixed-width ISA segment."""
    values = (
        b"00",
        b"".ljust(10),
        b"00",
        b"".ljust(10),
        b"ZZ",
        b"SENDER01".ljust(15),
        b"ZZ",
        b"RECEIVER01".ljust(15),
        b"260101",
        b"1200",
        repetition,
        b"00705",
        control_number,
        b"0",
        usage_indicator,
        component,
    )

    isa = b"ISA" + element + element.join(values) + terminator

    assert len(isa) == 106
    return isa


def build_payload() -> bytes:
    """Build one valid interchange containing two generic transactions."""
    return b"".join(
        (
            build_isa_segment(),
            b"GS*XX*SENDER01*RECEIVER01*20260101*1200*1*X*007050~",
            b"ST*999*0001~",
            b"DTM*011*20260101~",
            b"N1*SH*PARTY-ONE~",
            b"SE*4*0001~",
            b"ST*999*0002~",
            b"DTM*011*20260101~",
            b"REF*AA*VALUE-ONE~",
            b"REF*BB*VALUE-TWO~",
            b"SE*5*0002~",
            b"GE*2*1~",
            b"IEA*1*000000001~",
        )
    )


@pytest.fixture
def interchange() -> X12Interchange:
    """Return a parsed generic interchange."""
    return parse_x12_interchange(tokenize_x12(build_payload()))


@pytest.fixture
def inspection(
    interchange: X12Interchange,
) -> X12InspectionResult:
    """Return the inspection result for the generic interchange."""
    return inspect_x12_interchange(interchange)


def test_inspector_returns_inspection_result(
    inspection: X12InspectionResult,
) -> None:
    """The inspector should return an immutable inspection result."""
    assert isinstance(inspection, X12InspectionResult)


def test_inspector_copies_interchange_metadata(
    inspection: X12InspectionResult,
) -> None:
    """Interchange metadata should be copied into the result."""
    assert inspection.interchange_version == b"00705"
    assert inspection.interchange_control_number == b"000000001"
    assert inspection.usage_indicator == b"T"
    assert inspection.declared_group_count == 1
    assert inspection.actual_group_count == 1


def test_inspector_copies_separator_metadata(
    inspection: X12InspectionResult,
) -> None:
    """Discovered separators should be copied into the result."""
    assert inspection.element_separator == b"*"
    assert inspection.repetition_separator == b"^"
    assert inspection.component_separator == b":"
    assert inspection.segment_terminator == b"~"


def test_inspector_counts_transactions(
    inspection: X12InspectionResult,
) -> None:
    """The result should count all transaction sets."""
    assert inspection.total_transaction_count == 2
    assert inspection.transaction_set_codes == (
        b"999",
        b"999",
    )


def test_inspector_counts_all_document_segments(
    interchange: X12Interchange,
    inspection: X12InspectionResult,
) -> None:
    """The result should count every document segment."""
    assert inspection.total_segment_count == len(interchange.document)
    assert inspection.total_segment_count == 13


def test_inspector_builds_group_inspection(
    inspection: X12InspectionResult,
) -> None:
    """A functional group should be represented by one group inspection."""
    assert len(inspection.groups) == 1

    group = inspection.groups[0]

    assert isinstance(group, X12FunctionalGroupInspection)
    assert group.index == 0
    assert group.functional_identifier_code == b"XX"
    assert group.application_sender_code == b"SENDER01"
    assert group.application_receiver_code == b"RECEIVER01"
    assert group.control_number == b"1"
    assert group.implementation_version == b"007050"
    assert group.declared_transaction_count == 2
    assert group.actual_transaction_count == 2


def test_inspector_builds_transaction_inspections(
    inspection: X12InspectionResult,
) -> None:
    """Each transaction set should produce one transaction inspection."""
    transactions = inspection.groups[0].transactions

    assert len(transactions) == 2
    assert all(
        isinstance(transaction, X12TransactionInspection)
        for transaction in transactions
    )
    assert tuple(transaction.index for transaction in transactions) == (
        0,
        1,
    )
    assert tuple(transaction.control_number for transaction in transactions) == (
        b"0001",
        b"0002",
    )


def test_inspector_reports_transaction_counts(
    inspection: X12InspectionResult,
) -> None:
    """Declared and observed transaction segment counts should be retained."""
    first, second = inspection.groups[0].transactions

    assert first.declared_segment_count == 4
    assert first.actual_segment_count == 4
    assert second.declared_segment_count == 5
    assert second.actual_segment_count == 5


def test_inspector_preserves_first_transaction_segment_order(
    inspection: X12InspectionResult,
) -> None:
    """The first transaction's segment order should be preserved."""
    first = inspection.groups[0].transactions[0]

    assert first.segment_tags == (
        "ST",
        "DTM",
        "N1",
        "SE",
    )


def test_inspector_preserves_second_transaction_segment_order(
    inspection: X12InspectionResult,
) -> None:
    """The second transaction's segment order should be preserved."""
    second = inspection.groups[0].transactions[1]

    assert second.segment_tags == (
        "ST",
        "DTM",
        "REF",
        "REF",
        "SE",
    )


def test_inspector_reports_transaction_segment_frequencies(
    inspection: X12InspectionResult,
) -> None:
    """Transaction frequencies should preserve first-appearance order."""
    first, second = inspection.groups[0].transactions

    assert first.segment_frequencies == (
        X12SegmentFrequency(tag="ST", count=1),
        X12SegmentFrequency(tag="DTM", count=1),
        X12SegmentFrequency(tag="N1", count=1),
        X12SegmentFrequency(tag="SE", count=1),
    )
    assert second.segment_frequencies == (
        X12SegmentFrequency(tag="ST", count=1),
        X12SegmentFrequency(tag="DTM", count=1),
        X12SegmentFrequency(tag="REF", count=2),
        X12SegmentFrequency(tag="SE", count=1),
    )


def test_inspector_reports_repeating_transaction_segments(
    inspection: X12InspectionResult,
) -> None:
    """Repeating transaction tags should be reported in frequency order."""
    first, second = inspection.groups[0].transactions

    assert first.repeating_segment_tags == ()
    assert second.repeating_segment_tags == ("REF",)


def test_inspector_reports_document_frequencies_in_first_seen_order(
    inspection: X12InspectionResult,
) -> None:
    """Document frequencies should preserve first-appearance order."""
    assert inspection.segment_frequencies == (
        X12SegmentFrequency(tag="ISA", count=1),
        X12SegmentFrequency(tag="GS", count=1),
        X12SegmentFrequency(tag="ST", count=2),
        X12SegmentFrequency(tag="DTM", count=2),
        X12SegmentFrequency(tag="N1", count=1),
        X12SegmentFrequency(tag="SE", count=2),
        X12SegmentFrequency(tag="REF", count=2),
        X12SegmentFrequency(tag="GE", count=1),
        X12SegmentFrequency(tag="IEA", count=1),
    )


def test_inspector_reports_unique_document_tags(
    inspection: X12InspectionResult,
) -> None:
    """Unique tags should be returned in first-appearance order."""
    assert inspection.unique_segment_tags == (
        "ISA",
        "GS",
        "ST",
        "DTM",
        "N1",
        "SE",
        "REF",
        "GE",
        "IEA",
    )


def test_inspector_reports_repeating_document_tags(
    inspection: X12InspectionResult,
) -> None:
    """Document tags occurring more than once should be reported."""
    assert inspection.repeating_segment_tags == (
        "ST",
        "DTM",
        "SE",
        "REF",
    )


def test_inspector_numbers_groups_from_zero() -> None:
    """Functional-group inspection indexes should be zero-based."""
    payload = b"".join(
        (
            build_isa_segment(),
            b"GS*XX*SENDER01*RECEIVER01*20260101*1200*1*X*007050~",
            b"ST*999*0001~",
            b"SE*2*0001~",
            b"GE*1*1~",
            b"GS*XX*SENDER01*RECEIVER01*20260101*1300*2*X*007050~",
            b"ST*999*0002~",
            b"SE*2*0002~",
            b"GE*1*2~",
            b"IEA*2*000000001~",
        )
    )

    result = inspect_x12_interchange(parse_x12_interchange(tokenize_x12(payload)))

    assert tuple(group.index for group in result.groups) == (
        0,
        1,
    )


def test_inspector_numbers_transactions_from_zero_per_group() -> None:
    """Transaction indexes should restart from zero for each group."""
    payload = b"".join(
        (
            build_isa_segment(),
            b"GS*XX*SENDER01*RECEIVER01*20260101*1200*1*X*007050~",
            b"ST*999*0001~",
            b"SE*2*0001~",
            b"ST*999*0002~",
            b"SE*2*0002~",
            b"GE*2*1~",
            b"GS*XX*SENDER01*RECEIVER01*20260101*1300*2*X*007050~",
            b"ST*999*0003~",
            b"SE*2*0003~",
            b"GE*1*2~",
            b"IEA*2*000000001~",
        )
    )

    result = inspect_x12_interchange(parse_x12_interchange(tokenize_x12(payload)))

    assert tuple(
        transaction.index for transaction in result.groups[0].transactions
    ) == (
        0,
        1,
    )
    assert tuple(
        transaction.index for transaction in result.groups[1].transactions
    ) == (0,)


def test_inspector_supports_ta1_only_interchange() -> None:
    """A TA1-only interchange should produce an empty group summary."""
    payload = b"".join(
        (
            build_isa_segment(),
            b"TA1*000000002*260101*1200*A*000~",
            b"IEA*0*000000001~",
        )
    )

    result = inspect_x12_interchange(parse_x12_interchange(tokenize_x12(payload)))

    assert result.groups == ()
    assert result.actual_group_count == 0
    assert result.total_transaction_count == 0
    assert result.transaction_set_codes == ()
    assert result.total_segment_count == 3


def test_inspector_supports_minimal_functional_group() -> None:
    """A minimal functional group should contain one transaction inspection."""
    payload = b"".join(
        (
            build_isa_segment(),
            b"GS*XX*SENDER01*RECEIVER01*20260101*1200*1*X*007050~",
            b"ST*999*0001~",
            b"SE*2*0001~",
            b"GE*1*1~",
            b"IEA*1*000000001~",
        )
    )

    result = inspect_x12_interchange(parse_x12_interchange(tokenize_x12(payload)))
    group = result.groups[0]

    assert len(group.transactions) == 1
    assert group.actual_transaction_count == 1
    assert result.total_transaction_count == 1
    assert group.transactions[0].transaction_set_code == b"999"


def test_inspector_returns_new_result_each_time(
    interchange: X12Interchange,
) -> None:
    """Repeated inspection should return equal, independent results."""
    first = inspect_x12_interchange(interchange)
    second = inspect_x12_interchange(interchange)

    assert first == second
    assert first is not second


def test_inspector_does_not_mutate_interchange(
    interchange: X12Interchange,
) -> None:
    """Inspection should not mutate the source interchange or document."""
    original_groups = interchange.groups
    original_segments = interchange.document.segments
    original_raw = interchange.document.raw

    inspect_x12_interchange(interchange)

    assert interchange.groups is original_groups
    assert interchange.document.segments is original_segments
    assert interchange.document.raw is original_raw


def test_sample_fixture_inspection() -> None:
    """The generic sample fixture should inspect as a complete interchange."""
    payload = SAMPLE_MESSAGE_FIXTURE.read_bytes()

    result = inspect_x12_interchange(parse_x12_interchange(tokenize_x12(payload)))

    assert result.interchange_version == b"00705"
    assert result.interchange_control_number == b"000000010"
    assert result.usage_indicator == b"T"
    assert result.element_separator == b"*"
    assert result.repetition_separator == b"U"
    assert result.component_separator == b">"
    assert result.declared_group_count == 1
    assert result.actual_group_count == 1
    assert result.total_transaction_count == 2
    assert result.transaction_set_codes == (
        b"322",
        b"322",
    )


def test_sample_fixture_group_inspection() -> None:
    """The generic sample fixture should expose its group metadata."""
    payload = SAMPLE_MESSAGE_FIXTURE.read_bytes()

    result = inspect_x12_interchange(parse_x12_interchange(tokenize_x12(payload)))
    group = result.groups[0]

    assert group.index == 0
    assert group.functional_identifier_code == b"SO"
    assert group.application_sender_code == b"SENDER01"
    assert group.application_receiver_code == b"RECEIVER01"
    assert group.control_number == b"10"
    assert group.implementation_version == b"007050"
    assert group.declared_transaction_count == 2
    assert group.actual_transaction_count == 2


def test_sample_fixture_transaction_inspections() -> None:
    """The generic sample fixture should expose both transactions."""
    payload = SAMPLE_MESSAGE_FIXTURE.read_bytes()

    result = inspect_x12_interchange(parse_x12_interchange(tokenize_x12(payload)))
    first, second = result.groups[0].transactions

    assert first.index == 0
    assert first.transaction_set_code == b"322"
    assert first.control_number == b"100001"
    assert first.declared_segment_count == 12
    assert first.actual_segment_count == 12

    assert second.index == 1
    assert second.transaction_set_code == b"322"
    assert second.control_number == b"100002"
    assert second.declared_segment_count == 12
    assert second.actual_segment_count == 12


def test_sample_fixture_transaction_shapes() -> None:
    """Both generic fixture transactions should have the expected shape."""
    payload = SAMPLE_MESSAGE_FIXTURE.read_bytes()

    result = inspect_x12_interchange(parse_x12_interchange(tokenize_x12(payload)))
    first, second = result.groups[0].transactions

    expected = (
        "ST",
        "Q5",
        "N7",
        "W2",
        "R4",
        "R4",
        "R4",
        "N1",
        "N1",
        "N9",
        "N9",
        "SE",
    )

    assert first.segment_tags == expected
    assert second.segment_tags == expected


def test_sample_fixture_segment_frequencies() -> None:
    """The generic sample fixture should expose its segment frequencies."""
    payload = SAMPLE_MESSAGE_FIXTURE.read_bytes()

    result = inspect_x12_interchange(parse_x12_interchange(tokenize_x12(payload)))

    frequencies = {
        frequency.tag: frequency.count for frequency in result.segment_frequencies
    }

    assert frequencies == {
        "ISA": 1,
        "GS": 1,
        "ST": 2,
        "Q5": 2,
        "N7": 2,
        "W2": 2,
        "R4": 6,
        "N1": 4,
        "N9": 4,
        "SE": 2,
        "GE": 1,
        "IEA": 1,
    }
