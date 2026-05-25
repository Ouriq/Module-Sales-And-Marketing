# Indofood Login System

Sistem login internal PT Indofood CBP Sukses Makmur Tbk.

---

## Struktur Proyek

```
indofood-login/
├── index.html        ← Halaman login (frontend)
├── style.css         ← Styling halaman
├── app.js            ← JavaScript (validasi & API calls)
├── server.py         ← Backend Python (Flask + SQLite)
├── requirements.txt  ← Dependensi Python
└── README.md
```

---

## Cara Menjalankan

### 1. Install dependensi Python

```bash
pip install -r requirements.txt
```

### 2. Jalankan backend server

```bash
python server.py
```

Server berjalan di: **http://localhost:5000**

Database SQLite (`indofood.db`) dibuat otomatis.

### 3. Buka frontend

Buka file `index.html` di browser, atau gunakan server lokal sederhana:

```bash
# Python
python -m http.server 8080

# Node.js (npx)
npx serve .
```

Kemudian buka: **http://localhost:8080**

---

## Akun Demo

| Email                  | Password   | Role  |
|------------------------|------------|-------|
| admin@indofood.com     | admin123   | Admin |
| user@indofood.com      | user123    | User  |
| demo@perusahaan.com    | demo123    | User  |

> ⚠️ Ganti password sebelum deploy ke production!

---

## API Endpoints

| Method | Endpoint               | Keterangan                      |
|--------|------------------------|---------------------------------|
| POST   | /api/login             | Login dengan email & password   |
| POST   | /api/logout            | Logout (butuh token)            |
| POST   | /api/forgot-password   | Kirim email reset password      |
| GET    | /api/me                | Info profil (butuh token)       |
| GET    | /api/login-history     | Riwayat login (butuh token)     |

### Contoh Request Login

```bash
curl -X POST http://localhost:5000/api/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@indofood.com","password":"admin123","remember":false}'
```

### Contoh Response Sukses

```json
{
  "success": true,
  "message": "Login berhasil.",
  "token": "eyJ...",
  "user": {
    "id": "...",
    "name": "Administrator",
    "email": "admin@indofood.com",
    "role": "admin",
    "department": "IT"
  },
  "redirect_url": "/dashboard"
}
```

---

## Fitur Keamanan

- ✅ Password di-hash dengan **bcrypt** (cost factor 12)
- ✅ Token autentikasi **JWT** (expire 8 jam / 30 hari jika "ingat saya")
- ✅ **Account lockout** setelah 5 gagal login (kunci 15 menit)
- ✅ **Login audit log** — setiap percobaan login dicatat
- ✅ **Password reset token** sekali pakai (expire 2 jam)
- ✅ Validasi email & password di frontend dan backend
- ✅ Generic error message (mencegah email enumeration)
- ✅ CORS dikonfigurasi

---

## Database (SQLite)

Tabel yang dibuat otomatis:

| Tabel                   | Keterangan                          |
|-------------------------|-------------------------------------|
| `users`                 | Data pengguna                       |
| `login_logs`            | Riwayat setiap percobaan login      |
| `password_reset_tokens` | Token reset password sekali pakai   |

Untuk mengganti ke **PostgreSQL** atau **MySQL**, cukup ubah URI di `server.py`:

```python
# PostgreSQL
SQLALCHEMY_DATABASE_URI = "postgresql://user:pass@localhost/indofood_db"

# MySQL
SQLALCHEMY_DATABASE_URI = "mysql+pymysql://user:pass@localhost/indofood_db"
```
