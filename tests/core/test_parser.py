"""
tests/core/test_parser.py

Tests for ANSI X12 interchange envelope parsing and validation.

End-to-end cases pass byte payloads through :func:`tokenize_x12` before
parsing. Low-level document builders are reserved for malformed envelope
orders or element combinations that must be tested independently of ISA
fixed-width tokenization.

Impossible ``X12Document`` states, such as an empty segment collection or
non-contiguous segment indexes, are model concerns covered by
``tests/test_segments.py`` rather than duplicated here.
"""

from __future__ import annotations

import pytest

from x12.core.envelopes import X12Interchange
from x12.core.exceptions import X12EnvelopeError
from x12.core.parser import parse_x12_interchange
from x12.core.segments import X12Document, X12Segment
from x12.core.separators import ISA_SEGMENT_LENGTH, X12Separators
from x12.core.tokenizer import tokenize_x12

INTERCHANGE_CONTROL_NUMBER = b"000000001"
GROUP_CONTROL_NUMBER = b"1"
TRANSACTION_CONTROL_NUMBER = b"0001"
TRANSACTION_SET_CODE = b"999"

ISA_ELEMENTS = (
    b"00",
    b"          ",
    b"00",
    b"          ",
    b"ZZ",
    b"SENDER01       ",
    b"ZZ",
    b"RECEIVER01     ",
    b"260101",
    b"1200",
    b"^",
    b"00705",
    INTERCHANGE_CONTROL_NUMBER,
    b"0",
    b"T",
    b":",
)
GS_ELEMENTS = (
    b"XX",
    b"SENDER01",
    b"RECEIVER01",
    b"20260101",
    b"1200",
    GROUP_CONTROL_NUMBER,
    b"X",
    b"007050",
)
ST_ELEMENTS = (
    TRANSACTION_SET_CODE,
    TRANSACTION_CONTROL_NUMBER,
)
SE_ELEMENTS = (
    b"2",
    TRANSACTION_CONTROL_NUMBER,
)
GE_ELEMENTS = (
    b"1",
    GROUP_CONTROL_NUMBER,
)
IEA_ELEMENTS = (
    b"1",
    INTERCHANGE_CONTROL_NUMBER,
)


def build_isa_segment(
    *,
    control_number: bytes = INTERCHANGE_CONTROL_NUMBER,
) -> bytes:
    """Build one generic, valid, fixed-width ISA segment."""
    values = (
        *ISA_ELEMENTS[:12],
        control_number,
        *ISA_ELEMENTS[13:],
    )
    isa = b"ISA*" + b"*".join(values) + b"~"

    assert len(isa) == ISA_SEGMENT_LENGTH
    return isa


def build_payload(
    *segments: bytes,
    interchange_control_number: bytes = INTERCHANGE_CONTROL_NUMBER,
    trailer_control_number: bytes | None = None,
    declared_group_count: bytes = b"1",
) -> bytes:
    """Build an interchange around caller-provided interior segments."""
    if trailer_control_number is None:
        trailer_control_number = interchange_control_number

    return b"".join(
        (
            build_isa_segment(
                control_number=interchange_control_number,
            ),
            *segments,
            b"IEA*" + declared_group_count + b"*" + trailer_control_number + b"~",
        )
    )


def build_single_transaction_payload() -> bytes:
    """Build one valid group containing one generic transaction set."""
    return build_payload(
        b"GS*XX*SENDER01*RECEIVER01*20260101*1200*1*X*007050~",
        b"ST*999*0001~",
        b"N1*SH*SAMPLE-PARTY~",
        b"DTM*011*20260101*1200~",
        b"SE*4*0001~",
        b"GE*1*1~",
    )


def make_segment(
    index: int,
    tag: str,
    *elements: bytes,
) -> X12Segment:
    """Build one tokenized segment for low-level parser tests."""
    raw = tag.encode("ascii")

    if elements:
        raw += b"*" + b"*".join(elements)

    return X12Segment(
        index=index,
        tag=tag,
        elements=elements,
        raw=raw,
    )


