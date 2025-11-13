import os
import glob
import json
from typing import Dict, List, Set, Tuple
from collections import Counter
from pathlib import Path

import pandas as pd

OUTPUT_DIR = Path(r"C:\scripts\vlan_script\outputs")

# Define zones to process - each will be processed separately
ZONES = [
    "EA-",
    "MSS",
    "ITS",
    "CORPORATE"
]

# Switch groups
switch_types = {
    "DC2_Core": ["TU-NSW-DC2-L0-SW-COR-PRD-01", "TU-NSW-DC2-L0-SW-COR-PRD-02"],
    "DC2_TOR_MGT": [f"TU-NSW-DC2-L0-SW-TOR-MGT-0{i}" for i in range(1, 10)],
    "DC2_TOR_PRD": [
        "TU-NSW-DC2-L0-SW-TOR-PRD-01", "TU-NSW-DC2-L0-SW-TOR-PRD-02", "TU-NSW-DC2-L0-SW-TOR-PRD-03",
        "TU-NSW-DC2-L0-SW-TOR-PRD-04", "TU-NSW-DC2-L0-SW-TOR-PRD-05", "TU-NSW-DC2-L0-SW-TOR-PRD-06",
        "TU-NSW-DC2-L0-SW-TOR-PRD-07", "TU-NSW-DC2-L0-SW-TOR-PRD-09", "TU-NSW-DC2-L0-SW-TOR-PRD-10"
    ],
    "DC1_Core": ["TU-VIC-DC1-L0-SW-COR-PRD-01", "TU-VIC-DC1-L0-SW-COR-PRD-02"],
    "DC1_TOR_MGT": [f"TU-VIC-DC1-L0-SW-TOR-MGT-0{i}" for i in range(1, 6)],
    "DC1_TOR_PRD": [
        "TU-VIC-DC1-L0-SW-TOR-PRD-01", "TU-VIC-DC1-L0-SW-TOR-PRD-02", "TU-VIC-DC1-L0-SW-TOR-PRD-03",
        "TU-VIC-DC1-L0-SW-TOR-PRD-04", "TU-VIC-DC1-L0-SW-TOR-PRD-05", "TU-VIC-DC1-L0-SW-TOR-PRD-06",
        "TU-VIC-DC1-L0-SW-TOR-PRD-07"
    ]
}


def get_file_list_vlan():
    # Adjust if your input path changes
    search = r"C:\scripts\vlan_script\configs\**\show_vlan.json"
    return glob.glob(search, recursive=True)


def get_file_list_vrf():
    # Adjust if your input path changes
    search = r"C:\scripts\vlan_script\configs\**\show_ip_interface_brief_vrf_all.json"
    return glob.glob(search, recursive=True)


def read_vlan_data():
    filenames = get_file_list_vlan()
    vlan_data = {}
    for filename in filenames:
        hostname = filename.split("\\")[4]  # keep your existing indexing
        if "DC" in hostname and ("VIC" in hostname or "NSW" in hostname):
            with open(filename, "r") as f:
                vlans = json.load(f)
            # Collect tuples of (VLAN_ID, VLAN_NAME)
            vlan_info = sorted({(str(v['VLAN_ID']), v.get('VLAN_NAME', '')) for v in vlans},
                               key=lambda x: int(x[0]))
            vlan_data[hostname] = vlan_info
        else:
            continue
    return vlan_data


def read_interface_vrf_data_for_zone(zone: str):
    """Read VRF data for a specific zone"""
    filenames = get_file_list_vrf()
    interface_vrf_data: Dict[str, List[Dict[str, str]]] = {}

    for filename in filenames:
        with open(filename, "r") as f:
            vrfs = json.load(f)

        hostname = filename.split("\\")[4]
        zone_vrf_list = []

        for vrf in vrfs:
            vrf_name = vrf.get("VRF", "")
            if zone.lower() in vrf_name.lower():
                interface = vrf.get("INTERFACE", "")
                vlan_id = interface.replace("Vlan", "") if interface.startswith("Vlan") else ""
                if vlan_id:
                    zone_vrf_list.append({
                        "VRF_NAME": vrf_name,
                        "INTERFACE": interface,
                        "VLAN_ID": vlan_id
                    })

        if zone_vrf_list:
            interface_vrf_data[hostname] = zone_vrf_list

    return interface_vrf_data


