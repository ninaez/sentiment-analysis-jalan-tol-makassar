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
st.set_page_config(page_title="Dashboard Sentimen MUN", page_icon="📊", layout="wide")
st.title("⚙️ PROGRAM SENTIMENT ANALYSIS INTERAKTIF (PT MARGAUTAMA NUSANTARA)")

# ==========================================
# SIDEBAR (MENU PENGATURAN DI SAMPING)
# ==========================================
with st.sidebar:
    st.header("⚙️ Pengaturan Analisis")
    
    st.subheader("1. Pengumuman Tarif")
    ada_penyesuaian_tarif = st.checkbox("Ada penyesuaian tarif?")
    tanggal_pengumuman = st.text_input("Tanggal Pengumuman (YYYY-MM-DD, pisahkan koma)", "2026-04-01, 2026-03-05")
    
    st.subheader("2. Tambah Topik Baru")
    topik_baru_spesifik = st.text_input("Topik Spesifik Baru (Opsional)")
    kategori_general = ["Infrastruktur & Kondisi Jalan", "Tarif & Biaya", "Layanan & Sistem Operasional", "Keamanan & Lalu Lintas", "Interaksi & Lainnya", "Tidak Spesifik"]
    topik_baru_general = st.selectbox("Masuk ke Kategori General:", kategori_general, index=5)
    
    st.subheader("3. Pengaturan Kata Buang (Wordcloud)")
    kata_buang_tambahan = st.text_area("Kata yang ingin dihilangkan (pisahkan koma):", "tol, makassar, min, jalan, fyp")

# ==========================================
# PERSIAPAN SISTEM & KAMUS
# ==========================================
OUTPUT_DIR = "Hasil_Analisis_Sentimen"
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
# AREA UPLOAD & PROSES DATA
# ==========================================
st.write("### 🚀 Silakan unggah file data sentimen Anda (.csv)")
uploaded_file = st.file_uploader("", type=['csv'])

if uploaded_file is not None:
    # Membaca data
    df = pd.read_csv(uploaded_file)
    
    with st.spinner('Memproses data dan membuat visualisasi...'):
        # PREPROCESSING
        df = df.dropna(subset=['text']).drop_duplicates(subset=['text'])
        
        if 'platform' in df.columns:
            df['platform'] = df['platform'].astype(str).str.strip().str.title().replace({'Tiktok': 'TikTok', 'Dm Instagram': 'DM Instagram'})
        
        df['date'] = pd.to_datetime(df['date'], format='%m/%d/%Y', errors='coerce')
        
        df['content_type'] = 'Konten Reguler'
        if ada_penyesuaian_tarif:
            try:
                tgl_list = [pd.to_datetime(t.strip()).date() for t in tanggal_pengumuman.split(',')]
                df.loc[df['date'].dt.date.isin(tgl_list), 'content_type'] = 'Pengumuman Tarif'
            except Exception as e:
                st.warning("Peringatan: Format tanggal pengumuman salah.")

        df.to_csv(f"{OUTPUT_DIR}/1_Cleaned_Data.csv", index=False)

        st.success("✅ Data berhasil diproses! Berikut adalah hasil visualisasinya:")
        
        # VISUALISASI
        col1, col2 = st.columns(2)
        
        # V1. Distribusi Platform
        df['platform_group'] = df['platform'].replace({'DM Instagram': 'Instagram'})
        plat_count = df['platform_group'].value_counts().reset_index(name='Total')
        fig_p = px.bar(plat_count, x='platform_group', y='Total', title='Distribusi Komentar Per-Platform', text='Total', color_discrete_sequence=[MUN_BLUE])
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
        fig_line.write_html(f"{OUTPUT_DIR}/Chart_3_Sentiment_Trend.html")
        st.plotly_chart(fig_line, use_container_width=True)

        # V4. Konten Reguler vs Pengumuman
        if ada_penyesuaian_tarif:
            df_comp = df.groupby(['content_type', 'category']).size().reset_index(name='Total')
            fig_comp = px.bar(df_comp, x='content_type', y='Total', color='category', barmode='group', title='Perbandingan: Konten Reguler vs Pengumuman Tarif', text='Total', color_discrete_map=COLOR_MAP)
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

        for cat in df_ex['category'].unique():
            sub = df_ex[df_ex['category'] == cat]
            if len(sub) > 0:
                col_g, col_s = st.columns(2)
                
                # General
                g_count = sub['general_topic'].value_counts().reset_index(name='Total')
                fig_g = px.bar(g_count, x='Total', y='general_topic', orientation='h', title=f'Topik General - {cat}', text='Total', color_discrete_sequence=[COLOR_MAP.get(cat, 'gray')])
                fig_g.update_layout(yaxis={'categoryorder':'total ascending'})
                fig_g.write_html(f"{OUTPUT_DIR}/Chart_5_General_Topic_{cat}.html")
                with col_g: st.plotly_chart(fig_g, use_container_width=True)

                # Spesifik
                s_count = sub['topic_list'].value_counts().reset_index(name='Total')
                fig_s = px.bar(s_count, x='Total', y='topic_list', orientation='h', title=f'Topik Spesifik - {cat}', text='Total', color_discrete_sequence=[COLOR_MAP.get(cat, 'gray')])
                fig_s.update_layout(yaxis={'categoryorder':'total ascending'}, height=max(400, len(s_count)*25))
                fig_s.write_html(f"{OUTPUT_DIR}/Chart_6_Specific_Topic_{cat}.html")
                with col_s: st.plotly_chart(fig_s, use_container_width=True)

        # V6. Wordcloud
        st.write("---")
        st.write("### Wordcloud Sentimen")
        custom_exclusions = {'tol', 'jalan', 'dan', 'di', 'lagi', 'makassar', 'dalam', 'yang', 'lewat',
                         'nusantara', 'min', 'kdng', 'fyp', 'guys', 'untuk', 'maros', 'merupakan',
                         'ini', 'itu', 'ke', 'dari', 'ada', 'sudah', 'infotolmakassar', 'tdk', 'toll',
                         'nya', 'info', 'banyak', 'akan', 'kalau', 'pada', 'gak', 'juga', 'tidak', 'mau',
                         'terimakasih', 'klo', 'saya', 'biar', 'bsa', 'mamo', 'kak', 'suryadi', 'mana',
                         'lain', 'penyebab', 'memang', 'tengah', 'orng', 'sy', 'ya', 'arah', 'jam', 'selalu',
                         'apa', 'ji', 'justru', 'menjalankan', 'ternyata', 'hanya', 'news', 'bisajikah', 'ni',
                         'pas', 'hari', 'na', 'seorang', 'kan', 'oleh', 'tengah', 'masih', 'om', 'lebih',
                         'kah', 'tiap', 'makassarkah', 'tpi', 'soal', 'semoga', 'keterangan', 'mslh', 'sekali',
                         'tolo', 'sekali', 'bahwa', 'bawa', 'umum', 'selalu', 'jangan'}
        
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
        shutil.make_archive("Dashboard_Sentimen_MUN", 'zip', OUTPUT_DIR)
        
        st.write("---")
        st.info("✅ Seluruh grafik interaktif (HTML) dan Data Bersih (CSV) telah siap diunduh.")
        
        with open("Dashboard_Sentimen_MUN.zip", "rb") as fp:
            st.download_button(
                label="⬇️ Unduh Dashboard & Data (ZIP)",
                data=fp,
                file_name="Dashboard_Sentimen_MUN.zip",
                mime="application/zip"
            )