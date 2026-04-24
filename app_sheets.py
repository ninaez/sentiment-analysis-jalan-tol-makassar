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
st.set_page_config(page_title="Dashboard Sentimen MAN & MMN (Live)", page_icon="📊", layout="wide")

# ==========================================
# INJEKSI CSS UNTUK MENGUBAH UKURAN FONT
# ==========================================
st.markdown("""
    <style>
    /* 1. Ukuran font Judul Utama (st.title) */
    h1 {
        font-size: 34px !important;
    }
    
    /* 2. Ukuran font Header (st.header) */
    h2 {
        font-size: 26px !important;
    }
    
    /* 3. Ukuran font Subheader (st.subheader) */
    h3 {
        font-size: 20px !important;
    }
    
    /* 4. Ukuran font Teks Biasa / Info / Paragraf (st.write, st.info) */
    p {
        font-size: 16px !important;
    }
    
    /* 5. Khusus mengubah ukuran Header di Sidebar */
    [data-testid="stSidebar"] h2 {
        font-size: 24px !important;
    }
    
    /* 6. Khusus mengubah ukuran Subheader di Sidebar */
    [data-testid="stSidebar"] h3 {
        font-size: 16px !important;
    }
    </style>
""", unsafe_allow_html=True)

st.title("PROGRAM SENTIMENT ANALYSIS JALAN TOL MAKASSAR")

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
# SIDEBAR (MENU PENGATURAN DI SAMPING)
# ==========================================
with st.sidebar:
    st.header("Konfigurasi Analisis")
    
    st.subheader("1. Sumber Data")
    gsheets_url = st.text_input("Link Google Sheets:", placeholder="Tempel link yang sudah diset 'Anyone with the link' di sini...")
    
    st.write("---")
    
    st.subheader("2. Filter Rentang Waktu")
    tanggal_mulai = st.date_input("Tanggal Mulai")
    tanggal_selesai = st.date_input("Tanggal Selesai")
    
    st.write("---")
    
    st.subheader("3. Pengumuman Tarif")
    ada_penyesuaian_tarif = st.checkbox("Ada penyesuaian tarif dalam rentang ini?")
    tanggal_pengumuman = st.text_input("Tanggal Pengumuman (YYYY-MM-DD, pisahkan koma)", "2026-01-01, 2026-01-02")
    
    st.write("---")
    
    st.subheader("4. Tambah Topik Baru")
    topik_baru_spesifik = st.text_input("Topik Spesifik Baru (Opsional)")
    kategori_general = ["Infrastruktur & Kondisi Jalan", "Tarif & Biaya", "Layanan & Sistem Operasional", "Keamanan & Lalu Lintas", "Interaksi & Lainnya", "Tidak Spesifik"]
    topik_baru_general = st.selectbox("Masuk ke Kategori General:", kategori_general, index=5)
    
    st.write("---")
    
    st.subheader("5. Pengaturan Kata Buang")
    kata_buang_tambahan = st.text_area("Kata yang ingin dihilangkan dari Wordcloud (pisahkan koma):", "tol, makassar, min, jalan, fyp")

# ==========================================
# PERSIAPAN SISTEM & KAMUS
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

if topik_baru_spesifik.strip() != "":
    topic_mapping[topik_baru_spesifik.strip()] = topik_baru_general

# ==========================================
# AREA UTAMA: PROSES DATA
# ==========================================
if not gsheets_url:
    st.info("Silakan masukkan Link Google Sheets Anda di menu sebelah kiri (sidebar) untuk memulai analisis.")
