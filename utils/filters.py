# ============================================================
# 🎛️ SHARED TOP-OF-PAGE FILTERS
# ============================================================
import streamlit as st
from utils.data_loader import list_bulan_standar
from utils.components import render_tile_filter


def render_top_filters(df_order, df_supply, page_key):
    """Render filter umum (Tahun/Bulan/Area/Cabang/Jenis/Kelas Customer) di badan halaman,
    di dalam expander — pengganti sidebar filter lama, supaya layout tab bisa full-width dan
    filter bisa di-collapse kalau tidak dibutuhkan lagi setelah dipilih.

    Layout tile 3-baris (baris 1: Tahun+Bulan, baris 2: Area/Jenis/Kelas Customer, baris 3:
    Cabang full-width) dibungkus st.container(key=f"general_filter_panel_{page_key}") supaya
    CSS di utils/styles.py bisa nge-tint expander-nya oranye transparan — pembeda visual dari
    expander/filter per-tab lain yang polos, tanpa harus styling st.expander app-wide.

    `page_key` (mis. "financial"/"marketing") bikin class container unik per halaman, supaya
    CSS yang menyasar tab tertentu di 1 halaman (mis. auto-hide panel ini di tab Pacing-nya
    Laporan Financial) tidak ikut ke-apply di halaman lain yang urutan tab-nya beda.
    """
    with st.container(key=f"general_filter_panel_{page_key}"):
        with st.expander("🎛️ Filter General", expanded=True):
            # ── Baris 1: Tahun (1/3), Bulan (2/3) ──
            col_tahun, col_bulan = st.columns([1, 2])
            with col_tahun:
                with st.container(key="genfilter_tile_tahun"):
                    tahun_list = sorted(df_order["Tahun"].dropna().unique())
                    tahun_options = [str(t) for t in tahun_list]
                    st.markdown("**📅 Tahun**")
                    pilih_tahun_raw = st.pills(
                        "Tahun", tahun_options, selection_mode="single",
                        default=str(tahun_list[-1]), key="genfilter_tahun", label_visibility="collapsed",
                    )
                    pilih_tahun = int(pilih_tahun_raw) if pilih_tahun_raw else tahun_list[-1]
            with col_bulan:
                with st.container(key="genfilter_tile_bulan"):
                    pilih_bulan = render_tile_filter("📆 Bulan", list_bulan_standar, key="genfilter_bulan")

            mask_base_order = (df_order["Tahun"] == pilih_tahun) & (df_order["Bulan"].isin(pilih_bulan))
            mask_base_supply = (df_supply["Tahun"].isin([pilih_tahun, pilih_tahun - 1])) & (df_supply["Bulan"].isin(pilih_bulan))
            df_order_base = df_order[mask_base_order]
            df_supply_base = df_supply[mask_base_supply]

            # ── Baris 2: Area Operation, Jenis Customer, Kelas Customer ──
            col_area, col_jenis, col_kelas = st.columns(3)
            with col_area:
                with st.container(key="genfilter_tile_area"):
                    area_list = sorted(df_order_base["Kode_Area"].dropna().unique())
                    pilih_area = render_tile_filter("🌐 Area Operation", area_list, key="genfilter_area")

            df_order_area = df_order_base[df_order_base["Kode_Area"].isin(pilih_area)]
            df_supply_area = df_supply_base[df_supply_base["Kode_Area"].isin(pilih_area)]

            with col_jenis:
                with st.container(key="genfilter_tile_jenis"):
                    jenis_list = sorted(df_order_area["Jenis_Customer"].dropna().unique())
                    pilih_jenis = render_tile_filter("👤 Jenis Customer", jenis_list, key="genfilter_jenis")

            with col_kelas:
                with st.container(key="genfilter_tile_kelas"):
                    kelas_list = sorted(df_order_area[df_order_area["Jenis_Customer"].isin(pilih_jenis)]["Kelas_Customer"].dropna().unique())
                    pilih_kelas = render_tile_filter("⭐ Kelas Customer", kelas_list, key="genfilter_kelas")

            # ── Baris 3: Cabang (opsi terbanyak → tile full-width, wrap ~2 baris) ──
            with st.container(key="genfilter_tile_cabang"):
                cabang_list = sorted(df_order_area["Cabang"].dropna().unique())
                pilih_cabang = render_tile_filter("🏢 Cabang", cabang_list, key="genfilter_cabang")

    mask_final = lambda df: (
        df["Jenis_Customer"].isin(pilih_jenis)
        & df["Kelas_Customer"].isin(pilih_kelas)
        & df["Cabang"].isin(pilih_cabang)
    )
    df_order_final = df_order_area[mask_final(df_order_area)].copy()
    df_supply_final = df_supply_area[mask_final(df_supply_area)].copy()

    return df_order_final, df_supply_final, pilih_tahun, pilih_bulan, pilih_cabang, pilih_jenis, pilih_kelas, pilih_area, cabang_list
