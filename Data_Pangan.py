import pandas as pd
import json
from kafka import KafkaProducer
from flask import Flask, render_template, request
import matplotlib.pyplot as plt
import io
import base64
from collections import defaultdict

# Konfigurasi Kafka
producer = KafkaProducer(
    bootstrap_servers='localhost:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)
topic_name = 'pangan_data'

# Fungsi untuk mengirimkan data ke Kafka
def send_to_kafka(filtered_df):
    for _, row in filtered_df.iterrows():
        message = row.to_dict()
        producer.send(topic_name, value=message)
        print(f"Mengirim: {message}")

# Flask Application
app = Flask(__name__)

@app.route('/')
def index():
    # Baca dataset untuk mengisi dropdown secara dinamis
    file_path = '/home/idris/hadoop/Dataset_Pangan.csv'
    df = pd.read_csv(file_path)
    provinsi_list = df['Provinsi'].dropna().unique().tolist()
    tahun_list = df['Tahun'].dropna().unique().tolist()
    return render_template('index.html', provinsi_list=provinsi_list, tahun_list=tahun_list)

@app.route('/filter', methods=['POST'])
def filter_data():
    provinsi = request.form.get('provinsi')
    tahun = request.form.get('tahun')

    # Baca dataset lokal
    file_path = '/home/idris/hadoop/Dataset_Pangan.csv'
    df = pd.read_csv(file_path)

    # Bersihkan data
    df = df[['Tahun', 'Provinsi', 'Kelompok Bahan Pangan', 'Komoditas', 'Konsumsi_Pangan']]

    # Terapkan filter
    if provinsi:
        df = df[df['Provinsi'] == provinsi]
    if tahun:
        df = df[df['Tahun'] == tahun]

    if df.empty:
        return render_template('result.html', pie_charts_by_year={}, provinsi=provinsi, error="Tidak ada data yang cocok dengan filter.")

    # Kirim data yang difilter ke Kafka
    send_to_kafka(df)

    # Visualisasi data: Pie chart untuk setiap kelompok bahan pangan dan tahun
    pie_charts_by_year = defaultdict(list)
    groups = df.groupby(['Tahun', 'Kelompok Bahan Pangan'])

    for (year, group), data in groups:
        pie_data = data.groupby('Komoditas')['Konsumsi_Pangan'].sum()
        fig, ax = plt.subplots()
        ax.pie(pie_data, labels=pie_data.index, autopct='%1.1f%%', startangle=140)
        ax.set_title(f"{group} ({year})")

        # Simpan plot sebagai gambar base64
        img = io.BytesIO()
        plt.savefig(img, format='png')
        img.seek(0)
        pie_charts_by_year[year].append({
            "title": f"{group} ({year})",
            "url": base64.b64encode(img.getvalue()).decode()
        })
        plt.close()

    # Kirim data ke template
    return render_template('result.html', pie_charts_by_year=pie_charts_by_year, provinsi=provinsi, error=None)

if __name__ == '__main__':
    app.run(debug=True)

