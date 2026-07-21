# ============================================================
# DATA LOADER — Config, Parquet caching, loading & processing
# ============================================================
import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import json
import os

# ────────────────────────────────────────────────────────────
# Konfigurasi path & konstanta
# ────────────────────────────────────────────────────────────

_DEFAULT_DATA = Path(__file__).resolve().parent.parent / "TASTI"
if not _DEFAULT_DATA.exists():
    _DEFAULT_DATA = Path(__file__).resolve().parent.parent / "TASTI_SYNTHETIC"
BASE_DIR = Path(os.getenv("DASHBOARD_DATA_DIR", str(_DEFAULT_DATA)))
PARQUET_DIR = BASE_DIR / "parquet"
CONVERT_META = PARQUET_DIR / "convert_meta.json"

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
PART_MASTER_FILE = BASE_DIR / "part_master.xlsx"

_MASTER_FILES = [
    CUSTOMER_FILE, TARGET_FILE, KALKERJA_FILE, TMO_FILE, TOPT_FILE,
    CHEM_FILE, BATTERY_FILE, KP7_FILE, KP7_PREFIX_FILE, DPROG_FILE,
    KELAS_CABANG_FILE, PART_MASTER_FILE,
]

# Diskon Toyota->TASTI per kategori produk (mat_group). Sumber: konfirmasi manual pemilik
# TASTI, bukan data sistem — angka flat per kategori, tidak berjenjang per cabang.
MATGROUP_TOYOTA_DISCOUNT = {
    "TMO": 44.0, "TGP": 31.0, "AVANZA": 31.0, "TOOLS & TGA": 31.0,
    "CHEMICAL": 31.0, "DYNA/ARPI": 31.0, "BUSI": 31.0,
    "T-OPT": 27.0, "AC": 25.0, "TGB": 25.0,
}
MATGROUP_TOYOTA_DISCOUNT_DEFAULT = 31.0

_PARQUET_SCHEMA_VERSION = 2  # bump when adding/removing columns to invalidate old cache

# Konsolidasi Salesman_Code yang kepecah di raw data (migrasi/typo kode cabang di source
# system) — supaya transaksi lama & baru ke-grouping sebagai 1 orang.
SALESMAN_CODE_ALIAS = {
    "2C30-S2": "2C11-S13",   # FAIZ NUR ALAWY
    "2C10-S13": "2C11-S13",  # FAIZ NUR ALAWY
}


# ────────────────────────────────────────────────────────────
# Fingerprint — cache-key dari mtime seluruh file sumber
# ────────────────────────────────────────────────────────────

def compute_data_fingerprint():
    stamps = [f"{p.name}:{p.stat().st_mtime}" for p in _MASTER_FILES if p.exists()]
    for directory in (ORDER_DIR, SUPPLY_DIR):
        if directory.exists():
            stamps += [f"{f.name}:{f.stat().st_mtime}" for f in sorted(directory.glob("*.csv"))]
    return "|".join(stamps)


# ────────────────────────────────────────────────────────────
# Parquet cache — freshness check, save, load
# ────────────────────────────────────────────────────────────

def _is_parquet_fresh():
    """Fresh jika bulan sama DAN tidak ada file sumber yang berubah sejak convert."""
    if not CONVERT_META.exists():
        return False
    with open(CONVERT_META) as f:
        meta = json.load(f)
    now = datetime.now()
    if meta.get("year_month") != f"{now.year}-{now.month:02d}":
        return False
    if meta.get("schema_version") != _PARQUET_SCHEMA_VERSION:
        return False
    return meta.get("source_fingerprint") == compute_data_fingerprint()