def build_document_from_segments(
    *segments: X12Segment,
) -> X12Document:
    """Build a low-level document without invoking the tokenizer."""
    separators = X12Separators(
        element=b"*",
        repetition=b"^",
        component=b":",
        segment=b"~",
    )

    return X12Document(
        raw=b"~".join(segment.raw for segment in segments) + b"~",
        separators=separators,
        segments=segments,
    )


def valid_isa_segment(
    *,
    index: int = 0,
    control_number: bytes = INTERCHANGE_CONTROL_NUMBER,
) -> X12Segment:
    """Build a structurally valid tokenized ISA segment."""
    elements = (
        *ISA_ELEMENTS[:12],
        control_number,
        *ISA_ELEMENTS[13:],
    )
    return make_segment(index, "ISA", *elements)


def valid_gs_segment(
    *,
    index: int = 1,
    control_number: bytes = GROUP_CONTROL_NUMBER,
) -> X12Segment:
    """Build a structurally valid tokenized GS segment."""
    elements = (
        *GS_ELEMENTS[:5],
        control_number,
        *GS_ELEMENTS[6:],
    )
    return make_segment(index, "GS", *elements)


def minimal_valid_segments() -> list[X12Segment]:
    """Return one minimal valid interchange as independent segments."""
    return [
        valid_isa_segment(index=0),
        valid_gs_segment(index=1),
        make_segment(2, "ST", *ST_ELEMENTS),
        make_segment(3, "SE", *SE_ELEMENTS),
        make_segment(4, "GE", *GE_ELEMENTS),
        make_segment(5, "IEA", *IEA_ELEMENTS),
    ]


def test_parse_single_group_and_transaction() -> None:
    """A complete document should become one nested envelope hierarchy."""
    document = tokenize_x12(build_single_transaction_payload())

    interchange = parse_x12_interchange(document)

    assert isinstance(interchange, X12Interchange)
    assert interchange.document is document
    assert interchange.header.tag == "ISA"
    assert interchange.trailer.tag == "IEA"

    expected_group_count = 1
    assert interchange.actual_group_count == expected_group_count

    group = interchange.groups[0]

    assert group.header.tag == "GS"
    assert group.trailer.tag == "GE"

    expected_transaction_count = 1
    assert group.actual_transaction_count == expected_transaction_count

    transaction = group.transactions[0]

    assert transaction.header.tag == "ST"
    assert transaction.trailer.tag == "SE"
    assert transaction.transaction_set_code == TRANSACTION_SET_CODE
    assert transaction.control_number == TRANSACTION_CONTROL_NUMBER
    assert tuple(segment.tag for segment in transaction.segments) == (
        "N1",
        "DTM",
    )


def test_parse_preserves_original_document() -> None:
    """The parsed interchange should retain the original document object."""
    payload = build_single_transaction_payload()
    document = tokenize_x12(payload)

    interchange = parse_x12_interchange(document)

    assert interchange.document is document
    assert interchange.document.raw is payload
    assert interchange.all_segments == document.segments


def test_parse_multiple_transactions_in_one_group() -> None:
    """A functional group may contain multiple ordered transaction sets."""
    payload = build_payload(
        b"GS*XX*SENDER01*RECEIVER01*20260101*1200*1*X*007050~",
        b"ST*999*0001~",
        b"N1*SH*PARTY-ONE~",
        b"SE*3*0001~",
        b"ST*999*0002~",
        b"N1*CN*PARTY-TWO~",
        b"DTM*011*20260102~",
        b"SE*4*0002~",
        b"GE*2*1~",
    )

    interchange = parse_x12_interchange(tokenize_x12(payload))
    group = interchange.groups[0]

    expected_transaction_count = 2
    assert group.actual_transaction_count == expected_transaction_count
    assert tuple(transaction.control_number for transaction in group.transactions) == (
        b"0001",
        b"0002",
    )
    assert tuple(
        transaction.actual_segment_count for transaction in group.transactions
    ) == (
        3,
        4,
    )


