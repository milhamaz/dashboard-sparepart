# ============================================================
# 🔧 TAB: T-OPT
# ============================================================
import streamlit as st
import pandas as pd
from utils.components import (
    hitung_growth, hitung_aly, hitung_avg, render_card, render_growth_card,
    validate_lookup, render_bar_chart, render_styled_table, append_total_row, trim_future_months,
    render_tile_filter,
)


def render(df_order_final, df_supply_final, df_topt_lookup, pilih_tahun, pilih_bulan, fmt_rp, highlight_pct):
    if not validate_lookup(df_topt_lookup, ["Partnumber", "Partname", "Step", "Kategori"], "PnoTOPT.xlsx"):
        return

    topt_cols = ["Partnumber", "Partname", "Step", "Kategori"]

    df_ord_topt_base = pd.merge(df_order_final, df_topt_lookup[topt_cols], on="Partnumber", how="inner") if "Partnumber" in df_order_final.columns else pd.DataFrame()
    df_sup_topt_base = pd.merge(df_supply_final[df_supply_final["Tahun"] == pilih_tahun], df_topt_lookup[topt_cols], on="Partnumber", how="inner") if "Partnumber" in df_supply_final.columns else pd.DataFrame()
    df_ly_topt_base = pd.merge(df_supply_final[df_supply_final["Tahun"] == pilih_tahun - 1], df_topt_lookup[topt_cols], on="Partnumber", how="inner") if "Partnumber" in df_supply_final.columns else pd.DataFrame()

    col_f_topt1, col_f_topt2 = st.columns([1, 3])
    
    with col_f_topt1:
        all_step = sorted(set(
            (df_ord_topt_base["Step"].dropna().unique().tolist() if len(df_ord_topt_base) else []) +
            (df_sup_topt_base["Step"].dropna().unique().tolist() if len(df_sup_topt_base) else []) +
            (df_ly_topt_base["Step"].dropna().unique().tolist() if len(df_ly_topt_base) else [])
        ))
        pilih_step = render_tile_filter("🪜 Filter Step", all_step, key="topt_step_filter")

    with col_f_topt2:
        all_kategori = sorted(set(
            (df_ord_topt_base["Kategori"].dropna().unique().tolist() if len(df_ord_topt_base) else []) +
            (df_sup_topt_base["Kategori"].dropna().unique().tolist() if len(df_sup_topt_base) else []) +
            (df_ly_topt_base["Kategori"].dropna().unique().tolist() if len(df_ly_topt_base) else [])
        ))
        pilih_kategori = render_tile_filter("🗂️ Filter Kategori", all_kategori, key="topt_kategori_filter")

    def filter_topt_data(df):
        if df.empty: return df
        return df[df["Step"].isin(pilih_step) & df["Kategori"].isin(pilih_kategori)]

    df_ord_topt = filter_topt_data(df_ord_topt_base)
    df_sup_topt = filter_topt_data(df_sup_topt_base)
    df_ly_topt = filter_topt_data(df_ly_topt_base)

    m_ord_topt = df_ord_topt.groupby(["Bulan_Num", "Bulan"])["Order"].sum().reset_index() if not df_ord_topt.empty else pd.DataFrame(columns=["Bulan_Num", "Bulan", "Order"])
    m_sup_topt = df_sup_topt.groupby(["Bulan_Num", "Bulan"])["Actual"].sum().reset_index() if not df_sup_topt.empty else pd.DataFrame(columns=["Bulan_Num", "Bulan", "Actual"])
    m_ly_topt = df_ly_topt.groupby(["Bulan_Num", "Bulan"])["Actual"].sum().reset_index().rename(columns={"Actual": "Last_Year"}) if not df_ly_topt.empty else pd.DataFrame(columns=["Bulan_Num", "Bulan", "Last_Year"])

    total_topt_order = df_ord_topt["Order"].sum() if len(df_ord_topt) else 0
    total_topt_actual = df_sup_topt["Actual"].sum() if len(df_sup_topt) else 0
    total_topt_ly = df_ly_topt["Actual"].sum() if len(df_ly_topt) else 0
    topt_growth = hitung_growth(total_topt_actual, total_topt_ly)

    avg_topt_order = hitung_avg(total_topt_order, m_ord_topt, "Order")
    avg_topt_actual = hitung_avg(total_topt_actual, m_sup_topt, "Actual")

    ct1, ct2, ct3, ct4 = st.columns(4)
    with ct1: st.markdown(render_card("", "Order", fmt_rp(total_topt_order), f"Avg: {fmt_rp(avg_topt_order)}/bln"), unsafe_allow_html=True)
    with ct2: st.markdown(render_card("", "Actual", fmt_rp(total_topt_actual), f"Avg: {fmt_rp(avg_topt_actual)}/bln"), unsafe_allow_html=True)
    with ct3: st.markdown(render_card("", "Last Year", fmt_rp(total_topt_ly), f"Tahun {pilih_tahun - 1}"), unsafe_allow_html=True)
    with ct4: st.markdown(render_growth_card("", "Growth", topt_growth, f"Supply vs {pilih_tahun - 1}"), unsafe_allow_html=True)

    topt_ly_vals = [m_ly_topt[m_ly_topt["Bulan"] == b]["Last_Year"].values[0] if len(m_ly_topt[m_ly_topt["Bulan"] == b]) else 0 for b in pilih_bulan]
    topt_ord_vals = [m_ord_topt[m_ord_topt["Bulan"] == b]["Order"].values[0] if len(m_ord_topt[m_ord_topt["Bulan"] == b]) else 0 for b in pilih_bulan]
    topt_sup_vals = [m_sup_topt[m_sup_topt["Bulan"] == b]["Actual"].values[0] if len(m_sup_topt[m_sup_topt["Bulan"] == b]) else 0 for b in pilih_bulan]

    format_topt_rp_hover = lambda v: f"Rp{v:,.0f}".replace(",", ".") if v else "Rp0"
    format_topt_rp_text = lambda v: (
        f"Rp {v / 1_000_000_000:,.2f} M" if v >= 1_000_000_000 else (
            f"Rp {v / 1_000_000:,.0f} JT" if v >= 1_000_000 else (
                f"Rp {v / 1_000:,.0f} RB" if v >= 1_000 else "Rp 0"
            )
        )
    )

    fig_topt = render_bar_chart(
        pilih_bulan,
        [
            {"values": topt_ly_vals, "name": f"Last Year ({pilih_tahun - 1})", "color": "#e11d48", "hover_fmt": format_topt_rp_hover, "text_fmt": format_topt_rp_text},
            {"values": topt_ord_vals, "name": "Order", "color": "#2563eb", "hover_fmt": format_topt_rp_hover, "text_fmt": format_topt_rp_text},
            {"values": topt_sup_vals, "name": "Supply", "color": "#10b981", "hover_fmt": format_topt_rp_hover, "text_fmt": format_topt_rp_text},
        ],
        yaxis_title="Revenue (Rp)", height=580,
    )
    st.plotly_chart(fig_topt, use_container_width=True)

    with st.expander("Detail Data T-OPT (Rupiah)"):
        if not m_ord_topt.empty or not m_sup_topt.empty or not m_ly_topt.empty:
            topt_detail = m_ly_topt.merge(m_ord_topt, on=["Bulan_Num", "Bulan"], how="outer").merge(m_sup_topt, on=["Bulan_Num", "Bulan"], how="outer").fillna(0)
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
            st.info("Tidak ada data T-OPT untuk filter yang dipilih.")