# gets cor, tor_prd and tor_mgt switches
def get_switch_groups_for_dc(dc: str, switch_types_map: Dict[str, List[str]]
                             ) -> Tuple[List[str], List[str], List[str]]:
    cor_key = f"{dc}_Core"
    tor_prd_key = f"{dc}_TOR_PRD"
    tor_mgt_key = f"{dc}_TOR_MGT"

    cor_switches = switch_types_map.get(cor_key, [])
    tor_prd_switches = switch_types_map.get(tor_prd_key, [])
    tor_mgt_switches = switch_types_map.get(tor_mgt_key, [])
    return cor_switches, tor_prd_switches, tor_mgt_switches


# gets vlans data for the cor switches in the zones
def collect_zone_vlans_in_cor(cor_switches: List[str],
                              zone_vrf_data: Dict[str, List[Dict[str, str]]]
                              ) -> Set[str]:
    zone_vlans_in_cor: Set[str] = set()
    for cor_switch in cor_switches:
        if cor_switch in zone_vrf_data:
            for vrf_entry in zone_vrf_data[cor_switch]:
                vlan_id = vrf_entry["VLAN_ID"]
                if vlan_id:
                    zone_vlans_in_cor.add(vlan_id)
    return zone_vlans_in_cor


# gets cor_zone_vlans for a single zone, and uses cor_zone_vlan data
def build_cor_zone_vlan_baseline(cor_switches: List[str],
                                 vlan_data: Dict[str, List[Tuple[str, str]]],
                                 zone_vlans_in_cor: Set[str]
                                 ) -> Tuple[Dict[str, Set[str]], Set[str]]:
    cor_switch_vlans: Dict[str, Set[str]] = {}
    all_cor_zone_vlans: Set[str] = set()

    for cor_switch in cor_switches:
        cor_vlans = vlan_data.get(cor_switch, [])
        cor_vlan_ids = {vlan_id for vlan_id, _ in cor_vlans}
        cor_zone_vlans = cor_vlan_ids.intersection(zone_vlans_in_cor)

        cor_switch_vlans[cor_switch] = cor_zone_vlans
        all_cor_zone_vlans.update(cor_zone_vlans)

    return cor_switch_vlans, all_cor_zone_vlans


# compares cor switch vlans within DC
def compare_cor_switches(dc: str,
                         zone_name: str,
                         cor_switches: List[str],
                         cor_switch_vlans: Dict[str, Set[str]],
                         all_cor_zone_vlans: Set[str]
                         ) -> List[Dict[str, object]]:
    results: List[Dict[str, object]] = []

    print(f"\n--- COR Switches Comparison (Within DC) ---")
    print(f"All {zone_name} VLANs across COR switches (baseline): {sorted(all_cor_zone_vlans, key=int)}")
    print(f"Note: 'Has' means VLAN exists AND has a {zone_name} VRF interface")

    for cor_switch in cor_switches:
        has_vlans = cor_switch_vlans.get(cor_switch, set())
        missing_vlans = all_cor_zone_vlans - has_vlans

        print(f"\n{cor_switch}:")
        print(f" Has {zone_name} VLANs (VLAN + VRF): {sorted(has_vlans, key=int) if has_vlans else 'None'}")
        print(f" Missing {zone_name} VLANs: {sorted(missing_vlans, key=int) if missing_vlans else 'None'}")
        print(f"   DEBUG - baseline: {sorted(all_cor_zone_vlans, key=int)}")
        print(f"   DEBUG - has: {sorted(has_vlans, key=int)}")
        print(f"   DEBUG - missing: {sorted(missing_vlans, key=int)}")

        results.append({
            "Zone": zone_name,
            "DC": dc,
            "Switch_Type": "COR_within_DC",
            "Switch": cor_switch,
            "Has_VLANs": sorted(has_vlans, key=int),
            "Missing_VLANs": sorted(missing_vlans, key=int)
        })

    return results


