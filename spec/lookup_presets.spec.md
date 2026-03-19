# Specification: Updating Model Presets

This document instructs an LLM agent on how to look up and update preset configurations in `spec/presets.spec.md` for Gemini models on Vertex AI.

## 1. Source URLs

The following Google Cloud documentation pages should be searched/scraped to find the latest values:

*   **Pricing**: `https://cloud.google.com/vertex-ai/generative-ai/pricing`
    *   *Alternative*: Search for "Vertex AI Generative AI pricing"
*   **Quotas and Limits**: `https://cloud.google.com/vertex-ai/generative-ai/quotas`
    *   *Alternative*: Search for "Vertex AI Gemini quotas TPM"
*   **Provisioned Throughput (GSU)**: `https://cloud.google.com/vertex-ai/generative-ai/provisioned-throughput`
    *   *Alternative*: Pricing page often includes Provisioned Throughput rates.

## 2. Data Points to Collect

For each model (e.g., Gemini 3 Pro, Gemini 3 Flash, Gemini 3 Flash-Lite), collect:

### A. Standard Pay-as-you-go (PayGo) rates
*   `Input Rate`: Cost per 1,000,000 tokens. Note if there are tiering thresholds (e.g., <= 200k vs > 200k tokens).
*   `Output Rate`: Cost per 1,000,000 tokens. Include thinking tokens if applicable.

### B. Priority PayGo (if available)
*   Look for a multiplier (e.g., 1.8x Standard) or explicitly listed rates for Priority tier.
*   If not explicitly stated, fit to existing derivation logic (e.g., assuming historical multipliers if applicable, but prioritize current documentation).

### C. Provisioned Throughput
*   `GSU Cost / Month`: Monthly cost for one Geographic/Global Scale Unit (GSU).
*   `TPM per GSU`: The number of Tokens Per Minute (TPM) capacity provided by 1 GSU for that specific model.

### D. Quota / Capacity Limits
*   `Max TPM Standard PayGo capacity`: Default quota limit for Standard PayGo. Derived from `https://docs.cloud.google.com/vertex-ai/generative-ai/docs/standard-paygo` (use the highest tier, e.g., Tier 3, as the value). If the page is unavailable, search for Vertex AI Standard PayGo capacity.
*   `Max TPM Priority PayGo capacity`: Default quota limit for Priority PayGo. For simplification, use the **same value as `Max TPM Standard PayGo capacity`** (the user can adjust via UI sliders). Note that while Priority PayGo in reality uses ramping logic (see `https://docs.cloud.google.com/vertex-ai/generative-ai/docs/priority-paygo#ramp-limits`), we are simplifying this and **will not be implementing the ramping logic**.

## 3. Execution Steps for Updating Presets

1.  **Read Current Presets**: View `spec/presets.spec.md` to understand the current format and models listed.
2.  **Scrape Pricing Information**:
    *   Navigate to the pricing page.
    *   Locate tables for "Gemini" models.
    *   Extract token pricing for input and output.
3.  **Scrape Quota Information**:
    *   Navigate to the quotas page.
    *   Search for rate limits (TPMs) for Gemini models on Vertex AI.
4.  **Calculate / Deduce missing fields**:
    *   If "Priority PayGo" rates aren't listed, use historical multipliers or note that it is not offered/different.
    *   If "TPM per GSU" requires deduction based on capacity scaling, explicitly document the logic.
5.  **Update `spec/presets.spec.md`**:
    *   Add new models if discovered (e.g., moving from preview to GA, or new releases).
    *   Update existing values with the latest scraped numbers.
    *   Save the updated file.

## 4. Verification

*   The updated `presets.spec.md` must maintain the existing structure.
*   Include a "Derivation Notes" section detailing *when* the lookup occurred and any specific assumptions made during calculation.
