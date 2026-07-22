# ============================================================
# 📊 PAGE: ANALISA PARTNUMBER (merged from Analisa Produk + Operasional Partnumber)
# ============================================================
import streamlit as st
from utils.data_loader import load_and_process_data, compute_data_fingerprint, load_part_master
from utils.styles import inject_styles
from utils.components import render_nav_bar, render_footer
from views import tab_komposisi, tab_profitabilitas, tab_moving
from views.tab_kelebaran_kedalaman import render_kelebaran, render_kedalaman

st.set_page_config(page_title="Analisa Partnumber", page_icon="📊", layout="wide", initial_sidebar_state="collapsed")

inject_styles()

st.markdown(
    '<h1 style="color: white; text-align: center; font-size: 24px;">Analisa Partnumber</h1>',
    unsafe_allow_html=True
)

render_nav_bar("partnumber")

# ── Load Data ──
(df_order, df_supply, df_target, df_tmo_lookup, df_topt_lookup,
 df_chem_lookup, df_tgb_lookup, df_7kp_lookup, df_dprog_lookup, df_kalkerja,
 df_7kp_prefix, _df_customer_master) = load_and_process_data(compute_data_fingerprint())

df_part_master = load_part_master(compute_data_fingerprint())

if df_supply is None or df_supply.empty:
    st.warning("Data Supply belum siap.")
    st.stop()

# ── Tabs ──
tab_komposisi_ui, tab_profit_ui, tab_moving_ui, tab_lebar_ui, tab_dalam_ui = st.tabs(
    ["🧬 Komposisi Kategori", "💰 Profitabilitas", "📦 Moving Analysis", "📐 Kelebaran", "📏 Kedalaman"]
)

with tab_komposisi_ui:
    tab_komposisi.render(df_supply, df_part_master)

with tab_profit_ui:
    tab_profitabilitas.render(df_supply)

with tab_moving_ui:
    tab_moving.render(df_supply)

with tab_lebar_ui:
    render_kelebaran(df_order)

with tab_dalam_ui:
    render_kedalaman(df_order)

render_footer()
