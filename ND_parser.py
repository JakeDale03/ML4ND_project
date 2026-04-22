import os
import re
import pandas as pd


def find_most_recent_exfor_data(target, reaction, exfor_dir):
    most_recent = []
    # Walk through directory, ignore subdirectories. Pick out each file
    for folder, _, files in os.walk(exfor_dir):
        for file_name in files:

            # Build in some resilience
            path = os.path.join(folder, file_name)
            try:
                # Open each file in turn and read it in
                with open(path, encoding="utf-8", errors="ignore") as working_file:
                    file_contents = working_file.read()

                    # Filter: only include files with cross-section (SIG) reactions
                    if not re.search(r"REACTION\s*\(.*?,\s*SIG\)", file_contents, re.IGNORECASE):
                        continue

                    # Look for the specific target + reaction
                    pattern = rf"REACTION\s*\(?{re.escape(target)}{re.escape(reaction)}"
                    if re.search(pattern, file_contents, re.IGNORECASE):
                        entry_line = re.search(r"ENTRY\s+\S+\s+(\d{8})", file_contents)
                        if entry_line:
                            most_recent.append((entry_line.group(1), path))

            except Exception as exception_text:
                # If it all goes wrong, where did it all go wrong?
                print(f"Skipped {path}: {exception_text}")

    # Tell me pls
    most_recent.sort(key=lambda x: x[0], reverse=True)
    return most_recent


def parse_exfor_file(file_name):
    # Create list of formatted sub-entries
    sub_entries_formatted = []

    # Open EXFOR file
    with open(file_name, encoding="utf-8", errors="ignore") as working_file:
        file_contents = working_file.read()

    # Pick up and assign metadata
    entry_match = re.search(r"ENTRY\s+(\S+)\s+(\d{8})", file_contents)
    if entry_match:
        entry_id = entry_match.group(1)
        entry_date = entry_match.group(2)
    else:
        entry_id = None
        entry_date = None

    # Check to see if the file has subentries
    if "SUBENT" in file_contents:
        file_has_sub_entries = True
    else:
        file_has_sub_entries = False

    # If the file has subentries, split it up into blocks. If not, make it one block
    if file_has_sub_entries:
        sub_entries = re.findall(r"(SUBENT\s+\S+.*?ENDSUBENT)", file_contents, re.S)
    else:
        sub_entries = [file_contents]

    for sub_entry in sub_entries:
        # Create list of dataframes
        dataframes = []

        # Pick up and assign metadata
        sub_match = re.search(r"SUBENT\s+(\S+)\s+(\d{8})", sub_entry)
        if sub_match:
            sub_id = sub_match.group(1)
            sub_date = sub_match.group(2)
        else:
            sub_id = None
            sub_date = None

        reaction_match = re.search(r"REAC(?:TION)?\s+([^(]*\([^)]*\)[^,\n]*)", sub_entry)
        if reaction_match:
            reaction = reaction_match.group(1).strip()
        else:
            reaction = None

        # Split up data block
        data_blocks = re.findall(r"DATA(.*?)ENDDATA", sub_entry, re.S)
        # print("No. of data blocks: ", len(data_blocks))
        if not data_blocks and not file_has_sub_entries:
            # Some single-entry files don't have data tags
            data_blocks = [sub_entry]

        # Create a Pandas dataframe to store the data
        for block in data_blocks:
            dataframe = create_dataframe(block)
            if not dataframe.empty:
                dataframes.append(dataframe)

        # Add each sub-entry into the list
        sub_entries_formatted.append({
            "subentry_id": sub_id,
            "subentry_date": sub_date,
            "reaction": reaction,
            "data": dataframes
        })

    # Return formatted database
    return {
        "entry_id": entry_id,
        "entry_date": entry_date,
        "subentries": sub_entries_formatted
    }


# Helper function to detect the units the block is in
def read_in_headers_and_units(lines):
    # Check to see if there is a "DATA" line. Sometimes it's on the same line, etc. (Poor formatting IMO)
    data_index = next((i for i, l in enumerate(lines) if l.strip().upper().startswith("DATA")), None)

    # choose search segment
    if data_index is not None:
        search_start = data_index + 1
    else:
        search_start = 0

    # lines to search
    for index in range(search_start, len(lines)):
        line = lines[index].strip()

        # match header patterns common in EXFOR
        if re.match(r"^(EN-|EN\s|EN-MIN\b|EN-MAX\b|EN-RES\b|EN-EXP\b|ENERGY\b)", line, re.IGNORECASE):

            # Split header into a list
            header = re.split(r"\s+", line)

            # Units should be here
            units_idx = index + 1
            units = None

            # Clean things up
            if units_idx < len(lines):
                units_line = lines[units_idx].strip()

                # only accept line if it has the right characters
                if units_line and re.search(r"[A-Za-z/*]", units_line):
                    units = re.split(r"\s+", units_line)
                else:
                    units = None

            # Start looking at data on the next line; even if no unit line
            if units is not None:
                start_idx = units_idx + 1
            else:
                start_idx = index + 1
            return header, units, start_idx

    # Fallback to nil vals
    return None, None, 0


