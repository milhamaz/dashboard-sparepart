# ============================================================
# 🎯 TARGET ENGINE — Cascade Target Cabang → Customer → Salesman
# ============================================================
"""
Target cuma ada di layer Cabang (Tgt_Cabang.xlsx). Modul ini mecah target itu ke
Customer_No, lalu ke Salesman_Code, berbasis ORDER (bukan Actual/Supply — Supply itu
eksekusi logistik pihak ketiga, kurang murni cerminan performa sales/customer).

Cascade-nya SATU ARAH: Cabang -> Customer -> Salesman (bukan 2 pemecahan independen),
supaya sum(Target Customer) == Target Cabang == sum(Target Salesman) terjamin by
construction, bukan kebetulan.

Target Customer per bulan dipecah proporsional dari share Order customer itu dalam
window TRAILING 12 bulan sebelum bulan target (bukan kalender tahun lalu yang fixed) —
di-recompute tiap bulan, supaya customer/salesman baru & yang berhenti otomatis
ke-update tanpa override manual:
  - Customer lama (ada histori di window trailing) -> proporsional dari situ.
  - Customer baru (0 histori trailing, tapi transaksi di bulan target) -> floor
    berjenjang per Kelas Cabang (KELAS_FLOOR_BARU), supaya gak dapat Target 0.
    Floor ini di-CARVE OUT dari Target Cabang bulan itu (bukan ditambah di luar),
    jadi total tetap pas sama Target Cabang meski ada customer baru.

Target Salesman BUKAN dihitung independen dari proporsi historis nama Salesman
(itu bakal salah pas ada resign/pindah/staff baru) — tapi dijumlah dari Target
Customer yang SAAT INI (transaksi Order paling baru, dibatasi sampai akhir periode
target — no leakage ke masa depan) tercatat di bawah Salesman_Code itu. Jadi kalau
customer di-oper ke Salesman lain, Target-nya otomatis ikut pindah di bulan
berikutnya, tanpa perlu deteksi "Salesman resign" secara eksplisit.
"""
import streamlit as st
import pandas as pd

# Floor Target Customer baru (bulan pertama, 0 histori trailing) — berjenjang per Kelas
# Cabang, cabang lebih besar wajar dikasih ekspektasi awal lebih tinggi. Angka kecil &
# seragam di ujung bawah (bukan lompatan besar kayak versi awal 500jt/A) sengaja dipilih
# supaya salah taksir 1 bulan pertama gak bikin over-target customer kecil yang legitimately
# onboarding di cabang besar (mis. customer kecil baru di Jakarta).
KELAS_FLOOR_BARU = {"E": 30_000_000, "D": 35_000_000, "C": 40_000_000, "B": 45_000_000, "A": 50_000_000}

# Jakarta & Medan sengaja tidak ada di Kelas_Cabang.xlsx (mereka punya rule margin sendiri
# di luar sistem Kelas A-E, lihat CABANG_MARGIN_RANGE di data_loader.py) — disamakan Kelas A
# di sini karena keduanya cabang besar.
CABANG_KELAS_OVERRIDE = {"JAKARTA": "A", "MEDAN": "A"}


def get_cabang_kelas_map(df_kelas_cabang):
    mapping = dict(zip(df_kelas_cabang["Cabang"], df_kelas_cabang["Kelas"]))
    mapping.update(CABANG_KELAS_OVERRIDE)
    return mapping


def _month_key(tahun, bulan_num):
    return tahun * 12 + bulan_num


