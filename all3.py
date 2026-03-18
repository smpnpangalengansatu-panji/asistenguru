import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt
from io import BytesIO
import PyPDF2

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="AA Guru", layout="wide", page_icon="🎓")

# --- SISIPAN KODE CSS & HTML UNTUK TAMPILAN PROFESIONAL ---
def apply_custom_ui():
    st.markdown("""
        <style>
        /* Impor Font Modern */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
        
        /* Pengaturan Global */
        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
            color: #1E293B;
        }

        /* Header Utama dengan Gradien */
        .main-header {
            background: linear-gradient(135deg, #1E3A8A 0%, #3B82F6 100%);
            color: white;
            padding: 2.5rem;
            border-radius: 15px;
            margin-bottom: 2rem;
            text-align: center;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        }
        .main-header h1 { margin: 0; font-size: 2.5rem; font-weight: 700; }
        .main-header p { margin-top: 0.5rem; opacity: 0.9; font-size: 1.1rem; }

        /* Styling Sidebar */
        [data-testid="stSidebar"] {
            background-color: #F8FAFC;
            border-right: 1px solid #E2E8F0;
        }

        /* Kontainer Hasil AI agar seperti Card */
        .ai-output-card {
            background-color: #ffffff;
            border: 1px solid #E2E8F0;
            padding: 2rem;
            border-radius: 12px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
            margin-top: 1.5rem;
            line-height: 1.6;
        }

        /* Mempercantik Tombol Download */
        .stDownloadButton button {
            background-color: #10B981 !important;
            color: white !important;
            border: none !important;
            padding: 0.6rem 1.2rem !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            transition: all 0.3s ease !important;
            width: 100%;
        }
        .stDownloadButton button:hover {
            background-color: #059669 !important;
            box-shadow: 0 10px 15px -3px rgba(16, 185, 129, 0.3) !important;
            transform: translateY(-2px);
        }

        /* Garis Divider */
        hr { margin: 2rem 0 !important; border-top: 2px solid #F1F5F9 !important; }
        </style>
        
        <div class="main-header">
            <h1>🎓 AA Guru </h1>
            <p>Asisten Administrasi Guru</p>
        </div>
    """, unsafe_allow_html=True)

# Panggil Fungsi UI
apply_custom_ui()

# --- FUNGSI PARSER DOCX ---
def create_formatted_docx(text, title):
    text = text.replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n")
    doc = Document()
    doc.add_heading(title, 0)
    lines = text.split('\n')
    is_table = False
    table_data = []

    for line in lines:
        clean_line = line.strip()
        if '|' in clean_line:
            if '---' in clean_line: continue
            cells = [c.strip() for c in clean_line.split('|') if c.strip()]
            if cells:
                table_data.append(cells)
                is_table = True
            continue
        else:
            if is_table and table_data:
                table = doc.add_table(rows=len(table_data), cols=len(table_data[0]))
                table.style = 'Table Grid'
                for i, row in enumerate(table_data):
                    for j, cell_text in enumerate(row):
                        if j < len(table.columns):
                            table.cell(i, j).text = cell_text.replace('**', '')
                table_data = []
                is_table = False
        
        if not clean_line: continue
        if clean_line.startswith('#'):
            level = clean_line.count('#')
            doc.add_heading(clean_line.replace('#', '').strip(), level=min(level, 3))
        elif clean_line.startswith(('* ', '- ')):
            doc.add_paragraph(clean_line[2:].replace('**', ''), style='List Bullet')
        else:
            doc.add_paragraph(clean_line.replace('**', ''))
            
    target_stream = BytesIO()
    doc.save(target_stream)
    return target_stream.getvalue()

# --- FUNGSI GLOBAL ---
def call_gemini_ai(api_key, prompt):
    try:
        genai.configure(api_key=api_key)
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        selected_model = next((m for m in available_models if "1.5-flash" in m), available_models[0])
        model = genai.GenerativeModel(model_name=selected_model, safety_settings=safety_settings)
        response = model.generate_content(prompt)
        return response.text if response.candidates and response.candidates[0].content.parts else "ERROR: Respons kosong."
    except Exception as e:
        return f"ERROR: {str(e)}"

