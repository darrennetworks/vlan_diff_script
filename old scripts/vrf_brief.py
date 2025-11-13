from multiprocessing.forkserver import connect_to_new_process

import pandas as pd
import glob
import json
from collections import Counter

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

# Define zones to process - each will be processed separately
ZONES = [
    "EA-",
    "MSS",
    "ITS",
    "CORPORATE"
]


# Load VLAN data from files
def get_file_list_vlan():
    search = "C:\\scripts\\vlan_script\\configs\\**\\show_vlan.json"
    return glob.glob(search, recursive=True)


# Load interface vrf from files
def get_file_list_vrf():
    search = "C:\\scripts\\vlan_script\\configs\\**\\show_ip_interface_brief_vrf_all.json"
    return glob.glob(search, recursive=True)


def read_vlan_data():
    filenames = get_file_list_vlan()
    vlan_data = {}

    for filename in filenames:
        hostname = filename.split("\\")[4]

        if "DC" in hostname and ("VIC" in hostname or "NSW" in hostname):

            with open(filename, "r") as f:
                vlans = json.load(f)

            # Collect tuples of (VLAN_ID, VLAN_NAME)
            vlan_info = sorted({(str(v['VLAN_ID']), v.get('VLAN_NAME', '')) for v in vlans}, key=lambda x: int(x[0]))
            vlan_data[hostname] = vlan_info
        else:
            continue

    return vlan_data


def read_interface_vrf_data_for_zone(zone):
    """Read VRF data for a specific zone"""
    filenames = get_file_list_vrf()
    interface_vrf_data = {}

    for filename in filenames:
        with open(filename, "r") as f:
            vrfs = json.load(f)

        hostname = filename.split("\\")[4]

        # Create a list of dictionaries with VRF_NAME, INTERFACE, and extracted VLAN_ID
        zone_vrf_list = []
        for vrf in vrfs:
            vrf_name = vrf.get("VRF", "")
            # Check if VRF name contains this specific zone (case-insensitive)
            if zone.lower() in vrf_name.lower():
                interface = vrf.get("INTERFACE", "")
                # Extract VLAN ID from interface name (e.g., "Vlan211" -> "211")
                vlan_id = interface.replace("Vlan", "") if interface.startswith("Vlan") else ""

                # Only add if we successfully extracted a VLAN ID
                if vlan_id:
                    zone_vrf_list.append({
                        "VRF_NAME": vrf_name,
                        "INTERFACE": interface,
                        "VLAN_ID": vlan_id
                    })

        # Store in dictionary under hostname if we found any zone VRFs
        if zone_vrf_list:
            interface_vrf_data[hostname] = zone_vrf_list

    return interface_vrf_data


