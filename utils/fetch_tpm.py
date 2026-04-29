#!/usr/bin/env python3
"""
fetch_tpm.py — Query GCP Cloud Monitoring for Vertex AI token usage and
generate per-model TPM CSV files compatible with the Gemini Cost Optimizer app.

Usage (Cloud Shell):
    python3 utils/fetch_tpm.py --project MY_PROJECT_ID [--port 8080]

Requirements:
    pip install google-cloud-monitoring

Authentication:
    Runs under the active gcloud credentials (Application Default Credentials).
    In Cloud Shell this is automatic. Otherwise run:
        gcloud auth application-default login

Output:
    - One CSV per selected model (or a combined one):  tpm_<model_id>.csv
    - Prints a localhost app URL for each file so you can click to load it
      directly in the Gemini Cost Optimizer (served via `python3 -m http.server`).
"""

import argparse
import csv
import os
import re
import sys
from datetime import datetime, timezone, timedelta

# ---------------------------------------------------------------------------
# Metric constants
# ---------------------------------------------------------------------------
METRIC_TYPE = "aiplatform.googleapis.com/publisher/online_serving/token_count"
# metric.labels.type  -> "input" | "output"
# resource.labels.model_id -> e.g. "gemini-1.5-pro-002"

ALIGNMENT_PERIOD_SECONDS = 60  # 1-minute buckets

# ---------------------------------------------------------------------------
# Interactive prompt helpers
# ---------------------------------------------------------------------------

CYAN  = "\033[96m"
GREEN = "\033[92m"
BOLD  = "\033[1m"
DIM   = "\033[2m"
RESET = "\033[0m"


def _separator(char="─", width=60):
    print(f"{DIM}{char * width}{RESET}")


def prompt_choice(title: str, options: list[str], default: int = 1) -> int:
    """
    Print a numbered menu and return the 1-based index of the chosen option.
    Loops until a valid selection is made.
    """
    print()
    _separator()
    print(f"{BOLD}{CYAN}{title}{RESET}")
    _separator()
    for i, opt in enumerate(options, 1):
        marker = f"{GREEN}▶{RESET}" if i == default else " "
        print(f"  {marker} {BOLD}{i}{RESET}. {opt}")
    _separator()

    while True:
        try:
            raw = input(f"  Enter choice [1–{len(options)}] (default {default}): ").strip()
            if raw == "":
                return default
            choice = int(raw)
            if 1 <= choice <= len(options):
                return choice
            print(f"  Please enter a number between 1 and {len(options)}.")
        except (ValueError, EOFError):
            print(f"  Please enter a number between 1 and {len(options)}.")


def prompt_multi_choice(title: str, options: list[str]) -> list[int]:
    """
    Print a numbered menu for multi-selection.
    User may enter comma-separated numbers, ranges (e.g. 1-3), or 'all'.
    Returns a sorted list of 1-based indices.
    """
    print()
    _separator()
    print(f"{BOLD}{CYAN}{title}{RESET}")
    _separator()
    for i, opt in enumerate(options, 1):
        print(f"   {BOLD}{i}{RESET}. {opt}")
    _separator()
    print(f"  {DIM}Enter numbers separated by commas, a range like 1-3, or 'all'.{RESET}")

    while True:
        try:
            raw = input("  Your selection: ").strip().lower()
        except EOFError:
            raw = "all"

        if raw in ("all", "a", ""):
            return list(range(1, len(options) + 1))

        selected = set()
        valid = True
        for part in raw.replace(" ", "").split(","):
            if "-" in part:
                bounds = part.split("-", 1)
                try:
                    lo, hi = int(bounds[0]), int(bounds[1])
                    if 1 <= lo <= hi <= len(options):
                        selected.update(range(lo, hi + 1))
                    else:
                        valid = False; break
                except ValueError:
                    valid = False; break
            else:
                try:
                    n = int(part)
                    if 1 <= n <= len(options):
                        selected.add(n)
                    else:
                        valid = False; break
                except ValueError:
                    valid = False; break

        if valid and selected:
            return sorted(selected)

        print(f"  Invalid input. Please try again (e.g. '1,3', '1-4', 'all').")