def test_parse_multiple_functional_groups() -> None:
    """An interchange may contain multiple ordered functional groups."""
    payload = build_payload(
        b"GS*XX*SENDER01*RECEIVER01*20260101*1200*1*X*007050~",
        b"ST*999*0001~",
        b"SE*2*0001~",
        b"GE*1*1~",
        b"GS*XX*SENDER01*RECEIVER01*20260101*1201*2*X*007050~",
        b"ST*999*0002~",
        b"N1*SH*PARTY-TWO~",
        b"SE*3*0002~",
        b"GE*1*2~",
        declared_group_count=b"2",
    )

    interchange = parse_x12_interchange(tokenize_x12(payload))

    expected_group_count = 2
    assert interchange.actual_group_count == expected_group_count
    assert tuple(group.control_number for group in interchange.groups) == (
        b"1",
        b"2",
    )
    assert tuple(
        group.transactions[0].control_number for group in interchange.groups
    ) == (
        b"0001",
        b"0002",
    )


def test_parse_rejects_empty_functional_group() -> None:
    """A functional group must contain at least one transaction set."""
    payload = build_payload(
        b"GS*XX*SENDER01*RECEIVER01*20260101*1200*1*X*007050~",
        b"GE*0*1~",
    )

    with pytest.raises(
        X12EnvelopeError,
        match="must contain at least one transaction set",
    ):
        parse_x12_interchange(tokenize_x12(payload))


def test_parse_allows_ta1_only_interchange() -> None:
    """An interchange acknowledgment may appear without a functional group."""
    payload = build_payload(
        b"TA1*000000002*260101*1200*A*000~",
        declared_group_count=b"0",
    )

    interchange = parse_x12_interchange(tokenize_x12(payload))

    assert interchange.groups == ()
    assert interchange.actual_group_count == 0
    assert tuple(segment.tag for segment in interchange.interchange_segments) == (
        "TA1",
    )
    assert interchange.all_segments == interchange.document.segments


def test_parse_allows_multiple_ta1_segments() -> None:
    """An interchange may contain multiple ordered acknowledgments."""
    payload = build_payload(
        b"TA1*000000002*260101*1200*A*000~",
        b"TA1*000000003*260101*1201*R*001~",
        declared_group_count=b"0",
    )

    interchange = parse_x12_interchange(tokenize_x12(payload))

    assert tuple(
        segment.element(1) for segment in interchange.interchange_segments
    ) == (
        b"000000002",
        b"000000003",
    )


def test_parse_allows_ta1_before_functional_group() -> None:
    """A TA1 acknowledgment may precede functional groups in one interchange."""
    payload = build_payload(
        b"TA1*000000002*260101*1200*A*000~",
        b"GS*XX*SENDER01*RECEIVER01*20260101*1200*1*X*007050~",
        b"ST*999*0001~",
        b"SE*2*0001~",
        b"GE*1*1~",
    )

    interchange = parse_x12_interchange(tokenize_x12(payload))

    assert len(interchange.interchange_segments) == 1
    assert interchange.actual_group_count == 1


def test_parse_rejects_empty_interchange() -> None:
    """An interchange needs at least one TA1 acknowledgment or group."""
    payload = build_payload(declared_group_count=b"0")

    with pytest.raises(
        X12EnvelopeError,
        match=(
            "X12 interchange must contain at least one TA1 interchange "
            "acknowledgment or functional group"
        ),
    ):
        parse_x12_interchange(tokenize_x12(payload))


def test_parse_requires_isa_as_first_segment() -> None:
    """The first segment must be ISA."""
    document = build_document_from_segments(
        valid_gs_segment(index=0),
        make_segment(1, "IEA", b"0", INTERCHANGE_CONTROL_NUMBER),
    )

    with pytest.raises(
        X12EnvelopeError,
        match="X12 interchange must begin with an ISA segment",
    ):
        parse_x12_interchange(document)


def test_parse_requires_iea_as_last_segment() -> None:
    """The final segment must be IEA."""
    document = build_document_from_segments(
        valid_isa_segment(index=0),
        valid_gs_segment(index=1),
    )

    with pytest.raises(
        X12EnvelopeError,
        match="X12 interchange must end with an IEA segment",
    ):
        parse_x12_interchange(document)


