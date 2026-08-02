"""
tests/core/test_tokenizer.py

Tests for lossless X12 structural tokenization.
"""

from __future__ import annotations

import pytest

from x12.core.exceptions import (
    X12EnvelopeError,
    X12SegmentError,
    X12TokenizerError,
)
from x12.core.separators import ISA_SEGMENT_LENGTH
from x12.core.tokenizer import tokenize_x12


def build_isa_segment(
    *,
    element: bytes = b"*",
    repetition: bytes = b"^",
    component: bytes = b":",
    terminator: bytes = b"~",
    version: bytes = b"00705",
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
        version,
        b"000000001",
        b"0",
        b"T",
        component,
    )

    isa = b"ISA" + element + element.join(values) + terminator

    assert len(isa) == ISA_SEGMENT_LENGTH
    return isa


def build_document(
    *,
    terminator: bytes = b"~",
) -> bytes:
    """Build a small, structurally complete generic X12 interchange."""
    return b"".join(
        (
            build_isa_segment(terminator=terminator),
            b"GS*XX*SENDER01*RECEIVER01*20260101*1200*1*X*007050" + terminator,
            b"ST*999*0001" + terminator,
            b"N1*SH*SAMPLE-SHIPPER" + terminator,
            b"SE*3*0001" + terminator,
            b"GE*1*1" + terminator,
            b"IEA*1*000000001" + terminator,
        )
    )


def test_tokenize_x12_preserves_exact_raw_payload() -> None:
    """The document should retain the exact original payload object."""
    payload = build_document()

    document = tokenize_x12(payload)

    assert document.raw is payload
    assert document.raw == payload


def test_tokenize_x12_discovers_document_separators() -> None:
    """The tokenizer should expose separators derived from ISA."""
    document = tokenize_x12(build_document())

    assert document.separators.element == b"*"
    assert document.separators.repetition == b"^"
    assert document.separators.component == b":"
    assert document.separators.segment == b"~"


def test_tokenize_x12_preserves_segment_order() -> None:
    """Segments should remain in their original document order."""
    document = tokenize_x12(build_document())

    assert tuple(segment.tag for segment in document.segments) == (
        "ISA",
        "GS",
        "ST",
        "N1",
        "SE",
        "GE",
        "IEA",
    )


def test_tokenize_x12_assigns_contiguous_zero_based_indexes() -> None:
    """Tokenized segments should receive contiguous zero-based indexes."""
    document = tokenize_x12(build_document())

    assert tuple(segment.index for segment in document.segments) == tuple(
        range(len(document.segments))
    )


def test_tokenize_x12_preserves_empty_elements() -> None:
    """Empty data elements should remain present in the token stream."""
    payload = b"".join(
        (
            build_isa_segment(),
            b"GS*XX*SENDER01*RECEIVER01*20260101*1200*1*X*007050~",
            b"ST*999*0001~",
            b"N1*SH**SAMPLE~",
            b"SE*3*0001~",
            b"GE*1*1~",
            b"IEA*1*000000001~",
        )
    )

    document = tokenize_x12(payload)
    segment = document.find_segments("N1")[0]

    assert segment.elements == (
        b"SH",
        b"",
        b"SAMPLE",
    )


def test_tokenize_x12_preserves_trailing_element_whitespace() -> None:
    """Trailing spaces inside segment data should not be stripped."""
    payload = b"".join(
        (
            build_isa_segment(),
            b"GS*XX*SENDER01*RECEIVER01*20260101*1200*1*X*007050~",
            b"ST*999*0001~",
            b"N1*SH*VALUE   ~",
            b"SE*3*0001~",
            b"GE*1*1~",
            b"IEA*1*000000001~",
        )
    )

    document = tokenize_x12(payload)
    segment = document.find_segments("N1")[0]

    assert segment.element(2) == b"VALUE   "
    assert segment.raw == b"N1*SH*VALUE   "


