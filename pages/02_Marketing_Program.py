# ============================================================
# 📢 PAGE: MARKETING PROGRAM
# ============================================================
import streamlit as st
from utils.data_loader import load_and_process_data, compute_data_fingerprint
from utils.filters import render_sidebar
from utils.styles import inject_styles, fmt_rp, fmt_liter, highlight_pct
from views import tab_7kp, tab_dprog, tab_gebyur

st.set_page_config(page_title="Marketing Program", page_icon="📢", layout="wide")

st.markdown(
    '<h1 style="color: white; text-align: center; font-size: 24px;">Marketing Program</h1>',
    unsafe_allow_html=True
)

# ── Load Data ──
(df_order, df_supply, df_target, df_tmo_lookup, df_topt_lookup,
 df_chem_lookup, df_tgb_lookup, df_7kp_lookup, df_dprog_lookup, df_kalkerja,
 df_7kp_prefix) = load_and_process_data(compute_data_fingerprint())

# ── Sidebar Filters ──
df_order_final, df_supply_final, pilih_tahun, pilih_bulan, pilih_cabang = render_sidebar(df_order, df_supply)

# ── Styles ──
inject_styles()

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