def test_parse_rejects_unexpected_segment_between_isa_and_group() -> None:
    """An unrelated segment cannot appear at interchange scope."""
    document = build_document_from_segments(
        valid_isa_segment(index=0),
        make_segment(1, "N1", b"SH", b"SAMPLE-PARTY"),
        make_segment(2, "IEA", b"0", INTERCHANGE_CONTROL_NUMBER),
    )

    with pytest.raises(
        X12EnvelopeError,
        match="Expected GS or IEA at segment index 1, found 'N1'",
    ):
        parse_x12_interchange(document)


def test_parse_rejects_segment_after_early_iea() -> None:
    """No segment may appear after the IEA selected as the trailer."""
    document = build_document_from_segments(
        valid_isa_segment(index=0),
        make_segment(1, "IEA", b"0", INTERCHANGE_CONTROL_NUMBER),
        make_segment(2, "N1", b"SH", b"SAMPLE-PARTY"),
        make_segment(3, "IEA", b"0", INTERCHANGE_CONTROL_NUMBER),
    )

    with pytest.raises(
        X12EnvelopeError,
        match="Unexpected segment 'N1' appears after IEA at segment index 2",
    ):
        parse_x12_interchange(document)


def test_parse_rejects_ta1_after_functional_group() -> None:
    """TA1 acknowledgments must precede any functional groups."""
    document = build_document_from_segments(
        valid_isa_segment(index=0),
        valid_gs_segment(index=1),
        make_segment(2, "ST", *ST_ELEMENTS),
        make_segment(3, "SE", *SE_ELEMENTS),
        make_segment(4, "GE", *GE_ELEMENTS),
        make_segment(5, "TA1", b"000000002", b"260101", b"1200", b"A", b"000"),
        make_segment(6, "IEA", *IEA_ELEMENTS),
    )

    with pytest.raises(
        X12EnvelopeError,
        match="Expected GS or IEA at segment index 5, found 'TA1'",
    ):
        parse_x12_interchange(document)


def test_parse_rejects_unexpected_segment_inside_group() -> None:
    """Only ST or GE may appear at functional-group scope."""
    document = build_document_from_segments(
        valid_isa_segment(index=0),
        valid_gs_segment(index=1),
        make_segment(2, "N1", b"SH", b"SAMPLE-PARTY"),
        make_segment(3, "GE", b"0", GROUP_CONTROL_NUMBER),
        make_segment(4, "IEA", b"1", INTERCHANGE_CONTROL_NUMBER),
    )

    with pytest.raises(
        X12EnvelopeError,
        match=(
            "Expected ST or GE inside functional group at segment index 2, found 'N1'"
        ),
    ):
        parse_x12_interchange(document)


def test_parse_rejects_functional_group_without_ge() -> None:
    """An IEA encountered at group scope cannot substitute for GE."""
    document = build_document_from_segments(
        valid_isa_segment(index=0),
        valid_gs_segment(index=1),
        make_segment(2, "ST", *ST_ELEMENTS),
        make_segment(3, "SE", *SE_ELEMENTS),
        make_segment(4, "IEA", b"1", INTERCHANGE_CONTROL_NUMBER),
    )

    with pytest.raises(
        X12EnvelopeError,
        match=(
            "Expected ST or GE inside functional group at segment index 4, found 'IEA'"
        ),
    ):
        parse_x12_interchange(document)


@pytest.mark.parametrize(
    "nested_tag",
    [
        "ISA",
        "TA1",
        "GS",
        "ST",
        "GE",
        "IEA",
    ],
)
def test_parse_rejects_envelope_segment_inside_transaction(
    nested_tag: str,
) -> None:
    """Envelope boundary tags cannot occur inside a transaction body."""
    document = build_document_from_segments(
        valid_isa_segment(index=0),
        valid_gs_segment(index=1),
        make_segment(2, "ST", *ST_ELEMENTS),
        make_segment(3, nested_tag),
        make_segment(4, "SE", b"3", TRANSACTION_CONTROL_NUMBER),
        make_segment(5, "GE", b"1", GROUP_CONTROL_NUMBER),
        make_segment(6, "IEA", b"1", INTERCHANGE_CONTROL_NUMBER),
    )

    with pytest.raises(
        X12EnvelopeError,
        match=f"Unexpected envelope segment '{nested_tag}' inside",
    ):
        parse_x12_interchange(document)


