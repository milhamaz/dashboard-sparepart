# ============================================================
# 🔄 TAB: CUSTOMER RETENTION & CHURN
# ============================================================
import streamlit as st

from utils.components import render_card, auto_table_height, compute_customer_yoy
from utils.styles import fmt_rp_full as FMT_RP


def render(df_supply_final, pilih_tahun):
    st.caption(
        "**Retained** = beli di tahun lalu & tahun ini. **Churned** = beli tahun lalu tapi tidak "
        "tahun ini. **New** = baru beli tahun ini, tidak ada transaksi tahun lalu. Mengikuti scope "
        "Bulan/Area/Cabang/Jenis/Kelas Customer dari Filter General — kalau Bulan yang dipilih cuma "
        "sebagian, perbandingannya jadi periode yang sama di kedua tahun, bukan setahun penuh."
    )

    yoy = compute_customer_yoy(df_supply_final, pilih_tahun)
    if yoy.empty:
        st.info("Tidak ada data Supply untuk filter yang dipilih.")
        return

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

    st.markdown("#### Customer Churned — diurutkan dari nilai terbesar tahun lalu")
    churned = yoy[yoy["Status"] == "Churned"].sort_values("Last_Year", ascending=False).copy()
    if churned.empty:
        st.info("Tidak ada customer yang churn untuk filter yang dipilih.")
    else:
        display_churned = churned[["Customer_No", "Customer_Name", "Cabang", "Last_Year"]].rename(
            columns={"Customer_No": "Kode Customer", "Customer_Name": "Nama Customer", "Last_Year": f"Actual {pilih_tahun - 1}"}
        )
        st.dataframe(
            display_churned.style.format({f"Actual {pilih_tahun - 1}": FMT_RP}),
            use_container_width=True, hide_index=True,
            height=min(auto_table_height(len(display_churned)), 500),
        )

    st.markdown("#### Customer Baru — diurutkan dari nilai terbesar tahun ini")
    new_cust = yoy[yoy["Status"] == "New"].sort_values("This_Year", ascending=False).copy()
    if new_cust.empty:
        st.info("Tidak ada customer baru untuk filter yang dipilih.")
    else:
        display_new = new_cust[["Customer_No", "Customer_Name", "Cabang", "This_Year"]].rename(
            columns={"Customer_No": "Kode Customer", "Customer_Name": "Nama Customer", "This_Year": f"Actual {pilih_tahun}"}
        )
        st.dataframe(
            display_new.style.format({f"Actual {pilih_tahun}": FMT_RP}),
            use_container_width=True, hide_index=True,
            height=min(auto_table_height(len(display_new)), 500),
        )