def read_pdf(file):
    pdf_reader = PyPDF2.PdfReader(file)
    return "".join([page.extract_text() for page in pdf_reader.pages])

# --- 2. SESSION STATE ---
if "api_key" not in st.session_state: st.session_state.api_key = ""
if "tp_result" not in st.session_state: st.session_state.tp_result = ""
if "atp_result" not in st.session_state: st.session_state.atp_result = ""
if "modul_result" not in st.session_state: st.session_state.modul_result = ""
if "page_modul" not in st.session_state: st.session_state.page_modul = 1
if "data_modul" not in st.session_state: st.session_state.data_modul = {}
if "fase_terpilih" not in st.session_state: st.session_state.fase_terpilih = "Fase A"
if 'soal_result' not in st.session_state: st.session_state.soal_result = None
if 'kisikisi_result' not in st.session_state: st.session_state.kisikisi_result = None
if 'list_topik' not in st.session_state: st.session_state.list_topik = [{"nama": "", "jumlah": 5}]

# --- 3. SIDEBAR NAVIGATION ---
page = st.sidebar.radio("Tahapan Kerja:", [
    "1. Bedah CP & TP", 
    "2. Alur (ATP) & Pemetaan JP", 
    "3. Modul Ajar Expert",
    "4. Generator Soal & Kisi-kisi"
])
st.sidebar.divider()
st.sidebar.markdown("### 🔑 Akses")
st.session_state.api_key = st.sidebar.text_input("API Key Gemini:", type="password", value=st.session_state.api_key)

# --- 4. LOGIKA HALAMAN ---

if page == "1. Bedah CP & TP":
    st.header("📋 Tahap 1: Bedah CP & Tujuan Pembelajaran (TP)")
    uploaded_file = st.file_uploader("Unggah PDF CP (Opsional):", type="pdf")
    initial_cp = read_pdf(uploaded_file) if uploaded_file else ""
    
    col1, col2 = st.columns([3, 1])
    with col1:
        cp_input = st.text_area("Tempel Teks CP BSKAP 046/2025:", value=initial_cp, height=250)
    with col2:
        st.session_state.fase_terpilih = st.selectbox("Pilih Fase:", ["Fase A", "Fase B", "Fase C", "Fase D", "Fase E", "Fase F"])
    
    if st.button("Generate Analisis & TP", type="primary", use_container_width=True):
        if not st.session_state.api_key or not cp_input:
            st.warning("Mohon lengkapi API Key dan teks CP.")
        else:
            with st.spinner("AI sedang membedah CP..."):
                prompt = f"""Bertindaklah sebagai ahli kurikulum Spesialis Kurikulum Kemendikbudristek (Update BSKAP 046/2025). Analisis CP berikut: {cp_input}. 
                1. Buat tabel dengan format yang rapi analisis Kompetensi & Materi Pokok. 
                2. Turunkan menjadi TP yang dibagi otomatis per kelas dalam {st.session_state.fase_terpilih} secara scaffolding.
                    Instruksi Analisis:
                    a. Dekonstruksi: Pisahkan identifikasi Kompetensi Kata Kerja Operasional(KKO) dan Konten (Materi Esensial).
                    b. Perumusan TP: Buat Tujuan Pembelajaran yang konkret, terukur, dan mencakup aspek pemahaman.
                    c. Penyusunan ATP: Urutkan TP secara logis dan prasyarat sesuai prinsip Panduan Pembelajaran dan Asesmen (PPA) Kurikulum Merdeka 2025/2026.
                    d. Deep Learning Integration: Berikan saran aktivitas belajar yang:
                        - Mindful: Membangun kesadaran diri siswa akan tujuan belajar.
                        - Meaningful: Menghubungkan konteks nyata/masalah otentik.
                        - Joyful: Menantang namun menyenangkan (Flow state).
                    e. Output harus dalam tabel Markdown yang rapi."""
                
                st.session_state.tp_result = call_gemini_ai(st.session_state.api_key, prompt)
                st.rerun()

    if st.session_state.tp_result:
        st.markdown(f'<div class="ai-output-card">{st.session_state.tp_result}</div>', unsafe_allow_html=True)
        st.download_button("📥 Unduh TP (Docx)", create_formatted_docx(st.session_state.tp_result, "Analisis CP dan TP"), "TP_Analisis.docx")

