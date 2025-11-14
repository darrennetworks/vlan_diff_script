import pandas
import glob
import json


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
    # results = {}

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
            if vlan_id not in results:
                results[vlan_id] = {}
            if hostname not in results[vlan_id]:
                results[vlan_id][hostname] = {}
            results[vlan_id][hostname]['sw_interface'] = v['INTERFACE']
            results[vlan_id][hostname]['sw_vrf'] = v['VRF']
            results[vlan_id][hostname]['sw_ip'] = v['IP_ADDRESS']

    return results  # , hostnames


def read_files_firewalls(results):
    filenames = get_firewall_file_list()
    # results = {}

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


def parse_results(results):
    parsed_results = {}
    hostnames = {"DC1", "DC2"}

    for vlan, vlan_data in results.items():
        if vlan not in parsed_results:
            parsed_results[vlan] = {}
        for hostname, device_data in vlan_data.items():
            hostnames.add(hostname)
            if "DC1" in hostname:
                parsed_results[vlan]["DC1"] = True
            if "DC2" in hostname:
                parsed_results[vlan]["DC2"] = True
            # Firewall Data
            if "DCFW" in hostname:
                parsed_results[vlan][f"{hostname}_interface"] = device_data["fw_interface"]
                parsed_results[vlan][f"{hostname}_zone"] = device_data["fw_zone"]
                parsed_results[vlan][f"{hostname}_fwd"] = device_data["fw_fwd"]
                parsed_results[vlan][f"{hostname}_ip"] = device_data["fw_ip"]
            else:
                if "has_vlan" in device_data:
                    parsed_results[vlan][hostname] = device_data["has_vlan"]
                if "sw_interface" in device_data:
                    parsed_results[vlan][f"{hostname}_interface"] = device_data["sw_interface"]
                    parsed_results[vlan][f"{hostname}_vrf"] = device_data["sw_vrf"]
                    parsed_results[vlan][f"{hostname}_ip"] = device_data["sw_ip"]

    return parsed_results


def main():
    results = read_vlan_files()
    results = read_core_switch_files(results)
    results = read_files_firewalls(results)

    # results = sw_results | cw_results | fw_results
    results = parse_results(results)

    # Columns orientation
    df = pandas.DataFrame.from_dict(results)
    df = df.sort_index()
    filename = "../results_columns_orientation.csv"
    df.to_csv(filename)
    print(f"Results saved to {filename}")

    # Index orientation
    hostnames = {x for v in results.values() for x in v}
    columns = sorted(list(hostnames))
    df = pandas.DataFrame.from_dict(results, orient="index")
    filename = "../results_index_orientation.csv"
    df.to_csv(filename, columns=columns)
    print(f"Results saved to {filename}")


if __name__ == "__main__":
    main()
