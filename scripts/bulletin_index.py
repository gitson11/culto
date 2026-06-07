#!/usr/bin/env python3
"""Scan the published bulletin folders and export a small index of each item."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Iterable, List, Optional, Tuple, Dict, Set

ALLOWED_EXTENSIONS = {".docx", ".pdf"}
DEFAULT_ROOTS = ["NOVOS BOLETINS", "NOVOS BOLETINS EM PDF"]
MONTHS = {
    "JANEIRO": 1,
    "FEVEREIRO": 2,
    "MARÇO": 3,
    "MARCO": 3,
    "ABRIL": 4,
    "MAIO": 5,
    "JUNHO": 6,
    "JULHO": 7,
    "AGOSTO": 8,
    "SETEMBRO": 9,
    "OUTUBRO": 10,
    "NOVEMBRO": 11,
    "DEZEMBRO": 12,
}
DATE_PATTERN = re.compile(r"(\d{1,2})\s+DE\s+([A-Za-zÀ-ÿ]+)\s+DE\s+(\d{4})", re.IGNORECASE)


def parse_filename(
    base_name: str,
) -> Tuple[Optional[date], Optional[str], Optional[str], Optional[str]]:
    """Return (parsed date, prefix, suffix, month token) or (None, ...) on failure."""

    def _trim(value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        cleaned = value.strip(" ,;:-_()[]")
        return cleaned if cleaned else None

    match = DATE_PATTERN.search(base_name)
    if not match:
        return None, _trim(base_name), None, None

    prefix = base_name[: match.start()]
    suffix = base_name[match.end() :]
    day_token, month_token, year_token = match.groups()
    prefix_trimmed = _trim(prefix)
    suffix_trimmed = _trim(suffix)
    month_upper = month_token.upper()
    month_number = MONTHS.get(month_upper)
    if month_number is None:
        return None, prefix_trimmed, suffix_trimmed, month_upper
    try:
        parsed_date = date(year=int(year_token), month=month_number, day=int(day_token))
    except ValueError:
        return None, prefix_trimmed, suffix_trimmed, month_upper
    return parsed_date, prefix_trimmed, suffix_trimmed, month_upper


def normalize_category(value: Optional[str]) -> str:
    if not value:
        return "UNLABELED"
    normalized = re.sub(r"\s+", " ", value.strip())
    normalized = normalized.rstrip(" ,;:-_()[]")
    normalized = normalized.strip()
    return normalized.upper() if normalized else "UNLABELED"


def build_index(root_paths: Iterable[str]) -> Dict[str, object]:
    """Scan the requested directories and gather file metadata."""

    base_path = Path.cwd()
    entries: List[dict] = []
    warnings: List[str] = []
    counts_by_ext: Counter = Counter()
    counts_by_year: Counter = Counter()
    counts_by_category: Counter = Counter()
    files_by_root: Counter[str] = Counter()
    missing_date: List[dict] = []
    unknown_months: Set[str] = set()
    duplicates: defaultdict = defaultdict(list)
    earliest: Optional[date] = None
    latest: Optional[date] = None
    scanned_roots: List[str] = []

    for raw_root in root_paths:
        root_path = Path(raw_root)
        if not root_path.is_absolute():
            root_path = (base_path / raw_root).resolve()
        if not root_path.exists():
            warnings.append(f"Skipped {raw_root!r}: path not found ({root_path})")
            continue
        scanned_roots.append(str(root_path))
        for file_path in sorted(root_path.rglob("*")):
            if not file_path.is_file():
                continue
            ext = file_path.suffix.lower()
            if ext not in ALLOWED_EXTENSIONS:
                continue
            try:
                relative = file_path.relative_to(base_path).as_posix()
            except ValueError:
                relative = str(file_path)
            parsed_date, prefix, suffix, month_token = parse_filename(file_path.stem)
            category = prefix
            normalized_category = normalize_category(category)
            notes = suffix
            entry = {
                "relative_path": relative,
                "filename": file_path.name,
                "format": ext.lstrip("."),
                "root": root_path.name,
                "category": category,
                "normalized_category": normalized_category,
                "notes": notes,
                "date": parsed_date.isoformat() if parsed_date else None,
            }
            entries.append(entry)
            counts_by_ext[ext.lstrip(".")] += 1
            files_by_root[root_path.name] += 1
            if parsed_date:
                counts_by_year[parsed_date.year] += 1
                counts_by_category[normalized_category] += 1
                key = (normalized_category, parsed_date.isoformat())
                duplicates[key].append(relative)
                if earliest is None or parsed_date < earliest:
                    earliest = parsed_date
                if latest is None or parsed_date > latest:
                    latest = parsed_date
            else:
                missing_date.append(
                    {
                        "relative_path": relative,
                        "category": category,
                        "notes": notes,
                        "month_token": month_token,
                    }
                )
                if month_token:
                    month_upper = month_token.upper()
                    if month_upper not in MONTHS:
                        unknown_months.add(month_upper)

    duplicate_details = []
    for (category, dt), file_list in sorted(duplicates.items()):
        if len(file_list) <= 1:
            continue
        duplicate_details.append(
            {"category": category, "date": dt, "files": sorted(file_list)}
        )

    summary = {
        "scanned_roots": scanned_roots,
        "total_files": len(entries),
        "with_dates": sum(1 for entry in entries if entry["date"]),
        "without_dates": len(missing_date),
        "earliest_date": earliest.isoformat() if earliest else None,
        "latest_date": latest.isoformat() if latest else None,
        "counts_by_extension": {
            ext: counts_by_ext[ext] for ext in sorted(counts_by_ext)
        },
        "counts_by_year": {year: counts_by_year[year] for year in sorted(counts_by_year)},
        "top_categories": [
            {"category": cat, "count": cnt}
            for cat, cnt in counts_by_category.most_common(5)
        ],
        "files_by_root": {root: files_by_root[root] for root in sorted(files_by_root)},
        "duplicate_groups": len(duplicate_details),
        "unknown_month_tokens": sorted(unknown_months),
    }

    return {
        "entries": entries,
        "summary": summary,
        "duplicates": duplicate_details,
        "missing_dates": missing_date,
        "warnings": warnings,
    }


def print_summary(
    summary: dict,
    missing: List[dict],
    duplicates: List[dict],
    warnings: List[str],
    output_path: Optional[Path],
    wrote_file: bool,
) -> None:
    """Emit a short human summary to stdout."""

    print("Bulletin index summary")
    scanned = summary.get("scanned_roots") or []
    if scanned:
        print(f"  Scanned roots: {', '.join(scanned)}")
    print(
        f"  Files found: {summary.get('total_files', 0)} "
        f"(with dates: {summary.get('with_dates', 0)}, "
        f"without parseable date: {summary.get('without_dates', 0)})"
    )
    earliest = summary.get("earliest_date")
    latest = summary.get("latest_date")
    if earliest and latest:
        print(f"  Date range: {earliest} -> {latest}")
    counts_ext = summary.get("counts_by_extension", {})
    if counts_ext:
        ext_summary = ", ".join(f"{ext}={counts_ext[ext]}" for ext in counts_ext)
        print(f"  Extension counts: {ext_summary}")
    if duplicates:
        print(f"  Duplicate groups (same category/date): {len(duplicates)}")
    top_categories = summary.get("top_categories") or []
    if top_categories:
        tops = ", ".join(
            f"{item['category']} ({item['count']})" for item in top_categories
        )
        print(f"  Top categories: {tops}")
    if missing:
        sample = " | ".join(
            f"{item['relative_path']}" for item in missing[:3]
        )
        print(
            f"  Missing dates ({len(missing)} entries). Examples: {sample} "
            "- see JSON for full list."
        )
    if warnings:
        print("  Warnings:")
        for msg in warnings:
            print(f"    - {msg}")
    if output_path:
        print(f"  Data { 'written to' if wrote_file else 'not written (dry run) to' } {output_path}")


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Index the Word/PDF bulletins under the NOVOS BOLETINS folders."
    )
    parser.add_argument(
        "--roots",
        "-r",
        nargs="+",
        default=DEFAULT_ROOTS,
        help="Root folders to scan (default: NOVOS BOLETINS and NOVOS BOLETINS EM PDF).",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="bulletin-index.json",
        help="JSON file where the index is written.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the summary without writing the JSON output.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_arguments()
    index = build_index(args.roots)
    output_path = Path(args.output)
    if not args.dry_run:
        output_path.write_text(
            json.dumps(
                index,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    print_summary(
        index["summary"],
        index["missing_dates"],
        index["duplicates"],
        index["warnings"],
        output_path,
        not args.dry_run,
    )


if __name__ == "__main__":
    main()
