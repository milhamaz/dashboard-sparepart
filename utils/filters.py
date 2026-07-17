# ============================================================
# 🎛️ SHARED SIDEBAR FILTERS
# ============================================================
import streamlit as st
from utils.data_loader import list_bulan_standar


def render_sidebar(df_order, df_supply):
    """Render sidebar filters dan return filtered dataframes + selections."""
    st.sidebar.markdown("### 🎛️ Filter General")

    tahun_list = sorted(df_order["Tahun"].dropna().unique())
    pilih_tahun = st.sidebar.selectbox("📅 Tahun", tahun_list, index=len(tahun_list) - 1)
    pilih_bulan = st.sidebar.multiselect("📆 Bulan", list_bulan_standar, default=list_bulan_standar)

    area_list = sorted(df_order["Kode_Area"].dropna().unique())
    pilih_area = st.sidebar.multiselect("🌐 Area Operation", area_list, default=area_list)

    mask_base_order = (df_order["Tahun"] == pilih_tahun) & (df_order["Bulan"].isin(pilih_bulan)) & (df_order["Kode_Area"].isin(pilih_area))
    mask_base_supply = (df_supply["Tahun"].isin([pilih_tahun, pilih_tahun - 1])) & (df_supply["Bulan"].isin(pilih_bulan)) & (df_supply["Kode_Area"].isin(pilih_area))

    df_order_f1 = df_order[mask_base_order]
    df_supply_f1 = df_supply[mask_base_supply]

    cabang_list = sorted(df_order_f1["Cabang"].dropna().unique())
    pilih_cabang = st.sidebar.multiselect("🏢 Cabang", cabang_list, default=cabang_list)

    df_order_f2 = df_order_f1[df_order_f1["Cabang"].isin(pilih_cabang)]
    df_supply_f2 = df_supply_f1[df_supply_f1["Cabang"].isin(pilih_cabang)]

    jenis_list = sorted(df_order_f2["Jenis_Customer"].dropna().unique())
    pilih_jenis = st.sidebar.multiselect("👤 Jenis Customer", jenis_list, default=jenis_list)

    kelas_list = sorted(df_order_f2[df_order_f2["Jenis_Customer"].isin(pilih_jenis)]["Kelas_Customer"].dropna().unique())
    pilih_kelas = st.sidebar.multiselect("⭐ Kelas Customer", kelas_list, default=kelas_list)

    st.sidebar.divider()
    st.sidebar.caption("Built with Streamlit + Plotly | Updated (2026)")
    st.sidebar.caption("*Data isn't actual numbers, for display purposes only*")
    st.sidebar.caption("*Created by Ilham (2026)*")

    mask_cust = lambda df: (df["Jenis_Customer"].isin(pilih_jenis)) & (df["Kelas_Customer"].isin(pilih_kelas))
    df_order_final = df_order_f2[mask_cust(df_order_f2)].copy()
    df_supply_final = df_supply_f2[mask_cust(df_supply_f2)].copy()

    return df_order_final, df_supply_final, pilih_tahun, pilih_bulan, pilih_cabang