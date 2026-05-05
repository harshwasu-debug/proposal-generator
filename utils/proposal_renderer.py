import os

TEAL   = "#2D7070"
WHITE  = "#FFFFFF"

def _aed(v):
    return f"AED{v:,.2f}"

def _esc(text):
    return str(text).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('\n','<br>')

CSS = f"""
<style>
  .pw {{ font-family: Arial, sans-serif; font-size: 10.5pt; max-width: 780px; }}
  .pt {{ border-collapse: collapse; width: 100%; }}
  .pt td {{ border: 1px solid #bbb; padding: 7px 11px; vertical-align: middle; }}
  .tl {{ background:{TEAL}; color:{WHITE}; font-weight:bold; width:42%; }}
  .sh td {{ background:{TEAL}; color:{WHITE}; font-weight:bold; padding:7px 11px; }}
  .oh td {{ background:{WHITE}; text-align:center; font-weight:bold; }}
  .vc {{ text-align:center; }}
  .bv {{ font-weight:bold; }}
  .stk {{ text-decoration:line-through; color:#999; }}
  .wv {{ color:green; font-style:italic; margin-left:5px; font-weight:normal; }}
  .nt {{ font-size:9pt; border:none !important; padding:2px 0 !important; }}
  .rd {{ color:red; }}
  .sp td {{ border:none !important; height:6px; }}
</style>
"""

