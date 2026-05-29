# Specification: Gemini Cost Calculator App (`geminicostcalc.spec.md`)

This specification outlines the design and functionality for a single-page web application to analyze LLM token usage timeseries and calculate optimal Provisioned Throughput (GSU) configurations for cost efficiency on Gemini Vertex AI.

## 1. Application Overview

**Goal**: A client-side web dashboard where users load a CSV file containing TPM (Tokens Per Minute) timeseries data to view interactive graphs and a cost breakdown table comparing Provisioned Throughput (GSU) vs Pay-as-you-go Pricing.

**Data ingestion paths**:
1. **Drag-and-drop / file picker** — works in any browser environment.
2. **URL parameter `?file=<path>`** — app fetches the CSV from the local HTTP server. Used by `utils/fetch_tpm.py` to generate click-to-load links for Cloud Shell users (where drag-and-drop is unavailable).
3. **`?test=true`** — loads a bundled sample CSV for quick local testing.

**Philosophy**: No backend processing. All analysis runs client-side in the browser — data never leaves the device.

---

## 2. Technology Stack

*   **Structure**: HTML5 Semantic Elements.
*   **Styling**: Vanilla CSS3.
*   **Logic**: Vanilla JavaScript (ES6+).
*   **Third-party Libraries (loaded via CDN)**:
    *   **PapaParse**: For robust client-side CSV parsing.
    *   **Chart.js**: For rendering the timeseries line chart with threshold annotations.
    *   **chartjs-plugin-zoom**: For drag-to-zoom on the timeseries chart.
    *   **FontAwesome**: For UI icons.
    *   **Google Fonts**: 'Outfit' for modern typography.

---

## 3. Design & Aesthetics

The application adopts a "Glassmorphic Dashboard" aesthetic:

*   **Theme**: Dark Mode default (deep slate/navy background with subtle radial gradients).
*   **Cards/Panels**: Translucent backgrounds (`rgba(...)`) with backdrop blur and subtle borders.
*   **Color Palette**:
    *   Background: `#0B0F19`
    *   Surface: Linear-gradients transitioning to `rgba(30, 41, 59, 0.5)`.
    *   Accent (Actual TPM): Cyan/Blue gradient (`#22D3EE` to `#3B82F6`).
    *   Accent (Threshold): Red/Coral dashed line (`#F87171`).
*   **Typography**: Clean sans-serif weights using 'Outfit'.
*   **Animations**: Micro-transitions on hover; loading overlay during calculation.

---

## 4. UI Layout & Wireframe

### Header
-   **Title**: `Gemini Cost Optimizer`
-   **Subtitle**: `Analyze TPM usage to find your optimal Provisioned Throughput setup`

### File-load Banner
Displayed across the full width when `?file=` is present in the URL. Shows the filename being loaded and a status pill: `Loading…` → `✓ Loaded N rows` or an error message.

### Main Layout (two-column grid)

#### **Panel A: Configuration & Upload (Left or Top)**
0.  **Model Preset**: Dropdown at the top to select specific Gemini models and auto-populate all rate/capacity parameters dynamically.
0.1. **CSV Model Filter**: A conditional scrollable checkbox checklist that appears only when the `429-dash-export` format is uploaded, allowing filtering of rows by selecting one or more models to aggregate.
1.  **Drop Zone**: Large, dashed border box with icon for direct drag-and-drop integration. Alternatively, a "Select File" button.
2.  **Parameters Form**:
    *   **Global Layout**: `TPM per GSU`, `GSU Cost / Month`, rates pointers.
    *   **Tiers Config (Toggle Toggles)**:
        *   `Enable PT` layout limits.
        *   `Enable Priority` layout & Priority multiplier sliders.
        *   `Enable Standard` layout bounding frames.
        *   `Max Prio TPM` and `Max Std TPM` continuous bounds sliders headers incorporating absolute `Unlimited` checkboxes overlays natively securely.

#### **Panel B: Interactive Chart & Results (Right or Center)**
-   **Welcome State** (no data loaded): Large drop zone + info cards including a Cloud Shell Quickstart guide.
-   **Active State** (data loaded):
    -   Line chart: `tpm` vs `time`, with dashed threshold lines per enabled tier.
    -   **Secondary Y-Axis Overlays**: For `429-dash-export` files, display actual historical throttled request counts (429s/throttles) aligned with the timeline, rendered as semi-transparent vertical bar spikes only when throttling occurs (zero values are hidden to declutter the chart).
    -   Drag-to-zoom with Reset Zoom button.
    -   Metric cards:
        *   Total Tokens calculated.
        *   Peak TPM.
        *   Optimal GSU count (suggested).
        *   Estimated total monthly cost (Optimal vs pure PayGo).
        *   **Throttled Rate**: The percentage of requests that were throttled (only for `429-dash-export`).
    -   **Breakdowns Section (Collapsible)**: Collapsible cards showing top regions and projects by token volume (only for `429-dash-export`).
    -   GSU Comparison Table.
        *   Columns: `GSU Units`, `TPM Threshold`, `PT Capacity Cost`, `PT Utilization %`, `Spillover (Tokens)`, `PayGo Cost`, `Total Expected Cost`.
        *   Highlight the row corresponding to the minimum `Total Expected Cost`.

