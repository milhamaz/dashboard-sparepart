# ============================================================
# 📦 DATA LOADER — Semua config path & fungsi load data
# ============================================================
import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
import os

# Base directory — bisa di-override via environment variable
BASE_DIR = Path(os.getenv("DASHBOARD_DATA_DIR", r"D:\Dashboard\TASTI"))

kamus_bulan = {
    "January": "Januari", "February": "Februari", "March": "Maret",
    "April": "April", "May": "Mei", "June": "Juni",
    "July": "Juli", "August": "Agustus", "September": "September",
    "October": "Oktober", "November": "November", "December": "Desember"
}

list_bulan_standar = [
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember"
]

ORDER_DIR = BASE_DIR / "Order"
ORDER_SKIP_COLS = [
    "Partname", "Discount", "Item_Disc", "Sales_Net",
    "DPP", "PPN", "Total_Amount", "Group_Part", "Group_Part_Desc",
    "No_PO_Customer", "SO_Status", "Qty_Invoice", 
    "Status_Invoice", "Time_to_TPOS", "Status_SO", "Stop_Sales",
]

SUPPLY_DIR = BASE_DIR / "Supply"
SUPPLY_SKIP_COLS = [
    "Partname", "Item_Disc", "Scp_Disc", "Sales_Net",
    "DPP", "PPN", "Total_Amount", "Group_Part", "Group_Part_Desc",
    "No_PO_Customer", "Item_Disc_Desc", "Base_Disc", "No_Faktur_Pajak",
    "Due_Date", "Performa_Invoice", "Cust_NPWP", "Nomor_DA",
]

CUSTOMER_FILE = BASE_DIR / "Customer.xlsx"
CUSTOMER_COLS = ["Kode_Customer", "Jenis_Customer", "Kelas_Customer", "Cabang", "Kode_Area"]
CUSTOMER_MASTER_COLS = ["Kode_Customer", "Nama_Customer", "Jenis_Customer", "Kelas_Customer", "Cabang", "Kode_Area", "Status"]

TARGET_FILE = BASE_DIR / "Tgt_Cabang.xlsx"
TARGET_COLS = ["Tahun", "Bulan_Num", "Bulan", "Code_Cabang", "Cabang", "Target"]

KALKERJA_FILE = BASE_DIR / "Kal_Kerja.xlsx"
KALKERJA_COLS = ["Tahun", "Bulan", "Bulan_Num", "Hari_Kerja"]

TMO_FILE = BASE_DIR / "PnoTMO.xlsx"
TOPT_FILE = BASE_DIR / "PnoTOPT.xlsx"
CHEM_FILE = BASE_DIR / "PnoChem.xlsx"
BATTERY_FILE = BASE_DIR / "PnoTGB.xlsx"
KP7_FILE = BASE_DIR / "Pno7KP.xlsx"
KP7_PREFIX_FILE = BASE_DIR / "Pno7KP_Prefix.xlsx"
DPROG_FILE = BASE_DIR / "PnoDProg.xlsx"
KELAS_CABANG_FILE = BASE_DIR / "Kelas_Cabang.xlsx"

_MASTER_FILES = [CUSTOMER_FILE, TARGET_FILE, KALKERJA_FILE, TMO_FILE, TOPT_FILE, CHEM_FILE, BATTERY_FILE, KP7_FILE, KP7_PREFIX_FILE, DPROG_FILE, KELAS_CABANG_FILE]

# ── Estimasi COGS/Profit (data pembelian TASTI-ke-Toyota ga praktis ditarik bulk) ──
TMO_PREFIX = "08880"
TOYOTA_DISCOUNT_TMO = 44.0  # % diskon Toyota->TASTI buat kategori TMO, fixed & diketahui

# Margin (persen poin, selisih diskon Toyota-ke-TASTI vs TASTI-ke-customer) per Kelas Cabang
KELAS_MARGIN_RANGE = {
    "A": (7.3, 7.7), "B": (7.5, 7.9), "C": (7.8, 8.3), "D": (8.0, 8.5), "E": (8.3, 9.0),
}
# Cabang dengan rule margin sendiri (di luar sistem Kelas A-E)
CABANG_MARGIN_RANGE = {"JAKARTA": (6.5, 7.1), "MEDAN": (6.8, 7.3)}


@st.cache_data
def load_kelas_cabang():
    """Kelas Cabang (A-E) — dipakai terpisah dari load_and_process_data() karena cuma
    dibutuhkan target_engine.py (fitur cascade Target Cabang->Customer->Salesman), gak
    perlu ikut nambahin tuple besar yang di-unpack di 5 halaman lain."""
    df = pd.read_excel(KELAS_CABANG_FILE, engine="openpyxl")
    df.columns = df.columns.str.strip().str.replace(" ", "_")
    return df