def compute_customer_target_month(df_order_raw, df_target, kelas_map, target_tahun, target_bulan_num):
    """Target per Customer_No untuk SATU bulan spesifik. `df_order_raw` harus data Order
    MENTAH (semua tahun yang ke-load, tidak dipotong Filter General) — window trailing
    perlu menengok jauh ke belakang terlepas dari Bulan/Cabang yang lagi difilter user.
    """
    order_key = df_order_raw["Tahun"] * 12 + df_order_raw["Bulan_Num"]
    cutoff = _month_key(target_tahun, target_bulan_num)
    win_start, win_end = cutoff - 12, cutoff - 1

    trailing = df_order_raw[(order_key >= win_start) & (order_key <= win_end)]
    this_month = df_order_raw[order_key == cutoff]

    trailing_by_cust = trailing.groupby(["Cabang", "Customer_No"])["Order"].sum()
    this_month_by_cust = this_month.groupby(["Cabang", "Customer_No"])["Order"].sum()

    target_scope = df_target[(df_target["Tahun"] == target_tahun) & (df_target["Bulan_Num"] == target_bulan_num)]

    rows = []
    cabang_list = sorted(set(trailing["Cabang"].dropna().unique()) | set(this_month["Cabang"].dropna().unique()))
    for cabang in cabang_list:
        tgt_row = target_scope[target_scope["Cabang"] == cabang]
        if tgt_row.empty:
            continue
        cabang_target = tgt_row["Target"].sum()

        trailing_cab = trailing_by_cust.xs(cabang, level=0) if cabang in trailing_by_cust.index.get_level_values(0) else pd.Series(dtype=float)
        this_month_cab = this_month_by_cust.xs(cabang, level=0) if cabang in this_month_by_cust.index.get_level_values(0) else pd.Series(dtype=float)

        old_customers = trailing_cab[trailing_cab > 0]
        new_customers = [c for c in this_month_cab.index if c not in old_customers.index]

        if old_customers.empty and not this_month_cab.empty:
            # Bootstrap: cabang ini nol histori trailing SAMA SEKALI (mis. bulan pertama
            # data Order ke-load, window trailing-nya nengok ke sebelum data ada) — gak ada
            # basis historis apa pun, jadi split habis Target Cabang berdasar proporsi Order
            # BULAN INI sendiri (bukan floor — kalau tetap pakai floor, sisa `remaining_pool`
            # gak kebagian ke siapa2 karena old_customers kosong, targetnya jadi "hilang").
            total_this = this_month_cab.sum()
            for c, v in this_month_cab.items():
                share = (v / total_this) if total_this > 0 else (1 / len(this_month_cab))
                rows.append({"Cabang": cabang, "Customer_No": c, "Target_Customer": share * cabang_target, "Tipe": "Bootstrap"})
            continue

        kelas = kelas_map.get(cabang, "E")
        floor_val = KELAS_FLOOR_BARU[kelas]
        reserved_new = floor_val * len(new_customers)

        if reserved_new > cabang_target and reserved_new > 0:
            # Kalau customer baru bulan ini kebanyakan sampai floor gabungannya lebih besar
            # dari Target Cabang itu sendiri, skala turun floor-nya biar tetap pas (gak
            # boleh sampai total Target Customer > Target Cabang).
            scale = cabang_target / reserved_new
            new_target = floor_val * scale
            remaining_pool = 0.0
        else:
            new_target = floor_val
            remaining_pool = cabang_target - reserved_new

        total_old = old_customers.sum()
        for c, v in old_customers.items():
            share = (v / total_old) if total_old > 0 else 0
            rows.append({"Cabang": cabang, "Customer_No": c, "Target_Customer": share * remaining_pool, "Tipe": "Existing"})
        for c in new_customers:
            rows.append({"Cabang": cabang, "Customer_No": c, "Target_Customer": new_target, "Tipe": "Baru"})

    return pd.DataFrame(rows, columns=["Cabang", "Customer_No", "Target_Customer", "Tipe"])


@st.cache_data(show_spinner=False)
def compute_customer_target(df_order_raw, df_target, df_kelas_cabang, pilih_tahun, bulan_num_list):
    """Target per Customer_No, dijumlah untuk semua bulan di `bulan_num_list` pada
    `pilih_tahun` — tiap bulan pakai window trailing-nya sendiri2 (rolling), lalu
    hasilnya di-total supaya konsisten dengan cara Filter General nge-scope banyak
    Bulan sekaligus di tab lain (mis. Cabang Scorecard nge-sum Target Cabang per Bulan
    yang dipilih).

    @st.cache_data di sini penting: loop 12 bulan x beberapa groupby per bulan ini gak
    murah, dan tanpa cache bakal re-run dari nol tiap widget lain di-interaksi (Streamlit
    re-run seluruh script tiap rerun, termasuk body semua tab lain di halaman yang sama).
    """
    cols = ["Cabang", "Customer_No", "Target_Customer", "Tipe"]
    if df_order_raw is None or df_order_raw.empty or not bulan_num_list:
        return pd.DataFrame(columns=cols)

    kelas_map = get_cabang_kelas_map(df_kelas_cabang)
    frames = [
        compute_customer_target_month(df_order_raw, df_target, kelas_map, pilih_tahun, m)
        for m in bulan_num_list
    ]
    frames = [f for f in frames if not f.empty]
    if not frames:
        return pd.DataFrame(columns=cols)

    combined = pd.concat(frames, ignore_index=True)
    agg = combined.groupby(["Cabang", "Customer_No"], as_index=False).agg(
        Target_Customer=("Target_Customer", "sum"),
        Tipe=("Tipe", "last"),
    )
    return agg[cols]


def compute_current_salesman(df_order_raw, pilih_tahun, bulan_num_list):
    """Salesman_Code 'pemegang' tiap Customer_No SAAT INI — diambil dari transaksi Order
    PALING BARU yang gak melewati akhir periode target (no leakage ke bulan setelahnya),
    supaya Target Salesman bulan lalu gak berubah gara-gara reassignment yang baru
    kejadian belakangan.
    """
    cols = ["Customer_No", "Salesman_Code", "Salesman_Name"]
    if df_order_raw is None or df_order_raw.empty or not bulan_num_list:
        return pd.DataFrame(columns=cols)

    cutoff = _month_key(pilih_tahun, max(bulan_num_list))
    order_key = df_order_raw["Tahun"] * 12 + df_order_raw["Bulan_Num"]
    hist = df_order_raw[order_key <= cutoff].sort_values("SO_Date")
    latest = hist.groupby("Customer_No").last().reset_index()
    latest["Salesman_Name"] = latest["Salesman_Name"].astype(str).str.strip().str.upper()
    return latest[cols]


