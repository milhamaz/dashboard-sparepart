# ============================================================
# 📐 TAB: FILL RATE (Qty Actual vs Qty Order, per baris pengiriman)
# ============================================================
import streamlit as st

from utils.leadtime_engine import (
    compute_order_actual_link, summarize_fulfillment_by_cabang, summarize_fulfillment_by_partnumber,
    compute_split_order_rate,
)
from utils.components import render_card, render_topn_barh_chart, auto_table_height, cleanup_selection
from utils.styles import fmt_pct as FMT_PCT

FMT_RATIO = lambda v: f"{v:.2f}".replace(".", ",")
MIN_N_PARTNUMBER = 5


def render(df_order, df_supply):
    if df_order is None or df_order.empty or df_supply is None or df_supply.empty:
        st.warning("Data Order/Supply belum siap.")
        return

    matched, stats = compute_order_actual_link(df_order, df_supply)

    if matched.empty:
        st.info("Tidak ada pasangan Order-Actual yang berhasil di-link.")
        return

    tahun_list = sorted(matched["Tahun"].dropna().unique().tolist())
    tahun_terbaru = tahun_list[-1] if tahun_list else None
    col_tahun, col_cabang = st.columns([1, 2])
    with col_tahun:
        tahun_options = [str(t) for t in tahun_list]
        pilih_tahun_raw = st.pills(
            "Pilih Tahun", tahun_options, selection_mode="single",
            default=str(tahun_terbaru) if tahun_terbaru is not None else None, key="fillrate_tahun",
        )
    pilih_tahun = int(pilih_tahun_raw) if pilih_tahun_raw else tahun_terbaru

    scope = matched[matched["Tahun"] == pilih_tahun]

    cabang_options = sorted(scope["Cabang"].dropna().unique().tolist())
    cleanup_selection("fillrate_cabang", cabang_options)
    with col_cabang:
        pilih_cabang = st.multiselect("Filter Cabang", cabang_options, key="fillrate_cabang", placeholder="Semua (klik untuk filter)")
    if pilih_cabang:
        scope = scope[scope["Cabang"].isin(pilih_cabang)]

    if scope.empty:
        st.info(f"Tidak ada data untuk tahun {pilih_tahun}.")
        return

    summary_cabang = summarize_fulfillment_by_cabang(scope)

    partial_rate_nasional = scope["Is_Partial"].mean() * 100
    median_ratio_nasional = scope["Fulfillment_Ratio"].median()
    n_split, n_orders, split_rate_nasional = compute_split_order_rate(scope)
    terbaik = summary_cabang.iloc[-1]
    terburuk = summary_cabang.iloc[0]

    r1c1, r1c2, r1c3 = st.columns(3)
    with r1c1:
        st.markdown(render_card("📐", "Median Fill Rate Nasional", FMT_RATIO(median_ratio_nasional), "1,00 = dikirim penuh sesuai pesanan"), unsafe_allow_html=True)
    with r1c2:
        st.markdown(render_card("📦", "Pengiriman Tidak Penuh Nasional", FMT_PCT(partial_rate_nasional), f"{len(scope):,} baris pengiriman ke-link".replace(",", ".")), unsafe_allow_html=True)
    with r1c3:
        st.markdown(render_card("🔀", "Order Dipecah (Multi-Kirim)", FMT_PCT(split_rate_nasional), f"{n_split:,} dari {n_orders:,} Order".replace(",", ".")), unsafe_allow_html=True)

    r2c1, r2c2 = st.columns(2)
    with r2c1:
        st.markdown(render_card("✅", "Cabang Fill Rate Terbaik", terbaik["Cabang"], f"Pengiriman Tidak Penuh {FMT_PCT(terbaik['Partial_Rate'])}"), unsafe_allow_html=True)
    with r2c2:
        st.markdown(render_card("⚠️", "Cabang Fill Rate Terburuk", terburuk["Cabang"], f"Pengiriman Tidak Penuh {FMT_PCT(terburuk['Partial_Rate'])}"), unsafe_allow_html=True)

    st.markdown("#### Cabang dengan Pengiriman Tidak Penuh Tertinggi (Top 10)")
    render_topn_barh_chart(
        summary_cabang, "Cabang", "Partial_Rate", top_n=10, color="#f59e0b",
        value_fmt=FMT_PCT, xaxis_title="Pengiriman Tidak Penuh (%)", key="chart_fillrate_top10",
        extra_hover_cols=[
            ("Median_Ratio", "Median Fill Rate", FMT_RATIO),
            ("N_Matched", "Jumlah baris", lambda v: f"{v:.0f}"),
        ],
    )

    st.markdown("#### Partnumber Paling Sering Kurang Dipenuhi (Top 15)")
    st.caption(f"Hanya menampilkan Partnumber dengan minimal {MIN_N_PARTNUMBER} transaksi ke-link, supaya tidak terpengaruh sample yang terlalu kecil.")
    summary_pno = summarize_fulfillment_by_partnumber(scope, min_n=MIN_N_PARTNUMBER)
    if summary_pno.empty:
        st.info("Tidak ada Partnumber dengan jumlah transaksi yang memadai untuk ranking ini.")
    else:
        top_pno = summary_pno.head(15).rename(columns={
            "Partial_Rate": "Pengiriman Tidak Penuh (%)", "Median_Ratio": "Median Fill Rate", "N_Matched": "Jumlah Transaksi",
        })
        st.dataframe(
            top_pno.style.format({
                "Pengiriman Tidak Penuh (%)": "{:.1f}", "Median Fill Rate": "{:.2f}", "Jumlah Transaksi": "{:.0f}",
            }),
            use_container_width=True, hide_index=True,
            height=min(auto_table_height(len(top_pno)), 500),
        )

    st.markdown("#### Ranking Lengkap Fill Rate per Cabang")
    display = summary_cabang.rename(columns={
        "Partial_Rate": "Pengiriman Tidak Penuh (%)", "Median_Ratio": "Median Fill Rate", "N_Matched": "Jumlah Baris",
    })
    st.dataframe(
        display.style.format({
            "Pengiriman Tidak Penuh (%)": "{:.1f}", "Median Fill Rate": "{:.2f}", "Jumlah Baris": "{:.0f}",
        }),
        use_container_width=True, hide_index=True,
        height=min(auto_table_height(len(display)), 600),
    )

    st.markdown("---")
    st.markdown("### Penjelasan")
    st.markdown(
        "- **Fill Rate** adalah istilah standar dalam analisis rantai pasok untuk mengukur perbandingan antara jumlah barang yang benar-benar dikirim (Qty Actual) dengan jumlah yang dipesan (Qty Order), dihitung sebagai **Qty Actual dibagi Qty Order** untuk satu baris pengiriman. Nilai 1,00 berarti pengiriman tersebut memenuhi penuh jumlah yang dipesan; nilai di bawah 1,00 berarti pengiriman tersebut tidak penuh.\n"
        "- **Penting**: metrik pada tab ini dihitung per **baris pengiriman** (setiap kali barang keluar dari gudang), bukan per Order secara keseluruhan. Apabila satu Order dikirim secara bertahap dalam beberapa kali pengiriman, setiap baris pengiriman tersebut dapat tercatat memiliki Fill Rate di bawah 1,00 — termasuk pengiriman terakhir yang justru menyelesaikan Order tersebut secara penuh. Untuk melihat status akhir suatu Order secara keseluruhan (apakah pada akhirnya terpenuhi, sebagian, belum dikirim, atau tidak dapat ditelusuri), silakan lihat tab **Status Fulfillment**.\n"
        "- **Pengiriman Tidak Penuh** adalah persentase baris pengiriman dengan Fill Rate di bawah 1,00 terhadap seluruh baris pengiriman yang berhasil dipasangkan dengan Order-nya.\n"
        "- **Order Dipecah (Multi-Kirim)** adalah persentase Order yang penyelesaiannya memerlukan lebih dari satu baris pengiriman, dihitung per Order (bukan per baris pengiriman) — sehingga satu Order yang dikirim tiga kali tetap dihitung sebagai satu Order yang dipecah, bukan tiga.\n"
        "- Tabel Partnumber ditampilkan untuk mengidentifikasi produk spesifik yang secara konsisten mengalami kekurangan pemenuhan, sebagai referensi bagi fungsi pengadaan/inventori.\n"
        "- Data yang digunakan pada tab ini bersumber dari pasangan Order-Actual yang sama dengan tab **Lead Time** — metode pencocokan, cakupan data (sejak 2024), dan pengecualian data yang berlaku pada tab tersebut berlaku pula di sini."
    )

    match_rate = stats["n_matched"] / stats["n_supply_total"] * 100 if stats["n_supply_total"] else 0
    with st.expander(f"Rincian tingkat kecocokan data — {match_rate:.1f}% data Actual berhasil dipasangkan dengan Order"):
        st.markdown(
            f"- Total baris data Actual: **{stats['n_supply_total']:,}**\n"
            f"- Kecocokan persis (Nomor SO, Kode Customer, dan Partnumber sama persis): **{stats['n_exact']:,}**\n"
            f"- Kecocokan melalui pendekatan prefix (kandidat substitusi produk): **{stats['n_prefix']:,}**\n"
            f"- Dikecualikan karena Lead Time bernilai negatif: **{stats['n_negative_excluded']:,}**\n"
            f"- Tidak berhasil dipasangkan sama sekali (termasuk seluruh data Actual tahun 2023): **{stats['n_unmatched']:,}**"
        )