def compute_data_fingerprint():
    """Fingerprint dari mtime seluruh file sumber data (CSV Order/Supply + Excel master).

    st.cache_data hanya menghash berdasarkan bytecode fungsi + argumennya, bukan isi file
    yang dibaca di dalamnya — jadi kalau file di TASTI/ diupdate, cache lama tetap terpakai
    sampai proses Streamlit di-restart manual. Dengan meneruskan fingerprint ini sebagai
    argumen ke load_and_process_data(), cache otomatis invalidasi begitu ada file yang
    berubah/baru, tanpa reload percuma kalau tidak ada perubahan sama sekali.
    """
    stamps = [f"{p.name}:{p.stat().st_mtime}" for p in _MASTER_FILES if p.exists()]
    for directory in (ORDER_DIR, SUPPLY_DIR):
        if directory.exists():
            stamps += [f"{f.name}:{f.stat().st_mtime}" for f in sorted(directory.glob("*.csv"))]
    return "|".join(stamps)


def _load_csvs(directory, prefix, min_year, skip_cols=None):
    dfs = []
    for file in sorted(directory.glob(f"{prefix}*.csv")):
        tahun = int(file.stem[1:3]) + 2000
        if tahun < min_year: continue
        try:
            df = pd.read_csv(file, low_memory=False, encoding="utf-8")
        except UnicodeDecodeError:
            df = pd.read_csv(file, low_memory=False, encoding="latin-1")
        df.columns = df.columns.str.strip().str.replace(" ", "_")
        if skip_cols:
            df = df.drop(columns=[c for c in skip_cols if c in df.columns])
        dfs.append(df)
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


_clean_cols = lambda df: df.columns.str.strip().str.replace(r'\s+', '_', regex=True)


@st.cache_data(show_spinner=False)
def _load_raw_csvs(fingerprint):
    """Load & concat CSV Order/Supply mentah — tahap terberat (I/O banyak file), makanya
    dipisah cache-nya sendiri dari _load_masters()/_merge_and_finalize() supaya progress bar
    di load_and_process_data() nunjukin tahap yang lagi jalan beneran, bukan replay widget
    (lihat catatan di load_and_process_data() soal cached element replay Streamlit)."""
    df_order = _load_csvs(ORDER_DIR, "O", 2024, skip_cols=ORDER_SKIP_COLS)
    df_supply = _load_csvs(SUPPLY_DIR, "S", 2023, skip_cols=SUPPLY_SKIP_COLS)
    return df_order, df_supply