# ---------------------------------------------------------------------------
# CLI arguments (minimal — interactive prompts handle the main choices)
# ---------------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(
        description="Fetch Vertex AI TPM timeseries from Cloud Monitoring and generate CSVs."
    )
    p.add_argument(
        "--project",
        required=True,
        help="GCP project ID to query (e.g. my-gcp-project).",
    )
    p.add_argument(
        "--out-dir",
        default=".",
        help="Directory to write CSV files into (default: current directory).",
    )
    p.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port the app is being served on (default: 8080, Cloud Shell Web Preview port).",
    )
    p.add_argument(
        "--no-server",
        action="store_true",
        help="Skip printing localhost URLs.",
    )
    return p.parse_args()


# ---------------------------------------------------------------------------
# Cloud Monitoring fetch
# ---------------------------------------------------------------------------

def sanitize_filename(model_id: str) -> str:
    """Turn a model_id string into a safe filename fragment."""
    return re.sub(r"[^a-zA-Z0-9_\-]", "_", model_id)


def fetch_timeseries(project_id: str, start_dt: datetime, end_dt: datetime) -> dict:
    """
    Query Cloud Monitoring and return a dict:
        { model_id: [ (datetime_utc, tpm_float), ... ] }

    Tokens are summed (input + output) per 1-minute window, grouped by model.
    """
    try:
        from google.cloud import monitoring_v3
        from google.protobuf.duration_pb2 import Duration
    except ImportError:
        print(
            "\nERROR: google-cloud-monitoring is not installed.\n"
            "       Run:  pip install google-cloud-monitoring\n",
            file=sys.stderr,
        )
        sys.exit(1)

    client = monitoring_v3.MetricServiceClient()
    project_name = f"projects/{project_id}"

    interval = monitoring_v3.TimeInterval(
        {
            "end_time":   {"seconds": int(end_dt.timestamp()),   "nanos": 0},
            "start_time": {"seconds": int(start_dt.timestamp()), "nanos": 0},
        }
    )

    aggregation = monitoring_v3.Aggregation(
        {
            "alignment_period": Duration(seconds=ALIGNMENT_PERIOD_SECONDS),
            "per_series_aligner":   monitoring_v3.Aggregation.Aligner.ALIGN_SUM,
            "cross_series_reducer": monitoring_v3.Aggregation.Reducer.REDUCE_SUM,
            # One time-series per model
            "group_by_fields": ["resource.label.model_id"],
        }
    )

    filter_str = f'metric.type = "{METRIC_TYPE}"'

    duration_desc = _duration_desc(end_dt - start_dt)
    print(
        f"\n  Querying Cloud Monitoring for project '{BOLD}{project_id}{RESET}'\n"
        f"  Period : {start_dt.strftime('%Y-%m-%d %H:%M')} → "
        f"{end_dt.strftime('%Y-%m-%d %H:%M')} UTC  ({duration_desc})\n"
        f"  Granularity : 1-minute buckets\n"
    )

    results = client.list_time_series(
        request={
            "name":        project_name,
            "filter":      filter_str,
            "interval":    interval,
            "view":        monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
            "aggregation": aggregation,
        }
    )

    model_data: dict[str, list[tuple[datetime, float]]] = {}

    debug_printed = False
    for ts in results:
        # Debug: print all available labels on the first time series
        if not debug_printed:
            print(f"  {DIM}DEBUG — Resource type: {ts.resource.type}{RESET}")
            print(f"  {DIM}DEBUG — Resource labels: {dict(ts.resource.labels)}{RESET}")
            print(f"  {DIM}DEBUG — Metric type: {ts.metric.type}{RESET}")
            print(f"  {DIM}DEBUG — Metric labels: {dict(ts.metric.labels)}{RESET}")
            debug_printed = True

        # Try multiple label locations for the model identifier
        model_id = (
            ts.resource.labels.get("model_id")
            or ts.metric.labels.get("model_id")
            or ts.resource.labels.get("model_name")
            or ts.metric.labels.get("model_name")
            or ts.resource.labels.get("publisher_model")
            or "unknown_model"
        )
        for point in ts.points:
            # point.interval.end_time is a DatetimeWithNanoseconds (datetime subclass)
            dt = point.interval.end_time.replace(tzinfo=timezone.utc)
            # value may be int64 or double depending on the aggregation
            value = float(point.value.int64_value or point.value.double_value or 0)
            model_data.setdefault(model_id, []).append((dt, value))

    for mid in model_data:
        model_data[mid].sort(key=lambda x: x[0])

    return model_data