def _save_to_parquet(df_order, df_supply, df_target, df_tmo_lookup, df_topt_lookup,
                     df_chem_lookup, df_tgb_lookup, df_7kp_lookup, df_dprog_lookup,
                     df_kalkerja, df_7kp_prefix, df_customer_master,
                     df_part_master, df_kelas_cabang):
    PARQUET_DIR.mkdir(parents=True, exist_ok=True)
    frames = {
        "order": df_order, "supply": df_supply, "target": df_target,
        "kalkerja": df_kalkerja, "customer_master": df_customer_master,
        "tmo_lookup": df_tmo_lookup, "topt_lookup": df_topt_lookup,
        "chem_lookup": df_chem_lookup, "tgb_lookup": df_tgb_lookup,
        "kp7_lookup": df_7kp_lookup, "kp7_prefix": df_7kp_prefix,
        "dprog_lookup": df_dprog_lookup, "part_master": df_part_master,
        "kelas_cabang": df_kelas_cabang,
    }
    for name, df in frames.items():
        df.to_parquet(PARQUET_DIR / f"{name}.parquet", index=False)

    now = datetime.now()
    with open(CONVERT_META, "w") as f:
        json.dump({
            "year_month": f"{now.year}-{now.month:02d}",
            "converted_at": now.isoformat(),
            "source_fingerprint": compute_data_fingerprint(),
            "schema_version": _PARQUET_SCHEMA_VERSION,
        }, f, indent=2)


def _load_from_parquet():
    """Load semua DataFrame dari Parquet — return tuple sama dengan load_and_process_data."""
    r = lambda name: pd.read_parquet(PARQUET_DIR / f"{name}.parquet")
    return (
        r("order"), r("supply"), r("target"),
        r("tmo_lookup"), r("topt_lookup"), r("chem_lookup"),
        r("tgb_lookup"), r("kp7_lookup"), r("dprog_lookup"),
        r("kalkerja"), r("kp7_prefix"), r("customer_master"),
    )


# ────────────────────────────────────────────────────────────
# Core I/O & processing — standalone (no Streamlit dependency)
# Fungsi-fungsi ini bisa dipanggil dari convert_to_parquet.py
# tanpa perlu Streamlit running.
# ────────────────────────────────────────────────────────────

_clean_cols = lambda df: df.columns.str.strip().str.replace(r'\s+', '_', regex=True)


def _load_csvs(directory, prefix, min_year, skip_cols=None):
    dfs = []
    for file in sorted(directory.glob(f"{prefix}*.csv")):
        tahun = int(file.stem[1:3]) + 2000
        if tahun < min_year:
            continue
        try:
            df = pd.read_csv(file, low_memory=False, encoding="utf-8")
        except UnicodeDecodeError:
            df = pd.read_csv(file, low_memory=False, encoding="latin-1")
        df.columns = df.columns.str.strip().str.replace(" ", "_")
        if skip_cols:
            df = df.drop(columns=[c for c in skip_cols if c in df.columns])
        dfs.append(df)
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


