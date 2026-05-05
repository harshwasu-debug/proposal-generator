import pandas as pd
import json
import os
import re

files = {
    'Raw Data/UAE_Bahrain Kitchen Tracker.xlsx': 'Raw Data/JSON/Kitchen Tracker',
    'Raw Data/UAE - Utility Estimator.xlsx': 'Raw Data/JSON/Utility Estimator',
}

for excel_path, json_dir in files.items():
    os.makedirs(json_dir, exist_ok=True)
    all_sheets = pd.read_excel(excel_path, sheet_name=None, header=None)
    for name, df in all_sheets.items():
        safe_name = re.sub(r'[\\/:*?"<>|]', '_', name)
        df_clean = df.where(pd.notnull(df), None)
        data = df_clean.values.tolist()
        with open(f'{json_dir}/{safe_name}.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)
    print(f'Done: {excel_path} -> {json_dir}')
