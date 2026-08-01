"""
src/x12/tokenizer.py

Lossless structural tokenization for ANSI X12 interchange documents.
"""

from __future__ import annotations

from .exceptions import X12SegmentError, X12TokenizerError
from .segments import X12Document, X12Segment
from .separators import derive_x12_separators

INTER_SEGMENT_WHITESPACE = b" \t\r\n"


def tokenize_x12(payload: bytes) -> X12Document:
    """Tokenize a complete ANSI X12 interchange document.

    This function performs structural tokenization only. It identifies
    segments and data elements without interpreting transaction-set semantics
    or business values.

    Whitespace placed between segment terminators and the following segment is
    ignored. Whitespace within segment data is preserved.

    Args:
        payload: Complete X12 interchange encoded as bytes.

    Returns:
        A document containing the original payload, discovered separators,
        and tokenized segments.

    Raises:
        X12TokenizerError: If the payload is empty, lacks a final segment
            terminator, or contains an empty segment.
        X12SegmentError: If an individual segment has an invalid identifier.
        X12EnvelopeError: If the ISA interchange header is malformed.
        X12SeparatorError: If separators derived from ISA are invalid.
    """
    if not payload:
        msg = "X12 payload cannot be empty."
        raise X12TokenizerError(msg)

    separators = derive_x12_separators(payload)
    formatting_whitespace = _formatting_whitespace(separators.segment)

    if not payload.rstrip(formatting_whitespace).endswith(separators.segment):
        msg = "X12 payload does not end with its ISA-defined segment terminator."
        raise X12TokenizerError(msg)

    raw_segments = payload.split(separators.segment)
    segments: list[X12Segment] = []

    # The final item contains only permitted formatting whitespace because
    # the final-terminator check above has already validated the payload.
    raw_segments.pop()

    for raw_segment in raw_segments:
        # Formatting whitespace appears after a segment terminator and
        # therefore at the beginning of the next split item. Use lstrip
        # rather than strip so trailing element data remains lossless.
        normalized = raw_segment.lstrip(formatting_whitespace)

        if not normalized:
            msg = f"X12 payload contains an empty segment at index {len(segments)}."
            raise X12TokenizerError(msg)

        segments.append(
            _tokenize_segment(
                raw=normalized,
                index=len(segments),
                element_separator=separators.element,
            )
        )

    return X12Document(
        raw=payload,
        separators=separators,
        segments=tuple(segments),
    )


def _formatting_whitespace(segment_terminator: bytes) -> bytes:
    """Return ignorable whitespace that excludes the active terminator."""
    return bytes(
        character
        for character in INTER_SEGMENT_WHITESPACE
        if bytes((character,)) != segment_terminator
    )


def _tokenize_segment(
    *,
    raw: bytes,
    index: int,
    element_separator: bytes,
) -> X12Segment:
    """Tokenize one segment without interpreting its business meaning."""
    parts = raw.split(element_separator)
    raw_tag = parts[0]

    if not raw_tag:
        msg = f"X12 segment at index {index} has no segment identifier."
        raise X12SegmentError(msg)

    try:
        tag = raw_tag.decode("ascii")
    except UnicodeDecodeError as exc:
        msg = f"X12 segment at index {index} has a non-ASCII identifier."
        raise X12SegmentError(msg) from exc

    if not tag.isalnum():
        msg = (
            f"X12 segment identifier {tag!r} at index {index} "
            "must be ASCII alphanumeric."
        )
        raise X12SegmentError(msg)

    return X12Segment(
        index=index,
        tag=tag,
        elements=tuple(parts[1:]),
        raw=raw,
    )


__all__ = ["tokenize_x12"]
