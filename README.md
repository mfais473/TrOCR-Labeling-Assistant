# TrOCR-Labeling-Assistant
TrOCR Labeling Assistant adalah aplikasi desktop offline berbasis Python + Tkinter yang membantu anda untuk:
1. Membuat bounding box area teks secara manual di gambar,
2. Menyimpan hasil labeling dalam format teks yang sesuai untuk pelatihan model TrOCR atau model OCR lainnya,
3. Menyimpan hasil crop teks otomatis ke folder output untuk dataset.

# Fitur Utama:
GUI ringan (tidak butuh koneksi internet)
Mendukung format gambar umum: .jpg, .png, .jpeg
Penyimpanan otomatis hasil crop dan label (output/labels.txt)
Folder output dibuat otomatis
Kompatibel dengan dataset format TrOCR (image–text pair)

# Teknologi yang digunakan:
1. Python 3.x
2. Tkinter (GUI)
3. Pillow
4. OpenCV

# Contoh format label yang dihasilkan:
gambar1.jpg[tabs]labels1

# Kami juga memiliki beberapa project yang sedang dikerjakan sekarang:
1. Fine-tuning TrOCR untuk ekstraksi identitas (dalam bahasa Indonesia).
2. Fine-tuning BERT untuk analisis sentimen komentar (dalam bahasa Indonesia) dengan konteks.
3. Pengembangan sistem deteksi+tracking ayam menggunakan YOLO-tracker.
4. Pengembangan AI multimodal berbasis YOLO-tracker untuk monitoring kesehatan ayam di peternakan.

jika anda tertarik dengan project yang sedang kami kembangkan, anda dapat berkontribusi atau bergabung dengan kami untuk bersama-sama mengembangkan project-project tersebut.

