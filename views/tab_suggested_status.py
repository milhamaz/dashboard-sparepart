# ============================================================
# 🎯 TAB: SUGGESTED STATUS
# ============================================================
import streamlit as st
import pandas as pd

from utils.components import render_card, auto_table_height, compute_reactivation_candidates

GRACE_PERIOD_DAYS = 365  # 12 bulan tanpa transaksi Supply -> disarankan pindah ke TIDAK AKTIF


def render(df_customer_master, df_supply_raw, pilih_jenis, pilih_kelas, pilih_area, pilih_cabang):
    # Dinormalisasi ke tengah malam (bukan pd.Timestamp.now() presisi detik) supaya cache
    # compute_reactivation_candidates() cuma refresh 1x per hari kalender, bukan tiap render.
    reference_date = pd.Timestamp.now().normalize()
    candidates = compute_reactivation_candidates(
        df_customer_master, df_supply_raw, pilih_jenis, pilih_kelas, pilih_area, pilih_cabang,
        reference_date=reference_date, grace_period_days=GRACE_PERIOD_DAYS,
    )
    if candidates.empty:
        st.info("Tidak ada kandidat Suggested Status untuk filter yang dipilih.")
        return

    never_transacted = candidates["Last_Transaction"].isna().sum()
    has_history = candidates.dropna(subset=["Last_Transaction"])
    if not has_history.empty:
        gap_months = ((reference_date - has_history["Last_Transaction"]).dt.days / 30.44).mean()
        gap_label = f"{gap_months:.0f} bulan"
    else:
        gap_label = "-"

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(render_card("🎯", "Kandidat Suggested Status", f"{len(candidates)}", "AKTIF di master, tanpa transaksi ≥12 bulan"), unsafe_allow_html=True)
    with c2:
        st.markdown(render_card("⏳", "Rata-rata Sejak Transaksi Terakhir", gap_label, f"Dari {len(has_history)} yang punya histori"), unsafe_allow_html=True)
    with c3:
        st.markdown(render_card("❔", "Belum Pernah Transaksi", f"{never_transacted}", "Tidak ada histori Supply sama sekali"), unsafe_allow_html=True)

    st.markdown("#### Daftar Kandidat — diurutkan dari yang paling baru berhenti")
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

    st.markdown("---")
    st.markdown("### Penjelasan")
    st.markdown(
        "- Customer berstatus **AKTIF** di master (Customer.xlsx), tapi sudah **≥12 bulan** tanpa "
        "transaksi Supply sama sekali.\n"
        "- Beda dari **Churned** di tab Retention & Churn yang berbasis kalender tahun (Filter "
        "General) — ini dihitung murni dari tanggal transaksi terakhir, jadi tidak terikat Tahun "
        "yang lagi dipilih.\n"
        "- Daftar ini adalah **saran** (worklist) untuk ditinjau manual, bukan perubahan status "
        "otomatis — tim yang mengelola Customer.xlsx yang memutuskan apakah status customer ini "
        "perlu diubah jadi TIDAK AKTIF."
    )
