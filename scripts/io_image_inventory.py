"""Pure image inventory extracted from Information OS; see acceptance evidence."""

from __future__ import annotations

import dataclasses

import html as html_module

import re

from dataclasses import dataclass

from typing import Any, Sequence

IMAGE_ATTRIBUTE_PRIORITY = ("data-viewer-src", "src", "data-src", "data-lazy-src")

_HTML_TAG_RE = re.compile(r"<\s*([A-Za-z][A-Za-z0-9-]*)")

_REFERENCE_DEFINITION_RE = re.compile(r"^ {0,3}\[([^\]]+)\]:[ \t]*(.*)$")

_MARKDOWN_UNESCAPE_RE = re.compile(r"\\([\\`*_{}\[\]()#+\-.!<>])")

class LiteratureImagesError(ValueError):
    pass

@dataclass(frozen=True)
class Span:
    start: int
    end: int

    def slice(self, text: str) -> str:
        return text[self.start:self.end]

@dataclass(frozen=True)
class SrcsetCandidate:
    url: str
    descriptor: str
    span: Span

@dataclass(frozen=True)
class ReferenceDefinition:
    label: str
    target: str
    target_span: Span
    span: Span

@dataclass(frozen=True)
class ReviewRecord:
    kind: str
    reason: str
    span: Span | None = None
    detail: str = ""

@dataclass(frozen=True)
class ImageOccurrence:
    """One image reference token with exact byte spans in the source document."""

    index: int
    kind: str                 # markdown | reference | obsidian_embed | html_img | html_source | html_srcset
    start: int
    end: int
    raw: str
    target: str
    alt: str | None = None
    title: str | None = None
    label: str | None = None
    attribute: str = "src"
    target_span: Span | None = None
    definition_span: Span | None = None
    srcset_descriptor: str | None = None

@dataclass(frozen=True)
class ImageInventory:
    occurrences: tuple[ImageOccurrence, ...]
    reference_definitions: tuple[ReferenceDefinition, ...]
    review: tuple[ReviewRecord, ...]

    def targets(self) -> list[str]:
        return [occurrence.target for occurrence in self.occurrences]