---

## 5. Functional Requirements (Logic Flow)

### A. Data Consumption

Data can be loaded via three entry paths:

#### Path 1 — File drag-and-drop / picker
1.  `dragover`/`drop` or `<input type="file">` events trigger `handleFileUpdate(file)`.
2.  File buffer is passed to `Papa.parse`.
3.  **Format Auto-Detection & Validation**:
    *   **Standard**: If headers contain `time` and `tpm`.
    *   **429-dash-export**: If headers contain `large_model_name` and `date_time`.
4.  **Data Processing & Aggregation**:
    *   *Standard*: Parse `tpm` directly and map `time` to Date objects.
    *   *429-dash-export*:
        *   Extract unique model names from `large_model_name` to populate the CSV Model Filter checkbox list.
        *   Filter rows by all selected CSV models.
        *   Sum `input_tokens` and `output_tokens` per `date_time` (converted from microseconds to Date objects) across all selected models.
        *   Sum all request throttling counts.
        *   Compute the median interval $M$ between consecutive sorted timestamps.
        *   Convert to TPM rate: $TPM = (input\_tokens + output\_tokens) / M$.
        *   Auto-tune the Input/Output Split slider based on the total actual input vs output tokens.
        *   Auto-map the selected CSV model to the closest predefined pricing preset.
5.  **Resolution Detection**: Analyze intervals between consecutive timestamps to determine bucket duration $M$ (minutes). Support dynamic resolutions (e.g., 1 min, 5 min, 10 min). Minimum supported duration is 1 minute.

#### Path 2 — URL parameter `?file=<relative-path>`
1.  On `DOMContentLoaded`, read `URLSearchParams`.
2.  If `file` param is present, call `loadFileFromUrl(path)`.
3.  Show the file-load banner with a pulsing `Loading…` status pill.
4.  `fetch(path)` retrieves the CSV from the local HTTP server.
5.  Passes retrieved CSV text to `Papa.parse` and follows the same format auto-detection, validation, parsing, and resolution detection logic as Path 1.
6.  Banner updates to `✓ Loaded N rows` (success) or an error message (failure).

#### Path 3 — `?test=true`
1.  Fetches `my_sample_csv/sample_00.csv` from the local server.
2.  Parses and loads as per Path 1.

### B. Analytical Calculations
1.  **Bucket Aggregation**: `tokens_per_bucket = TPM × M` (computed once at parse time).
2.  **Simulation Sweep**: Grid search over GSU values from 1 to `ceil(peakTPM / tpmPerGSU)`. For each GSU, compute PT cost + Priority PayGo cost + Standard PayGo cost using the waterfall tiering logic defined in [tiering.spec.md](tiering.spec.md).
3.  **Optimal GSU**: The GSU count that minimises total combined cost.

> [!TIP]
> **Performance**: Pre-compute `total_tokens` and `tokens_per_bucket` once at parse time. Use a single `forEach` pass per GSU candidate. Avoid DOM updates inside loops.

---

## 6. GCP Data Pipeline (`utils/fetch_tpm.py`)

This companion script is intended for use in **Google Cloud Shell** to fetch real Vertex AI token usage and generate CSV files directly loadable by the app.

### Metric
`aiplatform.googleapis.com/publisher/online_serving/token_count`

### Behaviour
1.  **Interactive prompt — Timeframe**: User selects Last 24h / Last week / Last month / Last 3 months.
2.  **Fetch**: Queries Cloud Monitoring with 1-minute `ALIGN_SUM` alignment and `REDUCE_SUM` cross-series reduction grouped by `resource.label.model_id`. This sums input + output tokens per model per minute.
3.  **Interactive prompt — Model selection**: Multi-select from discovered models (displayed with total tokens consumed). Optionally generate a merged `tpm_all_models.csv` in addition to per-model files.
4.  **Output**: One CSV per selected model (`tpm_<model_id>.csv`) with `time,tpm` headers at 1-minute granularity.
5.  **Click-to-load URLs**: Prints `http://localhost:<port>/?file=<relative-path>` for each generated file so the user can click to open the app pre-loaded with that model's data.

### Requirements
*   `pip install google-cloud-monitoring`
*   `roles/monitoring.viewer` IAM role on the project.
*   Local HTTP server running from the repo root: `python3 -m http.server 8080`.

---

## 7. Verification Criteria

*   App loads without errors from a static file server (no Node/build step required).
*   Dropping a valid CSV immediately updates the chart and metrics.
*   Opening `?file=tpm_example.csv` (with the server running) loads the file and shows the banner.
*   Adjusting any slider or tier toggle re-runs the simulation and updates the table.

---

## 8. Reference Implementations

*   **[tiering.spec.md](tiering.spec.md)**: Multi-tier waterfall cost arithmetic.
*   **[presets.spec.md](presets.spec.md)**: Per-model rate and capacity presets.
*   **[lookup_presets.spec.md](lookup_presets.spec.md)**: Instructions for updating presets from GCP documentation.
*   **[README.md](../README.md)**: End-user setup and Cloud Shell quickstart guide.