def render_proposal_html(options: list, config: dict, chart_b64_map: dict = None) -> str:
    """
    chart_b64_map: {option_index: base64_png_string} — utility charts to embed per option.
    """
    n = len(options)
    is_multi = n > 1
    same_loc = len(set(o['location_display'] for o in options)) == 1
    same_lic = len(set(o['license'] for o in options)) == 1
    col_span = n + 1
    cat = options[0]['category']

    rows = []

    # Option header row
    if is_multi:
        cells = '<td style="border:none;background:#fff;"></td>'
        for o in options:
            cells += f'<td style="text-align:center;font-weight:bold;border:1px solid #bbb;">{o["label"]}</td>'
        rows.append(f'<tr class="oh">{cells}</tr>')

    # Location
    if same_loc or not is_multi:
        rows.append(f'<tr><td class="tl">Location:</td><td colspan="{n}" class="vc bv">{_esc(options[0]["location_display"])}</td></tr>')
    else:
        cells = '<td class="tl">Location:</td>' + ''.join(f'<td class="vc bv">{_esc(o["location_display"])}</td>' for o in options)
        rows.append(f'<tr>{cells}</tr>')

    # License
    if same_lic or not is_multi:
        rows.append(f'<tr><td class="tl">Required License:</td><td colspan="{n}" class="vc bv">{_esc(options[0]["license"])}</td></tr>')
    else:
        cells = '<td class="tl">Required License:</td>' + ''.join(f'<td class="vc bv">{_esc(o["license"])}</td>' for o in options)
        rows.append(f'<tr>{cells}</tr>')

    # Unit specs
    cells = '<td class="tl">Unit specs:</td>' + ''.join(f'<td class="vc bv">{_esc(o["unit_specs"])}</td>' for o in options)
    rows.append(f'<tr>{cells}</tr>')

    rows.append(f'<tr class="sp"><td colspan="{col_span}"></td></tr>')

    # Monthly Cost section
    rows.append(f'<tr class="sh"><td colspan="{col_span}">Monthly Cost</td></tr>')

    cells = '<td><b>Monthly license fee</b> <span style="font-weight:normal;font-size:9pt;">(VAT excl, applicable)</span></td>'
    cells += ''.join(f'<td class="vc bv">{_aed(o["rent"])}</td>' for o in options)
    rows.append(f'<tr>{cells}</tr>')

    if cat != 'EK':
        cells = '<td><b>Estimated shared utilities</b> <span style="font-weight:normal;font-size:9pt;">(excl. direct Gas &amp; Elec. for KP)</span></td>'
        for o in options:
            val = o.get('utility_estimate')
            cells += f'<td class="vc">{"To be advised" if val is None else _aed(val)}</td>'
        rows.append(f'<tr>{cells}</tr>')

    rows.append(f'<tr class="sp"><td colspan="{col_span}"></td></tr>')

    # Reservation Fees section
    rows.append(f'<tr class="sh"><td colspan="{col_span}">Reservation Fees</td></tr>')

    cells = '<td><b>Refundable Deposit</b> <span style="font-weight:normal;font-size:9pt;">(VAT excl.)</span></td>'
    cells += ''.join(f'<td class="vc">{_aed(o["deposit"])}</td>' for o in options)
    rows.append(f'<tr>{cells}</tr>')

    all_waived = all(o['activation_waived'] for o in options)
    act_label = '<td><b>One Time Activation Fee</b> <span style="font-weight:normal;font-size:9pt;">(Incl. VAT)</span>'
    if all_waived:
        act_label += '<span class="wv">- waved off!</span>'
    act_label += '</td>'
    act_cells = act_label
    for o in options:
        if o['activation_waived']:
            act_cells += f'<td class="vc"><span class="stk">{_aed(o["activation_display"])}</span></td>'
        else:
            act_cells += f'<td class="vc">{_aed(o["activation_fee"])}</td>'
    rows.append(f'<tr>{act_cells}</tr>')

    cells = '<td><b>Total to book the kitchen</b></td>'
    cells += ''.join(f'<td class="vc bv">{_aed(o["total"])}</td>' for o in options)
    rows.append(f'<tr>{cells}</tr>')

    rows.append(f'<tr class="sp"><td colspan="{col_span}"></td></tr>')

    # Notes — standard block
    notes = [
        "Note: *Starting from 24m terms, payable monthly (first cheques needed for move-in). The notice period is 3 months.",
    ]

    # Utility note — depends on category and gas-inclusion status
    gas_not_included = any(o.get('gas_not_included') for o in options)
    all_ek = all(o['category'] == 'EK' for o in options)
    any_standard = any(o['category'] == 'Standard' for o in options)

    if all_ek and not gas_not_included:
        notes.append("EK facilities are all-inclusive: all utilities are included in the price including direct gas and electricity.")
    elif gas_not_included:
        notes.append("Utilities are included except for direct gas, which is individually metered and billed directly by the gas authority based on actual consumption.")
    if any_standard:
        notes.append("Gas and electricity (5 kw per kitchen) are individually metered for each unit, and charged based on actual consumption")
        notes.append("The estimation of shared utilities is ±2,000-5,000 monthly at KP facilities (covers all service charges and AMCs)")

    notes.append("Only the monthly rate is paid pre-paid. Utilities are post-paid, except the fixed charges.")
    if config.get('show_mall_note'):
        notes.append("Facilities inside the shopping centers and malls operate based on the mall's working hours.")
    if config.get('show_dine_in_note'):
        notes.append("For dine-in facilities, 10% applies (table service, waste management, payment collection, menu integration, etc).")
    notes.append("2.95% processing fee for delivery orders (through aggregators) or 400 AED Fixed (commissary kitchens)")

    for note in notes:
        rows.append(f'<tr><td colspan="{col_span}" class="nt">{_esc(note)}</td></tr>')

    # Location-specific notes (deduplicated)
    seen_loc_notes = set()
    for o in options:
        for ln in o.get('location_notes', []):
            if ln not in seen_loc_notes:
                rows.append(f'<tr><td colspan="{col_span}" class="nt">{_esc(ln)}</td></tr>')
                seen_loc_notes.add(ln)

    # Comments
    comments = config.get('comments', '').strip()
    if comments:
        for line in comments.splitlines():
            line = line.strip()
            if line:
                rows.append(f'<tr><td colspan="{col_span}" class="nt">{_esc(line)}</td></tr>')

    validity = config.get('validity_date', '')
    rows.append(f'<tr><td colspan="{col_span}" class="nt rd"><b>This offer is valid till {validity} and is available on a first-come, first-served basis.</b></td></tr>')

    proposal_html = CSS + f'<div class="pw"><table class="pt">{"".join(rows)}</table></div>'

    # Append utility chart(s) if provided
    if chart_b64_map:
        for idx, b64 in chart_b64_map.items():
            label = f"Option {idx + 1} — " if len(chart_b64_map) > 1 else ""
            proposal_html += f'''
            <div class="pw" style="margin-top:24px;">
                <div style="font-family:Arial,sans-serif;font-size:10pt;font-weight:bold;margin-bottom:6px;">
                    {label}Utility Estimate (Shared Only — excl. Direct Gas &amp; Electricity)
                </div>
                <img src="data:image/png;base64,{b64}" style="width:100%;max-width:780px;">
            </div>'''

    return proposal_html


def export_html_file(html: str, path: str):
    full = f'<!DOCTYPE html><html><head><meta charset="utf-8"></head><body style="margin:30px;">{html}</body></html>'
    with open(path, 'w', encoding='utf-8') as f:
        f.write(full)
    return path


def _html_to_pdf(html: str, pdf_path: str):
    from xhtml2pdf import pisa
    full = f'<!DOCTYPE html><html><head><meta charset="utf-8"></head><body style="margin:30px;">{html}</body></html>'
    with open(pdf_path, 'wb') as f:
        result = pisa.CreatePDF(full, dest=f)
    if result.err:
        raise RuntimeError(f"xhtml2pdf error: {result.err}")


def export_pdf(html: str, path: str):
    _html_to_pdf(html, path)
    return path


def export_image(html: str, path: str):
    # PNG export requires poppler-utils system package (not available on all hosts).
    # Download the PDF and screenshot it for WhatsApp use.
    raise NotImplementedError("PNG export is not available on this deployment. Download the PDF instead.")