def test_parse_rejects_transaction_without_se() -> None:
    """A GE encountered in a transaction body cannot substitute for SE."""
    document = build_document_from_segments(
        valid_isa_segment(index=0),
        valid_gs_segment(index=1),
        make_segment(2, "ST", *ST_ELEMENTS),
        make_segment(3, "N1", b"SH", b"SAMPLE-PARTY"),
        make_segment(4, "GE", b"1", GROUP_CONTROL_NUMBER),
        make_segment(5, "IEA", b"1", INTERCHANGE_CONTROL_NUMBER),
    )

    with pytest.raises(
        X12EnvelopeError,
        match="Unexpected envelope segment 'GE' inside transaction set",
    ):
        parse_x12_interchange(document)


def test_parse_rejects_body_segment_after_completed_transaction() -> None:
    """A body segment cannot appear between a completed transaction and GE."""
    document = build_document_from_segments(
        valid_isa_segment(index=0),
        valid_gs_segment(index=1),
        make_segment(2, "ST", *ST_ELEMENTS),
        make_segment(3, "SE", *SE_ELEMENTS),
        make_segment(4, "N1", b"SH", b"SAMPLE-PARTY"),
        make_segment(5, "GE", b"1", GROUP_CONTROL_NUMBER),
        make_segment(6, "IEA", b"1", INTERCHANGE_CONTROL_NUMBER),
    )

    with pytest.raises(
        X12EnvelopeError,
        match=(
            "Expected ST or GE inside functional group at segment index 4, found 'N1'"
        ),
    ):
        parse_x12_interchange(document)


@pytest.mark.parametrize(
    ("tag", "elements", "expected_count"),
    [
        ("ISA", ISA_ELEMENTS[:-1], 16),
        ("ISA", (*ISA_ELEMENTS, b"EXTRA"), 16),
        ("GS", GS_ELEMENTS[:-1], 8),
        ("GS", (*GS_ELEMENTS, b"EXTRA"), 8),
        ("SE", SE_ELEMENTS[:-1], 2),
        ("SE", (*SE_ELEMENTS, b"EXTRA"), 2),
        ("GE", GE_ELEMENTS[:-1], 2),
        ("GE", (*GE_ELEMENTS, b"EXTRA"), 2),
        ("IEA", IEA_ELEMENTS[:-1], 2),
        ("IEA", (*IEA_ELEMENTS, b"EXTRA"), 2),
    ],
)
def test_parse_requires_exact_envelope_element_counts(
    tag: str,
    elements: tuple[bytes, ...],
    expected_count: int,
) -> None:
    """Every envelope segment should have its required element count."""
    segments = minimal_valid_segments()
    target_index = {
        "ISA": 0,
        "GS": 1,
        "ST": 2,
        "SE": 3,
        "GE": 4,
        "IEA": 5,
    }[tag]
    segments[target_index] = make_segment(
        target_index,
        tag,
        *elements,
    )
    document = build_document_from_segments(*segments)

    with pytest.raises(
        X12EnvelopeError,
        match=(
            f"{tag} segment at index {target_index} must contain exactly "
            f"{expected_count} elements"
        ),
    ):
        parse_x12_interchange(document)


def test_parse_requires_at_least_two_st_elements() -> None:
    """ST01 and ST02 are required while later ST elements are optional."""
    segments = minimal_valid_segments()
    segments[2] = make_segment(2, "ST", TRANSACTION_SET_CODE)
    document = build_document_from_segments(*segments)

    with pytest.raises(
        X12EnvelopeError,
        match="ST segment at index 2 must contain at least 2 elements; found 1",
    ):
        parse_x12_interchange(document)


def test_parse_preserves_optional_st_references() -> None:
    """ST03 and ST04 should be preserved as generic structural values."""
    payload = build_payload(
        b"GS*XX*SENDER01*RECEIVER01*20260101*1200*1*X*007050~",
        b"ST*999*0001*005010X231A1*008010~",
        b"SE*2*0001~",
        b"GE*1*1~",
    )

    transaction = parse_x12_interchange(tokenize_x12(payload)).groups[0].transactions[0]

    assert transaction.implementation_convention_reference == b"005010X231A1"
    assert transaction.overriding_version_release_reference == b"008010"


