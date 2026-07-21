# Dashboard Sparepart

Streamlit multipage dashboard untuk analisis penjualan sparepart Toyota (TASTI).
Data sumber di `TASTI/` (git-ignored, confidential).

## Menjalankan

```bash
streamlit run Dashboard.py
```

Converter Parquet (opsional, auto-trigger saat ganti bulan):
```bash
python scripts/convert_to_parquet.py          # convert jika belum fresh
python scripts/convert_to_parquet.py --force   # paksa rebuild
```

Synthetic data generator (untuk deploy publik):
```bash
python scripts/generate_synthetic.py          # output ke TASTI_SYNTHETIC/
python scripts/generate_synthetic.py --seed 42 --scale 0.6
```

## Struktur project

```
Dashboard.py                  # Entry point, halaman Home (card navigasi)
pages/
  01_Laporan_Financial.py     # Performance, Pacing, TMO, Chemical, TGB, T-OPT, COGS & Profit
  02_SDM.py                   # Target Cabang, Target Salesman, Cabang/Salesman Leaderboard,
                              #   Productivity, Segmentasi
  03_Customer.py              # Customer Target, Retention & Churn, Alert, Cross-sell Gap,
                              #   Diversifikasi, Suggested Status
  04_Marketing_Program.py     # 7KP, Item D (DProg), Gebyur, Kombo Servis
  05_Operasional_Partnumber.py# Kelebaran, Kedalaman
  06_Analisa_Produk.py        # Komposisi Kategori, Profitabilitas, Moving Analysis
views/
  tab_*.py                    # Satu file = satu tab, export fungsi render()
utils/
  data_loader.py              # Config path, Parquet caching, CSV/Excel loading, merge, COGS
  filters.py                  # Sidebar filter umum (tahun, bulan, cabang, dll)
  components.py               # Komponen UI reusable (metric cards, footer)
  styles.py                   # CSS injection
  *_engine.py                 # Business logic engines (target, matgroup, leadtime, dll)
scripts/
  convert_to_parquet.py       # CLI converter CSV/Excel → Parquet
  generate_synthetic.py      # Synthetic data generator (deploy publik)
  data_params.json           # Statistical parameters (aggregate only, no PII)
TASTI_SYNTHETIC/             # Generated fake data (committed for deploy)
```

## Data flow

```
TASTI/Order/*.csv  ─┐
TASTI/Supply/*.csv ─┤  data_loader.py     TASTI/parquet/*.parquet
TASTI/*.xlsx       ─┴→ (load, merge,   →  (14 file, auto-generated)
                        normalize, COGS)
                              │
                    ┌─────────┴──────────┐
                    ▼                    ▼
              Parquet fresh?         Parquet stale?
              → load instant         → pipeline CSV/Excel
                                     → save Parquet
                                     → return
```

- **Freshness check**: bulan sama + fingerprint file sumber cocok + schema version match.
- **Parquet di-rebuild otomatis** saat server start pertama bulan baru,
  atau jika ada file sumber yang berubah (mtime), atau jika schema version berubah
  (misal penambahan kolom `Mat_Group` ke supply/order).
- CSV/Excel asli TIDAK dihapus — Parquet adalah cache, bukan source of truth.

## Data sumber (TASTI/, git-ignored)

| Path | Isi |
|---|---|
| `Order/O{YY}S{sem}.csv` | Data SO (order) per semester |
| `Supply/S{YY}S{sem}.csv` | Data invoice (supply) per semester |
| `Customer.xlsx` | Master customer (kode, nama, jenis, kelas, cabang, area) |
| `Tgt_Cabang.xlsx` | Target penjualan per cabang per bulan |
| `Kal_Kerja.xlsx` | Kalender hari kerja |
| `part_master.xlsx` | Klasifikasi partnumber → mat_group |
| `Pno*.xlsx` | Lookup partnumber per kategori (TMO, T-OPT, Chemical, TGB, 7KP, DProg) |
| `Kelas_Cabang.xlsx` | Klasifikasi cabang (A-E) |

## Kolom computed (baked into Parquet)

- `df_supply.Mat_Group` — kategori produk per baris supply (exact → prefix match via part_master)
- `df_supply.COGS / Profit / Net_Sales / Pct_Profit_Margin` — estimasi COGS & profit
- `df_order.Mat_Group` — kategori produk per baris order (sama logic)

## Konvensi

- **Nama file `views/tab_*.py`** harus match dengan label tab yang tampil di UI.
- **Nama file `pages/NN_*.py`** harus match dengan judul halaman.
- **Setiap halaman baru** harus ditambahkan card + button di `Dashboard.py`.
- **Semua data confidential** — jangan commit isi TASTI/ atau screenshot berisi data real.
- **`TASTI_SYNTHETIC/`** berisi data sintetik yang aman untuk commit & deploy publik.
- **`DASHBOARD_DATA_DIR`** env var override data folder; tanpa env var, auto-fallback
  `TASTI` → `TASTI_SYNTHETIC`.
- **`_PARQUET_SCHEMA_VERSION`** di `data_loader.py` harus di-bump saat menambah/menghapus kolom
  di pipeline, supaya Parquet cache lama otomatis ter-invalidate.

## Dependencies

- Python 3.10+
- streamlit, pandas, numpy, plotly, openpyxl, pyarrow, scikit-learn
