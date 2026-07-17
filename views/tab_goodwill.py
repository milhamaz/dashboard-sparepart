# ============================================================
# ♻️ TAB: GOODWILL
# ============================================================
import pandas as pd
import streamlit as st

from utils.components import (
    TOTAL_ROW_STYLE, auto_table_height, build_pivot, classify_claim_goodwill,
    cleanup_selection, render_qty_heatmap,
)
from utils.data_loader import list_bulan_standar

FMT_RP = lambda x: f"Rp {x:,.0f}".replace(",", ".")


def render(df_supply):
    if df_supply is None or df_supply.empty:
        st.warning("Data Supply belum siap.")
        return
    if "Invoice_No" not in df_supply.columns:
        st.warning("Kolom Invoice_No tidak ditemukan di data Supply.")
        return

    _, df_goodwill = classify_claim_goodwill(df_supply)

    st.caption(
        "Goodwill = barang retur defect ringan yang tetap masuk inventory cabang (Qty minus, "
        "Invoice No mengandung \"G-RJUL\"). Qty dianggap reset tiap bulan (tidak akumulatif antar bulan)."
    )

    tahun_list = sorted(df_supply["Tahun"].dropna().unique().tolist())
    if not tahun_list:
        st.info("Belum ada data Supply.")
        return
    tahun_terbaru = tahun_list[-1]

    col_tahun, col_area = st.columns(2)
    with col_tahun:
        tahun_options = [str(t) for t in tahun_list]
        pilih_tahun_raw = st.pills(
            "Pilih Tahun", tahun_options, selection_mode="single",
            default=str(tahun_terbaru), key="gw_tahun",
        )
    pilih_tahun = int(pilih_tahun_raw) if pilih_tahun_raw else tahun_terbaru

    area_options = sorted(df_supply["Kode_Area"].dropna().unique().tolist())
    area_key = "gw_area"
    cleanup_selection(area_key, area_options)
    with col_area:
        pilih_area = st.pills("Filter Area (slicer)", area_options, selection_mode="multi", key=area_key) or []

    df_goodwill_scope = df_goodwill[df_goodwill["Tahun"] == pilih_tahun]
    if pilih_area:
        df_goodwill_scope = df_goodwill_scope[df_goodwill_scope["Kode_Area"].isin(pilih_area)]

    if df_goodwill_scope.empty:
        st.info(f"Tidak ada data Goodwill untuk tahun {pilih_tahun}.")
        return

    st.markdown("**Nilai Goodwill (Rp)**")
    pivot_value = build_pivot(df_goodwill_scope, "Cabang", "Bulan", list_bulan_standar, "Goodwill_Value", "sum")
    styled = pivot_value.style.format(FMT_RP).set_properties(
        **{'text-align': 'right', 'font-size': '13px'}
    ).set_properties(
        subset=pd.IndexSlice[:, "TOTAL"], **{'font-weight': 'bold', 'background-color': 'rgba(245, 158, 11, 0.08)'}
    ).set_properties(
        subset=pd.IndexSlice["TOTAL", :], **TOTAL_ROW_STYLE
    )
    st.dataframe(styled, use_container_width=True, height=auto_table_height(len(pivot_value)))

    st.markdown("**Qty Goodwill — Seluruh Cabang**")
    render_qty_heatmap(df_goodwill_scope, "Goodwill_Qty", group_col="Cabang", month_col="Bulan", key="gw_qty_heatmap")
