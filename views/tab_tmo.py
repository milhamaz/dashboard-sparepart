# ============================================================
# 🛢️ TAB: TMO
# ============================================================
import streamlit as st
import pandas as pd
from utils.components import (
    hitung_growth, hitung_avg, hitung_aly, render_card, render_growth_card,
    validate_lookup, render_bar_chart, render_styled_table, append_total_row, trim_future_months,
    render_tile_filter,
)


def render(df_order_final, df_supply_final, df_tmo_lookup, pilih_tahun, pilih_bulan, fmt_liter, highlight_pct):
    if not validate_lookup(df_tmo_lookup, ["Partnumber", "Partname", "Liter", "Jenis"], "PnoTMO.xlsx"):
        return

    tmo_cols = ["Partnumber", "Partname", "Liter", "Jenis"]

    df_ord_tmo_base = pd.merge(df_order_final, df_tmo_lookup[tmo_cols], on="Partnumber", how="inner") if "Partnumber" in df_order_final.columns else pd.DataFrame()
    if not df_ord_tmo_base.empty: df_ord_tmo_base["Volume"] = df_ord_tmo_base["Qty"] * df_ord_tmo_base["Liter"]

    df_sup_tmo_base = pd.merge(df_supply_final[df_supply_final["Tahun"] == pilih_tahun], df_tmo_lookup[tmo_cols], on="Partnumber", how="inner") if "Partnumber" in df_supply_final.columns else pd.DataFrame()
    if not df_sup_tmo_base.empty: df_sup_tmo_base["Volume"] = df_sup_tmo_base["Qty"] * df_sup_tmo_base["Liter"]

    df_ly_tmo_base = pd.merge(df_supply_final[df_supply_final["Tahun"] == pilih_tahun - 1], df_tmo_lookup[tmo_cols], on="Partnumber", how="inner") if "Partnumber" in df_supply_final.columns else pd.DataFrame()
    if not df_ly_tmo_base.empty: df_ly_tmo_base["Volume"] = df_ly_tmo_base["Qty"] * df_ly_tmo_base["Liter"]

    col_f_tmo1, col_f_tmo2 = st.columns(2)
    with col_f_tmo1:
        all_jenis = sorted(set((df_ord_tmo_base["Jenis"].dropna().unique().tolist() if len(df_ord_tmo_base) else []) + (df_sup_tmo_base["Jenis"].dropna().unique().tolist() if len(df_sup_tmo_base) else []) + (df_ly_tmo_base["Jenis"].dropna().unique().tolist() if len(df_ly_tmo_base) else [])))
        pilih_jenis_tmo = render_tile_filter("🏷️ Filter Jenis TMO", all_jenis, key="tmo_jenis_filter")

    with col_f_tmo2:
        kamus_so_type = {"C": "SO Campaign (C)", "3": "SO Non Campaign (3)"}
        all_so_types = sorted(set((df_ord_tmo_base["SO_Type"].dropna().unique().tolist() if len(df_ord_tmo_base) else []) + (df_sup_tmo_base["SO_Type"].dropna().unique().tolist() if len(df_sup_tmo_base) else [])))
        pilih_so_type_raw = render_tile_filter("🎁 Filter SO Type (Diskon)", all_so_types, key="tmo_so_type_filter", format_func=lambda x: kamus_so_type.get(x, x), show_select_all=False)

    def filter_tmo_data(df):
        if df.empty: return df
        mask = df["Jenis"].isin(pilih_jenis_tmo)
        if "SO_Type" in df.columns:
            mask = mask & df["SO_Type"].isin(pilih_so_type_raw)
        return df[mask]

    df_ord_tmo = filter_tmo_data(df_ord_tmo_base)
    df_sup_tmo = filter_tmo_data(df_sup_tmo_base)
    df_ly_tmo = filter_tmo_data(df_ly_tmo_base)

    def agg_tmo_total(df):
        if df.empty: return pd.DataFrame(columns=["Bulan_Num", "Bulan", "Volume"])
        return df.groupby(["Bulan_Num", "Bulan"])["Volume"].sum().reset_index()

    m_ord_tmo = agg_tmo_total(df_ord_tmo)
    m_sup_tmo = agg_tmo_total(df_sup_tmo)
    m_ly_tmo = agg_tmo_total(df_ly_tmo)

    total_vol_order = df_ord_tmo["Volume"].sum() if len(df_ord_tmo) else 0
    total_vol_supply = df_sup_tmo["Volume"].sum() if len(df_sup_tmo) else 0
    total_vol_ly = df_ly_tmo["Volume"].sum() if len(df_ly_tmo) else 0
    yoy_vol = hitung_growth(total_vol_supply, total_vol_ly)

    avg_v_order = hitung_avg(total_vol_order, m_ord_tmo, "Volume")
    avg_v_supply = hitung_avg(total_vol_supply, m_sup_tmo, "Volume")

    vol_so_campaign = df_ord_tmo[df_ord_tmo["SO_Type"] == "C"]["Volume"].sum() if len(df_ord_tmo) else 0
    vol_so_non_campaign = df_ord_tmo[df_ord_tmo["SO_Type"] == "3"]["Volume"].sum() if len(df_ord_tmo) else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(render_card("", "Vol. Order", fmt_liter(total_vol_order), f"Avg: {fmt_liter(avg_v_order)}/bln"), unsafe_allow_html=True)
    with c2: st.markdown(render_card("", "Vol. Supply", fmt_liter(total_vol_supply), f"Avg: {fmt_liter(avg_v_supply)}/bln"), unsafe_allow_html=True)
    with c3: st.markdown(render_card("", "Last Year", fmt_liter(total_vol_ly), f"Tahun {pilih_tahun - 1}"), unsafe_allow_html=True)
    with c4: st.markdown(render_growth_card("", "YoY Volume", yoy_vol, f"Supply vs {pilih_tahun - 1}"), unsafe_allow_html=True)

    c_sub1, c_sub2 = st.columns(2)
    with c_sub1:
        st.markdown(f'<div class="custom-card" style="border-left: 5px solid #2563eb;"><div class="card-title">Vol. SO Campaign (Tipe C)</div><div class="card-value">{fmt_liter(vol_so_campaign)}</div><div class="card-sub">Total order dengan program diskon</div></div>', unsafe_allow_html=True)
    with c_sub2:
        st.markdown(f'<div class="custom-card" style="border-left: 5px solid #f59e0b;"><div class="card-title">Vol. SO Non Campaign (Tipe 3)</div><div class="card-value">{fmt_liter(vol_so_non_campaign)}</div><div class="card-sub">Total order regular / normal price</div></div>', unsafe_allow_html=True)

    ly_vals = [m_ly_tmo[m_ly_tmo["Bulan"] == b]["Volume"].values[0] if len(m_ly_tmo[m_ly_tmo["Bulan"] == b]) else 0 for b in pilih_bulan]
    ord_vals = [m_ord_tmo[m_ord_tmo["Bulan"] == b]["Volume"].values[0] if len(m_ord_tmo[m_ord_tmo["Bulan"] == b]) else 0 for b in pilih_bulan]
    sup_vals = [m_sup_tmo[m_sup_tmo["Bulan"] == b]["Volume"].values[0] if len(m_sup_tmo[m_sup_tmo["Bulan"] == b]) else 0 for b in pilih_bulan]

    format_liter_hover = lambda v: f"{v:,.0f}".replace(",", ".") + " L" if v else "0 L"
    format_liter_text = lambda v: f"{v:,.0f}".replace(",", ".")

    fig_tmo = render_bar_chart(
        pilih_bulan,
        [
            {"values": ly_vals, "name": f"Last Year ({pilih_tahun - 1})", "color": "#e11d48", "hover_fmt": format_liter_hover, "text_fmt": format_liter_text},
            {"values": ord_vals, "name": "Order", "color": "#2563eb", "hover_fmt": format_liter_hover, "text_fmt": format_liter_text},
            {"values": sup_vals, "name": "Supply", "color": "#10b981", "hover_fmt": format_liter_hover, "text_fmt": format_liter_text},
        ],
        yaxis_title="Volume (Liter)", height=580,
    )
    st.plotly_chart(fig_tmo, use_container_width=True)

    with st.expander("Detail Volume TMO (Liter)"):
        p_ly = m_ly_tmo.rename(columns={"Volume": "Last_Year"})
        p_ord = m_ord_tmo.rename(columns={"Volume": "Vol_Order"})
        p_sup = m_sup_tmo.rename(columns={"Volume": "Vol_Supply"})

        if not p_ord.empty or not p_sup.empty or not p_ly.empty:
            tmo_detail = p_ly.merge(p_ord, on=["Bulan_Num", "Bulan"], how="outer").merge(p_sup, on=["Bulan_Num", "Bulan"], how="outer").fillna(0)
            tmo_detail["Bulan_Num"] = tmo_detail["Bulan_Num"].astype(int)
            tmo_detail = tmo_detail[tmo_detail["Bulan"].isin(pilih_bulan)].sort_values("Bulan_Num")
            tmo_detail = trim_future_months(tmo_detail, data_cols=["Vol_Order", "Vol_Supply"])
            tmo_detail["A/LY"] = (tmo_detail["Vol_Supply"] / tmo_detail["Last_Year"] * 100).fillna(0).replace([float('inf'), -float('inf')], 0)

            tmo_display = tmo_detail.drop(columns=["Bulan_Num"]).rename(columns={"Last_Year": "Last Year (L)", "Vol_Order": "Order (L)", "Vol_Supply": "Supply (L)", "A/LY": "A/LY (%)"})

            ly_sum = tmo_display["Last Year (L)"].sum()
            ord_sum = tmo_display["Order (L)"].sum()
            sup_sum = tmo_display["Supply (L)"].sum()
            tmo_display = append_total_row(tmo_display, {
                "Bulan": "TOTAL",
                "Last Year (L)": ly_sum,
                "Order (L)": ord_sum,
                "Supply (L)": sup_sum,
                "A/LY (%)": hitung_aly(sup_sum, ly_sum),
            })

            render_styled_table(
                tmo_display, highlight_pct, pct_cols=["A/LY (%)"],
                fmt_dict={"Last Year (L)": lambda x: f"{x:,.0f}".replace(",", "."), "Order (L)": lambda x: f"{x:,.0f}".replace(",", "."), "Supply (L)": lambda x: f"{x:,.0f}".replace(",", "."), "A/LY (%)": "{:.2f}%"},
                has_total_row=True,
            )
        else:
            st.info("Tidak ada data TMO untuk filter yang dipilih.")