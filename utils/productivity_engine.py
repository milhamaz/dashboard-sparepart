# ============================================================
# 📈 PRODUCTIVITY ENGINE — Assigned Customer -> Order/Actual per Cabang/Salesman
# ============================================================
"""
Dipakai bareng oleh tab Productivity dan tab Segmentasi (archetype) di halaman SDM —
satu fungsi assembly supaya logic "siapa pegang customer siapa" (current_salesman,
dominant_cabang, Top-1 Concentration base) gak double-maintained di dua tempat dan
gampang drift kalau salah satu diubah tanpa yang lain ikut.
"""
import pandas as pd

from utils.target_engine import compute_current_salesman, compute_salesman_order, compute_salesman_actual


def compute_productivity_df(df_order_raw, df_order_final, df_supply_final, df_customer_master,
                             pilih_tahun, bulan_num_list, pilih_jenis, pilih_kelas, pilih_area,
                             pilih_cabang, subject):
    """Return (df, label_col, name_col). df kosong kalau gak ada data untuk filter yang dipilih
    (caller yang tampilkan st.info — fungsi ini murni pandas, tanpa side-effect Streamlit).

    Kolom di df:
    - Assigned_Customers: total customer AKTIF (dalam scope Jenis/Kelas/Area) yang di-assign
      ke subjek ini — BUKAN cuma yang aktif transaksi periode ini, supaya subjek yang
      "nelantarin" sebagian besar portofolionya gak keliatan produktif cuma karena sisa
      akunnya sedikit.
    - Order, Actual: total Order/Actual subjek ini di periode `bulan_num_list`.
    - Active_Customers, Active_Ratio: dari Assigned_Customers itu, berapa yang BENERAN
      punya Actual>0 di periode ini — dan persentasenya. Ini beda dari Assigned_Customers
      (siapa yang dipegang) — Active_Ratio ngukur seberapa besar portofolio itu yang
      nyata-nyata digarap.
    - Top1_Concentration, Top1_Customer: seberapa besar 1 customer terbesar menyumbang ke
      Actual subjek ini, dan siapa customer-nya.
    - Productivity_Order, Productivity_Actual: Order/Actual dibagi Assigned_Customers.
    - Relative_Productivity: Productivity_Actual dibanding rata-rata Cabang sendiri (Salesman)
      atau rata-rata Nasional (Cabang) — SENGAJA bukan dibagi Target/customer, karena
      (Actual/N)/(Target/N) = Actual/Target, cuma jadi Achievement% yang sudah ada di tab
      Target, bukan metrik baru.
    """
    customer_scope = df_customer_master[
        df_customer_master["Jenis_Customer"].isin(pilih_jenis)
        & df_customer_master["Kelas_Customer"].isin(pilih_kelas)
        & df_customer_master["Kode_Area"].isin(pilih_area)
    ]
    sup_scope = df_supply_final[df_supply_final["Tahun"] == pilih_tahun].copy()

    if subject == "Cabang":
        assigned = (
            customer_scope[customer_scope["Status"] == "AKTIF"]
            .groupby("Cabang")["Kode_Customer"].nunique().rename("Assigned_Customers")
        )
        order_sum = df_order_final.groupby("Cabang")["Order"].sum().rename("Order") if not df_order_final.empty else pd.Series(dtype=float, name="Order")
        actual_sum = sup_scope.groupby("Cabang")["Actual"].sum().rename("Actual")

        df = assigned.to_frame().join(order_sum, how="left").join(actual_sum, how="left").fillna(0).reset_index()
        df = df[df["Cabang"].isin(pilih_cabang) & (df["Assigned_Customers"] > 0)].copy()

        cust_actual = sup_scope.groupby(["Cabang", "Customer_No"])["Actual"].sum().reset_index()
        top1_df = cust_actual.sort_values("Actual", ascending=False).drop_duplicates("Cabang").set_index("Cabang")
        df["Top1_Actual"] = df["Cabang"].map(top1_df["Actual"]).fillna(0)
        df["Top1_Customer_No"] = df["Cabang"].map(top1_df["Customer_No"])

        active_count = cust_actual[cust_actual["Actual"] > 0].groupby("Cabang")["Customer_No"].nunique()
        df["Active_Customers"] = df["Cabang"].map(active_count).fillna(0)

        label_col, name_col = "Cabang", "Cabang"
    else:
        df_order_scope = df_order_raw[df_order_raw["Customer_No"].isin(customer_scope["Kode_Customer"])]

        current_salesman = compute_current_salesman(df_order_scope, pilih_tahun, bulan_num_list)
        if current_salesman.empty:
            return pd.DataFrame(), "Salesman_Name", "Salesman_Name"

        cust_cabang = df_customer_master.set_index("Kode_Customer")["Cabang"]
        current_salesman = current_salesman.copy()
        current_salesman["Cabang"] = current_salesman["Customer_No"].map(cust_cabang)

        assigned = current_salesman.groupby("Salesman_Code")["Customer_No"].nunique().rename("Assigned_Customers")
        order_sum = compute_salesman_order(df_order_scope, pilih_tahun, bulan_num_list, current_salesman=current_salesman).set_index("Salesman_Code")["Order"]
        # Actual TIDAK lewat current_salesman (lihat docstring compute_salesman_actual() —
        # Actual pakai Salesman_Code mentah dari Supply, bukan pemegang Order terkini).
        actual_sum = compute_salesman_actual(df_supply_final, pilih_tahun, bulan_num_list).set_index("Salesman_Code")["Actual"]

        name_map = current_salesman.drop_duplicates("Salesman_Code").set_index("Salesman_Code")["Salesman_Name"]
        # Cabang "rumah" tiap Salesman = Cabang dengan customer assigned terbanyak — sebagian
        # kecil Salesman ada yang pegang 1-2 customer nyasar di Cabang lain (data quirk yang
        # sama dicatat di tab_salesman_leaderboard.py/target_engine.py).
        dominant_cabang = (
            current_salesman.groupby(["Salesman_Code", "Cabang"]).size().reset_index(name="n")
            .sort_values("n", ascending=False).drop_duplicates("Salesman_Code")
            .set_index("Salesman_Code")["Cabang"]
        )

        df = assigned.to_frame().join(order_sum.rename("Order"), how="left").join(actual_sum.rename("Actual"), how="left").fillna(0).reset_index()
        df["Salesman_Name"] = df["Salesman_Code"].map(name_map)
        df["Cabang"] = df["Salesman_Code"].map(dominant_cabang)
        df = df[df["Cabang"].isin(pilih_cabang) & (df["Assigned_Customers"] > 0)].copy()

        # Top1/Active_Customers dihitung dari Salesman_Code MENTAH di Supply itu sendiri —
        # harus sepopulasi sama `actual_sum` di atas (juga dari Salesman_Code mentah, bukan
        # current_salesman/pemegang Order terkini), supaya Top1_Actual gak pernah lebih besar
        # dari total Actual-nya sendiri (kalau basis-nya beda, Top-1 Concentration% bisa
        # "lebih dari 100%" — data quirk yang sempat kejadian pas Top1 masih lewat
        # current_salesman sementara Actual udah di-switch).
        cust_totals = sup_scope.groupby(["Salesman_Code", "Customer_No"])["Actual"].sum().reset_index()
        top1_df = cust_totals.sort_values("Actual", ascending=False).drop_duplicates("Salesman_Code").set_index("Salesman_Code")
        df["Top1_Actual"] = df["Salesman_Code"].map(top1_df["Actual"]).fillna(0)
        df["Top1_Customer_No"] = df["Salesman_Code"].map(top1_df["Customer_No"])

        # Active_Customers SENGAJA beda basis dari Top1 di atas: di sini yang mau dijawab
        # adalah "dari customer yang di-assign ke Salesman ini SEKARANG, berapa yang beneran
        # transaksi" — jadi dicek per Customer_No di current_salesman terlepas dari Salesman_Code
        # mentah mana yang tercatat di baris Supply-nya. Kalau dipaksa pakai cust_totals
        # (Salesman_Code mentah, basis yang sama dengan Top1/actual_sum), Active_Customers bisa
        # lebih besar dari Assigned_Customers (customer yang Actual-nya masih tercatat di kode
        # lama tapi Order-nya udah dioper ke Salesman ini ikut kehitung) — bikin Active_Ratio
        # tembus >100%, gak masuk akal buat sebuah rasio.
        sup_by_customer = sup_scope.groupby("Customer_No")["Actual"].sum()
        active_customer_no = current_salesman["Customer_No"].map(sup_by_customer).fillna(0) > 0
        active_count = current_salesman[active_customer_no].groupby("Salesman_Code")["Customer_No"].nunique()
        df["Active_Customers"] = df["Salesman_Code"].map(active_count).fillna(0)

        label_col, name_col = "Salesman_Name", "Salesman_Name"

    if df.empty:
        return df, label_col, name_col

    df["Productivity_Order"] = df["Order"] / df["Assigned_Customers"]
    df["Productivity_Actual"] = df["Actual"] / df["Assigned_Customers"]
    df["Top1_Concentration"] = (df["Top1_Actual"] / df["Actual"].replace(0, pd.NA) * 100).fillna(0.0)
    df["Active_Ratio"] = df["Active_Customers"] / df["Assigned_Customers"] * 100

    # Nama customer di balik Top1_Concentration — biar hover chart gak cuma nunjukin angka
    # %-nya doang, tapi juga customer siapa yang dimaksud.
    cust_name_map = df_customer_master.set_index("Kode_Customer")["Nama_Customer"]
    def _top1_customer_label(kode):
        if pd.isna(kode):
            return "-"
        nama = cust_name_map.get(kode, "")
        return f"{kode} - {nama}" if nama else str(kode)
    df["Top1_Customer"] = df["Top1_Customer_No"].map(_top1_customer_label)

    # Relative Productivity — dibanding rata-rata Cabang sendiri (Salesman) atau rata-rata
    # Nasional (Cabang). SENGAJA bukan dibagi Target/customer: (Actual/N)/(Target/N) = Actual/Target,
    # N-nya kecoret habis dan itu cuma jadi Achievement% yang sudah ada di tab Target — bukan
    # metrik baru.
    if subject == "Cabang":
        national_avg = df["Actual"].sum() / df["Assigned_Customers"].sum() if df["Assigned_Customers"].sum() > 0 else 0.0
        df["Relative_Productivity"] = (df["Productivity_Actual"] / national_avg * 100) if national_avg > 0 else 0.0
    else:
        cabang_actual_sum = df.groupby("Cabang")["Actual"].transform("sum")
        cabang_cust_sum = df.groupby("Cabang")["Assigned_Customers"].transform("sum")
        cabang_avg_productivity = (cabang_actual_sum / cabang_cust_sum.replace(0, pd.NA)).fillna(0.0)
        df["Relative_Productivity"] = (df["Productivity_Actual"] / cabang_avg_productivity.replace(0, pd.NA) * 100).fillna(0.0)

    df = df.sort_values("Productivity_Actual", ascending=False).reset_index(drop=True)
    return df, label_col, name_col