def _duration_desc(delta: timedelta) -> str:
    hours = int(delta.total_seconds() // 3600)
    if hours <= 24:
        return f"{hours}h"
    days = delta.days
    if days <= 7:
        return f"{days} days"
    weeks = days // 7
    return f"{weeks} week{'s' if weeks > 1 else ''}"


# ---------------------------------------------------------------------------
# CSV writing
# ---------------------------------------------------------------------------

def write_csv(label: str, points: list, out_dir: str) -> str:
    """Write a CSV file and return its path."""
    os.makedirs(out_dir, exist_ok=True)
    filename = f"tpm_{sanitize_filename(label)}.csv"
    filepath = os.path.join(out_dir, filename)

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["time", "tpm"])
        for dt, tpm in points:
            writer.writerow([dt.strftime("%Y-%m-%dT%H:%M:%SZ"), int(tpm)])

    return filepath


def merge_points(all_points: list[list[tuple]]) -> list[tuple]:
    """
    Merge multiple per-model point lists by timestamp, summing TPM values.
    Returns a sorted list of (datetime, tpm).
    """
    combined: dict[datetime, float] = {}
    for points in all_points:
        for dt, tpm in points:
            combined[dt] = combined.get(dt, 0.0) + tpm
    return sorted(combined.items())


# ---------------------------------------------------------------------------
# URL printing
# ---------------------------------------------------------------------------

def print_app_urls(generated_files: list[tuple[str, str]], port: int):
    print()
    _separator("═")
    print(f"  {BOLD}{GREEN}LOAD IN GEMINI COST OPTIMIZER{RESET}")
    _separator("═")
    print(
        f"\n  {DIM}Make sure the app is served from the repo root:{RESET}\n\n"
        f"      python3 -m http.server {port}\n\n"
        f"  Then click a link below in the Cloud Shell Web Preview:\n"
    )
    for label, filepath in generated_files:
        try:
            rel = os.path.relpath(filepath)
        except ValueError:
            rel = filepath
        encoded = rel.replace(" ", "%20")
        url = f"http://localhost:{port}/?file={encoded}"
        print(f"  {BOLD}[{label}]{RESET}")
        print(f"  {CYAN}{url}{RESET}\n")

    print(
        f"  {DIM}TIP: If the Web Preview rewrites the port, use 'Change Port'\n"
        f"  (top-right of the preview window) and select port {port}.{RESET}\n"
    )
    _separator("═")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

TIMEFRAME_OPTIONS = [
    ("Last 24 hours",  timedelta(hours=24)),
    ("Last week",      timedelta(days=7)),
    ("Last month",     timedelta(days=30)),
    ("Last 3 months",  timedelta(days=90)),
]


