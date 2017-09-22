import csv
import json
import operator
from collections import OrderedDict

with open('all_year_data.csv') as data:
    reader = csv.DictReader(data)
    rows = list(reader)


# process rows
for row in rows:
    year = row['']
    row['year'] = year
    del row['']
    del row['total_win']
    del row['total_win_pct']
    for k, v in row.iteritems():
        if '_pct' in k:
            k = k.replace('_pct', '%')
        if k == 'year':
            row[k] = int(v)
        else:
            row[k] = float(v)

last_yr =  rows[-1]
import pdb; pdb.set_trace()

# sort by stat values descending from the last year


with open('parsed_data.json', 'w') as f:
    json.dump(rows, f)
