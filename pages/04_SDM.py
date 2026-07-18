# ============================================================
# 👥 PAGE: SDM (SALESMAN LEADERBOARD & CABANG SCORECARD)
# ============================================================
import streamlit as st
from utils.data_loader import load_and_process_data, compute_data_fingerprint
from utils.filters import render_top_filters
from utils.styles import inject_styles, fmt_rp
from utils.components import render_nav_bar, render_footer
from views import tab_salesman_leaderboard, tab_cabang_scorecard, tab_target_salesman

st.set_page_config(page_title="SDM", page_icon="👥", layout="wide", initial_sidebar_state="collapsed")

inject_styles()

st.markdown(
    '<h1 style="color: white; text-align: center; font-size: 24px;">SDM</h1>',
    unsafe_allow_html=True
)

render_nav_bar("sdm")

# ── Load Data ──
(df_order, df_supply, df_target, df_tmo_lookup, df_topt_lookup,
 df_chem_lookup, df_tgb_lookup, df_7kp_lookup, df_dprog_lookup, df_kalkerja,
 df_7kp_prefix, df_customer_master) = load_and_process_data(compute_data_fingerprint())

# ── Filter General ──
df_order_final, df_supply_final, pilih_tahun, pilih_bulan, pilih_cabang, pilih_jenis, pilih_kelas, pilih_area = render_top_filters(df_order, df_supply, page_key="sdm")

# ── Tabs ──
tab_salesman_ui, tab_cabang_ui, tab_target_salesman_ui = st.tabs(
    ["🏆 Salesman Leaderboard", "🏢 Cabang Scorecard", "🎯 Target Salesman"]
)

with tab_salesman_ui:
    tab_salesman_leaderboard.render(df_order_final, df_supply_final, pilih_tahun, fmt_rp)

with tab_cabang_ui:
    tab_cabang_scorecard.render(df_order_final, df_supply_final, df_target, pilih_tahun, pilih_bulan, pilih_cabang, fmt_rp)

with tab_target_salesman_ui:
    tab_target_salesman.render(
        df_order, df_target, df_customer_master, pilih_tahun, pilih_bulan,
        pilih_jenis, pilih_kelas, pilih_area, pilih_cabang, fmt_rp,
    )

render_footer()