# Helper to do the actual data parsing
def parse_numeric_block(lines, start_index):
    rows = []

    # Check every line, starting after the units line
    for line in lines[start_index:]:
        # Break loop after data
        if line.startswith("ENDDATA"):
            break

        # Just in case the line doesn't have numbers in it for some reason (#EXFORsucks)
        try:
            numbers = []
            for number in re.split(r"\s+", line):
                numbers.append(float(number))
            rows.append(numbers)
        except ValueError:
            continue

    # Return the dataframe with the numbers (hopefully) correctly formatted
    return pd.DataFrame(rows)


# Helper to convert all reaction data to barns
def convert_reaction_data(dataframe, units):
    # Set scale factors
    factors = {
        "B": 1.0, "MB": 1e-3, "UB": 1e-6, "NB": 1e-9,
        "PB": 1e-12, "KB": 1e3, "MB*EV": 1e-3, "MB/SR": 1e-3,
        "EV": 1e-6, "KEV": 1e-3, "MEV": 1.0, "GEV": 1e3
    }

    # Clean up any whitespace in headers
    dataframe.columns = dataframe.columns.str.strip()

    # Iterate over the columns, scale each in turn
    new_names = {}
    for col, unit in zip(list(dataframe.columns), units):
        unit = unit.upper()
        if unit == "NO-DIM":
            unit = "B"
        if "B" in unit:
            base_unit = unit.split("*")[0].split("/")[0]
            factor = factors.get(base_unit, 1.0)

            # Only attempt to scale if the column is numeric
            if pd.api.types.is_numeric_dtype(dataframe[col]):
                dataframe[col] = dataframe[col] * factor

            # Preserve suffix (*EV, /SR, etc.)
            suffix = ""
            if "*" in unit:
                suffix = "*" + unit.split("*", 1)[1]
            elif "/" in unit:
                suffix = "/" + unit.split("/", 1)[1]

            new_names[col] = f"{col} (b{suffix})"

        else:
            unit = (unit or "MEV").upper()
            factor = factors.get(unit, 1.0)

            # Only attempt to scale if the column is numeric
            if pd.api.types.is_numeric_dtype(dataframe[col]):
                dataframe[col] = dataframe[col] * factor

            new_names[col] = f"{col} (MeV)"

    # Apply all renames at once to avoid mid-loop KeyError
    dataframe.rename(columns=new_names, inplace=True)

    return dataframe


# Fully parse block into dataframe
def create_dataframe(data_block):
    lines = []
    # Clean lines, detect header/units
    for line in data_block.strip().splitlines():
        if line.strip():
            lines.append(line.strip())
    header, unit_line, start_idx = read_in_headers_and_units(lines)

    # Parse data, check if the data exists
    dataframe = parse_numeric_block(lines, start_idx)
    if dataframe.empty:
        return dataframe

    # Check that there is actually a header
    if header and len(header) == dataframe.shape[1]:
        dataframe.columns = header
    else:
        dataframe.columns = [f"Col{i + 1}" for i in range(dataframe.shape[1])]

    if not unit_line:
        # Fallback to default units (MeV, b)
        unit_line = ["MEV"] + ["b"] * (dataframe.shape[1] - 1)

    # Ensure unit_line matches dataframe width
    while len(unit_line) < len(dataframe.columns):
        unit_line.append("")

    # Convert units
    dataframe = convert_reaction_data(dataframe, unit_line)
    return dataframe


def read_END_CSV(filename):

    # Read the CSV file
    file_to_return = pd.read_csv(filename, sep=';', low_memory=False)

    # Clean columns
    file_to_return.columns = file_to_return.columns.str.strip()
    file_to_return = file_to_return.dropna()
    for column in file_to_return.columns:

        file_to_return[column] = pd.to_numeric(file_to_return[column][2:], errors="coerce")

    return file_to_return

