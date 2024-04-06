import pandas as pd
import os
import numpy as np


# Importing talks from Google sheets

# Google sheets
sheet_id = "1ozMqEZPNpK4szjnODCX-5H8Ks432nAAXP8Ds19_B-2o"
sheet_name = "my_list_of_talks"
url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"

talks = pd.read_csv(url, header=0)

# Escape special characters

# YAML is very picky about how it takes a valid string, so we are replacing single and double quotes (and ampersands) with their HTML encoded equivilents.
# This makes them look not so readable in raw format, but they are parsed and rendered nicely.

html_escape_table = {"&": "&amp;", '"': "&quot;", "'": "&apos;"}


def html_escape(text):
    if type(text) is str:
        return "".join(html_escape_table.get(c, c) for c in text)
    else:
        return "False"


### Remove empty entries

talks = talks.replace(np.nan, "", regex=True)

### Creating the markdown files

# This is where the heavy lifting is done.
# This loops through all the rows in the TSV dataframe, then starts to concatentate a big string (```md```) that contains the markdown for each type.
# It does the YAML metadata first, then does the description for the individual page.

for f in os.listdir("../_talks"):
    os.remove(os.path.join("../_talks", f))

loc_dict = {}
for row, item in talks.iterrows():
    if item.venue != "":
        print(item.venue)
        year = f"20{item.date[5:]}"
        month = item.date[:2]
        print(month, year)
        if len(str(item.ID)) == 1:
            id_for_sorting = f"000{item.ID}"
        elif len(str(item.ID)) == 2:
            id_for_sorting = f"00{item.ID}"
        elif len(str(item.ID)) == 3:
            id_for_sorting = f"0{item.ID}"
        else:
            print(f"Invalid ID number {item.ID} with length {len(str(item.ID))}")
            break
        md_filename = f"{str(id_for_sorting)}_{item.venue}.md"
        html_filename = str(id_for_sorting)
        md = "---\n"
        md += "collection: talks" + "\n"
        md += 'talk_number: "' + str(item.ID) + '"\n'
        md += 'id_for_sorting: "' + str(id_for_sorting) + '"\n'
        md += "permalink: /talks/" + html_filename + "\n"

        if len(str(item.type)) > 1:
            md += f'title: "{item.title}" \n'

        if len(str(item.type)) > 0:
            md += 'type: "' + item.type + '"\n'
        else:
            md += 'type: "talk"\n'

        if len(str(item.venue)) > 0:
            md += 'venue: "' + item.venue + '"\n'

        if len(str(item.date)) > 0:
            md += "date: " + month + "/" + year[2:] + "\n"

        if len(str(item.location)) > 0:
            md += 'location: "' + str(item.location) + '"\n'

        if len(str(item.talk_url)) > 3:
            md += "link: True \n"
            md += f"talk_url: {str(item.talk_url)} \n"

        md += "---\n"

        if len(str(item.talk_url)) > 3:
            md += "\n[More information here](" + item.talk_url + ")\n"

        if len(str(item.description)) > 3:
            md += "\n" + html_escape(item.description) + "\n"

        md_filename = os.path.basename(md_filename)
        with open("../_talks/" + md_filename, "w") as f:
            f.write(md)