def test_parse_requires_st01() -> None:
    """ST01 must contain a transaction-set code."""
    payload = build_payload(
        b"GS*XX*SENDER01*RECEIVER01*20260101*1200*1*X*007050~",
        b"ST**0001~",
        b"SE*2*0001~",
        b"GE*1*1~",
    )

    with pytest.raises(
        X12EnvelopeError,
        match="ST01 is required in ST segment",
    ):
        parse_x12_interchange(tokenize_x12(payload))


def test_parse_requires_st02() -> None:
    """ST02 must contain a transaction-set control number."""
    payload = build_payload(
        b"GS*XX*SENDER01*RECEIVER01*20260101*1200*1*X*007050~",
        b"ST*999*~",
        b"SE*2*0001~",
        b"GE*1*1~",
    )

    with pytest.raises(
        X12EnvelopeError,
        match="ST02 is required in ST segment",
    ):
        parse_x12_interchange(tokenize_x12(payload))


def test_parse_requires_se02() -> None:
    """SE02 must contain a transaction-set control number."""
    payload = build_payload(
        b"GS*XX*SENDER01*RECEIVER01*20260101*1200*1*X*007050~",
        b"ST*999*0001~",
        b"SE*2*~",
        b"GE*1*1~",
    )

    with pytest.raises(
        X12EnvelopeError,
        match="SE02 is required in SE segment",
    ):
        parse_x12_interchange(tokenize_x12(payload))


def test_parse_rejects_mismatched_transaction_control_numbers() -> None:
    """ST02 and SE02 must match exactly."""
    payload = build_payload(
        b"GS*XX*SENDER01*RECEIVER01*20260101*1200*1*X*007050~",
        b"ST*999*0001~",
        b"SE*2*9999~",
        b"GE*1*1~",
    )

    with pytest.raises(
        X12EnvelopeError,
        match=("ST02 and SE02 transaction-set control numbers do not match"),
    ):
        parse_x12_interchange(tokenize_x12(payload))


def test_transaction_control_number_error_includes_both_values() -> None:
    """A transaction control mismatch should report both raw values."""
    payload = build_payload(
        b"GS*XX*SENDER01*RECEIVER01*20260101*1200*1*X*007050~",
        b"ST*999*0001~",
        b"SE*2*9999~",
        b"GE*1*1~",
    )

    with pytest.raises(
        X12EnvelopeError,
        match="transaction-set control numbers do not match",
    ) as exc_info:
        parse_x12_interchange(tokenize_x12(payload))

    message = str(exc_info.value)
    assert "b'0001'" in message
    assert "b'9999'" in message


@pytest.mark.parametrize(
    "declared_count",
    [
        b"",
        b"ABC",
        b"-1",
        b"+2",
        b"2.0",
        b" 2",
        b"2 ",
    ],
)
def test_parse_requires_numeric_se01(
    declared_count: bytes,
) -> None:
    """SE01 must contain a required ASCII decimal value."""
    payload = build_payload(
        b"GS*XX*SENDER01*RECEIVER01*20260101*1200*1*X*007050~",
        b"ST*999*0001~",
        b"SE*" + declared_count + b"*0001~",
        b"GE*1*1~",
    )
    expected = (
        "SE01 is required"
        if declared_count == b""
        else "SE01 must contain only ASCII digits"
    )

    with pytest.raises(X12EnvelopeError, match=expected):
        parse_x12_interchange(tokenize_x12(payload))


def test_parse_requires_positive_se01() -> None:
    """SE01 must be greater than zero."""
    payload = build_payload(
        b"GS*XX*SENDER01*RECEIVER01*20260101*1200*1*X*007050~",
        b"ST*999*0001~",
        b"SE*0*0001~",
        b"GE*1*1~",
    )

    with pytest.raises(
        X12EnvelopeError,
        match="SE01 must be greater than zero; found 0",
    ):
        parse_x12_interchange(tokenize_x12(payload))


