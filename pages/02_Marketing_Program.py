# ============================================================
# 📢 PAGE: MARKETING PROGRAM
# ============================================================
import streamlit as st
from utils.data_loader import load_and_process_data, compute_data_fingerprint
from utils.filters import render_top_filters
from utils.styles import inject_styles, fmt_rp, fmt_liter, highlight_pct
from utils.components import render_nav_bar, render_footer
from views import tab_7kp, tab_dprog, tab_gebyur

st.set_page_config(page_title="Marketing Program", page_icon="📢", layout="wide", initial_sidebar_state="collapsed")

inject_styles()

st.markdown(
    '<h1 style="color: white; text-align: center; font-size: 24px;">Marketing Program</h1>',
    unsafe_allow_html=True
)

render_nav_bar("marketing")

# ── Load Data ──
(df_order, df_supply, df_target, df_tmo_lookup, df_topt_lookup,
 df_chem_lookup, df_tgb_lookup, df_7kp_lookup, df_dprog_lookup, df_kalkerja,
 df_7kp_prefix, _df_customer_master) = load_and_process_data(compute_data_fingerprint())

# ── Filter General ──
df_order_final, df_supply_final, pilih_tahun, pilih_bulan, pilih_cabang, pilih_jenis, pilih_kelas, pilih_area = render_top_filters(df_order, df_supply, page_key="marketing")

# ── Tabs ──
tab_7kp_ui, tab_dprog_ui, tab_gebyur_ui = st.tabs(
    ["🎯 7 Key Product", "🏷️ Item D", "🎁 Gebyur"]
)

with tab_7kp_ui:
    tab_7kp.render(df_order_final, df_supply_final, df_7kp_lookup, df_7kp_prefix, pilih_tahun, pilih_bulan, fmt_rp, highlight_pct)

with tab_dprog_ui:
    tab_dprog.render(df_order_final, df_supply_final, df_dprog_lookup, pilih_tahun, pilih_bulan, fmt_rp, highlight_pct)

with tab_gebyur_ui:
    tab_gebyur.render(df_order_final, df_tmo_lookup, df_dprog_lookup, pilih_bulan, fmt_rp, fmt_liter)

render_footer()