def test_tokenize_x12_ignores_formatting_whitespace_between_segments() -> None:
    """Formatting whitespace after terminators should be ignored."""
    payload = b"\r\n".join(
        (
            build_isa_segment(),
            b"GS*XX*SENDER01*RECEIVER01*20260101*1200*1*X*007050~",
            b"ST*999*0001~",
            b"SE*2*0001~",
            b"GE*1*1~",
            b"IEA*1*000000001~",
        )
    )

    document = tokenize_x12(payload)

    assert tuple(segment.tag for segment in document.segments) == (
        "ISA",
        "GS",
        "ST",
        "SE",
        "GE",
        "IEA",
    )

    assert document.segments[1].raw.startswith(b"GS")
    assert not document.segments[1].raw.startswith(b"\r\n")


@pytest.mark.parametrize(
    "formatting",
    [
        b" ",
        b"\t",
        b"\r",
        b"\n",
        b" \t\r\n",
    ],
)
def test_tokenize_x12_accepts_formatting_after_final_terminator(
    formatting: bytes,
) -> None:
    """Permitted formatting whitespace may follow the final terminator."""
    payload = build_document() + formatting

    document = tokenize_x12(payload)

    assert document.last_segment.tag == "IEA"
    assert document.raw == payload


def test_tokenize_x12_uses_valid_custom_separators() -> None:
    """Tokenization should honor custom separators discovered from ISA."""
    payload = b"".join(
        (
            build_isa_segment(
                element=b"|",
                repetition=b"^",
                component=b">",
                terminator=b"!",
            ),
            b"GS|XX|SENDER01|RECEIVER01|20260101|1200|1|X|007050!",
            b"ST|999|0001!",
            b"SE|2|0001!",
            b"GE|1|1!",
            b"IEA|1|000000001!",
        )
    )

    document = tokenize_x12(payload)

    assert document.separators.element == b"|"
    assert document.separators.repetition == b"^"
    assert document.separators.component == b">"
    assert document.separators.segment == b"!"
    assert document.find_segments("ST")[0].elements == (
        b"999",
        b"0001",
    )


@pytest.mark.parametrize(
    "terminator",
    [
        b"\r",
        b"\n",
    ],
)
def test_tokenize_x12_accepts_line_break_segment_terminators(
    terminator: bytes,
) -> None:
    """A carriage return or line feed may be the active terminator."""
    document = tokenize_x12(build_document(terminator=terminator))

    assert document.separators.segment == terminator
    assert tuple(segment.tag for segment in document.segments) == (
        "ISA",
        "GS",
        "ST",
        "N1",
        "SE",
        "GE",
        "IEA",
    )


def test_tokenize_x12_allows_line_feed_after_carriage_return_terminator() -> None:
    """Line-feed formatting may follow a carriage-return terminator."""
    payload = build_document(terminator=b"\r") + b"\n"

    document = tokenize_x12(payload)

    assert document.separators.segment == b"\r"
    assert document.last_segment.tag == "IEA"


def test_tokenize_x12_finds_repeated_segments() -> None:
    """Repeated tags should remain individually accessible."""
    payload = b"".join(
        (
            build_isa_segment(),
            b"GS*XX*SENDER01*RECEIVER01*20260101*1200*1*X*007050~",
            b"ST*999*0001~",
            b"N1*SH*PARTY-ONE~",
            b"N1*CN*PARTY-TWO~",
            b"SE*4*0001~",
            b"GE*1*1~",
            b"IEA*1*000000001~",
        )
    )

    document = tokenize_x12(payload)

    assert tuple(segment.element(2) for segment in document.find_segments("N1")) == (
        b"PARTY-ONE",
        b"PARTY-TWO",
    )


def test_tokenize_x12_exposes_first_and_last_segments() -> None:
    """The document should expose its outermost segments."""
    document = tokenize_x12(build_document())

    assert document.first_segment.tag == "ISA"
    assert document.last_segment.tag == "IEA"


