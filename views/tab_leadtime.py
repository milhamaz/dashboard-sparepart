# ============================================================
# ⏱️ TAB: LEAD TIME (Order -> Actual)
# ============================================================
import streamlit as st

from utils.leadtime_engine import compute_order_actual_link, summarize_by_cabang
from utils.components import render_card, render_topn_barh_chart, auto_table_height, cleanup_selection

FMT_DAY = lambda v: f"{v:.1f} hari".replace(".", ",")


def render(df_order, df_supply):
    if df_order is None or df_order.empty or df_supply is None or df_supply.empty:
        st.warning("Data Order/Supply belum siap.")
        return

    matched, stats = compute_order_actual_link(df_order, df_supply)

    if matched.empty:
        st.info("Tidak ada pasangan Order-Actual yang berhasil di-link.")
        return

    match_rate = stats["n_matched"] / stats["n_supply_total"] * 100 if stats["n_supply_total"] else 0

    tahun_list = sorted(matched["Tahun"].dropna().unique().tolist())
    tahun_terbaru = tahun_list[-1] if tahun_list else None
    col_tahun, col_cabang = st.columns([1, 2])
    with col_tahun:
        tahun_options = [str(t) for t in tahun_list]
        pilih_tahun_raw = st.pills(
            "Pilih Tahun", tahun_options, selection_mode="single",
            default=str(tahun_terbaru) if tahun_terbaru is not None else None, key="leadtime_tahun",
        )
    pilih_tahun = int(pilih_tahun_raw) if pilih_tahun_raw else tahun_terbaru

    scope = matched[matched["Tahun"] == pilih_tahun]

    cabang_options = sorted(scope["Cabang"].dropna().unique().tolist())
    cleanup_selection("leadtime_cabang", cabang_options)
    with col_cabang:
        pilih_cabang = st.multiselect("Filter Cabang", cabang_options, key="leadtime_cabang", placeholder="Semua (klik untuk filter)")
    if pilih_cabang:
        scope = scope[scope["Cabang"].isin(pilih_cabang)]

    if scope.empty:
        st.info(f"Tidak ada data Lead Time untuk tahun {pilih_tahun}.")
        return

    summary = summarize_by_cabang(scope)

    median_nasional = scope["Lead_Time_Days"].median()
    p90_nasional = scope["Lead_Time_Days"].quantile(0.9)
    tercepat = summary.iloc[-1]
    terlama = summary.iloc[0]

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(render_card("⏱️", "Median Lead Time Nasional", FMT_DAY(median_nasional), f"{len(scope):,} baris ke-link"), unsafe_allow_html=True)
    with c2:
        st.markdown(render_card("📊", "P90 Lead Time Nasional", FMT_DAY(p90_nasional), "90% pengiriman lebih cepat dari ini"), unsafe_allow_html=True)
    with c3:
        st.markdown(render_card("🚀", "Cabang Tercepat", tercepat["Cabang"], FMT_DAY(tercepat["Median_Lead_Time"])), unsafe_allow_html=True)
    with c4:
        st.markdown(render_card("🐢", "Cabang Terlama", terlama["Cabang"], FMT_DAY(terlama["Median_Lead_Time"])), unsafe_allow_html=True)

    st.markdown("#### Cabang dengan Lead Time Terlama (Top 10)")
    render_topn_barh_chart(
        summary, "Cabang", "Median_Lead_Time", top_n=10, color="#ef4444",
        value_fmt=FMT_DAY, xaxis_title="Median Lead Time (hari)", key="chart_leadtime_top10",
        extra_hover_cols=[
            ("P90_Lead_Time", "P90", FMT_DAY),
            ("N_Matched", "Jumlah baris", lambda v: f"{v:.0f}"),
        ],
    )

    st.markdown("#### Ranking Lengkap Lead Time per Cabang")
    display = summary.rename(columns={
        "Median_Lead_Time": "Median (hari)", "P90_Lead_Time": "P90 (hari)",
        "Mean_Lead_Time": "Rata-rata (hari)", "N_Matched": "Jumlah Baris",
    })
    st.dataframe(
        display.style.format({
            "Median (hari)": "{:.1f}", "P90 (hari)": "{:.1f}",
            "Rata-rata (hari)": "{:.1f}", "Jumlah Baris": "{:.0f}",
        }),
        use_container_width=True, hide_index=True,
        height=min(auto_table_height(len(display)), 600),
    )

    st.markdown("---")
    st.markdown("### Penjelasan")
    st.markdown(
        "- **Lead Time** adalah selisih waktu antara pesanan diterima (tanggal SO) hingga barang dikeluarkan dari gudang (tanggal Invoice). Metrik ini mencerminkan aspek logistik dan ketersediaan stok, bukan kecepatan kerja salesman.\n"
        "- **Median** digunakan sebagai acuan utama karena lebih tahan terhadap nilai ekstrem dibanding rata-rata (misalnya satu pesanan yang tertunda sangat lama tidak akan menggeser angka secara berlebihan). **P90** ditampilkan sebagai pelengkap untuk menggambarkan kondisi 10% pengiriman paling lambat.\n"
        "- **Metode pencocokan data**: setiap baris data Actual (Supply) dipasangkan dengan data Order yang bersesuaian menggunakan kombinasi Nomor SO, Kode Customer, dan Partnumber. Apabila Partnumber tidak sama persis — misalnya karena terjadi substitusi produk — pencocokan tetap dilakukan menggunakan lima karakter awal Partnumber sebagai pendekatan alternatif.\n"
        "- **Cakupan data**: data Order hanya tersedia sejak tahun 2024, sehingga data Actual dari tahun 2023 tidak memiliki pasangan Order dan otomatis tidak tercakup dalam perhitungan Lead Time. Hal ini merupakan keterbatasan cakupan data, bukan kesalahan sistem.\n"
        "- Baris dengan nilai Lead Time negatif (tanggal Actual tercatat lebih awal dari tanggal Order) tidak diikutsertakan dalam perhitungan karena dianggap sebagai anomali data.\n"
        "- Informasi Cabang pada tabel ini diambil dari data **Supply** (pihak yang mengeluarkan barang), bukan dari data Order."
    )

    with st.expander(f"Rincian tingkat kecocokan data — {match_rate:.1f}% data Actual berhasil dipasangkan dengan Order"):
        st.markdown(
            f"- Total baris data Actual: **{stats['n_supply_total']:,}**\n"
            f"- Kecocokan persis (Nomor SO, Kode Customer, dan Partnumber sama persis): **{stats['n_exact']:,}**\n"
            f"- Kecocokan melalui pendekatan prefix (kandidat substitusi produk): **{stats['n_prefix']:,}**\n"
            f"- Dikecualikan karena Lead Time bernilai negatif: **{stats['n_negative_excluded']:,}**\n"
            f"- Tidak berhasil dipasangkan sama sekali (termasuk seluruh data Actual tahun 2023): **{stats['n_unmatched']:,}**"
        )
