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
            results[vlan_id][hostname] = True

    return results


def read_core_switch_files():
    filenames = get_core_sw_file_list()
    results = {}

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


def read_files_firewalls():
    filenames = get_firewall_file_list()
    results = {}

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
            # DC presence flags (unchanged)
            if "DC1" in hostname:
                parsed_results[vlan]["DC1"] = True
            if "DC2" in hostname:
                parsed_results[vlan]["DC2"] = True

            if isinstance(device_data, dict):
                # ---- Layer 3 information (SVIs, firewall interfaces) ----
                base = f"{hostname} (layer 3 information)"
                if "-SW-" in hostname:
                    # Switch L3
                    parsed_results[vlan][f"{base}_interface"] = device_data.get("sw_interface")
                    parsed_results[vlan][f"{base}_vrf"]       = device_data.get("sw_vrf")
                    parsed_results[vlan][f"{base}_ip"]        = device_data.get("sw_ip")
                else:
                    # Firewall L3
                    parsed_results[vlan][f"{base}_interface"] = device_data.get("fw_interface")
                    parsed_results[vlan][f"{base}_zone"]      = device_data.get("fw_zone")
                    parsed_results[vlan][f"{base}_fwd"]       = device_data.get("fw_fwd")
                    parsed_results[vlan][f"{base}_ip"]        = device_data.get("fw_ip")
            else:
                # ---- Layer 2 information (VLAN seen on that switch) ----
                if "-SW-" in hostname:
                    parsed_results[vlan][f"{hostname} (layer 2 information)"] = device_data
                else:
                    # Non-switch true flags (if any) stay as-is
                    parsed_results[vlan][hostname] = device_data
    return parsed_results


def main():
    sw_results = read_vlan_files()
    cw_results = read_core_switch_files()
    fw_results = read_files_firewalls()

    results = sw_results | cw_results | fw_results

    results = parse_results(results)

    # Columns orientation
    df = pandas.DataFrame.from_dict(results)
    df = df.sort_index()
    filename = "results_columns_orientation.csv"
    df.to_csv(filename)
    print(f"Results saved to {filename}")

    # Index orientation
    hostnames = {x for v in results.values() for x in v}
    columns = sorted(list(hostnames))
    df = pandas.DataFrame.from_dict(results, orient="index")
    filename = "results_index_orientation.csv"
    df.to_csv(filename, columns=columns)
    print(f"Results saved to {filename}")


if __name__ == "__main__":
    main()
