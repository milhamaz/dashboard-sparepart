# ============================================================
# 🔋 TAB: TGB (Quantity Unit Base)
# ============================================================
import streamlit as st
import pandas as pd
from utils.components import (
    hitung_growth, hitung_aly, hitung_avg, render_card, render_growth_card,
    validate_lookup, render_bar_chart, render_styled_table, append_total_row, trim_future_months,
    render_tile_filter,
)

def render(df_order_final, df_supply_final, df_TGB_lookup, pilih_tahun, pilih_bulan, highlight_pct):
    TGB_cols = ["Partnumber", "Kategori"]
    if not validate_lookup(df_TGB_lookup, TGB_cols, "PnoTGB.xlsx"):
        return

    df_ord_TGB_base = pd.merge(df_order_final, df_TGB_lookup[TGB_cols], on="Partnumber", how="inner") if "Partnumber" in df_order_final.columns else pd.DataFrame()
    df_sup_TGB_base = pd.merge(df_supply_final[df_supply_final["Tahun"] == pilih_tahun], df_TGB_lookup[TGB_cols], on="Partnumber", how="inner") if "Partnumber" in df_supply_final.columns else pd.DataFrame()
    df_ly_TGB_base = pd.merge(df_supply_final[df_supply_final["Tahun"] == pilih_tahun - 1], df_TGB_lookup[TGB_cols], on="Partnumber", how="inner") if "Partnumber" in df_supply_final.columns else pd.DataFrame()

    if not df_ord_TGB_base.empty:
        df_ord_TGB_base["Order"] = df_ord_TGB_base["Qty"]
    if not df_sup_TGB_base.empty:
        df_sup_TGB_base["Actual"] = df_sup_TGB_base["Qty"]
    if not df_ly_TGB_base.empty:
        df_ly_TGB_base["Actual"] = df_ly_TGB_base["Qty"]

    list_TGB_categories = sorted(set(
        (df_ord_TGB_base["Kategori"].dropna().unique().tolist() if len(df_ord_TGB_base) else []) +
        (df_sup_TGB_base["Kategori"].dropna().unique().tolist() if len(df_sup_TGB_base) else []) +
        (df_ly_TGB_base["Kategori"].dropna().unique().tolist() if len(df_ly_TGB_base) else [])
    ))
    pilih_TGB_category = render_tile_filter("🔋 Filter Kategori TGB", list_TGB_categories, key="TGB_category_filter")

    def filter_TGB_data(df):
        if df.empty: return df
        return df[df["Kategori"].isin(pilih_TGB_category)]
    
    df_ord_TGB = filter_TGB_data(df_ord_TGB_base)
    df_sup_TGB = filter_TGB_data(df_sup_TGB_base)
    df_ly_TGB = filter_TGB_data(df_ly_TGB_base)

    m_ord_TGB = df_ord_TGB.groupby(["Bulan_Num", "Bulan"])["Order"].sum().reset_index() if not df_ord_TGB.empty else pd.DataFrame(columns=["Bulan_Num", "Bulan", "Order"])
    m_sup_TGB = df_sup_TGB.groupby(["Bulan_Num", "Bulan"])["Actual"].sum().reset_index() if not df_sup_TGB.empty else pd.DataFrame(columns=["Bulan_Num", "Bulan", "Actual"])
    m_ly_TGB = df_ly_TGB.groupby(["Bulan_Num", "Bulan"])["Actual"].sum().reset_index().rename(columns={"Actual": "Last_Year"}) if not df_ly_TGB.empty else pd.DataFrame(columns=["Bulan_Num", "Bulan", "Last_Year"])

    total_TGB_order = df_ord_TGB["Order"].sum() if len(df_ord_TGB) else 0
    total_TGB_actual = df_sup_TGB["Actual"].sum() if len(df_sup_TGB) else 0
    total_TGB_ly = df_ly_TGB["Actual"].sum() if len(df_ly_TGB) else 0       
    TGB_growth = hitung_growth(total_TGB_actual, total_TGB_ly)

    avg_TGB_order = hitung_avg(total_TGB_order, m_ord_TGB, "Order")
    avg_TGB_actual = hitung_avg(total_TGB_actual, m_sup_TGB, "Actual")

    def fmt_pcs(val):
        return f"{val:,.0f}".replace(",", ".") + " Pcs"

    ct1, ct2, ct3, ct4 = st.columns(4)
    with ct1: st.markdown(render_card("", "Total Order", fmt_pcs(total_TGB_order), f"Avg: {fmt_pcs(avg_TGB_order)}/bln"), unsafe_allow_html=True)
    with ct2: st.markdown(render_card("", "Total Actual Supply", fmt_pcs(total_TGB_actual), f"Avg: {fmt_pcs(avg_TGB_actual)}/bln"), unsafe_allow_html=True)
    with ct3: st.markdown(render_card("", "Last Year Qty", fmt_pcs(total_TGB_ly), f"Tahun {pilih_tahun - 1}"), unsafe_allow_html=True)
    with ct4: st.markdown(render_growth_card("", "Growth", TGB_growth, f"Supply vs {pilih_tahun - 1}"), unsafe_allow_html=True)

    TGB_ly_vals = [m_ly_TGB[m_ly_TGB["Bulan"] == b]["Last_Year"].values[0] if len(m_ly_TGB[m_ly_TGB["Bulan"] == b]) else 0 for b in pilih_bulan]
    TGB_ord_vals = [m_ord_TGB[m_ord_TGB["Bulan"] == b]["Order"].values[0] if len(m_ord_TGB[m_ord_TGB["Bulan"] == b]) else 0 for b in pilih_bulan]
    TGB_sup_vals = [m_sup_TGB[m_sup_TGB["Bulan"] == b]["Actual"].values[0] if len(m_sup_TGB[m_sup_TGB["Bulan"] == b]) else 0 for b in pilih_bulan]

    pcs_text = lambda v: f"{v:,.0f}".replace(",", ".") if v else ""

    fig_TGB = render_bar_chart(
        pilih_bulan,
        [
            {"values": TGB_ly_vals, "name": f"Last Year ({pilih_tahun - 1})", "color": "#e11d48", "hover_unit": " Pcs", "text_fmt": pcs_text, "text_size": 13},
            {"values": TGB_ord_vals, "name": "Order", "color": "#2563eb", "hover_unit": " Pcs", "text_fmt": pcs_text, "text_size": 13},
            {"values": TGB_sup_vals, "name": "Supply", "color": "#10b981", "hover_unit": " Pcs", "text_fmt": pcs_text, "text_size": 13},
        ],
        yaxis_title="Kuantitas (Pcs)", height=580,
    )
    st.plotly_chart(fig_TGB, use_container_width=True, key="chart_plotly_tgb")

    with st.expander("Detail Data TGB (Pcs)"):
        if not m_ord_TGB.empty or not m_sup_TGB.empty or not m_ly_TGB.empty:
            tgb_detail = m_ly_TGB.merge(m_ord_TGB, on=["Bulan_Num", "Bulan"], how="outer").merge(m_sup_TGB, on=["Bulan_Num", "Bulan"], how="outer").fillna(0)
            tgb_detail["Bulan_Num"] = tgb_detail["Bulan_Num"].astype(int)
            tgb_detail = tgb_detail[tgb_detail["Bulan"].isin(pilih_bulan)].sort_values("Bulan_Num")
            tgb_detail = trim_future_months(tgb_detail, data_cols=["Order", "Actual"])
            tgb_detail["A/LY (%)"] = tgb_detail.apply(lambda row: hitung_aly(row["Actual"], row["Last_Year"]), axis=1)

            tgb_display = tgb_detail.drop(columns=["Bulan_Num"]).rename(columns={"Last_Year": "Last Year (Pcs)", "Order": "Order (Pcs)", "Actual": "Supply (Pcs)"})

            ly_sum = tgb_display["Last Year (Pcs)"].sum()
            ord_sum = tgb_display["Order (Pcs)"].sum()
            sup_sum = tgb_display["Supply (Pcs)"].sum()
            tgb_display = append_total_row(tgb_display, {
                "Bulan": "TOTAL",
                "Last Year (Pcs)": ly_sum,
                "Order (Pcs)": ord_sum,
                "Supply (Pcs)": sup_sum,
                "A/LY (%)": hitung_aly(sup_sum, ly_sum),
            })

            render_styled_table(
                tgb_display, highlight_pct, pct_cols=["A/LY (%)"],
                fmt_dict={
                    "Last Year (Pcs)": lambda x: f"{x:,.0f}".replace(",", "."),
                    "Order (Pcs)": lambda x: f"{x:,.0f}".replace(",", "."),
                    "Supply (Pcs)": lambda x: f"{x:,.0f}".replace(",", "."),
                    "A/LY (%)": "{:.2f}%"
                },
                has_total_row=True,
            )
        else:
            st.info("Tidak ada data TGB untuk filter yang dipilih.")