@pytest.mark.parametrize(
    ("body_segments", "declared_count", "actual_count"),
    [
        ((), b"3", 2),
        ((b"N1*SH*SAMPLE-PARTY~",), b"2", 3),
        (
            (
                b"N1*SH*SAMPLE-PARTY~",
                b"DTM*011*20260101~",
            ),
            b"3",
            4,
        ),
    ],
)
def test_parse_rejects_incorrect_transaction_segment_count(
    body_segments: tuple[bytes, ...],
    declared_count: bytes,
    actual_count: int,
) -> None:
    """SE01 must equal the observed ST-through-SE segment count."""
    payload = build_payload(
        b"GS*XX*SENDER01*RECEIVER01*20260101*1200*1*X*007050~",
        b"ST*999*0001~",
        *body_segments,
        b"SE*" + declared_count + b"*0001~",
        b"GE*1*1~",
    )

    with pytest.raises(
        X12EnvelopeError,
        match="SE01 transaction segment count does not match",
    ) as exc_info:
        parse_x12_interchange(tokenize_x12(payload))

    message = str(exc_info.value)
    assert f"declared {int(declared_count)}" in message
    assert f"actual {actual_count}" in message


def test_parse_requires_gs06() -> None:
    """GS06 must contain a functional-group control number."""
    payload = build_payload(
        b"GS*XX*SENDER01*RECEIVER01*20260101*1200**X*007050~",
        b"GE*0*1~",
    )

    with pytest.raises(
        X12EnvelopeError,
        match="GS06 is required in GS segment",
    ):
        parse_x12_interchange(tokenize_x12(payload))


def test_parse_requires_ge02() -> None:
    """GE02 must contain a functional-group control number."""
    payload = build_payload(
        b"GS*XX*SENDER01*RECEIVER01*20260101*1200*1*X*007050~",
        b"GE*0*~",
    )

    with pytest.raises(
        X12EnvelopeError,
        match="GE02 is required in GE segment",
    ):
        parse_x12_interchange(tokenize_x12(payload))


def test_parse_rejects_mismatched_group_control_numbers() -> None:
    """GS06 and GE02 must match exactly."""
    payload = build_payload(
        b"GS*XX*SENDER01*RECEIVER01*20260101*1200*1*X*007050~",
        b"GE*0*999~",
    )

    with pytest.raises(
        X12EnvelopeError,
        match=("GS06 and GE02 functional-group control numbers do not match"),
    ):
        parse_x12_interchange(tokenize_x12(payload))


def test_group_control_number_error_includes_both_values() -> None:
    """A group control mismatch should report both raw values."""
    payload = build_payload(
        b"GS*XX*SENDER01*RECEIVER01*20260101*1200*1*X*007050~",
        b"GE*0*999~",
    )

    with pytest.raises(
        X12EnvelopeError,
        match="functional-group control numbers do not match",
    ) as exc_info:
        parse_x12_interchange(tokenize_x12(payload))

    message = str(exc_info.value)
    assert "b'1'" in message
    assert "b'999'" in message


@pytest.mark.parametrize(
    "declared_count",
    [
        b"",
        b"ABC",
        b"-1",
        b"+1",
        b"1.0",
        b" 1",
        b"1 ",
    ],
)
def test_parse_requires_nonnegative_numeric_ge01(
    declared_count: bytes,
) -> None:
    """GE01 must contain a required non-negative ASCII integer."""
    payload = build_payload(
        b"GS*XX*SENDER01*RECEIVER01*20260101*1200*1*X*007050~",
        b"GE*" + declared_count + b"*1~",
    )
    expected = (
        "GE01 is required"
        if declared_count == b""
        else "GE01 must contain only ASCII digits"
    )

    with pytest.raises(X12EnvelopeError, match=expected):
        parse_x12_interchange(tokenize_x12(payload))


def test_parse_rejects_incorrect_transaction_count_in_group() -> None:
    """GE01 must equal the number of parsed transaction sets."""
    payload = build_payload(
        b"GS*XX*SENDER01*RECEIVER01*20260101*1200*1*X*007050~",
        b"ST*999*0001~",
        b"SE*2*0001~",
        b"GE*2*1~",
    )

    with pytest.raises(
        X12EnvelopeError,
        match="GE01 transaction-set count does not match",
    ) as exc_info:
        parse_x12_interchange(tokenize_x12(payload))

    message = str(exc_info.value)
    assert "declared 2" in message
    assert "actual 1" in message


