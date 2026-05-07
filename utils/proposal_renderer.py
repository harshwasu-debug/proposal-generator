# v2 — per-option utility attribution for mixed proposals
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

    cells = '<td><b>Estimated shared utilities</b> <span style="font-weight:normal;font-size:9pt;">(excl. direct Gas &amp; Elec. for KP)</span></td>'
    for o in options:
        if o['category'] == 'EK':
            cells += f'<td class="vc">{_aed(0)}</td>'
        else:
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

    # ── Utility notes ────────────────────────────────────────────────────────
    # When the proposal mixes kitchen types / utility conditions, attribute each
    # note to its option so the customer knows which term applies to which unit.
    def _util_note(o):
        cat    = o['category']
        gas_ni = o.get('gas_not_included', False)
        if cat == 'EK' and not gas_ni:
            return None   # all-inclusive EK — nothing to mention
        if cat == 'EK' and gas_ni:
            return ("EK is all inclusive except for direct gas, which is individually metered "
                    "and billed directly by the gas authority based on consumption.")
        if cat == 'Standard':
            return ("Gas and electricity (5 kw per kitchen) are individually metered for each unit, "
                    "and charged based on actual consumption.")
        if cat == 'Cuisinette' and gas_ni:
            return ("CUI is all inclusive except for direct gas, which is individually metered "
                    "and billed directly by the gas authority based on consumption.")
        return None   # all-inclusive Cuisinette — nothing to mention

    util_notes = [_util_note(o) for o in options]

    # Decide whether attribution is needed: multi-option with differing conditions
    mixed_utility = is_multi and len(set(
        (o['category'], bool(o.get('gas_not_included'))) for o in options
    )) > 1

    # EK/CUI notes collected separately — rendered AFTER the 2.95% line
    ek_cui_notes = []

    if mixed_utility:
        seen_un = set()
        for o, un in zip(options, util_notes):
            if un and o['category'] == 'Standard' and un not in seen_un:
                notes.append(un)
                seen_un.add(un)
        if any(o['category'] == 'Standard' for o in options):
            notes.append("Estimated shared utilities AED 2,000–5,000/month "
                         "(covers all service charges and AMCs).")
        for o, un in zip(options, util_notes):
            if un and o['category'] != 'Standard' and un not in seen_un:
                ek_cui_notes.append(un)   # deferred — goes after 2.95%
                seen_un.add(un)
    else:
        all_ek      = all(o['category'] == 'EK'       for o in options)
        any_standard= any(o['category'] == 'Standard' for o in options)
        gas_ni_any  = any(o.get('gas_not_included')    for o in options)

        if all_ek and not gas_ni_any:
            pass  # all-inclusive EK — nothing to mention
        elif gas_ni_any:
            ek_cui_notes.append(
                "Utilities are included except for direct gas, which is individually metered "
                "and billed directly by the gas authority based on actual consumption.")
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

    # EK/CUI utility notes — always after 2.95%
    for note in ek_cui_notes:
        rows.append(f'<tr><td colspan="{col_span}" class="nt">{_esc(note)}</td></tr>')

    # ── Location-specific notes ───────────────────────────────────────────────
    # Attribute to option label when multiple locations are involved.
    multi_loc = is_multi and len(set(o['location_display'] for o in options)) > 1
    seen_loc_notes = set()
    for o in options:
        for ln in o.get('location_notes', []):
            key = ln  # deduplicate by text across options at same location
            if key not in seen_loc_notes:
                prefix = f"{o['label']}: " if multi_loc else ""
                rows.append(f'<tr><td colspan="{col_span}" class="nt">{_esc(prefix + ln)}</td></tr>')
                seen_loc_notes.add(key)

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


_CHROMIUM_CANDIDATES = [
    '/usr/bin/chromium',
    '/usr/bin/chromium-browser',
    '/usr/bin/google-chrome',
    '/usr/bin/google-chrome-stable',
]

def _chromium_exe():
    for p in _CHROMIUM_CANDIDATES:
        if os.path.exists(p):
            return p
    raise RuntimeError(
        "No Chromium/Chrome binary found. "
        "Ensure 'chromium' is listed in packages.txt."
    )

def _full_html(html: str) -> str:
    return (
        '<!DOCTYPE html><html><head><meta charset="utf-8"></head>'
        '<body style="margin:24px;background:white;">'
        f'{html}</body></html>'
    )

def _playwright_page(pw, viewport_width=860):
    exe = _chromium_exe()
    browser = pw.chromium.launch(
        executable_path=exe,
        args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'],
    )
    page = browser.new_page(viewport={'width': viewport_width, 'height': 800})
    return browser, page


def export_pdf(html: str, path: str):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser, page = _playwright_page(pw)
        page.set_content(_full_html(html), wait_until='domcontentloaded')
        page.pdf(
            path=path,
            format='A4',
            print_background=True,
            margin={'top': '15mm', 'bottom': '15mm', 'left': '12mm', 'right': '12mm'},
        )
        browser.close()
    return path


def export_image(html: str, path: str):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        exe = _chromium_exe()
        browser = pw.chromium.launch(
            executable_path=exe,
            args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'],
        )
        # Use a very tall viewport so all content (including charts) is laid out
        page = browser.new_page(viewport={'width': 900, 'height': 6000})
        page.set_content(_full_html(html), wait_until='load')
        # Wait for all images (base64 charts) to finish painting
        page.wait_for_function(
            "() => Array.from(document.images).every(img => img.complete && img.naturalHeight > 0)"
        )
        page.wait_for_timeout(200)  # brief settle for layout reflow
        # Measure tight content bounds
        content_height = page.evaluate("""() => {
            const children = document.body.children;
            if (!children.length) return document.body.scrollHeight;
            const last = children[children.length - 1];
            return Math.ceil(last.getBoundingClientRect().bottom) + 24;
        }""")
        content_width = page.evaluate("() => document.body.scrollWidth")
        page.screenshot(
            path=path,
            clip={'x': 0, 'y': 0, 'width': content_width, 'height': content_height},
        )
        browser.close()
    return path
