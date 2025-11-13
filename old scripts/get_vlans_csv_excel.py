import pandas as pd
import glob
import json
from collections import Counter

# Define regions and their switches
regions = {
    "DC2_Region1": ["TU-NSW-DC2-L0-SW-COR-PRD-01", "TU-NSW-DC2-L0-SW-COR-PRD-02"],
    "DC2_Region2": [f"TU-NSW-DC2-L0-SW-TOR-MGT-0{i}" for i in range(1, 10)],
    "DC2_Region3": [f"TU-NSW-DC2-L0-SW-TOR-PRD-0{i}" for i in range(1, 5)],
    "DC2_Region4": ["TU-NSW-DC2-L0-SW-TOR-PRD-05", "TU-NSW-DC2-L0-SW-TOR-PRD-06"],
    "DC2_Region5": ["TU-NSW-DC2-L0-SW-TOR-PRD-07"],
    "DC2_Region6": ["TU-NSW-DC2-L0-SW-TOR-PRD-09", "TU-NSW-DC2-L0-SW-TOR-PRD-10"],
    "DC1_Region1": ["TU-VIC-DC1-L0-SW-COR-PRD-01", "TU-VIC-DC1-L0-SW-COR-PRD-02"],
    "DC1_Region2": [f"TU-VIC-DC1-L0-SW-TOR-MGT-0{i}" for i in range(1, 6)],
    "DC1_Region3": [f"TU-VIC-DC1-L0-SW-TOR-PRD-0{i}" for i in range(1, 5)],
    "DC1_Region4": ["TU-VIC-DC1-L0-SW-TOR-PRD-05", "TU-VIC-DC1-L0-SW-TOR-PRD-06"],
    "DC1_Region5": ["TU-VIC-DC1-L0-SW-TOR-PRD-07"]
}

# Load VLAN data from files
def get_file_list():
    search = "C:\\scripts\\vlan_script\\configs\\**\\show_vlan.json"
    files = glob.glob(search, recursive=True)
    print("Found files:", files) 
    return files

def read_vlan_data():
    filenames = get_file_list()
    vlan_data = {}
    for filename in filenames:
        with open(filename, "r") as f:
            vlans = json.load(f)
        hostname = filename.split("\\")[4]
        vlan_ids = sorted(set(str(v['VLAN_ID']) for v in vlans))
        vlan_data[hostname] = vlan_ids
    return vlan_data

# Compare VLANs within each region
def compare_vlans(vlan_data):
    results = []
    for region, switches in regions.items():
        region_vlans = [vlan_data.get(sw, []) for sw in switches]
        all_vlans = [vlan for sublist in region_vlans for vlan in sublist]
        common_vlans = [vlan for vlan, count in Counter(all_vlans).items() if count > 1]

        for switch in switches:
            # switch_vlans = vlan_data.get(switch, [])
            switch_vlans = vlan_data.get(switch, [])
            odd_vlans = sorted(set(switch_vlans).symmetric_difference(common_vlans), key=int)
            results.append({
                "Region": region,
                "Switch Name": switch,
                "VLAN_IDs": ", ".join(sorted(switch_vlans, key=int)),
                "Missing/Odd VLANs": ", ".join(odd_vlans)
            })
    return results

# Save results to CSV and Excel
def save_results(data):
    df = pd.DataFrame(data)
    # df.to_csv("vlan_comparison_by_region.csv", index=False)
    df.to_excel("vlan_comparison_by_region.xlsx", index=False)

def main():
    vlan_data = read_vlan_data()
    comparison_results = compare_vlans(vlan_data)
    save_results(comparison_results)

main()



# DC2 
# Core switches
# TU-NSW-DC2-L0-SW-COR-PRD-01
# TU-NSW-DC2-L0-SW-COR-PRD-02

# TOR-MGT switches
# TU-NSW-DC2-L0-SW-TOR-MGT-01
# TU-NSW-DC2-L0-SW-TOR-MGT-02
# TU-NSW-DC2-L0-SW-TOR-MGT-03
# TU-NSW-DC2-L0-SW-TOR-MGT-04
# TU-NSW-DC2-L0-SW-TOR-MGT-05
# TU-NSW-DC2-L0-SW-TOR-MGT-06
# TU-NSW-DC2-L0-SW-TOR-MGT-07
# TU-NSW-DC2-L0-SW-TOR-MGT-08
# TU-NSW-DC2-L0-SW-TOR-MGT-09

# TOR-PRD switches
# TU-NSW-DC2-L0-SW-TOR-PRD-01
# TU-NSW-DC2-L0-SW-TOR-PRD-02
# TU-NSW-DC2-L0-SW-TOR-PRD-03 
# TU-NSW-DC2-L0-SW-TOR-PRD-04
# TU-NSW-DC2-L0-SW-TOR-PRD-05
# TU-NSW-DC2-L0-SW-TOR-PRD-06
# TU-NSW-DC2-L0-SW-TOR-PRD-07
# TU-NSW-DC2-L0-SW-TOR-PRD-09
# TU-NSW-DC2-L0-SW-TOR-PRD-10


# DC1
# Core switches
# TU-VIC-DC1-L0-SW-COR-PRD-01
# TU-VIC-DC1-L0-SW-COR-PRD-02

# TOR-MGT switches
# TU-VIC-DC1-L0-SW-TOR-MGT-01
# TU-VIC-DC1-L0-SW-TOR-MGT-02
# TU-VIC-DC1-L0-SW-TOR-MGT-03
# TU-VIC-DC1-L0-SW-TOR-MGT-04
# TU-VIC-DC1-L0-SW-TOR-MGT-05

# TOR-PRD switches
# TU-VIC-DC1-L0-SW-TOR-PRD-01
# TU-VIC-DC1-L0-SW-TOR-PRD-02
# TU-VIC-DC1-L0-SW-TOR-PRD-03
# TU-VIC-DC1-L0-SW-TOR-PRD-04
# TU-VIC-DC1-L0-SW-TOR-PRD-05
# TU-VIC-DC1-L0-SW-TOR-PRD-06
# TU-VIC-DC1-L0-SW-TOR-PRD-07
