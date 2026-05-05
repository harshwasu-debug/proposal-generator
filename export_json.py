import pandas as pd
import json
import os
import re

os.makedirs('Raw Data/JSON', exist_ok=True)

all_sheets = pd.read_excel('Raw Data/UAE_Bahrain Kitchen Tracker.xlsx', sheet_name=None, header=None)

for name, df in all_sheets.items():
    safe_name = re.sub(r'[\\/:*?"<>|]', '_', name)
    df_clean = df.where(pd.notnull(df), None)
    data = df_clean.values.tolist()
    with open(f'Raw Data/JSON/{safe_name}.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, default=str)
    print(f'  {name}')

print('Done')
