"""
tests/test_sample_message.py

Tests for the complete generic X12 sample-message fixture.
"""

from __future__ import annotations

from pathlib import Path

from x12 import parse_x12_interchange, tokenize_x12

FIXTURES_DIRECTORY = Path(__file__).parent / "fixtures"
SAMPLE_MESSAGE_FIXTURE = FIXTURES_DIRECTORY / "sample_message"


def test_sample_message_fixture_exists() -> None:
    """The sample message fixture should be present in the test suite."""
    assert SAMPLE_MESSAGE_FIXTURE.is_file()


def test_sample_message_tokenizes_as_x12() -> None:
    """The complete sample message should tokenize without data loss."""
    payload = SAMPLE_MESSAGE_FIXTURE.read_bytes()

    document = tokenize_x12(payload)

    assert document.raw == payload
    assert document.separators.element == b"*"
    assert document.separators.repetition == b"U"
    assert document.separators.component == b">"
    assert document.separators.segment == b"\r"
    assert len(document) == 28
    assert document.first_segment.tag == "ISA"
    assert document.last_segment.tag == "IEA"


def test_sample_message_parses_as_valid_x12_interchange() -> None:
    """The sample message should form one valid X12 interchange."""
    payload = SAMPLE_MESSAGE_FIXTURE.read_bytes()

    document = tokenize_x12(payload)
    interchange = parse_x12_interchange(document)

    assert interchange.document is document
    assert interchange.interchange_version == b"00705"
    assert interchange.control_number == b"000000010"
    assert interchange.trailer_control_number == b"000000010"
    assert interchange.usage_indicator == b"T"
    assert interchange.declared_group_count == 1
    assert interchange.actual_group_count == 1
    assert interchange.all_segments == document.segments


def test_sample_message_contains_one_valid_functional_group() -> None:
    """The fixture should contain one complete functional group."""
    payload = SAMPLE_MESSAGE_FIXTURE.read_bytes()

    interchange = parse_x12_interchange(tokenize_x12(payload))
    group = interchange.groups[0]

    assert group.functional_identifier_code == b"SO"
    assert group.application_sender_code == b"SENDER01"
    assert group.application_receiver_code == b"RECEIVER01"
    assert group.control_number == b"10"
    assert group.trailer_control_number == b"10"
    assert group.implementation_version == b"007050"
    assert group.declared_transaction_count == 2
    assert group.actual_transaction_count == 2


def test_sample_message_contains_two_valid_transactions() -> None:
    """The fixture should contain two structurally valid transaction sets."""
    payload = SAMPLE_MESSAGE_FIXTURE.read_bytes()

    interchange = parse_x12_interchange(tokenize_x12(payload))
    transactions = interchange.groups[0].transactions

    assert len(transactions) == 2

    assert tuple(transaction.transaction_set_code for transaction in transactions) == (
        b"322",
        b"322",
    )

    assert tuple(transaction.control_number for transaction in transactions) == (
        b"100001",
        b"100002",
    )

    assert tuple(
        transaction.trailer_control_number for transaction in transactions
    ) == (
        b"100001",
        b"100002",
    )

    assert tuple(
        transaction.declared_segment_count for transaction in transactions
    ) == (
        12,
        12,
    )

    assert tuple(transaction.actual_segment_count for transaction in transactions) == (
        12,
        12,
    )


def test_sample_message_preserves_transaction_segment_order() -> None:
    """Both transactions should preserve their original segment order."""
    payload = SAMPLE_MESSAGE_FIXTURE.read_bytes()

    interchange = parse_x12_interchange(tokenize_x12(payload))
    first, second = interchange.groups[0].transactions

    expected_tags = (
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

    assert tuple(segment.tag for segment in first.all_segments) == expected_tags
    assert tuple(segment.tag for segment in second.all_segments) == expected_tags


def test_sample_message_preserves_empty_positional_elements() -> None:
    """Empty elements should remain at their original X12 positions."""
    payload = SAMPLE_MESSAGE_FIXTURE.read_bytes()

    interchange = parse_x12_interchange(tokenize_x12(payload))
    first_transaction = interchange.groups[0].transactions[0]

    q5 = first_transaction.segments[0]
    n7 = first_transaction.segments[1]

    assert q5.tag == "Q5"
    assert q5.element(1) == b""
    assert q5.element(2) == b"20260728"

    assert n7.tag == "N7"
    assert n7.element(1) == b"ABCD"
    assert n7.element(2) == b"123456"

    assert tuple(n7.element(position) for position in range(3, 11)) == (
        b"",
        b"",
        b"",
        b"",
        b"",
        b"",
        b"",
        b"",
    )

    assert n7.element(11) == b"CH"
    assert n7.element(12) == b"EFGH"
    assert n7.element(15) == b"6804"
    assert n7.element(20) == b"186"


def test_sample_message_preserves_generic_party_values() -> None:
    """Generic party identifiers should remain unchanged."""
    payload = SAMPLE_MESSAGE_FIXTURE.read_bytes()

    interchange = parse_x12_interchange(tokenize_x12(payload))
    first, second = interchange.groups[0].transactions

    first_parties = tuple(
        segment.element(2) for segment in first.segments if segment.tag == "N1"
    )
    second_parties = tuple(
        segment.element(2) for segment in second.segments if segment.tag == "N1"
    )

    assert first_parties == (
        b"SHIPPER001",
        b"CONSIGNEE001",
    )
    assert second_parties == (
        b"SHIPPER001",
        b"CONSIGNEE002",
    )


def test_sample_message_round_trip_structure_is_lossless() -> None:
    """Rejoining parsed segments should reproduce the exact fixture bytes."""
    payload = SAMPLE_MESSAGE_FIXTURE.read_bytes()

    document = tokenize_x12(payload)
    interchange = parse_x12_interchange(document)

    reconstructed = (
        document.separators.segment.join(
            segment.raw for segment in interchange.all_segments
        )
        + document.separators.segment
    )

    assert reconstructed == payload
