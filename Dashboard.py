# ============================================================
# 📊 DASHBOARD SPAREPART — MAIN ENTRY POINT (MULTIPAGE)
# ============================================================
import streamlit as st

st.set_page_config(
    page_title="Dashboard Sparepart",
    page_icon="🚗",
    layout="wide"
)

st.markdown(
    '<h1 style="color: white; text-align: center; font-size: 28px;">Dashboard Sparepart</h1>',
    unsafe_allow_html=True
)

st.markdown("---")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    ### Laporan Financial
    Analisis performa penjualan berdasarkan kategori material:
    - **Performance** — Revenue overall (Order, Supply, Target, Last Year)
    - **Pacing** — Staging harian vs target bulanan
    - **TMO** — Volume oli mesin (Liter)
    - **Chemical** — Revenue produk chemical
    - **TGB** — Quantity baterai (Pcs)
    - **T-OPT** — Revenue T-Genuine Optima Parts
    """)

with col2:
    st.markdown("""
    ### Marketing Program
    Monitoring program marketing aktif:
    - **7KP** — 7 Key Product (Brake Pad, Shock Absorber, Clutch, dll)
    - **Item D** — Program diskon bulanan + burn analysis
    - **Gebyur** — Volume TMO Campaign & budget linkage
    &nbsp;
    &nbsp;
    """)

with col3:
    st.markdown("""
    ### Analisa Partnumber
    Analisis mendalam per Partnumber & Claim Goodwill:
    - **Kelebaran** — Unique Partnumber yang di-order
    - **Kedalaman** — Total Qty yang di-order
    - **Claim** — Barang retur reject
    - **Goodwill** — Barang retur reject layak jual
    &nbsp;
    """)

b1, b2, b3 = st.columns(3)
with b1:
    if st.button("Buka Laporan Financial", use_container_width=True):
        st.switch_page("pages/01_Laporan_Financial.py")
with b2:
    if st.button("Buka Marketing Program", use_container_width=True):
        st.switch_page("pages/02_Marketing_Program.py")
with b3:
    if st.button("Buka Analisa Partnumber", use_container_width=True):
        st.switch_page("pages/3_Analisa_Partnumber.py")

st.sidebar.markdown("### Home")
st.sidebar.divider()
st.sidebar.caption("Built with Streamlit + Plotly | Updated (2026)")
st.sidebar.caption("*Data isn't actual numbers, for display purposes only*")
st.sidebar.caption("*Created by Ilham (2026)*")