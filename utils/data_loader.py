import json, os
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KITCHEN_JSON = os.path.join(BASE_DIR, "Raw Data", "JSON", "Kitchen Tracker", "SF Kitchen Data.json")
UTILITY_DIR  = os.path.join(BASE_DIR, "Raw Data", "JSON", "Utility Estimator")

UTILITY_PREFIX_MAP = {
    "UAE - DXB - Motor City (1)":   "MC1",
    "UAE - DXB - Motor City (2)":   "MC2",
    "UAE - DXB - DSO":              "DSO",
    "UAE - DXB - JLT (1)":         "JLT1",
    "UAE - DXB - JLT (2)":         "JLT2",
    "UAE - DXB - Business Bay (1)": "BB1",
    "UAE - DXB - Business Bay (2)": "BB2",
    "UAE - DXB - Bur Dubai (1)":   "Bur1",
    "UAE - DXB - IMPZ":            "IMPZ",
    "UAE - DXB - Deira":           "Deira",
    "UAE - DXB - Sufouh":          "Sufouh",
    "UAE - DXB - Wafi Mall":       "Wafi Mall",
    "UAE - DXB - Quoz (1)":        "Quoz 1",
    "UAE - DXB - Quoz (2)":        "Quoz 2",
    "UAE - DXB - Mirdif":          "Mirdif",
    "UAE - AD - City of Light":    "COL",
}

DEFAULT_LICENSE_MAP = {
    # JLT = DMCC free zone
    "UAE - DXB - JLT (1)":              "DMCC TL",
    "UAE - DXB - JLT (2)":              "DMCC TL",
    "UAE - DXB - JLT (3) - EK":         "DMCC TL",
    # Dubai mainland
    "UAE - DXB - Motor City (1)":        "DET TL + Kiosk Permit",
    "UAE - DXB - Motor City (2)":        "DET TL + Kiosk Permit",
    "UAE - DXB - DSO":                   "DET TL + Kiosk Permit",
    "UAE - DXB - DSO (2) - EK":          "DET TL + Kiosk Permit",
    "UAE - DXB - Business Bay (1)":      "DET TL + Kiosk Permit",
    "UAE - DXB - Business Bay (2)":      "DET TL + Kiosk Permit",
    "UAE - DXB - Business Bay (3) - EK": "DET TL + Kiosk Permit",
    "UAE - DXB - Business Bay (4) - EK": "DET TL + Kiosk Permit",
    "UAE - DXB - Business Bay (5) - Cuisinette": "DET TL + Kiosk Permit",
    "UAE - DXB - Bur Dubai (1)":         "DET TL + Kiosk Permit",
    "UAE - DXB - IMPZ":                  "DET TL + Kiosk Permit",
    "UAE - DXB - Deira":                 "DET TL + Kiosk Permit",
    "UAE - DXB - Sufouh":                "DET TL + Kiosk Permit",
    "UAE - DXB - Wafi Mall":             "DET TL + Kiosk Permit",
    "UAE - DXB - Quoz (1)":              "DET TL + Kiosk Permit",
    "UAE - DXB - Quoz (2)":              "DET TL + Kiosk Permit",
    "UAE - DXB - Mirdif":                "DET TL + Kiosk Permit",
    "UAE - DXB - Arjan (3) - EK":        "DET TL + Kiosk Permit",
    "UAE - DXB - Hessa (1)":             "DET TL + Kiosk Permit",
    "UAE - DXB - Hessa (2) - EK":        "DET TL + Kiosk Permit",
    "UAE - DXB - Hessa (3) - EK":        "DET TL + Kiosk Permit",
    "UAE - DXB - Ras Al Khor":           "DET TL + Kiosk Permit",
    "UAE - DXB - Jabal Ali":             "DET TL + Kiosk Permit",
    # Abu Dhabi
    "UAE - AD - City of Light":          "DET TL + Kiosk Permit",
    "UAE - AD - Al Nahyan":              "DET TL + Kiosk Permit",
    "UAE - AD - Raha (1) - EK":          "DET TL + Kiosk Permit",
    # Sharjah
    "UAE - SHJ - Centre":                "TL + Kiosk Permit",
    "UAE - SHJ - Falah":                 "TL + Kiosk Permit",
    "UAE - SHJ - Muwaileh - EK":         "TL + Kiosk Permit",
    # Al Ain
    "UAE - AN - Jimi":                   "TL + Kiosk Permit",
}

GAS_NOT_INCLUDED = {
    "UAE - AD - Raha (1) - EK",
    "UAE - DXB - Business Bay (5) - Cuisinette",
    "UAE - SHJ - Muwaileh - EK",
}

LOCATION_SPECIFIC_NOTES = {
    # Gas note for these locations is handled by the renderer via gas_not_included flag —
    # do NOT duplicate it here.
    "UAE - SHJ - Centre": [
        "Gas connection activation fee: AED 300 per connection.",
        "Kiosk permit is charged as a monthly subscription fee.",
    ],
}

def get_default_license(account_name: str) -> str:
    if account_name in DEFAULT_LICENSE_MAP:
        return DEFAULT_LICENSE_MAP[account_name]
    if "- SHJ -" in account_name or "- AN -" in account_name:
        return "TL + Kiosk Permit"
    if "- JLT" in account_name:
        return "DMCC TL"
    return "DET TL + Kiosk Permit"

def load_kitchen_df():
    with open(KITCHEN_JSON, encoding='utf-8') as f:
        data = json.load(f)
    df = pd.DataFrame(data[1:], columns=data[0])
    # Coerce mixed-type columns to str so pyarrow doesn't choke in st.dataframe()
    for col in ['Hood Size', 'Kitchen Size (Sq. Meters)']:
        if col in df.columns:
            df[col] = df[col].astype(str).replace('None', '').replace('nan', '')
    return df

def get_available_kitchens():
    df = load_kitchen_df()
    return df[df['Status'].isin(['Vacant', 'Churning'])].copy()

def get_all_kitchens():
    """All kitchens regardless of status (for proposals on occupied units)."""
    return load_kitchen_df().copy()

def get_churning_kitchens():
    df = load_kitchen_df()
    return df[df['Status'] == 'Churning'].copy()

def kitchen_category(account_name: str) -> str:
    n = account_name.upper()
    if ' - EK' in n or '(EK)' in n:
        return 'EK'
    if 'CUISINETTE' in n or '- CUI' in n:
        return 'Cuisinette'
    return 'Standard'

def get_utility_estimate(account_name: str, kitchen_type: str):
    prefix = UTILITY_PREFIX_MAP.get(account_name)
    if not prefix:
        return None
    suffix = "Hot Kitchens" if kitchen_type == "Hot Kitchen" else "Cold Kitchens"
    path = os.path.join(UTILITY_DIR, f"{prefix} - {suffix}.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    rows = data[1:]
    shared_rows = [r for r in rows if any(k in str(r[0]) for k in ['Shared', 'Chilled', 'Other'])]
    if not shared_rows:
        return None
    n_months = len(shared_rows[0]) - 1
    monthly = []
    for m in range(1, n_months + 1):
        total = sum(r[m] for r in shared_rows if isinstance(r[m], (int, float)) and r[m] is not None)
        monthly.append(total)
    if not monthly:
        return None
    return {
        'average': round(sum(monthly) / len(monthly)),
        'highest': round(max(monthly)),
        'lowest':  round(min(monthly)),
    }

def get_similar_location_utility(kitchen_type: str):
    results = {}
    for loc, prefix in UTILITY_PREFIX_MAP.items():
        data = get_utility_estimate(loc, kitchen_type)
        if data:
            results[loc] = data
    return results
