# ============================================================
# 🧪 TAB: CHEMICAL
# ============================================================
import streamlit as st
import pandas as pd
from utils.components import (
    hitung_growth, hitung_aly, hitung_avg, render_card, render_growth_card,
    validate_lookup, render_bar_chart, render_styled_table, append_total_row, trim_future_months,
    render_tile_filter,
)

def render(df_order_final, df_supply_final, df_chem_lookup, pilih_tahun, pilih_bulan, fmt_rp, highlight_pct):
    chem_cols = ["Partnumber", "Kategori"]
    if not validate_lookup(df_chem_lookup, chem_cols, "PnoChem.xlsx"):
        return

    df_ord_chem_base = pd.merge(df_order_final, df_chem_lookup[chem_cols], on="Partnumber", how="inner") if "Partnumber" in df_order_final.columns else pd.DataFrame()
    df_sup_chem_base = pd.merge(df_supply_final[df_supply_final["Tahun"] == pilih_tahun], df_chem_lookup[chem_cols], on="Partnumber", how="inner") if "Partnumber" in df_supply_final.columns else pd.DataFrame()
    df_ly_chem_base = pd.merge(df_supply_final[df_supply_final["Tahun"] == pilih_tahun - 1], df_chem_lookup[chem_cols], on="Partnumber", how="inner") if "Partnumber" in df_supply_final.columns else pd.DataFrame()

    list_chem_categories = sorted(set(
    (df_ord_chem_base["Kategori"].dropna().unique().tolist() if len(df_ord_chem_base) else []) +
    (df_sup_chem_base["Kategori"].dropna().unique().tolist() if len(df_sup_chem_base) else []) +
    (df_ly_chem_base["Kategori"].dropna().unique().tolist() if len(df_ly_chem_base) else [])
    ))
    pilih_chem_category = render_tile_filter("🧪 Filter Kategori Chemical", list_chem_categories, key="chem_category_filter")

    def filter_chem_data(df):
        if df.empty: return df
        return df[df["Kategori"].isin(pilih_chem_category)]
    
    df_ord_chem = filter_chem_data(df_ord_chem_base)
    df_sup_chem = filter_chem_data(df_sup_chem_base)
    df_ly_chem = filter_chem_data(df_ly_chem_base)

    m_ord_chem = df_ord_chem.groupby(["Bulan_Num", "Bulan"])["Order"].sum().reset_index() if not df_ord_chem.empty else pd.DataFrame(columns=["Bulan_Num", "Bulan", "Order"])
    m_sup_chem = df_sup_chem.groupby(["Bulan_Num", "Bulan"])["Actual"].sum().reset_index() if not df_sup_chem.empty else pd.DataFrame(columns=["Bulan_Num", "Bulan", "Actual"])
    m_ly_chem = df_ly_chem.groupby(["Bulan_Num", "Bulan"])["Actual"].sum().reset_index().rename(columns={"Actual": "Last_Year"}) if not df_ly_chem.empty else pd.DataFrame(columns=["Bulan_Num", "Bulan", "Last_Year"])

    total_chem_order = df_ord_chem["Order"].sum() if len(df_ord_chem) else 0
    total_chem_actual = df_sup_chem["Actual"].sum() if len(df_sup_chem) else 0
    total_chem_ly = df_ly_chem["Actual"].sum() if len(df_ly_chem) else 0
    chem_growth = hitung_growth(total_chem_actual, total_chem_ly)

    avg_chem_order = hitung_avg(total_chem_order, m_ord_chem, "Order")
    avg_chem_actual = hitung_avg(total_chem_actual, m_sup_chem, "Actual")

    ct1, ct2, ct3, ct4 = st.columns(4)
    with ct1: st.markdown(render_card("", "Order", fmt_rp(total_chem_order), f"Avg: {fmt_rp(avg_chem_order)}/bln"), unsafe_allow_html=True)
    with ct2: st.markdown(render_card("", "Actual", fmt_rp(total_chem_actual), f"Avg: {fmt_rp(avg_chem_actual)}/bln"), unsafe_allow_html=True)
    with ct3: st.markdown(render_card("", "Last Year", fmt_rp(total_chem_ly), f"Tahun {pilih_tahun - 1}"), unsafe_allow_html=True)
    with ct4: st.markdown(render_growth_card("", "Growth", chem_growth, f"Supply vs {pilih_tahun - 1}"), unsafe_allow_html=True)

    chem_ly_vals = [m_ly_chem[m_ly_chem["Bulan"] == b]["Last_Year"].values[0] if len(m_ly_chem[m_ly_chem["Bulan"] == b]) else 0 for b in pilih_bulan]
    chem_ord_vals = [m_ord_chem[m_ord_chem["Bulan"] == b]["Order"].values[0] if len(m_ord_chem[m_ord_chem["Bulan"] == b]) else 0 for b in pilih_bulan]
    chem_sup_vals = [m_sup_chem[m_sup_chem["Bulan"] == b]["Actual"].values[0] if len(m_sup_chem[m_sup_chem["Bulan"] == b]) else 0 for b in pilih_bulan]

    format_chem_rp_hover = lambda v: f"Rp{v:,.0f}".replace(",", ".") if v else "Rp0"
    format_chem_rp_text = lambda v: (
        f"Rp {v / 1_000_000_000:,.2f} M" if v >= 1_000_000_000 else (
            f"Rp {v / 1_000_000:,.0f} JT" if v >= 1_000_000 else (
                f"Rp {v / 1_000:,.0f} RB" if v >= 1_000 else "Rp 0"
            )
        )
    )

    fig_chem = render_bar_chart(
        pilih_bulan,
        [
            {"values": chem_ly_vals, "name": f"Last Year ({pilih_tahun - 1})", "color": "#e11d48", "hover_fmt": format_chem_rp_hover, "text_fmt": format_chem_rp_text},
            {"values": chem_ord_vals, "name": "Order", "color": "#2563eb", "hover_fmt": format_chem_rp_hover, "text_fmt": format_chem_rp_text},
            {"values": chem_sup_vals, "name": "Supply", "color": "#10b981", "hover_fmt": format_chem_rp_hover, "text_fmt": format_chem_rp_text},
        ],
        yaxis_title="Revenue (Rp)", height=580,
    )
    st.plotly_chart(fig_chem, use_container_width=True)

    with st.expander("Detail Data Chemical (Rupiah)"):
        if not m_ord_chem.empty or not m_sup_chem.empty or not m_ly_chem.empty:
            topt_detail = m_ly_chem.merge(m_ord_chem, on=["Bulan_Num", "Bulan"], how="outer").merge(m_sup_chem, on=["Bulan_Num", "Bulan"], how="outer").fillna(0)
            topt_detail["Bulan_Num"] = topt_detail["Bulan_Num"].astype(int)
            topt_detail = topt_detail[topt_detail["Bulan"].isin(pilih_bulan)].sort_values("Bulan_Num")
            topt_detail = trim_future_months(topt_detail, data_cols=["Order", "Actual"])
            topt_detail["A/LY (%)"] = topt_detail.apply(lambda row: hitung_aly(row["Actual"], row["Last_Year"]), axis=1)

            topt_display = topt_detail.drop(columns=["Bulan_Num"]).rename(columns={"Last_Year": "Last Year", "Order": "Order", "Actual": "Actual"})

            ly_sum = topt_display["Last Year"].sum()
            ord_sum = topt_display["Order"].sum()
            act_sum = topt_display["Actual"].sum()
            topt_display = append_total_row(topt_display, {
                "Bulan": "TOTAL",
                "Last Year": ly_sum,
                "Order": ord_sum,
                "Actual": act_sum,
                "A/LY (%)": hitung_aly(act_sum, ly_sum),
            })

            render_styled_table(
                topt_display, highlight_pct, pct_cols=["A/LY (%)"],
                fmt_dict={
                    "Last Year": lambda x: f"Rp {x:,.0f}".replace(",", "."),
                    "Order": lambda x: f"Rp {x:,.0f}".replace(",", "."),
                    "Actual": lambda x: f"Rp {x:,.0f}".replace(",", "."),
                    "A/LY (%)": "{:.2f}%"
                },
                has_total_row=True,
            )
        else:
            st.info("Tidak ada data Chemical untuk filter yang dipilih.")