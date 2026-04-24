import streamlit as st
import pandas as pd
import numpy as np
import re
import os
import shutil
import plotly.express as px
import matplotlib.pyplot as plt
from wordcloud import WordCloud, STOPWORDS

# Konfigurasi Halaman Web
st.set_page_config(page_title="Sentiment Dashboard MAN & MMN (Live)", page_icon="📊", layout="wide")

# ==========================================
# INJEKSI CSS UNTUK MENGUBAH TAMPILAN
# ==========================================
st.markdown("""
    <style>
    /* 1. Mengurangi ruang kosong di atas halaman UTAMA */
    .block-container {
        padding-top: 2.5rem !important; 
        padding-bottom: 1rem !important;
    }

    /* 2. KUNCI PERBAIKAN: Mengurangi ruang kosong di atas SIDEBAR */
    [data-testid="stSidebarUserContent"] {
        padding-top: 1rem !important;
    }
    [data-testid="stSidebar"] .block-container {
        padding-top: 1rem !important;
    }

    /* 3. Ukuran font Judul Utama (st.title) */
    h1 {
        font-size: 35px !important;
        margin-top: 0rem !important; /* Pastikan tetap 0 agar tidak terpotong */
        padding-top: 0rem !important;
    }
    
    /* 4. Ukuran font Header (st.header) */
    h2 {
        font-size: 26px !important;
    }
    
    /* 5. Ukuran font Subheader (st.subheader) */
    h3 {
        font-size: 20px !important;
    }
    
    /* 6. Ukuran font Teks Biasa / Info / Paragraf (st.write, st.info) */
    p {
        font-size: 16px !important;
    }
    
    /* 7. Khusus mengubah ukuran Header di Sidebar */
    [data-testid="stSidebar"] h2 {
        font-size: 24px !important;
        margin-top: -1rem !important; /* Menarik teks "Konfigurasi Analisis" sedikit lebih ke atas */
    }
    
    /* 8. Khusus mengubah ukuran Subheader di Sidebar */
    [data-testid="stSidebar"] h3 {
        font-size: 16px !important;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# BAGIAN HEADER & LOGO
# ==========================================
# Membuat 2 kolom: proporsi 1 untuk logo, proporsi 5 untuk judul agar pas
col_logo, col_title = st.columns([1, 5])

with col_logo:
    # Masukkan nama file gambar Anda di sini. 
    # Gunakan use_column_width=True agar ukurannya otomatis menyesuaikan kolom
    try:
        st.image("logo_MUN.png", use_container_width=True)
    except FileNotFoundError:
        st.error("File logo_MUN.png tidak ditemukan. Pastikan nama dan foldernya benar.")

with col_title:
    # Menggunakan HTML agar tampilan teks persis seperti referensi (2 baris atas bawah)
    st.markdown("""
        <h1 style='margin-bottom: 0px; padding-bottom: 0px;'>SENTIMENT ANALYSIS DASHBOARD</h1>
        <h3 style='margin-top: 0px; padding-top: 0px; margin-bottom: 0px; color: #333; font-weight: normal; line-height: 1.3;'>PT Makassar Metro Network<br>PT Makassar Airport Network
        </h3>
    """, unsafe_allow_html=True)

# ==========================================
# FUNGSI MEMBACA GOOGLE SHEETS
# ==========================================
@st.cache_data(ttl=300) # Data di-cache selama 5 menit agar tidak terus-menerus menarik data
def load_data_from_gsheets(url):
    try:
        # Mengubah URL agar mengekspor sebagai CSV
        csv_url = url.replace('/edit?usp=sharing', '/export?format=csv')
        csv_url = re.sub(r'\/edit#gid=\d+', '/export?format=csv', csv_url)
        df = pd.read_csv(csv_url)
        return df
    except Exception as e:
        st.error(f"❌ Gagal membaca data. Pastikan link benar dan aksesnya 'Anyone with the link'. Detail: {e}")
        return None


# ==========================================
# PERSIAPAN SISTEM & KAMUS (DIPINDAH KE ATAS)
# ==========================================
OUTPUT_DIR = "Hasil_Analisis_Sentimen_Live"
if not os.path.exists(OUTPUT_DIR): 
    os.makedirs(OUTPUT_DIR)

MUN_BLUE, MUN_RED, MUN_YELLOW = "#004B93", "#E30613", "#FFCC00"
COLOR_MAP = {"Positif": MUN_BLUE, "Netral": MUN_YELLOW, "Negatif": MUN_RED}

topic_mapping = {
    'Jalan tidak rata (berlubang, bergelombang, tambalan)': 'Infrastruktur & Kondisi Jalan',
    'Genangan air/banjir': 'Infrastruktur & Kondisi Jalan',
    'Kurangnya penerangan': 'Infrastruktur & Kondisi Jalan',
    'Pengembangan fasilitas, gerbang, dan jalur tol': 'Infrastruktur & Kondisi Jalan',
    'Kondisi Jalan Frontage': 'Infrastruktur & Kondisi Jalan',
    'Tarif mahal / Tol termahal': 'Tarif & Biaya',
    'Tol pendek / Tol terpendek': 'Tarif & Biaya',
    'Tarif & Diskon': 'Tarif & Biaya',
    'Mesin toll gate yang lawas/perlu diganti': 'Layanan & Sistem Operasional',
    'Penambahan gerbang': 'Layanan & Sistem Operasional',
    'Macet di area tol dan sekitar gerbang': 'Layanan & Sistem Operasional',
    'Layanan dan konten sosial media': 'Layanan & Sistem Operasional',
    'Layanan petugas lapangan': 'Layanan & Sistem Operasional',
    'Fitur NITA': 'Layanan & Sistem Operasional',
    'Struk elektronik': 'Layanan & Sistem Operasional',
    'Metode pembayaran': 'Layanan & Sistem Operasional',
    'Kecelakaan dan gangguan batu/benda asing di tol': 'Keamanan & Lalu Lintas',
    'Pengendara lain (lane hogger, dll)': 'Keamanan & Lalu Lintas',
    'Kemacetan di jalan arteri': 'Keamanan & Lalu Lintas',
    'Penjagaan kurang ketat': 'Keamanan & Lalu Lintas',
    'Dukungan dan doa': 'Interaksi & Lainnya',
    'Humor': 'Interaksi & Lainnya',
    'Interaksi pengguna': 'Interaksi & Lainnya',
    'Pengalaman menggunakan tol': 'Interaksi & Lainnya',
    'CSR': 'Interaksi & Lainnya',
    'Tidak spesifik': 'Tidak Spesifik'
}

# ==========================================
# SIDEBAR (MENU PENGATURAN DI SAMPING)
# ==========================================
with st.sidebar:
    st.header("Konfigurasi Analisis")
    
    st.subheader("1. Sumber Data")
    gsheets_url = st.text_input("Link Google Sheets:", placeholder="Tempel link yang sudah diset 'Anyone with the link' di sini...")
    
    # Placeholder untuk pesan sukses (muncul di bawah input URL)
    status_data = st.empty() 
    
    st.write("---")
    
    # Penomoran disesuaikan karena filter tanggal sudah dipindah ke Main Area
    st.subheader("2. Pengumuman Tarif")
    ada_penyesuaian_tarif = st.checkbox("Ada penyesuaian tarif dalam rentang ini?")
    tanggal_pengumuman = st.text_input("Tanggal Pengumuman (YYYY-MM-DD, pisahkan koma)", "2026-01-01, 2026-01-02")
    
    st.write("---")
    
    st.subheader("3. Tambah Topik Baru")
    
    with st.expander("Lihat Daftar Topik Spesifik"):
        st.caption("Daftar topik yang saat ini sudah terdaftar di sistem:")
        for existing_topic in sorted(topic_mapping.keys()):
            st.markdown(f"- {existing_topic}")
            
    topik_baru_spesifik = st.text_input("Topik Spesifik Baru (Opsional)")
    kategori_general = ["Infrastruktur & Kondisi Jalan", "Tarif & Biaya", "Layanan & Sistem Operasional", "Keamanan & Lalu Lintas", "Interaksi & Lainnya", "Tidak Spesifik"]
    topik_baru_general = st.selectbox("Masuk ke Kategori General:", kategori_general, index=5)
    
    st.write("---")
    
    st.subheader("4. Pengaturan Kata Buang")
    kata_buang_tambahan = st.text_area("Kata yang ingin dihilangkan dari Wordcloud (pisahkan koma):", "tol, makassar, min, jalan, fyp")

if topik_baru_spesifik.strip() != "":
    topic_mapping[topik_baru_spesifik.strip()] = topik_baru_general


# ==========================================
# AREA UTAMA: PROSES DATA
# ==========================================
if not gsheets_url:
    st.info("Silakan masukkan Link Google Sheets Anda di menu sebelah kiri (sidebar) untuk memulai analisis.")
else:
    # ----------------------------------------------------
    # FILTER RENTANG TANGGAL (Pindah ke Main Area)
    # KUNCI PERBAIKAN: Layout sejajar dengan Teks "Periode waktu"
    # ----------------------------------------------------
    st.write("<hr style='margin-top: 10px; margin-bottom: 15px;'>", unsafe_allow_html=True)
    
    # Membuat 4 kolom: 1 untuk label, 2 untuk input tanggal, 1 sisanya dibiarkan kosong agar tidak melebar
    col_label, col_d1, col_d2, col_blank = st.columns([1.5, 2, 2, 4.5])
    
    with col_label:
        # Menambahkan padding atas agar sejajar dengan input box
        st.markdown("<div style='padding-top: 32px; font-size: 16px; font-weight: bold; color: #333;'>Periode waktu</div>", unsafe_allow_html=True)
    
    with col_d1:
        tanggal_mulai = st.date_input("Tanggal mulai (slicer)")
        
    with col_d2:
        tanggal_selesai = st.date_input("Tanggal selesai (slicer)")
        
    st.write("<br>", unsafe_allow_html=True)
    # ----------------------------------------------------

    df_raw = load_data_from_gsheets(gsheets_url)
    
    if df_raw is not None:
        with st.spinner('Menarik data dari Google Sheets dan membuat visualisasi...'):
            
            # PREPROCESSING DASAR
            df = df_raw.dropna(subset=['text']).drop_duplicates(subset=['text'])
            
            if 'platform' in df.columns:
                df['platform'] = df['platform'].astype(str).str.strip().str.title().replace({'Tiktok': 'TikTok', 'Dm Instagram': 'DM Instagram'})
            
            # Konversi Tanggal dan Buang baris yang tidak memiliki tanggal valid
            df['date'] = pd.to_datetime(df['date'], format='%m/%d/%Y', errors='coerce')
            df = df.dropna(subset=['date'])
            
            # Filter Berdasarkan Input Tanggal Baru
            start_date = pd.to_datetime(tanggal_mulai)
            end_date = pd.to_datetime(tanggal_selesai)
            df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
            
            if df.empty:
                st.warning("⚠️ Tidak ada data sentimen yang ditemukan pada rentang tanggal tersebut.")
                st.stop()

            df['content_type'] = 'Konten Reguler'
            if ada_penyesuaian_tarif:
                try:
                    tgl_list = [pd.to_datetime(t.strip()).date() for t in tanggal_pengumuman.split(',')]
                    df.loc[df['date'].dt.date.isin(tgl_list), 'content_type'] = 'Pengumuman Tarif'
                except Exception as e:
                    st.warning("Peringatan: Format tanggal pengumuman salah.")

            df.to_csv(f"{OUTPUT_DIR}/1_Cleaned_Data.csv", index=False)

            # Mengirim pesan sukses ke placeholder di sidebar
            status_data.success(f"Berhasil menarik {len(df)} baris data (Periode: {tanggal_mulai.strftime('%d %b %Y')} - {tanggal_selesai.strftime('%d %b %Y')}).")

            # ----------------------------------------------------
            # KARTU RINGKASAN & PERSENTASE SENTIMEN
            # ----------------------------------------------------
            total_komentar = len(df)
            
            if 'usrnm_cmmnt' in df.columns:
                total_user = df['usrnm_cmmnt'].nunique()
            else:
                total_user = 0
                st.warning("⚠️ Kolom 'usrnm_cmmnt' tidak ditemukan di dataset untuk menghitung Unique User.")

            # Hitung persentase sentimen
            sent_counts = df['category'].value_counts(normalize=True) * 100
            pct_positif = sent_counts.get('Positif', 0)
            pct_netral = sent_counts.get('Netral', 0)
            pct_negatif = sent_counts.get('Negatif', 0)

            # Buat 5 kolom sejajar
            c1, c2, c3, c4, c5 = st.columns(5)
            
            # Desain CSS untuk meniru gambar referensi (Putih, border abu-abu, teks di tengah)
            card_css = "background-color: white; border: 1px solid #e1e8ed; padding: 20px 10px; border-radius: 8px; text-align: center; box-shadow: 1px 1px 5px rgba(0,0,0,0.04);"
            title_css = "margin: 0 0 10px 0; font-size: 14px; font-weight: bold; color: #14171a;"
            
            with c1:
                # Menggunakan warna biru cerah (ala Twitter) untuk metrik umum
                st.markdown(f'<div style="{card_css}"><p style="{title_css}">Total Komentar</p><h1 style="margin: 0; font-size: 36px; color: #00AEEF;">{total_komentar}</h1></div>', unsafe_allow_html=True)
            with c2:
                st.markdown(f'<div style="{card_css}"><p style="{title_css}">Unique User</p><h1 style="margin: 0; font-size: 36px; color: #00AEEF;">{total_user}</h1></div>', unsafe_allow_html=True)
            with c3:
                # Menggunakan warna dari COLOR_MAP untuk metrik sentimen
                st.markdown(f'<div style="{card_css}"><p style="{title_css}">Positif</p><h1 style="margin: 0; font-size: 36px; color: {MUN_BLUE};">{pct_positif:.1f}%</h1></div>', unsafe_allow_html=True)
            with c4:
                st.markdown(f'<div style="{card_css}"><p style="{title_css}">Netral</p><h1 style="margin: 0; font-size: 36px; color: {MUN_YELLOW};">{pct_netral:.1f}%</h1></div>', unsafe_allow_html=True)
            with c5:
                st.markdown(f'<div style="{card_css}"><p style="{title_css}">Negatif</p><h1 style="margin: 0; font-size: 36px; color: {MUN_RED};">{pct_negatif:.1f}%</h1></div>', unsafe_allow_html=True)

            st.write("<br>", unsafe_allow_html=True)
            # ----------------------------------------------------
            
            # VISUALISASI
            col1, col2 = st.columns(2)
            
            # V1. Distribusi Platform
            df['platform_group'] = df['platform'].replace({'DM Instagram': 'Instagram'})
            plat_count = df['platform_group'].value_counts().reset_index(name='Total')
            fig_p = px.bar(plat_count, x='platform_group', y='Total', title='Distribusi Komentar Per-Platform', text='Total', color_discrete_sequence=[MUN_BLUE])
            
            fig_p.update_traces(textposition='auto', cliponaxis=False)
            fig_p.update_layout(xaxis_title=None, yaxis_title=None, margin=dict(t=50))
            
            fig_p.write_html(f"{OUTPUT_DIR}/Chart_1_Platform.html")
            with col1: st.plotly_chart(fig_p, use_container_width=True)

            # V1.1 Distribusi Instagram (Komentar vs DM)
            df_ig = df[df['platform'].isin(['Instagram', 'DM Instagram'])].copy()
            if len(df_ig) > 0:
                df_ig['platform_detail'] = df_ig['platform'].replace({'Instagram': 'Komentar Instagram'})
                ig_count = df_ig['platform_detail'].value_counts().reset_index(name='Total')
                fig_ig = px.bar(ig_count, x='platform_detail', y='Total', title='Breakdown Instagram: Komentar vs DM', 
                                text='Total', color='platform_detail', 
                                color_discrete_map={'Komentar Instagram': MUN_BLUE, 'DM Instagram': '#5FA5EB'})
                
                fig_ig.update_traces(textposition='auto', cliponaxis=False)
                fig_ig.update_layout(xaxis_title=None, yaxis_title=None, legend_title_text='', margin=dict(t=50))
                
                fig_ig.write_html(f"{OUTPUT_DIR}/Chart_1.1_Instagram_Breakdown.html")
                with col2: st.plotly_chart(fig_ig, use_container_width=True)
                    
            # V3. Tren Sentimen (Stacked Bar Chart)
            df_trend = df.groupby([df['date'].dt.date, 'category']).size().reset_index(name='Total')
            
            fig_trend = px.bar(df_trend, x='date', y='Total', color='category', title='Tren Sentimen Harian', color_discrete_map=COLOR_MAP)
            fig_trend.update_layout(xaxis_title=None, yaxis_title=None, legend_title_text='')
            
            fig_trend.write_html(f"{OUTPUT_DIR}/Chart_3_Sentiment_Trend.html")
            st.plotly_chart(fig_trend, use_container_width=True)
            
            # V4. Konten Reguler vs Pengumuman
            if ada_penyesuaian_tarif:
                df_comp = df.groupby(['content_type', 'category']).size().reset_index(name='Total')
                fig_comp = px.bar(df_comp, x='content_type', y='Total', color='category', 
                                  barmode='group', title='Perbandingan: Konten Reguler vs Pengumuman Tarif', 
                                  text='Total', color_discrete_map=COLOR_MAP)
                
                fig_comp.update_traces(textposition='auto', cliponaxis=False)
                fig_comp.update_layout(
                    xaxis_title=None, 
                    yaxis_title=None, 
                    legend_title_text='',
                    margin=dict(t=50) 
                )
                
                fig_comp.write_html(f"{OUTPUT_DIR}/Chart_4_Comparison.html")
                st.plotly_chart(fig_comp, use_container_width=True)

            # V5. Analisis Topik
            def split_topics(t): return [i.strip().strip('"') for i in re.split(r',(?=(?:[^"]*"[^"]*")*[^"]*$)', str(t)) if i.strip()]
            df['topic_list'] = df['topic'].apply(split_topics)
            df_ex = df.explode('topic_list')
            df_ex = df_ex[df_ex['topic_list'].notna() & (df_ex['topic_list'] != '')]
            df_ex['general_topic'] = df_ex['topic_list'].map(topic_mapping).fillna('Tidak Spesifik')
            df_ex.to_csv(f"{OUTPUT_DIR}/2_Exploded_Topic_Data.csv", index=False)

            st.write("---")
            st.write("### Analisis Topik Berdasarkan Sentimen")

            def wrap_text_25(text):
                text = str(text)
                if len(text) > 25:
                    spaces = [i for i, c in enumerate(text) if c == ' ']
                    if spaces:
                        mid = len(text) / 2
                        best_space = min(spaces, key=lambda x: abs(x - mid))
                        return text[:best_space] + '<br>' + text[best_space+1:]
                return text

            for cat in df_ex['category'].unique():
                sub = df_ex[df_ex['category'] == cat]
                if len(sub) > 0:
                    col_g, col_s = st.columns([2, 3])
                    
                    g_count = sub['general_topic'].value_counts().reset_index(name='Total')
                    s_count = sub['topic_list'].value_counts().reset_index(name='Total')
                    
                    g_count['label_general'] = g_count['general_topic'].str.replace(' & ', ' &<br>')
                    s_count['label_spesifik'] = s_count['topic_list'].apply(wrap_text_25)
                    
                    tinggi_grafik_g = max(200, 150 + (len(g_count) * 33))
                    tinggi_grafik_s = max(200, 150 + (len(s_count) * 33))
                    
                    # General
                    fig_g = px.bar(g_count, x='Total', y='label_general', orientation='h', text='Total', color_discrete_sequence=[COLOR_MAP.get(cat, 'gray')])
                    fig_g.update_layout(
                        title={'text': f'Topik General - {cat}', 'x': 0.0, 'xanchor': 'left'}, 
                        yaxis={'categoryorder':'total ascending', 'title': '', 'tickfont': {'size': 10.5}},
                        xaxis={'title': ''},
                        height=tinggi_grafik_g
                    )
                    fig_g.update_traces(textfont_size=10)
                    
                    fig_g.write_html(f"{OUTPUT_DIR}/Chart_5_General_Topic_{cat}.html")
                    with col_g: st.plotly_chart(fig_g, use_container_width=True)

                    # Spesifik
                    fig_s = px.bar(s_count, x='Total', y='label_spesifik', orientation='h', text='Total', color_discrete_sequence=[COLOR_MAP.get(cat, 'gray')])
                    fig_s.update_layout(
                        title={'text': f'Topik Spesifik - {cat}', 'x': 0.0, 'xanchor': 'left'}, 
                        yaxis={'categoryorder':'total ascending', 'title': '', 'tickfont': {'size': 10.5}}, 
                        xaxis={'title': ''},
                        height=tinggi_grafik_s
                    )
                    fig_s.update_traces(textfont_size=10)
                    
                    fig_s.write_html(f"{OUTPUT_DIR}/Chart_6_Specific_Topic_{cat}.html")
                    with col_s: st.plotly_chart(fig_s, use_container_width=True)
                        
            # V6. Wordcloud
            st.write("---")
            st.write("### Wordcloud Sentimen")
            
            all_stopwords = set() 
            
            base_exclusions = {
                '2x', '3x', '5k', '89xx', 'acar', 'acara', 'ada', 'adalah', 'adanya', 
                'adik', 'admin', 'aja', 'ajang', 'akan', 'alasan', 'allah', 'ambil', 
                'ancinikko', 'anda', 'anjay', 'anuu', 'apa', 'apalagi', 'apk', 'arah', 
                'area', 'arus', 'atas', 'atau', 'auto', 'bagian', 'bahwa', 'baik2', 
                'baku', 'balkon', 'banget', 'banyak', 'banyakji', 'baru', 'barusan', 
                'batas', 'bawa', 'begini', 'begitu', 'belakangan', 'beli', 'belum', 
                'benarko', 'berada', 'berperawakan', 'bersama', 'berulahko', 'betul', 
                'bgt', 'bgtu', 'biar', 'biasanya', 'bikin', 'bisa', 'bisaji', 
                'bisajikah', 'bkn', 'boss', 'bro', 'bsa', 'buat', 'bukan', 'cara', 
                'd', 'dah', 'dahhh', 'dalam', 'dan', 'dari', 'datang', 'dapat', 'dd', 
                'dengan', 'depan', 'di', 'dibilang', 'didapat', 'dimna', 'dipahami', 
                'disimak', 'dlu', 'dong', 'dpatji', 'dr', 'dri', 'dudui', 'fungsinya', 
                'fyp', 'ga', 'gak', 'gampng', 'gasnya', 'gel', 'gemoy', 'gimana', 
                'gini', 'gk', 'goyah', 'guys', 'haah', 'hadir', 'hampir', 'hanya', 
                'hari', 'heeh', 'heheee', 'hendak', 'hingga', 'humas_ditlantaspoldasulsel', 
                'ia', 'id', 'indonesia', 'info', 'informasi', 'infonya', 
                'infotolmakassar', 'ini', 'ir', 'itu', 'iya', 'jadi', 'jalan', 'jam', 
                'jan', 'jangan', 'jatanras_mksr', 'jd', 'jeli', 'jg', 'jgn', 'ji', 
                'jkt', 'jln', 'juga', 'justru', 'ka', 'kaau', 'kah', 'kak', 'kalau', 
                'kali', 'kalian', 'kalo', 'kami', 'kampungan', 'kan', 'kanan', 'kanda', 
                'kapan', 'karena', 'karna', 'katanya', 'kaumi', 'kaya', 'kdng', 'ke', 
                'kedengaran', 'kelakuan', 'kembali', 'kenapa', 'kepada', 'kerjaan', 
                'keterangan', 'ki', 'kidc', 'kini', 'kita', 'klo', 'km', 'ko', 
                'kodong', 'kok', 'krna', 'ku', 'kurang', 'kyk', 'lagi', 'lah', 'lain', 
                'lalang', 'lalu', 'langkahnya', 'lebih', 'lewat', 'liat', 'lima', 
                'luar', 'lupa', 'makassar', 'makassarkah', 'makanya', 'mako', 'maksd', 
                'mamo', 'mana', 'manapun', 'maros', 'masa', 'masih', 'masing2', 'mau', 
                'maw', 'max', 'melaju', 'melakukan', 'melalui', 'melihat', 'memang', 
                'menanggung', 'menjalankan', 'menjadi', 'menurut', 'mereka', 
                'merupakan', 'meski', 'mi', 'mikir', 'min', 'mko', 'mmg', 'mobilnya', 
                'mohon', 'msh', 'mslh', 'mulai', 'na', 'nai', 'namun', 'natau', 'nda', 
                'ndada', 'ndak', 'news', 'ngampung', 'ni', 'nih', 'nu', 'nupikir', 
                'nusantara', 'nya', 'ok', 'oleh', 'om', 'orang', 'org', 'org2', 'orng', 
                'pada', 'paham', 'pahami', 'paling', 'panjang', 'pas', 'pasti', 
                'pembangunan', 'penggunaan', 'penyebab', 'perasaanku', 'pernah', 
                'persoalan', 'pikir', 'pinggir', 'potong', 'project', 'pun', 'punya', 
                'rasa', 'ri', 'saat', 'sabtu', 'saja', 'sambil', 'sampe', 'sampai', 
                'sangat', 'saya', 'sebagai', 'sebelum', 'secara', 'sedeng', 'sedsng', 
                'sejumlah', 'sekali', 'seksi', 'sekitar', 'selalu', 'semakin', 
                'sementara', 'semoga', 'semua', 'semuaji', 'seorang', 'seperti', 
                'sering', 'serta', 'set', 'setelah', 'setidak', 'setiap', 'siapa', 
                'soal', 'sok', 'sotr', 'sudah', 'sudahmi', 'supaya', 'suryadi', 
                'sutami', 'sy', 'tabe', 'tahun', 'tak', 'talliwa', 'tapi', 'tau', 
                'tauji', 'td', 'tdk', 'telah', 'tempat', 'tengah', 'tentang', 
                'tepatnya', 'terasa', 'terhadap', 'terimakasih', 'terjadi', 'terkait', 
                'terlihat', 'ternyata', 'tersebut', 'tertop', 'terus', 'tetap', 'th', 
                'tiap', 'tidak', 'tindak', 'tol', 'toll', 'tolo', 'tp', 'tpi', 'trus', 
                'tuh', 'ucap', 'umum', 'unit', 'untuk', 'wajib', 'waktunya', 'ya', 
                'yaa', 'yaaa', 'yah', 'yang', 'yg'
            }
            
            all_stopwords.update(base_exclusions)

            if kata_buang_tambahan.strip() != "":
                user_words = [w.strip().lower() for w in kata_buang_tambahan.split(',') if w.strip()]
                all_stopwords.update(user_words)

            cols_wc = st.columns(len(df['category'].unique()))
            for i, cat in enumerate(df['category'].unique()):
                sub = df[df['category'] == cat]
                if len(sub) > 0:
                    text_data = " ".join(str(comment) for comment in sub.text).lower()
                    
                    wc_obj = WordCloud(
                        width=800, 
                        height=400, 
                        background_color='white', 
                        stopwords=all_stopwords,
                        colormap='viridis',
                        collocations=False
                    ).generate(text_data)
                    
                    fig_wc, ax = plt.subplots(figsize=(10, 5))
                    ax.imshow(wc_obj, interpolation='bilinear')
                    ax.set_title(f"Kata Kunci Sentimen {cat}", fontsize=15, fontweight='bold')
                    ax.axis("off")
                    fig_wc.savefig(f"{OUTPUT_DIR}/Chart_7_Wordcloud_{cat}.png", bbox_inches='tight')
                    with cols_wc[i]: st.pyplot(fig_wc)
                    plt.close(fig_wc)
                    

            # ZIP & DOWNLOAD
            shutil.make_archive("Dashboard_Sentimen_MUN_Live", 'zip', OUTPUT_DIR)
            
            st.write("---")
            st.info("Seluruh visualisasi dan Data Bersih (CSV) telah siap diunduh.")
            
            with open("Dashboard_Sentimen_MUN_Live.zip", "rb") as fp:
                st.download_button(
                    label="⬇️ Unduh Visualisasi & Data (ZIP)",
                    data=fp,
                    file_name="Dashboard_Sentimen_MUN_Live.zip",
                    mime="application/zip"
                )