@st.cache_data(show_spinner=False)
def _load_masters(fingerprint):
    """Load & normalisasi semua file Excel master/lookup (Customer, Target, Kal Kerja,
    TMO/T-OPT/Chemical/TGB/7KP/DProg, Kelas Cabang) — dipisah dari _load_raw_csvs() karena
    gak bergantung sama data Order/Supply sama sekali, jadi cache-nya independen."""
    df_customer_raw = pd.read_excel(CUSTOMER_FILE, engine="openpyxl")
    df_customer_raw.columns = df_customer_raw.columns.str.strip().str.replace(" ", "_")

    # Master lengkap (semua customer terdaftar, termasuk yang 0 transaksi) — dipakai buat
    # deteksi kandidat reaktivasi (AKTIF di master tapi ga muncul sama sekali di Supply),
    # beda dari df_customer di bawah yang cuma buat merge atribut ke tiap baris transaksi.
    df_customer_master = df_customer_raw[CUSTOMER_MASTER_COLS].copy()
    df_customer_master["Kode_Customer"] = df_customer_master["Kode_Customer"].astype(str).str.upper().str.strip()
    df_customer_master["Nama_Customer"] = df_customer_master["Nama_Customer"].astype(str).str.strip().str.upper()
    df_customer_master["Status"] = df_customer_master["Status"].astype(str).str.strip().str.upper()

    df_customer = df_customer_raw[CUSTOMER_COLS].copy()
    df_customer["Kode_Customer"] = df_customer["Kode_Customer"].astype(str).str.upper().str.strip()

    df_target = pd.read_excel(TARGET_FILE, engine="openpyxl")
    df_target.columns = df_target.columns.str.strip().str.replace(" ", "_")
    df_target = df_target[TARGET_COLS]
    df_target["Bulan"] = df_target["Bulan"].astype(str).str.strip().str.capitalize().map(kamus_bulan).fillna(df_target["Bulan"]).str.strip()

    df_kalkerja = pd.read_excel(KALKERJA_FILE, engine="openpyxl")
    df_kalkerja.columns = df_kalkerja.columns.str.strip().str.replace(" ", "_")
    df_kalkerja = df_kalkerja[KALKERJA_COLS]
    df_kalkerja["Tahun"] = df_kalkerja["Tahun"].astype(int)
    df_kalkerja["Bulan_Num"] = df_kalkerja["Bulan_Num"].astype(int)
    df_kalkerja["Hari_Kerja"] = df_kalkerja["Hari_Kerja"].astype(float)

    # ── Load Master Data Lookup ──
    df_tmo_lookup = pd.read_excel(TMO_FILE, engine="openpyxl")
    df_tmo_lookup.columns = _clean_cols(df_tmo_lookup)

    df_topt_lookup = pd.read_excel(TOPT_FILE, engine="openpyxl")
    df_topt_lookup.columns = _clean_cols(df_topt_lookup)

    df_chem_lookup = pd.read_excel(CHEM_FILE, engine="openpyxl")
    df_chem_lookup.columns = _clean_cols(df_chem_lookup)

    df_tgb_lookup = pd.read_excel(BATTERY_FILE, engine="openpyxl")
    df_tgb_lookup.columns = _clean_cols(df_tgb_lookup)

    # 🔄 [FIX 1-4] Loop untuk upper & strip Partnumber pada Master Data
    for df_master in [df_tmo_lookup, df_topt_lookup, df_chem_lookup, df_tgb_lookup]:
        df_master["Partnumber"] = df_master["Partnumber"].astype(str).str.upper().str.strip()

    # ── 7KP Master ──
    df_7kp_lookup = pd.read_excel(KP7_FILE, engine="openpyxl")
    df_7kp_lookup.columns = _clean_cols(df_7kp_lookup)
    # 🔄 [FIX 7] Upper & strip untuk master 7KP
    df_7kp_lookup["Partnumber"] = df_7kp_lookup["Partnumber"].astype(str).str.upper().str.strip()
    if "Grup_Part" in df_7kp_lookup.columns:
        df_7kp_lookup.rename(columns={"Grup_Part": "Grup_Part_7KP"}, inplace=True)

    # ── 7KP Prefix Rules (buat tebak partnumber substitusi yang belum diregister) ──
    # dtype=str eksplisit di read_excel — tanpa ini pandas diam-diam infer kolom Prefix
    # jadi angka dan leading zero (mis. "04465") hilang, walau cell aslinya sudah format Text.
    df_7kp_prefix = pd.read_excel(KP7_PREFIX_FILE, engine="openpyxl", dtype={"Prefix": str})
    df_7kp_prefix.columns = _clean_cols(df_7kp_prefix)
    df_7kp_prefix["Prefix"] = df_7kp_prefix["Prefix"].str.strip()

    # ── DProg Master (Item D) ──
    df_dprog_lookup = pd.read_excel(DPROG_FILE, engine="openpyxl")
    df_dprog_lookup.columns = _clean_cols(df_dprog_lookup)
    # 🔄 [FIX 8] Upper & strip untuk master DProg
    df_dprog_lookup["Partnumber"] = df_dprog_lookup["Partnumber"].astype(str).str.upper().str.strip()
    df_dprog_lookup["StartDate"] = pd.to_datetime(df_dprog_lookup["StartDate"], errors="coerce")
    df_dprog_lookup["EndDate"] = pd.to_datetime(df_dprog_lookup["EndDate"], errors="coerce")

    # ── Kelas Cabang (buat estimasi margin COGS — generated dari ranking revenue 2025,
    # exclude Jakarta & Medan yang punya rule margin sendiri) ──
    df_kelas_cabang = pd.read_excel(KELAS_CABANG_FILE, engine="openpyxl")
    df_kelas_cabang.columns = _clean_cols(df_kelas_cabang)

    return (df_customer, df_customer_master, df_target, df_kalkerja, df_tmo_lookup,
            df_topt_lookup, df_chem_lookup, df_tgb_lookup, df_7kp_lookup, df_7kp_prefix,
            df_dprog_lookup, df_kelas_cabang)


