# vlan_diff_script

# Overview
cor_tor_zone_comparison.py - Compares the cor and tor switches across DC1 and DC2.
Loops through the show_vlan.json and show_ip_interface_brief_vrf_all.json files from all devices and compares the vlans from the cor and tor switches 
within it's DC and compares the cor switches from DC1 vs DC2.


svi_fw_vlan_comparison.py - Compares the cor and tor switches across DC1 and DC2, and has all information for all switches and vlans. 
It also has svi and firewall information and filters it for zones.
Does the same comparison logic as cor_tor_zone_comparison.py but also loops through firewall interfaces (show_interface_all.json) and outputs firewall and 
svi information.

# Pre-requisites

The following pre-requisites are required to use this toolkit:

- Python 3.8 or 3.9
- Git

In addition to these pre-requisites, the following items are recommended:

- Basic understanding of Python
- Basic understanding of Python virtual environments

## Installation

To install the application and the associated modules, please perform the following:

1) Create a Python virtual environment:

```console
virtualenv --python=`which python3` venv
```

2) Activate the virtual environment:

```console
source ./venv/bin/activate
```

3) Clone the repository to the machine:

```console
git clone https://github.com/darrennetworks/vlan_diff_script.git
```

4) Change to the repo directory:

```console
cd vlan_diff_script
```

5) Install the required modules:

```console
pip install -r requirements-dev.txt
```

## How to use modules/functions

1) Create folder named "Configs" in root directory

2) Populate configs folder by running this command:
```
aws s3 cp s3://netops-collection/config_collector/ . --recursive
```