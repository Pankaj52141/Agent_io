"""
Understanding File Generator — Creates pre-computed artifacts for faster agent responses.
Uses rule-based extraction (no LLM calls) for speed and cost.
"""
import json
import os
import re
from collections import defaultdict
from pathlib import Path
from backend.config import UNDERSTANDING_DIR


def generate_understanding_files(chunks: list[dict]):
    """Generate all understanding files from processed chunks."""
    os.makedirs(UNDERSTANDING_DIR, exist_ok=True)

    _generate_file_summaries(chunks)
    _generate_key_metrics(chunks)
    _generate_category_index(chunks)
    _generate_schema_notes(chunks)
    _generate_glossary()

    print(f"    Generated 5 understanding files in {UNDERSTANDING_DIR}")


def _generate_file_summaries(chunks: list[dict]):
    """Create per-file summaries."""
    file_stats = defaultdict(lambda: {
        "total_chunks": 0,
        "data_categories": set(),
        "fiscal_years": set(),
        "fiscal_quarters": set(),
        "sample_content": [],
    })

    for chunk in chunks:
        source = chunk.get("source_file", "unknown")
        file_stats[source]["total_chunks"] += 1
        cat = chunk.get("data_category", "general")
        file_stats[source]["data_categories"].add(cat)
        fy = chunk.get("fiscal_year", "")
        if fy:
            file_stats[source]["fiscal_years"].add(fy)
        fq = chunk.get("fiscal_quarter", "")
        if fq:
            file_stats[source]["fiscal_quarters"].add(fq)
        if len(file_stats[source]["sample_content"]) < 3:
            file_stats[source]["sample_content"].append(
                chunk.get("content", "")[:200]
            )

    summaries = {}
    for source, stats in file_stats.items():
        cats = ", ".join(sorted(stats["data_categories"]))
        years = ", ".join(sorted(stats["fiscal_years"]))
        quarters = ", ".join(sorted(stats["fiscal_quarters"]))

        if source.endswith(".pdf"):
            doc_type = "Annual Report (10-K)"
        else:
            doc_type = f"Quarterly Financial Statement ({quarters})" if quarters else "Financial Statement"

        summary = f"Apple Inc. {doc_type} for FY {years}. Contains {stats['total_chunks']} data chunks covering: {cats}."

        summaries[source] = {
            "total_chunks": stats["total_chunks"],
            "data_categories": sorted(stats["data_categories"]),
            "fiscal_years": sorted(stats["fiscal_years"]),
            "fiscal_quarters": sorted(stats["fiscal_quarters"]),
            "document_type": doc_type,
            "summary": summary,
            "sample_content": stats["sample_content"],
        }

    _save_json("file_summaries.json", summaries)


def _generate_key_metrics(chunks: list[dict]):
    """Extract key financial metrics using regex."""
    metrics_by_year = defaultdict(lambda: defaultdict(list))

    patterns = [
        (r'(?i)(?:total\s+)?(?:net\s+)?revenue[s]?\s*(?:was|were|of|:)?\s*\$?\s*([\d,]+(?:\.\d+)?)\s*(billion|million|B|M)', "revenue"),
        (r'(?i)net\s+income\s*(?:was|were|of|:)?\s*\$?\s*([\d,]+(?:\.\d+)?)\s*(billion|million|B|M)', "net_income"),
        (r'(?i)gross\s+margin\s*(?:was|were|of|:)?\s*([\d.]+)\s*%', "gross_margin_pct"),
        (r'(?i)operating\s+income\s*(?:was|were|of|:)?\s*\$?\s*([\d,]+(?:\.\d+)?)\s*(billion|million|B|M)', "operating_income"),
        (r'(?i)(?:diluted\s+)?(?:earnings|EPS)\s+per\s+(?:diluted\s+)?share\s*(?:was|were|of|:)?\s*\$?\s*([\d.]+)', "eps"),
        (r'(?i)total\s+assets\s*(?:was|were|of|:)?\s*\$?\s*([\d,]+(?:\.\d+)?)\s*(billion|million|B|M)', "total_assets"),
        (r'(?i)(?:total\s+)?(?:long[- ]term\s+)?debt\s*(?:was|were|of|:)?\s*\$?\s*([\d,]+(?:\.\d+)?)\s*(billion|million|B|M)', "total_debt"),
        (r'(?i)cash\s+(?:and\s+cash\s+equivalents|equivalents)\s*(?:was|were|of|:)?\s*\$?\s*([\d,]+(?:\.\d+)?)\s*(billion|million|B|M)', "cash"),
        (r'(?i)(?:total\s+)?employees?\s*(?:was|were|of|approximately|:)?\s*([\d,]+)', "employee_count"),
        (r'\$\s*([\d,]+(?:\.\d+)?)\s*(billion|million)', "dollar_amount"),
    ]

    for chunk in chunks:
        content = chunk.get("content", "")
        fy = chunk.get("fiscal_year", "unknown")
        fq = chunk.get("fiscal_quarter", "")
        period = f"FY{fy}" + (f" {fq}" if fq else "")

        for pattern, metric_name in patterns:
            if metric_name == "dollar_amount":
                continue  # Skip generic dollar amounts
            for match in re.finditer(pattern, content):
                value = match.group(0).strip()
                metrics_by_year[period][metric_name].append({
                    "value": value,
                    "source": chunk.get("source_file", "unknown"),
                })

    # Deduplicate
    clean_metrics = {}
    for period, metrics in metrics_by_year.items():
        clean_metrics[period] = {}
        for metric_name, entries in metrics.items():
            # Keep unique values
            seen = set()
            unique = []
            for e in entries:
                if e["value"] not in seen:
                    seen.add(e["value"])
                    unique.append(e)
            clean_metrics[period][metric_name] = unique[:5]  # Top 5

    _save_json("key_metrics.json", clean_metrics)