def _read_all_masters():
    """Read & normalize semua file Excel master/lookup."""
    df_customer_raw = pd.read_excel(CUSTOMER_FILE, engine="openpyxl")
    df_customer_raw.columns = df_customer_raw.columns.str.strip().str.replace(" ", "_")

    df_customer_master = df_customer_raw[CUSTOMER_MASTER_COLS].copy()
    df_customer_master["Kode_Customer"] = df_customer_master["Kode_Customer"].astype(str).str.upper().str.strip()
    df_customer_master["Nama_Customer"] = df_customer_master["Nama_Customer"].astype(str).str.strip().str.upper()
    df_customer_master["Status"] = df_customer_master["Status"].astype(str).str.strip().str.upper()

    df_customer = df_customer_raw[CUSTOMER_COLS].copy()
    df_customer["Kode_Customer"] = df_customer["Kode_Customer"].astype(str).str.upper().str.strip()

    df_target = pd.read_excel(TARGET_FILE, engine="openpyxl")
    df_target.columns = df_target.columns.str.strip().str.replace(" ", "_")
    df_target = df_target[TARGET_COLS]
    df_target["Bulan"] = (df_target["Bulan"].astype(str).str.strip().str.capitalize()
                          .map(kamus_bulan).fillna(df_target["Bulan"]).str.strip())

    df_kalkerja = pd.read_excel(KALKERJA_FILE, engine="openpyxl")
    df_kalkerja.columns = df_kalkerja.columns.str.strip().str.replace(" ", "_")
    df_kalkerja = df_kalkerja[KALKERJA_COLS]
    df_kalkerja["Tahun"] = df_kalkerja["Tahun"].astype(int)
    df_kalkerja["Bulan_Num"] = df_kalkerja["Bulan_Num"].astype(int)
    df_kalkerja["Hari_Kerja"] = df_kalkerja["Hari_Kerja"].astype(float)

    df_tmo_lookup = pd.read_excel(TMO_FILE, engine="openpyxl")
    df_tmo_lookup.columns = _clean_cols(df_tmo_lookup)
    df_topt_lookup = pd.read_excel(TOPT_FILE, engine="openpyxl")
    df_topt_lookup.columns = _clean_cols(df_topt_lookup)
    df_chem_lookup = pd.read_excel(CHEM_FILE, engine="openpyxl")
    df_chem_lookup.columns = _clean_cols(df_chem_lookup)
    df_tgb_lookup = pd.read_excel(BATTERY_FILE, engine="openpyxl")
    df_tgb_lookup.columns = _clean_cols(df_tgb_lookup)

    for df_m in [df_tmo_lookup, df_topt_lookup, df_chem_lookup, df_tgb_lookup]:
        df_m["Partnumber"] = df_m["Partnumber"].astype(str).str.upper().str.strip()

    df_7kp_lookup = pd.read_excel(KP7_FILE, engine="openpyxl")
    df_7kp_lookup.columns = _clean_cols(df_7kp_lookup)
    df_7kp_lookup["Partnumber"] = df_7kp_lookup["Partnumber"].astype(str).str.upper().str.strip()
    if "Grup_Part" in df_7kp_lookup.columns:
        df_7kp_lookup.rename(columns={"Grup_Part": "Grup_Part_7KP"}, inplace=True)

    # dtype=str eksplisit — tanpa ini pandas infer Prefix jadi angka, leading zero hilang.
    df_7kp_prefix = pd.read_excel(KP7_PREFIX_FILE, engine="openpyxl", dtype={"Prefix": str})
    df_7kp_prefix.columns = _clean_cols(df_7kp_prefix)
    df_7kp_prefix["Prefix"] = df_7kp_prefix["Prefix"].str.strip()

    df_dprog_lookup = pd.read_excel(DPROG_FILE, engine="openpyxl")
    df_dprog_lookup.columns = _clean_cols(df_dprog_lookup)
    df_dprog_lookup["Partnumber"] = df_dprog_lookup["Partnumber"].astype(str).str.upper().str.strip()
    df_dprog_lookup["StartDate"] = pd.to_datetime(df_dprog_lookup["StartDate"], errors="coerce")
    df_dprog_lookup["EndDate"] = pd.to_datetime(df_dprog_lookup["EndDate"], errors="coerce")

    df_kelas_cabang = pd.read_excel(KELAS_CABANG_FILE, engine="openpyxl")
    df_kelas_cabang.columns = _clean_cols(df_kelas_cabang)

    return (df_customer, df_customer_master, df_target, df_kalkerja, df_tmo_lookup,
            df_topt_lookup, df_chem_lookup, df_tgb_lookup, df_7kp_lookup, df_7kp_prefix,
            df_dprog_lookup, df_kelas_cabang)