def test_tokenize_x12_document_supports_iteration_and_length() -> None:
    """Tokenized documents should be iterable and sized."""
    document = tokenize_x12(build_document())

    assert len(document) == 7
    assert tuple(document) == document.segments


def test_tokenize_x12_rejects_empty_payload() -> None:
    """An empty payload should fail before separator discovery."""
    with pytest.raises(
        X12TokenizerError,
        match="cannot be empty",
    ):
        tokenize_x12(b"")


def test_tokenize_x12_rejects_short_isa_payload() -> None:
    """An incomplete ISA should surface an envelope error."""
    with pytest.raises(
        X12EnvelopeError,
        match="too short",
    ):
        tokenize_x12(b"ISA*00")


def test_tokenize_x12_requires_isa_at_first_byte() -> None:
    """The payload must begin directly with ISA."""
    payload = b"NOT" + build_isa_segment()[3:]

    with pytest.raises(
        X12EnvelopeError,
        match="must begin with an ISA",
    ):
        tokenize_x12(payload)


def test_tokenize_x12_rejects_broken_isa_fixed_width_layout() -> None:
    """Every fixed-width ISA separator position should be validated."""
    payload = bytearray(build_document())
    payload[17] = ord("|")

    with pytest.raises(
        X12EnvelopeError,
        match="fixed-width layout",
    ):
        tokenize_x12(bytes(payload))


def test_tokenize_x12_requires_final_segment_terminator() -> None:
    """The payload must end with its ISA-defined terminator."""
    payload = build_document().removesuffix(b"~")

    with pytest.raises(
        X12TokenizerError,
        match="does not end",
    ):
        tokenize_x12(payload)


def test_tokenize_x12_requires_carriage_return_terminator_when_configured() -> None:
    """A carriage-return interchange must end with carriage return."""
    payload = build_document(terminator=b"\r").removesuffix(b"\r")

    with pytest.raises(
        X12TokenizerError,
        match="does not end",
    ):
        tokenize_x12(payload)


def test_tokenize_x12_rejects_empty_segment() -> None:
    """Consecutive terminators should be rejected as an empty segment."""
    payload = build_document().replace(
        b"ST*999*0001~",
        b"ST*999*0001~~",
    )

    with pytest.raises(
        X12TokenizerError,
        match="contains an empty segment",
    ):
        tokenize_x12(payload)


def test_tokenize_x12_rejects_segment_without_identifier() -> None:
    """A segment beginning with an element separator has no identifier."""
    payload = build_document().replace(
        b"N1*SH*SAMPLE-SHIPPER~",
        b"*SH*SAMPLE-SHIPPER~",
    )

    with pytest.raises(
        X12SegmentError,
        match="has no segment identifier",
    ):
        tokenize_x12(payload)


def test_tokenize_x12_rejects_non_ascii_segment_identifier() -> None:
    """Segment identifiers must contain ASCII bytes."""
    payload = build_document().replace(
        b"N1*SH*SAMPLE-SHIPPER~",
        b"\xff1*SH*SAMPLE-SHIPPER~",
    )

    with pytest.raises(
        X12SegmentError,
        match="non-ASCII identifier",
    ):
        tokenize_x12(payload)


@pytest.mark.parametrize(
    "tag",
    [
        b"N-1",
        b"N_1",
        b"N 1",
        b"$N1",
    ],
)
def test_tokenize_x12_rejects_non_alphanumeric_segment_identifier(
    tag: bytes,
) -> None:
    """Segment identifiers must be ASCII alphanumeric."""
    payload = build_document().replace(
        b"N1*SH*SAMPLE-SHIPPER~",
        tag + b"*SH*SAMPLE-SHIPPER~",
    )

    with pytest.raises(
        X12SegmentError,
        match="must be ASCII alphanumeric",
    ):
        tokenize_x12(payload)
