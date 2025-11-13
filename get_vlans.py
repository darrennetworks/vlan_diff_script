import sys
from pathlib import Path
import pandas as pd
import csv
import glob
import json
import openpyxl



def get_file_list():
    search = "C:\\scripts\\vlan_script\\**\\show_vlan.json"
    return glob.glob(search, recursive=True)

def read_files():
    filenames = get_file_list()
    vlan_map = {}

    for filename in filenames:
        with open(filename, "r") as f:
            vlans = json.load(f)

        split_file_path = filename.split("\\")
        hostname = split_file_path[3]

        # Normalize hostname to lowercase for filtering
        hostname_lower = hostname.lower()

        # Filter for switches in DC1 or DC2 and containing COR or TOR
        if ("dc1" in hostname_lower or "dc2" in hostname_lower) and ("cor" in hostname_lower or "tor" in hostname_lower):
            vlan_ids = [str(v['VLAN_ID']) for v in vlans]

            if hostname in vlan_map:
                vlan_map[hostname].extend(vlan_ids)
            else:
                vlan_map[hostname] = vlan_ids

    # # Combine VLAN IDs into a single string per hostname
    # data = [{'hostname': host, 'VLAN_IDs': ", ".join(sorted(set(ids)))} for host, ids in vlan_map.items()]


    # Combine VLAN IDs into a single string per hostname
    data = [
        {
            'hostname': host,
            'VLAN_IDs': ", ".join(sorted(set(ids), key=int))  # Sort numerically
        }
        for host, ids in vlan_map.items()
    ]


    # Save to Excel
    df = pd.DataFrame(data)
    df.to_excel("vlan_data_filtered.xlsx", index=False)

def main():
    read_files()

if __name__ == "__main__":
    main()




# hostname | CCT (region) hostnames | vlan id | missing vlans | extra vlans

# # DC2 
# Region 1
# # TU-NSW-DC2-L0-SW-COR-PRD-01
# # TU-NSW-DC2-L0-SW-COR-PRD-02

# Region 2
# # TU-NSW-DC2-L0-SW-TOR-MGT-01
# # TU-NSW-DC2-L0-SW-TOR-MGT-02
# # TU-NSW-DC2-L0-SW-TOR-MGT-03
# # TU-NSW-DC2-L0-SW-TOR-MGT-04
# # TU-NSW-DC2-L0-SW-TOR-MGT-05
# # TU-NSW-DC2-L0-SW-TOR-MGT-06
# # TU-NSW-DC2-L0-SW-TOR-MGT-07
# # TU-NSW-DC2-L0-SW-TOR-MGT-08
# # TU-NSW-DC2-L0-SW-TOR-MGT-09

# Regoin 3
# # TU-NSW-DC2-L0-SW-TOR-PRD-01
# # TU-NSW-DC2-L0-SW-TOR-PRD-02
# # TU-NSW-DC2-L0-SW-TOR-PRD-03
# # TU-NSW-DC2-L0-SW-TOR-PRD-04

# Region 4
# # TU-NSW-DC2-L0-SW-TOR-PRD-05
# # TU-NSW-DC2-L0-SW-TOR-PRD-06

# Region 5
# # TU-NSW-DC2-L0-SW-TOR-PRD-07

# Region 6
# # TU-NSW-DC2-L0-SW-TOR-PRD-09
# # TU-NSW-DC2-L0-SW-TOR-PRD-10


# # DC1

# Region 1
# # TU-VIC-DC1-L0-SW-COR-PRD-01
# # TU-VIC-DC1-L0-SW-COR-PRD-02

# Region 2
# # TU-VIC-DC1-L0-SW-TOR-MGT-01
# # TU-VIC-DC1-L0-SW-TOR-MGT-02
# # TU-VIC-DC1-L0-SW-TOR-MGT-03
# # TU-VIC-DC1-L0-SW-TOR-MGT-04
# # TU-VIC-DC1-L0-SW-TOR-MGT-05

# Region 3
# # TU-VIC-DC1-L0-SW-TOR-PRD-01
# # TU-VIC-DC1-L0-SW-TOR-PRD-02
# # TU-VIC-DC1-L0-SW-TOR-PRD-03
# # TU-VIC-DC1-L0-SW-TOR-PRD-04

# Regoin 4
# # TU-VIC-DC1-L0-SW-TOR-PRD-05
# # TU-VIC-DC1-L0-SW-TOR-PRD-06

# Region 5
# # TU-VIC-DC1-L0-SW-TOR-PRD-07