def compare_zone_vlans_tor_vs_cor(vlan_data, zone_vrf_data, zone_name):
    """
    Compare Zone VLANs between TOR and COR switches for a specific zone
    - First compare COR switches against each other in the same DC
    - Then check if TOR switches have the VLANs that exist in their DC's COR switches
    """
    results = []

    # Process DC1 and DC2 separately
    for dc in ["DC1", "DC2"]:
        print(f"\n{'=' * 60}")
        print(f"=== Processing {dc} - Zone: {zone_name} ===")
        print(f"{'=' * 60}")

        # Get the COR, TOR_PRD, and TOR_MGT switch names for this DC
        cor_key = f"{dc}_Core"
        tor_prd_key = f"{dc}_TOR_PRD"
        tor_mgt_key = f"{dc}_TOR_MGT"

        cor_switches = switch_types.get(cor_key, [])
        tor_prd_switches = switch_types.get(tor_prd_key, [])
        tor_mgt_switches = switch_types.get(tor_mgt_key, [])

        print(f"COR switches: {cor_switches}")
        print(f"TOR_PRD switches: {tor_prd_switches}")
        print(f"TOR_MGT switches: {tor_mgt_switches}")

        # Get all Zone VLANs from the zone_vrf_data that exist in this DC's COR switches
        zone_vlans_in_cor = set()
        for cor_switch in cor_switches:
            if cor_switch in zone_vrf_data:
                for vrf_entry in zone_vrf_data[cor_switch]:
                    vlan_id = vrf_entry["VLAN_ID"]
                    zone_vlans_in_cor.add(vlan_id)

        print(f"\n{zone_name} VLANs found in {dc} COR switches (from VRF data): {sorted(zone_vlans_in_cor, key=int)}")

        # Compare COR switches against each other using actual VLAN data
        # Get the union of all Zone VLANs that should exist across both COR switches
        all_cor_zone_vlans = set()
        cor_switch_vlans = {}

        for cor_switch in cor_switches:
            # Get all VLANs on this COR switch
            cor_vlans = vlan_data.get(cor_switch, [])
            cor_vlan_ids = {vlan_id for vlan_id, vlan_name in cor_vlans}

            # Filter to only Zone VLANs (ones that are in zone_vlans_in_cor)
            cor_zone_vlans = cor_vlan_ids.intersection(zone_vlans_in_cor)
            cor_switch_vlans[cor_switch] = cor_zone_vlans

            # Add to the union
            all_cor_zone_vlans.update(cor_zone_vlans)

        print(f"\n--- COR Switches Comparison ---")
        print(f"All {zone_name} VLANs across COR switches: {sorted(all_cor_zone_vlans, key=int)}")

        # Compare each COR switch against the union of all COR Zone VLANs
        for cor_switch in cor_switches:
            has_vlans = cor_switch_vlans[cor_switch]
            missing_vlans = all_cor_zone_vlans - has_vlans

            print(f"\n{cor_switch}:")
            print(f"  Has {zone_name} VLANs: {sorted(has_vlans, key=int) if has_vlans else 'None'}")
            print(f"  Missing {zone_name} VLANs: {sorted(missing_vlans, key=int) if missing_vlans else 'None'}")

            results.append({
                "DC": dc,
                "Switch_Type": "COR",
                "Switch": cor_switch,
                "Has_VLANs": sorted(has_vlans, key=int),
                "Missing_VLANs": sorted(missing_vlans, key=int)
            })

        # For each TOR_PRD switch, check which Zone VLANs from COR it has and which are missing
        print(f"\n--- TOR_PRD Switches ---")
        for tor_switch in tor_prd_switches:
            tor_vlans = vlan_data.get(tor_switch, [])
            tor_vlan_ids = {vlan_id for vlan_id, vlan_name in tor_vlans}
            tor_zone_vlans = tor_vlan_ids.intersection(all_cor_zone_vlans)
            missing_zone_vlans = all_cor_zone_vlans - tor_vlan_ids

            print(f"\n{tor_switch}:")
            print(f"  Has {zone_name} VLANs: {sorted(tor_zone_vlans, key=int) if tor_zone_vlans else 'None'}")
            print(
                f"  Missing {zone_name} VLANs: {sorted(missing_zone_vlans, key=int) if missing_zone_vlans else 'None'}")

            results.append({
                "DC": dc,
                "Switch_Type": "TOR_PRD",
                "Switch": tor_switch,
                "Has_VLANs": sorted(tor_zone_vlans, key=int),
                "Missing_VLANs": sorted(missing_zone_vlans, key=int)
            })

        # For each TOR_MGT switch, check which Zone VLANs from COR it has and which are missing
        print(f"\n--- TOR_MGT Switches ---")
        for tor_switch in tor_mgt_switches:
            tor_vlans = vlan_data.get(tor_switch, [])
            tor_vlan_ids = {vlan_id for vlan_id, vlan_name in tor_vlans}
            tor_zone_vlans = tor_vlan_ids.intersection(all_cor_zone_vlans)
            missing_zone_vlans = all_cor_zone_vlans - tor_vlan_ids

            print(f"\n{tor_switch}:")
            print(f"  Has {zone_name} VLANs: {sorted(tor_zone_vlans, key=int) if tor_zone_vlans else 'None'}")
            print(
                f"  Missing {zone_name} VLANs: {sorted(missing_zone_vlans, key=int) if missing_zone_vlans else 'None'}")

            results.append({
                "DC": dc,
                "Switch_Type": "TOR_MGT",
                "Switch": tor_switch,
                "Has_VLANs": sorted(tor_zone_vlans, key=int),
                "Missing_VLANs": sorted(missing_zone_vlans, key=int)
            })

    return results



