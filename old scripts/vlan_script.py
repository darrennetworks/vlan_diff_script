import sys
from pathlib import Path
import pandas as pd
import csv
import glob
import json
import openpyxl

# Create some paths
this_file_path = Path(__file__)
this_file_path_parent = this_file_path.parent
this_file_path_subfolder = this_file_path_parent / "sub_folder"
repo_path = this_file_path_parent.parent
# Append paths to SYS path list
sys.path.append(str(this_file_path_parent))
sys.path.append(str(this_file_path_subfolder))
sys.path.append(str(repo_path))

Print out the paths
print("\n".join(sys.path))

# from sub_folder.other_folder_module import get_all_files_2
from other_folder_module import get_all_files_2


def get_file_list():

    # For glob - when recursive is set, ** followed by a path separator matches 0 or more subdirectories
    search = "C:\\scripts\\vlan_script\\**\\show_vlan.json"

    files = glob.glob(search, recursive=True)

    # search2 = '/Users/kanmartin/scripts/state_files/**/show_ip_arp.txt'
    # files2 = get_all_files_2(search2)
    return files


def read_files():

    filenames = get_file_list()

    # Creating 34 different ways to store the results
    results_dictionary = {}
    results_string = ""
    results_list = []

    # Iterate through the filenames
    for filename in filenames:
        print(f"Reading {filename}")

        # # Using 'Path'
        # path = Path(file)
        # file_text = path.read_text()
        # file_text_lines = file_text.splitlines()
        
        # Using 'with Open'
        with open(filename, "r") as f:
            # file_text_lines = f.readlines()
            vlans = json.load(f)

        # Get a hostname from the filepath
        split_file_path = filename.split("\\")
        hostname = split_file_path[3]

        print(hostname)
        ids = [v['VLAN_ID'] for v in vlans]
        print(ids)