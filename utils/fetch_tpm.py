#!/usr/bin/env python3
"""
fetch_tpm.py — Query GCP Cloud Monitoring for Vertex AI token usage and
generate per-model TPM CSV files compatible with the Gemini Cost Optimizer app.

Usage (Cloud Shell):
    python3 utils/fetch_tpm.py --project MY_PROJECT_ID [--port 8080]

Requirements (install in venv):
    pip install -r requirements.txt

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

try:
    import questionary
    from questionary import Style
except ImportError:
    print(
        "\nERROR: 'questionary' is not installed.\n"
        "       Run:  pip install -r requirements.txt\n",
        file=sys.stderr,
    )
    sys.exit(1)

# ---------------------------------------------------------------------------
# Metric constants
# ---------------------------------------------------------------------------
METRIC_TYPE = "aiplatform.googleapis.com/publisher/online_serving/token_count"
ALIGNMENT_PERIOD_SECONDS = 60  # 1-minute buckets

# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------
CYAN  = "\033[96m"
GREEN = "\033[92m"
BOLD  = "\033[1m"
DIM   = "\033[2m"
RESET = "\033[0m"

PROMPT_STYLE = Style([
    ("qmark",       "fg:cyan bold"),
    ("question",    "fg:white bold"),
    ("answer",      "fg:cyan bold"),
    ("pointer",     "fg:cyan bold"),
    ("highlighted", "fg:cyan bold"),
    ("selected",    "fg:green"),
    ("instruction", "fg:#888888"),
])

def _separator(char="─", width=60):
    print(f"{DIM}{char * width}{RESET}")


# ---------------------------------------------------------------------------
# CLI arguments
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
            "       Run:  pip install -r requirements.txt\n",
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

    # Query with only per-series alignment (no cross-series reduction)
    # so all labels are preserved — we need them to identify models.
    discovery_agg = monitoring_v3.Aggregation(
        {
            "alignment_period": Duration(seconds=ALIGNMENT_PERIOD_SECONDS),
            "per_series_aligner": monitoring_v3.Aggregation.Aligner.ALIGN_SUM,
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

    raw_results = client.list_time_series(
        request={
            "name":        project_name,
            "filter":      filter_str,
            "interval":    interval,
            "view":        monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
            "aggregation": discovery_agg,
        }
    )

    # ── Discover model label and collect data ────────────────────────────
    MODEL_LABEL_CANDIDATES = [
        "model_user_id",    # PublisherModel resources
        "model_id", "model_name", "publisher_model", "model",
    ]

    raw_model_data: dict[str, list[tuple[datetime, float]]] = {}
    model_label_field = None
    label_discovered = False

    for ts in raw_results:
        res_labels = dict(ts.resource.labels)
        met_labels = dict(ts.metric.labels)

        if not label_discovered:
            label_discovered = True
            for candidate in MODEL_LABEL_CANDIDATES:
                if candidate in res_labels:
                    model_label_field = ("resource", candidate)
                    break
                if candidate in met_labels:
                    model_label_field = ("metric", candidate)
                    break

        # Extract model name
        if model_label_field:
            src, key = model_label_field
            labels = res_labels if src == "resource" else met_labels
            model_id = labels.get(key, "unknown_model")
        else:
            model_id = "all_models"

        for point in ts.points:
            dt = point.interval.end_time.replace(tzinfo=timezone.utc)
            value = float(point.value.int64_value or point.value.double_value or 0)
            raw_model_data.setdefault(model_id, []).append((dt, value))

    # ── Merge input + output tokens per model per timestamp ──────────────
    model_data: dict[str, list[tuple[datetime, float]]] = {}
    for mid, points in raw_model_data.items():
        merged: dict[datetime, float] = {}
        for dt, val in points:
            # Round to nearest minute to ensure reliable mapping
            dt_clean = dt.replace(second=0, microsecond=0)
            merged[dt_clean] = merged.get(dt_clean, 0.0) + val
        
        # ── Zero-padding ──
        # Ensure every minute in [start_dt, end_dt] is represented
        padded = []
        curr = start_dt.replace(second=0, microsecond=0)
        # We go up to end_dt (exclusive or inclusive? Usually inclusive for charts)
        # Cloud Monitoring alignment periods usually mean the point at T represents [T-1m, T]
        limit = end_dt.replace(second=0, microsecond=0)
        while curr <= limit:
            val = merged.get(curr, 0.0)
            padded.append((curr, val))
            curr += timedelta(minutes=1)
            
        model_data[mid] = padded

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
# Helpers
# ---------------------------------------------------------------------------

def _fmt_tokens(n: int) -> str:
    """Human-readable token count: B / M / K."""
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.2f}B tokens"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M tokens"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K tokens"
    return f"{n:,} tokens"


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
    """Merge multiple point lists by timestamp, summing TPM values."""
    combined: dict[datetime, float] = {}
    for points in all_points:
        for dt, tpm in points:
            combined[dt] = combined.get(dt, 0.0) + tpm
    return sorted(combined.items())


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

TIMEFRAME_CHOICES = [
    {"name": "Last 24 hours",  "value": timedelta(hours=24)},
    {"name": "Last week",      "value": timedelta(days=7)},
    {"name": "Last month",     "value": timedelta(days=30)},
    {"name": "Last 3 months",  "value": timedelta(days=90)},
]


def main():
    args = parse_args()

    print(f"\n{BOLD}{CYAN}  Gemini Cost Optimizer — TPM Data Fetcher{RESET}")
    print(f"  Project: {BOLD}{args.project}{RESET}\n")

    # ── Step 1: Timeframe ────────────────────────────────────────────────
    tf_delta = questionary.select(
        "Select timeframe:",
        choices=[
            questionary.Choice(c["name"], value=c["value"])
            for c in TIMEFRAME_CHOICES
        ],
        default=timedelta(days=30),
        style=PROMPT_STYLE,
    ).ask()

    if tf_delta is None:
        sys.exit(0)  # user pressed Ctrl+C

    end_dt   = datetime.now(timezone.utc)
    start_dt = end_dt - tf_delta

    # ── Fetch all model data ─────────────────────────────────────────────
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

    print(f"\n  Found {BOLD}{len(sorted_models)}{RESET} model(s) with data:\n")
    for m in sorted_models:
        print(f"    • {m}  {DIM}({_fmt_tokens(total_tokens[m])}){RESET}")
    print()

    # ── Step 2: Model selection (checkbox multi-select) ──────────────────
    model_choices = [
        questionary.Choice(
            f"{m}  ({_fmt_tokens(total_tokens[m])})",
            value=m,
            checked=True,  # all selected by default
        )
        for m in sorted_models
    ]

    selected_models = questionary.checkbox(
        "Select models to export (one CSV per model):",
        choices=model_choices,
        style=PROMPT_STYLE,
        instruction="(↑↓ navigate, Space toggle, Enter confirm)",
    ).ask()

    if selected_models is None:
        sys.exit(0)

    if not selected_models:
        print("  No models selected. Exiting.")
        sys.exit(0)

    print(f"\n  {GREEN}✓{RESET} Selected {BOLD}{len(selected_models)}{RESET} model(s)")

    # ── Step 3: Combined CSV? ────────────────────────────────────────────
    combine = False
    if len(selected_models) > 1:
        combine = questionary.confirm(
            "Also generate a combined CSV (all selected models merged)?",
            default=False,
            style=PROMPT_STYLE,
        ).ask()

        if combine is None:
            sys.exit(0)

    print()

    # ── Write CSVs ───────────────────────────────────────────────────────
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

    # ── Print app URLs ───────────────────────────────────────────────────
    if not args.no_server:
        print_app_urls(generated_files, args.port)


if __name__ == "__main__":
    main()
