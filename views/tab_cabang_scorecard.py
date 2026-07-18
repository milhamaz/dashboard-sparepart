# ============================================================
# 🏢 TAB: CABANG SCORECARD
# ============================================================
import streamlit as st
import pandas as pd

from utils.components import render_card, render_bidirectional_barh_chart, render_styled_table, auto_table_height, hitung_aly
from utils.styles import fmt_rp_full as FMT_RP, highlight_achievement_pct as _highlight_achievement


def render(df_order_final, df_supply_final, df_target, pilih_tahun, pilih_bulan, pilih_cabang, fmt_rp):
    """Ranking semua Cabang (bukan cuma 1 cabang seperti tab Pacing) berdasar Achievement =
    Actual/Target. Target diambil dari df_target MENTAH (bukan kolom Target yang sudah
    ke-merge duplikat per baris transaksi di df_order/df_supply) — sama pola dengan
    tab_performance.py, supaya Target ke-sum sekali per Cabang/Bulan, bukan berkali-kali.
    """
    df_target_scope = df_target[
        (df_target["Tahun"] == pilih_tahun)
        & (df_target["Bulan"].isin(pilih_bulan))
        & (df_target["Cabang"].isin(pilih_cabang))
    ]
    target_per_cabang = df_target_scope.groupby("Cabang")["Target"].sum()

    df_sup_this = df_supply_final[df_supply_final["Tahun"] == pilih_tahun]
    actual_per_cabang = df_sup_this.groupby("Cabang")["Actual"].sum()

    order_per_cabang = df_order_final.groupby("Cabang")["Order"].sum() if not df_order_final.empty else pd.Series(dtype=float, name="Order")

    scorecard = (
        target_per_cabang.rename("Target").to_frame()
        .join(actual_per_cabang.rename("Actual"), how="outer")
        .join(order_per_cabang.rename("Order"), how="outer")
        .fillna(0)
    )
    scorecard.index.name = "Cabang"
    scorecard = scorecard.reset_index()
    scorecard["Achievement (%)"] = scorecard.apply(lambda r: hitung_aly(r["Actual"], r["Target"]), axis=1)
    scorecard["Order_Achievement (%)"] = scorecard.apply(lambda r: hitung_aly(r["Order"], r["Target"]), axis=1)
    scorecard = scorecard.sort_values("Achievement (%)", ascending=False).reset_index(drop=True)

    if scorecard.empty:
        st.info("Tidak ada data Target/Actual untuk filter yang dipilih.")
        return

    total_target = scorecard["Target"].sum()
    total_actual = scorecard["Actual"].sum()
    total_order = scorecard["Order"].sum()
    national_achievement = (total_actual / total_target * 100) if total_target > 0 else 0.0

    # %Kontribusi — Order/Actual cabang tersebut dibanding total kumulatif nasional (semua
    # Cabang di scope filter ini), dipakai cuma buat tooltip hover chart bidirectional.
    scorecard["Pct_Kontribusi_Actual"] = (scorecard["Actual"] / total_actual * 100) if total_actual > 0 else 0.0
    scorecard["Pct_Kontribusi_Order"] = (scorecard["Order"] / total_order * 100) if total_order > 0 else 0.0

    cabang_capai_target = (scorecard["Achievement (%)"] >= 100).sum()
    best_row = scorecard.iloc[0]
    worst_row = scorecard.iloc[-1]

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(render_card("", "Achievement Nasional", f"{national_achievement:.1f}%", f"{fmt_rp(total_actual)} / {fmt_rp(total_target)}"), unsafe_allow_html=True)
    with c2:
        st.markdown(render_card("✅", "Cabang Capai Target", f"{cabang_capai_target}", f"dari {len(scorecard)} cabang"), unsafe_allow_html=True)
    with c3:
        st.markdown(render_card("🥇", "Cabang Terbaik", best_row["Cabang"], f"{best_row['Achievement (%)']:.1f}%"), unsafe_allow_html=True)
    with c4:
        st.markdown(render_card("⚠️", "Perlu Perhatian", worst_row["Cabang"], f"{worst_row['Achievement (%)']:.1f}%"), unsafe_allow_html=True)

    st.markdown("#### Top 10 Cabang — %O/T vs %A/T")
    # Panjang bar sengaja dibikin dari %O/T & %A/T (bukan Rp Order/Actual mentah) — Cabang
    # Scorecard ini pusatnya soal pencapaian vs Target, jadi cabang kecil dengan Achievement
    # tinggi (mis. Pontianak) harus kelihatan lebih menonjol di grafik daripada cabang besar
    # dengan Achievement rendah (mis. Jakarta), meski nilai Rp-nya jauh lebih kecil. Rp
    # mentahnya tetap ada, cuma dipindah ke hover.
    top10 = scorecard.nlargest(10, "Achievement (%)")
    pct_fmt = lambda v: f"{v:.1f}%"
    render_bidirectional_barh_chart(
        top10, "Cabang", "Order_Achievement (%)", "Achievement (%)", "Order", "Actual",
        left_color="#f97316", right_color="#2563eb", value_fmt=pct_fmt,
        key="chart_cabang_order_vs_actual", xaxis_title="% Pencapaian vs Target (Order kiri • Actual kanan)",
        left_hover_extra=[
            ("Order", "Total Order", fmt_rp),
            ("Pct_Kontribusi_Order", "% Kontribusi", pct_fmt),
        ],
        right_hover_extra=[
            ("Actual", "Total Actual", fmt_rp),
            ("Pct_Kontribusi_Actual", "% Kontribusi", pct_fmt),
        ],
    )

    st.markdown("#### Scorecard Lengkap per Cabang")
    display = scorecard[["Cabang", "Target", "Actual", "Achievement (%)"]].copy()
    display.insert(0, "Rank", range(1, len(display) + 1))

    render_styled_table(
        display, _highlight_achievement, pct_cols=["Achievement (%)"],
        fmt_dict={"Target": FMT_RP, "Actual": FMT_RP, "Achievement (%)": "{:.2f}%"},
        height=min(auto_table_height(len(display)), 600),
    )
