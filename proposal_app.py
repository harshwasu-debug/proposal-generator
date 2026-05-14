import streamlit as st
import pandas as pd
import os, sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.data_loader import (
    get_available_kitchens, get_churning_kitchens,
    kitchen_category, get_utility_estimate,
    get_similar_location_utility,
    get_default_license, UTILITY_PREFIX_MAP,
    LOCATION_SPECIFIC_NOTES, GAS_NOT_INCLUDED
)
from utils.calculations import calc_activation_amount, calc_deposit, is_waived, calc_total, round_to_50
from utils.proposal_renderer import render_proposal_html, export_html_file, export_pdf, export_image
from utils.chart_generator import generate_utility_chart_base64, generate_utility_chart_streamlit

st.set_page_config(page_title="SF Proposal Generator", layout="wide", page_icon="🍽️")

EXPORTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exports")
os.makedirs(EXPORTS_DIR, exist_ok=True)

LICENSE_OPTIONS = ["DMCC TL", "DET TL", "DET TL + Kiosk Permit", "TL + Kiosk Permit", "Other"]

@st.cache_data
def load_data():
    return get_available_kitchens()

@st.cache_data
def load_churning():
    return get_churning_kitchens()

df_all   = load_data()
df_churn = load_churning()

if 'proposal_options' not in st.session_state:
    st.session_state.proposal_options = []

tab_proposal, tab_availability = st.tabs(["📄 Proposal Generator", "📅 Kitchen Availability"])

