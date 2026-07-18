# ============================================================
# 🔄 TAB: CUSTOMER RETENTION & CHURN
# ============================================================
import streamlit as st

from utils.components import render_card, auto_table_height, compute_customer_yoy
from utils.styles import fmt_rp_full as FMT_RP


def _search_box(df, key):
    query = st.text_input(
        "Cari Customer (kode/nama)", key=key, placeholder="Ketik kode atau nama customer...",
    )
    if query.strip():
        q = query.strip().upper()
        df = df[df["Customer"].str.upper().str.contains(q, na=False)]
    return df


def render(df_supply_final, pilih_tahun):
    yoy = compute_customer_yoy(df_supply_final, pilih_tahun)
    if yoy.empty:
        st.info("Tidak ada data Supply untuk filter yang dipilih.")
        return

    yoy["Customer"] = yoy["Customer_No"].astype(str) + " - " + yoy["Customer_Name"].astype(str)

    n_ly = (yoy["Last_Year"] > 0).sum()
    n_this = (yoy["This_Year"] > 0).sum()
    n_retained = (yoy["Status"] == "Retained").sum()
    n_churned = (yoy["Status"] == "Churned").sum()
    n_new = (yoy["Status"] == "New").sum()
    retention_rate = (n_retained / n_ly * 100) if n_ly > 0 else 0.0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(render_card("", f"Customer {pilih_tahun - 1}", f"{n_ly}", "Total aktif tahun lalu"), unsafe_allow_html=True)
    with c2:
        st.markdown(render_card("", f"Customer {pilih_tahun}", f"{n_this}", "Total aktif tahun ini"), unsafe_allow_html=True)
    with c3:
        st.markdown(render_card("📈", "Retention Rate", f"{retention_rate:.1f}%", f"{n_retained} dari {n_ly} bertahan"), unsafe_allow_html=True)
    with c4:
        churn_color = "#ef4444" if n_churned > n_new else "#10b981"
        st.markdown(
            f'<div class="custom-card"><div class="card-title">Churned vs New</div>'
            f'<div class="card-value" style="color:{churn_color}">{n_churned} / {n_new}</div>'
            f'<div class="card-sub">Customer hilang / Customer baru</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown("#### Customer Baru — diurutkan dari nilai terbesar tahun ini")
    new_cust = yoy[yoy["Status"] == "New"].sort_values("This_Year", ascending=False).copy()
    if new_cust.empty:
        st.info("Tidak ada customer baru untuk filter yang dipilih.")
    else:
        new_cust = _search_box(new_cust, key="retention_search_new")
        display_new = new_cust[["Customer", "Cabang", "This_Year"]].rename(columns={"This_Year": f"Actual {pilih_tahun}"})
        st.dataframe(
            display_new.style.format({f"Actual {pilih_tahun}": FMT_RP}),
            use_container_width=True, hide_index=True,
            height=min(auto_table_height(len(display_new)), 500),
        )

    st.markdown("#### Customer Churned — diurutkan dari nilai terbesar tahun lalu")
    churned = yoy[yoy["Status"] == "Churned"].sort_values("Last_Year", ascending=False).copy()
    if churned.empty:
        st.info("Tidak ada customer yang churn untuk filter yang dipilih.")
    else:
        churned = _search_box(churned, key="retention_search_churned")
        display_churned = churned[["Customer", "Cabang", "Last_Year"]].rename(columns={"Last_Year": f"Actual {pilih_tahun - 1}"})
        st.dataframe(
            display_churned.style.format({f"Actual {pilih_tahun - 1}": FMT_RP}),
            use_container_width=True, hide_index=True,
            height=min(auto_table_height(len(display_churned)), 500),
        )

    st.markdown("---")
    st.markdown("### Penjelasan")
    st.markdown(
        "- **Retained** — customer yang bertahan, beli baik di tahun lalu maupun tahun ini.\n"
        "- **New** — customer baru, baru mulai beli tahun ini dan tidak ada transaksi tahun lalu.\n"
        "- **Churned** — customer non-aktif, sempat beli tahun lalu tapi berhenti (tidak ada transaksi tahun ini).\n"
        "- Semua kategori mengikuti scope Bulan/Area/Cabang/Jenis/Kelas Customer dari Filter General — "
        "kalau Bulan yang dipilih cuma sebagian, perbandingannya jadi periode yang sama di kedua tahun, "
        "bukan setahun penuh."
    )
