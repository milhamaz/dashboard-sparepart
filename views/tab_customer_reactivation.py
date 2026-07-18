# ============================================================
# 🎯 TAB: REAKTIVASI CUSTOMER
# ============================================================
import streamlit as st
import pandas as pd

from utils.components import render_card, auto_table_height, compute_reactivation_candidates


def render(df_customer_master, df_supply_final, df_supply_raw, pilih_tahun,
           pilih_jenis, pilih_kelas, pilih_area, pilih_cabang):
    st.caption(
        "Customer berstatus **AKTIF** di master (Customer.xlsx) tapi 0 transaksi di "
        f"{pilih_tahun - 1} maupun {pilih_tahun} — beda dari Churned di tab Retention yang "
        "cuma nangkep customer yang beli tahun lalu lalu berhenti. Di sini yang muncul adalah "
        "customer yang sudah hilang dari radar 2 tahun tapi status masternya belum diupdate. "
        "Mengikuti scope Area/Cabang/Jenis/Kelas Customer dari Filter General."
    )

    candidates = compute_reactivation_candidates(
        df_customer_master, df_supply_final, df_supply_raw, pilih_tahun,
        pilih_jenis, pilih_kelas, pilih_area, pilih_cabang,
    )
    if candidates.empty:
        st.info("Tidak ada kandidat reaktivasi untuk filter yang dipilih.")
        return

    never_transacted = candidates["Last_Transaction"].isna().sum()
    has_history = candidates.dropna(subset=["Last_Transaction"])
    if not has_history.empty:
        gap_months = ((pd.Timestamp.now() - has_history["Last_Transaction"]).dt.days / 30.44).mean()
        gap_label = f"{gap_months:.0f} bulan"
    else:
        gap_label = "-"

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(render_card("🎯", "Kandidat Reaktivasi", f"{len(candidates)}", "AKTIF di master, 0 transaksi 2 tahun terakhir"), unsafe_allow_html=True)
    with c2:
        st.markdown(render_card("⏳", "Rata-rata Sejak Transaksi Terakhir", gap_label, f"Dari {len(has_history)} yang punya histori"), unsafe_allow_html=True)
    with c3:
        st.markdown(render_card("❔", "Belum Pernah Transaksi", f"{never_transacted}", "Tidak ada histori Supply sama sekali"), unsafe_allow_html=True)

    st.markdown("#### Daftar Kandidat Reaktivasi — diurutkan dari yang paling baru berhenti")
    display = candidates.rename(columns={
        "Kode_Customer": "Kode Customer", "Nama_Customer": "Nama Customer",
        "Jenis_Customer": "Jenis Customer", "Kelas_Customer": "Kelas Customer",
        "Last_Transaction": "Transaksi Terakhir",
    }).copy()
    display["Transaksi Terakhir"] = display["Transaksi Terakhir"].dt.strftime("%d-%m-%Y")
    display["Transaksi Terakhir"] = display["Transaksi Terakhir"].fillna("Belum Pernah Transaksi")

    st.dataframe(
        display, use_container_width=True, hide_index=True,
        height=min(auto_table_height(len(display)), 600),
    )