def _line_spans(text: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    start = 0
    for index, char in enumerate(text):
        if char == "\n":
            spans.append((start, index))
            start = index + 1
    spans.append((start, len(text)))
    return spans

def _mask_range(chars: list[str], start: int, end: int) -> None:
    for position in range(start, end):
        if chars[position] != "\n":
            chars[position] = "\x00"

def _is_escaped(text: str, index: int) -> bool:
    backslashes = 0
    position = index - 1
    while position >= 0 and text[position] == "\\":
        backslashes += 1
        position -= 1
    return backslashes % 2 == 1

def _comment_end(text: str, index: int, review: list[ReviewRecord] | None = None) -> int:
    """Recognize bounded comment endings; ambiguous browser-visible boundaries hold."""
    start = index + 4
    if text.startswith(">", start) or text.startswith("->", start):
        end = start + (1 if text[start] == ">" else 2)
        ambiguous = True
    else:
        closing = re.compile(r"--!?>").search(text, start)
        end = closing.end() if closing else len(text)
        ambiguous = closing is not None and closing.group() != "-->"
    if ambiguous and review is not None:
        review.append(ReviewRecord(
            "ambiguous_html_comment", "unsupported HTML comment boundary", Span(index, end)))
    return end

def _inline_code_end(text: str, index: int, limit: int) -> int | None:
    """Match an inline backtick run before a paragraph boundary, preserving offsets."""
    run_end = index
    while run_end < limit and text[run_end] == "`":
        run_end += 1
    scan = run_end
    while scan < limit:
        if text[scan:scan + 2] == "\n\n":
            return None
        if text[scan] == "`":
            close_end = scan
            while close_end < limit and text[close_end] == "`":
                close_end += 1
            if close_end - scan == run_end - index:
                return close_end
            scan = close_end
        else:
            scan += 1
    return None

def _html_literal_end(text: str, start: int, name: str,
                      review: list[ReviewRecord] | None, *,
                      inline_ranges: Sequence[tuple[int, int]] = ()) -> int:
    """Find a literal boundary without mistaking raw-text contents for nodes."""
    rawtext = {"script", "style", "textarea", "title"}
    closer = re.compile(r"</" + name + r"(?=[\s/>])", re.I)
    if name in rawtext:
        closing = closer.search(text, start)
        return _skip_tag(text, closing.start()) if closing else len(text)
    tag_opener = re.compile(r"<(/?)([A-Za-z][A-Za-z0-9:_-]*)(?=[\s/>])")
    resources = {"img", "object", "embed", "canvas", "svg", "math", "picture", "source"}
    depth, index = 1, start
    marker = re.compile(r"[<`]") if inline_ranges else re.compile("<")
    while index < len(text):
        opening = marker.search(text, index)
        if opening is None:
            break
        index = opening.start()
        limit = next((end for begin, end in inline_ranges if begin <= index < end), None)
        if limit is not None and _is_escaped(text, index):
            index += 1
            continue
        if text[index] == "`":
            code_end = _inline_code_end(text, index, limit) if limit is not None else None
            index = code_end if code_end is not None else index + 1
            continue
        if text.startswith("<!--", index):
            index = _comment_end(text, index, review)
            continue
        tag = tag_opener.match(text, index)
        if tag is None:
            index += 1
            continue
        end = _skip_tag(text, index)
        child = tag[2].lower()
        if not tag[1] and child in rawtext:
            index = _html_literal_end(text, end, child, None)
            continue
        if child == name:
            depth += -1 if tag[1] else 1
            if depth == 0:
                return end
        if not tag[1] and child in resources and review is not None:
            review.append(ReviewRecord(
                "resource_in_html_literal", "raw HTML resource cannot be hidden as literal code",
                Span(index, end), child))
        index = end
    return len(text)

def _inline_literal_image_reviews(tokens, starts: list[int], size: int) -> list[ReviewRecord]:
    """Require review only for actual CommonMark image tokens in inline HTML literals."""
    review: list[ReviewRecord] = []
    literals: list[str] = []
    rawtext: str | None = None
    tag = re.compile(r"<(/?)(pre|code|script|style|textarea|title)(?=[\s/>])", re.I)

    def visit(children) -> bool:
        nonlocal rawtext
        found = False
        for child in children:
            if child.type == "html_inline":
                match = tag.match(child.content)
                if match:
                    name = match[2].lower()
                    if rawtext:
                        if match[1] and name == rawtext:
                            rawtext = None
                    elif name in {"script", "style", "textarea", "title"}:
                        if not match[1]:
                            rawtext = name
                    elif match[1]:
                        if name in literals:
                            while literals.pop() != name:
                                pass
                    else:
                        literals.append(name)
            elif child.type == "image":
                # Image alt children are rendered as text, not HTML context openers.
                found |= bool(literals and rawtext is None)
            elif child.children and child.type != "code_inline":
                found |= visit(child.children)
        return found

    for token in tokens:
        if token.type == "inline" and token.children and visit(token.children):
            first, last = token.map
            review.append(ReviewRecord(
                "markdown_image_in_html_literal", "CommonMark image inside raw HTML code/pre requires review",
                Span(starts[first], starts[last] if last < len(starts) else size)))
    return review

def _mask_code(text: str, *, review: list[ReviewRecord] | None = None) -> str:
    """Mask CommonMark code and HTML literal elements with exact source offsets.

    Block token line maps account for list/quote containers and indentation. A
    literal scanner then protects inline code and HTML pre/code in source order.
    Actual resource children of pre/code require review before they are masked;
    these wrappers do not turn HTML nodes into text.
    """
    try:
        from ._snapshot_vendor.markdown_it import MarkdownIt
    except ImportError:
        from _snapshot_vendor.markdown_it import MarkdownIt
    chars = list(text)
    starts = [0] + [match.end() for match in re.finditer(r"\r\n|\r|\n", text)]
    tokens = MarkdownIt("commonmark").parse(text)
    if review is not None:
        review.extend(_inline_literal_image_reviews(tokens, starts, len(text)))
    for token in tokens:
        if token.type in {"fence", "code_block"} and token.map:
            first, last = token.map
            start = starts[first] if first < len(starts) else len(text)
            end = starts[last] if last < len(starts) else len(text)
            _mask_range(chars, start, end)
    block_masked = "".join(chars)
    inline_ranges = [(starts[token.map[0]], starts[token.map[1]] if token.map[1] < len(starts) else len(text))
                     for token in tokens if token.type == "inline" and token.map]

    literal_opener = re.compile(r"<(pre|code|script|style|textarea|title)(?=[\s/>])", re.I)
    tag_opener = re.compile(r"</?[A-Za-z][A-Za-z0-9:_-]*(?=[\s/>])|<![A-Za-z]|<\?")
    size = len(chars)
    index = 0
    while index < size:
        if chars[index] == "<" and not _is_escaped(text, index):
            if text.startswith("<!--", index):
                end = _comment_end(block_masked, index, review)
                _mask_range(chars, index, end)
                index = end
                continue
            opening = literal_opener.match(text, index)
            if opening:
                name = opening.group(1).lower()
                literal_end = _html_literal_end(
                    block_masked, _skip_tag(text, index), name, review,
                    inline_ranges=inline_ranges)
                _mask_range(chars, index, literal_end)
                index = literal_end
                continue
            if tag_opener.match(text, index):
                # Ignore attribute values while locating literal/code openers.
                index = _skip_tag(text, index)
                continue
        if chars[index] != "`" or _is_escaped(text, index):
            index += 1
            continue
        limit = next((end for begin, end in inline_ranges if begin <= index < end), None)
        end = _inline_code_end(block_masked, index, limit) if limit is not None else None
        if end is None:
            index += 1
            while index < size and chars[index] == "`":
                index += 1
            continue
        _mask_range(chars, index, end)
        index = end
    return "".join(chars)

def _find_matching_bracket(masked: str, start: int) -> int:
    depth = 1
    index = start
    size = len(masked)
    while index < size:
        char = masked[index]
        if char == "\\":
            index += 2
            continue
        if char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
            if depth == 0:
                return index
        index += 1
    return -1

def _unescape_markdown(value: str) -> str:
    return _MARKDOWN_UNESCAPE_RE.sub(r"\1", value)

def _parse_destination_and_title(
    inner: str, base: int
) -> tuple[str, Span, str | None] | None:
    """Parse ``<dest> "title"``-style content and return absolute spans."""
    size = len(inner)
    index = 0
    while index < size and inner[index] in " \t":
        index += 1
    if index < size and inner[index] == "<":
        close = inner.find(">", index + 1)
        if close < 0:
            return None
        target = inner[index + 1:close]
        target_span = Span(base + index, base + close + 1)
        index = close + 1
    else:
        start = index
        while index < size and inner[index] not in " \t":
            index += 1
        if index == start:
            return None
        target = inner[start:index]
        target_span = Span(base + start, base + index)
    while index < size and inner[index] in " \t":
        index += 1
    title: str | None = None
    if index < size:
        opener = inner[index]
        closer = {"\"": "\"", "'": "'", "(": ")"}.get(opener)
        if closer is None:
            return None
        end = inner.find(closer, index + 1)
        if end < 0:
            return None
        title = inner[index + 1:end]
        index = end + 1
        while index < size and inner[index] in " \t":
            index += 1
        if index != size:
            return None
    return _unescape_markdown(target), target_span, title

def _parse_inline_destination(
    masked: str, open_paren: int
) -> tuple[str, Span, str | None, int] | None:
    size = len(masked)
    index = open_paren + 1
    depth = 1
    in_angle = False
    quote: str | None = None
    while index < size:
        char = masked[index]
        if char == "\\":
            index += 2
            continue
        if quote is not None:
            if char == quote:
                quote = None
        elif in_angle:
            if char == ">":
                in_angle = False
        elif char == "<":
            in_angle = True
        elif char in "\"'":
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                break
        index += 1
    if index >= size:
        return None
    parsed = _parse_destination_and_title(masked[open_paren + 1:index], open_paren + 1)
    if parsed is None:
        return None
    target, target_span, title = parsed
    return target, target_span, title, index + 1

def _normalize_label(label: str) -> str:
    return " ".join(label.split()).lower()

def _try_obsidian_embed(masked: str, index: int) -> tuple[ImageOccurrence | None, int, ReviewRecord | None]:
    if not masked.startswith("![[", index):
        return None, index, None
    close = masked.find("]]", index + 3)
    if close < 0:
        return None, index, ReviewRecord(
            "unsupported_syntax", "unterminated Obsidian embed", Span(index, len(masked))
        )
    content = masked[index + 3:close]
    if "\n" in content:
        return None, close + 2, ReviewRecord(
            "unsupported_syntax", "Obsidian embed spans multiple lines", Span(index, close + 2)
        )
    name, _, alias = content.partition("|")
    if "#" in name:
        return None, close + 2, ReviewRecord(
            "unsupported_syntax", "Obsidian heading/block embed is not an image", Span(index, close + 2)
        )
    alt: str | None = None
    width: str | None = None
    if alias:
        if re.fullmatch(r"\d+(?:x\d+)?", alias.strip()):
            width = alias.strip()
        else:
            alt = alias
    occurrence = ImageOccurrence(
        index=-1,
        kind="obsidian_embed",
        start=index,
        end=close + 2,
        raw=masked[index:close + 2],
        target=name.strip(),
        alt=alt,
        attribute="embed",
    )
    if width is not None:
        occurrence = dataclasses.replace(occurrence, label=width)
    return occurrence, close + 2, None

def _try_markdown_image(
    masked: str, index: int
) -> tuple[ImageOccurrence | None, int, ReviewRecord | None]:
    if not masked.startswith("![", index):
        return None, index, None
    close = _find_matching_bracket(masked, index + 2)
    if close < 0:
        return None, index, ReviewRecord(
            "unsupported_syntax", "unterminated image alt text", Span(index, min(len(masked), index + 2))
        )
    alt = masked[index + 2:close]
    after = close + 1
    if after < len(masked) and masked[after] == "(":
        parsed = _parse_inline_destination(masked, after)
        if parsed is None:
            return None, after, ReviewRecord(
                "unsupported_syntax", "malformed image destination", Span(index, after)
            )
        target, target_span, title, end = parsed
        return (
            ImageOccurrence(
                index=-1,
                kind="markdown",
                start=index,
                end=end,
                raw=masked[index:end],
                target=target,
                alt=alt,
                title=title,
                target_span=target_span,
            ),
            end,
            None,
        )
    if after < len(masked) and masked[after] == "[":
        label_close = _find_matching_bracket(masked, after + 1)
        if label_close < 0:
            return None, after, ReviewRecord(
                "unsupported_syntax", "unterminated reference label", Span(index, after)
            )
        label = masked[after + 1:label_close] or alt
        return (
            ImageOccurrence(
                index=-1,
                kind="reference",
                start=index,
                end=label_close + 1,
                raw=masked[index:label_close + 1],
                target="",
                alt=alt,
                label=_normalize_label(label),
            ),
            label_close + 1,
            None,
        )
    # Shortcut reference: only meaningful if a definition exists.
    return (
        ImageOccurrence(
            index=-1,
            kind="reference",
            start=index,
            end=close + 1,
            raw=masked[index:close + 1],
            target="",
            alt=alt,
            label=_normalize_label(alt),
        ),
        close + 1,
        None,
    )

def _skip_tag(masked: str, index: int) -> int:
    size = len(masked)
    if masked.startswith("<!--", index):
        return _comment_end(masked, index)
    quote: str | None = None
    before_value = False
    unquoted_value = False
    position = index + 1
    while position < size:
        char = masked[position]
        if quote is not None:
            if char == quote:
                quote = None
        elif char == ">":
            return position + 1
        elif unquoted_value:
            if char in " \t\r\n\f":
                unquoted_value = False
        elif before_value:
            if char not in " \t\r\n\f":
                before_value = False
                if char in "\"'":
                    quote = char
                else:
                    unquoted_value = True
        elif char == "=":
            before_value = True
        # Quotes inside an unquoted value or an attribute name do not open a
        # quoted value in HTML. Treating them as openers can hide the next IMG.
        position += 1
    return size

def _parse_tag_attributes(
    tag_text: str, base: int
) -> tuple[str, list[dict[str, Any]]]:
    match = _HTML_TAG_RE.match(tag_text)
    if not match:
        return "", []
    name = match.group(1).lower()
    index = match.end()
    size = len(tag_text)
    attributes: list[dict[str, Any]] = []
    while index < size:
        while index < size and tag_text[index] in " \t\r\n\f":
            index += 1
        if index >= size or tag_text[index] in "/>":
            break
        attribute_match = re.match(r"([^\s=/>]+)", tag_text[index:])
        if not attribute_match:
            break
        attribute_name = attribute_match.group(1).lower()
        index += attribute_match.end()
        while index < size and tag_text[index] in " \t\r\n\f":
            index += 1
        value: str | None = None
        value_span: Span | None = None
        quote = ""
        if index < size and tag_text[index] == "=":
            index += 1
            while index < size and tag_text[index] in " \t\r\n\f":
                index += 1
            if index < size and tag_text[index] in "\"'":
                quote = tag_text[index]
                index += 1
                value_start = index
                while index < size and tag_text[index] != quote:
                    index += 1
                value = tag_text[value_start:index]
                value_span = Span(base + value_start, base + index)
                if index < size:
                    index += 1
            else:
                value_start = index
                while index < size and tag_text[index] not in " \t\r\n\f>":
                    index += 1
                value = tag_text[value_start:index]
                value_span = Span(base + value_start, base + index)
        attributes.append(
            {"name": attribute_name, "value": value, "value_span": value_span, "quote": quote}
        )
    return name, attributes

def _usable_reference(value: str) -> bool:
    candidate = value.strip()
    if not candidate or candidate.startswith("#"):
        return False
    if candidate.startswith("//"):
        # Reject the Taylor & Francis ``//:0`` placeholder with no host.
        return not candidate.startswith("//:")
    if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", candidate):
        return True
    return True

def _parse_srcset(value: str, base: int) -> list[SrcsetCandidate]:
    candidates: list[SrcsetCandidate] = []
    index = 0
    size = len(value)
    while index < size:
        while index < size and value[index] in " \t\r\n,":
            index += 1
        if index >= size:
            break
        url_start = index
        while index < size and value[index] not in " \t\r\n,":
            index += 1
        url = value[url_start:index]
        while index < size and value[index] in " \t":
            index += 1
        descriptor_start = index
        while index < size and value[index] != ",":
            index += 1
        descriptor = value[descriptor_start:index].strip()
        if url:
            candidates.append(
                SrcsetCandidate(
                    url=url,
                    descriptor=descriptor,
                    span=Span(base + url_start, base + url_start + len(url)),
                )
            )
        if index < size and value[index] == ",":
            index += 1
    return candidates

def _try_html_images(
    masked: str, index: int
) -> tuple[list[ImageOccurrence], int, list[ReviewRecord]]:
    # A statistical comparison such as ``p < 0.05`` is prose, not the start of
    # an HTML tag. Scanning it up to the next '>' used to swallow every image
    # between that comparison and a later table (17 real MinerU figures in the
    # retained sepsis sample). Only enter the tag scanner at a syntactic opener.
    if not (masked.startswith("<!--", index)
            or re.match(r"</?[A-Za-z][A-Za-z0-9:_-]*(?=[\s/>])|<![A-Za-z]|<\?",
                        masked[index:])):
        return [], index + 1, []
    end = _skip_tag(masked, index)
    tag_text = masked[index:end]
    name, attributes = _parse_tag_attributes(tag_text, index)
    if name not in {"img", "source"}:
        return [], end, []
    occurrences: list[ImageOccurrence] = []
    review: list[ReviewRecord] = []
    names = [attribute["name"] for attribute in attributes]
    if len(names) != len(set(names)):
        # Browsers keep the first duplicate HTML attribute. Choosing one URL
        # here and rewriting another can report ready with an unhosted picture.
        return [], end, [ReviewRecord(
            "duplicate_image_attribute", "image tag contains duplicate attributes",
            Span(index, end))]
    by_name = {attribute["name"]: attribute for attribute in attributes}
    alt: str | None = None
    if "alt" in by_name and by_name["alt"]["value"] is not None:
        alt = html_module.unescape(by_name["alt"]["value"])
    kind = "html_img" if name == "img" else "html_source"
    for attribute_name in IMAGE_ATTRIBUTE_PRIORITY:
        attribute = by_name.get(attribute_name)
        if attribute is None or attribute["value"] is None or attribute["value_span"] is None:
            continue
        if not _usable_reference(attribute["value"]):
            continue
        occurrences.append(
            ImageOccurrence(
                index=-1,
                kind=kind,
                start=index,
                end=end,
                raw=tag_text,
                target=html_module.unescape(attribute["value"]).strip(),
                alt=alt,
                attribute=attribute_name,
                target_span=attribute["value_span"],
            )
        )
    for attribute in attributes:
        if attribute["name"] not in {"srcset", "data-srcset"}:
            continue
        if attribute["value"] is None or attribute["value_span"] is None:
            continue
        for candidate in _parse_srcset(attribute["value"], attribute["value_span"].start):
            occurrences.append(
                ImageOccurrence(
                    index=-1,
                    kind="html_srcset",
                    start=index,
                    end=end,
                    raw=tag_text,
                    target=candidate.url,
                    alt=alt,
                    attribute=attribute["name"],
                    target_span=candidate.span,
                    srcset_descriptor=candidate.descriptor or None,
                )
            )
    return occurrences, end, review

def _scan_reference_definitions(
    masked: str,
) -> tuple[dict[str, ReferenceDefinition], list[ReviewRecord]]:
    definitions: dict[str, ReferenceDefinition] = {}
    review: list[ReviewRecord] = []
    for start, end in _line_spans(masked):
        line = masked[start:end]
        match = _REFERENCE_DEFINITION_RE.match(line)
        if not match:
            continue
        raw_label = match.group(1)
        if raw_label.startswith("^"):
            continue
        rest = match.group(2)
        rest_start = start + match.start(2)
        parsed = _parse_destination_and_title(rest, rest_start)
        if parsed is None:
            review.append(
                ReviewRecord("unsupported_syntax", "malformed reference definition", Span(start, end))
            )
            continue
        target, target_span, _title = parsed
        label = _normalize_label(raw_label)
        if label in definitions:
            review.append(
                ReviewRecord(
                    "duplicate_reference",
                    "duplicate reference definition; the first one wins",
                    Span(start, end),
                    label,
                )
            )
            continue
        definitions[label] = ReferenceDefinition(
            label=label,
            target=target,
            target_span=target_span,
            span=Span(start, end),
        )
    return definitions, review

def inventory_markdown_images(text: str) -> ImageInventory:
    """Inventory image constructs without touching fenced or inline code."""
    if not isinstance(text, str):
        raise LiteratureImagesError("Document text must be a string")
    review: list[ReviewRecord] = []
    masked = _mask_code(text, review=review)
    if review:
        return ImageInventory((), (), tuple(review))
    definitions, review = _scan_reference_definitions(masked)
    occurrences: list[ImageOccurrence] = []
    additional_attributes: list[ImageOccurrence] = []
    index = 0
    size = len(masked)
    while index < size:
        char = masked[index]
        if char == "!" and not _is_escaped(text, index):
            if masked.startswith("![[", index):
                occurrence, end, record = _try_obsidian_embed(masked, index)
            else:
                occurrence, end, record = _try_markdown_image(masked, index)
            if record is not None:
                review.append(record)
            if occurrence is not None:
                occurrences.append(occurrence)
            index = end if end > index else index + 1
            continue
        elif char == "<" and not _is_escaped(text, index):
            found, end, records = _try_html_images(masked, index)
            review.extend(records)
            primary_seen = False
            for occurrence in found:
                if occurrence.kind in {"html_img", "html_source"}:
                    if primary_seen:
                        additional_attributes.append(occurrence)
                        continue
                    primary_seen = True
                occurrences.append(occurrence)
            index = max(end, index + 1)
            continue
        index += 1

    # Keep existing reviewed alias indices stable when adding secondary HTML URLs.
    occurrences.extend(additional_attributes)
    resolved: list[ImageOccurrence] = []
    for occurrence in occurrences:
        if occurrence.kind == "reference" and occurrence.label:
            definition = definitions.get(occurrence.label)
            if definition is None:
                review.append(
                    ReviewRecord(
                        "undefined_reference",
                        "reference-style image has no matching definition",
                        Span(occurrence.start, occurrence.end),
                        occurrence.label,
                    )
                )
                resolved.append(dataclasses.replace(occurrence, index=len(resolved), target=""))
                continue
            resolved.append(
                dataclasses.replace(
                    occurrence,
                    index=len(resolved),
                    target=definition.target,
                    target_span=definition.target_span,
                    definition_span=definition.span,
                )
            )
        else:
            resolved.append(dataclasses.replace(occurrence, index=len(resolved)))

    return ImageInventory(
        occurrences=tuple(resolved),
        reference_definitions=tuple(definitions.values()),
        review=tuple(review),
    )
