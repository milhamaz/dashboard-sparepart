# ============================================================
# 📅 TAB: ODOM (ONE MILLION ONE DAY)
# ============================================================
import streamlit as st

from utils.components import render_card, render_styled_table, auto_table_height, compute_odom_status
from utils.styles import fmt_rp_full as FMT_RP

_CARD_META = {
    "ODOM Lancar": {"icon": "🟢", "title": "ODOM LANCAR", "sub": "Sebaran order harian stabil ≥Rp1 juta/hari"},
    "ODOM Bolong-bolong": {"icon": "🟡", "title": "ODOM FLUKTUATIF", "sub": "Order bulanan ≥30 Juta, namun transaksi tidak merata"},
    "Belum ODOM": {"icon": "🔴", "title": "Non-ODOM", "sub": "Belum mencapai standar minimum nilai transaksi bulanan"},
}
_STATUS_FILTER_OPTIONS = ["ODOM Lancar", "ODOM Fluktuatif", "Non-ODOM"]
_FILTER_LABEL_TO_STATUS = {"ODOM Lancar": "ODOM Lancar", "ODOM Fluktuatif": "ODOM Bolong-bolong", "Non-ODOM": "Belum ODOM"}


def _highlight_status(val):
    if val == "ODOM Lancar":
        return "color: #10b981; font-weight: bold;"
    if val == "ODOM Bolong-bolong":
        return "color: #f59e0b; font-weight: bold;"
    return "color: #ef4444; font-weight: bold;"


def render(df_order_final, df_kalkerja, pilih_tahun, pilih_bulan):
    hari_kerja_scope = df_kalkerja[(df_kalkerja["Tahun"] == pilih_tahun) & (df_kalkerja["Bulan"].isin(pilih_bulan))]
    hari_kerja_total = hari_kerja_scope["Hari_Kerja"].sum()

    st.markdown("### Ambang hari aktif minimum (%)")
    ambang_hari_aktif = st.slider(
        "Ambang hari aktif minimum (%)", min_value=20, max_value=80, value=50, step=5,
        key="odom_ambang_hari_aktif", label_visibility="collapsed",
        help="Hari aktif (ada Order) dibanding Hari Kerja di scope Bulan yang dipilih — di bawah ini dianggap 'Bolong-bolong' meski total bulanannya lolos ambang.",
    )
    hari_equiv = round(ambang_hari_aktif / 100 * hari_kerja_total) if hari_kerja_total > 0 else 0
    st.caption(f"≈ **{hari_equiv} hari aktif** dari **{hari_kerja_total:.0f} Hari Kerja** di scope Bulan yang dipilih di Filter General.")

    status_df = compute_odom_status(df_order_final, df_kalkerja, pilih_tahun, pilih_bulan, ambang_hari_aktif=ambang_hari_aktif)
    if status_df.empty:
        st.info("Tidak ada data Order untuk filter yang dipilih.")
        return

    n_lancar = (status_df["Status"] == "ODOM Lancar").sum()
    n_bolong = (status_df["Status"] == "ODOM Bolong-bolong").sum()
    n_belum = (status_df["Status"] == "Belum ODOM").sum()
    counts = {"ODOM Lancar": n_lancar, "ODOM Bolong-bolong": n_bolong, "Belum ODOM": n_belum}

    c1, c2, c3 = st.columns(3)
    for col, status_key in zip((c1, c2, c3), ("ODOM Lancar", "ODOM Bolong-bolong", "Belum ODOM")):
        meta = _CARD_META[status_key]
        with col:
            st.markdown(
                render_card(meta["icon"], meta["title"], f"{counts[status_key]}", meta["sub"]),
                unsafe_allow_html=True,
            )

    st.markdown("#### Daftar Customer — Status ODOM")
    col_filter, col_search = st.columns([1, 2])
    with col_filter:
        pilih_status_label = st.pills(
            "Filter Status ODOM", _STATUS_FILTER_OPTIONS, selection_mode="multi",
            default=_STATUS_FILTER_OPTIONS, key="odom_status_filter_pills",
        )
    with col_search:
        search_query = st.text_input(
            "Cari Customer (kode/nama)", key="odom_search_query",
            placeholder="Ketik kode atau nama customer...",
        )

    pilih_status_set = {_FILTER_LABEL_TO_STATUS[label] for label in pilih_status_label} if pilih_status_label else set()
    status_df = status_df[status_df["Status"].isin(pilih_status_set)]
    if search_query.strip():
        q = search_query.strip().upper()
        status_df = status_df[
            status_df["Customer_No"].astype(str).str.upper().str.contains(q, na=False)
            | status_df["Customer_Name"].astype(str).str.upper().str.contains(q, na=False)
        ]

    display = status_df.sort_values(["Status", "Total_Order"], ascending=[True, False]).copy()
    display["Customer"] = display["Customer_No"].astype(str) + " - " + display["Customer_Name"].astype(str)
    display = display[["Customer", "Cabang", "Total_Order", "Hari_Aktif", "Hari_Kerja", "Rasio_Aktif", "Status"]]
    display = display.rename(columns={
        "Total_Order": "Total Order",
        "Hari_Aktif": "Hari Aktif", "Hari_Kerja": "Hari Kerja", "Rasio_Aktif": "Rasio Aktif (%)",
    })

    render_styled_table(
        display, _highlight_status, pct_cols=["Status"],
        fmt_dict={"Total Order": FMT_RP, "Hari Kerja": "{:.0f}", "Rasio Aktif (%)": "{:.1f}%"},
        height=min(auto_table_height(len(display)), 600),
    )

    st.markdown("---")
    st.markdown("### Penjelasan")
    st.markdown(
        "- **ODOM (One Million One Day)** — customer dikategorikan sehat apabila pola Order-nya rutin dengan nilai "
        "minimal Rp1 juta per hari aktif (setara ±Rp30 juta per bulan), dihitung dari data Order.\n"
        "- **Rasio Aktif (%)** = persentase hari kerja yang benar-benar memiliki transaksi Order.\n"
        "- Semakin tinggi Rasio Aktif, semakin merata sebaran transaksi Order sepanjang periode yang dipilih — "
        "bukan terkonsentrasi hanya pada beberapa hari tertentu."
    )
