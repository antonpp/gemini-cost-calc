# Specification: Gemini Cost Calculator App (`geminicostcalc.spec.md`)

This specification outlines the design and functionality for a single-page web application to analyze LLM token usage timeseries and calculate optimal Provisioned Throughput (GSU) configurations for cost efficiency on Gemini Vertex AI.

## 1. Application Overview

**Goal**: A client-side web dashboard where users drag-and-drop a CSV file containing TPM (Tokens Per Minute) timeseries data to view interactive graphs and a cost breakdown table comparing Provisioned Throughput (GSU) vs Pay-as-you-go Pricing.

**Philosophy**: No backend processing. All data remains local in the browser for privacy and speed.

---

## 2. Technology Stack

*   **Structure**: HTML5 Semantic Elements.
*   **Styling**: Vanilla CSS3.
*   **Logic**: Vanilla JavaScript (ES6+).
*   **Third-party Libraries (loaded via CDN)**:
    *   **PapaParse**: For robust client-side CSV parsing.
    *   **Chart.js**: For rendering the timeseries line chart with threshold annotations.
    *   **FontAwesome (Optional)**: For rich UI icons.
    *   **Google Fonts**: 'Inter' or 'Outfit' for modern typography.

---

## 3. Design & Aesthetics

The application SHOULD look extremely premium, adopting a "Glassmorphic Dashboard" aesthetic:

*   **Theme**: Dark Mode default (Deep slate/navy background with subtle radial gradients).
*   **Cards/Panels**: Translucent backgrounds (`rgba(...)`) with slight backdrop blur (`backdrop-filter: blur()`) and safe borders.
*   **Color Palette**:
    *   Background: `#0B0F19`
    *   Surface: Linear-gradients transitioning to `rgba(30, 41, 59, 0.5)`.
    *   Accent (Actual TPM): Cyan/Blue gradient (`#22D3EE` to `#3B82F6`).
    *   Accent (Threshold): Red/Coral dashed line (`#F87171`).
*   **Typography**: Clean sans-serif weights, legible sizing, well-spaced values.
*   **Animations**: Micro-transitions on hover for parameter inputs and buttons. Smooth animations when dataset updates.

---

## 4. UI Layout & Wireframe

### Header
-   **Title**: `Gemini Cost Optimizer`
-   **Subtitle**: `Analyze TPM usage to find your optimal Provisioned Throughput setup`

### Main Layout (Grid or Flex)

#### **Panel A: Configuration & Upload (Left or Top)**
1.  **Drop Zone**: Large, dashed border box with icon for direct drag-and-drop integration. Alternatively, a "Select File" button.
2.  **Parameters Form**:
    *   `TPM per GSU` (e.g., slider/input, default: 30,000)
    *   `GSU Cost / Month` (e.g., slider/input, default: $2,000)
    *   `Input Token Cost per M` (e.g., input, default: $2.00)
    *   `Output Token Cost per M` (e.g., input, default: $12.00)
    *   `Input/Output ratio Split` (e.g., slider for percentage inputs, default 96/4)
    *   `PayGo Multiplier` (e.g., slider, default 1.8x)

#### **Panel B: Interactive Chart (Right or Center)**
-   Line chart plotting `tpm` on the Y-axis vs `time` on the X-axis.
-   Horizontal dashed line showing the **Selected/Optimal GSU Threshold** capacity.
-   Responsive scaling with time-axis formatting (Hour/Date support).

#### **Panel C: Cost Breakdown Summary & Table (Bottom)**
1.  **Metric Cards**:
    *   Total Tokens calculated.
    *   Optimal GSU count (suggested).
    *   Estimated total monthly cost (Optimal vs pure PayGo).
2.  **Comparison Grid/Table**:
    *   Columns: `GSU Units`, `TPM Threshold`, `PT Capacity Cost`, `PT Utilization %`, `Spillover (Tokens)`, `PayGo Cost`, `Total Expected Cost`.
    *   Highlight the row corresponding to the minimum `Total Expected Cost`.

---

## 5. Functional Requirements (Logic Flow)

### A. Data Consumption
1.  Trigger standard listener on `dragover`/`drop` or `.csv` upload inputs.
2.  Pass data buffer into `Papa.parse`.
3.  **Validation**: Verify headers `time` and `tpm` are present.
4.  **Parsing**: Convert strings: `tpm` to Float, `time` to Datetime (JS objects).
5.  **Resolution Detection**: Analyze intervals between consecutive timestamps to determine bucket duration $M$ (minutes). Support dynamic resolutions (e.g., 1 min, 5 min, 10 min). Minimum supported duration is 1 minute.


### B. Analytical Calculations
1.  **Bucket Aggregation**: Calculate tokens using the detected interval $M$ (in minutes): `tokens_per_bucket = TPM * M`.
2.  **Simulation Loop**:
    *   Accept a range of GSU candidates (e.g., presets: 20, 50, 100, or a list generated dynamically centered around the mean).
    *   For each GSU value:
        *   `threshold = GSU_Units * TPM_per_GSU`.
        *   Calculate Spillover: `sum(max(0, row.tpm - threshold) * M)`.
        *   Calculate Provisioned Used: `sum(min(row.tpm, threshold) * M)`.
        *   Calculate PT Util rate: `USED / TOTAL_AVAILABLE`.
        *   Compute Month-based costs equivalent to **generate_cost_table.py**.

> [!TIP]
> **Efficient Porting to JS (Single-Page App)**
> *   **One-time Aggregation**: Calculate `total_tokens` and pre-calculate `tokens_per_bucket` (row.tpm * M) ONCE during CSV parse instead of every loop execution for sliders/GSU count.

> *   **Single-Pass Simulator Tooling**: Standard JS `Array.prototype.reduce` is extremely fast for dataset sizes `<10k` rows. Avoid rendering or DOM updates *inside* loops.
> *   **Reactivity**: Trigger loop simulation only on parameter inputs (parameters trigger calculation updates quickly).


---

## 6. Verification Criteria

*   **Static Rendering**: App loads within a single static HTML render without throwing layout-breaking Node errors or script omissions.
*   **Sample Load**: Drop loaded `example_data.csv` generates a non-null dataset, updates numbers, and plots correctly on the Chart overlay immediately.
*   **Parameter Sensitivity**: Adjusting any slider pushes a calculated response to the Data Table outputs concurrently.

---

## 7. Reference Implementations

The application logic replicates calculations verified in existing Python scripts within the repository:
*   `generate_cost_table.py`: Defines the exact table metrics, default multipliers, and arithmetic used for Provisioned Throughput cost comparisons vs Pay-as-you-go Spillover calculations.
*   `plot_with_threshold.py`: Displays visual mapping of Threshold line overlays on token timeseries aggregates.
*   **Ground Truth Values**: Code behavior MUST replicate the output formats verified when testing natively with `example_data.csv`.