# compares tor switches with all cor switch vlans
def compare_tor_group(dc: str,
                      zone_name: str,
                      tor_switches: List[str],
                      vlan_data: Dict[str, List[Tuple[str, str]]],
                      all_cor_zone_vlans: Set[str],
                      switch_type_label: str
                      ) -> List[Dict[str, object]]:
    results: List[Dict[str, object]] = []

    for tor_switch in tor_switches:
        tor_vlans = vlan_data.get(tor_switch, [])
        tor_vlan_ids = {vlan_id for vlan_id, _ in tor_vlans}
        tor_zone_vlans = tor_vlan_ids.intersection(all_cor_zone_vlans)
        missing_zone_vlans = all_cor_zone_vlans - tor_vlan_ids

        print(f"\n{tor_switch}:")
        print(f" Has {zone_name} VLANs: {sorted(tor_zone_vlans, key=int) if tor_zone_vlans else 'None'}")
        print(f" Missing {zone_name} VLANs: {sorted(missing_zone_vlans, key=int) if missing_zone_vlans else 'None'}")

        results.append({
            "Zone": zone_name,
            "DC": dc,
            "Switch_Type": switch_type_label,
            "Switch": tor_switch,
            "Has_VLANs": sorted(tor_zone_vlans, key=int),
            "Missing_VLANs": sorted(missing_zone_vlans, key=int)
        })

    return results


def infer_dc_from_switch_name(switch: str) -> str:
    """Best-effort DC extraction from hostname (expects '-DC1-' or '-DC2-')."""
    if "-DC1-" in switch:
        return "DC1"
    if "-DC2-" in switch:
        return "DC2"
    return "UNKNOWN"


def compare_cor_across_dcs(
        zone_name: str,
        xdc_cor_switch_vlans: Dict[str, Set[str]],
        xdc_all_cor_zone_vlans: Set[str]
) -> List[Dict[str, object]]:
    """
    Compare COR switches across DCs for a single zone:
      - Baseline: union of COR zone VLANs across BOTH DCs.
      - For each COR switch across both DCs, print Has/Missing vs that global union.
    """
    results: List[Dict[str, object]] = []

    print(f"\n--- COR Across DCs (Zone: {zone_name}) ---")
    print(f"All {zone_name} VLANs across BOTH DCs (COR union): "
          f"{sorted(xdc_all_cor_zone_vlans, key=int)}")

    for cor_switch, has_vlans in xdc_cor_switch_vlans.items():
        missing_vlans = xdc_all_cor_zone_vlans - has_vlans

        print(f"\n{cor_switch}:")
        print(f" Has {zone_name} VLANs: {sorted(has_vlans, key=int) if has_vlans else 'None'}")
        print(f" Missing {zone_name} VLANs (vs ALL DCs): "
              f"{sorted(missing_vlans, key=int) if missing_vlans else 'None'}")

        results.append({
            "Zone": zone_name,
            "DC": infer_dc_from_switch_name(cor_switch),
            "Switch_Type": "DC1_vs_DC2",  # distinct label for cross-DC results
            "Switch": cor_switch,
            "Has_VLANs": sorted(has_vlans, key=int),
            "Missing_VLANs": sorted(missing_vlans, key=int),
        })

    return results


def compare_zone_vlans_tor_vs_cor(vlan_data, zone_vrf_data, zone_name):
    """
    Compare Zone VLANs between TOR and COR switches for a specific zone
    - First compare COR switches against each other in the same DC
    - Then check if TOR switches have the VLANs that exist in their DC's COR switches
    - Finally: compare COR switches across BOTH DCs against the global COR union baseline
    """
    results = []

    # Accumulators for cross-DC comparison
    xdc_cor_switch_vlans: Dict[str, Set[str]] = {}  # across dc (xdc), switch -> zone VLAN set
    xdc_all_cor_zone_vlans: Set[str] = set()  # global union across DC1 + DC2

    for dc in ["DC1", "DC2"]:
        print(f"\n{'=' * 60}")
        print(f"=== Processing {dc} - Zone: {zone_name} ===")
        print(f"{'=' * 60}")

        # 1) Switch groups
        cor_switches, tor_prd_switches, tor_mgt_switches = get_switch_groups_for_dc(dc, switch_types)
        print(f"COR switches: {cor_switches}")
        print(f"TOR_PRD switches: {tor_prd_switches}")
        print(f"TOR_MGT switches: {tor_mgt_switches}")

        # 2) Zone VLANs present in COR (from VRF data)
        zone_vlans_in_cor = collect_zone_vlans_in_cor(cor_switches, zone_vrf_data)
        print(f"\n{zone_name} VLANs found in {dc} COR switches (from VRF data): "
              f"{sorted(zone_vlans_in_cor, key=int)}")

        # 3) COR baseline & COR comparisons (within the DC)
        cor_switch_vlans, all_cor_zone_vlans = build_cor_zone_vlan_baseline(
            cor_switches, vlan_data, zone_vlans_in_cor
        )
        results.extend(
            compare_cor_switches(dc, zone_name, cor_switches, cor_switch_vlans, all_cor_zone_vlans)
        )

        # Accumulate for cross-DC comparison
        for sw, s in cor_switch_vlans.items():
            xdc_cor_switch_vlans[sw] = s
        xdc_all_cor_zone_vlans.update(all_cor_zone_vlans)

        # 4) TOR_PRD comparisons
        print(f"\n--- TOR_PRD Switches ---")
        results.extend(
            compare_tor_group(dc, zone_name, tor_prd_switches, vlan_data, all_cor_zone_vlans, "TOR_PRD")
        )

        # 5) TOR_MGT comparisons
        print(f"\n--- TOR_MGT Switches ---")
        results.extend(
            compare_tor_group(dc, zone_name, tor_mgt_switches, vlan_data, all_cor_zone_vlans, "TOR_MGT")
        )

    # After both DCs processed, do cross-DC COR comparison once
    if xdc_cor_switch_vlans and xdc_all_cor_zone_vlans:
        results.extend(
            compare_cor_across_dcs(zone_name, xdc_cor_switch_vlans, xdc_all_cor_zone_vlans)
        )

    return results