def compute_salesman_order(df_order_raw, pilih_tahun, bulan_num_list, current_salesman=None):
    """Order aktual per Salesman_Code untuk periode `bulan_num_list`, diatribusikan
    berdasar siapa yang SEKARANG pegang tiap Customer (compute_current_salesman) — BUKAN
    siapa yang literally memproses tiap transaksi historis. Ini penting: kalau Customer_No
    dioper dari Salesman A ke B di tengah periode (mis. kasus Rangga di Jakarta), seluruh
    Order customer itu sepanjang periode ini harus ikut ke B (pemegang sekarang), sama
    dengan cara Target Salesman dihitung — supaya Order vs Target apple-to-apple. Kalau
    Order tetap diatribusikan ke siapa yang memproses tiap transaksi (attribusi historis),
    Salesman lama bakal keliatan overachieve semu (masih bawa Order customer yang udah
    dioper), sementara Salesman baru underachieve semu (Target-nya udah ikut customer itu,
    tapi Order historisnya ketinggalan di Salesman lama).

    `current_salesman` opsional — kalau pemanggil sudah punya hasil compute_current_salesman()
    (mis. karena juga dipakai buat compute_salesman_target di render yang sama), oper di sini
    supaya gak dihitung ulang dari nol (groupby+sort atas seluruh histori Order itu lumayan
    berat kalau dipanggil 2x per render).
    """
    cols = ["Salesman_Code", "Order"]
    if df_order_raw is None or df_order_raw.empty or not bulan_num_list:
        return pd.DataFrame(columns=cols)

    scope = df_order_raw[(df_order_raw["Tahun"] == pilih_tahun) & (df_order_raw["Bulan_Num"].isin(bulan_num_list))]
    order_by_cust = scope.groupby("Customer_No")["Order"].sum().rename("Order").reset_index()

    if current_salesman is None:
        current_salesman = compute_current_salesman(df_order_raw, pilih_tahun, bulan_num_list)
    merged = current_salesman.merge(order_by_cust, on="Customer_No", how="left")
    merged["Order"] = merged["Order"].fillna(0)

    result = merged.groupby("Salesman_Code", as_index=False)["Order"].sum()
    return result[cols]


def compute_salesman_target(df_customer_target, df_order_raw, pilih_tahun, bulan_num_list, current_salesman=None):
    """Target per Salesman_Code = agregasi Target_Customer berdasar Salesman_Code yang
    SEKARANG pegang tiap Customer_No (compute_current_salesman) — bukan proporsi historis
    nama Salesman sendiri, supaya otomatis ngikut begitu ada customer yang di-oper
    (Salesman resign/pindah cabang/staff baru masuk pegang customer eksisting).

    `current_salesman` opsional — lihat docstring compute_salesman_order() soal alasannya.
    """
    cols = ["Salesman_Code", "Salesman_Name", "Cabang", "Target_Salesman"]
    if df_customer_target is None or df_customer_target.empty:
        return pd.DataFrame(columns=cols)

    if current_salesman is None:
        current_salesman = compute_current_salesman(df_order_raw, pilih_tahun, bulan_num_list)
    merged = df_customer_target.merge(current_salesman, on="Customer_No", how="left")

    # Total Target per Salesman TANPA ikut di-split per Cabang di kunci groupby — sebagian
    # kecil Salesman ada yang pegang 1-2 customer yang somehow ke-register di Cabang lain
    # (data quirk, sama seperti kasus serupa di tab_salesman_leaderboard.py). Kalau Cabang
    # ikut jadi kunci groupby, itu bakal mecah 1 Salesman jadi >1 baris dan sebagian besar
    # Target-nya "nyasar" ke baris terpisah, padahal Order actual (dihitung independen di
    # pemanggil, gak peduli Cabang) tetap dijumlah utuh — bikin %O/T meledak gak masuk akal.
    result = merged.groupby(["Salesman_Code", "Salesman_Name"], as_index=False, dropna=False).agg(
        Target_Salesman=("Target_Customer", "sum"),
    )

    # Cabang cuma buat filter/tampilan — diambil dari Cabang dengan Target_Customer terbesar
    # (dominan) per Salesman, bukan bagian dari kunci penjumlahan di atas.
    dominant_cabang = (
        merged.groupby(["Salesman_Code", "Cabang"])["Target_Customer"].sum()
        .reset_index().sort_values("Target_Customer", ascending=False)
        .drop_duplicates("Salesman_Code").set_index("Salesman_Code")["Cabang"]
    )
    result["Cabang"] = result["Salesman_Code"].map(dominant_cabang)
    return result[cols]
