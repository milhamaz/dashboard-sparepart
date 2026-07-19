# ============================================================
# 🧬 MAT GROUP ENGINE — Klasifikasi Partnumber -> Kategori Produk (part_master.xlsx)
# ============================================================
"""
Menempelkan kolom Mat_Group (TGP/AVANZA/TOOLS & TGA/DYNA-ARPI/AC/TGB/TMO/CHEMICAL/T-OPT/
BUSI) ke tiap baris Order/Supply lewat part_master.xlsx, dengan 3 tahap pencocokan
berurutan yang sudah divalidasi manual sebelum dipakai di sini (lihat sesi rapi-rapi
part_master.xlsx — coverage tervalidasi 100% terhadap PnoTMO/PnoChem/PnoTGB/PnoTOPT):

  1. part_number_substitusi — dicek LEBIH DULU, karena kolom ini merepresentasikan kode
     PENGGANTI resmi dari suatu Partnumber (baris lama di part_master menunjuk ke kode
     barunya). Kalau Partnumber transaksi ternyata adalah kode baru itu, mat_group dari
     baris lama yang menunjuknya dianggap paling relevan.
  2. part_number — exact match langsung ke kolom utama, kalau tahap 1 tidak ketemu.
  3. Fallback prefix 5-karakter — pola yang sama dipakai leadtime_engine.py (Order-Actual
     link) dan Pno7KP_Prefix.xlsx, untuk kasus substitusi produk yang belum terdaftar resmi
     di part_number_substitusi. Kategori diambil dari mat_group PALING SERING (mode) di
     antara semua part_number yang berbagi prefix yang sama.

Sisa yang tidak ketemu sama sekali di-tag "Unclassified" — SENGAJA tidak dibuang, supaya
total revenue tetap rekonsiliasi dengan angka di tab lain (Performance, dst); cuma
kategorinya yang belum diketahui, bukan datanya yang hilang.
"""
import streamlit as st

PREFIX_LEN = 5

MATGROUP_ORDER = [
    "TGP", "AVANZA", "TOOLS & TGA", "DYNA/ARPI", "AC", "TGB", "TMO",
    "CHEMICAL", "T-OPT", "BUSI", "Unclassified",
]
MATGROUP_COLORS = {
    "TGP": "#3987e5", "AVANZA": "#f59e0b", "TOOLS & TGA": "#8b5cf6", "DYNA/ARPI": "#14b8a6",
    "AC": "#38bdf8", "TGB": "#eab308", "TMO": "#f97316", "CHEMICAL": "#22c55e",
    "T-OPT": "#ec4899", "BUSI": "#d946ef", "Unclassified": "#64748b",
}


@st.cache_data(show_spinner="Mencocokkan Partnumber ke Kategori Produk...")
def compute_matgroup_link(df, df_part_master, partnumber_col="Partnumber"):
    """Return (df_with_Mat_Group, stats). `stats` berisi hitungan tiap tahap pencocokan
    (n_substitusi/n_exact/n_prefix/n_unclassified) buat expander transparansi — pola yang
    sama dengan `stats` di leadtime_engine.compute_order_actual_link()."""
    cols_stats = ["n_total", "n_substitusi", "n_exact", "n_prefix", "n_unclassified"]

    if df.empty or df_part_master is None or df_part_master.empty:
        result = df.copy()
        result["Mat_Group"] = "Unclassified"
        return result, dict(zip(cols_stats, [len(df), 0, 0, 0, len(df)]))

    pm = df_part_master
    sub_map = (
        pm.dropna(subset=["part_number_substitusi"])
        .drop_duplicates("part_number_substitusi", keep="first")
        .set_index("part_number_substitusi")["mat_group"]
    )
    exact_map = pm.set_index("part_number")["mat_group"]
    prefix_map = (
        pm.assign(_prefix=pm["part_number"].str[:PREFIX_LEN])
        .groupby("_prefix")["mat_group"]
        .agg(lambda s: s.mode().iloc[0])
    )

    result = df.copy()
    pno = result[partnumber_col].astype(str).str.upper().str.strip()

    mg = pno.map(sub_map)
    n_substitusi = int(mg.notna().sum())

    need_exact = mg.isna()
    mg.loc[need_exact] = pno.loc[need_exact].map(exact_map)
    n_exact = int(mg.notna().sum()) - n_substitusi

    need_prefix = mg.isna()
    mg.loc[need_prefix] = pno.loc[need_prefix].str[:PREFIX_LEN].map(prefix_map)
    n_prefix = int(mg.notna().sum()) - n_substitusi - n_exact

    n_unclassified = int(mg.isna().sum())
    result["Mat_Group"] = mg.fillna("Unclassified")

    stats = dict(zip(cols_stats, [len(df), n_substitusi, n_exact, n_prefix, n_unclassified]))
    return result, stats
