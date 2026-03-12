# Gemini Cost Calculator App

This application is designed to analyze LLM token usage (tokens per minute) timeseries data to:
1.  Generate interactive timeseries graphs showing TPM (Tokens Per Minute) over time.
2.  Calculate and display cost breakdowns for different Provisioned Throughput (GSU) configurations on Gemini Vertex AI.
3.  Help find the optimal GSU threshold to minimize costs (balancing Provisioned Cost vs Pay-as-you-go Spillover).

## Features
-   **Drag-and-Drop CSV Interface**: Upload your `timestamp_timeseries.csv` file directly in the browser.
-   **Interactive Graphs**: View TPM over time with visual indicators for GSU capacity thresholds.
-   **Dynamic Cost Calculations**: Adjust pricing parameters (GSU cost, input/output token rates) and see calculations update in real-time.
-   **Cost Comparison Table**: Compare multiple GSU levels to find the most cost-effective option.

## Reference Files
-   `generate_cost_table.py`: Original Python script for cost calculations.
-   `plot_with_threshold.py`: Original Python script for visual plotting.
-   `example_data.csv`: Sample dataset for testing.
