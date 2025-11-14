"""
Example File Operations
"""

import sys
from pathlib import Path
import pandas
import csv
import glob

# # Create some paths
# this_file_path = Path(__file__)
# this_file_path_parent = this_file_path.parent
# this_file_path_subfolder = this_file_path_parent / "sub_folder"
# repo_path = this_file_path_parent.parent
# # Append paths to SYS path list
# sys.path.append(str(this_file_path_parent))
# sys.path.append(str(this_file_path_subfolder))
# sys.path.append(str(repo_path))

# Print out the paths
print("\n".join(sys.path))

# # from sub_folder.other_folder_module import get_all_files_2
# from other_folder_module import get_all_files_2


def get_file_list():

    # For glob - when recursive is set, ** followed by a path separator matches 0 or more subdirectories
    search = "/Users/kanmartin/scripts/state_files/**/show_ip_ssh.txt"
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
            file_text_lines = f.readlines()

        # Get a hostname from the filepath
        split_file_path = filename.split("/")
        hostname = split_file_path[5]

        # Go through the file line by line
        for line in file_text_lines:
            if "Diffie Hellman" in line:

                # String
                results_string += f"{hostname},{line}"

                # List
                hostname_line_tuple = (hostname, line)
                results_list.append(hostname_line_tuple)

                # Dictionary
                results_dictionary[hostname] = line

                pass

    # Return the results (will return as a tuple)
    return results_string, results_list, results_dictionary


def write_files(results_string, results_list, results_dictionary):
    # Create CSV from string
    headers = "hostname,key_size\n"
    results_string = headers + results_string
    with open("results_string.csv", "w") as f:
        f.write(results_string)

    # Create CSV from list using standard library csv module
    with open("results_list.csv", "w", newline="") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow(("hostname", "key_size"))
        for row in results_list:
            writer.writerow(row)

    # Create CSV using imported library Pandas
    df = pandas.DataFrame.from_dict(results_dictionary, orient="index")
    df.to_csv("results_dictionary.csv", index_label="hostname", header=["key_size"])

    pass


def main():
    # Get the results in 3 different formats
    results_string, results_list, results_dictionary = read_files()
    # Write the results to CSVs
    write_files(results_string, results_list, results_dictionary)


if __name__ == "__main__":
    main()