elif page == "2. Alur (ATP) & Pemetaan JP":
    st.header("🗺️ Tahap 2: Alur Tujuan Pembelajaran (ATP) & JP")
    if not st.session_state.tp_result:
        st.error("⚠️ Selesaikan Tahap 1 terlebih dahulu.")
    else:
        if st.button("Generate Tabel ATP & Pemetaan JP", type="primary", use_container_width=True):
            with st.spinner("AI sedang menyusun alur..."):
                prompt = f"""Buatlah tabel ATP berdasarkan data TP ini: {st.session_state.tp_result}.
                Buatlah tabel Alur Tujuan Pembelajaran (ATP) dengan Output harus dalam tabel Markdown yang rapi untuk {st.session_state.fase_terpilih}.
                buatkan secara lengkap dan rinci, WAJIB tampilkan pada kolom: No, Capaian Pembelajaran (CP), Elemen, Kelas, Semester, TP, Materi Pokok, Alokasi Waktu (JP)."""
                st.session_state.atp_result = call_gemini_ai(st.session_state.api_key, prompt)
                st.rerun()
        
        if st.session_state.atp_result:
            st.markdown(f'<div class="ai-output-card">{st.session_state.atp_result}</div>', unsafe_allow_html=True)
            st.download_button("📥 Unduh ATP (Docx)", create_formatted_docx(st.session_state.atp_result, "Alur Tujuan Pembelajaran"), "ATP_JP.docx")