def _process_merge(df_order, df_supply, df_customer, df_target):
    """Merge Order/Supply + Customer/Target, derive dates, normalize Partnumber, compute COGS."""
    df_order = df_order.copy()
    df_supply = df_supply.copy()

    df_order["Customer_No"] = df_order["Customer_No"].astype(str).str.upper().str.strip()
    df_order = pd.merge(df_order, df_customer, left_on="Customer_No",
                        right_on="Kode_Customer", how="left").drop(columns=["Kode_Customer"])

    df_supply["Customer_No"] = df_supply["Customer_No"].astype(str).str.upper().str.strip()
    df_supply = pd.merge(df_supply, df_customer, left_on="Customer_No",
                         right_on="Kode_Customer", how="left").drop(columns=["Kode_Customer"])

    # Olah tanggal & konversi ke Bahasa Indonesia
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

    # Normalize Partnumber column name
    def _find_pno_col(df):
        for col in ["Partnumber", "Part_No", "Part_Number", "PartNumber"]:
            if col in df.columns:
                return col
        return None

    for df in [df_order, df_supply]:
        pno_col = _find_pno_col(df)
        if pno_col and pno_col != "Partnumber":
            df.rename(columns={pno_col: "Partnumber"}, inplace=True)

    for df in [df_order, df_supply]:
        if "Partnumber" in df.columns:
            df["Partnumber"] = df["Partnumber"].astype(str).str.upper().str.strip()
            # Partnumber notasi ilmiah ("2.33008E+11") = korupsi ekspor Excel di sistem sumber.
            # Dinormalisasi ke bentuk digit supaya prefix 5-karakter engine tetap mengenali.
            sci_mask = df["Partnumber"].str.fullmatch(r"\d+(?:\.\d+)?E\+\d+")
            if sci_mask.any():
                df.loc[sci_mask, "Partnumber"] = (
                    df.loc[sci_mask, "Partnumber"].astype(float).map(lambda v: f"{v:.0f}")
                )

    for df in [df_order, df_supply]:
        if "Salesman_Code" in df.columns:
            df["Salesman_Code"] = df["Salesman_Code"].astype(str).str.strip().replace(SALESMAN_CODE_ALIAS)

    if "Scp_Disc" in df_order.columns:
        df_order["Scp_Disc"] = pd.to_numeric(df_order["Scp_Disc"], errors="coerce").fillna(0).astype(int)
    else:
        df_order["Scp_Disc"] = 0

    # ── Estimasi COGS & Profit ──
    df_supply["Discount"] = pd.to_numeric(df_supply["Discount"], errors="coerce").fillna(0)
    df_supply["Net_Sales"] = df_supply["Qty"] * df_supply["Retail_Price"] * (1 - df_supply["Discount"] / 100) / 1.11

    df_pm = pd.read_excel(PART_MASTER_FILE, engine="openpyxl")
    df_pm.columns = df_pm.columns.str.strip().str.replace(" ", "_")
    df_pm["part_number"] = df_pm["part_number"].astype(str).str.upper().str.strip()
    exact_mg = df_pm.set_index("part_number")["mat_group"]
    prefix_mg = (df_pm.assign(pfx=df_pm["part_number"].str[:5])
                 .drop_duplicates("pfx").set_index("pfx")["mat_group"])

    pno_s = df_supply["Partnumber"].astype(str).str.upper().str.strip()
    mg = pno_s.map(exact_mg).fillna(pno_s.str[:5].map(prefix_mg)).fillna("Unclassified")

    df_supply["Mat_Group"] = mg

    pno_o = df_order["Partnumber"].astype(str).str.upper().str.strip()
    df_order["Mat_Group"] = pno_o.map(exact_mg).fillna(pno_o.str[:5].map(prefix_mg)).fillna("Unclassified")
    df_supply["Toyota_Discount"] = mg.map(MATGROUP_TOYOTA_DISCOUNT).fillna(MATGROUP_TOYOTA_DISCOUNT_DEFAULT)
    df_supply["COGS"] = df_supply["Qty"] * df_supply["Retail_Price"] * (1 - df_supply["Toyota_Discount"] / 100) / 1.11
    df_supply["Profit"] = df_supply["Net_Sales"] - df_supply["COGS"]
    df_supply["Pct_Profit"] = np.where(df_supply["Actual"] != 0,
                                       df_supply["Profit"] / df_supply["Actual"] * 100, 0)
    df_supply["Pct_Profit_Margin"] = np.where(df_supply["Net_Sales"] != 0,
                                              df_supply["Profit"] / df_supply["Net_Sales"] * 100, 0)
    df_supply = df_supply.drop(columns=["Toyota_Discount"])

    return df_order, df_supply


