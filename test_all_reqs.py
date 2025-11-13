import pandas
import glob
import json

# Define zones and their VRF name patterns
ZONES = {
    "EA": ["EA-BMS", "EA-"],
    "MSS": ["MSS"],
    "ITS": ["ITS"],
    "CORPORATE": ["corporate"]
}


def get_vlan_file_list():
    search = r"C:\scripts\vlan_script\configs\**\show_vlan.json"
    files = glob.glob(search, recursive=True)
    return files


def get_core_sw_file_list():
    search = r"C:\scripts\vlan_script\configs\**\show_ip_interface_brief_vrf_all.json"
    files = glob.glob(search, recursive=True)
    return files


def get_firewall_file_list():
    search = r"C:\scripts\vlan_script\configs\**\show_interface_all.json"
    files = glob.glob(search, recursive=True)
    return files


def get_zone_from_vrf(vrf_name):
    """Determine which zone a VRF belongs to"""
    if not vrf_name:
        return ""

    vrf_upper = vrf_name.upper()

    for zone, patterns in ZONES.items():
        for pattern in patterns:
            if pattern.upper() in vrf_upper:
                return zone
    return ""


def read_vlan_files():
    filenames = get_vlan_file_list()
    results = {}

    for filename in filenames:
        print(f"Reading {filename}")

        with open(filename, "r") as f:
            vlans = json.load(f)

        split_file_path = filename.split("\\")
        hostname = split_file_path[4]

        if "TU-VIC-DC1" not in hostname and "TU-NSW-DC2" not in hostname:
            continue

        print(hostname)

        for v in vlans:
            vlan_id = v['VLAN_ID']
            if vlan_id not in results:
                results[vlan_id] = {}
            if hostname not in results[vlan_id]:
                results[vlan_id][hostname] = {}
            results[vlan_id][hostname] = {'has_vlan': True}

    return results


def read_core_switch_files(results):
    filenames = get_core_sw_file_list()
    vlan_zones = {}  # Track zone for each VLAN

    for filename in filenames:
        print(f"Reading {filename}")

        with open(filename, "r") as f:
            vlans = json.load(f)

        split_file_path = filename.split("\\")
        hostname = split_file_path[4]

        if "COR" not in hostname:
            continue

        if "TU-VIC-DC1" not in hostname and "TU-NSW-DC2" not in hostname:
            continue

        print(hostname)

        for v in vlans:
            if "Vlan" not in v['INTERFACE']:
                continue
            vlan_id = v['INTERFACE'].replace('Vlan', '')
            vrf_name = v.get('VRF', '')

            # Determine zone from VRF
            zone = get_zone_from_vrf(vrf_name)
            if zone and vlan_id not in vlan_zones:
                vlan_zones[vlan_id] = zone

            if vlan_id not in results:
                results[vlan_id] = {}
            if hostname not in results[vlan_id]:
                results[vlan_id][hostname] = {}
            results[vlan_id][hostname]['sw_interface'] = v['INTERFACE']
            results[vlan_id][hostname]['sw_vrf'] = v['VRF']
            results[vlan_id][hostname]['sw_ip'] = v['IP_ADDRESS']

    return results, vlan_zones


def read_files_firewalls(results):
    filenames = get_firewall_file_list()

    for filename in filenames:
        print(f"Reading {filename}")

        with open(filename, "r") as f:
            response = json.load(f)

        split_file_path = filename.split("\\")
        hostname = split_file_path[4]

        if "MIT" not in hostname and "BKH" not in hostname:
            continue
        if "DCFW" not in hostname:
            continue

        interfaces = response['response']['result']['ifnet']['entry']

        print(hostname)

        for interface in interfaces:
            if 'tag' not in interface or interface['tag'] == '0':
                continue
            vlan_id = interface['tag']
            if vlan_id not in results:
                results[vlan_id] = {}
            if hostname not in results[vlan_id]:
                results[vlan_id][hostname] = {}
            results[vlan_id][hostname]['fw_interface'] = interface['name']
            results[vlan_id][hostname]['fw_zone'] = interface['zone']
            results[vlan_id][hostname]['fw_fwd'] = interface['fwd']
            results[vlan_id][hostname]['fw_ip'] = interface['ip']
    return results