else:
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
            
            # ----------------------------------------------------
            # FILTER RENTANG TANGGAL (Slicer)
            # ----------------------------------------------------
            # Konversi input date st.date_input ke format datetime pandas
            start_date = pd.to_datetime(tanggal_mulai)
            end_date = pd.to_datetime(tanggal_selesai)
            
            # Terapkan filter
            df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
            
            if df.empty:
                st.warning("⚠️ Tidak ada data sentimen yang ditemukan pada rentang tanggal tersebut.")
                st.stop() # Hentikan proses jika data kosong
            # ----------------------------------------------------

            df['content_type'] = 'Konten Reguler'
            if ada_penyesuaian_tarif:
                try:
                    tgl_list = [pd.to_datetime(t.strip()).date() for t in tanggal_pengumuman.split(',')]
                    df.loc[df['date'].dt.date.isin(tgl_list), 'content_type'] = 'Pengumuman Tarif'
                except Exception as e:
                    st.warning("Peringatan: Format tanggal pengumuman salah.")

            df.to_csv(f"{OUTPUT_DIR}/1_Cleaned_Data.csv", index=False)

            st.success(f"Berhasil menarik {len(df)} baris data dari Google Sheets (Periode: {tanggal_mulai.strftime('%d %b %Y')} - {tanggal_selesai.strftime('%d %b %Y')}).")
            
            # VISUALISASI
            col1, col2 = st.columns(2)
            
            # V1. Distribusi Platform
            df['platform_group'] = df['platform'].replace({'DM Instagram': 'Instagram'})
            plat_count = df['platform_group'].value_counts().reset_index(name='Total')
            fig_p = px.bar(plat_count, x='platform_group', y='Total', title='Distribusi Komentar Per-Platform', text='Total', color_discrete_sequence=[MUN_BLUE])
            
            # KUNCI PERBAIKAN: Menghilangkan judul sumbu X dan Y
            fig_p.update_layout(xaxis_title=None, yaxis_title=None)
            
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
                
                # KUNCI PERBAIKAN: Tambahkan legend_title_text='' di sini
                fig_ig.update_layout(xaxis_title=None, yaxis_title=None, legend_title_text='')
                
                fig_ig.write_html(f"{OUTPUT_DIR}/Chart_1.1_Instagram_Breakdown.html")
                with col2: st.plotly_chart(fig_ig, use_container_width=True)
                    
            # V2. Distribusi Sentimen
            sent_count = df['category'].value_counts().reset_index(name='Total')
            sent_count['Legend_Label'] = sent_count['category'] + ' (' + sent_count['Total'].astype(str) + ')'
            DYNAMIC_COLOR_MAP = {row['Legend_Label']: COLOR_MAP.get(row['category'], 'gray') for idx, row in sent_count.iterrows()}
            
            fig_pie = px.pie(sent_count, names='Legend_Label', values='Total', title='Persentase Sentimen Keseluruhan', 
                             color='Legend_Label', color_discrete_map=DYNAMIC_COLOR_MAP, hole=0.3)
            fig_pie.update_traces(textinfo='percent', textfont_size=14, hovertemplate='%{label}<br>Persentase: %{percent}<extra></extra>')
            fig_pie.update_layout(legend_title_text='Kategori Sentimen (Total)')
            fig_pie.write_html(f"{OUTPUT_DIR}/Chart_2_Sentiment_Pie.html")
            st.plotly_chart(fig_pie, use_container_width=True)

            # V3. Tren Sentimen
            df_trend = df.groupby([df['date'].dt.date, 'category']).size().reset_index(name='Total')
            fig_line = px.line(df_trend, x='date', y='Total', color='category', title='Tren Sentimen Harian', color_discrete_map=COLOR_MAP, markers=True)
            
            # KUNCI PERBAIKAN: Menghilangkan judul sumbu X, sumbu Y, dan judul legenda
            fig_line.update_layout(xaxis_title=None, yaxis_title=None, legend_title_text='')
            
            fig_line.write_html(f"{OUTPUT_DIR}/Chart_3_Sentiment_Trend.html")
            st.plotly_chart(fig_line, use_container_width=True)
            
            # V4. Konten Reguler vs Pengumuman
            if ada_penyesuaian_tarif:
                df_comp = df.groupby(['content_type', 'category']).size().reset_index(name='Total')
                fig_comp = px.bar(df_comp, x='content_type', y='Total', color='category', 
                                  barmode='group', title='Perbandingan: Konten Reguler vs Pengumuman Tarif', 
                                  text='Total', color_discrete_map=COLOR_MAP)
                
                # KUNCI PERBAIKAN: 
                # 1. 'auto' akan menaruh angka di dalam jika cukup, dan di luar jika sempit.
                # 2. 'cliponaxis=False' memastikan angka di luar tidak terpotong garis bingkai.
                fig_comp.update_traces(textposition='auto', cliponaxis=False)
                
                # Menghilangkan judul sumbu X, sumbu Y, dan judul legenda
                fig_comp.update_layout(
                    xaxis_title=None, 
                    yaxis_title=None, 
                    legend_title_text='',
                    # Memastikan margin atas cukup jika angka pindah ke luar bar paling tinggi
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

            # Definisikan fungsi wrap di luar loop agar lebih efisien
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
                        # KUNCI PERBAIKAN: Menghilangkan judul sumbu X ('Total')
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
                        # KUNCI PERBAIKAN: Menghilangkan judul sumbu X ('Total')
                        xaxis={'title': ''},
                        height=tinggi_grafik_s
                    )
                    fig_s.update_traces(textfont_size=10)
                    
                    fig_s.write_html(f"{OUTPUT_DIR}/Chart_6_Specific_Topic_{cat}.html")
                    with col_s: st.plotly_chart(fig_s, use_container_width=True)
                        
            # V6. Wordcloud
            st.write("---")
            st.write("### Wordcloud Sentimen")
            custom_exclusions = {'2x', '89xx', 'acar', 'ada', 'adanya', 'aja', 'akan', 'ancinikko', 'anjay', 
                                 'anuu', 'apa', 'apk', 'arah', 'arus', 'atau', 'auto', 'bagian', 'bahwa', 
                                 'baik2', 'baku', 'banget', 'banyak', 'banyakji', 'baru', 'barusan', 'batas', 
                                 'bawa', 'begini', 'benarko', 'berada', 'bersama', 'berulahko', 'bgt', 'bgtu', 
                                 'biar', 'bikin', 'bisa', 'bisaji', 'bisajikah', 'bkn', 'boss', 'bro', 'bsa', 
                                 'bukan', 'cara', 'd', 'dah', 'dahhh', 'dalam', 'dan', 'dari', 'dd', 'dengan', 
                                 'di', 'dimna', 'dipahami', 'disimak', 'dlu', 'dpatji', 'dr', 'dri', 'dudui', 
                                 'fyp', 'gak', 'gampng', 'gel', 'gimana', 'gini', 'gk', 'guys', 'haah', 
                                 'hampir', 'hanya', 'hari', 'heeh', 'heheee', 'hingga', 'ia', 'id', 'info', 
                                 'informasi', 'infotolmakassar', 'ini', 'ir', 'itu', 'jadi', 'jalan', 'jam', 
                                 'jan', 'jangan', 'jd', 'jeli', 'jg', 'jgn', 'ji', 'jkt', 'jln', 'juga', 
                                 'justru', 'ka', 'kaau', 'kah', 'kak', 'kalau', 'kali', 'kalo', 'kampungan', 
                                 'kan', 'kanda', 'kapan', 'karena', 'karna', 'katanya', 'kaumi', 'kaya', 
                                 'kdng', 'ke', 'kenapa', 'kepada', 'keterangan', 'ki', 'kidc', 'kini', 'klo', 
                                 'ko', 'kodong', 'kok', 'krna', 'ku', 'kyk', 'lagi', 'lah', 'lain', 'lalang', 
                                 'lalu', 'lebih', 'lewat', 'liat', 'lima', 'makassar', 'makassarkah', 
                                 'makanya', 'mako', 'maksd', 'mamo', 'mana', 'maros', 'masa', 'masih', 
                                 'masing2', 'mau', 'maw', 'melakukan', 'melalui', 'memang', 'menjalankan', 
                                 'menjadi', 'mereka', 'merupakan', 'meski', 'mi', 'min', 'mko', 'mmg', 'msh', 
                                 'mslh', 'na', 'nai', 'namun', 'natau', 'nda', 'ndada', 'ndak', 'news', 
                                 'ngampung', 'ni', 'nih', 'nu', 'nupikir', 'nusantara', 'nya', 'ok', 'oleh', 
                                 'om', 'orang', 'org2', 'orng', 'pada', 'pas', 'pasti', 'pembangunan', 
                                 'penyebab', 'pernah', 'pinggir', 'potong', 'pun', 'punya', 'ri', 'saat', 
                                 'saja', 'sambil', 'sampe', 'sangat', 'saya', 'sebelum', 'sedeng', 'sedsng', 
                                 'sejumlah', 'sekali', 'seksi', 'sekitar', 'selalu', 'sementara', 'semoga', 
                                 'semua', 'semuaji', 'seorang', 'sering', 'serta', 'setelah', 'soal', 'sok', 
                                 'sotr', 'sudah', 'sudahmi', 'supaya', 'suryadi', 'sy', 'tabe', 'tahun', 'tak', 
                                 'talliwa', 'tau', 'tauji', 'td', 'tdk', 'tempat', 'tengah', 'tepatnya', 
                                 'terasa', 'terhadap', 'terimakasih', 'terjadi', 'terkait', 'ternyata', 
                                 'tersebut', 'terus', 'th', 'tiap', 'tidak', 'tol', 'toll', 'tolo', 'tp', 
                                 'tpi', 'trus', 'tuh', 'ucap', 'umum', 'untuk', 'ya', 'yaa', 'yaaa', 'yah', 
                                 'yang', 'yg'
                                }
            
            if kata_buang_tambahan.strip() != "":
                user_stopwords = {kata.strip().lower() for kata in kata_buang_tambahan.split(',') if kata.strip() != ""}
                custom_exclusions = custom_exclusions.union(user_stopwords)

            all_stopwords = STOPWORDS.union(custom_exclusions)
            
            cols_wc = st.columns(len(df['category'].unique()))
            for i, cat in enumerate(df['category'].unique()):
                sub = df[df['category'] == cat]
                if len(sub) > 0:
                    text_data = " ".join(str(comment) for comment in sub.text).lower()
                    wc = WordCloud(width=800, height=400, background_color='white', stopwords=all_stopwords, colormap='viridis').generate(text_data)
                    
                    fig_wc, ax = plt.subplots(figsize=(10, 5))
                    ax.imshow(wc, interpolation='bilinear')
                    ax.set_title(f"Kata Kunci Sentimen {cat}", fontsize=15, fontweight='bold')
                    ax.axis("off")
                    fig_wc.savefig(f"{OUTPUT_DIR}/Chart_7_Wordcloud_{cat}.png", bbox_inches='tight')
                    with cols_wc[i]: st.pyplot(fig_wc)

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
