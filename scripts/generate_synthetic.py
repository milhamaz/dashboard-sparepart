"""
Synthetic Data Generator for Dashboard Sparepart.

Reads statistical parameters from data_params.json and generates
CSV/Excel files with identical schema to the real TASTI data.
No real data is used — only aggregate distributions.

Usage:
    python scripts/generate_synthetic.py [--out FOLDER] [--seed 42] [--scale 0.3]
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

PARAMS_FILE = Path(__file__).parent / "data_params.json"

BULAN_MAP = {
    1: "Januari", 2: "Februari", 3: "Maret", 4: "April",
    5: "Mei", 6: "Juni", 7: "Juli", 8: "Agustus",
    9: "September", 10: "Oktober", 11: "November", 12: "Desember",
}

MATGROUPS = ["TGP", "AVANZA", "TOOLS & TGA", "DYNA/ARPI", "AC",
             "TGB", "TMO", "CHEMICAL", "T-OPT", "BUSI"]

# ── Raw CSV columns (what data_loader expects BEFORE merge) ────
RAW_SUPPLY_COLS = [
    "Invoice_No", "SO_No", "Invoice_Date", "Customer_No", "Customer_Name",
    "Salesman_Code", "Salesman_Name", "Partnumber", "Qty", "Retail_Price",
    "Discount", "SO_Type",
]
RAW_ORDER_COLS = [
    "SO_No", "SO_No_TPOS", "SO_Date", "Customer_No", "Customer_Name",
    "SO_Type", "Salesman_Code", "Salesman_Name", "Partnumber", "Qty",
    "Retail_Price", "Scp_Disc", "Campaign_Code",
]

# ── Fake name pools ────────────────────────────────────────────
_PREFIX = ["PT", "CV", "UD", "Toko", "PD", "TB", "PT"]
_NAME1 = [
    "Maju", "Sinar", "Berkah", "Jaya", "Sejahtera", "Abadi", "Mandiri",
    "Karya", "Makmur", "Sentosa", "Utama", "Prima", "Bersama", "Cahaya",
    "Gemilang", "Lestari", "Mulia", "Perkasa", "Setia", "Indah",
    "Anugerah", "Harapan", "Nusantara", "Pratama", "Cipta", "Dharma",
    "Graha", "Mega", "Surya", "Teknik", "Buana", "Logam", "Mitra",
    "Persada", "Timur", "Barat", "Selatan", "Utara", "Agung", "Putra",
]
_NAME2 = [
    "Motor", "Otomotif", "Parts", "Sparepart", "Teknik", "Mobilindo",
    "Auto", "Diesel", "Jasa", "Makmur", "Sukses", "Mandiri", "Sentosa",
    "Perdana", "Niaga", "Abadi", "Perkasa", "Utama", "Sejahtera", "Pratama",
    "Gemilang", "Lestari", "Bersatu", "Multindo", "Karya", "Raya",
    "Diesel Motor", "Servis", "Bengkel", "Autoparts",
]
_FIRST = [
    "Budi", "Agus", "Dedi", "Eko", "Hadi", "Iwan", "Joko", "Kurnia",
    "Lukman", "Maman", "Nandi", "Adi", "Rizki", "Sigit", "Teguh",
    "Umar", "Wahyu", "Yanto", "Zainal", "Arif", "Bambang", "Dani",
    "Fajar", "Gunawan", "Hendra", "Irfan", "Kusuma", "Mahendra",
    "Nugroho", "Prasetyo", "Rudi", "Surya", "Taufik", "Wibowo",
    "Siti", "Ani", "Dewi", "Rina", "Sri", "Yuli", "Nina", "Putri",
    "Ratna", "Wati", "Lina", "Maya", "Fitri", "Indah", "Novia",
]
_LAST = [
    "Santoso", "Wijaya", "Pratama", "Hidayat", "Susanto", "Hartono",
    "Setiawan", "Nugraha", "Permana", "Saputra", "Suryadi", "Gunawan",
    "Wibowo", "Cahyadi", "Firmansyah", "Rahayu", "Purnama", "Kusuma",
    "Handoko", "Budiman", "Suryana", "Mulyadi", "Halim", "Adiputra",
    "Darmawan", "Fauzi", "Iskandar", "Mariadi", "Sugiarto", "Tanjung",
]


def load_params():
    with open(PARAMS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _unique_name(pool_a, pool_b, used, rng, sep=" "):
    while True:
        name = f"{rng.choice(pool_a)}{sep}{rng.choice(pool_b)}"
        if name not in used:
            used.add(name)
            return name


# ── Master generators ──────────────────────────────────────────

def gen_cabang(params, rng):
    cab_area = params["cabang_area"]
    cab_rev = params["cab_rev_share"]
    cab_kelas = params.get("cab_kelas", {})
    records = []
    for i, (cab, area) in enumerate(cab_area.items()):
        records.append({
            "Cabang": cab,
            "Kode_Area": area,
            "Code_Cabang": f"{i + 1:03d}",
            "Kelas_Cabang": cab_kelas.get(cab, rng.choice(["A", "B", "C", "D", "E"])),
            "_rev_share": cab_rev.get(cab, 0.02),
        })
    return pd.DataFrame(records)


def gen_customers(params, cabang_df, rng, scale=0.6):
    cust_per_cab = params["cust_per_cab"]
    jenis_opts = list(params["jenis_dist"].keys())
    jenis_p = np.array(list(params["jenis_dist"].values()))
    jenis_p /= jenis_p.sum()
    kelas_opts = list(params["kelas_dist"].keys())
    kelas_p = np.array(list(params["kelas_dist"].values()))
    kelas_p /= kelas_p.sum()

    used, records, cid = set(), [], 1000
    for _, cab_row in cabang_df.iterrows():
        cab = cab_row["Cabang"]
        n = max(5, int(cust_per_cab.get(cab, 15) * scale))
        for _ in range(n):
            cid += 1
            name = _unique_name(_NAME1, _NAME2, used, rng)
            name = f"{rng.choice(_PREFIX)} {name}"
            status = rng.choice(["AKTIF", "AKTIF", "AKTIF", "AKTIF", "TIDAK AKTIF"])
            records.append({
                "Kode_Customer": f"C{cid}",
                "Nama_Customer": name.upper(),
                "Jenis_Customer": rng.choice(jenis_opts, p=jenis_p),
                "Kelas_Customer": rng.choice(kelas_opts, p=kelas_p),
                "Cabang": cab,
                "Kode_Area": cab_row["Kode_Area"],
                "Status": status,
            })
    return pd.DataFrame(records)


def gen_salesman(cabang_df, rng):
    used, records, sid = set(), [], 100
    for _, cab_row in cabang_df.iterrows():
        cab = cab_row["Cabang"]
        code_cab = cab_row["Code_Cabang"]
        n = rng.integers(3, 7)
        for j in range(n):
            sid += 1
            name = _unique_name(_FIRST, _LAST, used, rng)
            records.append({
                "Salesman_Code": f"{code_cab}-S{j + 1}",
                "Salesman_Name": name,
                "Cabang": cab,
            })
    return pd.DataFrame(records)


def gen_partnumbers(params, rng, n_total=8000):
    mg_share = params["mg_pno_share"]
    mg_list = [mg for mg in MATGROUPS if mg in mg_share]
    mg_p = np.array([mg_share.get(mg, 0.05) for mg in mg_list])
    mg_p /= mg_p.sum()
    counts = rng.multinomial(n_total, mg_p)

    records, used = [], set()
    for mg, cnt in zip(mg_list, counts):
        for _ in range(cnt):
            while True:
                pno = (f"{rng.integers(10, 99)}"
                       f"{rng.choice(list('ABCDEFGHJKLMNPQRSTUVWXYZ'))}"
                       f"{rng.integers(100, 999)}"
                       f"{rng.choice(list('ABCDEFGHJKLMNPQRSTUVWXYZ'))}"
                       f"{rng.integers(100, 999)}")
                if pno not in used:
                    used.add(pno)
                    break
            records.append({"Partnumber": pno, "Mat_Group": mg})
    return pd.DataFrame(records)


# ── Transaction generators ─────────────────────────────────────

def gen_supply(params, cabang_df, customers_df, salesman_df, parts_df, rng):
    """Generate supply (invoice) rows. Returns internal DF with extra columns
    for target/order generation; only RAW_SUPPLY_COLS are written to CSV."""
    years = params["years"]
    seasonal = params["seasonal"]
    mg_rev = params["mg_rev_share"]
    price_mg = params["price_mg"]
    qty_mg = params["qty_mg"]
    discount_mg = params["discount_mg"]  # percentages (e.g. 24.02)
    mg_diversity = params["mg_diversity"]

    div_keys = sorted(int(k) for k in mg_diversity.keys())
    div_p = np.array([mg_diversity[str(k)] for k in div_keys])
    div_p /= div_p.sum()

    mg_list = [mg for mg in MATGROUPS if mg in mg_rev]
    mg_w = np.array([mg_rev.get(mg, 0.05) for mg in mg_list])
    mg_w /= mg_w.sum()

    # Pre-assign customer → matgroup set
    cust_mg = {}
    for _, c in customers_df.iterrows():
        n = rng.choice(div_keys, p=div_p)
        n = min(n, len(mg_list))
        chosen = list(rng.choice(mg_list, size=n, replace=False, p=mg_w))
        if "TGP" not in chosen and n >= 2:
            chosen[0] = "TGP"
        cust_mg[c["Kode_Customer"]] = chosen

    # Salesman lookup by cabang
    sal_by_cab = salesman_df.groupby("Cabang").apply(
        lambda g: g[["Salesman_Code", "Salesman_Name"]].values.tolist()
    ).to_dict()

    # Customer revenue scale (log-normal)
    log_m, log_s = params["cust_rev_logmean"], params["cust_rev_logstd"]
    cust_rev = {c: np.exp(rng.normal(log_m, log_s)) * 0.4
                for c in customers_df["Kode_Customer"]}

    parts_by_mg = parts_df.groupby("Mat_Group")["Partnumber"].apply(list).to_dict()
    cust_lookup = customers_df.set_index("Kode_Customer").to_dict("index")
    cab_lookup = cabang_df.set_index("Cabang").to_dict("index")

    rows = []
    inv = 10000

    for year in years:
        growth = 1.0
        for y in years:
            if years[0] < y <= year:
                growth *= (1 + params["yoy_growth"].get(str(y), 0.05))
        max_m = 7 if year == max(years) else 12

        for month in range(1, max_m + 1):
            seas = seasonal.get(str(month), 1.0)
            date_day_pool = list(range(1, 29))

            for _, cust in customers_df.iterrows():
                cno = cust["Kode_Customer"]
                cab = cust["Cabang"]
                if rng.random() > 0.6:
                    continue

                mgs = cust_mg.get(cno, ["TGP"])
                sals = sal_by_cab.get(cab, [["SL0001", "Unknown"]])
                sal = sals[rng.integers(0, len(sals))]
                cinfo = cust_lookup.get(cno, {})
                n_lines = max(1, int(rng.exponential(3) + 1))

                for _ in range(n_lines):
                    mg = rng.choice(mgs)
                    pno = rng.choice(parts_by_mg.get(mg, ["99X999X999"]))

                    pm = price_mg.get(mg, {"mean": 50000, "std": 30000})
                    price = max(1000, rng.normal(pm["mean"], pm["std"] * 0.5))
                    price = round(price / 100) * 100

                    qm = qty_mg.get(mg, {"mean": 5, "std": 3})
                    qty = max(1, int(rng.exponential(qm["mean"] * 0.5) + 1))

                    # Discount as percentage (24.02 means 24.02%)
                    disc_pct = discount_mg.get(mg, 24.0)
                    disc_pct = max(0, min(50, rng.normal(disc_pct, 1.5)))

                    inv += 1
                    day = int(rng.choice(date_day_pool))

                    rows.append({
                        "Invoice_No": f"INV{year % 100:02d}{month:02d}{inv:06d}",
                        "SO_No": f"SO{year % 100:02d}{month:02d}{inv:06d}",
                        "Invoice_Date": f"{day:02d}/{month:02d}/{year}",
                        "Customer_No": cno,
                        "Customer_Name": cinfo.get("Nama_Customer", ""),
                        "Salesman_Code": sal[0],
                        "Salesman_Name": sal[1],
                        "Partnumber": pno,
                        "Qty": qty,
                        "Retail_Price": price,
                        "Discount": round(disc_pct, 2),
                        "SO_Type": "3",
                        # internal columns for gen_order / gen_targets
                        "_Cabang": cab,
                        "_Year": year,
                        "_Month": month,
                    })

    return pd.DataFrame(rows)


def gen_order(supply_df, params, rng):
    """Generate order data from supply with fill-rate variance.
    Only RAW_ORDER_COLS are written to CSV."""
    fill_rates = params.get("fill_rate", {})
    rows = []
    so_ctr = 50000

    for (year, month), grp in supply_df.groupby(["_Year", "_Month"]):
        fr = fill_rates.get(str(int(year)), 0.85)

        # Fulfilled orders = every supply row
        for _, r in grp.iterrows():
            so_ctr += 1
            rows.append({
                "SO_No": r["SO_No"],
                "SO_No_TPOS": f"TPOS{so_ctr:08d}",
                "SO_Date": r["Invoice_Date"],
                "Customer_No": r["Customer_No"],
                "Customer_Name": r["Customer_Name"],
                "SO_Type": r["SO_Type"],
                "Salesman_Code": r["Salesman_Code"],
                "Salesman_Name": r["Salesman_Name"],
                "Partnumber": r["Partnumber"],
                "Qty": r["Qty"],
                "Retail_Price": r["Retail_Price"],
                "Scp_Disc": int(rng.integers(0, 6)),
                "Campaign_Code": "",
                "_Year": year,
                "_Month": month,
            })

        # Unfulfilled orders
        n_extra = int(len(grp) * (1 / fr - 1))
        if n_extra > 0:
            sample = grp.sample(n=min(n_extra, len(grp)), replace=True,
                                random_state=int(rng.integers(1e6)))
            for _, r in sample.iterrows():
                so_ctr += 1
                qty = max(1, int(r["Qty"] * rng.uniform(0.5, 2.0)))
                rows.append({
                    "SO_No": f"SO{int(year) % 100:02d}{int(month):02d}{so_ctr:06d}",
                    "SO_No_TPOS": f"TPOS{so_ctr:08d}",
                    "SO_Date": r["Invoice_Date"],
                    "Customer_No": r["Customer_No"],
                    "Customer_Name": r["Customer_Name"],
                    "SO_Type": r["SO_Type"],
                    "Salesman_Code": r["Salesman_Code"],
                    "Salesman_Name": r["Salesman_Name"],
                    "Partnumber": r["Partnumber"],
                    "Qty": qty,
                    "Retail_Price": r["Retail_Price"],
                    "Scp_Disc": int(rng.integers(0, 6)),
                    "Campaign_Code": "",
                    "_Year": year,
                    "_Month": month,
                })

    return pd.DataFrame(rows)


def gen_targets(params, cabang_df, supply_df):
    """Generate Tgt_Cabang.xlsx — target per cabang per month, reverse-engineered
    from actual supply so achievement rates match real distributions."""
    years = params["years"]
    ach_mean = params.get("ach_mean", 1.05)
    ach_std = params.get("ach_std", 0.1)
    rng = np.random.default_rng(99)

    # Compute actual per cabang-month from supply
    supply_df = supply_df.copy()
    supply_df["_Actual"] = supply_df["Qty"] * supply_df["Retail_Price"] / 1.11

    actuals = supply_df.groupby(["_Cabang", "_Year", "_Month"])["_Actual"].sum()

    records = []
    for year in years:
        max_m = 7 if year == max(years) else 12
        for month in range(1, max_m + 1):
            for _, cab_row in cabang_df.iterrows():
                cab = cab_row["Cabang"]
                actual = actuals.get((cab, year, month), 0)
                ach = max(0.5, rng.normal(ach_mean, ach_std))
                target = round(actual / ach) if actual > 0 else 0
                records.append({
                    "Tahun": year,
                    "Bulan_Num": month,
                    "Bulan": BULAN_MAP[month],
                    "Code_Cabang": cab_row["Code_Cabang"],
                    "Cabang": cab,
                    "Target": target,
                })
    return pd.DataFrame(records)


def gen_kalkerja(params):
    records = []
    for year in params["years"]:
        max_m = 7 if year == max(params["years"]) else 12
        for month in range(1, max_m + 1):
            base = 22
            if month == 1: base = 20
            elif month == 4: base = 19
            elif month == 5: base = 20
            elif month == 12: base = 20
            records.append({
                "Tahun": year, "Bulan": BULAN_MAP[month],
                "Bulan_Num": month, "Hari_Kerja": base,
            })
    return pd.DataFrame(records)


def gen_pno_lookups(parts_df, rng):
    lookups = {}
    tmo_jenis = ["MINERAL", "SEMI SYNTHETIC", "FULL SYNTHETIC"]
    tmo_liters = [1.0, 4.0, 5.0, 6.0, 1.0, 4.0, 4.0]
    topt_steps = ["STEP 1", "STEP 2", "STEP 3"]
    topt_kategori = ["Performance", "Comfort", "Safety", "Exterior"]
    chem_kategori = ["Glass Cleaner", "Engine Flush", "Coolant", "Lubricant"]
    tgb_kategori = ["NS40", "NS60", "NS70", "55D23L", "80D26L"]

    # TMO: Partnumber, Partname, Liter, Jenis
    sub = parts_df[parts_df["Mat_Group"] == "TMO"][["Partnumber"]].copy()
    if not sub.empty:
        sub["Partname"] = [f"TMO-{rng.choice(tmo_jenis)[:3]}-{rng.integers(1,99):02d}L" for _ in range(len(sub))]
        sub["Liter"] = rng.choice(tmo_liters, size=len(sub))
        sub["Jenis"] = rng.choice(tmo_jenis, size=len(sub))
        lookups["PnoTMO"] = sub

    # T-OPT: Partnumber, Partname, Step, Kategori
    sub = parts_df[parts_df["Mat_Group"] == "T-OPT"][["Partnumber"]].copy()
    if not sub.empty:
        sub["Partname"] = [f"TOPT-{rng.integers(100,999)}" for _ in range(len(sub))]
        sub["Step"] = rng.choice(topt_steps, size=len(sub))
        sub["Kategori"] = rng.choice(topt_kategori, size=len(sub))
        lookups["PnoTOPT"] = sub

    # Chemical: Partnumber, Kategori
    sub = parts_df[parts_df["Mat_Group"] == "CHEMICAL"][["Partnumber"]].copy()
    if not sub.empty:
        sub["Kategori"] = rng.choice(chem_kategori, size=len(sub))
        lookups["PnoChem"] = sub

    # TGB: Partnumber, Kategori
    sub = parts_df[parts_df["Mat_Group"] == "TGB"][["Partnumber"]].copy()
    if not sub.empty:
        sub["Kategori"] = rng.choice(tgb_kategori, size=len(sub))
        lookups["PnoTGB"] = sub

    # 7KP
    grup_names = ["Engine Oil", "Brake Parts", "Filter", "Electrical",
                  "Suspension", "Body Parts", "Accessories"]
    kp_parts = []
    for mg in ["TGP", "TMO", "CHEMICAL", "BUSI", "AC", "TGB", "T-OPT"]:
        sub = parts_df[parts_df["Mat_Group"] == mg]
        if not sub.empty:
            s = sub.sample(n=min(50, len(sub)), random_state=int(rng.integers(1e6))).copy()
            s["Grup_Part_7KP"] = rng.choice(grup_names, size=len(s))
            kp_parts.append(s[["Partnumber", "Grup_Part_7KP"]])
    if kp_parts:
        lookups["Pno7KP"] = pd.concat(kp_parts, ignore_index=True)

    # 7KP Prefix
    pfx_data = []
    for mg in ["TGP", "TMO"]:
        sub = parts_df[parts_df["Mat_Group"] == mg]
        if not sub.empty:
            for pfx in sub["Partnumber"].str[:5].unique()[:10]:
                pfx_data.append({"Prefix": pfx, "Grup_Part_7KP": rng.choice(grup_names)})
    if pfx_data:
        lookups["Pno7KP_Prefix"] = pd.DataFrame(pfx_data)

    # DProg — needs StartDate, EndDate
    dprog_parts = []
    for mg in ["TGP", "AVANZA", "TMO"]:
        sub = parts_df[parts_df["Mat_Group"] == mg]
        if not sub.empty:
            s = sub.sample(n=min(80, len(sub)), random_state=int(rng.integers(1e6)))
            dprog_parts.append(s[["Partnumber"]].copy())
    if dprog_parts:
        dprog = pd.concat(dprog_parts, ignore_index=True)
        dprog["StartDate"] = "2024-01-01"
        dprog["EndDate"] = "2026-12-31"
        lookups["PnoDProg"] = dprog

    return lookups


# ── Main ────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate synthetic data")
    parser.add_argument("--out", default="TASTI_SYNTHETIC",
                        help="Output folder (default: TASTI_SYNTHETIC)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--scale", type=float, default=0.6,
                        help="Customer scale factor vs real data (default: 0.6)")
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "Order").mkdir(exist_ok=True)
    (out / "Supply").mkdir(exist_ok=True)

    rng = np.random.default_rng(args.seed)
    print(f"Loading parameters from {PARAMS_FILE}")
    params = load_params()

    # ── Masters ──
    print("Generating masters...")
    cabang_df = gen_cabang(params, rng)
    print(f"  {len(cabang_df)} cabang")

    customers_df = gen_customers(params, cabang_df, rng, scale=args.scale)
    print(f"  {len(customers_df)} customers")

    salesman_df = gen_salesman(cabang_df, rng)
    print(f"  {len(salesman_df)} salesman")

    parts_df = gen_partnumbers(params, rng, n_total=8000)
    print(f"  {len(parts_df)} partnumbers")

    # ── Transactions ──
    print("Generating supply (invoice) data... (takes ~1 min)")
    supply_df = gen_supply(params, cabang_df, customers_df, salesman_df, parts_df, rng)
    print(f"  {len(supply_df):,} supply rows")

    print("Generating order data from supply...")
    order_df = gen_order(supply_df, params, rng)
    print(f"  {len(order_df):,} order rows")

    print("Generating targets...")
    target_df = gen_targets(params, cabang_df, supply_df)
    print(f"  {len(target_df):,} target rows")

    # ── Save CSVs (raw columns only) ──
    print("\nSaving files...")

    # Supply CSVs by semester
    for year in params["years"]:
        for sem, months in [(1, range(1, 7)), (2, range(7, 13))]:
            mask = (supply_df["_Year"] == year) & (supply_df["_Month"].isin(months))
            chunk = supply_df.loc[mask, RAW_SUPPLY_COLS]
            if chunk.empty:
                continue
            path = out / "Supply" / f"S{year % 100:02d}S{sem}.csv"
            chunk.to_csv(path, index=False)
            print(f"  {path.name}: {len(chunk):,} rows")

    # Order CSVs by semester (only years >= 2024)
    for year in params["years"]:
        if year < 2024:
            continue
        for sem, months in [(1, range(1, 7)), (2, range(7, 13))]:
            mask = (order_df["_Year"] == year) & (order_df["_Month"].isin(months))
            chunk = order_df.loc[mask, RAW_ORDER_COLS]
            if chunk.empty:
                continue
            path = out / "Order" / f"O{year % 100:02d}S{sem}.csv"
            chunk.to_csv(path, index=False)
            print(f"  {path.name}: {len(chunk):,} rows")

    # Customer.xlsx (column names match what data_loader expects)
    customers_df.to_excel(out / "Customer.xlsx", index=False)
    print(f"  Customer.xlsx: {len(customers_df)} rows")

    # Tgt_Cabang.xlsx
    target_df.to_excel(out / "Tgt_Cabang.xlsx", index=False)
    print(f"  Tgt_Cabang.xlsx: {len(target_df)} rows")

    # Kal_Kerja.xlsx
    kalkerja = gen_kalkerja(params)
    kalkerja.to_excel(out / "Kal_Kerja.xlsx", index=False)
    print(f"  Kal_Kerja.xlsx: {len(kalkerja)} rows")

    # part_master.xlsx (lowercase column names — matches data_loader)
    pm = parts_df.copy()
    pm_out = pd.DataFrame({
        "part_number": pm["Partnumber"],
        "part_number_substitusi": "",
        "mat_group": pm["Mat_Group"],
    })
    # Add some substitution pairs (~5% of parts)
    n_sub = len(pm_out) // 20
    sub_idx = rng.choice(len(pm_out), size=n_sub, replace=False)
    target_idx = rng.choice(len(pm_out), size=n_sub, replace=True)
    pm_out.iloc[sub_idx, pm_out.columns.get_loc("part_number_substitusi")] = \
        pm_out.iloc[target_idx]["part_number"].values
    pm_out.to_excel(out / "part_master.xlsx", index=False)
    print(f"  part_master.xlsx: {len(pm_out)} rows")

    # Kelas_Cabang.xlsx (column "Kelas" not "Kelas_Cabang" — matches real file)
    kc = cabang_df[["Cabang", "Kelas_Cabang"]].rename(columns={"Kelas_Cabang": "Kelas"})
    kc.to_excel(out / "Kelas_Cabang.xlsx", index=False)
    print(f"  Kelas_Cabang.xlsx: {len(kc)} rows")

    # Pno*.xlsx lookups
    lookups = gen_pno_lookups(parts_df, rng)
    for fname, df in lookups.items():
        df.to_excel(out / f"{fname}.xlsx", index=False)
        print(f"  {fname}.xlsx: {len(df)} rows")

    total_size = sum(f.stat().st_size for f in out.rglob("*") if f.is_file())
    print(f"\nDone! Total: {total_size / 1024 / 1024:.1f} MB in {out.resolve()}")


if __name__ == "__main__":
    main()
