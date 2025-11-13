import os
import glob
import json
from typing import Dict, List, Set, Tuple
from pathlib import Path
import pandas as pd

from vlan_comparison_req1_2 import (
    OUTPUT_DIR, ZONES, read_vlan_data, read_interface_vrf_data_for_zone,
    compare_zone_vlans_tor_vs_cor, safe_sheet_name, results_to_dataframe
)

# Switch groups
switch_types = {
    "DC2_Core": ["TU-NSW-DC2-L0-SW-COR-PRD-01", "TU-NSW-DC2-L0-SW-COR-PRD-02"],
    "DC2_TOR_MGT": [f"TU-NSW-DC2-L0-SW-TOR-MGT-0{i}" for i in range(1, 10)],
    "DC2_TOR_PRD": [
        "TU-NSW-DC2-L0-SW-TOR-PRD-01", "TU-NSW-DC2-L0-SW-TOR-PRD-02",
        "TU-NSW-DC2-L0-SW-TOR-PRD-03", "TU-NSW-DC2-L0-SW-TOR-PRD-04",
        "TU-NSW-DC2-L0-SW-TOR-PRD-05", "TU-NSW-DC2-L0-SW-TOR-PRD-06",
        "TU-NSW-DC2-L0-SW-TOR-PRD-07", "TU-NSW-DC2-L0-SW-TOR-PRD-09",
        "TU-NSW-DC2-L0-SW-TOR-PRD-10"
    ],
    "DC1_Core": ["TU-VIC-DC1-L0-SW-COR-PRD-01", "TU-VIC-DC1-L0-SW-COR-PRD-02"],
    "DC1_TOR_MGT": [f"TU-VIC-DC1-L0-SW-TOR-MGT-0{i}" for i in range(1, 6)],
    "DC1_TOR_PRD": [
        "TU-VIC-DC1-L0-SW-TOR-PRD-01", "TU-VIC-DC1-L0-SW-TOR-PRD-02",
        "TU-VIC-DC1-L0-SW-TOR-PRD-03", "TU-VIC-DC1-L0-SW-TOR-PRD-04",
        "TU-VIC-DC1-L0-SW-TOR-PRD-05", "TU-VIC-DC1-L0-SW-TOR-PRD-06",
        "TU-VIC-DC1-L0-SW-TOR-PRD-07"
    ]
}


def transform_for_excel(results: List[Dict[str, object]]) -> pd.DataFrame:
    """
    Build transposed DataFrame:
    - Switches as columns
    - Rows: Has_VLANs, Missing_VLANs
    - COR switches use COR_ALL_DC comparison results
    """
    tor_entries = [r for r in results if r["Switch_Type"] in ("TOR_PRD", "TOR_MGT")]
    cor_entries = [r for r in results if r["Switch_Type"] == "COR_ALL_DC"]

    filtered = tor_entries + cor_entries
    transposed = {"Has_VLANs": {}, "Missing_VLANs": {}}

    for entry in filtered:
        switch = entry["Switch"]
        transposed["Has_VLANs"][switch] = ", ".join(entry["Has_VLANs"]) if entry["Has_VLANs"] else ""
        transposed["Missing_VLANs"][switch] = ", ".join(entry["Missing_VLANs"]) if entry["Missing_VLANs"] else ""

    return pd.DataFrame.from_dict(transposed, orient="index")

from typing import Dict, List

def build_transposed_zone_df(comparison_results: List[Dict[str, object]]) -> pd.DataFrame:
    """
    Given the 'results' list of dicts (from compare_zone_vlans_tor_vs_cor),
    build a DataFrame with rows ['Has_VLANs','Missing_VLANs'] and columns as switch names.
    Cell values are comma-separated VLAN lists.
    """
    # Keep switch order as encountered in results (no de-dup expected from your generator)
    switches = [r["Switch"] for r in comparison_results]

    # Create the transposed shape
    transposed_df = pd.DataFrame(index=["Has_VLANs", "Missing_VLANs"], columns=switches)

    # Fill values
    for r in comparison_results:
        sw = r["Switch"]
        has_list = r.get("Has_VLANs", [])
        miss_list = r.get("Missing_VLANs", [])

        has_str = ", ".join(map(str, has_list)) if has_list else ""
        miss_str = ", ".join(map(str, miss_list)) if miss_list else ""

        transposed_df.at["Has_VLANs", sw] = has_str
        transposed_df.at["Missing_VLANs", sw] = miss_str

    return transposed_df


