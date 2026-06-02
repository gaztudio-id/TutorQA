import json

# Define the cells for the Jupyter Notebook without any emojis
cells = [
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "# TutorQA — Upgraded Fine-Tuning Pipeline (mT5-small untuk Sistem Tanya Jawab Bahasa Indonesia)\n",
            "\n",
            "Notebook ini dirancang khusus untuk Google Colab (direkomendasikan menggunakan runtime GPU T4) untuk melatih model **google/mt5-small** pada dataset **TyDi QA** (Bahasa Indonesia) dengan kestabilan tinggi.\n",
            "\n",
            "### Fitur Baru & Peningkatan:\n",
            "1. **Adafactor Optimizer**: Menghindari masalah loss NaN (collapse) yang sering terjadi pada mT5 dengan AdamW, serta lebih hemat memori GPU.\n",
            "2. **Gradient Accumulation (Akumulasi Gradien)**: Mensimulasikan batch size yang lebih besar (16) secara virtual tanpa resiko Out-Of-Memory (OOM).\n",
            "3. **Pemberhentian Awal (Early Stopping)**: Menghentikan pelatihan jika loss validasi tidak membaik, meminimalkan overfitting.\n",
            "4. **Metrik Evaluasi ROUGE**: Mengukur kemiripan tekstual jawaban AI dengan jawaban referensi secara kuantitatif selama evaluasi.\n",
            "5. **Dynamic Padding**: Mempercepat tokenisasi hingga 2x lipat dan menghemat VRAM.\n",
            "6. **Indonesian QA Alignment**: Format prompt yang digunakan sama persis dengan yang disajikan oleh aplikasi backend TutorQA (`pertanyaan: ... konteks: ...`)."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Sel 1: Instal library yang diperlukan dengan versi terbaru yang stabil\n",
            "!pip install --upgrade transformers datasets evaluate accelerate sentencepiece rouge-score -q"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## 1. Load dan Persiapan Dataset TyDi QA (Bahasa Indonesia)\n",
            "Kami menggunakan pembagian dataset bahasa Indonesia yang disaring dari dataset QA multibahasa TyDi QA."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Sel 2: Mengunduh dan memfilter dataset TyDi QA untuk Bahasa Indonesia\n",
            "from datasets import load_dataset\n",
            "\n",
            "print(\"Mengunduh dataset TyDi QA...\")\n",
            "# Menggunakan secondary_task karena formatnya berisi pasangan question, context, answers secara terstruktur\n",
            "dataset = load_dataset(\"tydiqa\", \"secondary_task\")\n",
            "\n",
            "# Memfilter data Bahasa Indonesia (id yang berawalan 'indonesian')\n",
            "print(\"Memfilter data Bahasa Indonesia...\")\n",
            "ds_id_train = dataset['train'].filter(lambda x: x['id'].startswith('indonesian'))\n",
            "ds_id_val = dataset['validation'].filter(lambda x: x['id'].startswith('indonesian'))\n",
            "\n",
            "print(f\"Jumlah data latih (train): {len(ds_id_train)}\")\n",
            "print(f\"Jumlah data validasi (val): {len(ds_id_val)}\")"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## 2. Load Model & Tokenizer (mT5-small)\n",
            "Kami menggunakan model Google mT5-small yang sudah terlatih pada berbagai bahasa termasuk bahasa Indonesia."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Sel 3: Memuat Tokenizer dan Model mT5-small\n",
            "from transformers import AutoTokenizer, AutoModelForSeq2SeqLM\n",
            "\n",
            "model_id = \"google/mt5-small\"\n",
            "\n",
            "print(f\"Memuat tokenizer dan model dari {model_id}...\")\n",
            "tokenizer = AutoTokenizer.from_pretrained(model_id)\n",
            "model = AutoModelForSeq2SeqLM.from_pretrained(model_id)"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## 3. Preprocessing Data & Tokenisasi (Efisiensi Tinggi)\n",
            "Kami menggunakan pemotongan (truncation) tanpa padding statis di awal. Dynamic padding akan dilakukan secara efisien oleh `DataCollatorForSeq2Seq`.\n",
            "Format prompt disesuaikan dengan format inferensi aplikasi: `pertanyaan: {soal} konteks: {materi}`."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Sel 4: Fungsi Tokenisasi & Preprocessing\n",
            "max_input_length = 512\n",
            "max_target_length = 128\n",
            "\n",
            "def preprocess_function(examples):\n",
            "    # Format input: \"pertanyaan: [soal] konteks: [materi]\"\n",
            "    inputs = [\"pertanyaan: \" + q + \" konteks: \" + c for q, c in zip(examples[\"question\"], examples[\"context\"])]\n",
            "    \n",
            "    # Ambil jawaban pertama dari daftar jawaban (atau kosong jika tidak ada)\n",
            "    targets = [answers[\"text\"][0] if len(answers[\"text\"]) > 0 else \"\" for answers in examples[\"answers\"]]\n",
            "    \n",
            "    # Tokenisasi tanpa padding di awal (di-pad dinamis oleh collator untuk menghemat memori)\n",
            "    model_inputs = tokenizer(inputs, max_length=max_input_length, truncation=True)\n",
            "    labels = tokenizer(text_target=targets, max_length=max_target_length, truncation=True)\n",
            "    \n",
            "    model_inputs[\"labels\"] = labels[\"input_ids\"]\n",
            "    return model_inputs\n",
            "\n",
            "print(\"Memproses tokenisasi dataset...\")\n",
            "tokenized_train = ds_id_train.map(preprocess_function, batched=True, remove_columns=ds_id_train.column_names)\n",
            "tokenized_val = ds_id_val.map(preprocess_function, batched=True, remove_columns=ds_id_val.column_names)\n",
            "print(\"Tokenisasi selesai!\")"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## 4. Konfigurasi Metrik Evaluasi (ROUGE Score)\n",
            "Untuk mengukur seberapa bagus jawaban yang dihasilkan oleh model selama proses training, kita akan menghitung ROUGE-1, ROUGE-2, dan ROUGE-L secara otomatis setiap akhir epoch."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Sel 5: Set up Metrik ROUGE\n",
            "import evaluate\n",
            "import numpy as np\n",
            "\n",
            "rouge_metric = evaluate.load(\"rouge\")\n",
            "\n",
            "def compute_metrics(eval_preds):\n",
            "    preds, labels = eval_preds\n",
            "    if isinstance(preds, tuple):\n",
            "        preds = preds[0]\n",
            "        \n",
            "    # Ganti token -100 (ignore index) dengan pad token id agar bisa di-decode\n",
            "    decoded_preds = tokenizer.batch_decode(preds, skip_special_tokens=True)\n",
            "    labels = np.where(labels != -100, labels, tokenizer.pad_token_id)\n",
            "    decoded_labels = tokenizer.batch_decode(labels, skip_special_tokens=True)\n",
            "    \n",
            "    # Bersihkan whitespace\n",
            "    decoded_preds = [pred.strip() for pred in decoded_preds]\n",
            "    decoded_labels = [label.strip() for label in decoded_labels]\n",
            "    \n",
            "    # Hitung ROUGE\n",
            "    result = rouge_metric.compute(predictions=decoded_preds, references=decoded_labels, use_stemmer=True)\n",
            "    \n",
            "    # Format nilai menjadi persen\n",
            "    result = {key: round(value * 100, 4) for key, value in result.items()}\n",
            "    return result"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## 5. Konfigurasi Argumen Pelatihan (Stabilitas Tinggi & Tanpa NaN Loss)\n",
            "Disini kita melakukan perbaikan krusial:\n",
            "- Mengaktifkan **Adafactor** optimizer (`optim=\"adafactor\"`), sangat krusial untuk kestabilan mT5.\n",
            "- Mengaktifkan **Gradient Accumulation** (`gradient_accumulation_steps=4`) untuk mensimulasikan batch size = 16.\n",
            "- Menambahkan **Early Stopping** untuk menghindari overfitting."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Sel 6: Konfigurasi TrainingArguments, Collator, dan Trainer\n",
            "from transformers import Seq2SeqTrainingArguments, Seq2SeqTrainer, DataCollatorForSeq2Seq, EarlyStoppingCallback\n",
            "\n",
            "data_collator = DataCollatorForSeq2Seq(tokenizer, model=model)\n",
            "\n",
            "args = Seq2SeqTrainingArguments(\n",
            "    output_dir=\"./hasil-qa-mt5\",\n",
            "    eval_strategy=\"epoch\",\n",
            "    save_strategy=\"epoch\",\n",
            "    learning_rate=1e-3, # Direkomendasikan untuk T5 dengan Adafactor + Warmup\n",
            "    optim=\"adafactor\", # Mencegah NaN Loss & Menghemat Memori GPU\n",
            "    lr_scheduler_type=\"constant_with_warmup\",\n",
            "    warmup_ratio=0.1,\n",
            "    per_device_train_batch_size=4, # Batch size GPU fisik\n",
            "    per_device_eval_batch_size=4,\n",
            "    gradient_accumulation_steps=4, # Mengakumulasi gradien selama 4 langkah (Batch Size Efektif = 16)\n",
            "    weight_decay=0.01,\n",
            "    save_total_limit=2,\n",
            "    num_train_epochs=5, # 5 epoch latih agar hasil maksimal\n",
            "    predict_with_generate=True,\n",
            "    logging_steps=20,\n",
            "    metric_for_best_model=\"eval_loss\",\n",
            "    greater_is_better=False,\n",
            "    load_best_model_at_end=True, # Memuat model terbaik saat evaluasi selesai\n",
            "    report_to=\"none\"\n",
            ")\n",
            "\n",
            "trainer = Seq2SeqTrainer(\n",
            "    model=model,\n",
            "    args=args,\n",
            "    train_dataset=tokenized_train,\n",
            "    eval_dataset=tokenized_val,\n",
            "    data_collator=data_collator,\n",
            "    processing_class=tokenizer,\n",
            "    compute_metrics=compute_metrics,\n",
            "    callbacks=[EarlyStoppingCallback(early_stopping_patience=2)] # Berhenti jika 2 epoch berturut-turut loss tidak membaik\n",
            ")"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## 6. Mulai Proses Training / Fine-Tuning\n",
            "Jalankan sel ini untuk memulai pelatihan. Anda akan melihat metrik loss dan ROUGE diperbarui setiap akhir epoch."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Sel 7: Menjalankan fine-tuning\n",
            "print(\"Memulai proses training model...\")\n",
            "train_result = trainer.train()\n",
            "print(\"Training Selesai dengan sukses!\")"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## 7. Pengujian Model Hasil Latihan (Local Inference)\n",
            "Uji model Anda langsung di Colab dengan memasukkan teks/materi baru dan pertanyaan di bawah ini."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Sel 8: Menguji hasil pelatihan model secara langsung\n",
            "import torch\n",
            "\n",
            "device = \"cuda\" if torch.cuda.is_available() else \"cpu\"\n",
            "model.to(device)\n",
            "\n",
            "# Masukkan contoh konteks dan pertanyaan baru\n",
            "konteks_materi = \"\"\"\n",
            "Politeknik Caltex Riau (PCR) adalah perguruan tinggi swasta di Pekanbaru, Riau, Indonesia yang didirikan pada tahun 2001.\n",
            "Kampus ini didirikan atas kerja sama antara Pemerintah Provinsi Riau dengan PT Caltex Pacific Indonesia.\n",
            "PCR terkenal dengan program-program teknologi informasi, komputer, dan rekayasa tekniknya yang berstandar tinggi.\n",
            "\"\"\"\n",
            "\n",
            "pertanyaan = \"Kapan Politeknik Caltex Riau didirikan?\"\n",
            "\n",
            "# Format prompt harus sama persis dengan training\n",
            "teks_input = f\"pertanyaan: {pertanyaan} konteks: {konteks_materi}\"\n",
            "\n",
            "# Tokenisasi & Generate\n",
            "inputs = tokenizer(teks_input, return_tensors=\"pt\").to(device)\n",
            "outputs = model.generate(**inputs, max_new_tokens=64)\n",
            "\n",
            "# Decode output menjadi teks\n",
            "jawaban_ai = tokenizer.decode(outputs[0], skip_special_tokens=True)\n",
            "\n",
            "print(\"=\"*60)\n",
            "print(f\"Konteks: {konteks_materi.strip()}\")\n",
            "print(f\"Pertanyaan: {pertanyaan}\")\n",
            "print(f\"Jawaban AI: {jawaban_ai}\")\n",
            "print(\"=\"*60)"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## 8. Backup & Simpan Model ke Google Drive Anda\n",
            "Gunakan sel ini untuk menghubungkan Colab dengan Google Drive Anda, lalu simpan model dan tokenizer hasil latihan agar bisa langsung diunduh atau digunakan di server backend TutorQA lokal."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Sel 9: Menghubungkan Google Drive & Menyimpan Model\n",
            "from google.colab import drive\n",
            "import os\n",
            "\n",
            "print(\"Menghubungkan ke Google Drive...\")\n",
            "drive.mount('/content/drive')\n",
            "\n",
            "path_simpan = '/content/drive/MyDrive/mt5-qa-indonesia'\n",
            "\n",
            "if not os.path.exists(path_simpan):\n",
            "    os.makedirs(path_simpan)\n",
            "\n",
            "print(f\"Menyimpan model ke folder Google Drive: {path_simpan}...\")\n",
            "trainer.save_model(path_simpan)\n",
            "tokenizer.save_pretrained(path_simpan)\n",
            "\n",
            "print(\"Model dan tokenizer telah sukses disimpan di Google Drive Anda! Siap digunakan.\")"
        ]
    }
]

notebook_data = {
    "cells": cells,
    "metadata": {
        "colab": {
            "provenance": [],
            "gpuType": "T4"
        },
        "kernelspec": {
            "display_name": "Python 3",
            "name": "python3"
        },
        "language_info": {
            "name": "python"
        },
        "accelerator": "GPU"
    },
    "nbformat": 4,
    "nbformat_minor": 0
}

with open(r"c:\Punya GW\01. CODE\NLP\Untitled11.ipynb", "w", encoding="utf-8") as f:
    json.dump(notebook_data, f, indent=2, ensure_ascii=False)

print("SUCCESS: Notebook Untitled11.ipynb has been upgraded and emoji-free!")
