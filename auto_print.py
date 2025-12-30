import streamlit as st
import win32print
import subprocess
import tempfile
import os
import time
import pandas as pd

# --- KONFIGURASI ---
# Karena sudah satu folder, cukup nama filenya aja
SUMATRA_EXE_PATH = "SumatraPDF.exe" 

st.set_page_config(page_title="Pro PDF Printer", layout="centered")

# --- CSS BIAR TAMPILAN RAPI ---
st.markdown("""
    <style>
    .stProgress > div > div > div > div {
        background-color: #4CAF50;
    }
    </style>
""", unsafe_allow_html=True)

# --- FUNGSI ---
def get_printers():
    try:
        return [p[2] for p in win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)]
    except:
        return []

def print_pdf_command(file_path, printer_name, sumatra_path):
    cmd = [
        sumatra_path,
        "-print-to", printer_name,
        "-print-settings", "noscale", # <-- Mencegah pengecilan skala yang bikin garis tipis
        "-silent",
        file_path
    ]
    # Menggunakan shell=True dan subprocess agar lebih bandel
    process = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if process.returncode != 0:
        raise Exception(f"Error SumatraPDF: {process.stderr}")

# --- UI UTAMA ---
st.title("🖨️ PDF Batch Printer (Pro V2)")

# Cek SumatraPDF
if not os.path.exists(SUMATRA_EXE_PATH):
    st.error(f"❌ File `{SUMATRA_EXE_PATH}` tidak ditemukan di folder ini!")
    st.info("Pastikan script ini dan folder SumatraPDF ada di tempat yang sama.")
    st.stop()

# 1. Pilih Printer
printer_list = get_printers()
l3210_index = 0
for i, p in enumerate(printer_list):
    if "L3210" in p or "Epson" in p:
        l3210_index = i
        break

col1, col2 = st.columns([3, 1])
with col1:
    selected_printer = st.selectbox("🖨️ Pilih Printer:", printer_list, index=l3210_index)
with col2:
    st.write("") # Spacer
    st.write("") 
    if st.button("⚙️ Tips Kualitas"):
        st.toast("Seting Epson ke 'High Quality' di Control Panel Windows biar garis tebal!", icon="💡")

# 2. Upload File
uploaded_files = st.file_uploader("📂 Upload PDF (Bisa Banyak)", type=["pdf"], accept_multiple_files=True)

if uploaded_files:
    st.divider()
    st.subheader("📝 Pilih File yang Mau Diprint")
    
    # Buat Dataframe untuk Checklist
    if 'file_selection' not in st.session_state or len(st.session_state.file_selection) != len(uploaded_files):
        # Default semua terpilih (True)
        data = [{"Nama File": f.name, "Print": True} for f in uploaded_files]
        st.session_state.file_selection = pd.DataFrame(data)

    # Tampilkan Editor Tabel (Bisa Centang/Uncentang)
    edited_df = st.data_editor(
        st.session_state.file_selection,
        column_config={
            "Print": st.column_config.CheckboxColumn(
                "Cetak?",
                help="Hilangkan centang jika tidak ingin mencetak file ini",
                default=True,
            )
        },
        disabled=["Nama File"],
        hide_index=True,
        use_container_width=True
    )

    # Filter file yang dicentang saja
    files_to_print = []
    for index, row in edited_df.iterrows():
        if row["Print"]:
            files_to_print.append(uploaded_files[index])

    count_print = len(files_to_print)
    
    # Tombol Aksi
    st.write(f"Total file akan dicetak: **{count_print}** file.")
    
    col_btn1, col_btn2 = st.columns([1, 1])
    
    start_print = col_btn1.button("🚀 MULAI PRINT", type="primary", use_container_width=True, disabled=count_print==0)
    
    if start_print:
        progress_bar = st.progress(0)
        status_text = st.empty()
        cancel_placeholder = st.empty()
        
        # Info Cancel
        cancel_placeholder.info("⚠️ Untuk membatalkan paksa, klik tombol 'Stop' (⏹️) di pojok kanan atas browser.")
        
        success_count = 0
        fail_count = 0
        
        for i, file_obj in enumerate(files_to_print):
            status_text.markdown(f"⏳ Sedang mencetak **{i+1}/{count_print}**: `{file_obj.name}`")
            
            try:
                # 1. Bikin Temp File
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tfile:
                    tfile.write(file_obj.read())
                    tpath = tfile.name
                
                # 2. Kirim ke Printer
                print_pdf_command(tpath, selected_printer, SUMATRA_EXE_PATH)
                success_count += 1
                
                # 3. Cleanup
                time.sleep(1.5) # Jeda biar printer napas dan antrean masuk
                try:
                    os.remove(tpath)
                except:
                    pass

            except Exception as e:
                fail_count += 1
                st.error(f"Gagal mencetak {file_obj.name}: {e}")
            
            # Update Progress
            progress = (i + 1) / count_print
            progress_bar.progress(progress)

        status_text.success("✅ Proses Selesai!")
        cancel_placeholder.empty() # Hilangkan info cancel
        
        if fail_count > 0:
            st.warning(f"Selesai: {success_count} Berhasil, {fail_count} Gagal.")
        else:
            st.balloons()
            st.toast(f"Mantap! {success_count} file berhasil dikirim ke printer.", icon="🎉")

else:
    st.info("👆 Upload file dulu di atas.")