def write_transposed_consolidated_workbook(
    out_dir: Path = OUTPUT_DIR,
    out_filename: str = "zone_vlan_comparison_formatted.xlsx",
) -> Path:
    """
    Build the transposed, consolidated workbook directly from live 'results' — one sheet per zone.
    Uses your existing data readers and compare functions, so it does not read the earlier Excel.
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    vlan_data = read_vlan_data()
    transposed_per_zone: Dict[str, pd.DataFrame] = {}

    for zone in ZONES:
        print(f"\n### Building transposed output for zone: {zone} ###")
        zone_vrf_data = read_interface_vrf_data_for_zone(zone)
        if not zone_vrf_data:
            print(f"No VRF data found for zone: {zone}")
            continue

        # Get the original results list for the zone
        comparison_results = compare_zone_vlans_tor_vs_cor(vlan_data, zone_vrf_data, zone)

        # Build the transposed DF for this zone
        transposed_per_zone[zone] = build_transposed_zone_df(comparison_results)

    # Write consolidated workbook with one sheet per zone
    out_path = out_dir / out_filename
    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        for zone, df in transposed_per_zone.items():
            sheet = safe_sheet_name(zone)
            df.to_excel(writer, index=True, sheet_name=sheet)

    print(f"\n✓ Saved transposed consolidated workbook to {out_path}")
    return out_path


def main(out_dir: Path = OUTPUT_DIR,
         save_per_zone: bool = True,
         save_consolidated: bool = True,
         save_transposed: bool = True):
    # Ensure output directory exists
    out_dir.mkdir(parents=True, exist_ok=True)

    vlan_data = read_vlan_data()

    print("\n" + "=" * 60)
    print("=== Processing Zones Separately ===")
    print("=" * 60)
    print(f"Zones to process: {', '.join(ZONES)}")

    # For consolidated workbook (if enabled)
    zone_dfs: Dict[str, pd.DataFrame] = {}

    # Process each zone separately
    for zone in ZONES:
        print(f"\n{'#' * 60}")
        print(f"### Processing Zone: {zone} ###")
        print(f"{'#' * 60}")

        # Read VRF data for this specific zone
        zone_vrf_data = read_interface_vrf_data_for_zone(zone)
        if not zone_vrf_data:
            print(f"No VRF data found for zone: {zone}")
            continue
        print(f"Found {len(zone_vrf_data)} switches with {zone} VRFs")

        # Save VRF data for this zone (JSON)
        zone_filename = zone.replace("-", "").lower()
        vrf_json_filename = out_dir / f"{zone_filename}_vrf_data.json"
        with open(vrf_json_filename, "w") as f:
            json.dump(zone_vrf_data, f, indent=4)
        print(f"Saved {zone} VRF data to {vrf_json_filename}")

        # Compare VLANs for this zone
        comparison_results = compare_zone_vlans_tor_vs_cor(vlan_data, zone_vrf_data, zone)

        # Save comparison results to JSON
        comparison_json_filename = out_dir / f"{zone_filename}_vlan_comparison.json"
        with open(comparison_json_filename, "w") as f:
            json.dump(comparison_results, f, indent=4)
        print(f"✓ Saved {zone} comparison results to {comparison_json_filename}")

        # Convert to DataFrame
        df = results_to_dataframe(comparison_results)

        # Save per-zone Excel
        if save_per_zone:
            excel_filename = out_dir / f"{zone_filename}_vlan_comparison.xlsx"
            df.to_excel(excel_filename, index=False)
            print(f"✓ Saved {zone} comparison results to {excel_filename}")

        # Accumulate for consolidated workbook
        if save_consolidated:
            zone_dfs[zone] = df

    # Write consolidated workbook with one sheet per zone (optional)
    if save_consolidated and zone_dfs:
        consolidated_path = out_dir / "zone_vlan_comparison_formatted.xlsx"
        with pd.ExcelWriter(consolidated_path, engine="openpyxl") as writer:
            for zone, df in zone_dfs.items():
                sheet = safe_sheet_name(zone)
                df.to_excel(writer, index=False, sheet_name=sheet)
        print(f"\n✓ Saved consolidated workbook to {consolidated_path}")


    if save_transposed:
        write_transposed_consolidated_workbook(out_dir=out_dir,
                                               out_filename="zone_vlan_comparison_formatted.xlsx")

if __name__ == "__main__":
    main()