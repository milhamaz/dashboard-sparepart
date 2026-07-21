"""Konversi data mentah (CSV/Excel) ke Parquet untuk loading dashboard lebih cepat.

Usage:
    python scripts/convert_to_parquet.py            # convert jika belum fresh
    python scripts/convert_to_parquet.py --force     # paksa rebuild
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.data_loader import (
    _load_csvs, _read_all_masters, _process_merge, _read_part_master_impl,
    _save_to_parquet, _is_parquet_fresh,
    ORDER_DIR, SUPPLY_DIR, ORDER_SKIP_COLS, SUPPLY_SKIP_COLS, PARQUET_DIR,
)


def main(force=False):
    if _is_parquet_fresh() and not force:
        print(f"Parquet sudah fresh (bulan ini). Gunakan --force untuk rebuild.")
        print(f"  Lokasi: {PARQUET_DIR}")
        return

    print("=" * 60)
    print("KONVERSI DATA KE PARQUET")
    print("=" * 60)

    print("\n[1/5] Loading CSV Order & Supply...")
    df_order_raw = _load_csvs(ORDER_DIR, "O", 2024, skip_cols=ORDER_SKIP_COLS)
    df_supply_raw = _load_csvs(SUPPLY_DIR, "S", 2023, skip_cols=SUPPLY_SKIP_COLS)
    print(f"      Order: {len(df_order_raw):,} baris | Supply: {len(df_supply_raw):,} baris")

    print("\n[2/5] Loading master data (Excel)...")
    (df_customer, df_customer_master, df_target, df_kalkerja, df_tmo_lookup,
     df_topt_lookup, df_chem_lookup, df_tgb_lookup, df_7kp_lookup, df_7kp_prefix,
     df_dprog_lookup, df_kelas_cabang) = _read_all_masters()
    print(f"      Customer master: {len(df_customer_master):,} baris")

    print("\n[3/5] Merge data & hitung estimasi COGS...")
    df_order, df_supply = _process_merge(
        df_order_raw, df_supply_raw, df_customer, df_target)
    print(f"      Order final: {len(df_order):,} baris | Supply final: {len(df_supply):,} baris")

    print("\n[4/5] Loading part master...")
    df_part_master = _read_part_master_impl()
    print(f"      Part master: {len(df_part_master):,} baris")

    print("\n[5/5] Menyimpan Parquet...")
    _save_to_parquet(
        df_order, df_supply, df_target, df_tmo_lookup, df_topt_lookup,
        df_chem_lookup, df_tgb_lookup, df_7kp_lookup, df_dprog_lookup,
        df_kalkerja, df_7kp_prefix, df_customer_master,
        df_part_master, df_kelas_cabang)

    # Hitung total size file Parquet
    total_bytes = sum(f.stat().st_size for f in PARQUET_DIR.glob("*.parquet"))
    total_mb = total_bytes / (1024 * 1024)
    n_files = len(list(PARQUET_DIR.glob("*.parquet")))

    print(f"\nSelesai! {n_files} file Parquet tersimpan di {PARQUET_DIR}")
    print(f"Total size: {total_mb:.1f} MB")
    print("=" * 60)


if __name__ == "__main__":
    main(force="--force" in sys.argv)
