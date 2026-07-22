# ============================================================
# 📐📏 TAB: KELEBARAN & KEDALAMAN (extracted from Operasional Partnumber)
# ============================================================
import streamlit as st
import pandas as pd
from utils.data_loader import list_bulan_standar
from utils.matgroup_engine import MATGROUP_ORDER
from utils.components import TOTAL_ROW_STYLE, auto_table_height, build_pivot, cleanup_selection

SUBJECT_DIMENSIONS = {
    "Per Area": "Area",
    "Per Cabang": "Cabang",
    "Per Salesman": "Salesman_Name",
    "Per Customer": "Customer_Label",
}

SUBJECT_COL_WIDTH = {"Per Area": None, "Per Cabang": 140, "Per Salesman": 150, "Per Customer": 180}

QUARTER_MONTHS = {
    1: list_bulan_standar[0:3],
    2: list_bulan_standar[3:6],
    3: list_bulan_standar[6:9],
    4: list_bulan_standar[9:12],
}

BULAN_ABBR = {
    "Januari": "JAN", "Februari": "FEB", "Maret": "MAR", "April": "APR",
    "Mei": "MEI", "Juni": "JUN", "Juli": "JUL", "Agustus": "AGS",
    "September": "SEP", "Oktober": "OKT", "November": "NOV", "Desember": "DES",
}

MAX_TABLE_HEIGHT = 600

SUBJECT_SORT_MODE = {
    "Per Area": "total_desc",
    "Per Cabang": "alpha",
    "Per Salesman": "alpha",
    "Per Customer": "alpha",
}