def results_to_dataframe(comparison_results: List[Dict[str, object]]) -> pd.DataFrame:
    """
    Convert comparison results (list of dicts) to an Excel-friendly DataFrame.
    Now includes Zone column for filtering.
    """
    excel_rows = []
    for result in comparison_results:
        excel_rows.append({
            "Zone": result["Zone"],
            "DC": result["DC"],
            "Switch_Type": result["Switch_Type"],
            "Switch": result["Switch"],
            "Has_VLANs": ", ".join(map(str, result["Has_VLANs"])) if result["Has_VLANs"] else "",
            "Missing_VLANs": ", ".join(map(str, result["Missing_VLANs"])) if result["Missing_VLANs"] else ""
        })
    return pd.DataFrame(excel_rows)


def main(out_dir: Path = OUTPUT_DIR):
    # Ensure output directory exists
    out_dir.mkdir(parents=True, exist_ok=True)

    vlan_data = read_vlan_data()

    print("\n" + "=" * 60)
    print("=== Processing All Zones to Single Sheet ===")
    print("=" * 60)
    print(f"Zones to process: {', '.join(ZONES)}")

    # Collect all results across all zones
    all_results = []

    # Process each zone
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

        # Save VRF data for this zone (JSON) - optional individual files
        zone_filename = zone.replace("-", "").lower()
        vrf_json_filename = out_dir / f"{zone_filename}_vrf_data.json"
        with open(vrf_json_filename, "w") as f:
            json.dump(zone_vrf_data, f, indent=4)
        print(f"Saved {zone} VRF data to {vrf_json_filename}")

        # Compare VLANs for this zone
        comparison_results = compare_zone_vlans_tor_vs_cor(vlan_data, zone_vrf_data, zone)

        # Add to overall results
        all_results.extend(comparison_results)

    # Convert all results to a single DataFrame
    if all_results:
        df = results_to_dataframe(all_results)

        # Sort by Zone, DC, Switch_Type, then Switch for better organization
        df = df.sort_values(by=["Zone", "DC", "Switch_Type", "Switch"])

        # Save to single Excel file
        excel_filename = out_dir / "all_zones_vlan_comparison.xlsx"
        df.to_excel(excel_filename, index=False, sheet_name="All Zones")
        print(f"\n✓ Saved all zones comparison to {excel_filename}")
        print(f"  Total rows: {len(df)}")
        print(f"  Zones included: {', '.join(df['Zone'].unique())}")

        # Also save as CSV for easier filtering/analysis
        csv_filename = out_dir / "all_zones_vlan_comparison.csv"
        df.to_csv(csv_filename, index=False)
        print(f"✓ Saved CSV version to {csv_filename}")

        # Save consolidated JSON with all results
        json_filename = out_dir / "all_zones_vlan_comparison.json"
        with open(json_filename, "w") as f:
            json.dump(all_results, f, indent=4)
        print(f"✓ Saved JSON version to {json_filename}")
    else:
        print("\nNo results to save.")


if __name__ == "__main__":
    main()