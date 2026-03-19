# Gemini Models Preset Specification

This document defines the preset configurations for Gemini models on Vertex AI to pre-populate the calculator settings.

## Model Presets

### 1. Gemini 3.1 Pro (Preview)
*   `standard paygo rate: input`: $2.00
*   `standard paygo rate: output`: $12.00
*   `max TPM Standard PayGo capacity`: 2000000
*   `tpm per gsu`: 30000
*   `gsu cost / month`: 2000
*   `priority multiplier`: 1.8
*   `max TPM Priority PayGocapacity`: 2000000

---

### 2. Gemini 3 Flash (Preview)
*   `standard paygo rate: input`: $0.50
*   `standard paygo rate: output`: $3.00
*   `max TPM Standard PayGo capacity`: 10000000
*   `tpm per gsu`: 120900
*   `gsu cost / month`: 2000
*   `priority multiplier`: 1.8
*   `max TPM Priority PayGocapacity`: 10000000

---

### 3. Gemini 3.1 Flash-Lite (Preview)
*   `standard paygo rate: input`: $0.25
*   `standard paygo rate: output`: $1.50
*   `max TPM Standard PayGo capacity`: 10000000
*   `tpm per gsu`: 241800
*   `gsu cost / month`: 2000
*   `priority multiplier`: 1.8
*   `max TPM Priority PayGocapacity`: 10000000

---

## Derivation Notes
*   **Pricing & Multiplier**: Sourced from Vertex AI public rates (Standard & Priority) for Gemini 3 / 3.1 models.
*   **Scale Units (GSU)**: Calculated from "Per-second throughput per GSU" rates multiplied by 60.
*   **Capacity (Max TPM)**: Sourced from Vertex AI Standard PayGo Baseline Throughput for **Tier 3** spend level ($2000+ rolling 30-day spend).
*   **Simplification**: Priority capacity capped at Standard levels; ramping ignored.
*   **Updated**: 2026-03-19