def test_parse_requires_isa13() -> None:
    """ISA13 must contain an interchange control number."""
    document = build_document_from_segments(
        valid_isa_segment(
            index=0,
            control_number=b"",
        ),
        make_segment(1, "IEA", b"0", INTERCHANGE_CONTROL_NUMBER),
    )

    with pytest.raises(
        X12EnvelopeError,
        match="ISA13 is required in ISA segment",
    ):
        parse_x12_interchange(document)


def test_parse_requires_iea02() -> None:
    """IEA02 must contain an interchange control number."""
    document = build_document_from_segments(
        valid_isa_segment(index=0),
        make_segment(1, "IEA", b"0", b""),
    )

    with pytest.raises(
        X12EnvelopeError,
        match="IEA02 is required in IEA segment",
    ):
        parse_x12_interchange(document)


def test_parse_rejects_mismatched_interchange_control_numbers() -> None:
    """ISA13 and IEA02 must match exactly."""
    document = build_document_from_segments(
        valid_isa_segment(
            index=0,
            control_number=INTERCHANGE_CONTROL_NUMBER,
        ),
        make_segment(1, "IEA", b"0", b"000000999"),
    )

    with pytest.raises(
        X12EnvelopeError,
        match=("ISA13 and IEA02 interchange control numbers do not match"),
    ):
        parse_x12_interchange(document)


def test_interchange_control_number_error_includes_both_values() -> None:
    """An interchange control mismatch should report both raw values."""
    document = build_document_from_segments(
        valid_isa_segment(
            index=0,
            control_number=INTERCHANGE_CONTROL_NUMBER,
        ),
        make_segment(1, "IEA", b"0", b"000000999"),
    )

    with pytest.raises(
        X12EnvelopeError,
        match="interchange control numbers do not match",
    ) as exc_info:
        parse_x12_interchange(document)

    message = str(exc_info.value)
    assert "b'000000001'" in message
    assert "b'000000999'" in message


@pytest.mark.parametrize(
    "declared_count",
    [
        b"",
        b"ABC",
        b"-1",
        b"+1",
        b"1.0",
        b" 1",
        b"1 ",
    ],
)
def test_parse_requires_nonnegative_numeric_iea01(
    declared_count: bytes,
) -> None:
    """IEA01 must contain a required non-negative ASCII integer."""
    document = build_document_from_segments(
        valid_isa_segment(index=0),
        make_segment(
            1,
            "IEA",
            declared_count,
            INTERCHANGE_CONTROL_NUMBER,
        ),
    )
    expected = (
        "IEA01 is required"
        if declared_count == b""
        else "IEA01 must contain only ASCII digits"
    )

    with pytest.raises(X12EnvelopeError, match=expected):
        parse_x12_interchange(document)


def test_parse_rejects_incorrect_functional_group_count() -> None:
    """IEA01 must equal the number of parsed functional groups."""
    payload = build_payload(
        b"GS*XX*SENDER01*RECEIVER01*20260101*1200*1*X*007050~",
        b"ST*999*0001~",
        b"SE*2*0001~",
        b"GE*1*1~",
        declared_group_count=b"2",
    )

    with pytest.raises(
        X12EnvelopeError,
        match="IEA01 functional-group count does not match",
    ) as exc_info:
        parse_x12_interchange(tokenize_x12(payload))

    message = str(exc_info.value)
    assert "declared 2" in message
    assert "actual 1" in message


def test_parser_returns_new_interchange_each_time() -> None:
    """Repeated parsing should return equal, independent envelopes."""
    document = tokenize_x12(build_single_transaction_payload())

    first = parse_x12_interchange(document)
    second = parse_x12_interchange(document)

    assert first == second
    assert first is not second


def test_parser_does_not_mutate_document() -> None:
    """Parsing should not replace or alter document data."""
    document = tokenize_x12(build_single_transaction_payload())
    original_segments = document.segments
    original_raw = document.raw

    parse_x12_interchange(document)

    assert document.segments is original_segments
    assert document.raw is original_raw
