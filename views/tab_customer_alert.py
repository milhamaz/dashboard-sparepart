# ============================================================
# 🚨 TAB: ALERT PENURUNAN CUSTOMER
# ============================================================
import streamlit as st

from utils.components import render_card, auto_table_height, compute_customer_yoy
from utils.styles import fmt_rp_full as FMT_RP


def _highlight_decline(val):
    """Merah kalau penurunan makin dalam, oranye kalau masih ringan — threshold ambil dari
    slider di atas, jadi warnanya relatif terhadap ambang yang user pilih sendiri."""
    return "color: #ef4444; font-weight: bold;" if val <= -50 else "color: #f59e0b; font-weight: bold;"


def render(df_supply_final, pilih_tahun):
    yoy = compute_customer_yoy(df_supply_final, pilih_tahun)
    if yoy.empty:
        st.info("Tidak ada data Supply untuk filter yang dipilih.")
        return

    st.markdown("### Ambang batas penurunan (%)")
    threshold = st.slider(
        "Ambang batas penurunan (%)", min_value=10, max_value=90, value=30, step=5,
        key="customer_alert_threshold", label_visibility="collapsed",
        help="Customer Retained dengan penurunan >= ambang ini akan muncul di daftar.",
    )

    at_risk = yoy[(yoy["Status"] == "Retained") & (yoy["Pct_Change"] <= -threshold)].copy()
    at_risk["Value_Lost"] = at_risk["Last_Year"] - at_risk["This_Year"]
    at_risk["Customer"] = at_risk["Customer_No"].astype(str) + " - " + at_risk["Customer_Name"].astype(str)
    at_risk = at_risk.sort_values("Pct_Change", ascending=True)

    total_value_lost = at_risk["Value_Lost"].sum()
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(render_card("🚨", "Customer At Risk", f"{len(at_risk)}", f"Turun ≥{threshold}% vs {pilih_tahun - 1}"), unsafe_allow_html=True)
    with c2:
        st.markdown(render_card("", "Total Nilai Hilang", FMT_RP(total_value_lost), "Selisih Last Year - This Year"), unsafe_allow_html=True)
    with c3:
        avg_decline = at_risk["Pct_Change"].mean() if not at_risk.empty else 0.0
        st.markdown(render_card("", "Rata-rata Penurunan", f"{avg_decline:.1f}%", "Dari customer at risk"), unsafe_allow_html=True)

    st.markdown("#### Daftar Customer At Risk — diurutkan dari penurunan terdalam")
    if at_risk.empty:
        st.info(f"Tidak ada customer dengan penurunan ≥{threshold}% untuk filter yang dipilih.")
        return

    search_query = st.text_input(
        "Cari Customer (kode/nama)", key="alert_search_query", placeholder="Ketik kode atau nama customer...",
    )
    if search_query.strip():
        q = search_query.strip().upper()
        at_risk = at_risk[at_risk["Customer"].str.upper().str.contains(q, na=False)]

    display = at_risk[["Customer", "Cabang", "Last_Year", "This_Year", "Pct_Change", "Value_Lost"]].rename(
        columns={
            "Last_Year": f"Actual {pilih_tahun - 1}", "This_Year": f"Actual {pilih_tahun}",
            "Pct_Change": "Perubahan (%)", "Value_Lost": "Nilai Hilang",
        }
    )
    st.dataframe(
        display.style.map(_highlight_decline, subset=["Perubahan (%)"]).format({
            f"Actual {pilih_tahun - 1}": FMT_RP, f"Actual {pilih_tahun}": FMT_RP,
            "Perubahan (%)": "{:.2f}%", "Nilai Hilang": FMT_RP,
        }),
        use_container_width=True, hide_index=True,
        height=min(auto_table_height(len(display)), 600),
    )

    st.markdown("---")
    st.markdown("### Penjelasan")
    st.markdown(
        "- Customer yang **masih beli di kedua tahun (Retained)**, tapi nilainya turun melebihi ambang batas di atas.\n"
        "- Sinyal lebih awal dibanding **Churned** — customer di sini belum berhenti total, tapi sudah menunjukkan tanda-tanda penurunan yang perlu diwaspadai."
    )