def _read_part_master_impl():
    df = pd.read_excel(PART_MASTER_FILE, engine="openpyxl")
    df.columns = df.columns.str.strip().str.replace(" ", "_")
    df["part_number"] = df["part_number"].astype(str).str.upper().str.strip()
    df["part_number_substitusi"] = df["part_number_substitusi"].astype(str).str.upper().str.strip()
    df.loc[df["part_number_substitusi"].isin(["NAN", "NONE", ""]), "part_number_substitusi"] = pd.NA
    return df


# ────────────────────────────────────────────────────────────
# Streamlit-cached wrappers
# ────────────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def _load_raw_csvs(fingerprint):
    return (_load_csvs(ORDER_DIR, "O", 2024, skip_cols=ORDER_SKIP_COLS),
            _load_csvs(SUPPLY_DIR, "S", 2023, skip_cols=SUPPLY_SKIP_COLS))


@st.cache_data(show_spinner=False)
def _load_masters(fingerprint):
    return _read_all_masters()


@st.cache_data(show_spinner=False)
def _merge_and_finalize(fingerprint, _df_order, _df_supply, _df_customer, _df_target):
    return _process_merge(_df_order, _df_supply, _df_customer, _df_target)


@st.cache_data(show_spinner=False)
def _load_all_parquet(meta_stamp):
    """Cached Parquet loader. meta_stamp berubah saat Parquet di-rebuild."""
    return _load_from_parquet()


# ────────────────────────────────────────────────────────────
# Public API
# ────────────────────────────────────────────────────────────

@st.cache_data
def load_kelas_cabang():
    pq = PARQUET_DIR / "kelas_cabang.parquet"
    if pq.exists() and _is_parquet_fresh():
        return pd.read_parquet(pq)
    df = pd.read_excel(KELAS_CABANG_FILE, engine="openpyxl")
    df.columns = df.columns.str.strip().str.replace(" ", "_")
    return df


@st.cache_data
def load_part_master(fingerprint):
    pq = PARQUET_DIR / "part_master.parquet"
    if pq.exists() and _is_parquet_fresh():
        return pd.read_parquet(pq)
    return _read_part_master_impl()


def load_and_process_data(fingerprint):
    """Orchestrator — cek Parquet dulu, fallback ke CSV/Excel pipeline + auto-save Parquet."""
    if _is_parquet_fresh():
        progress = st.progress(0, text="Loading dari cache Parquet...")
        with open(CONVERT_META) as f:
            stamp = json.load(f)["converted_at"]
        result = _load_all_parquet(stamp)
        progress.progress(100, text="Selesai!")
        progress.empty()
        return result

    progress = st.progress(0, text="Konversi data (pertama kali bulan ini)...")

    progress.progress(10, text="Loading data Order & Supply (CSV)...")
    df_order_raw, df_supply_raw = _load_raw_csvs(fingerprint)

    progress.progress(40, text="Loading master Customer/Target/TMO/T-OPT/Chemical/TGB/7KP/DProg...")
    (df_customer, df_customer_master, df_target, df_kalkerja, df_tmo_lookup,
     df_topt_lookup, df_chem_lookup, df_tgb_lookup, df_7kp_lookup, df_7kp_prefix,
     df_dprog_lookup, df_kelas_cabang) = _load_masters(fingerprint)

    progress.progress(70, text="Merge Order/Supply, olah tanggal, hitung estimasi COGS & Profit...")
    df_order, df_supply = _merge_and_finalize(
        fingerprint, df_order_raw, df_supply_raw, df_customer, df_target)

    progress.progress(90, text="Menyimpan cache Parquet...")
    _save_to_parquet(
        df_order, df_supply, df_target, df_tmo_lookup, df_topt_lookup,
        df_chem_lookup, df_tgb_lookup, df_7kp_lookup, df_dprog_lookup,
        df_kalkerja, df_7kp_prefix, df_customer_master,
        _read_part_master_impl(), df_kelas_cabang)

    progress.progress(100, text="Selesai!")
    progress.empty()

    return (df_order, df_supply, df_target, df_tmo_lookup, df_topt_lookup, df_chem_lookup,
            df_tgb_lookup, df_7kp_lookup, df_dprog_lookup, df_kalkerja, df_7kp_prefix,
            df_customer_master)
