# ============================================================
# 📈 TAB: PRODUCTIVITY
# ============================================================
import streamlit as st
import pandas as pd

from utils.data_loader import list_bulan_standar
from utils.target_engine import compute_current_salesman, compute_salesman_order, compute_salesman_actual
from utils.components import render_card, render_topn_barh_chart, auto_table_height
from utils.styles import fmt_rp_full as FMT_RP, highlight_pct as _highlight_pct, highlight_concentration_pct as _highlight_concentration

_BULAN_NUM = {b: i + 1 for i, b in enumerate(list_bulan_standar)}

# Ambang minimum jumlah customer assigned — di bawah ini, angka Productivity gampang
# melenceng gara-gara 1-2 transaksi besar/kecil, bukan cerminan skill yang stabil.
_MIN_N_CUSTOMER = 5


def render(df_order_raw, df_order_final, df_supply_final, df_customer_master, pilih_tahun, pilih_bulan,
           pilih_jenis, pilih_kelas, pilih_area, pilih_cabang, fmt_rp):
    bulan_num_list = sorted(_BULAN_NUM[b] for b in pilih_bulan if b in _BULAN_NUM)
    if not bulan_num_list:
        st.info("Tidak ada Bulan yang dipilih di Filter General.")
        return

    subject = st.radio(
        "Lihat Productivity berdasarkan", ["Cabang", "Salesman"], horizontal=True, key="productivity_subject",
    )

    # Populasi customer sesuai Jenis/Kelas/Area di Filter General — dipakai buat menyaring
    # customer_master (denominator Assigned_Customers) SUPAYA SEPADAN dengan df_order_final/
    # df_supply_final (numerator), yang keduanya sudah kena filter dimensi ini juga.
    customer_scope = df_customer_master[
        df_customer_master["Jenis_Customer"].isin(pilih_jenis)
        & df_customer_master["Kelas_Customer"].isin(pilih_kelas)
        & df_customer_master["Kode_Area"].isin(pilih_area)
    ]

    sup_scope = df_supply_final[df_supply_final["Tahun"] == pilih_tahun].copy()

    if subject == "Cabang":
        # Resource = customer AKTIF (dalam scope Jenis/Kelas/Area) di master per Cabang —
        # bukan cuma yang aktif transaksi periode ini, biar Cabang yang "nelantarin" sebagian
        # besar portofolionya gak keliatan produktif cuma karena sisa akunnya sedikit.
        assigned = (
            customer_scope[customer_scope["Status"] == "AKTIF"]
            .groupby("Cabang")["Kode_Customer"].nunique().rename("Assigned_Customers")
        )
        order_sum = df_order_final.groupby("Cabang")["Order"].sum().rename("Order") if not df_order_final.empty else pd.Series(dtype=float, name="Order")
        actual_sum = sup_scope.groupby("Cabang")["Actual"].sum().rename("Actual")

        df = assigned.to_frame().join(order_sum, how="left").join(actual_sum, how="left").fillna(0).reset_index()
        df = df[df["Cabang"].isin(pilih_cabang) & (df["Assigned_Customers"] > 0)].copy()

        cust_actual = sup_scope.groupby(["Cabang", "Customer_No"])["Actual"].sum().reset_index()
        top1 = (
            cust_actual.sort_values("Actual", ascending=False).drop_duplicates("Cabang")
            .set_index("Cabang")["Actual"]
        )
        df["Top1_Actual"] = df["Cabang"].map(top1).fillna(0)

        label_col, name_col = "Cabang", "Cabang"
    else:
        # Order/Actual Salesman dihitung dari histori Order MENTAH (compute_current_salesman
        # butuh jangkauan Tahun lengkap), tapi tetap disaring dulu ke populasi customer yang
        # sama dengan cabang Jenis/Kelas/Area di atas — konsisten dgn pola tab_target_salesman.py.
        df_order_scope = df_order_raw[df_order_raw["Customer_No"].isin(customer_scope["Kode_Customer"])]

        current_salesman = compute_current_salesman(df_order_scope, pilih_tahun, bulan_num_list)
        if current_salesman.empty:
            st.info("Tidak ada data Salesman untuk filter yang dipilih.")
            return

        cust_cabang = df_customer_master.set_index("Kode_Customer")["Cabang"]
        current_salesman = current_salesman.copy()
        current_salesman["Cabang"] = current_salesman["Customer_No"].map(cust_cabang)

        assigned = current_salesman.groupby("Salesman_Code")["Customer_No"].nunique().rename("Assigned_Customers")
        order_sum = compute_salesman_order(df_order_scope, pilih_tahun, bulan_num_list, current_salesman=current_salesman).set_index("Salesman_Code")["Order"]
        actual_sum = compute_salesman_actual(df_supply_final, pilih_tahun, bulan_num_list, current_salesman).set_index("Salesman_Code")["Actual"]

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

        # df_supply punya kolom Salesman_Code sendiri (siapa yang proses transaksi historis),
        # tapi itu BUKAN yang dipakai buat atribusi di sini — drop dulu biar gak nabrak nama
        # kolom pas di-merge sama mapping "pemegang customer SAAT INI" dari current_salesman.
        cust_by_salesman = sup_scope.drop(columns=["Salesman_Code"], errors="ignore").merge(
            current_salesman[["Customer_No", "Salesman_Code"]], on="Customer_No", how="inner"
        )
        cust_totals = cust_by_salesman.groupby(["Salesman_Code", "Customer_No"])["Actual"].sum().reset_index()
        top1 = (
            cust_totals.sort_values("Actual", ascending=False).drop_duplicates("Salesman_Code")
            .set_index("Salesman_Code")["Actual"]
        )
        df["Top1_Actual"] = df["Salesman_Code"].map(top1).fillna(0)

        label_col, name_col = "Salesman_Name", "Salesman_Name"

    if df.empty:
        st.info("Tidak ada data untuk filter yang dipilih.")
        return

    df["Productivity_Order"] = df["Order"] / df["Assigned_Customers"]
    df["Productivity_Actual"] = df["Actual"] / df["Assigned_Customers"]
    df["Top1_Concentration"] = (df["Top1_Actual"] / df["Actual"].replace(0, pd.NA) * 100).fillna(0.0)

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

    high_risk = (df["Top1_Concentration"] >= 50).sum()
    low_n = (df["Assigned_Customers"] < _MIN_N_CUSTOMER).sum()
    avg_productivity = df["Productivity_Actual"].mean() if not df.empty else 0.0
    top_row = df.iloc[0]

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(render_card("🏆", f"{subject} Paling Produktif", top_row[label_col], f"{fmt_rp(top_row['Productivity_Actual'])}/customer"), unsafe_allow_html=True)
    with c2:
        st.markdown(render_card("", "Rata-rata Productivity", fmt_rp(avg_productivity), f"per customer, {len(df)} {subject.lower()}"), unsafe_allow_html=True)
    with c3:
        st.markdown(render_card("🚨", "Concentration Risk Tinggi", f"{high_risk}", "Top-1 customer ≥50% revenue"), unsafe_allow_html=True)
    with c4:
        st.markdown(render_card("⚠️", "Sample Kecil", f"{low_n}", f"<{_MIN_N_CUSTOMER} customer assigned"), unsafe_allow_html=True)

    st.markdown(f"#### Top 10 {subject} — Productivity per Customer")
    top10 = df.nlargest(10, "Productivity_Actual")
    render_topn_barh_chart(
        top10, label_col, "Productivity_Actual", top_n=10, color="#2563eb",
        value_fmt=fmt_rp, xaxis_title="Rp per Customer", key="chart_productivity_top10",
        extra_hover_cols=[
            ("Assigned_Customers", "Jumlah Customer", lambda v: f"{v:.0f}"),
            ("Top1_Concentration", "Top-1 Concentration", lambda v: f"{v:.1f}%"),
        ],
    )

    st.markdown(f"#### Ranking Lengkap Productivity {subject}")
    search_query = st.text_input(
        f"Cari {subject}", key="productivity_search_query", placeholder=f"Ketik nama {subject.lower()}...",
    )
    table_source = df
    if search_query.strip():
        q = search_query.strip().upper()
        table_source = table_source[table_source[label_col].astype(str).str.upper().str.contains(q, na=False)]

    display_cols = [name_col] + (["Cabang"] if subject == "Salesman" else []) + [
        "Assigned_Customers", "Order", "Actual", "Productivity_Order", "Productivity_Actual",
        "Relative_Productivity", "Top1_Concentration",
    ]
    display = table_source[display_cols].copy()
    display = display.rename(columns={
        name_col: subject, "Assigned_Customers": "Jumlah Customer",
        "Productivity_Order": "Productivity (Order)", "Productivity_Actual": "Productivity (Actual)",
        "Relative_Productivity": "Relative Productivity (%)", "Top1_Concentration": "Top-1 Concentration (%)",
    })

    st.dataframe(
        display.style
        .map(_highlight_pct, subset=["Relative Productivity (%)"])
        .map(_highlight_concentration, subset=["Top-1 Concentration (%)"])
        .format({
            "Order": FMT_RP, "Actual": FMT_RP, "Productivity (Order)": FMT_RP, "Productivity (Actual)": FMT_RP,
            "Relative Productivity (%)": "{:.1f}%", "Top-1 Concentration (%)": "{:.1f}%",
            "Jumlah Customer": "{:.0f}",
        }),
        use_container_width=True, hide_index=True,
        height=min(auto_table_height(len(display)), 600),
    )

    st.markdown("---")
    st.markdown("### Penjelasan")
    st.markdown(
        "- **Productivity** = Order/Actual dibagi jumlah customer yang di-assign (bukan cuma yang aktif transaksi) — supaya subjek yang cuma mengandalkan sedikit akun besar tidak terlihat lebih \"produktif\" dari yang bekerja ke seluruh portofolionya.\n"
        "- **Relative Productivity (%)** = Productivity (Actual) dibanding rata-rata Cabang sendiri (untuk Salesman) atau rata-rata Nasional (untuk Cabang) — bukan dibanding Target, supaya bukan sekadar mengulang Achievement% yang sudah ada di tab Target.\n"
        "- **Top-1 Concentration (%)** = seberapa besar 1 customer terbesar menyumbang ke revenue subjek ini. ≥50% berarti kalau customer itu berhenti, lebih dari separuh revenue subjek ini ikut hilang.\n"
        f"- **Sample Kecil** = subjek dengan <{_MIN_N_CUSTOMER} customer assigned — angka Productivity-nya gampang melenceng gara-gara 1-2 transaksi besar, baca hati-hati."
    )