elif page == "3. Modul Ajar Expert":
    d = st.session_state.data_modul
    
    if st.session_state.page_modul == 1:
        st.title("📝 Penyusunan Modul Ajar")
        st.progress(0.33)
        
        with st.form("form_input_modul"):
            col1, col2 = st.columns(2)
            with col1:
                nama = st.text_input("Nama Guru", value=d.get('nama', ""), placeholder="Contoh: Iman Nuriman, ST.")
                unit = st.text_input("Unit Kerja", value=d.get('unit', ""), placeholder="Contoh: SMP Negeri 1 Pangalengan")
                mapel = st.text_input("Mata Pelajaran", value=d.get('mapel', ""))
                fase_input = st.selectbox("Fase", ["A", "B", "C", "D", "E", "F"], index=0)
            
            with col2:
                kelas = st.text_input("Kelas", value=d.get('kelas', ""))
                semester = st.selectbox("Semester", ["1 (Ganjil)", "2 (Genap)"])
                jp = st.text_input("Alokasi Waktu", value=d.get('jp', ""), placeholder="Contoh: 2 x 40 Menit")
                topik = st.text_input("Topik Pembelajaran", value=d.get('topik', ""))

            st.markdown("#### 🎯 Dimensi Profil Lulusan (DPL)")
            dimensi_dpl = st.multiselect("Pilih Dimensi:", ["Keimanan", "Kewargaan", "Penalaran Kritis", "Kreativitas", "Kolaborasi", "Kemandirian", "Kesehatan", "Komunikasi"], default=["Penalaran Kritis"])

            st.markdown("#### ⚙️ Metode Pembelajaran")
            model_belajar = st.selectbox("Model Pembelajaran", ["PBL", "PjBL", "Inquiry", "Cooperative", "Discovery", "Berdiferensiasi"])
            pertemuan = st.number_input("Jumlah Pertemuan", min_value=1, value=1)
            kondisi_khusus = st.text_area("Instruksi Tambahan:", value=d.get('kondisi_khusus', ""))

            submit = st.form_submit_button("Lanjut ke Konfirmasi →", use_container_width=True)
            if submit:
                st.session_state.data_modul = {
                    'nama': nama, 'unit': unit, 'mapel': mapel, 'fase': fase_input, 
                    'kelas': kelas, 'semester': semester, 'jp': jp, 'pertemuan': pertemuan,
                    'topik': topik, 'model': model_belajar, 'kondisi_khusus': kondisi_khusus,
                    'dimensi_dpl': dimensi_dpl
                }
                st.session_state.page_modul = 2
                st.rerun()

    elif st.session_state.page_modul == 2:
        st.title("🔍 Konfirmasi Kerangka Pembelajaran")
        data = st.session_state.data_modul
        with st.container(border=True):
            c1, c2 = st.columns(2)
            with c1:
                st.write(f"**Nama:** {data.get('nama')}")
                st.write(f"**Mapel:** {data.get('mapel')}")
            with c2:
                st.write(f"**Topik:** {data.get('topik')}")
                st.write(f"**Alokasi:** {data.get('jp')}")
        
        col_bt1, col_bt2 = st.columns(2)
        if col_bt1.button("⬅️ Edit Kembali", use_container_width=True):
            st.session_state.page_modul = 1
            st.rerun()
        if col_bt2.button("🚀 GENERATE", type="primary", use_container_width=True):
            st.session_state.page_modul = 3
            st.rerun()  # [PERBAIKAN] Menambahkan tanda kurung

    elif st.session_state.page_modul == 3:
        st.title("✨ Hasil Modul Ajar")
        d = st.session_state.data_modul
        
        # [PERBAIKAN] Cek apakah hasil sudah ada, jika belum baru panggil AI
        if not st.session_state.modul_result:
            prompt = f"""Bertindaklah sebagai Guru Ahli Kurikulum 2026. Buatlah **Modul Ajar** lengkap dengan pendekatan **Deep Learning** (Mindful, Meaningful, Joyful).
            
            IDENTITAS: 
            Nama: {d['nama']}, Unit: {d['unit']}, Mapel: {d['mapel']}, Fase/Kelas: {d['fase']}/{d['kelas']}, Semester: {d['semester']}, Alokasi: {d['jp']}, Topik: {d['topik']}.

            INSTRUKSI KHUSUS PEMBAGIAN ALOKASI WAKTU (WAJIB DIPATUHI): jika Fase {d['fase']} = A atau B atau C maka setiap 1 jam pelajaran (JP) = 35 Menit, jika Fase {d['fase']} = D maka setiap 1 jam pelajaran (JP) = 40 Menit, jika Fase {d['fase']} = E atau F maka setiap 1 jam pelajaran (JP) = 45 Menit.

            INSTRUKSI KHUSUS DARI GURU (WAJIB DIINTEGRASIKAN):
            {d['kondisi_khusus'] if d['kondisi_khusus'] else "Tidak ada instruksi tambahan."}

            STRUKTUR MODUL:
            A. CAPAIAN PEMBELAJARAN (CP): Jabarkan elemen dan rumusan CP sesuai topik {d['topik']} yang mengacu pada BSKAP Nomor 046/H/KR/2025 tentang Capaian Pembelajaran (CP) terbaru untuk PAUD, Pendidikan Dasar, dan Menengah (SD, SMP, SMA/SMK) pada Kurikulum Merdeka.
            B. DIMENSI PROFIL LULUSAN (DPL): Integrasikan dimensi {', '.join(d['dimensi_dpl'])} secara eksplisit dalam aktivitas.
            C. CAKUPAN MATERI: rumusan ruang lingkup materi apa saja yang akan dilaksanakan dalam pembelajaran sesuai dengan topik {d['topik']}.        
            D. DESAIN PEMBELAJARAN : Terdiri dari 
                1. TUJUAN PEMBELAJARAN: Tuliskan  rumusan  tujuan  pembelajaran  apa  yang  akan  dicapai  dalam  pembelajaran  yang mencakup kompetensi dan konten pada ruang lingkup materi dengan menggunakan kata kerja operasional yang relevan, Selan itu dalam merumuskan tujuan pembejaran harus mengandung ABCD, yaitu Audien, Behavior, Condition, dan Degree) Fokus pada kedalaman pemahaman (Deep Learning).
                2. PRAKTIK PAEDAGOGIS :Tuliskan model {d['model']} yang dipilih untuk mencapai tujuan pembelajaran dan tuliskan sintaksnya.
                3. KEMITRAAN PEMBELAJARAN (OPSIONAL) :Tuliskan kegiatan kemitraan atau kolaborasi dalam dan/atau ruang lingkup sekolah, seperti: kemitraan antar guru, lintas mata pelajaran, antar murid antar kelas, antar guru lintas sekolah, orang tua, komunitas, tokoh masyarakat, dunia usaha dan dunia industri kerja, institusi, atau mitra profesional.
                4. LINGKUNGAN PEMBELAJARAN : Tuliskan lingkungan pembelajaran yang diinginkan dalam pembelajaran dalam budaya belajar, ruang fisik dan/atau ruang virtual agar tecipta iklim belajar yang aman, nyaman, dan saling memuliakan, contoh : memberikan kepada siswa untuk menyampaikan pendapatnya dalam ruang kelas dan dan forum diskusi pada platform daring (ruang virtual bersifat opsional).
                5. PEMANFAATAN DIGITAL (OPSIONAL):Tuliskan pemanfaatan digital untuk menciptakan pembelajaran yang inteaktif, kolaboratif dan kontekstual, contoh : video pembelajaran, platform pembelajaran, perpustakaan digital, forum diskusi daring, aplikasi penilaian, dan sebagainya.

            E. PEMAHAMAN BERMAKNA & PERTANYAAN PEMANTIK: 3 Pertanyaan HOTS.
            F. LANGKAH-LANGKAH PEMBELAJARAN (Sintaks {d['model']} buat dalam {d['pertemuan']} pertemuan):
            Wajib mencakup 3 Kategori Deep Learning:
            1. MEMAHAMI (Berkesadaran & Bermakna)
            2. MENGAPLIKASI (Berkesadaran, Bermakna, Menyenangkan)
            3. MEREFLEKSI (Berkesadaran & Bermakna)
            Rincian: 
		a. Pendahuluan: Membangun koneksi emosional dan kesadaran (Mindful). 
		b. Inti : Eksplorasi mendalam menggunakan sintaks {d['model']}'
		c. Penutup: Refleksi metakognisi (Apa yang sekarang saya tahu yang sebelumnya saya tidak tahu?).
            G. ASESMEN: 
            WAJIB: Sajikan bagian asesmen dalam TABEL TERPISAH dengan ketentuan sebagai berikut:
            1. INSTRUMEN ASESMEN : Tuliskan instrumen asesment yang akan dipergunakan selama proses pembelajaran berlangsung dai awal sampai akhir Sajikan dalam tabel.
            2. TEKNIK ASESMEN: Tuliskan teknik asesment yang akan dipergunakan selama proses pembelajaran berlangsung dai awal  sampai  akhir,  apakah  menggunakan  tehnik  tes,  yaitu  :  tes  tulis,  tes  lisan,  atau  tes perbuatan dan non tes, yaitu : penilaian sejawat, penilaian diri, penilaian produk, observasi, portofolio, penilaian berbasis kelas, penilaian kinerja, skala sikap, wawancara, atau sosiometri, beserta contohnya dan sajikan dalam tabel.
            
            H. MEDIA, ALAT, DAN SUMBER BELAJAR : 
                1. MEDIA DAN ALAT PEMBELAJARAN : Tuliskan media dan alat pembelajaran yang akan dipergunakan pada saat pembelajaran berlangsung untuk membantu dan/atau mempermudah pemahaman murid dalam menerima materi pembelajaran.
                2. SUMBER BELAJAR : Tuliskan referensi baik berupa buku, jurnal, kamus, surat kabar, majalah, website, dan/atau yang lainnya yang akan  dipakai  selama proses  pembelajaran  dalam mendukung  ketecapaian kompetensi seperti yang telah dirumuskan dalam tujuan pembelajaran di atas. Contoh penulisan referensi berupa buku dalam sumber belajar, yaitu : Haris, Mohamad, 2020, Mudah Belajar Matematika, hal. 27-32, edisi kedua, cetakan kesatu, Surabaya, Pelita Bangsa.

            I. LEMBAR KERJA PESERTA DIDIK (LKPD): 
                1. LKPD : buatkan LKPD sesuai dengan jumlah pertemuan dan Buat instruksi tugas yang jelas dan mendalam setiap LKPD nya disertai RUBRIK PENILAIAN LKPD nya.

            J. LAMPIRAN: Ringkasan Materi Mendalam, dan Glosarium.

            Gunakan bahasa Indonesia yang formal namun mudah dipahami guru, pada kegiatan inti buat pembelajaran yang menyenangkan, membuat siswa aktif serta Gunakan format Markdown yang rapi dengan tabel untuk bagian Asesmen."""
            
            with st.status("🚀 AI sedang menyusun perangkat ajar...", expanded=True) as status:
                # [PERBAIKAN] Simpan ke session_state agar tidak hilang
                st.session_state.modul_result = call_gemini_ai(st.session_state.api_key, prompt)
                status.update(label="Selesai!", state="complete")
        
        # [PERBAIKAN] Tampilkan hasil dari session_state
        if st.session_state.modul_result:
            st.markdown(f'<div class="ai-output-card">{st.session_state.modul_result}</div>', unsafe_allow_html=True)
            
            docx_bytes = create_formatted_docx(st.session_state.modul_result, f"Modul Ajar - {d['topik']}")
                    
            st.divider()
            c_dl, c_new = st.columns([3, 1])
            with c_dl:
                st.download_button(
                    label="📥 Download Modul Ajar (.docx)",
                    data=docx_bytes,
                    file_name=f"Modul_Ajar_{d['topik'].replace(' ', '_')}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
            with c_new:
                if st.button("🔄 Buat Baru", use_container_width=True):
                    st.session_state.modul_result = ""
                    st.session_state.page_modul = 1
                    st.rerun()

elif page == "4. Generator Soal & Kisi-kisi":
    st.header("❓ Tahap 4: Bank Soal & Kisi-kisi")
    
    # Ambil data dari Modul Ajar secara otomatis (Sinkronisasi)
    d_modul = st.session_state.data_modul
    
    col_config1, col_config2, col_config3 = st.columns(3)
    with col_config1:
        jenjang = st.selectbox("Jenjang", ["SD", "SMP", "SMA", "SMK"], index=1)
    with col_config2:
        kelas_soal = st.text_input("Kelas", value=d_modul.get('kelas', ''))
    with col_config3:
        mapel_soal = st.text_input("Mata Pelajaran", value=d_modul.get('mapel', ''))

    st.subheader("📚 Manajemen Topik")
    # Validasi list_topik agar tidak error saat iterasi
    if not st.session_state.list_topik:
        st.session_state.list_topik = [{"nama": "", "jumlah": 5}]

    for i, item in enumerate(st.session_state.list_topik):
        c1, c2, c3 = st.columns([3, 1, 0.5])
        default_topik = item["nama"] if item["nama"] else (d_modul.get('topik', '') if i == 0 else "")
        st.session_state.list_topik[i]["nama"] = c1.text_input(f"Topik {i+1}", value=default_topik, key=f"topik_input_{i}")
        st.session_state.list_topik[i]["jumlah"] = c2.number_input(f"Jml Soal", min_value=1, value=item["jumlah"], key=f"jml_input_{i}")
        if c3.button("🗑️", key=f"del_topik_{i}"):
            if len(st.session_state.list_topik) > 1:
                st.session_state.list_topik.pop(i)
                st.rerun()

    if st.button("➕ Tambah Topik Baru"):
        st.session_state.list_topik.append({"nama": "", "jumlah": 5})
        st.rerun()

    # Form Pengaturan Soal
    with st.form("form_soal_expert"):
        st.write("### ⚙️ Pengaturan Jenis & Jumlah")
        f1, f2, f3 = st.columns(3)
        n_pg = f1.number_input("Jumlah PG", min_value=0, value=10)
        n_essay = f2.number_input("Jumlah Essay", min_value=0, value=5)
        n_bs = f3.number_input("Jumlah B/S", min_value=0, value=0)
        
        st.write("### 📊 Tingkat Kesulitan (%)")
        diff_col1, diff_col2, diff_col3 = st.columns(3)
        p_mudah = diff_col1.number_input("Mudah (C1-C2) %", value=30)
        p_sedang = diff_col2.number_input("Sedang (C3-C4) %", value=50)
        p_sulit = diff_col3.number_input("Sulit (C5-C6) %", value=20)
        
        st.write("### 🎨 Pengaturan Gambar")
        img_c1, img_c2 = st.columns(2)
        cb_gambar = img_c1.checkbox("Sertakan Prompt Gambar Detail", value=True)
        n_gambar = img_c1.number_input("Jumlah Soal Stimulus Gambar", min_value=0, value=2)
        gaya_gambar = img_c2.selectbox("Gaya Visual", ["Diagram Teknis", "Ilustrasi Edukasi", "Foto Realistik", "Sketsa", "Gambar style kartun 3d"])
        
        generate_btn = st.form_submit_button("🚀 Generate Bank Soal", use_container_width=True)
        
        if generate_btn:
            if not st.session_state.api_key:
                st.error("Masukkan API Key di Sidebar!")
            else:
                with st.spinner("AI sedang merancang soal berkualitas..."):
                    # Menyiapkan rincian topik untuk prompt
                    valid_topik = [t for t in st.session_state.list_topik if t["nama"].strip() != ""]
                    rincian_str = "\n".join([f"- {t['nama']}: {t['jumlah']} soal" for t in valid_topik])
                    
                    prompt_visual = ""
                    if cb_gambar and n_gambar > 0:
                        prompt_visual = f"\nSertakan {n_gambar} soal dengan [Gambar: Prompt: <deskripsi detail>] gaya {gaya_gambar}."

                    prompt_soal = (
                        f"""Anda adalah seorang spesialis evaluasi pendidikan. Buat naskah soal {jenjang} {mapel_soal} Kelas {kelas_soal}. yang disesuaikan dengan kaidah-kaidah penyusunan soal yang baik dan benar sebagai berikut:
                        1. Kaidah Substansi/Materi (Kesesuaian):
                             a. Sesuai Indikator: Soal harus mengukur perilaku dan materi yang ditetapkan dalam kisi-kisi.
                             b. Pilihan Jawaban Homogen: Semua pilihan jawaban (pengecoh) harus logis, masuk akal, dan homogen dari segi materi.
                             c. Satu Jawaban Benar: Hanya ada satu kunci jawaban yang benar untuk setiap soal.
                             d. Tidak SARA: Soal tidak boleh menyinggung isu SARA, politik, pornografi, atau kekerasan. 
                        2. Kaidah Konstruksi (Teknis Soal):
                             a. Pokok Soal Jelas: Pokok soal (stem) dirumuskan secara jelas, tegas, dan tidak menimbulkan penafsiran ganda.
                             b. Hindari Petunjuk Jawaban: Pokok soal jangan memberi petunjuk ke arah jawaban benar.
                             c. Negatif Ganda: Hindari penggunaan pernyataan yang bersifat negatif ganda.
                             d. Panjang Pilihan Jawaban: Panjang rumusan pilihan jawaban (pilihan ganda) harus relatif sama.
                             e. Pengecoh Berfungsi: Pengecoh (distractor) harus berfungsi, logis, dan dipilih oleh peserta didik yang kurang paham materi.
                             f. Grafik/Tabel Jelas: Gambar, grafik, tabel, atau diagram harus jelas dan berfungsi dalam soal. 
                        3. Kaidah Bahasa:
                             a. Bahasa Baku: Menggunakan bahasa Indonesia yang baik dan benar (baku) sesuai ejaan (EYD).
                             b. Komunikatif: Rumusan soal harus komunikatif dan mudah dipahami sesuai jenjang pendidikan peserta didik.
                             c. Tidak Ambigu: Kalimat soal tidak menimbulkan tafsiran ganda.
                             d. Bahasa Setempat: Hindari penggunaan bahasa atau istilah yang hanya berlaku di tempat tertentu (lokal/tabu). 
                        4. Kaidah Khusus: 
                             a. Jawaban Singkat: Kalimat harus dirumuskan agar jawaban yang dihasilkan benar-benar singkat dan jelas.
                             b. Uraian (Essay): Rumusan soal menggunakan kata tanya yang menuntut uraian, seperti: "mengapa", "jelaskan", "uraikan".
                             c. Pedoman Penskoran: Soal uraian wajib disertai dengan pedoman penskoran atau kunci jawaban.\n"""
                        f"Materi: {rincian_str}\n"
                        f"Komposisi: {n_pg} PG, {n_essay} Essay, {n_bs} B/S.\n"
                        f"Target: Mudah {p_mudah}%, Sedang {p_sedang}%, Sulit {p_sulit}%.\n"
                        f"{prompt_visual}\n"
                        f"Aturan: Jika SD/SMP opsi A-D, jika SMA/SMK opsi A-E. "
                        f"Cantumkan Level Kognitif di awal soal. Sertakan Kunci Jawaban."
                    )
                    
                    st.session_state.soal_result = call_gemini_ai(st.session_state.api_key, prompt_soal)
                    st.rerun()

    # [PERBAIKAN] Tampilkan hasil soal di luar form agar tombol kisi-kisi berfungsi
    if st.session_state.soal_result:
        st.markdown(f'<div class="ai-output-card">{st.session_state.soal_result}</div>', unsafe_allow_html=True)
        btn_soal_docx = create_formatted_docx(st.session_state.soal_result, f"Bank Soal {mapel_soal}")
        st.download_button("📥 Unduh Bank Soal (DOCX)", btn_soal_docx, f"Soal_{mapel_soal}.docx")

        st.divider()
        st.subheader("📋 Generator Kisi-kisi (BSKAP 046/2025)")
        if st.button("✨ Buat Kisi-kisi Otomatis", type="primary", use_container_width=True):
            with st.spinner("Memetakan soal ke CP BSKAP 046/2025..."):
                prompt_kisi = (
                    f"Buatlah TABEL kisi-kisi berdasarkan soal ini: {st.session_state.soal_result}. "
                    "Gunakan referensi BSKAP No. 046/H/KR/2025. Kolom: No, CP, Elemen, Indikator Soal, Level, Bentuk Soal."
                )
                st.session_state.kisikisi_result = call_gemini_ai(st.session_state.api_key, prompt_kisi)
                st.rerun()

        if st.session_state.kisikisi_result:
            st.markdown(f'<div class="ai-output-card">{st.session_state.kisikisi_result}</div>', unsafe_allow_html=True)
            btn_kisi_docx = create_formatted_docx(st.session_state.kisikisi_result, "Kisi-kisi Instrumen Penilaian")
            st.download_button("📥 Unduh Kisi-kisi (DOCX)", btn_kisi_docx, "Kisi_Kisi.docx")