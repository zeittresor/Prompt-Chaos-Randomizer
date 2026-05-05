from __future__ import annotations

import csv
import os
import random
import re
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Iterable, Literal

TextMode = Literal["txt", "csv_prompt", "csv_negative"]
ShuffleMode = Literal["all_halves", "keep_first_halves", "line_insert"]
SegmentMode = Literal["halves", "quarters", "mixed"]
PlacementMode = Literal["random", "prepend", "append"]
HeaderMode = Literal["auto", "yes", "no"]
DelimiterMode = Literal["auto", "comma", "semicolon", "tab"]


@dataclass
class RandomizerOptions:
    mode: TextMode = "txt"
    shuffle_mode: ShuffleMode = "all_halves"
    segment_mode: SegmentMode = "halves"
    output_factor: int = 1
    placement_mode: PlacementMode = "random"
    positive_suffix: str = " anything is matching well."
    negative_suffix: str = " worse looking."
    avoid_same_source_pair: bool = True
    preserve_blank_lines: bool = True
    normalize_whitespace: bool = True
    passes: int = 1
    seed: int | None = None
    csv_header_mode: HeaderMode = "auto"
    csv_delimiter_mode: DelimiterMode = "auto"
    csv_encoding: str = "auto"
    text_encoding: str = "auto"


@dataclass
class RandomizerStats:
    input_path: str
    output_path: str
    mode: str
    processed_items: int = 0
    untouched_items: int = 0
    zero_dot_fixed: int = 0
    odd_dot_fixed: int = 0
    even_dot_unchanged: int = 0
    chunks_created: int = 0
    segment_mode: str = "halves"
    output_factor: int = 1
    passes: int = 1
    seed: int | None = None
    warnings: list[str] | None = None

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class Chunk:
    text: str
    source_index: int
    chunk_index: int


_ENCODING_CANDIDATES = ("utf-8-sig", "utf-8", "cp1252", "latin-1")


def timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def make_output_path(input_path: str | Path, suffix: str = "changed") -> Path:
    """Create an output path that is always a plain .txt wildcard file."""
    path = Path(input_path)
    stamp = timestamp()
    return path.with_name(f"{path.stem}_{suffix}_{stamp}.txt")


def read_text_file(path: str | Path, encoding: str = "auto") -> tuple[list[str], str]:
    path = Path(path)
    if encoding and encoding.lower() != "auto":
        text = path.read_text(encoding=encoding)
        return text.splitlines(), encoding

    last_error: Exception | None = None
    for enc in _ENCODING_CANDIDATES:
        try:
            text = path.read_text(encoding=enc)
            return text.splitlines(), enc
        except UnicodeDecodeError as exc:
            last_error = exc
    raise UnicodeDecodeError("auto", b"", 0, 1, f"Could not decode {path}: {last_error}")


def write_text_file(path: str | Path, lines: Iterable[str], encoding: str = "utf-8") -> None:
    Path(path).write_text("\n".join(lines) + "\n", encoding=encoding)


