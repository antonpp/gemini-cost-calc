import pandas as pd
import matplotlib.pyplot as plt

# Read the CSV data
df = pd.read_csv('example_data.csv')

# Convert 'time' column to datetime objects
df['time'] = pd.to_datetime(df['time'])

# Sort by time to ensure correct plotting
df = df.sort_values(by='time')

import matplotlib.ticker as mticker

# Optimal GSU Threshold
optimal_tpm_threshold = 102 * (500 * 60)

# Create the plot
fig, ax = plt.subplots(figsize=(12, 6))
ax.plot(df['time'], df['tpm'], label='Actual TPM')
ax.axhline(y=optimal_tpm_threshold, color='r', linestyle='--', label=f'Optimal GSU Threshold ({optimal_tpm_threshold:,.0f} TPM)')

# Format y-axis to millions
formatter = mticker.FuncFormatter(lambda x, pos: f'{x/1_000_000:.1f}M')
ax.yaxis.set_major_formatter(formatter)

plt.xlabel('Time')
plt.ylabel('TPM (Millions)')
plt.title('TPM Values Over Time with Optimal GSU Threshold')
plt.grid(True)
plt.legend()
plt.tight_layout()


# Save the plot as a PNG image
plt.savefig('tpm_with_threshold_plot.png')

print("Plot generated successfully and saved as 'tpm_with_threshold_plot.png'")