def main():
    args = parse_args()

    print(f"\n{BOLD}{CYAN}  Gemini Cost Optimizer — TPM Data Fetcher{RESET}")
    print(f"  Project: {BOLD}{args.project}{RESET}")

    # ── Step 1: Timeframe ────────────────────────────────────────────────────
    tf_idx = prompt_choice(
        "Step 1 of 2 — Select timeframe",
        [label for label, _ in TIMEFRAME_OPTIONS],
        default=3,  # "Last month" pre-selected
    )
    tf_label, tf_delta = TIMEFRAME_OPTIONS[tf_idx - 1]

    end_dt   = datetime.now(timezone.utc)
    start_dt = end_dt - tf_delta

    print(f"\n  {GREEN}✓{RESET} Timeframe: {BOLD}{tf_label}{RESET}")

    # ── Fetch all model data ─────────────────────────────────────────────────
    model_data = fetch_timeseries(args.project, start_dt, end_dt)

    if not model_data:
        print(
            "\nNo data returned. Possible reasons:\n"
            "  • The project has no Vertex AI generative model usage in the requested period.\n"
            "  • Your account lacks the 'roles/monitoring.viewer' IAM role.\n"
            "  • Try a longer timeframe.\n",
            file=sys.stderr,
        )
        sys.exit(1)

    sorted_models = sorted(model_data.keys())
    total_tokens  = {m: int(sum(tpm for _, tpm in model_data[m])) for m in sorted_models}

    def _fmt_tokens(n: int) -> str:
        """Human-readable token count: B / M / K."""
        if n >= 1_000_000_000:
            return f"{n / 1_000_000_000:.2f} B tokens"
        if n >= 1_000_000:
            return f"{n / 1_000_000:.1f} M tokens"
        if n >= 1_000:
            return f"{n / 1_000:.1f} K tokens"
        return f"{n:,} tokens"

    print(f"\n  Found {BOLD}{len(sorted_models)}{RESET} model(s) with data:\n")
    for m in sorted_models:
        print(f"    • {m}  {DIM}({_fmt_tokens(total_tokens[m])}){RESET}")

    # ── Step 2a: Which models? (multi-select, all pre-selected by default) ────
    model_menu_options = [
        f"{m}  {DIM}({_fmt_tokens(total_tokens[m])}){RESET}"
        for m in sorted_models
    ]

    sel_idx = prompt_multi_choice(
        "Step 2 of 2 — Select models  (one CSV per model)",
        model_menu_options,
    )
    selected_models = [sorted_models[i - 1] for i in sel_idx]

    print(f"\n  {GREEN}✓{RESET} Selected {BOLD}{len(selected_models)}{RESET} model(s)")

    # ── Step 2b: Also generate a combined CSV? ────────────────────────────────
    combine = False
    if len(selected_models) > 1:
        print()
        _separator()
        print(f"{BOLD}{CYAN}Also generate a combined CSV? (all selected models merged){RESET}")
        _separator()
        print(f"  {BOLD}1{RESET}. No  — individual CSVs only")
        print(f"  {BOLD}2{RESET}. Yes — also write tpm_all_models.csv")
        _separator()
        while True:
            try:
                raw = input("  Enter choice [1–2] (default 1): ").strip()
                if raw in ("", "1"):
                    combine = False
                    break
                if raw == "2":
                    combine = True
                    break
                print("  Please enter 1 or 2.")
            except EOFError:
                break

    print()

    # ── Write CSVs ───────────────────────────────────────────────────────────
    generated_files: list[tuple[str, str]] = []

    for m in selected_models:
        fp = write_csv(m, model_data[m], args.out_dir)
        generated_files.append((m, fp))
        print(f"  {GREEN}✓{RESET}  {m}  →  {fp}  ({_fmt_tokens(total_tokens[m])})")

    if combine:
        points         = merge_points([model_data[m] for m in selected_models])
        combined_total = sum(total_tokens[m] for m in selected_models)
        fp             = write_csv("all_models", points, args.out_dir)
        generated_files.append(("all_models", fp))
        print(f"  {GREEN}✓{RESET}  {BOLD}all_models{RESET}  →  {fp}  ({_fmt_tokens(combined_total)})")

    # ── Print app URLs ────────────────────────────────────────────────────────
    if not args.no_server:
        print_app_urls(generated_files, args.port)


if __name__ == "__main__":
    main()
