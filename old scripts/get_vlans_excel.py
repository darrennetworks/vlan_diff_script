import pandas as pd
import glob
import json
from collections import Counter

# Define updated switch groupings
regions = {
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

# Load VLAN data from files
def get_file_list_vlan():
    search = "C:\\scripts\\vlan_script\\configs\\**\\show_vlan.json"
    return glob.glob(search, recursive=True)

# Load interface vrf from files
def get_file_list_vrf():
    search = "C:\\scripts\\vlan_script\\configs\\**\\show_ip_interface_brief_vrf_all.json"
    return glob.glob(search, recursive=True)

# def read_vlan_data():
#     filenames = get_file_list()
#     vlan_data = {}
#     for filename in filenames:
#         with open(filename, "r") as f:
#             vlans = json.load(f)
#         hostname = filename.split("\\")[4]
#         vlan_ids = sorted(set(str(v['VLAN_ID']) for v in vlans))
#         vlan_data[hostname] = vlan_ids
#     return vlan_data

def read_vlan_data():
    filenames = get_file_list_vlan()
    vlan_data = {}

    for filename in filenames:
        with open(filename, "r") as f:
            vlans = json.load(f)
        hostname = filename.split("\\")[4]
        # Collect tuples of (VLAN_ID, VLAN_NAME)
        vlan_info = sorted({(str(v['VLAN_ID']), v.get('VLAN_NAME', '')) for v in vlans}, key=lambda x: int(x[0]))
        vlan_data[hostname] = vlan_info
    return vlan_data # returns dict that maps switches to vlans

def read_interface_vrf_data():
    filenames = get_file_list_vrf()
    interface_vrf_data = {}

    for filename in filenames:
        with open(filename, "r") as f:
            vrfs = json.load(f)

        hostname = filename.split("\\")[4]

        # Create a set of (VRF_NAME, VLAN_NAME) tuples where VRF_NAME contains "EA-"
        vrf_set = {(vrf.get("VRF_NAME", ""), vrf.get("VLAN_NAME", "")) for vrf in vrfs if "EA-" in vrf.get("VRF_NAME", "")}

        # Sort the set by VRF_NAME
        vrf_info = sorted(vrf_set, key=lambda x: x[0])

        # Store in dictionary under hostname
        if vrf_info:
            interface_vrf_data[hostname] = vrf_info

    return interface_vrf_data 


# Compare VLANs within each region
# def compare_vlans(vlan_data):
#     results = []
#     for region, switches in regions.items():
#         region_vlans = [vlan_data.get(sw, []) for sw in switches]
#         all_vlans = [vlan for sublist in region_vlans for vlan in sublist]
#         vlan_counts = Counter(all_vlans)
#         majority_vlans = [vlan for vlan, count in vlan_counts.items() if count > len(switches) // 2]

#         for switch in switches:
#             switch_vlans = vlan_data.get(switch, [])
#             odd_vlans = sorted(set(switch_vlans).symmetric_difference(majority_vlans), key=int)
#             results.append({
#                 "Region": region,
#                 "Switch Name": switch,
#                 "VLAN_IDs": ", ".join(sorted(switch_vlans, key=int)),
#                 "Missing/Extra VLANs": ", ".join(odd_vlans)
#             })
#     return results


def compare_vlans(vlan_data):
    results = []
    for region, switches in regions.items(): # loops through each region in regions
        region_vlans = [vlan_data.get(sw, []) for sw in switches] # loops through switch in switches and gets the vlans from that switch it's looping through
        all_vlans = [vlan for sublist in region_vlans for vlan in sublist] # puts it into one big list
        vlan_counts = Counter(all_vlans) # counts lists

        majority_vlans = [vlan for vlan, count in vlan_counts.items() if count > len(switches) // 2] 
        # for vlan, count in vlan_counts.items(), this line loops through each vlan and how many switches it's on
        # if count > len(switches) // 2, calculates if the vlan is on more than half the switches

        for switch in switches:
            switch_vlans = vlan_data.get(switch, [])

            # figures out which VLANs are not matching the majority — either missing or extra — and sort them by VLAN ID
            odd_vlans = sorted(set(switch_vlans).symmetric_difference(majority_vlans), key=lambda x: int(x[0]))

            results.append({
                "Region": region,
                "Switch Name": switch,
                "VLANs": ", ".join([f"{vid}" for vid, vname in sorted(switch_vlans, key=lambda x: int(x[0]))]),
                "Missing/Extra VLANs": "\n".join([f"vlan_id:{vid}, vlan_name:{vname}" for vid, vname in odd_vlans])
            })
    return results


# TO DO: loop through all "show IP VRF brief" structured files
# def compare_vlans_EA_zone(vlan_data):
#     for 
#     pass



# def check_tor_prd_vlans_in_cor_prd(vlan_data):
#     # VLANs to check (from DC1 TOR_PRD)
#     vlans_to_check = [
#         ("3499", "3499_INT_DC1_P_Z5_RemoteUsers"),
#         ("3364", "ADC_Transit_Z5"),
#         ("3377", "3377_EXT_DC1_P_WIFI-TUEMS"),
#         ("3383", "VLAN_3383"),
#         ("3384", "VLAN3384"),
#         ("3495", "3495_INT_DC1_P_SHD_GEN_F5-XCONN"),
#         ("3496", "3496_INT_DC1_P_SHD_PALO-F5-INT"),
#         ("3900", "3900_EA_DC1_P_DAT_SEC_X-CONN"),
#     ]
#     # DC1 COR_PRD switches
#     cor_prd_switches = ["TU-VIC-DC1-L0-SW-COR-PRD-01", "TU-VIC-DC1-L0-SW-COR-PRD-02"]

#     # # DC1 TOR_PRD switches
#     # tor_prd_swches = 

#     # Gather VLANs present in COR_PRD switches
#     cor_prd_vlans = set()
#     for switch in cor_prd_switches:
#         cor_prd_vlans.update(vlan_data.get(switch, []))

#     print("\nChecking if TOR_PRD VLANs are in COR_PRD switches (DC1):")
#     for vlan in vlans_to_check:
#         if vlan in cor_prd_vlans:
#             print(f"  FOUND in COR_PRD: vlan_id:{vlan[0]}, vlan_name:{vlan[1]}")
#         else:
#             print(f"  MISSING in COR_PRD: vlan_id:{vlan[0]}, vlan_name:{vlan[1]}")

def check_vlan_in_dc1_tor_prd(vlan_data):
    vlan_to_check = ("3499", "3499_INT_DC1_P_Z5_RemoteUsers")
    dc1_tor_prd_switches = [
        "TU-VIC-DC1-L0-SW-TOR-PRD-01", "TU-VIC-DC1-L0-SW-TOR-PRD-02", "TU-VIC-DC1-L0-SW-TOR-PRD-03",
        "TU-VIC-DC1-L0-SW-TOR-PRD-04", "TU-VIC-DC1-L0-SW-TOR-PRD-05", "TU-VIC-DC1-L0-SW-TOR-PRD-06",
        "TU-VIC-DC1-L0-SW-TOR-PRD-07"
    ]
    found = False
    for switch in dc1_tor_prd_switches:
        if vlan_to_check in vlan_data.get(switch, []):
            print(f"FOUND in {switch}: vlan_id:{vlan_to_check[0]}, vlan_name:{vlan_to_check[1]}")
            found = True
    if not found:
        print(f"NOT FOUND in any DC1 TOR_PRD switch: vlan_id:{vlan_to_check[0]}, vlan_name:{vlan_to_check[1]}")




# Save results to CSV and Excel
def save_results(data):
    df = pd.DataFrame(data)
    # df.to_csv("vlan_comparison.csv", index=False)
    # df.to_excel("vlan_comparison_vid_vname.xlsx", index=False)

def main():
    # vlan_data = read_vlan_data()
    interface_vrf_data = read_interface_vrf_data()

    # check_tor_prd_vlans_in_cor_prd(vlan_data)

    # check_vlan_in_dc1_tor_prd(vlan_data)
    # comparison_results = compare_vlans(vlan_data)
    # save_results(comparison_results)
   
if __name__ == "__main__":
    main()

