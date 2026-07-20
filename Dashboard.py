# ============================================================
# 📊 DASHBOARD SPAREPART — MAIN ENTRY POINT (MULTIPAGE)
# ============================================================
import streamlit as st
from utils.styles import inject_styles
from utils.components import render_footer

st.set_page_config(
    page_title="Dashboard Sparepart",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="collapsed",
)

inject_styles()

st.markdown(
    '<h1 style="color: white; text-align: center; font-size: 28px;">Dashboard Sparepart</h1>',
    unsafe_allow_html=True
)

st.markdown('<hr class="thick-divider">', unsafe_allow_html=True)

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
    - **COGS & Profit** — Estimasi profit nasional/cabang/salesman/customer
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
    - **Lead Time** — Durasi Order sampai Actual keluar gudang
    - **Fill Rate** — Kelengkapan Qty per pengiriman
    - **Status Fulfillment** — Status akhir tiap Order (akumulatif)
    - **Komposisi Kategori** — Sebaran & growth revenue per kategori produk (Mat Group)
    - **Substitusi Partnumber** — Migrasi volume kode lama → kode baru & kesehatannya
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
        st.switch_page("pages/03_Analisa_Partnumber.py")

col4, col5 = st.columns(2)

with col4:
    st.markdown("""
    ### SDM
    Performa internal perusahaan — orang & cabang:
    - **Target Cabang** — Achievement semua cabang vs target
    - **Target Salesman** — Achievement semua salesman vs target
    - **Cabang Leaderboard** — Ranking Actual & growth YoY per cabang
    - **Salesman Leaderboard** — Ranking Actual & growth YoY per salesman
    - **Productivity** — Revenue per customer aktif per salesman
    - **Segmentasi** — Archetype Cabang/Salesman (rule-based + validasi K-Means)
    """)

with col5:
    st.markdown("""
    ### Customer
    Performa eksternal — kesehatan basis customer:
    - **Target Customer** — Achievement customer vs target
    - **ODOM** — Kestabilan order harian (One Million One Day)
    - **Retention & Churn** — Customer bertahan/hilang/baru YoY
    - **Alert Penurunan** — Customer aktif dengan penurunan signifikan
    - **Cross-sell Gap** — Kategori lazim di peer yang belum digarap per customer
    - **Diversifikasi Produk** — Segmentasi ketergantungan customer ke 1 kategori
    - **Suggested Status** — Rekomendasi reaktivasi customer tidak aktif
    """)

b4, b5 = st.columns(2)
with b4:
    if st.button("Buka SDM", use_container_width=True):
        st.switch_page("pages/04_SDM.py")
with b5:
    if st.button("Buka Customer", use_container_width=True):
        st.switch_page("pages/05_Customer.py")

render_footer()