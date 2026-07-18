# ============================================================
# 📅 TAB: ODOM (ONE MILLION ONE DAY)
# ============================================================
import streamlit as st

from utils.components import render_card, render_styled_table, auto_table_height, compute_odom_status
from utils.styles import fmt_rp_full as FMT_RP


def _highlight_status(val):
    if val == "ODOM Lancar":
        return "color: #10b981; font-weight: bold;"
    if val == "ODOM Bolong-bolong":
        return "color: #f59e0b; font-weight: bold;"
    return "color: #ef4444; font-weight: bold;"


def render(df_order_final, df_kalkerja, pilih_tahun, pilih_bulan):
    st.caption(
        "**ODOM (One Million One Day)** — customer dianggap sehat kalau Order-nya rutin "
        "≥Rp1 juta/hari (~Rp30 juta/bulan), berbasis **Order** (bukan Actual/Supply). "
        "**ODOM Lancar** = lolos ambang bulanan DAN hari aktifnya tersebar wajar. "
        "**ODOM Bolong-bolong** = lolos ambang bulanan tapi Order-nya numpuk di sedikit "
        "hari (gak rutin harian). **Belum ODOM** = gak nyampe ambang bulanan sama sekali."
    )

    ambang_hari_aktif = st.slider(
        "Ambang hari aktif minimum (%)", min_value=20, max_value=80, value=50, step=5,
        key="odom_ambang_hari_aktif",
        help="Hari aktif (ada Order) dibanding Hari Kerja di scope Bulan yang dipilih — di bawah ini dianggap 'Bolong-bolong' meski total bulanannya lolos ambang.",
    )

    status_df = compute_odom_status(df_order_final, df_kalkerja, pilih_tahun, pilih_bulan, ambang_hari_aktif=ambang_hari_aktif)
    if status_df.empty:
        st.info("Tidak ada data Order untuk filter yang dipilih.")
        return

    n_lancar = (status_df["Status"] == "ODOM Lancar").sum()
    n_bolong = (status_df["Status"] == "ODOM Bolong-bolong").sum()
    n_belum = (status_df["Status"] == "Belum ODOM").sum()

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(render_card("🟢", "ODOM Lancar", f"{n_lancar}", f"dari {len(status_df)} customer"), unsafe_allow_html=True)
    with c2:
        st.markdown(render_card("🟡", "ODOM Bolong-bolong", f"{n_bolong}", "lolos bulanan, gak konsisten harian"), unsafe_allow_html=True)
    with c3:
        st.markdown(render_card("🔴", "Belum ODOM", f"{n_belum}", "di bawah ambang bulanan"), unsafe_allow_html=True)

    st.markdown("#### Daftar Customer — Status ODOM")
    display = status_df.sort_values(["Status", "Total_Order"], ascending=[True, False]).copy()
    display = display[["Customer_Name", "Cabang", "Total_Order", "Hari_Aktif", "Hari_Kerja", "Rasio_Aktif", "Status"]]
    display = display.rename(columns={
        "Customer_Name": "Customer", "Total_Order": "Total Order",
        "Hari_Aktif": "Hari Aktif", "Hari_Kerja": "Hari Kerja", "Rasio_Aktif": "Rasio Aktif (%)",
    })

    render_styled_table(
        display, _highlight_status, pct_cols=["Status"],
        fmt_dict={"Total Order": FMT_RP, "Hari Kerja": "{:.0f}", "Rasio Aktif (%)": "{:.1f}%"},
        height=min(auto_table_height(len(display)), 600),
    )