def _generate_category_index(chunks: list[dict]):
    """Map data_category -> list of chunk IDs."""
    index = defaultdict(list)
    for chunk in chunks:
        cat = chunk.get("data_category", "general")
        chunk_id = chunk.get("id", "")
        if chunk_id:
            index[cat].append(chunk_id)

    _save_json("category_index.json", dict(index))


def _generate_schema_notes(chunks: list[dict]):
    """Document schema for Excel-sourced chunks."""
    schema = {}
    for chunk in chunks:
        source = chunk.get("source_file", "")
        if source.endswith(".xls") or source.endswith(".xlsx"):
            if source not in schema:
                schema[source] = {
                    "sheets": [],
                    "fiscal_year": chunk.get("fiscal_year", ""),
                    "fiscal_quarter": chunk.get("fiscal_quarter", ""),
                }
            sheet = chunk.get("page_or_sheet", chunk.get("section", ""))
            if sheet and sheet not in schema[source]["sheets"]:
                schema[source]["sheets"].append(sheet)
            # Extract column headers from first line of content
            content = chunk.get("content", "")
            first_line = content.split("\n")[0] if content else ""
            if "|" in first_line and "columns" not in schema[source]:
                cols = [c.strip() for c in first_line.split("|") if c.strip()]
                schema[source]["columns_sample"] = cols[:10]

    _save_json("schema_notes.json", schema)


def _generate_glossary():
    """Apple-specific financial terms glossary."""
    glossary = {
        "Services revenue": "Revenue from Apple's services segment including App Store, Apple Music, iCloud+, Apple TV+, Apple Pay, AppleCare, and licensing.",
        "Greater China segment": "Geographic operating segment covering China mainland, Hong Kong, and Taiwan.",
        "Wearables, Home and Accessories": "Product category including Apple Watch, AirPods, AirTag, HomePod, and accessories.",
        "Products revenue": "Revenue from hardware sales including iPhone, Mac, iPad, and Wearables/Home/Accessories.",
        "Americas segment": "Geographic segment covering North and South America.",
        "Europe segment": "Geographic segment covering European countries, India, the Middle East, and Africa.",
        "Japan segment": "Geographic segment covering Japan.",
        "Rest of Asia Pacific": "Geographic segment covering Australia, South Korea, and other Asian markets.",
        "10-K": "Annual report filed with the SEC containing comprehensive financial information.",
        "Cost of sales": "Direct costs attributable to the production of goods and services sold.",
        "R&D expenses": "Research and development costs expensed as incurred.",
        "SG&A expenses": "Selling, general, and administrative expenses.",
        "RSU": "Restricted Stock Unit — a form of equity compensation.",
        "ASC 606": "Revenue recognition accounting standard.",
        "Operating segments": "Apple's reportable operating segments: Americas, Europe, Greater China, Japan, Rest of Asia Pacific.",
        "Deferred revenue": "Revenue collected but not yet recognized, primarily from services and extended warranties.",
        "Commercial paper": "Short-term unsecured promissory notes used for financing.",
        "Term debt": "Long-term borrowings including fixed and floating rate notes.",
    }

    _save_json("glossary.json", glossary)


def _save_json(filename: str, data):
    """Save data as JSON file."""
    path = os.path.join(UNDERSTANDING_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