# ==============================================================================
# TAB 1 - PROPOSAL GENERATOR
# ==============================================================================
with tab_proposal:
    st.title("Kitchen Proposal Generator")

    # Step 1: Build option list
    st.subheader("Step 1 — Add Kitchen Options")
    st.caption("Each option becomes a column in the proposal. Options can be from different locations.")

    with st.container(border=True):
        add_col1, add_col2, add_col3, add_col4 = st.columns([2, 1, 3, 1])
        with add_col1:
            locations = sorted(df_all['Account Name'].unique())
            add_loc   = st.selectbox("Location", locations, key="add_loc")
        loc_df_add = df_all[df_all['Account Name'] == add_loc]
        with add_col2:
            ktypes   = sorted(loc_df_add['Type'].unique())
            add_type = st.selectbox("Type", ktypes, key="add_type")
        type_df_add    = loc_df_add[loc_df_add['Type'] == add_type]
        existing_units = [o['unit_name'] for o in st.session_state.proposal_options]
        available      = [u for u in type_df_add['Kitchen Number Name'].tolist() if u not in existing_units]
        with add_col3:
            add_unit = st.selectbox("Unit", available if available else ["— no units available —"], key="add_unit")
        with add_col4:
            st.write("")
            st.write("")
            if st.button("Add Option", type="primary", disabled=(not available)):
                st.session_state.proposal_options.append({
                    'account_name': add_loc,
                    'kitchen_type': add_type,
                    'unit_name':    add_unit,
                })
                st.rerun()

    if st.session_state.proposal_options:
        st.markdown("**Current options in this proposal:**")
        for i, opt in enumerate(st.session_state.proposal_options):
            r1, r2 = st.columns([8, 1])
            with r1:
                st.markdown(f"**Option {i+1}:** {opt['unit_name']}  —  {opt['account_name']}")
            with r2:
                if st.button("X", key=f"remove_{i}"):
                    st.session_state.proposal_options.pop(i)
                    st.rerun()
        if st.button("Clear all options"):
            st.session_state.proposal_options = []
            st.rerun()
    else:
        st.info("No options added yet. Add at least one kitchen unit above.")

    options = st.session_state.proposal_options

    if options:
        # Step 2: Global settings
        st.subheader("Step 2 — Global Settings")
        g_col1, g_col2 = st.columns(2)
        with g_col1:
            validity_date = st.date_input("Offer valid till", value=date.today() + timedelta(days=14))
        with g_col2:
            waive_all     = st.checkbox("Waive activation fee for all options")
            show_mall     = st.checkbox("Mall / shopping centre note")
            show_dinein   = st.checkbox("Dine-in note (10%)")
            include_chart = st.checkbox("Include utility chart in export", value=True)

        comments = st.text_area(
            "Comments (optional) — each line appears as a separate note in the proposal",
            height=80,
            placeholder="e.g. Special move-in terms apply. Storage space available upon request."
        )

        # Step 3: Per-option configuration
        st.subheader("Step 3 — Per-option Details")
        options_data    = []
        chart_b64_map   = {}
        seen_util_for_loc = {}   # acc_name -> utility_val (one estimator per location)

        for i, opt in enumerate(options):
            acc_name     = opt['account_name']
            kitchen_type = opt['kitchen_type']
            unit_name    = opt['unit_name']
            cat          = kitchen_category(acc_name)

            _match = df_all[df_all['Kitchen Number Name'] == unit_name]
            if _match.empty:
                st.error(
                    f"**Option {i+1} — '{unit_name}'** is no longer in the available inventory "
                    f"(it may have been leased or removed). Please click **X** to remove it and add a new option."
                )
                continue
            unit_row = _match.iloc[0]
            size     = unit_row.get('Kitchen Size (Sq. Meters)', '')
            hood     = unit_row.get('Hood Size', '')
            floor_p  = float(unit_row.get('Floor Price') or 0)
            list_p   = float(unit_row.get('List Price') or 0)
            churn_dt = unit_row.get('Churn date')
            status   = unit_row.get('Status', '')

            first_at_loc = acc_name not in seen_util_for_loc

            with st.expander(f"Option {i+1}: {unit_name}  [{status}]", expanded=True):

                # Utility estimator — show once per location only
                util_data = get_utility_estimate(acc_name, kitchen_type)
                if first_at_loc and util_data and cat != 'EK':
                    with st.container(border=True):
                        st.markdown(f"**Utility Estimator — {acc_name} ({kitchen_type})**")
                        u_c1, u_c2, u_c3 = st.columns(3)
                        u_c1.metric("Lowest (12m)",  f"AED {util_data['lowest']:,}")
                        u_c2.metric("Average (12m)", f"AED {util_data['average']:,}")
                        u_c3.metric("Highest (12m)", f"AED {util_data['highest']:,}")
                        chart_fig, _ = generate_utility_chart_streamlit(acc_name, kitchen_type)
                        if chart_fig:
                            st.pyplot(chart_fig, use_container_width=True)
                            if include_chart:
                                b64 = generate_utility_chart_base64(acc_name, kitchen_type)
                                if b64:
                                    loc_label  = (acc_name
                                        .replace("UAE - DXB - ", "").replace("UAE - AD - ", "")
                                        .replace("UAE - SHJ - ", "").replace("UAE - AN - ", ""))
                                    unit_label = unit_name.split(' - UAE')[0].strip() if ' - UAE' in unit_name else unit_name
                                    chart_b64_map[i] = (b64, f"{loc_label} — {unit_label}")

                st.divider()
                c1, c2 = st.columns(2)

                with c1:
                    raw_num = unit_name.split(' - UAE')[0].strip() if ' - UAE' in unit_name else unit_name
                    default_specs = f"{raw_num}\n{size} sqm / {hood} hood"
                    if status == 'Churning' and churn_dt:
                        try:
                            churn_str = pd.to_datetime(churn_dt).strftime("from %d/%m/%Y")
                            default_specs = f"{raw_num} {churn_str}\n{size} sqm / {hood} hood"
                        except:
                            pass
                    unit_specs = st.text_area("Unit specs", value=default_specs, height=80, key=f"specs_{i}")

                    default_display = (
                        acc_name
                        .replace("UAE - DXB - ", "")
                        .replace("UAE - AD - ", "")
                        .replace("UAE - SHJ - ", "")
                        .replace("UAE - AN - ", "")
                    )
                    loc_display  = st.text_area("Location display text", value=default_display, height=70, key=f"loc_{i}")
                    default_lic  = get_default_license(acc_name)
                    lic_idx      = LICENSE_OPTIONS.index(default_lic) if default_lic in LICENSE_OPTIONS else 2
                    license_type = st.selectbox("Required License", LICENSE_OPTIONS, index=lic_idx, key=f"lic_{i}")

                    if cat in ('EK', 'Cuisinette'):
                        deposit_multiplier = st.select_slider(
                            "Deposit multiplier", options=[1.2, 1.3, 1.4, 1.5, 1.6], value=1.4, key=f"dep_mul_{i}"
                        )
                    else:
                        deposit_multiplier = 2.0

                with c2:
                    opt_price_mode = st.radio(
                        "Price to quote",
                        ["List Price", "Floor Price", "Custom (% discount on List)"],
                        horizontal=True, key=f"pm_{i}"
                    )
                    if opt_price_mode == "Custom (% discount on List)":
                        disc_pct  = st.slider("Discount on List (%)", 0, 40, 5, 1, key=f"disc_{i}")
                        base_rent = round_to_50(list_p * (1 - disc_pct / 100))
                        if base_rent < floor_p:
                            st.warning(f"Discounted price AED {base_rent:,.0f} is below floor AED {floor_p:,.0f}. Clamped to floor.")
                            base_rent = floor_p
                    elif opt_price_mode == "Floor Price":
                        base_rent = floor_p
                    else:
                        base_rent = list_p

                    st.caption(f"Floor: AED {floor_p:,.0f}  |  List: AED {list_p:,.0f}")
                    rent = st.number_input("Monthly rent (AED)", value=float(base_rent), min_value=float(floor_p), step=100.0, key=f"rent_{i}_{opt_price_mode}")

                    if cat in ('EK', 'Cuisinette'):
                        utility_val = 0
                        if first_at_loc:
                            st.info(f"{cat} — utilities included (AED 0).")
                    elif not first_at_loc:
                        # Inherit utility value from the first option at this location
                        utility_val = seen_util_for_loc.get(acc_name)
                        if utility_val is not None:
                            st.caption(f"Utility estimate: AED {utility_val:,.0f} (shared with first option at this location)")
                        else:
                            st.caption("Utility estimate: TBA (shared with first option at this location)")
                    elif util_data:
                        util_choice = st.selectbox(
                            "Utility estimate to show in proposal",
                            ["Average (12m)", "Lowest", "Highest", "Manual entry", "No data / TBA"],
                            key=f"util_mode_{i}"
                        )
                        if util_choice == "Average (12m)":
                            utility_val = util_data['average']
                        elif util_choice == "Lowest":
                            utility_val = util_data['lowest']
                        elif util_choice == "Highest":
                            utility_val = util_data['highest']
                        elif util_choice == "Manual entry":
                            utility_val = st.number_input("Utility (AED)", value=float(util_data['average']), step=100.0, key=f"util_v_{i}")
                        else:
                            utility_val = None
                    else:
                        st.warning("No utility data for this location.")
                        util_choice = st.selectbox(
                            "Utility estimate",
                            ["Manual entry", "Use similar location", "No data / TBA"],
                            key=f"util_mode_{i}"
                        )
                        if util_choice == "Manual entry":
                            utility_val = st.number_input("Utility (AED)", value=3000.0, step=100.0, key=f"util_v_{i}")
                        elif util_choice == "Use similar location":
                            similar  = get_similar_location_utility(kitchen_type)
                            sim_locs = list(similar.keys())
                            if sim_locs:
                                sim_loc  = st.selectbox("Similar location", sim_locs, key=f"sim_{i}")
                                sim_d    = similar[sim_loc]
                                st.caption(f"Avg: AED {sim_d['average']:,}  |  Low: AED {sim_d['lowest']:,}  |  High: AED {sim_d['highest']:,}")
                                sim_pick    = st.selectbox("Use", ["Average", "Lowest", "Highest"], key=f"sim_pick_{i}")
                                utility_val = sim_d['average'] if sim_pick == "Average" else sim_d['lowest'] if sim_pick == "Lowest" else sim_d['highest']
                            else:
                                utility_val = None
                        else:
                            utility_val = None

                    # Store utility val for this location after first encounter
                    if first_at_loc and cat != 'EK':
                        seen_util_for_loc[acc_name] = utility_val

                    per_unit_waive = st.checkbox("Waive activation fee", value=waive_all, key=f"waive_{i}")

                activation_display = calc_activation_amount(rent, cat)
                waived             = is_waived(license_type, per_unit_waive or waive_all)
                activation_fee     = 0.0 if waived else activation_display
                deposit            = calc_deposit(rent, cat, deposit_multiplier)
                total              = calc_total(deposit, activation_fee)

                st.markdown(
                    f"**Deposit:** AED {deposit:,.0f} &nbsp;|&nbsp; "
                    f"**Activation:** {'Waived' if waived else f'AED {activation_fee:,.0f}'} &nbsp;|&nbsp; "
                    f"**Total to book:** AED {total:,.0f}"
                )

                options_data.append({
                    'label':              f"Option {i+1}",
                    'location_display':   loc_display,
                    'license':            license_type,
                    'unit_specs':         unit_specs,
                    'rent':               rent,
                    'utility_estimate':   utility_val,
                    'deposit':            deposit,
                    'activation_fee':     activation_fee,
                    'activation_display': activation_display,
                    'activation_waived':  waived,
                    'total':              total,
                    'category':           cat,
                    'gas_not_included':   acc_name in GAS_NOT_INCLUDED,
                    'location_notes':     LOCATION_SPECIFIC_NOTES.get(acc_name, []),
                })

        # Step 4: Preview & Export
        st.subheader("Step 4 — Preview & Export")
        config = {
            'validity_date':     validity_date.strftime("%d %B %Y"),
            'show_mall_note':    show_mall,
            'show_dine_in_note': show_dinein,
            'comments':          comments,
        }
        proposal_html = render_proposal_html(options_data, config, chart_b64_map if include_chart else None)
        st.components.v1.html(proposal_html, height=780, scrolling=True)

        st.divider()
        proposal_for = st.text_input(
            "Proposal for",
            placeholder="e.g. Acme Restaurants LLC or John Smith",
            help="Used as the exported file name."
        )
        safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in proposal_for).strip() or "proposal"

        exp_col1, exp_col2 = st.columns([1, 2])
        with exp_col1:
            export_fmt = st.radio("Export format", ["PDF", "Image (PNG)", "Email HTML"])
        with exp_col2:
            if st.button("Generate & Download", type="primary"):
                if export_fmt == "Email HTML":
                    out = os.path.join(EXPORTS_DIR, f"{safe_name}.html")
                    export_html_file(proposal_html, out)
                    with open(out, 'rb') as f:
                        st.download_button("Download HTML", f, file_name=f"{safe_name}.html", mime="text/html")
                elif export_fmt == "PDF":
                    try:
                        out = os.path.join(EXPORTS_DIR, f"{safe_name}.pdf")
                        export_pdf(proposal_html, out)
                        with open(out, 'rb') as f:
                            st.download_button("Download PDF", f, file_name=f"{safe_name}.pdf", mime="application/pdf")
                    except Exception as e:
                        st.error(f"PDF export failed: {e}")
                elif export_fmt == "Image (PNG)":
                    try:
                        out = os.path.join(EXPORTS_DIR, f"{safe_name}.png")
                        export_image(proposal_html, out)
                        with open(out, 'rb') as f:
                            st.download_button("Download PNG", f, file_name=f"{safe_name}.png", mime="image/png")
                    except Exception as e:
                        st.error(f"Image export failed: {e}")