def parse_results(results, vlan_zones):
    """
    Parse results and set DC1/DC2 to True only if BOTH core switches in that DC have the VLAN
    Show blank instead of False
    Add Zone column
    """
    parsed_results = {}

    # Define the core switches for each DC
    dc1_core_switches = {
        "TU-VIC-DC1-L0-SW-COR-PRD-01",
        "TU-VIC-DC1-L0-SW-COR-PRD-02"
    }

    dc2_core_switches = {
        "TU-NSW-DC2-L0-SW-COR-PRD-01",
        "TU-NSW-DC2-L0-SW-COR-PRD-02"
    }

    for vlan, vlan_data in results.items():
        if vlan not in parsed_results:
            parsed_results[vlan] = {}

        # Add Zone column
        parsed_results[vlan]["Zone"] = vlan_zones.get(vlan, "")

        # Track which core switches have this VLAN
        dc1_cores_with_vlan = set()
        dc2_cores_with_vlan = set()

        for hostname, device_data in vlan_data.items():
            # Track core switches
            if hostname in dc1_core_switches:
                dc1_cores_with_vlan.add(hostname)
            elif hostname in dc2_core_switches:
                dc2_cores_with_vlan.add(hostname)

            # Firewall Data
            if "DCFW" in hostname:
                parsed_results[vlan][f"{hostname}_fw_info"] = {
                    'interface': device_data["fw_interface"],
                    'zone': device_data["fw_zone"],
                    'fwd': device_data["fw_fwd"],
                    'ip': device_data["fw_ip"]
                }
            else:
                if "has_vlan" in device_data:
                    parsed_results[vlan][hostname] = device_data["has_vlan"]
                if "sw_interface" in device_data:
                    parsed_results[vlan][f"{hostname}_svi_info"] = {
                        'interface': device_data["sw_interface"],
                        'vrf': device_data["sw_vrf"],
                        'ip': device_data["sw_ip"]
                    }

        # Set DC1 to True ONLY if BOTH DC1 core switches have this VLAN, otherwise blank
        dc1_has_all = (dc1_cores_with_vlan == dc1_core_switches)
        parsed_results[vlan]["DC1"] = True if dc1_has_all else ""

        # Set DC2 to True ONLY if BOTH DC2 core switches have this VLAN, otherwise blank
        dc2_has_all = (dc2_cores_with_vlan == dc2_core_switches)
        parsed_results[vlan]["DC2"] = True if dc2_has_all else ""

    return parsed_results