@st.cache_data(show_spinner=False)
def _merge_and_finalize(fingerprint, _df_order, _df_supply, _df_customer, _df_target,
                         _df_kelas_cabang):
    """Merge Order/Supply mentah dengan Customer & Target, olah tanggal, turunkan SO_Type,
    normalisasi Partnumber, dan hitung estimasi COGS/Profit.

    Parameter di-prefix underscore supaya Streamlit skip hashing isi DataFrame besar ini —
    `fingerprint` (dari compute_data_fingerprint()) udah cukup jadi cache key yang reliable,
    karena berubah begitu ada file sumber yang berubah/baru.
    """
    df_order = _df_order
    df_supply = _df_supply
    df_customer = _df_customer
    df_target = _df_target
    df_kelas_cabang = _df_kelas_cabang

    df_order["Customer_No"] = df_order["Customer_No"].astype(str).str.upper().str.strip()
    df_order = pd.merge(df_order, df_customer, left_on="Customer_No", right_on="Kode_Customer", how="left").drop(columns=["Kode_Customer"])

    df_supply["Customer_No"] = df_supply["Customer_No"].astype(str).str.upper().str.strip()
    df_supply = pd.merge(df_supply, df_customer, left_on="Customer_No", right_on="Kode_Customer", how="left").drop(columns=["Kode_Customer"])

    # Olah Tanggal & Konversi ke Bahasa Indonesia
    df_order["SO_Date"] = pd.to_datetime(df_order["SO_Date"], dayfirst=True, errors="coerce")
    df_order = df_order.dropna(subset=["SO_Date"])
    df_order["Tahun"] = df_order["SO_Date"].dt.year
    df_order["Bulan_Num"] = df_order["SO_Date"].dt.month
    df_order["Bulan"] = df_order["SO_Date"].dt.strftime("%B").map(kamus_bulan).str.strip()
    df_order["Order"] = (df_order["Qty"] * df_order["Retail_Price"]) / 1.11

    df_supply["Invoice_Date"] = pd.to_datetime(df_supply["Invoice_Date"], dayfirst=True, errors="coerce")
    df_supply = df_supply.dropna(subset=["Invoice_Date"])
    df_supply["Tahun"] = df_supply["Invoice_Date"].dt.year
    df_supply["Bulan_Num"] = df_supply["Invoice_Date"].dt.month
    df_supply["Bulan"] = df_supply["Invoice_Date"].dt.strftime("%B").map(kamus_bulan).str.strip()
    df_supply["Actual"] = (df_supply["Qty"] * df_supply["Retail_Price"]) / 1.11

    df_order = pd.merge(df_order, df_target, on=["Tahun", "Bulan_Num", "Bulan", "Cabang"], how="left")
    df_supply = pd.merge(df_supply, df_target, on=["Tahun", "Bulan_Num", "Bulan", "Cabang"], how="left")

    for df in [df_order, df_supply]:
        if "SO_Type" not in df.columns:
            df["SO_Type"] = None
        df["SO_Type"] = df["SO_Type"].astype(str).str.strip().replace(["nan", "None", ""], None)
        
        if "Campaign_Code" in df.columns:
            mask_blank = df["SO_Type"].isna()
            mask_has_camp = df["Campaign_Code"].notna() & (df["Campaign_Code"].astype(str).str.strip() != "")
            df.loc[mask_blank & mask_has_camp, "SO_Type"] = "C"
            df.loc[mask_blank & ~mask_has_camp, "SO_Type"] = "3"
        else:
            df["SO_Type"] = df["SO_Type"].fillna("3")

    def find_pno_col(df):
        for col in ["Partnumber", "Part_No", "Part_Number", "PartNumber"]:
            if col in df.columns: return col
        return None

    pno_col_order, pno_col_supply = find_pno_col(df_order), find_pno_col(df_supply)
    if pno_col_order and pno_col_order != "Partnumber": df_order = df_order.rename(columns={pno_col_order: "Partnumber"})
    if pno_col_supply and pno_col_supply != "Partnumber": df_supply = df_supply.rename(columns={pno_col_supply: "Partnumber"})
    
    # 🔄 [FIX 5-6] Loop untuk upper & strip Partnumber pada Data Transaksi (Order & Supply)
    for df in [df_order, df_supply]:
        if "Partnumber" in df.columns: 
            df["Partnumber"] = df["Partnumber"].astype(str).str.upper().str.strip()

    # Ensure Scp_Disc column exists and is numeric (for Item D burn calculation)
    if "Scp_Disc" in df_order.columns:
        df_order["Scp_Disc"] = pd.to_numeric(df_order["Scp_Disc"], errors="coerce").fillna(0).astype(int)
    else:
        df_order["Scp_Disc"] = 0

    # ── Estimasi COGS & Profit ──
    # Data pembelian TASTI-ke-Toyota (Modal asli) ga bisa ditarik bulk (limit 10 hari/tarik),
    # jadi di-estimasi: Net Sales pakai kolom Discount asli (diskon TASTI->customer), COGS
    # pakai simulasi diskon Toyota->TASTI (TMO = fixed 44%; selain itu = Discount asli +
    # random margin sesuai Cabang/Kelas). Profit = Net Sales - COGS, bisa minus kalau
    # TASTI ngasih diskon customer lebih gede dari yang didapat dari Toyota (umum di TMO).
    margin_rows = [{"Cabang": c, "Margin_Low": lo, "Margin_High": hi} for c, (lo, hi) in CABANG_MARGIN_RANGE.items()]
    for _, r in df_kelas_cabang.iterrows():
        lo, hi = KELAS_MARGIN_RANGE.get(r["Kelas"], (7.3, 8.7))
        margin_rows.append({"Cabang": r["Cabang"], "Margin_Low": lo, "Margin_High": hi})
    df_margin_range = pd.DataFrame(margin_rows)

    df_supply = df_supply.merge(df_margin_range, on="Cabang", how="left")
    df_supply["Margin_Low"] = df_supply["Margin_Low"].fillna(7.3)
    df_supply["Margin_High"] = df_supply["Margin_High"].fillna(8.7)

    df_supply["Discount"] = pd.to_numeric(df_supply["Discount"], errors="coerce").fillna(0)
    df_supply["Net_Sales"] = df_supply["Qty"] * df_supply["Retail_Price"] * (1 - df_supply["Discount"] / 100) / 1.11

    is_tmo = df_supply["Partnumber"].astype(str).str.startswith(TMO_PREFIX)
    rng = np.random.default_rng(42)  # seed tetap biar angka profit stabil antar reload/rerun
    random_margin = rng.uniform(df_supply["Margin_Low"].to_numpy(), df_supply["Margin_High"].to_numpy())
    df_supply["Simulated_Toyota_Discount"] = np.where(is_tmo, TOYOTA_DISCOUNT_TMO, df_supply["Discount"].to_numpy() + random_margin)

    df_supply["COGS"] = df_supply["Qty"] * df_supply["Retail_Price"] * (1 - df_supply["Simulated_Toyota_Discount"] / 100) / 1.11
    df_supply["Profit"] = df_supply["Net_Sales"] - df_supply["COGS"]
    df_supply["Pct_Profit"] = np.where(df_supply["Actual"] != 0, df_supply["Profit"] / df_supply["Actual"] * 100, 0)
    df_supply["Pct_Profit_Margin"] = np.where(df_supply["Net_Sales"] != 0, df_supply["Profit"] / df_supply["Net_Sales"] * 100, 0)
    df_supply = df_supply.drop(columns=["Margin_Low", "Margin_High"])

    return df_order, df_supply