# def compare_cor_vlans_across_dc():
#     total_cor_vlans_across_dc = set(DC1_cor_switch_vlans + DC2_cor_switch_vlans)
#
#     for dc in ["DC1", "DC2"]:
#         for cor_switch in cor_switches:
#             cor_switch_set =  set for cor_switch
#             missing_vlans = cor_switch_set.difference(total_cor_vlans_across_dc)
#
#     return missing_vlans




# def compare_vlans(vlan_data):
#     results = []
#     for switch_type, switches in switch_types.items():
#         switch_type_vlans = [vlan_data.get(sw, []) for sw in switches]
#         all_vlans = [vlan for sublist in switch_type_vlans for vlan in sublist]
#         vlan_counts = Counter(all_vlans)
#
#         majority_vlans = [vlan for vlan, count in vlan_counts.items() if count > len(switches) // 2]
#
#         for switch in switches:
#             switch_vlans = vlan_data.get(switch, [])
#             odd_vlans = sorted(set(switch_vlans).symmetric_difference(majority_vlans), key=lambda x: int(x[0]))
#
#             results.append({
#                 "Switch Type": switch_type,
#                 "Switch Name": switch,
#                 "VLANs": ", ".join([f"{vid}" for vid, vname in sorted(switch_vlans, key=lambda x: int(x[0]))]),
#                 "Missing/Extra VLANs": "\n".join([f"vlan_id:{vid}, vlan_name:{vname}" for vid, vname in odd_vlans])
#             })
#     return results


def main():
    vlan_data = read_vlan_data()

    print("\n" + "=" * 60)
    print("=== Processing Zones Separately ===")
    print("=" * 60)
    print(f"Zones to process: {', '.join(ZONES)}")

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

        # Save VRF data for this zone
        zone_filename = zone.replace("-", "").lower()
        vrf_json_filename = f"{zone_filename}_vrf_data.json"
        with open(vrf_json_filename, "w") as f:
            json.dump(zone_vrf_data, f, indent=4)
        print(f"Saved {zone} VRF data to {vrf_json_filename}")

        # Compare VLANs for this zone
        comparison_results = compare_zone_vlans_tor_vs_cor(vlan_data, zone_vrf_data, zone)

        # Save comparison results for this zone to JSON
        comparison_json_filename = f"{zone_filename}_vlan_comparison.json"
        with open(comparison_json_filename, "w") as f:
            json.dump(comparison_results, f, indent=4)
        print(f"✓ Saved {zone} comparison results to {comparison_json_filename}")

        # Convert results to Excel-friendly format and save
        excel_results = []
        for result in comparison_results:
            excel_results.append({
                "DC": result["DC"],
                "Switch_Type": result["Switch_Type"],
                "Switch": result["Switch"],
                "Has_VLANs": ", ".join(map(str, result["Has_VLANs"])) if result["Has_VLANs"] else "",
                "Missing_VLANs": ", ".join(map(str, result["Missing_VLANs"])) if result["Missing_VLANs"] else ""
            })

        # Save to Excel
        df = pd.DataFrame(excel_results)
        excel_filename = f"{zone_filename}_vlan_comparison.xlsx"
        df.to_excel(excel_filename, index=False)
        print(f"✓ Saved {zone} comparison results to {excel_filename}")

        # Also save to CSV (commented out to avoid file lock issues)
        # csv_filename = f"{zone_filename}_vlan_comparison.csv"
        # df.to_csv(csv_filename, index=False)
        # print(f"✓ Saved {zone} comparison results to {csv_filename}")


if __name__ == "__main__":
    main()