# ==============================================================================
# TAB 2 - KITCHEN AVAILABILITY
# ==============================================================================
with tab_availability:
    st.title("Kitchen Availability")

    try:
        disp_cols  = ['Account Name', 'Type', 'Kitchen Number Name', 'Kitchen Size (Sq. Meters)', 'Hood Size', 'Floor Price', 'List Price', 'Floor']
        churn_cols = ['Account Name', 'Type', 'Kitchen Number Name', 'Kitchen Size (Sq. Meters)', 'Hood Size', 'Floor Price', 'List Price', 'Churn date']

        f1, f2, f3 = st.columns([2, 1, 1])
        with f1:
            search_term = st.text_input("Search by location or unit name", placeholder="e.g. JLT, DSO, K05...")
        with f2:
            filter_type = st.selectbox("Kitchen Type", ["All", "Hot Kitchen", "Cold Kitchen"])
        with f3:
            filter_loc = st.selectbox("Location", ["All"] + sorted(df_all['Account Name'].unique()))

        def apply_filters(df):
            if search_term:
                mask = (
                    df['Account Name'].str.contains(search_term, case=False, na=False) |
                    df['Kitchen Number Name'].str.contains(search_term, case=False, na=False)
                )
                df = df[mask]
            if filter_type != "All":
                df = df[df['Type'] == filter_type]
            if filter_loc != "All":
                df = df[df['Account Name'] == filter_loc]
            return df

        st.subheader("Currently Vacant")
        vacant_df = apply_filters(df_all[df_all['Status'] == 'Vacant'].copy())
        if vacant_df.empty:
            st.info("No vacant kitchens match the current filters.")
        else:
            st.dataframe(vacant_df[disp_cols].sort_values('Account Name').reset_index(drop=True), use_container_width=True, height=320)
            st.caption(f"{len(vacant_df)} unit(s) shown")

        st.subheader("Upcoming Availability (Churning)")
        churn_filtered = apply_filters(df_churn.copy())
        if churn_filtered.empty:
            st.info("No churning kitchens match the current filters.")
        else:
            churn_display = churn_filtered[churn_cols].copy()
            churn_display['Churn date'] = pd.to_datetime(churn_display['Churn date'], errors='coerce').dt.strftime('%d %b %Y')
            st.dataframe(churn_display.sort_values('Churn date').reset_index(drop=True), use_container_width=True, height=280)
            st.caption(f"{len(churn_display)} unit(s) shown")

        st.subheader("Availability by Location")
        summary = df_all.groupby(['Account Name', 'Status']).size().unstack(fill_value=0).reset_index()
        st.dataframe(summary, use_container_width=True)

    except Exception as e:
        st.error(f"Error loading availability data: {e}")
        st.exception(e)
