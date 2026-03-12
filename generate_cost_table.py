
import pandas as pd

# Load the data from the CSV file
df = pd.read_csv('example_data.csv')

# Convert 'time' column to datetime objects
df['time'] = pd.to_datetime(df['time'])

# Calculate tokens per 5-minute bucket
df['tokens_per_bucket'] = df['tpm'] * 5

# Global parameters for cost calculation
tpm_per_gsu = 500 * 60  # 500 tokens/sec * 60 seconds/min = 30,000 TPM per GSU
gsu_cost_per_month = 2000
input_token_cost_per_million = 2
output_token_cost_per_million = 12
input_token_percentage = 0.96
output_token_percentage = 0.04
payg_priority_multiplier = 1.8

def calculate_costs_for_gsu(gsu_units, dataframe, tpm_per_gsu_val):
    # Calculate TPM threshold for the current GSU
    current_tpm_threshold = gsu_units * tpm_per_gsu_val

    # Calculate spilled TPM for each row
    spilled_tpm_loop = dataframe['tpm'].apply(lambda x: max(0, x - current_tpm_threshold))
    total_spilled_tokens_loop = (spilled_tpm_loop * 5).sum()
    total_spilled_tokens_in_billions_loop = total_spilled_tokens_loop / 1_000_000_000

    # Calculate PT Utilization Rate
    # Calculate the utilized tokens within the provisioned capacity for each bucket
    utilized_provisioned_tpm_loop = dataframe['tpm'].apply(lambda x: min(x, current_tpm_threshold))
    total_utilized_provisioned_tokens_loop = (utilized_provisioned_tpm_loop * 5).sum()

    # Calculate the total available provisioned tokens over the entire period
    total_available_provisioned_tokens_loop = current_tpm_threshold * 5 * len(dataframe)

    # Avoid division by zero if no provisioned capacity
    if total_available_provisioned_tokens_loop > 0:
        pt_utilization_rate_loop = (total_utilized_provisioned_tokens_loop / total_available_provisioned_tokens_loop) * 100
    else:
        pt_utilization_rate_loop = 0.0 # No provisioned capacity, so 0% utilization

    # Calculate costs for the current GSU level
    provisioned_cost_loop = gsu_units * gsu_cost_per_month

    spilled_input_tokens_loop = total_spilled_tokens_loop * input_token_percentage
    spilled_output_tokens_loop = total_spilled_tokens_loop * output_token_percentage
    
    payg_cost_loop = (((spilled_input_tokens_loop / 1_000_000) * input_token_cost_per_million) + \
                    ((spilled_output_tokens_loop / 1_000_000) * output_token_cost_per_million)) * payg_priority_multiplier
                    
    total_combined_cost_loop = provisioned_cost_loop + payg_cost_loop


    return {
        'GSU': gsu_units,
        'TPM Thresh.': current_tpm_threshold,
        'PT Cost': provisioned_cost_loop,
        'PT Util.': pt_utilization_rate_loop,
        'Spilled (B)': total_spilled_tokens_in_billions_loop,
        'PayGo Prio. Cost': payg_cost_loop,
        'Total Cost': total_combined_cost_loop
    }

# Define GSU values for the table
gsu_values = [20, 24, 50, 102, 150] # Include current, optimal, and some surrounding values

results = []
for gsu in gsu_values:
    results.append(calculate_costs_for_gsu(gsu, df, tpm_per_gsu))

# Create a DataFrame for better display
results_df = pd.DataFrame(results)

# Format currency columns
results_df['PT Cost'] = results_df['PT Cost'].map('${:,.0f}'.format)
results_df['PayGo Prio. Cost'] = results_df['PayGo Prio. Cost'].map('${:,.0f}'.format)
results_df['Total Cost'] = results_df['Total Cost'].map('${:,.0f}'.format)
results_df['PT Util.'] = results_df['PT Util.'].map('{:.2f}%'.format)
results_df['TPM Thresh.'] = results_df['TPM Thresh.'].map('{:,.0f}'.format)
results_df['Spilled (B)'] = results_df['Spilled (B)'].map('{:,.2f}'.format)




# Calculate the total number of tokens for the entire period
total_tokens_for_period = df['tokens_per_bucket'].sum()
total_tokens_in_billions_for_period = total_tokens_for_period / 1_000_000_000


print("\n--- Cost Parameters and Data Summary ---")
print(f"Total Tokens for the period: {total_tokens_in_billions_for_period:.2f} Billions")
print(f"TPM per GSU: {tpm_per_gsu:,.0f} tokens/minute")
print(f"GSU Cost per month: ${gsu_cost_per_month:,.0f}")
print(f"Input Token Cost per million: ${input_token_cost_per_million:,.0f}")
print(f"Output Token Cost per million: ${output_token_cost_per_million:,.0f}")
print(f"Input Token Percentage: {input_token_percentage:.0%}")
print(f"Output Token Percentage: {output_token_percentage:.0%}")
print(f"Pay-as-you-go Priority Multiplier: {payg_priority_multiplier:.1f}x")
print(f"GSU Units compared in table: {gsu_values}")


print("\n--- GSU Cost Comparison Table ---\n")
print(results_df.to_markdown(index=False))
