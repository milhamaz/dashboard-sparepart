# ============================================================
# 📊 TAB: TARGET CUSTOMER
# ============================================================
import streamlit as st

from utils.data_loader import load_kelas_cabang, list_bulan_standar
from utils.target_engine import compute_customer_target
from utils.components import render_card, render_topn_barh_chart, render_styled_table, auto_table_height, hitung_aly
from utils.styles import fmt_rp_full as FMT_RP, highlight_achievement_pct as _highlight_ot

_BULAN_NUM = {b: i + 1 for i, b in enumerate(list_bulan_standar)}


def render(df_order_raw, df_target, df_customer_master, pilih_tahun, pilih_bulan,
           pilih_jenis, pilih_kelas, pilih_area, pilih_cabang, fmt_rp):
    st.caption(
        "Target per Customer diturunkan dari Target Cabang (Tgt_Cabang.xlsx), dipecah "
        "proporsional berbasis **Order** dari share tiap Customer dalam window trailing "
        "12 bulan, di-recompute tiap ganti bulan. Customer baru (0 histori trailing) "
        "dapat floor berjenjang per Kelas Cabang, supaya gak dapat Target 0 di bulan "
        "pertamanya."
    )

    bulan_num_list = sorted(_BULAN_NUM[b] for b in pilih_bulan if b in _BULAN_NUM)
    if not bulan_num_list:
        st.info("Tidak ada Bulan yang dipilih di Filter General.")
        return

    df_kelas_cabang = load_kelas_cabang()
    customer_target = compute_customer_target(df_order_raw, df_target, df_kelas_cabang, pilih_tahun, bulan_num_list)
    if customer_target.empty:
        st.info("Tidak ada data Target/Order untuk filter yang dipilih.")
        return

    # Atribut Jenis/Kelas/Area — dari Customer Master, bukan dari transaksi, biar customer
    # yang 0 transaksi pun tetap kena filter dengan benar (konsisten dgn tab Reaktivasi).
    attr = df_customer_master.set_index("Kode_Customer")[["Nama_Customer", "Jenis_Customer", "Kelas_Customer", "Kode_Area"]]
    customer_target = customer_target.merge(attr, left_on="Customer_No", right_index=True, how="left")

    customer_target = customer_target[
        customer_target["Cabang"].isin(pilih_cabang)
        & customer_target["Jenis_Customer"].isin(pilih_jenis)
        & customer_target["Kelas_Customer"].isin(pilih_kelas)
        & customer_target["Kode_Area"].isin(pilih_area)
    ].copy()

    order_scope = df_order_raw[
        (df_order_raw["Tahun"] == pilih_tahun) & (df_order_raw["Bulan_Num"].isin(bulan_num_list))
    ]
    order_sum = order_scope.groupby("Customer_No")["Order"].sum()

    customer_target["Order"] = customer_target["Customer_No"].map(order_sum).fillna(0)
    customer_target["Achievement (%)"] = customer_target.apply(
        lambda r: hitung_aly(r["Order"], r["Target_Customer"]), axis=1
    )
    customer_target = customer_target.sort_values("Target_Customer", ascending=False).reset_index(drop=True)

    if customer_target.empty:
        st.info("Tidak ada data Customer untuk filter yang dipilih.")
        return

    total_target = customer_target["Target_Customer"].sum()
    total_order = customer_target["Order"].sum()
    national_ot = (total_order / total_target * 100) if total_target > 0 else 0.0
    customer_capai = (customer_target["Achievement (%)"] >= 100).sum()
    best_row = customer_target.loc[customer_target["Achievement (%)"].idxmax()]

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(render_card("", "Achievement Nasional (O/T)", f"{national_ot:.1f}%", f"{fmt_rp(total_order)} / {fmt_rp(total_target)}"), unsafe_allow_html=True)
    with c2:
        st.markdown(render_card("✅", "Customer Capai Target", f"{customer_capai}", f"dari {len(customer_target)} customer"), unsafe_allow_html=True)
    with c3:
        st.markdown(render_card("🥇", "Customer Terbaik (%O/T)", best_row["Nama_Customer"], f"{best_row['Achievement (%)']:.1f}%"), unsafe_allow_html=True)
    with c4:
        st.markdown(render_card("", "Total Target", fmt_rp(total_target), f"Total Order: {fmt_rp(total_order)}"), unsafe_allow_html=True)

    st.markdown("#### Top 10 Customer — %O/T")
    top10 = customer_target.nlargest(10, "Achievement (%)")
    render_topn_barh_chart(
        top10, "Nama_Customer", "Achievement (%)", top_n=10, color="#f97316",
        value_fmt=lambda v: f"{v:.1f}%", xaxis_title="%O/T", key="chart_target_customer_top10",
    )

    st.markdown("#### Ranking Lengkap Target Customer")
    display = customer_target[["Nama_Customer", "Cabang", "Target_Customer", "Order", "Achievement (%)", "Tipe"]].copy()
    display.insert(0, "Rank", range(1, len(display) + 1))
    display = display.rename(columns={"Nama_Customer": "Customer", "Target_Customer": "Target"})

    render_styled_table(
        display, _highlight_ot, pct_cols=["Achievement (%)"],
        fmt_dict={"Target": FMT_RP, "Order": FMT_RP, "Achievement (%)": "{:.2f}%"},
        height=min(auto_table_height(len(display)), 600),
    )
