# ============================================================
# 🤝 PAGE: CUSTOMER (RETENTION/CHURN & ALERT PENURUNAN)
# ============================================================
import streamlit as st
from utils.data_loader import load_and_process_data, compute_data_fingerprint
from utils.filters import render_top_filters
from utils.styles import inject_styles, fmt_rp
from utils.components import render_nav_bar, render_footer
from views import tab_customer_retention, tab_customer_alert, tab_suggested_status, tab_customer_target, tab_odom

st.set_page_config(page_title="Customer", page_icon="🤝", layout="wide", initial_sidebar_state="collapsed")

inject_styles()

st.markdown(
    '<h1 style="color: white; text-align: center; font-size: 24px;">Customer</h1>',
    unsafe_allow_html=True
)

render_nav_bar("customer")

# ── Load Data ──
(df_order, df_supply, df_target, df_tmo_lookup, df_topt_lookup,
 df_chem_lookup, df_tgb_lookup, df_7kp_lookup, df_dprog_lookup, df_kalkerja,
 df_7kp_prefix, df_customer_master) = load_and_process_data(compute_data_fingerprint())

# ── Filter General ──
df_order_final, df_supply_final, pilih_tahun, pilih_bulan, pilih_cabang, pilih_jenis, pilih_kelas, pilih_area, cabang_list = render_top_filters(df_order, df_supply, page_key="customer")

# ── Tabs ──
tab_target_customer_ui, tab_odom_ui, tab_retention_ui, tab_alert_ui, tab_suggested_status_ui = st.tabs(
    ["📊 Target Customer", "📅 ODOM", "🔄 Retention & Churn", "🚨 Alert Penurunan", "🎯 Suggested Status"]
)

with tab_target_customer_ui:
    tab_customer_target.render(
        df_order, df_supply_final, df_target, df_customer_master, pilih_tahun, pilih_bulan,
        pilih_jenis, pilih_kelas, pilih_area, pilih_cabang, cabang_list, fmt_rp,
    )

with tab_odom_ui:
    tab_odom.render(df_order_final, df_kalkerja, pilih_tahun, pilih_bulan)

with tab_retention_ui:
    tab_customer_retention.render(df_supply_final, pilih_tahun)

with tab_alert_ui:
    tab_customer_alert.render(df_supply_final, pilih_tahun)

with tab_suggested_status_ui:
    tab_suggested_status.render(
        df_customer_master, df_supply, pilih_jenis, pilih_kelas, pilih_area, pilih_cabang,
    )

render_footer()
