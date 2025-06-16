# office_equipment_tracker.py

import streamlit as st
import pandas as pd
import sqlite3
import os

# --- Konstanta ---
DB_FILE = "office_equipment.db"
DEFAULT_COLUMNS = ["ID Barang", "Nama Barang", "Lokasi", "Jumlah", "Status"]

# --- Inisialisasi Database ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            id_barang TEXT PRIMARY KEY,
            nama_barang TEXT,
            lokasi TEXT,
            jumlah INTEGER,
            status TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT
        )
    ''')
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", ("admin", "admin123"))
    conn.commit()
    conn.close()

# --- Autentikasi ---
def login():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "username" not in st.session_state:
        st.session_state.username = ""

    if not st.session_state.logged_in:
        st.title("🔒 Login Inventaris Kantor")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
            if cursor.fetchone():
                st.session_state.logged_in = True
                st.session_state.username = username
                st.success("Login berhasil!")
                st.rerun()
            else:
                st.error("Username atau password salah!")
            conn.close()
        st.stop()

# --- Load data dari DB ---
def load_data():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM inventory", conn)
    conn.close()
    return df

# --- Simpan data ke DB ---
def insert_item(item):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO inventory (id_barang, nama_barang, lokasi, jumlah, status)
        VALUES (?, ?, ?, ?, ?)
    """, (item["ID Barang"], item["Nama Barang"], item["Lokasi"], item["Jumlah"], item["Status"]))
    conn.commit()
    conn.close()

def delete_item(item_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM inventory WHERE id_barang = ?", (item_id,))
    conn.commit()
    conn.close()

# --- Aplikasi Streamlit ---
def app():
    st.set_page_config(page_title="Pelacak Inventaris Kantor", layout="wide")

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "username" not in st.session_state:
        st.session_state.username = ""

    login()
    init_db()

    st.title("🏢 Pelacak Inventaris Kantor")
    df = load_data()

    # --- Sidebar: Tambah barang baru ---
    st.sidebar.header("➕ Tambah Barang Baru")
    with st.sidebar.form("add_form"):
        item_id = st.text_input("ID Barang")
        item_name = st.text_input("Nama Barang")
        location = st.text_input("Lokasi")
        quantity = st.number_input("Jumlah", min_value=1, step=1)
        status = st.selectbox("Status", ["Tersedia", "Dipinjam", "Rusak", "Tidak tersedia"])
        submitted = st.form_submit_button("Tambah Barang")

        if submitted:
            if not item_id.isdigit() or len(item_id) < 5:
                st.warning("ID Barang harus berupa angka dengan minimal 5 digit.")
            elif item_id and item_name and location:
                new_row = {
                    "ID Barang": item_id,
                    "Nama Barang": item_name,
                    "Lokasi": location,
                    "Jumlah": quantity,
                    "Status": status
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

    # --- Tampilan utama ---
    st.subheader("📋 Daftar Inventaris")
    search_query = st.text_input("🔍 Cari berdasarkan ID atau Nama Barang")

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

    st.write("### 📄 Hasil Pencarian")
    page_size = 10
    total_pages = max((len(filtered_df) - 1) // page_size + 1, 1)
    page_number = st.number_input("Halaman", min_value=1, max_value=total_pages, value=1, step=1)

    start_idx = (page_number - 1) * page_size
    end_idx = start_idx + page_size
    paged_df = filtered_df.iloc[start_idx:end_idx]

    st.dataframe(paged_df, use_container_width=True)

    # --- Hapus data ---
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

if __name__ == '__main__':
    app()
