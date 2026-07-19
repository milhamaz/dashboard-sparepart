# ============================================================
# 📊 TAB: STATUS FULFILLMENT (status akhir tiap Order, akumulatif)
# ============================================================
import pandas as pd
import streamlit as st

from utils.leadtime_engine import compute_order_actual_link, compute_fulfillment_status, STATUS_ORDER
from utils.components import render_card, auto_table_height, cleanup_selection
from utils.styles import fmt_pct as FMT_PCT

STATUS_ICON = {"Fulfill": "✅", "Fulfill Sebagian": "🟡", "Belum Dikirim": "🔵", "Hilang / Trace Data": "🔴"}


def _fmt_count(count):
    return f"{count:,.0f}".replace(",", ".")


def render(df_order, df_supply):
    if df_order is None or df_order.empty or df_supply is None or df_supply.empty:
        st.warning("Data Order/Supply belum siap.")
        return

    # compute_fulfillment_status() internally memanggil compute_order_actual_link() lagi buat
    # nentuin ambang "Hilang" — karena dua-duanya @st.cache_data, panggilan ini gak ngitung ulang
    # (cache hit), cuma buat ngambil `stats` yang dipakai expander transparansi di bawah.
    _, stats = compute_order_actual_link(df_order, df_supply)
    status_df, lost_threshold, reference_date = compute_fulfillment_status(df_order, df_supply)

    if status_df.empty:
        st.info("Tidak ada data Order yang bisa dianalisis.")
        return

    tahun_list = sorted(status_df["Tahun"].dropna().unique().tolist())
    tahun_terbaru = tahun_list[-1] if tahun_list else None
    col_tahun, col_cabang = st.columns([1, 2])
    with col_tahun:
        pilih_tahun_raw = st.pills(
            "Pilih Tahun (berdasarkan tanggal Order)", [str(t) for t in tahun_list],
            selection_mode="single", default=str(tahun_terbaru) if tahun_terbaru is not None else None,
            key="statusfulfillment_tahun",
        )
    pilih_tahun = int(pilih_tahun_raw) if pilih_tahun_raw else tahun_terbaru
    scope = status_df[status_df["Tahun"] == pilih_tahun]

    cabang_options = sorted(scope["Cabang"].dropna().unique().tolist())
    cleanup_selection("statusfulfillment_cabang", cabang_options)
    with col_cabang:
        pilih_cabang = st.multiselect(
            "Filter Cabang", cabang_options, key="statusfulfillment_cabang", placeholder="Semua (klik untuk filter)",
        )
    if pilih_cabang:
        scope = scope[scope["Cabang"].isin(pilih_cabang)]

    if scope.empty:
        st.info(f"Tidak ada data Order untuk tahun {pilih_tahun}.")
        return

    status_counts = scope["Status"].value_counts()
    total_baris = len(scope)

    c1, c2, c3, c4 = st.columns(4)
    for col, status in zip([c1, c2, c3, c4], STATUS_ORDER):
        jumlah = int(status_counts.get(status, 0))
        pct = jumlah / total_baris * 100 if total_baris else 0
        with col:
            st.markdown(render_card(STATUS_ICON[status], status, FMT_PCT(pct), f"{jumlah:,} baris Order".replace(",", ".")), unsafe_allow_html=True)

    st.markdown("#### Ringkasan Status Fulfillment per Cabang")
    pivot = scope.groupby(["Cabang", "Status"]).size().unstack(fill_value=0)
    for status in STATUS_ORDER:
        if status not in pivot.columns:
            pivot[status] = 0
    pivot = pivot[STATUS_ORDER]
    pivot["Jumlah SO"] = pivot.sum(axis=1)
    pivot = pivot.sort_values("Jumlah SO", ascending=False)

    rows = []
    for cabang, row in pivot.iterrows():
        total = row["Jumlah SO"]
        entry = {"Cabang": cabang, "Jumlah SO": total}
        for status in STATUS_ORDER:
            entry[status] = row[status]
            entry[f"% {status}"] = (row[status] / total * 100) if total else 0
        rows.append(entry)
    status_cols = [col for status in STATUS_ORDER for col in (status, f"% {status}")]
    table = pd.DataFrame(rows, columns=["Cabang", "Jumlah SO"] + status_cols)

    fmt_map = {"Jumlah SO": _fmt_count}
    for status in STATUS_ORDER:
        fmt_map[status] = _fmt_count
        fmt_map[f"% {status}"] = FMT_PCT

    st.dataframe(
        table.style.format(fmt_map).set_properties(subset=["Jumlah SO"] + status_cols, **{"text-align": "right"}),
        use_container_width=True, hide_index=True,
        height=min(auto_table_height(len(table)), 600),
    )
    st.caption("Kolom **%** menunjukkan persentase terhadap total Order Cabang tersebut.")

    st.markdown("---")
    st.markdown("### Penjelasan")
    st.markdown(
        "- **Status Fulfillment** mengelompokkan setiap baris Order ke dalam empat status berdasarkan akumulasi seluruh pengiriman yang pernah terjadi untuk Order tersebut (bukan per baris pengiriman — lihat tab **Fill Rate** untuk analisis pada level pengiriman):\n"
        "  - **Fulfill**: total Qty Actual yang telah dikirim sudah mencapai atau melebihi Qty Order.\n"
        "  - **Fulfill Sebagian**: sudah ada Qty Actual yang dikirim, namun belum mencapai Qty Order.\n"
        "  - **Belum Dikirim**: belum ada Qty Actual sama sekali, namun umur Order masih berada dalam rentang waktu pengiriman yang wajar.\n"
        "  - **Hilang / Trace Data**: belum ada Qty Actual sama sekali dan umur Order sudah melampaui rentang waktu wajar tersebut — kemungkinan pesanan batal tanpa tercatat di sistem, atau data tidak dapat ditelusuri lebih lanjut.\n"
        f"- Ambang waktu untuk status **Hilang / Trace Data** ditetapkan pada **{lost_threshold:.0f} hari** sejak tanggal Order, mengacu pada P95 (persentil ke-95) Lead Time dari seluruh pengiriman yang sudah tuntas secara historis — bukan angka tetap yang ditentukan sepihak. Tanggal acuan \"saat ini\" yang digunakan dalam perhitungan umur Order adalah **{reference_date.strftime('%d-%m-%Y')}**, yaitu tanggal transaksi terbaru yang tersedia pada data (bukan tanggal sistem hari ini), supaya Order yang baru saja dibuat tidak keliru dianggap terlambat.\n"
        "- Data yang digunakan pada tab ini bersumber dari pasangan Order-Actual yang sama dengan tab **Lead Time** dan **Fill Rate** — cakupan data (sejak 2024) yang berlaku pada tab tersebut berlaku pula di sini. Pencocokan Actual ke Order pada tab ini menggunakan kecocokan persis (Nomor SO, Kode Customer, dan Partnumber sama persis) tanpa pendekatan prefix substitusi, sehingga sebagian kecil Order yang sebenarnya sudah terkirim lewat produk substitusi dapat tampak sebagai \"Belum Dikirim\"/\"Hilang\" di sini — bias ini kecil dan condong ke arah under-estimate fulfillment."
    )

    match_rate = stats["n_matched"] / stats["n_supply_total"] * 100 if stats["n_supply_total"] else 0
    with st.expander(f"Rincian tingkat kecocokan data Fill Rate — {match_rate:.1f}% data Actual berhasil dipasangkan dengan Order"):
        st.markdown(
            f"- Total baris data Actual: **{stats['n_supply_total']:,}**\n"
            f"- Kecocokan persis (Nomor SO, Kode Customer, dan Partnumber sama persis): **{stats['n_exact']:,}**\n"
            f"- Kecocokan melalui pendekatan prefix (kandidat substitusi produk): **{stats['n_prefix']:,}**\n"
            f"- Dikecualikan karena Lead Time bernilai negatif: **{stats['n_negative_excluded']:,}**\n"
            f"- Tidak berhasil dipasangkan sama sekali (termasuk seluruh data Actual tahun 2023): **{stats['n_unmatched']:,}**"
        )
