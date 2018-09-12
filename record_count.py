# This script counts the number of records in the given JSON file

import json, os, sys

# parse arguments to the script
if len(sys.argv) == 2:
    json_file = sys.argv[1]
else:
    sys.exit(1)

# navigate to fixtures directory
curdir = os.getcwd()
newdir = os.path.join(curdir, 'socapp', 'fixtures')
os.chdir(newdir)

# assert file exists
if not os.path.isfile(json_file):
    print("Invalid file")
    sys.exit(1)

# read the JSON data from the file
with open(json_file, mode="r") as f:
    data = json.load(f)

# print the number of records
print("{} records in this JSON file".format(len(data)))