import json, os, base64
from io import BytesIO
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd

UTILITY_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Raw Data", "JSON", "Utility Estimator")

from utils.data_loader import UTILITY_PREFIX_MAP

COLORS = {
    'shared': '#4472C4',
    'chilled': '#FF0000',
    'other': '#FFC000',
}

def _safe(v):
    return v if isinstance(v, (int, float)) and v is not None else 0

def get_utility_chart_data(account_name: str, kitchen_type: str):
    prefix = UTILITY_PREFIX_MAP.get(account_name)
    if not prefix:
        return None
    suffix = "Hot Kitchens" if kitchen_type == "Hot Kitchen" else "Cold Kitchens"
    path = os.path.join(UTILITY_DIR, f"{prefix} - {suffix}.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    headers = data[0][1:]
    rows = data[1:]
    months = []
    for h in headers:
        try:
            months.append(pd.to_datetime(h).strftime('%b %Y'))
        except:
            months.append(str(h))
    result = {'months': months, 'shared': [], 'chilled': [], 'other': []}
    for row in rows:
        desc = str(row[0])
        vals = [_safe(v) for v in row[1:]]
        if 'Shared' in desc:
            result['shared'] = vals
        elif 'Chilled' in desc:
            result['chilled'] = vals
        elif 'Other' in desc:
            result['other'] = vals
    return result

def generate_utility_chart_base64(account_name: str, kitchen_type: str) -> str | None:
    d = get_utility_chart_data(account_name, kitchen_type)
    if not d or not d['months']:
        return None

    months  = d['months']
    shared  = d['shared']
    chilled = d['chilled']
    other   = d['other']

    n = len(months)
    x = np.arange(n)

    fig, ax = plt.subplots(figsize=(11, 3.8))
    fig.patch.set_facecolor('white')

    b1 = ax.bar(x, shared,  color=COLORS['shared'],  label='Shared Electricity (Extraction hot),  AC, Common Area')
    b2 = ax.bar(x, chilled, color=COLORS['chilled'], label='Chilled Water', bottom=shared)
    bottom3 = [s + c for s, c in zip(shared, chilled)]
    b3 = ax.bar(x, other,   color=COLORS['other'],   label='Other (Pest, Maintainence, Internet, etc)', bottom=bottom3)

    totals = [s + c + o for s, c, o in zip(shared, chilled, other)]
    for xi, total in zip(x, totals):
        ax.text(xi, total + max(totals) * 0.01, f'{total:,.2f}', ha='center', va='bottom', fontsize=7)

    ax.set_xticks(x)
    ax.set_xticklabels(months, fontsize=8)
    ax.set_ylabel('Total - Shared Only', fontsize=9)
    ax.set_title('Utility Trend', fontsize=11)
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: f'{v:,.0f}'))
    ax.tick_params(axis='y', labelsize=8)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.set_ylim(0, max(totals) * 1.15)

    ax.legend(loc='upper right', fontsize=7.5, framealpha=0.7)
    plt.tight_layout()

    buf = BytesIO()
    fig.savefig(buf, format='png', dpi=120, bbox_inches='tight')
    buf.seek(0)
    img_b64 = base64.b64encode(buf.read()).decode()
    plt.close(fig)
    return img_b64


def generate_utility_chart_streamlit(account_name: str, kitchen_type: str):
    """Returns (fig, data_dict) for use with st.pyplot."""
    d = get_utility_chart_data(account_name, kitchen_type)
    if not d or not d['months']:
        return None, None

    months  = d['months']
    shared  = d['shared']
    chilled = d['chilled']
    other   = d['other']
    x = np.arange(len(months))

    fig, ax = plt.subplots(figsize=(11, 3.8))
    fig.patch.set_facecolor('white')

    ax.bar(x, shared,  color=COLORS['shared'],  label='Shared Electricity (Extraction hot),  AC, Common Area')
    ax.bar(x, chilled, color=COLORS['chilled'], label='Chilled Water', bottom=shared)
    bottom3 = [s + c for s, c in zip(shared, chilled)]
    ax.bar(x, other,   color=COLORS['other'],   label='Other (Pest, Maintainence, Internet, etc)', bottom=bottom3)

    totals = [s + c + o for s, c, o in zip(shared, chilled, other)]
    for xi, total in zip(x, totals):
        ax.text(xi, total + max(totals) * 0.01, f'{total:,.2f}', ha='center', va='bottom', fontsize=7)

    ax.set_xticks(x)
    ax.set_xticklabels(months, fontsize=8)
    ax.set_ylabel('Total - Shared Only', fontsize=9)
    ax.set_title('Utility Trend', fontsize=11)
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: f'{v:,.0f}'))
    ax.tick_params(axis='y', labelsize=8)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.set_ylim(0, max(totals) * 1.15)
    ax.legend(loc='upper right', fontsize=7.5, framealpha=0.7)
    plt.tight_layout()

    return fig, d
