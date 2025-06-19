# office_equipment_tracker.py

import streamlit as st
import pandas as pd
from supabase import create_client, Client

# --- Supabase Setup ---
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Autentikasi ---
def login():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "username" not in st.session_state:
        st.session_state.username = ""

    if not st.session_state.logged_in:
        st.set_page_config(page_title="Login Inventaris", layout="centered")
        st.title("🔒 Login Inventaris Kantor")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            result = supabase.table("users").select("*").eq("username", username).eq("password", password).execute()
            if result.data:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.success("Login berhasil!")
                st.rerun()
            else:
                st.error("Username atau password salah!")
        st.stop()

# --- Load data dari Supabase ---
def load_data():
    try:
        result = supabase.table("inventory").select("*").execute()
        df = pd.DataFrame(result.data)
        required_columns = ["id_barang", "nama_barang", "lokasi", "jumlah", "status"]
        missing = [col for col in required_columns if col not in df.columns]
        if missing:
            st.warning(f"⚠️ Kolom berikut tidak ditemukan di database: {missing}")
        return df
    except Exception as e:
        st.error("❌ Gagal memuat data dari Supabase.")
        st.exception(e)
        return pd.DataFrame()

# --- Simpan data ke Supabase ---
def insert_item(item):
    supabase.table("inventory").insert(item).execute()

# --- Hapus data dari Supabase ---
def delete_item(item_id):
    supabase.table("inventory").delete().eq("id_barang", item_id).execute()

# --- Aplikasi Streamlit ---
def app():
    st.set_page_config(page_title="Pelacak Inventaris Kantor", layout="wide")
    login()
    
    # === HEADER LOGO + JUDUL ===
    col_logo, col_title = st.columns([0.1, 0.9])
    with col_logo:
        st.image("Logo_PLN.png", width=60)
    with col_title:
        st.markdown("""
        <div style='display: flex; align-items: center; height: 100%;'>
            <h1 style='margin: 0; padding-left: 10px;'>Pelacak Inventaris Kantor di PT. PLN (Persero) UID Suluttenggo</h1>
        </div>
        """, unsafe_allow_html=True)

    # === LOAD DATA ===
    df = load_data()

    # === SIDEBAR: TAMBAH BARANG ===
    st.sidebar.header("➕ Tambah Barang Baru")
    with st.sidebar.form("add_form"):
        id_barang = st.text_input("ID Barang")
        nama_barang = st.text_input("Nama Barang")
        lokasi = st.text_input("Lokasi")
        jumlah = st.number_input("Jumlah", min_value=1, step=1)
        status = st.selectbox("Status", ["Tersedia", "Dipinjam", "Rusak", "Tidak tersedia"])
        submitted = st.form_submit_button("Tambah Barang")

        if submitted:
            if not id_barang.isdigit() or len(id_barang) != 5:
                st.warning("ID Barang harus berupa 5 digit angka (contoh: 12345).")
            elif id_barang and nama_barang and lokasi:
                new_row = {
                    "id_barang": id_barang,
                    "nama_barang": nama_barang,
                    "lokasi": lokasi,
                    "jumlah": jumlah,
                    "status": status
                }
                insert_item(new_row)
                st.success("Barang baru berhasil ditambahkan! Silakan refresh halaman.")
            else:
                st.warning("Mohon isi semua kolom wajib (ID, Nama, Lokasi).")

    st.sidebar.markdown("---")
    st.sidebar.write(f"Selamat datang, **{st.session_state.username}**!")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.rerun()

    # === FILTER & SEARCH ===
    st.subheader("📋 Daftar Inventaris")
    search_query = st.text_input("🔍 Cari berdasarkan ID atau Nama Barang")

    if df.empty:
        st.warning("Tidak ada data inventaris untuk ditampilkan.")
        return

    filter_col1, filter_col2 = st.columns(2)
    with filter_col1:
        filter_status = st.selectbox("Filter Status", ["Semua"] + df["status"].dropna().unique().tolist())
    with filter_col2:
        filter_location = st.selectbox("Filter Lokasi", ["Semua"] + df["lokasi"].dropna().unique().tolist())

    filtered_df = df.copy()
    if search_query:
        filtered_df = filtered_df[
            filtered_df["id_barang"].astype(str).str.contains(search_query, case=False, na=False) |
            filtered_df["nama_barang"].astype(str).str.contains(search_query, case=False, na=False)
        ]
    if filter_status != "Semua":
        filtered_df = filtered_df[filtered_df["status"] == filter_status]
    if filter_location != "Semua":
        filtered_df = filtered_df[filtered_df["lokasi"] == filter_location]

    # === HASIL PENCARIAN ===
    st.write("### 📄 Hasil Pencarian")
    page_size = 10
    total_pages = max((len(filtered_df) - 1) // page_size + 1, 1)
    page_number = st.number_input("Halaman", min_value=1, max_value=total_pages, value=1, step=1)

    start_idx = (page_number - 1) * page_size
    end_idx = start_idx + page_size
    paged_df = filtered_df.iloc[start_idx:end_idx]

    st.dataframe(paged_df, use_container_width=True)

    # === HAPUS DATA ===
    st.subheader("🗑️ Hapus Data Inventaris")
    with st.form("delete_form"):
        id_to_delete = st.text_input("Masukkan ID Barang yang ingin dihapus")
        delete_submitted = st.form_submit_button("Hapus Barang")
        if delete_submitted:
            if id_to_delete:
                if id_to_delete in df["id_barang"].astype(str).values:
                    delete_item(id_to_delete)
                    st.success(f"Barang dengan ID '{id_to_delete}' telah dihapus.")
                    st.rerun()
                else:
                    st.warning("ID Barang tidak ditemukan.")
            else:
                st.warning("Mohon masukkan ID Barang.")

    st.download_button("📥 Unduh CSV", data=filtered_df.to_csv(index=False), file_name="inventaris_kantor.csv", mime="text/csv")

if __name__ == "__main__":
    app()
