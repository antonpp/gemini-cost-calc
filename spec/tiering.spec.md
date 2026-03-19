# Vertex AI Gemini Tiering Logic Specification

This document outlines the theoretical multi-tiered capacity consumption structure deployed for Gemini models on Vertex AI dashboards calculations.

## Consumption Tiers Hierarchy

*   **Global Parameters**: 
    *   Input/Output split (default: 96% input / 4% output)

### Tier 1: Provisioned Throughput (PT)
*   **Cost Type**: Optional. Fixed-term Subscription.
*   **Behavior**: Reserved throughput (TPM/RPM)
*   **Parameters**: 
    *   tpm per gsu (TPM/GSU)
    *   gsu cost / month (USD/GSU/Month)
*   **Spills Over Into**: Tier 2

---

### Tier 2: Priority Pay-as-you-go (Priority PayGo)
*   **Cost Type**: Optional. Priority PayGo rate (priority_multiplier x standard_paygo_rate)
*   **Parameters**: 
    *   priority multiplier (float, default: 1.8)
    *   max TPM Priority PayGocapacity (default: 4M TPM)
*   **Spills Over Into**: Tier 3

---

### Tier 3: Standard Pay-as-you-go (Standard PayGo)
*   **Cost Type**: Optional. Standard rate.
*   **Behavior**: Dynamically sourced shared pool capacity on-demand best-effort.
*   **Parameters**: 
    *   standard paygo rate: input (default: 2$/M tokens)
    *   standard paygo rate: output (default: 12$/M tokens)
    *   max TPM Standard PayGo capacity (default: 10M TPM)
*   **Spills Over Into**: 429 errors

---