def get_ordered_columns():
    """
    Returns the columns in the specific order:
    1. Zone, DC1, DC2
    2. DC1 Core switches and their _svi_info
    3. DC2 Core switches and their _svi_info
    4. Firewall info
    5. Other switches (ACC, OOB, TOR-MGT, TOR-PRD, etc.)
    """
    ordered_columns = [
        "Zone",
        "DC1",
        "DC2",
        # DC1 Core switches with svi_info
        "TU-VIC-DC1-L0-SW-COR-PRD-01",
        "TU-VIC-DC1-L0-SW-COR-PRD-01_svi_info",
        "TU-VIC-DC1-L0-SW-COR-PRD-02",
        "TU-VIC-DC1-L0-SW-COR-PRD-02_svi_info",
        # DC2 Core switches with svi_info
        "TU-NSW-DC2-L0-SW-COR-PRD-01",
        "TU-NSW-DC2-L0-SW-COR-PRD-01_svi_info",
        "TU-NSW-DC2-L0-SW-COR-PRD-02",
        "TU-NSW-DC2-L0-SW-COR-PRD-02_svi_info",
        # Firewall info
        "TUVIC-MIT-PA-DCFW1_fw_info",
        "TUNSW-BKH-PA-DCFW1_fw_info",
        # DC2 ACC switches
        "TU-NSW-DC2-L0-SW-ACC-PRD-01",
        "TU-NSW-DC2-L0-SW-ACC-PRD-02",
        "TU-NSW-DC2-L0-SW-ACC-PRD-03",
        "TU-NSW-DC2-L0-SW-ACC-PRD-04",
        "TU-NSW-DC2-L0-SW-ACC-PRD-05",
        "TU-NSW-DC2-L0-SW-ACC-PRD-06",
        # DC2 OOB switches
        "TU-NSW-DC2-L0-SW-OOB-PRD-01",
        "TU-NSW-DC2-L0-SW-OOB-PRD-02",
        # DC2 TOR-MGT switches
        "TU-NSW-DC2-L0-SW-TOR-MGT-01",
        "TU-NSW-DC2-L0-SW-TOR-MGT-02",
        "TU-NSW-DC2-L0-SW-TOR-MGT-03",
        "TU-NSW-DC2-L0-SW-TOR-MGT-04",
        "TU-NSW-DC2-L0-SW-TOR-MGT-05",
        "TU-NSW-DC2-L0-SW-TOR-MGT-06",
        "TU-NSW-DC2-L0-SW-TOR-MGT-07",
        "TU-NSW-DC2-L0-SW-TOR-MGT-08",
        "TU-NSW-DC2-L0-SW-TOR-MGT-09",
        # DC2 TOR-PRD switches
        "TU-NSW-DC2-L0-SW-TOR-PRD-01",
        "TU-NSW-DC2-L0-SW-TOR-PRD-02",
        "TU-NSW-DC2-L0-SW-TOR-PRD-03",
        "TU-NSW-DC2-L0-SW-TOR-PRD-04",
        "TU-NSW-DC2-L0-SW-TOR-PRD-05",
        "TU-NSW-DC2-L0-SW-TOR-PRD-06",
        "TU-NSW-DC2-L0-SW-TOR-PRD-07",
        "TU-NSW-DC2-L0-SW-TOR-PRD-09",
        "TU-NSW-DC2-L0-SW-TOR-PRD-10",
        # DC1 TOR-MGT switches
        "TU-VIC-DC1-L0-SW-TOR-MGT-01",
        "TU-VIC-DC1-L0-SW-TOR-MGT-02",
        "TU-VIC-DC1-L0-SW-TOR-MGT-03",
        "TU-VIC-DC1-L0-SW-TOR-MGT-04",
        "TU-VIC-DC1-L0-SW-TOR-MGT-05",
        # DC1 TOR-PRD switches
        "TU-VIC-DC1-L0-SW-TOR-PRD-01",
        "TU-VIC-DC1-L0-SW-TOR-PRD-02",
        "TU-VIC-DC1-L0-SW-TOR-PRD-03",
        "TU-VIC-DC1-L0-SW-TOR-PRD-04",
        "TU-VIC-DC1-L0-SW-TOR-PRD-05",
        "TU-VIC-DC1-L0-SW-TOR-PRD-06",
        "TU-VIC-DC1-L0-SW-TOR-PRD-07",
    ]

    return ordered_columns


def main():
    results = read_vlan_files()
    results, vlan_zones = read_core_switch_files(results)
    results = read_files_firewalls(results)

    # Parse results with zone information
    results = parse_results(results, vlan_zones)

    # Get the ordered columns list
    ordered_columns = get_ordered_columns()

    # Columns orientation (VLANs as rows, devices as columns)
    df = pandas.DataFrame.from_dict(results, orient="index")

    # Reorder columns to match the specified order
    # Only include columns that exist in the dataframe
    existing_columns = [col for col in ordered_columns if col in df.columns]

    # Add any remaining columns that weren't in our ordered list
    remaining_columns = [col for col in df.columns if col not in existing_columns]
    final_columns = existing_columns + remaining_columns

    df = df[final_columns]
    df = df.sort_index()

    filename = "results_columns_orientation.csv"
    df.to_csv(filename)
    print(f"Results saved to {filename}")

    # Also save as Excel for better readability
    filename_excel = "results_columns_orientation.xlsx"
    df.to_excel(filename_excel)
    print(f"Results saved to {filename_excel}")

    # Index orientation (devices as rows, VLANs as columns) - with ordered rows
    df_transposed = pandas.DataFrame.from_dict(results)
    df_transposed = df_transposed.sort_index()

    # Reorder rows to match the specified order
    # Only include rows that exist in the dataframe
    existing_rows = [row for row in ordered_columns if row in df_transposed.index]

    # Add any remaining rows that weren't in our ordered list
    remaining_rows = [row for row in df_transposed.index if row not in existing_rows]
    final_rows = existing_rows + remaining_rows

    df_transposed = df_transposed.reindex(final_rows)

    filename = "results_index_orientation.csv"
    df_transposed.to_csv(filename)
    print(f"Results saved to {filename}")

    # Also save as Excel for better readability
    filename_excel = "results_index_orientation.xlsx"
    df_transposed.to_excel(filename_excel)
    print(f"Results saved to {filename_excel}")


if __name__ == "__main__":
    main()