def _normalize_spaces(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\s+([.,;:!?])", r"\1", text)
    text = re.sub(r"([.!?])(?=\S)", r"\1 ", text)
    return text.strip()


def normalize_period_balance(text: str, suffix: str, normalize_whitespace: bool = True) -> tuple[str, str]:
    """Return normalized text and status: zero, odd, even, or blank."""
    original = text
    if not text.strip():
        return text, "blank"

    dot_count = text.count(".")
    if dot_count == 0:
        text = text.rstrip() + "." + _suffix_with_leading_space(suffix)
        status = "zero"
    elif dot_count % 2 == 1:
        text = text.rstrip() + _suffix_with_leading_space(suffix)
        status = "odd"
    else:
        status = "even"

    if normalize_whitespace:
        text = _normalize_spaces(text)
    elif text is not original:
        text = text.strip()
    return text, status


def _suffix_with_leading_space(suffix: str) -> str:
    suffix = suffix.strip()
    if not suffix:
        return ""
    return " " + suffix


def split_into_period_segments(text: str) -> list[str]:
    """Split text into dot-terminated fragments. Only '.' is used as requested."""
    text = text.strip()
    if not text:
        return []

    segments: list[str] = []
    buf: list[str] = []
    for ch in text:
        buf.append(ch)
        if ch == ".":
            segment = "".join(buf).strip()
            if segment:
                segments.append(segment)
            buf = []

    trailing = "".join(buf).strip()
    if trailing:
        if segments:
            segments[-1] = (segments[-1] + " " + trailing).strip()
        else:
            segments.append(trailing + ".")

    return segments


def _split_segments_evenly(segments: list[str], target_parts: int) -> list[str]:
    """Split segments into up to target_parts non-empty chunk groups."""
    if not segments:
        return []
    if len(segments) == 1:
        return [" ".join(segments).strip()]

    parts = max(2, min(target_parts, len(segments)))
    base = len(segments) // parts
    remainder = len(segments) % parts

    chunks: list[str] = []
    start = 0
    for part_index in range(parts):
        size = base + (1 if part_index < remainder else 0)
        group = segments[start : start + size]
        start += size
        chunk = " ".join(group).strip()
        if chunk:
            chunks.append(chunk)
    return chunks


def split_text_into_chunks(text: str, segment_mode: SegmentMode = "halves") -> list[str]:
    """Create two-part, four-part or mixed chunks at period boundaries."""
    text = text.strip()
    if not text:
        return []

    segments = split_into_period_segments(text)
    if len(segments) < 2:
        return [text]

    if segment_mode == "quarters":
        return _split_segments_evenly(segments, 4)
    if segment_mode == "mixed":
        halves = _split_segments_evenly(segments, 2)
        quarters = _split_segments_evenly(segments, 4)
        return halves + quarters
    return _split_segments_evenly(segments, 2)


def split_after_periods_at_half(text: str) -> tuple[str, str]:
    """Legacy helper: split at the 50% period boundary."""
    chunks = split_text_into_chunks(text, "halves")
    if not chunks:
        return "", ""
    if len(chunks) == 1:
        return chunks[0], ""
    return chunks[0], " ".join(chunks[1:]).strip()


def combine_chunks(a: str, b: str, placement: PlacementMode, rng: random.Random, normalize_whitespace: bool) -> str:
    a = a.strip()
    b = b.strip()
    if placement == "prepend":
        text = f"{b} {a}" if b else a
    elif placement == "append":
        text = f"{a} {b}" if b else a
    else:
        if rng.choice([True, False]):
            text = f"{a} {b}" if b else a
        else:
            text = f"{b} {a}" if b else a
    return _normalize_spaces(text) if normalize_whitespace else text.strip()


def randomize_text_items(items: list[str], options: RandomizerOptions, suffix: str) -> tuple[list[str], RandomizerStats]:
    rng = random.Random(options.seed)
    warnings: list[str] = []
    working = list(items)
    passes = max(1, int(options.passes))
    output_factor = max(1, min(2, int(getattr(options, "output_factor", 1) or 1)))
    stats = RandomizerStats(
        input_path="",
        output_path="",
        mode=options.mode,
        passes=passes,
        seed=options.seed,
        segment_mode=options.segment_mode,
        output_factor=output_factor,
        warnings=warnings,
    )

    for pass_index in range(passes):
        active_positions: list[int] = []
        normalized_items: list[str] = list(working)
        chunks: list[Chunk] = []
        left_chunks: list[Chunk] = []
        right_chunks: list[Chunk] = []

        for pos, item in enumerate(working):
            if not item.strip() and options.preserve_blank_lines:
                stats.untouched_items += 1 if pass_index == 0 else 0
                continue

            normalized, status = normalize_period_balance(item, suffix, options.normalize_whitespace)
            normalized_items[pos] = normalized
            if pass_index == 0:
                stats.processed_items += 1
                if status == "zero":
                    stats.zero_dot_fixed += 1
                elif status == "odd":
                    stats.odd_dot_fixed += 1
                elif status == "even":
                    stats.even_dot_unchanged += 1

            half_left, half_right = split_after_periods_at_half(normalized)
            if not half_left and not half_right:
                if pass_index == 0:
                    stats.untouched_items += 1
                continue
            if not half_right:
                half_right = suffix.strip() or "."

            active_positions.append(pos)
            left_chunks.append(Chunk(half_left, pos, 0))
            right_chunks.append(Chunk(half_right, pos, 1))

            item_chunks = split_text_into_chunks(normalized, options.segment_mode)
            if len(item_chunks) < 2:
                item_chunks = [half_left, half_right]
            for chunk_index, chunk_text in enumerate(item_chunks):
                if chunk_text.strip():
                    chunks.append(Chunk(chunk_text, pos, chunk_index))

        if pass_index == 0:
            stats.chunks_created = len(chunks)

        if not active_positions:
            working = normalized_items
            continue

        final_pass = pass_index == passes - 1
        target_count = len(active_positions) * (output_factor if final_pass else 1)

        if options.shuffle_mode == "keep_first_halves":
            new_values = _generate_keep_first_values(
                left_chunks,
                right_chunks,
                target_count,
                rng,
                options.avoid_same_source_pair,
                options.placement_mode,
                options.normalize_whitespace,
            )

        elif options.shuffle_mode == "line_insert":
            new_values = _generate_line_insert_values(
                left_chunks,
                right_chunks,
                target_count,
                rng,
                options.avoid_same_source_pair,
                options.placement_mode,
                options.normalize_whitespace,
            )

        else:  # all_halves / all chunks
            new_values = _generate_pool_values(
                chunks,
                target_count,
                rng,
                options.avoid_same_source_pair,
                options.placement_mode,
                options.normalize_whitespace,
            )

        if len(new_values) < len(active_positions):
            warnings.append("The chunk mixer produced fewer items than expected; remaining lines were left normalized only.")

        new_working = list(normalized_items)
        for pos, value in zip(active_positions, new_values):
            new_working[pos] = value

        if final_pass and len(new_values) > len(active_positions):
            extra_values = new_values[len(active_positions) : target_count]
            new_working.extend(extra_values)

        working = new_working

    if output_factor > 1:
        warnings.append("Expanded output was enabled; the saved TXT wildcard file may contain more lines than the source.")

    return working, stats


def _generate_pool_values(
    chunks: list[Chunk],
    target_count: int,
    rng: random.Random,
    avoid_same_source: bool,
    placement: PlacementMode,
    normalize_whitespace: bool,
) -> list[str]:
    if len(chunks) < 2:
        return [chunk.text for chunk in chunks][:target_count]

    values: list[str] = []
    attempts = 0
    while len(values) < target_count and attempts < max(3, target_count * 4):
        shuffled_chunks = chunks[:]
        rng.shuffle(shuffled_chunks)
        pairs = _pair_chunks(shuffled_chunks, rng, avoid_same_source)
        values.extend(combine_chunks(a.text, b.text, placement, rng, normalize_whitespace) for a, b in pairs)
        attempts += 1
    return values[:target_count]


def _generate_keep_first_values(
    left_chunks: list[Chunk],
    right_chunks: list[Chunk],
    target_count: int,
    rng: random.Random,
    avoid_same_source: bool,
    placement: PlacementMode,
    normalize_whitespace: bool,
) -> list[str]:
    if not left_chunks or not right_chunks:
        return []

    values: list[str] = []
    attempts = 0
    while len(values) < target_count and attempts < max(3, target_count * 4):
        bases = left_chunks[:]
        rights = right_chunks[:]
        rng.shuffle(rights)
        if avoid_same_source and len(rights) > 1:
            _avoid_same_source_against_bases(bases, rights, rng)
        for base, right in zip(bases, rights):
            values.append(combine_chunks(base.text, right.text, placement, rng, normalize_whitespace))
            if len(values) >= target_count:
                break
        attempts += 1
    return values[:target_count]


def _generate_line_insert_values(
    left_chunks: list[Chunk],
    right_chunks: list[Chunk],
    target_count: int,
    rng: random.Random,
    avoid_same_source: bool,
    placement: PlacementMode,
    normalize_whitespace: bool,
) -> list[str]:
    if not left_chunks or not right_chunks:
        return []

    values: list[str] = []
    attempts = 0
    while len(values) < target_count and attempts < max(3, target_count * 4):
        shuffled_lefts = left_chunks[:]
        shuffled_rights = right_chunks[:]
        rng.shuffle(shuffled_lefts)
        rng.shuffle(shuffled_rights)
        for left, right in zip(shuffled_lefts, shuffled_rights):
            if avoid_same_source and len(shuffled_rights) > 1 and left.source_index == right.source_index:
                alternatives = [candidate for candidate in shuffled_rights if candidate.source_index != left.source_index]
                if alternatives:
                    right = rng.choice(alternatives)
            values.append(combine_chunks(left.text, right.text, placement, rng, normalize_whitespace))
            if len(values) >= target_count:
                break
        attempts += 1
    return values[:target_count]


def _avoid_same_source_against_bases(bases: list[Chunk], candidates: list[Chunk], rng: random.Random) -> None:
    if len(candidates) <= 1:
        return
    for i, base in enumerate(bases):
        if candidates[i].source_index != base.source_index:
            continue
        swap_candidates = [j for j in range(len(candidates)) if j != i and candidates[j].source_index != base.source_index and candidates[i].source_index != bases[j].source_index]
        if swap_candidates:
            j = rng.choice(swap_candidates)
            candidates[i], candidates[j] = candidates[j], candidates[i]


def _pair_chunks(chunks: list[Chunk], rng: random.Random, avoid_same_source: bool) -> list[tuple[Chunk, Chunk]]:
    chunks = chunks[:]
    if len(chunks) % 2 == 1:
        chunks.pop()
    pairs: list[tuple[Chunk, Chunk]] = []
    i = 0
    while i < len(chunks) - 1:
        a = chunks[i]
        b = chunks[i + 1]
        if avoid_same_source and a.source_index == b.source_index and len(chunks) > 2:
            swap_index = None
            for j in range(i + 2, len(chunks)):
                if chunks[j].source_index != a.source_index:
                    swap_index = j
                    break
            if swap_index is not None:
                chunks[i + 1], chunks[swap_index] = chunks[swap_index], chunks[i + 1]
                b = chunks[i + 1]
        pairs.append((a, b))
        i += 2
    return pairs


def process_txt_file(input_path: str | Path, options: RandomizerOptions) -> RandomizerStats:
    lines, encoding = read_text_file(input_path, options.text_encoding)
    output_lines, stats = randomize_text_items(lines, options, options.positive_suffix)
    output_path = make_output_path(input_path)
    write_text_file(output_path, output_lines, "utf-8")
    stats.input_path = str(input_path)
    stats.output_path = str(output_path)
    stats.mode = "txt"
    if stats.warnings is not None and encoding.lower() not in ("utf-8", "utf-8-sig"):
        stats.warnings.append(f"Input was decoded as {encoding}; output was saved as UTF-8.")
    return stats


def read_csv_file(path: str | Path, delimiter_mode: DelimiterMode = "auto", encoding: str = "auto") -> tuple[list[list[str]], csv.Dialect, str]:
    path = Path(path)
    text = None
    used_encoding = "utf-8-sig"
    if encoding and encoding.lower() != "auto":
        text = path.read_text(encoding=encoding)
        used_encoding = encoding
    else:
        last_error: Exception | None = None
        for enc in _ENCODING_CANDIDATES:
            try:
                text = path.read_text(encoding=enc)
                used_encoding = enc
                break
            except UnicodeDecodeError as exc:
                last_error = exc
        if text is None:
            raise UnicodeDecodeError("auto", b"", 0, 1, f"Could not decode {path}: {last_error}")

    delimiter = _delimiter_from_mode(delimiter_mode)
    if delimiter is None:
        try:
            dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t")
        except csv.Error:
            dialect = csv.excel
    else:
        class CustomDialect(csv.excel):
            pass
        CustomDialect.delimiter = delimiter
        dialect = CustomDialect

    rows = list(csv.reader(text.splitlines(), dialect=dialect))
    return rows, dialect, used_encoding


def _delimiter_from_mode(mode: DelimiterMode) -> str | None:
    if mode == "comma":
        return ","
    if mode == "semicolon":
        return ";"
    if mode == "tab":
        return "\t"
    return None


def has_csv_header(rows: list[list[str]], mode: HeaderMode) -> bool:
    if not rows:
        return False
    if mode == "yes":
        return True
    if mode == "no":
        return False
    first = [cell.strip().lower() for cell in rows[0]]
    header_words = {"name", "prompt", "negative prompt", "negative_prompt", "negative", "style", "title"}
    return any(cell in header_words for cell in first) or (len(first) >= 3 and "prompt" in first[1] and "negative" in first[2])


def process_csv_file(input_path: str | Path, options: RandomizerOptions) -> RandomizerStats:
    rows, _dialect, encoding = read_csv_file(input_path, options.csv_delimiter_mode, options.csv_encoding)
    column_index = 1 if options.mode == "csv_prompt" else 2
    suffix = options.positive_suffix if options.mode == "csv_prompt" else options.negative_suffix
    header = has_csv_header(rows, options.csv_header_mode)
    start = 1 if header else 0

    selected_values: list[str] = []
    warnings: list[str] = []
    for i, row in enumerate(rows[start:], start=start):
        if len(row) <= column_index:
            warnings.append(f"Row {i + 1} has no column {column_index + 1}; skipped for TXT wildcard output.")
            continue
        selected_values.append(row[column_index])

    output_values, stats = randomize_text_items(selected_values, options, suffix)

    output_path = make_output_path(input_path)
    write_text_file(output_path, output_values, "utf-8")

    stats.input_path = str(input_path)
    stats.output_path = str(output_path)
    stats.mode = f"{options.mode}_to_txt"
    if stats.warnings is None:
        stats.warnings = []
    stats.warnings.append("CSV was used as source only. Output was saved as plain TXT wildcard lines for Forge/A1111.")
    stats.warnings.extend(warnings)
    if header:
        stats.warnings.append("CSV header row was skipped and not written to the TXT output.")
    if encoding.lower() not in ("utf-8", "utf-8-sig"):
        stats.warnings.append(f"Input was decoded as {encoding}; output was saved as UTF-8.")
    if not selected_values:
        stats.warnings.append("No usable CSV rows were found for the selected column.")
    return stats


def process_file(input_path: str | Path, options: RandomizerOptions) -> RandomizerStats:
    path = Path(input_path)
    if not path.exists():
        raise FileNotFoundError(path)
    if options.mode == "txt":
        return process_txt_file(path, options)
    return process_csv_file(path, options)


def preview_items_from_file(input_path: str | Path, options: RandomizerOptions, max_items: int = 8) -> tuple[list[str], RandomizerStats]:
    """Preview without saving. Uses the same engine, only on a sample copy."""
    path = Path(input_path)
    if options.mode == "txt":
        lines, _encoding = read_text_file(path, options.text_encoding)
        sample = lines[:max_items]
        return randomize_text_items(sample, options, options.positive_suffix)

    rows, _dialect, _encoding = read_csv_file(path, options.csv_delimiter_mode, options.csv_encoding)
    column_index = 1 if options.mode == "csv_prompt" else 2
    suffix = options.positive_suffix if options.mode == "csv_prompt" else options.negative_suffix
    header = has_csv_header(rows, options.csv_header_mode)
    start = 1 if header else 0
    values = [row[column_index] for row in rows[start:] if len(row) > column_index][:max_items]
    return randomize_text_items(values, options, suffix)
