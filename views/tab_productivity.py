# ============================================================
# 📈 TAB: PRODUCTIVITY
# ============================================================
import streamlit as st

from utils.data_loader import list_bulan_standar
from utils.productivity_engine import compute_productivity_df
from utils.components import render_card, render_topn_barh_chart, render_bubble_chart, auto_table_height
from utils.styles import fmt_rp_full as FMT_RP, highlight_pct as _highlight_pct, highlight_concentration_pct as _highlight_concentration

_BULAN_NUM = {b: i + 1 for i, b in enumerate(list_bulan_standar)}

# Ambang minimum jumlah customer assigned — di bawah ini, angka Productivity gampang
# melenceng gara-gara 1-2 transaksi besar/kecil, bukan cerminan skill yang stabil.
_MIN_N_CUSTOMER = 5


def render(df_order_raw, df_order_final, df_supply_final, df_customer_master, pilih_tahun, pilih_bulan,
           pilih_jenis, pilih_kelas, pilih_area, pilih_cabang, fmt_rp):
    bulan_num_list = sorted(_BULAN_NUM[b] for b in pilih_bulan if b in _BULAN_NUM)
    if not bulan_num_list:
        st.info("Tidak ada Bulan yang dipilih di Filter General.")
        return

    subject = st.radio(
        "Lihat Productivity berdasarkan", ["Cabang", "Salesman"], horizontal=True, key="productivity_subject",
    )

    df, label_col, name_col = compute_productivity_df(
        df_order_raw, df_order_final, df_supply_final, df_customer_master,
        pilih_tahun, bulan_num_list, pilih_jenis, pilih_kelas, pilih_area, pilih_cabang, subject,
    )

    if df.empty:
        st.info("Tidak ada data untuk filter yang dipilih.")
        return

    high_risk = (df["Top1_Concentration"] >= 50).sum()
    avg_productivity = df["Productivity_Actual"].mean() if not df.empty else 0.0
    top_row = df.iloc[0]

    # Kurang Produktif dihitung cuma dari subjek dengan sample MEMADAI (>=_MIN_N_CUSTOMER) —
    # kalau dari seluruh df, hasilnya hampir pasti subjek 1-2 customer ber-Actual mepet 0
    # (noise sample kecil, bukan sinyal underperform beneran).
    reliable_df = df[df["Assigned_Customers"] >= _MIN_N_CUSTOMER]
    bottom_row = reliable_df.sort_values("Productivity_Actual").iloc[0] if not reliable_df.empty else None

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(render_card("🏆", f"{subject} Paling Produktif", top_row[label_col], f"{fmt_rp(top_row['Productivity_Actual'])}/customer"), unsafe_allow_html=True)
    with c2:
        st.markdown(render_card("", "Rata-rata Productivity", fmt_rp(avg_productivity), f"per customer, {len(df)} {subject.lower()}"), unsafe_allow_html=True)
    with c3:
        st.markdown(render_card("🚨", "Concentration Risk Tinggi", f"{high_risk}", "Top-1 customer ≥50% revenue"), unsafe_allow_html=True)
    with c4:
        if bottom_row is not None:
            st.markdown(render_card("🐌", f"{subject} Kurang Produktif", bottom_row[label_col], f"{fmt_rp(bottom_row['Productivity_Actual'])}/customer"), unsafe_allow_html=True)
        else:
            st.markdown(render_card("🐌", f"{subject} Kurang Produktif", "-", f"tidak ada {subject.lower()} dengan ≥{_MIN_N_CUSTOMER} customer"), unsafe_allow_html=True)

    st.markdown(f"#### Peta Productivity — {subject}")
    st.caption(
        "Tiap titik = 1 " + subject.lower() + ". Sumbu X = jumlah customer assigned, "
        "sumbu Y = Productivity per Customer, besar bubble = Total Actual (revenue). "
        "Titik kiri-atas (sedikit customer, Productivity tinggi) = ketergantungan ke akun "
        "besar; titik kanan-bawah (banyak customer, Productivity sedang) = portofolio "
        "tersebar. Merah = Concentration Risk tinggi (≥50%)."
    )
    render_bubble_chart(
        df, label_col, x_col="Assigned_Customers", y_col="Productivity_Actual", size_col="Actual",
        risk_col="Top1_Concentration", x_title="Jumlah Customer", y_title="Productivity per Customer (Rp)",
        value_fmt=fmt_rp, key="chart_productivity_bubble",
        extra_hover_cols=[("Top1_Customer", "Top-1 Customer", lambda v: v)],
    )

    st.markdown(f"#### Top 10 {subject} — Productivity per Customer")
    top10 = df.nlargest(10, "Productivity_Actual")
    render_topn_barh_chart(
        top10, label_col, "Productivity_Actual", top_n=10, color="#2563eb",
        value_fmt=fmt_rp, xaxis_title="Rp per Customer", key="chart_productivity_top10",
        extra_hover_cols=[
            ("Assigned_Customers", "Jumlah Customer", lambda v: f"{v:.0f}"),
            ("Top1_Concentration", "Top-1 Concentration", lambda v: f"{v:.1f}%"),
        ],
    )

    st.markdown(f"#### Ranking Lengkap Productivity {subject}")
    search_query = st.text_input(
        f"Cari {subject}", key="productivity_search_query", placeholder=f"Ketik nama {subject.lower()}...",
    )
    table_source = df
    if search_query.strip():
        q = search_query.strip().upper()
        table_source = table_source[table_source[label_col].astype(str).str.upper().str.contains(q, na=False)]

    display_cols = [name_col] + (["Cabang"] if subject == "Salesman" else []) + [
        "Assigned_Customers", "Order", "Actual", "Productivity_Order", "Productivity_Actual",
        "Relative_Productivity", "Top1_Concentration",
    ]
    display = table_source[display_cols].copy()
    display = display.rename(columns={
        name_col: subject, "Assigned_Customers": "Jumlah Customer",
        "Productivity_Order": "Productivity (Order)", "Productivity_Actual": "Productivity (Actual)",
        "Relative_Productivity": "Relative Productivity (%)", "Top1_Concentration": "Top-1 Concentration (%)",
    })

    st.dataframe(
        display.style
        .map(_highlight_pct, subset=["Relative Productivity (%)"])
        .map(_highlight_concentration, subset=["Top-1 Concentration (%)"])
        .format({
            "Order": FMT_RP, "Actual": FMT_RP, "Productivity (Order)": FMT_RP, "Productivity (Actual)": FMT_RP,
            "Relative Productivity (%)": "{:.1f}%", "Top-1 Concentration (%)": "{:.1f}%",
            "Jumlah Customer": "{:.0f}",
        }),
        use_container_width=True, hide_index=True,
        height=min(auto_table_height(len(display)), 600),
    )

    st.markdown("---")
    st.markdown("### Penjelasan")
    st.markdown(
        "- **Productivity** = Order/Actual dibagi jumlah customer yang di-assign (bukan cuma yang aktif transaksi) — supaya subjek yang cuma mengandalkan sedikit akun besar tidak terlihat lebih \"produktif\" dari yang bekerja ke seluruh portofolionya.\n"
        "- **Relative Productivity (%)** = Productivity (Actual) dibanding rata-rata Cabang sendiri (untuk Salesman) atau rata-rata Nasional (untuk Cabang) — bukan dibanding Target, supaya bukan sekadar mengulang Achievement% yang sudah ada di tab Target.\n"
        "- **Top-1 Concentration (%)** = seberapa besar 1 customer terbesar menyumbang ke revenue subjek ini. ≥50% berarti kalau customer itu berhenti, lebih dari separuh revenue subjek ini ikut hilang.\n"
        f"- **Sample Kecil** = subjek dengan <{_MIN_N_CUSTOMER} customer assigned — angka Productivity-nya gampang melenceng gara-gara 1-2 transaksi besar, baca hati-hati.\n"
        f"- **{subject} Kurang Produktif** = Productivity (Actual) terendah, cuma dihitung dari subjek dengan sample memadai (≥{_MIN_N_CUSTOMER} customer) — supaya bukan sekadar subjek 1-2 customer ber-Actual mepet 0 yang muncul, tapi underperform beneran."
    )
