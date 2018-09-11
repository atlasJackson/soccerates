# Appends given number to the 'pk' field in each JSON record
# cmd: python fixtures_script.py <filename> <increment_by>

import os, sys, json, shutil

if len(sys.argv) == 3:
    json_file = sys.argv[1]
    INCREMENT_BY = int(sys.argv[2])
else:
    sys.exit(1)

# Change the directory to the fixtures directory
current_dir = os.path.dirname(os.path.realpath(__file__))
newdir = os.path.join(current_dir, 'socapp', 'fixtures')
os.chdir(newdir)

# Check the passed json_file exists:
if not os.path.isfile(json_file):
    print("Invalid file")
    sys.exit(1)

# Determine new file name based on original
filename = ''.join(json_file.split(".")[:-1])
extension = json_file.split(".")[-1] # Should be: ".json"
newfile = "{}_1.{}".format(filename, extension) # output file

try:
    shutil.copyfile(json_file, newfile) # copy original file

    # Read contents of original file into data variable
    with open(json_file, mode="r", encoding='utf-8') as f:
        data = json.load(f)
    # Iterate over all the data and increment as necessary
    for record in data:
        record['pk'] += INCREMENT_BY
    # Write the changed data back to the newfile
    with open(newfile, "w", encoding='utf-8') as new_f:
        json.dump(data, new_f, indent=4) # indent param used for 'pretty-printing' the JSON in a readable way
finally:
    os.chdir(current_dir)