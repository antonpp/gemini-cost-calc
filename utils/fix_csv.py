import sys
import csv

def fix_csv(input_path, output_path):
    print(f"Reading {input_path}...")
    try:
        with open(input_path, 'r', newline='', encoding='utf-8') as infile:
            reader = csv.DictReader(infile)
            headers = reader.fieldnames
            print(f"Found headers: {headers}")
            
            if not headers:
                print("Error: Empty headers.")
                sys.exit(1)

            # Mapping rules
            time_col = 'timestamp' if 'timestamp' in headers else 'time'
            tpm_col = 'total_tokens' if 'total_tokens' in headers else 'tpm'

            if time_col not in headers or tpm_col not in headers:
                print(f"Error: Missing required columns. Found: {headers}")
                sys.exit(1)

            rows = []
            for row in reader:
                # Add check for blank/corrupted rows
                if row.get(time_col) is None:
                    continue
                rows.append({
                    'time': row[time_col],
                    'tpm': row[tpm_col]
                })

        print(f"Writing {len(rows)} rows to {output_path}...")
        with open(output_path, 'w', newline='', encoding='utf-8') as outfile:
            writer = csv.DictWriter(outfile, fieldnames=['time', 'tpm'])
            writer.writeheader()
            writer.writerows(rows)
            print("Successfully saved.")

    except Exception as e:
        print(f"Error parsing file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python fix_csv.py <input_path> <output_path>")
        sys.exit(1)
    fix_csv(sys.argv[1], sys.argv[2])