def load_and_process_data(fingerprint):
    """Orchestrator TIDAK di-@st.cache_data — cuma manggil 3 sub-fungsi yang masing-masing
    cached (_load_raw_csvs, _load_masters, _merge_and_finalize) dan update progress bar di
    antaranya. Sengaja dipisah dari sub-fungsinya supaya st.progress() di sini gak kena
    "cached element replay"-nya Streamlit — kalau widget progress ditaruh DI DALAM fungsi yang
    di-cache, Streamlit bakal replay widget itu tiap kali fungsi dipanggil lagi walau hasilnya
    diambil dari cache (bukan diproses ulang), jadi progress bar-nya nongol lagi seolah loading
    dari awal padahal cuma replay instan. Dengan progress bar di luar, ia cuma keliatan lama
    kalau sub-fungsinya BENERAN cache miss (proses dari nol)."""
    progress_bar = st.progress(0, text="Memulai loading data...")

    progress_bar.progress(10, text="Loading data Order & Supply (CSV)...")
    df_order, df_supply = _load_raw_csvs(fingerprint)

    progress_bar.progress(40, text="Loading master Customer/Target/TMO/T-OPT/Chemical/TGB/7KP/DProg...")
    (df_customer, df_customer_master, df_target, df_kalkerja, df_tmo_lookup, df_topt_lookup,
     df_chem_lookup, df_tgb_lookup, df_7kp_lookup, df_7kp_prefix, df_dprog_lookup,
     df_kelas_cabang) = _load_masters(fingerprint)

    progress_bar.progress(70, text="Merge Order/Supply, olah tanggal, hitung estimasi COGS & Profit...")
    df_order, df_supply = _merge_and_finalize(fingerprint, df_order, df_supply, df_customer, df_target, df_kelas_cabang)

    progress_bar.progress(100, text="Selesai!")
    progress_bar.empty()

    return (df_order, df_supply, df_target, df_tmo_lookup, df_topt_lookup, df_chem_lookup,
            df_tgb_lookup, df_7kp_lookup, df_dprog_lookup, df_kalkerja, df_7kp_prefix, df_customer_master)