def _prepare_order_df(df_order):
    df = df_order.copy()
    df["Area"] = df["Kode_Area"].astype(str).str.replace("AOM", "Area ", regex=False)
    df["Cabang"] = df["Cabang"].astype(str).str.strip()
    df["Salesman_Name"] = df["Salesman_Name"].astype(str).str.strip().str.upper()
    df["Customer_Name"] = df["Customer_Name"].astype(str).str.strip().str.upper()
    df["Customer_Label"] = df["Customer_No"].astype(str) + " - " + df["Customer_Name"]
    df["Tahun_Label"] = df["Tahun"].astype(int).astype(str)
    df["Kuartal_Num"] = ((df["Bulan_Num"] - 1) // 3) + 1
    df["Kuartal_Label"] = "Q" + df["Kuartal_Num"].astype(str) + " " + df["Tahun_Label"]
    df["Bulan_Label"] = df["Bulan"].astype(str) + " " + df["Tahun_Label"]
    return df


def _compact_bulan_label(label):
    bulan, tahun = label.rsplit(" ", 1)
    abbr = BULAN_ABBR.get(bulan, bulan[:3].upper())
    return f"{abbr}'{tahun[-2:]}"


def _truncate_customer_name(name):
    name = str(name).strip()
    if len(name) <= 17:
        return name.upper()
    words = name.split()
    if not words:
        return name.upper()
    first_stripped = words[0].upper().rstrip(".")
    if first_stripped in ("PT", "CV"):
        result = " ".join([words[0]] + words[1:3])
    else:
        result = " ".join(words[:3])
    return result.upper()


def _format_customer_display(label):
    no_part, name_part = label.split(" - ", 1)
    return f"{no_part} -\n{_truncate_customer_name(name_part)}"


def _get_time_dimension(data, time_dim):
    uniq = data[["Tahun_Label", "Tahun"]].drop_duplicates().sort_values("Tahun")
    return "Tahun_Label", uniq["Tahun_Label"].tolist()


def _build_matgroup_pivot(data, subj_col, time_col, time_order, value_col, aggfunc, sort_mode):
    d = data.dropna(subset=[subj_col, time_col, value_col, "Mat_Group"])
    if d.empty:
        return pd.DataFrame()

    pivot = pd.pivot_table(
        d, index=[subj_col, "Mat_Group"], columns=time_col, values=value_col,
        aggfunc=aggfunc, fill_value=0,
    )
    pivot = pivot.reindex(columns=time_order, fill_value=0)

    if aggfunc == "nunique":
        totals = d.groupby([subj_col, "Mat_Group"])[value_col].nunique()
        pivot["TOTAL"] = totals.reindex(pivot.index).fillna(0).astype(int)
    else:
        pivot["TOTAL"] = pivot[time_order].sum(axis=1)

    subj_totals = pivot.groupby(level=0)["TOTAL"].sum()
    if sort_mode == "alpha":
        ordered_subjs = sorted(subj_totals.index.tolist())
    else:
        ordered_subjs = subj_totals.sort_values(ascending=False).index.tolist()

    mg_rank = {m: i for i, m in enumerate(MATGROUP_ORDER)}
    new_idx = []
    for subj in ordered_subjs:
        if subj not in pivot.index.get_level_values(0):
            continue
        subj_mgs = pivot.loc[subj].index.tolist()
        subj_mgs.sort(key=lambda m: mg_rank.get(m, 999))
        new_idx.extend((subj, mg) for mg in subj_mgs)

    pivot = pivot.loc[new_idx]

    grand = {}
    for col in time_order:
        col_data = d[d[time_col] == col]
        grand[col] = col_data[value_col].nunique() if aggfunc == "nunique" else col_data[value_col].sum()
    grand["TOTAL"] = d[value_col].nunique() if aggfunc == "nunique" else d[value_col].sum()

    grand_df = pd.DataFrame(grand, index=pd.MultiIndex.from_tuples([("TOTAL", "")]))
    pivot = pd.concat([pivot, grand_df])

    return pivot


def _render_pivot_section(df_src, value_col, aggfunc, key_prefix, enable_matgroup=False):
    has_mg = enable_matgroup and "Mat_Group" in df_src.columns
    if has_mg:
        col_dim1, col_dim2, col_mg_mode = st.columns(3)
    else:
        col_dim1, col_dim2 = st.columns(2)

    with col_dim1:
        time_dim = st.selectbox("Dimensi Waktu", ["Per Tahun", "Per Kuartal", "Per Bulan"], key=f"waktu_{key_prefix}")
    with col_dim2:
        subj_dim = st.selectbox("Dimensi Subjek", list(SUBJECT_DIMENSIONS.keys()), key=f"subjek_{key_prefix}")

    show_matgroup = False
    if has_mg:
        with col_mg_mode:
            mg_mode = st.radio(
                "Mode Matgroup", ["Tanpa Matgroup", "Dengan Matgroup"],
                index=0, horizontal=True, key=f"mg_mode_{key_prefix}",
            )
            show_matgroup = mg_mode == "Dengan Matgroup"

    subj_col = SUBJECT_DIMENSIONS[subj_dim]
    tahun_list = sorted(df_src["Tahun"].dropna().unique().tolist())
    tahun_terbaru = tahun_list[-1] if tahun_list else None

    df_filtered = df_src
    pilih_tahun = None
    pilih_kuartal = []
    pilih_area, pilih_cabang, pilih_salesman = [], [], []
    area_key, cabang_key, salesman_key = f"filter_area_{key_prefix}", f"filter_cabang_{key_prefix}", f"filter_salesman_{key_prefix}"

    need_tahun_pill = time_dim in ("Per Kuartal", "Per Bulan")
    need_kuartal_pill = time_dim == "Per Bulan"
    need_area_pill = subj_dim != "Per Area"

    pills_needed = []
    if need_tahun_pill: pills_needed.append("tahun")
    if need_kuartal_pill: pills_needed.append("kuartal")
    if need_area_pill: pills_needed.append("area")

    pill_cols = st.columns(len(pills_needed)) if pills_needed else []
    pill_slot = dict(zip(pills_needed, pill_cols))

    if need_tahun_pill:
        with pill_slot["tahun"]:
            tahun_options = [str(t) for t in tahun_list]
            pilih_tahun_raw = st.pills(
                "Pilih Tahun", tahun_options, selection_mode="single",
                default=str(tahun_terbaru) if tahun_terbaru is not None else None,
                key=f"tahun_{key_prefix}",
            )
        pilih_tahun = int(pilih_tahun_raw) if pilih_tahun_raw else tahun_terbaru
        df_filtered = df_src[df_src["Tahun"] == pilih_tahun]

    if need_kuartal_pill:
        with pill_slot["kuartal"]:
            pilih_kuartal = st.pills(
                "Filter Kuartal", ["Q1", "Q2", "Q3", "Q4"], selection_mode="multi",
                key=f"kuartal_{key_prefix}",
            ) or []

    if time_dim == "Per Tahun":
        time_col, time_order = _get_time_dimension(df_filtered, time_dim)
    elif time_dim == "Per Kuartal":
        time_col = "Kuartal_Label"
        time_order = [f"Q{q} {pilih_tahun}" for q in [1, 2, 3, 4]]
    else:
        quarter_nums = sorted(int(q[1]) for q in pilih_kuartal) if pilih_kuartal else [1, 2, 3, 4]
        bulan_tampil = [b for q in quarter_nums for b in QUARTER_MONTHS[q]]
        time_col = "Bulan_Label"
        time_order = [f"{b} {pilih_tahun}" for b in bulan_tampil]
        if pilih_kuartal:
            df_filtered = df_filtered[df_filtered["Bulan"].isin(bulan_tampil)]

    if need_area_pill:
        if subj_dim == "Per Cabang":
            area_options = sorted(df_filtered["Area"].dropna().unique().tolist())
        else:
            sel_cabang_raw = st.session_state.get(cabang_key, [])
            sel_salesman_raw = st.session_state.get(salesman_key, [])
            scope_for_area = df_filtered
            if sel_cabang_raw:
                scope_for_area = scope_for_area[scope_for_area["Cabang"].isin(sel_cabang_raw)]
            if subj_dim == "Per Customer" and sel_salesman_raw:
                scope_for_area = scope_for_area[scope_for_area["Salesman_Name"].isin(sel_salesman_raw)]
            area_options = sorted(scope_for_area["Area"].dropna().unique().tolist())
        cleanup_selection(area_key, area_options)
        with pill_slot["area"]:
            pilih_area = st.pills("Filter Area", area_options, selection_mode="multi", key=area_key) or []

    dropdowns_needed = []
    if subj_dim in ("Per Salesman", "Per Customer"): dropdowns_needed.append("cabang")
    if subj_dim == "Per Customer": dropdowns_needed.append("salesman")

    if dropdowns_needed:
        dd_cols = st.columns(len(dropdowns_needed))
        dd_slot = dict(zip(dropdowns_needed, dd_cols))

        sel_salesman_raw = st.session_state.get(salesman_key, []) if subj_dim == "Per Customer" else []
        scope_for_cabang = df_filtered[df_filtered["Area"].isin(pilih_area)] if pilih_area else df_filtered
        if subj_dim == "Per Customer" and sel_salesman_raw:
            scope_for_cabang = scope_for_cabang[scope_for_cabang["Salesman_Name"].isin(sel_salesman_raw)]
        cabang_options = sorted(scope_for_cabang["Cabang"].dropna().unique().tolist())
        cleanup_selection(cabang_key, cabang_options)
        with dd_slot["cabang"]:
            pilih_cabang = st.multiselect("Filter Cabang", cabang_options, key=cabang_key, placeholder="Semua (klik untuk filter)")

        if subj_dim == "Per Customer":
            scope_for_salesman = df_filtered[df_filtered["Area"].isin(pilih_area)] if pilih_area else df_filtered
            if pilih_cabang:
                scope_for_salesman = scope_for_salesman[scope_for_salesman["Cabang"].isin(pilih_cabang)]
            salesman_options = sorted(scope_for_salesman["Salesman_Name"].dropna().unique().tolist())
            cleanup_selection(salesman_key, salesman_options)
            with dd_slot["salesman"]:
                pilih_salesman = st.multiselect("Filter Salesman", salesman_options, key=salesman_key, placeholder="Semua (klik untuk filter)")

    if pilih_area:
        df_filtered = df_filtered[df_filtered["Area"].isin(pilih_area)]
    if subj_dim in ("Per Salesman", "Per Customer") and pilih_cabang:
        df_filtered = df_filtered[df_filtered["Cabang"].isin(pilih_cabang)]
    if subj_dim == "Per Customer" and pilih_salesman:
        df_filtered = df_filtered[df_filtered["Salesman_Name"].isin(pilih_salesman)]

    auto_jakarta = False
    if show_matgroup and subj_dim in ("Per Salesman", "Per Customer") and not pilih_cabang:
        jakarta = [c for c in df_filtered["Cabang"].unique() if "jakarta" in c.lower()]
        if jakarta:
            df_filtered = df_filtered[df_filtered["Cabang"].isin(jakarta)]
            auto_jakarta = True

    if subj_dim == "Per Customer":
        search_kw = st.text_input(
            "Cari customer", placeholder="Cari customer...",
            key=f"search_customer_{key_prefix}", label_visibility="collapsed",
        )
        if search_kw:
            kw = search_kw.strip().lower()
            mask = (
                df_filtered["Customer_No"].astype(str).str.lower().str.contains(kw, na=False) |
                df_filtered["Customer_Name"].astype(str).str.lower().str.contains(kw, na=False)
            )
            df_filtered = df_filtered[mask]

    if auto_jakarta:
        st.caption("Mode Matgroup aktif — default Cabang JAKARTA. Pilih cabang lain di filter untuk mengubah.")

    fmt = lambda x: f"{x:,.0f}".replace(",", ".")

    if show_matgroup:
        pivot = _build_matgroup_pivot(df_filtered, subj_col, time_col, time_order, value_col, aggfunc, SUBJECT_SORT_MODE[subj_dim])
        if pivot.empty:
            st.info("Tidak ada data.")
            return
        pivot.index.names = [subj_dim.replace("Per ", ""), "Matgroup"]

        total_css = '; '.join(f'{k}: {v}' for k, v in TOTAL_ROW_STYLE.items())
        styled = pivot.style.format(fmt).set_properties(
            **{'text-align': 'right', 'font-size': '13px'}
        ).set_properties(
            subset=pd.IndexSlice[:, "TOTAL"],
            **{'font-weight': 'bold', 'background-color': 'rgba(245, 158, 11, 0.08)'}
        ).apply(
            lambda row: [total_css] * len(row) if (isinstance(row.name, tuple) and row.name[0] == "TOTAL") else [''] * len(row),
            axis=1,
        )

        if time_dim == "Per Bulan":
            styled = styled.format_index(lambda c: _compact_bulan_label(c) if c != "TOTAL" else c, axis=1)
        if subj_dim == "Per Customer":
            styled = styled.format_index(lambda i: _format_customer_display(i) if i != "TOTAL" else i, axis=0, level=0)

        row_px = 50 if subj_dim == "Per Customer" else 35
        height = min(auto_table_height(len(pivot), row_px=row_px), MAX_TABLE_HEIGHT)
        st.dataframe(styled, use_container_width=True, height=height)
    else:
        pivot = build_pivot(df_filtered, subj_col, time_col, time_order, value_col, aggfunc, sort_mode=SUBJECT_SORT_MODE[subj_dim])
        pivot.index.name = subj_dim.replace("Per ", "")

        styled = pivot.style.format(fmt).set_properties(
            **{'text-align': 'right', 'font-size': '13px'}
        ).set_properties(
            subset=pd.IndexSlice[:, "TOTAL"], **{'font-weight': 'bold', 'background-color': 'rgba(245, 158, 11, 0.08)'}
        ).set_properties(
            subset=pd.IndexSlice["TOTAL", :], **TOTAL_ROW_STYLE
        )

        if time_dim == "Per Bulan":
            styled = styled.format_index(lambda c: _compact_bulan_label(c) if c != "TOTAL" else c, axis=1)
        if subj_dim == "Per Customer":
            styled = styled.format_index(lambda i: _format_customer_display(i) if i != "TOTAL" else i, axis=0)

        row_px = 50 if subj_dim == "Per Customer" else 35
        height = min(auto_table_height(len(pivot), row_px=row_px), MAX_TABLE_HEIGHT)
        col_width = SUBJECT_COL_WIDTH.get(subj_dim)
        column_config = {"_index": st.column_config.Column(width=col_width)} if col_width else None
        row_height = 50 if subj_dim == "Per Customer" else None

        st.dataframe(
            styled, use_container_width=True, height=height,
            column_config=column_config, row_height=row_height,
        )


def render_kelebaran(df_order):
    df = _prepare_order_df(df_order)
    _render_pivot_section(df, "Partnumber", "nunique", "kelebaran", enable_matgroup=True)
    st.markdown("---")
    st.markdown("### Penjelasan")
    st.markdown(
        "- **Kelebaran** menunjukkan jumlah Partnumber unik yang dipesan, dihitung sebagai banyaknya nomor part yang berbeda (bukan total transaksi atau total quantity) dalam suatu Area, Cabang, Salesman, Customer, atau periode tertentu. Metrik ini menggambarkan **keberagaman produk** yang terjual — semakin besar nilainya, semakin luas ragam produk yang dibeli oleh subjek tersebut.\n"
        "- Baris dan kolom **TOTAL** tidak diperoleh dari menjumlahkan angka-angka di atasnya, melainkan dihitung ulang langsung dari data gabungan. Hal ini dilakukan agar Partnumber yang sama tidak terhitung berulang kali apabila muncul di lebih dari satu Area, Cabang, Salesman, Customer, atau periode."
    )


def render_kedalaman(df_order):
    df = _prepare_order_df(df_order)
    _render_pivot_section(df, "Qty", "sum", "kedalaman", enable_matgroup=True)
    st.markdown("---")
    st.markdown("### Penjelasan")
    st.markdown(
        "- **Kedalaman** menunjukkan total quantity (Qty) yang dipesan, yaitu penjumlahan seluruh unit barang yang dibeli tanpa memperhatikan keberagaman jenis Partnumber-nya. Metrik ini menggambarkan **volume pembelian** — semakin besar nilainya, semakin banyak unit barang yang dibeli oleh subjek tersebut, meskipun jenis Partnumber-nya bisa saja terbatas.\n"
        "- **Kelebaran** dan **Kedalaman** sebaiknya dibaca berdampingan: subjek dengan Kelebaran tinggi namun Kedalaman rendah cenderung membeli banyak jenis produk dalam jumlah kecil-kecil, sedangkan subjek dengan Kelebaran rendah namun Kedalaman tinggi cenderung membeli sedikit jenis produk namun dalam jumlah besar."
    )
