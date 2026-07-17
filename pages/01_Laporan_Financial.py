# ============================================================
# 📦 PAGE: LAPORAN FINANCIAL
# ============================================================
import streamlit as st
from utils.data_loader import load_and_process_data, compute_data_fingerprint
from utils.filters import render_sidebar
from utils.styles import inject_styles, fmt_rp, fmt_liter, highlight_pct
from views import tab_performance, tab_tmo, tab_chemical, tab_tgb, tab_topt, tab_pacing

st.set_page_config(page_title="Laporan Financial", page_icon="📦", layout="wide")

st.markdown(
    '<h1 style="color: white; text-align: center; font-size: 24px;">Laporan Financial</h1>',
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
tab_perf, tab_pacing_ui, tab_tmo_ui, tab_chem_ui, tab_battery_ui, tab_topt_ui = st.tabs(
    ["📊 Performance", "📈 Pacing", "🛢️ TMO", "🧪 Chemical", "🔋 TGB", "🔧 T-OPT"]
)

with tab_perf:
    tab_performance.render(df_order_final, df_supply_final, df_target, pilih_tahun, pilih_bulan, pilih_cabang, fmt_rp, highlight_pct)

with tab_pacing_ui:
    tab_pacing.render(df_order, df_target, df_kalkerja)

with tab_tmo_ui:
    tab_tmo.render(df_order_final, df_supply_final, df_tmo_lookup, pilih_tahun, pilih_bulan, fmt_liter, highlight_pct)

with tab_chem_ui:
    tab_chemical.render(df_order_final, df_supply_final, df_chem_lookup, pilih_tahun, pilih_bulan, fmt_rp, highlight_pct)

with tab_battery_ui:
    tab_tgb.render(df_order_final, df_supply_final, df_tgb_lookup, pilih_tahun, pilih_bulan, highlight_pct)

with tab_topt_ui:
    tab_topt.render(df_order_final, df_supply_final, df_topt_lookup, pilih_tahun, pilih_bulan, fmt_rp, highlight_pct)
