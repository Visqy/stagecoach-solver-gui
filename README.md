# Stagecoach DP GUI (Streamlit + Tailwind)

Made by [Visqy](https://github.com/Visqy) and [AkmalMakarim](https://github.com/AkmalMakarim).Aplikasi GUI sederhana untuk memecahkan **Stagecoach Dynamic Programming** (layered shortest/longest path) dan memvisualisasikan **semua jalur optimal**. Antarmuka dibuat dengan **Streamlit** dan styling **Tailwind CSS via CDN**. Solver, rekonstruksi jalur, dan visualisasi graf disediakan oleh modul lokal `stagecoach.py`.

## Fitur

- Input ber-stage (`layers`) dan bobot antar-node (`edges`) dalam format JSON.
- Memilih **mode optimasi**: `min` (biaya minimum) atau `max` (nilai maksimum).
- Memilih **operasi agregasi**: `+` (penjumlahan) atau `*` (perkalian).
- Tabel proses DP per stage (mundur).
- Rekonstruksi **semua** jalur optimal.
- Visualisasi graf dengan opsi unduh PNG.

## Struktur Berkas

```
.
├── app.py          # Streamlit GUI
├── stagecoach.py    # Solver DP + rekonstruksi jalur + plotter
├── requirements.txt
└── README.md
```

## Prasyarat

- Python **3.9+** (disarankan 3.10/3.11)
- Pip terbaru: `python -m pip install --upgrade pip`

## Instalasi Cepat

```bash
# (Opsional) buat virtual environment
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# Instal dependensi
pip install -r requirements.txt
```

## Menjalankan Aplikasi

Di direktori proyek yang sama dengan `main.py` dan `stagecoach.py`:

```bash
# Cara umum
streamlit run main.py

# Jika 'streamlit' tidak dikenali di Windows PowerShell/CMD:
python -m streamlit run main.py
```

Setelah berjalan, Streamlit akan membuka aplikasi di browser pada alamat `http://localhost:8501` (default).

## Cara Pakai Singkat

1. Buka aplikasi, isi **Layers** dan **Edges** di **sidebar** dalam format JSON, atau klik **Gunakan Contoh**.
2. Tentukan **Start**, **Goal**, **Mode Optimasi** (`min|max`), dan **Operasi Agregasi** (`+|*`).
3. Klik **Jalankan Solver**.
4. Lihat hasil:
   - **Hasil**: biaya optimal, salah satu path terpilih, dan daftar semua jalur optimal.
   - **Proses**: tabel per stage dari perhitungan DP.
   - **Visualisasi**: graf stagecoach, dapat diunduh sebagai PNG.
   - **Tentang**: ringkasan opsi dan contoh input valid.

## Format Input (JSON)

### Layers

`layers` adalah list of list berurutan dari kiri ke kanan (stage 0, 1, ..., K).

```json
[["S"], ["A", "B"], ["C", "D"], ["T"]]
```

- **Start** harus berada di **stage 0**.
- **Goal** harus berada di **stage terakhir**.

### Edges

`edges` adalah dict-of-dict: source -> {target: biaya}.

- **Wajib** menghubungkan **stage i** ke **stage i+1** saja (tidak boleh melompat stage).

```json
{
  "S": { "A": 2, "B": 5 },
  "A": { "C": 4, "D": 1 },
  "B": { "C": 2 },
  "C": { "T": 3 },
  "D": { "T": 2 }
}
```

### Contoh Konfigurasi Lengkap

```json
{
  "layers": [["S"], ["A", "B"], ["C", "D"], ["T"]],
  "edges": {
    "S": { "A": 2, "B": 5 },
    "A": { "C": 4, "D": 1 },
    "B": { "C": 2 },
    "C": { "T": 3 },
    "D": { "T": 2 }
  },
  "start": "S",
  "goal": "T",
  "opt_mode": "min",
  "combine_op": "+"
}
```

## Catatan & Batasan

- Edge **harus** dari stage i ke stage i+1. Jika tidak, validasi akan gagal.
- Node tidak boleh duplikat di `layers`.
- `opt_mode="min"` menggunakan inisialisasi `+∞`, `opt_mode="max"` menggunakan `-∞`.
- Untuk `combine_op="*"`, nilai terminal (di goal) = `1.0`. Untuk `+`, nilai terminal = `0.0`.
- Visualisasi menggunakan Matplotlib; pada environment server tanpa display, Streamlit akan menangani backend headless.

## Troubleshooting

- **"streamlit: command not found" atau "not recognized"** Jalankan `python -m streamlit run main.py` atau pastikan virtual env aktif.
- **"Gagal mengimpor modul stagecoach.py"** Pastikan `stagecoach.py` berada di folder yang sama dengan `main.py`.
- **"Edge melompat stage"** Periksa bahwa setiap edge hanya menghubungkan node di stage i ke node di stage i+1.
- **Graf kosong / jalur tidak muncul**
  Periksa kembali input JSON; gunakan contoh sebagai baseline, lalu ubah sedikit demi sedikit.
