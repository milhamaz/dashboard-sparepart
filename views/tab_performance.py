# ============================================================
# 📊 TAB: PERFORMANCE
# ============================================================
import streamlit as st
import pandas as pd
from utils.components import (
    hitung_growth, hitung_avg, hitung_aly, render_card, render_growth_card,
    render_bar_chart, render_styled_table, append_total_row, trim_future_months,
)


def render(df_order_final, df_supply_final, df_target, pilih_tahun, pilih_bulan, pilih_cabang, fmt_rp, highlight_pct):
    m_order = df_order_final.groupby(["Bulan_Num", "Bulan"])["Order"].sum().reset_index()
    m_actual = df_supply_final[df_supply_final["Tahun"] == pilih_tahun].groupby(["Bulan_Num", "Bulan"])["Actual"].sum().reset_index()
    m_lastyear = df_supply_final[df_supply_final["Tahun"] == pilih_tahun - 1].groupby(["Bulan_Num", "Bulan"])["Actual"].sum().reset_index().rename(columns={"Actual": "Last_Year"})
    
    df_target_filtered = df_target[(df_target["Tahun"] == pilih_tahun) & (df_target["Bulan"].isin(pilih_bulan)) & (df_target["Cabang"].isin(pilih_cabang))].copy()
    m_target = df_target_filtered.groupby(["Bulan_Num", "Bulan"])["Target"].sum().reset_index()

    monthly = m_lastyear.merge(m_target, on=["Bulan_Num", "Bulan"], how="outer")\
                        .merge(m_order, on=["Bulan_Num", "Bulan"], how="outer")\
                        .merge(m_actual, on=["Bulan_Num", "Bulan"], how="outer").fillna(0)
    monthly["Bulan_Num"] = monthly["Bulan_Num"].astype(int)
    monthly = monthly.sort_values("Bulan_Num")

    monthly["O/T"] = (monthly["Order"] / monthly["Target"] * 100).fillna(0).replace([float('inf'), -float('inf')], 0)
    monthly["A/T"] = (monthly["Actual"] / monthly["Target"] * 100).fillna(0).replace([float('inf'), -float('inf')], 0)
    monthly["A/LY"] = (monthly["Actual"] / monthly["Last_Year"] * 100).fillna(0).replace([float('inf'), -float('inf')], 0)

    total_order = monthly["Order"].sum()
    total_actual = monthly["Actual"].sum()
    total_ly = monthly["Last_Year"].sum()
    yoy_growth = hitung_growth(total_actual, total_ly)

    avg_order = hitung_avg(total_order, monthly, "Order")
    avg_actual = hitung_avg(total_actual, monthly, "Actual")

    col1, col2, col3, col4 = st.columns(4)
    with col1: st.markdown(render_card("", "Total Order", fmt_rp(total_order), f"Avg: {fmt_rp(avg_order)}/bln"), unsafe_allow_html=True)
    with col2: st.markdown(render_card("", "Total Actual", fmt_rp(total_actual), f"Avg: {fmt_rp(avg_actual)}/bln"), unsafe_allow_html=True)
    with col3: st.markdown(render_card("", "Last Year", fmt_rp(total_ly), f"Tahun {pilih_tahun - 1}"), unsafe_allow_html=True)
    with col4: st.markdown(render_growth_card("", "YoY Growth", yoy_growth, f"Actual vs {pilih_tahun - 1}"), unsafe_allow_html=True)

    format_rupiah_hover = lambda v: f"Rp{v:,.0f}".replace(",", ".") if pd.notnull(v) else "Rp0"
    format_rupiah_text = lambda v: f"{v / 1_000_000_000:,.2f}M"

    fig = render_bar_chart(
        monthly["Bulan"],
        [
            {"values": monthly["Last_Year"], "name": f"Last Year ({pilih_tahun - 1})", "color": "#e11d48", "hover_fmt": format_rupiah_hover, "text_fmt": format_rupiah_text},
            {"values": monthly["Target"], "name": "Target", "color": "#f59e0b", "hover_fmt": format_rupiah_hover, "text_fmt": format_rupiah_text},
            {"values": monthly["Order"], "name": "Order", "color": "#2563eb", "hover_fmt": format_rupiah_hover, "text_fmt": format_rupiah_text},
            {"values": monthly["Actual"], "name": "Actual", "color": "#10b981", "hover_fmt": format_rupiah_hover, "text_fmt": format_rupiah_text},
        ],
        yaxis_title="Revenue (Rp)", height=580,
    )
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("Detail Data (Rupiah)"):
        detail = trim_future_months(monthly, data_cols=["Order", "Actual"])
        display = detail[["Bulan", "Last_Year", "Target", "Order", "Actual", "O/T", "A/T", "A/LY"]].copy().rename(columns={"Last_Year": "Last Year"})

        ly_sum = display["Last Year"].sum()
        target_sum = display["Target"].sum()
        order_sum = display["Order"].sum()
        actual_sum = display["Actual"].sum()
        display = append_total_row(display, {
            "Bulan": "TOTAL",
            "Last Year": ly_sum,
            "Target": target_sum,
            "Order": order_sum,
            "Actual": actual_sum,
            "O/T": hitung_aly(order_sum, target_sum),
            "A/T": hitung_aly(actual_sum, target_sum),
            "A/LY": hitung_aly(actual_sum, ly_sum),
        })

        render_styled_table(
            display, highlight_pct, pct_cols=['O/T', 'A/T', 'A/LY'],
            fmt_dict={'O/T': '{:.2f}%', 'A/T': '{:.2f}%', 'A/LY': '{:.2f}%', 'Last Year': lambda x: f"Rp {x:,.0f}".replace(",", "."), 'Target': lambda x: f"Rp {x:,.0f}".replace(",", "."), 'Order': lambda x: f"Rp {x:,.0f}".replace(",", "."), 'Actual': lambda x: f"Rp {x:,.0f}".replace(",", ".")},
            has_total_row=True,
        )