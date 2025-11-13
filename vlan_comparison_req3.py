import pandas
import glob
import json


def get_file_list():
    search = r"C:\scripts\vlan_script\configs\**\show_vlan.json"
    files = glob.glob(search, recursive=True)
    return files


def get_file_list_firewalls():
    search = r"C:\scripts\vlan_script\configs\**\show_interface_all.json"
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

        if "DC-FW1" in hostname:
            FWDC = "DC1"
        else:
            FWDC = "DC2"

        print(hostname)
        hostnames.add(hostname)
        ids = [v['VLAN_ID'] for v in vlans]
        print(ids)

        for v in vlans:
            vlan_id = v['VLAN_ID']
            if vlan_id not in results:
                results[vlan_id] = {}
            results[vlan_id][DC] = True
            results[vlan_id][FWDC] = True
            results[vlan_id][hostname] = True

    return results, hostnames


def read_files_firewalls():
    filenames = get_file_list_firewalls()
    results = {}
    hostnames = {"DC1", "DC2"}

    for filename in filenames:
        print(f"Reading {filename}")

        with open(filename, "r") as f:
            response = json.load(f)

        split_file_path = filename.split("\\")
        hostname = split_file_path[4]

        if "DCFW" not in hostname:
            continue

        if "MIT" in hostname:
            FWDC = "DC1"
        elif "BKH" in hostname:
            FWDC = "DC2"
        else:
            continue

        interfaces = response['response']['result']['ifnet']['entry']

        print(hostname)
        hostnames.add(hostname)

        for interface in interfaces:
            if 'tag' not in interface or interface['tag'] == '0':
                continue
            vlan_id = interface['tag']
            if vlan_id not in results:
                results[vlan_id] = {}
            results[vlan_id][FWDC] = True
            results[vlan_id][hostname] = interface['name']
            results[vlan_id]['zone'] = interface['zone']
            results[vlan_id]['fwd'] = interface['fwd']

    return results, hostnames


def parse_results(results):
    for vlan, data in results.items():

        if "DC1" in data and "DC2" not in data:
            data['in DC1 not DC2'] = True
        if "DC2" in data and "DC1" not in data:
            data['in DC2 not DC1'] = True

    return results


def main():
    results, hostnames = read_files()
    results = parse_results(results)

    columns = sorted(hostnames)
    df = pandas.DataFrame.from_dict(results, orient="index")
    df.to_csv("switches.csv", columns=columns)

    results, hostnames = read_files_firewalls()
    results = parse_results(results)

    columns = sorted(hostnames)
    columns += ['zone', 'fwd']
    df = pandas.DataFrame.from_dict(results, orient="index")
    df.to_csv("firewalls.csv", columns=columns)


if __name__ == "__main__":
    main()
