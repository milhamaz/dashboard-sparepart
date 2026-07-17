# ============================================================
# 📤 TAB: CLAIM
# ============================================================
import pandas as pd
import streamlit as st

from utils.components import TOTAL_ROW_STYLE, auto_table_height, build_pivot, classify_claim_goodwill, cleanup_selection
from utils.data_loader import list_bulan_standar

FMT_RP = lambda x: f"Rp {x:,.0f}".replace(",", ".")


def render(df_supply):
    if df_supply is None or df_supply.empty:
        st.warning("Data Supply belum siap.")
        return
    if "Invoice_No" not in df_supply.columns:
        st.warning("Kolom Invoice_No tidak ditemukan di data Supply.")
        return

    df_claim, _ = classify_claim_goodwill(df_supply)
    df_claim["Salesman_Name"] = df_claim["Salesman_Name"].astype(str).str.strip().str.upper()
    df_claim["Customer_Name"] = df_claim["Customer_Name"].astype(str).str.strip().str.upper()

    st.caption(
        "Claim = barang retur karena defect/cacat (Qty minus, Invoice No **tidak** mengandung \"G-RJUL\"). "
        "Nilai Rupiah = |Qty × Retail Price / 1.11|."
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
            default=str(tahun_terbaru), key="claim_tahun",
        )
    pilih_tahun = int(pilih_tahun_raw) if pilih_tahun_raw else tahun_terbaru

    area_options = sorted(df_supply["Kode_Area"].dropna().unique().tolist())
    area_key = "claim_area"
    cleanup_selection(area_key, area_options)
    with col_area:
        pilih_area = st.pills("Filter Area (slicer)", area_options, selection_mode="multi", key=area_key) or []

    df_claim_scope = df_claim[df_claim["Tahun"] == pilih_tahun]
    if pilih_area:
        df_claim_scope = df_claim_scope[df_claim_scope["Kode_Area"].isin(pilih_area)]

    if df_claim_scope.empty:
        st.info(f"Tidak ada data Claim untuk tahun {pilih_tahun}.")
        return

    pivot_claim = build_pivot(df_claim_scope, "Cabang", "Bulan", list_bulan_standar, "Claim_Value", "sum")
    styled = pivot_claim.style.format(FMT_RP).set_properties(
        **{'text-align': 'right', 'font-size': '13px'}
    ).set_properties(
        subset=pd.IndexSlice[:, "TOTAL"], **{'font-weight': 'bold', 'background-color': 'rgba(245, 158, 11, 0.08)'}
    ).set_properties(
        subset=pd.IndexSlice["TOTAL", :], **TOTAL_ROW_STYLE
    )
    st.dataframe(styled, use_container_width=True, height=auto_table_height(len(pivot_claim)))

    with st.expander("Detail Data Claim"):
        col1, col2, col3 = st.columns(3)
        with col1:
            cabang_options = sorted(df_claim_scope["Cabang"].dropna().unique().tolist())
            cleanup_selection("claim_detail_cabang", cabang_options)
            f_cabang = st.multiselect("Filter Cabang", cabang_options, key="claim_detail_cabang")
        with col2:
            salesman_options = sorted(df_claim_scope["Salesman_Name"].dropna().unique().tolist())
            cleanup_selection("claim_detail_salesman", salesman_options)
            f_salesman = st.multiselect("Filter Salesman Name", salesman_options, key="claim_detail_salesman")
        with col3:
            customer_options = sorted(df_claim_scope["Customer_Name"].dropna().unique().tolist())
            cleanup_selection("claim_detail_customer", customer_options)
            f_customer = st.multiselect("Filter Customer Name", customer_options, key="claim_detail_customer")

        col4, col5 = st.columns(2)
        with col4:
            q_partnumber = st.text_input("Cari Partnumber", key="claim_detail_pno")
        with col5:
            q_invoice = st.text_input("Cari Invoice No", key="claim_detail_invoice")

        df_detail = df_claim_scope
        if f_cabang:
            df_detail = df_detail[df_detail["Cabang"].isin(f_cabang)]
        if f_salesman:
            df_detail = df_detail[df_detail["Salesman_Name"].isin(f_salesman)]
        if f_customer:
            df_detail = df_detail[df_detail["Customer_Name"].isin(f_customer)]
        if q_partnumber.strip():
            df_detail = df_detail[df_detail["Partnumber"].astype(str).str.contains(q_partnumber.strip(), case=False, na=False)]
        if q_invoice.strip():
            df_detail = df_detail[df_detail["Invoice_No"].astype(str).str.contains(q_invoice.strip(), case=False, na=False)]

        detail_cols = ["Cabang", "Salesman_Name", "Customer_Name", "Invoice_No", "Invoice_Date", "Partnumber", "Qty", "Claim_Value"]
        if df_detail.empty:
            st.info("Tidak ada data yang cocok dengan filter/pencarian.")
        else:
            st.dataframe(
                df_detail[detail_cols].sort_values("Invoice_Date", ascending=False).style.format(
                    {"Claim_Value": FMT_RP, "Invoice_Date": lambda d: d.strftime("%d-%m-%Y") if pd.notnull(d) else ""}
                ),
                use_container_width=True, hide_index=True, height=min(auto_table_height(len(df_detail)), 500),
            )
