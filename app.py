from flask import Flask, request, jsonify
import mysql.connector
import face_recognition
import json
import numpy as np
import io

app = Flask(__name__)

# Config Koneksi Database MySQL
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '', # Sesuaikan dengan password MySQL Anda
    'database': 'db_peminjaman'
}

def get_db_connection():
    return mysql.connector.connect(**db_config)


@app.route('/api/register-face', methods=['POST'])
def register_face():
    """
    Endpoint untuk mendaftarkan wajah pengguna baru.
    Input Form-Data: 'nim_nip', 'nama', 'image' (File Foto Wajah)
    """
    nim_nip = request.form.get('nim_nip')
    nama = request.form.get('nama')
    file_image = request.files.get('image')

    if not nim_nip or not nama or not file_image:
        return jsonify({'status': 'error', 'message': 'Data tidak lengkap!'}), 400

    # Process image & extract facial embedding
    img_bytes = file_image.read()
    image = face_recognition.load_image_file(io.BytesIO(img_bytes))
    encodings = face_recognition.face_encodings(image)

    if len(encodings) == 0:
        return jsonify({'status': 'error', 'message': 'Wajah tidak terdeteksi dalam foto!'}), 400

    # Ambil vector embedding pertama (128 nilai numerik)
    face_vector = encodings[0].tolist()
    face_vector_json = json.dumps(face_vector)

    # Simpan ke MySQL
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = "INSERT INTO users (nim_nip, nama, face_embedding) VALUES (%s, %s, %s)"
        cursor.execute(query, (nim_nip, nama, face_vector_json))
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'status': 'success', 'message': f'Pengguna {nama} berhasil didaftarkan.'}), 201
    except mysql.connector.Error as err:
        return jsonify({'status': 'error', 'message': str(err)}), 500


@app.route('/api/verify-face', methods=['POST'])
def verify_face():
    """
    Endpoint untuk memverifikasi wajah saat peminjaman barang.
    Input Form-Data: 'image' (File Foto dari WebCam)
    """
    file_image = request.files.get('image')

    if not file_image:
        return jsonify({'status': 'error', 'message': 'Foto kamera tidak ditemukan!'}), 400

    # Extrak embedding dari foto webcam
    img_bytes = file_image.read()
    unknown_image = face_recognition.load_image_file(io.BytesIO(img_bytes))
    unknown_encodings = face_recognition.face_encodings(unknown_image)

    if len(unknown_encodings) == 0:
        return jsonify({'status': 'error', 'message': 'Wajah tidak terdeteksi oleh kamera!'}), 400

    unknown_encoding = unknown_encodings[0]

    # Ambil semua data embedding pengguna dari MySQL
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, nim_nip, nama, face_embedding FROM users")
        users = cursor.fetchall()
        cursor.close()
        conn.close()
    except mysql.connector.Error as err:
        return jsonify({'status': 'error', 'message': str(err)}), 500

    # Cocokkan wajah dengan dataset di MySQL
    known_encodings = []
    user_data = []

    for user in users:
        embedding_list = json.loads(user['face_embedding'])
        known_encodings.append(np.array(embedding_list))
        user_data.append(user)

    if not known_encodings:
        return jsonify({'status': 'failed', 'message': 'Belum ada data pengguna terdaftar di sistem.'}), 404

    # Hitung jarak/kemiripan wajah (Tolerance standar: 0.6)
    face_distances = face_recognition.face_distance(known_encodings, unknown_encoding)
    best_match_index = int(np.argmin(face_distances))

    if face_distances[best_match_index] <= 0.5:  # Tolerance threshold = 0.5 (makin kecil makin ketat)
        matched_user = user_data[best_match_index]
        confidence = round((1 - face_distances[best_match_index]) * 100, 2)

        return jsonify({
            'status': 'success',
            'verified': True,
            'confidence': f'{confidence}%',
            'data': {
                'user_id': matched_user['id'],
                'nim_nip': matched_user['nim_nip'],
                'nama': matched_user['nama']
            }
        }), 200
    else:
        return jsonify({
            'status': 'failed',
            'verified': False,
            'message': 'Wajah tidak dikenali! Silakan mendaftar terlebih dahulu.'
        }), 401


if __name__ == '__main__':
    app.run(debug=True, port=5000)