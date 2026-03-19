# Gemini Models Preset Specification

This document defines the preset configurations for Gemini models on Vertex AI to pre-populate the calculator settings.

## Model Presets

### 1. Gemini 3.1 Pro (Preview)
*   `standard paygo rate: input`: $2.00
*   `standard paygo rate: output`: $12.00
*   `max TPM Standard PayGo capacity`: 10000000
*   `tpm per gsu`: 30000
*   `gsu cost / month`: 2000
*   `priority multiplier`: 1.8
*   `max TPM Priority PayGocapacity`: 4000000

---

### 2. Gemini 3 Flash (Preview)
*   `standard paygo rate: input`: $0.50
*   `standard paygo rate: output`: $3.00
*   `max TPM Standard PayGo capacity`: 40000000
*   `tpm per gsu`: 120000
*   `gsu cost / month`: 2000
*   `priority multiplier`: 1.8
*   `max TPM Priority PayGocapacity`: 16000000

---

### 3. Gemini 3.1 Flash-Lite (Preview)
*   `standard paygo rate: input`: $0.25
*   `standard paygo rate: output`: $1.50
*   `max TPM Standard PayGo capacity`: 80000000
*   `tpm per gsu`: 240000
*   `gsu cost / month`: 2000
*   `priority multiplier`: 1.8
*   `max TPM Priority PayGocapacity`: 32000000

---

## Derivation Notes
*   **Pricing**: Sourced from Vertex AI public rates for Gemini 3 / 3.1 models.
*   **Scale Units (GSU)**: Since exact GSU burndown rates for preview models vary, TPM capacity limits for Flash variants are scaled proportionally from the Pro base (30,000 TPM/GSU) to maintain cost-efficiency parity relative to standard pricing.
