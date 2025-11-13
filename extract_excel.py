import pandas as pd
import os
from pathlib import Path

# Define the zones and corresponding filenames
zones = {
    "CORPORATE": "corporate_vlan_comparison.csv",
    "EA": "ea_vlan_comparison.csv",
    "ITS": "its_vlan_comparison.csv",
    "MSS": "mss_vlan_comparison.csv"
}

# Define the input and output directories
input_dir = Path("C:/scripts/vlan_script/part_1_results")
output_dir = Path("C:/scripts/vlan_script/part_3_results")
output_file = output_dir / "vlan_summary_by_zone.xlsx"

# Helper function to parse VLAN strings into lists
def parse_vlans(val):
    if pd.isna(val):
        return []
    s = str(val).strip().strip('"').replace(' ', '')
    if not s:
        return []
    parts = [p for p in s.split(',') if p]
    out = []
    for p in parts:
        try:
            out.append(int(p))
        except ValueError:
            out.append(p)
    return out

# Create a Pandas Excel writer
with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
    for zone, filename in zones.items():
        file_path = input_dir / filename
        if not file_path.exists():
            continue
        df = pd.read_csv(file_path)
        df.columns = [c.strip().replace(' ', '_') for c in df.columns]
        df = df.dropna(subset=['Switch'], how='any')
        if 'Has_VLANs' in df.columns:
            df['Has_VLANs'] = df['Has_VLANs'].apply(parse_vlans)
        if 'Missing_VLANs' in df.columns:
            df['Missing_VLANs'] = df['Missing_VLANs'].apply(parse_vlans)
        df.to_excel(writer, sheet_name=zone, index=False)

print(f"Excel file saved to: {output_file}")