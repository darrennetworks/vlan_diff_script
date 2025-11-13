import pandas
import glob
import json


def get_file_list():
    search = r"C:\scripts\vlan_script\configs\**\show_vlan.json"
    files = glob.glob(search, recursive=True)
    return files


def read_files():
    filenames = get_file_list()
    results = {}
    hostnames = {"DC1", "DC2"}

    for filename in filenames:
        print(f"Reading {filename}")

        with open(filename, "r") as f:
            vlans = json.load(f)

        split_file_path = filename.split("\\")
        hostname = split_file_path[4]

        if "TU-VIC-DC1" not in hostname and "TU-NSW-DC2" not in hostname:
            continue

        if "TU-VIC-DC1" in hostname:
            DC = "DC1"
        else:
            DC = "DC2"

        print(hostname)
        hostnames.add(hostname)
        ids = [v['VLAN_ID'] for v in vlans]
        print(ids)

        for v in vlans:
            vlan_id = v['VLAN_ID']
            if vlan_id not in results:
                results[vlan_id] = {}
            results[vlan_id][DC] = vlan_id
            results[vlan_id][hostname] = "Interfaces"


    return results, hostnames


def main():
    results, hostnames = read_files()

    columns = sorted(hostnames)

    df = pandas.DataFrame.from_dict(results, orient="index")
    df.index = [f"vlan_id: {idx}" for idx in df.index]
    df.to_csv("test.csv", columns=columns)


if __name__ == "__main__":
    main()
