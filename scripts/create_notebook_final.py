import json

# Define cells for ModelT5Train_NLP.ipynb with clean, formal explanation-oriented Indonesian markdown (no emojis, no mention of upgrades/fixes)
cells = [
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "# Panduan Pelatihan Model mT5-small untuk Sistem Tanya Jawab Bahasa Indonesia (TutorQA)\n",
            "\n",
            "Notebook ini dirancang untuk melatih model **google/mt5-small** pada dataset **TyDi QA** (Bahasa Indonesia). Proses pelatihan disesuaikan untuk dijalankan di Google Colab menggunakan runtime GPU T4 dengan mengutamakan kestabilan numerik dan efisiensi memori.\n",
            "\n",
            "### Arsitektur Pelatihan:\n",
            "1. **Adafactor Optimizer**: Digunakan sebagai pengganti AdamW karena model T5/mT5 sangat sensitif terhadap akumulasi gradien dan sering mengalami loss NaN (numerical instability) selama pelatihan. Adafactor menjaga kestabilan skala pembaruan parameter dan lebih hemat VRAM.\n",
            "2. **Gradient Accumulation (Akumulasi Gradien)**: Mensimulasikan batch size efektif sebesar 16 secara virtual dengan melakukan akumulasi langkah gradien (accumulation steps = 4) pada batch fisik kecil (batch size = 4). Hal ini mencegah resiko kehabisan memori GPU (Out-Of-Memory/OOM).\n",
            "3. **Pemberhentian Awal (Early Stopping)**: Menghentikan pelatihan secara otomatis apabila loss evaluasi tidak menunjukkan perbaikan dalam beberapa epoch berturut-turut untuk menghindari overfitting.\n",
            "4. **Metrik Evaluasi ROUGE**: Digunakan untuk mengukur kemiripan tekstual jawaban yang dihasilkan oleh model dengan jawaban referensi secara kuantitatif selama tahapan evaluasi.\n",
            "5. **Dynamic Padding**: Mengabaikan padding statis pada proses awal tokenisasi, sehingga ukuran padding disesuaikan secara dinamis untuk setiap batch selama collation guna mempercepat proses pelatihan.\n",
            "6. **Indonesian QA Alignment**: Format prompt yang digunakan diselaraskan dengan format penyajian dari aplikasi backend TutorQA (`pertanyaan: ... konteks: ...`)."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Sel 1: Pemasangan library yang diperlukan\n",
            "!pip install --upgrade transformers datasets evaluate accelerate sentencepiece rouge-score -q"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## 1. Memuat dan Mempersiapkan Dataset TyDi QA (Bahasa Indonesia)\n",
            "Dataset TyDi QA dibatasi pada data sekunder untuk bahasa Indonesia."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Sel 2: Unduh dan saring data bahasa Indonesia\n",
            "from datasets import load_dataset\n",
            "\n",
            "print(\"Mengunduh dataset TyDi QA...\")\n",
            "dataset = load_dataset(\"tydiqa\", \"secondary_task\")\n",
            "\n",
            "print(\"Menyaring data Bahasa Indonesia...\")\n",
            "ds_id_train = dataset['train'].filter(lambda x: x['id'].startswith('indonesian'))\n",
            "ds_id_val = dataset['validation'].filter(lambda x: x['id'].startswith('indonesian'))\n",
            "\n",
            "print(f\"Jumlah data latih (train): {len(ds_id_train)}\")\n",
            "print(f\"Jumlah data validasi (validation): {len(ds_id_val)}\")"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## 2. Memuat Model dan Tokenizer mT5-small\n",
            "Tokenizer dan model dimuat dari model dasar google/mt5-small."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Sel 3: Memuat Tokenizer dan Model\n",
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
            "## 3. Preprocessing dan Tokenisasi Dataset\n",
            "Pada tahap ini, pertanyaan dan konteks digabungkan dengan format prompt terstruktur: `pertanyaan: {soal} konteks: {materi}`. Data dipotong (truncation) sesuai kapasitas model, sedangkan padding akan ditangani secara dinamis oleh collator."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Sel 4: Fungsi Preprocessing\n",
            "max_input_length = 512\n",
            "max_target_length = 128\n",
            "\n",
            "def preprocess_function(examples):\n",
            "    inputs = [\"pertanyaan: \" + q + \" konteks: \" + c for q, c in zip(examples[\"question\"], examples[\"context\"])]\n",
            "    targets = [answers[\"text\"][0] if len(answers[\"text\"]) > 0 else \"\" for answers in examples[\"answers\"]]\n",
            "    \n",
            "    model_inputs = tokenizer(inputs, max_length=max_input_length, truncation=True)\n",
            "    labels = tokenizer(text_target=targets, max_length=max_target_length, truncation=True)\n",
            "    \n",
            "    model_inputs[\"labels\"] = labels[\"input_ids\"]\n",
            "    return model_inputs\n",
            "\n",
            "print(\"Memulai pemrosesan dataset...\")\n",
            "tokenized_train = ds_id_train.map(preprocess_function, batched=True, remove_columns=ds_id_train.column_names)\n",
            "tokenized_val = ds_id_val.map(preprocess_function, batched=True, remove_columns=ds_id_val.column_names)\n",
            "print(\"Pemrosesan selesai.\")"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## 4. Konfigurasi Pengukuran Kinerja Model (Metrik ROUGE)\n",
            "Fungsi evaluasi disiapkan untuk menghitung skor ROUGE secara berkala guna melacak perkembangan akurasi teks jawaban hasil generate model terhadap jawaban referensi asli."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Sel 5: Inisialisasi Metrik Evaluasi\n",
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
            "    decoded_preds = tokenizer.batch_decode(preds, skip_special_tokens=True)\n",
            "    labels = np.where(labels != -100, labels, tokenizer.pad_token_id)\n",
            "    decoded_labels = tokenizer.batch_decode(labels, skip_special_tokens=True)\n",
            "    \n",
            "    decoded_preds = [pred.strip() for pred in decoded_preds]\n",
            "    decoded_labels = [label.strip() for label in decoded_labels]\n",
            "    \n",
            "    result = rouge_metric.compute(predictions=decoded_preds, references=decoded_labels, use_stemmer=True)\n",
            "    result = {key: round(value * 100, 4) for key, value in result.items()}\n",
            "    return result"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## 5. Parameter Pelatihan dan Inisialisasi Trainer\n",
            "Pelatihan dikonfigurasi menggunakan Adafactor optimizer untuk mencegah terjadinya NaN loss pada model berbasis T5. Parameter gradient accumulation disetel ke 4 langkah untuk menghasilkan kestabilan pembaruan bobot model."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Sel 6: Setup Parameter Pelatihan\n",
            "from transformers import Seq2SeqTrainingArguments, Seq2SeqTrainer, DataCollatorForSeq2Seq, EarlyStoppingCallback\n",
            "\n",
            "data_collator = DataCollatorForSeq2Seq(tokenizer, model=model)\n",
            "\n",
            "args = Seq2SeqTrainingArguments(\n",
            "    output_dir=\"./hasil-qa-mt5\",\n",
            "    eval_strategy=\"epoch\",\n",
            "    save_strategy=\"epoch\",\n",
            "    learning_rate=1e-3,\n",
            "    optim=\"adafactor\",\n",
            "    lr_scheduler_type=\"constant_with_warmup\",\n",
            "    warmup_ratio=0.1,\n",
            "    per_device_train_batch_size=4,\n",
            "    per_device_eval_batch_size=4,\n",
            "    gradient_accumulation_steps=4,\n",
            "    weight_decay=0.01,\n",
            "    save_total_limit=2,\n",
            "    num_train_epochs=5,\n",
            "    predict_with_generate=True,\n",
            "    logging_steps=20,\n",
            "    metric_for_best_model=\"eval_loss\",\n",
            "    greater_is_better=False,\n",
            "    load_best_model_at_end=True,\n",
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
            "    callbacks=[EarlyStoppingCallback(early_stopping_patience=2)]\n",
            ")"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## 6. Proses Pelatihan Model (Fine-Tuning)\n",
            "Jalankan sel ini untuk memulai proses pelatihan model."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Sel 7: Menjalankan Pelatihan\n",
            "print(\"Memulai pelatihan model...\")\n",
            "train_result = trainer.train()\n",
            "print(\"Pelatihan selesai.\")"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## 7. Pengujian Hasil Inferensi Model Secara Lokal\n",
            "Lakukan uji coba tanya jawab langsung pada model yang telah selesai dilatih menggunakan contoh teks materi dan pertanyaan di bawah ini."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Sel 8: Pengujian Inferensi\n",
            "import torch\n",
            "\n",
            "device = \"cuda\" if torch.cuda.is_available() else \"cpu\"\n",
            "model.to(device)\n",
            "\n",
            "konteks_materi = \"\"\"\n",
            "Politeknik Caltex Riau (PCR) adalah perguruan tinggi swasta di Pekanbaru, Riau, Indonesia yang didirikan pada tahun 2001.\n",
            "Kampus ini didirikan atas kerja sama antara Pemerintah Provinsi Riau dengan PT Caltex Pacific Indonesia.\n",
            "PCR terkenal dengan program-program teknologi informasi, komputer, dan rekayasa tekniknya yang berstandar tinggi.\n",
            "\"\"\"\n",
            "\n",
            "pertanyaan = \"Kapan Politeknik Caltex Riau didirikan?\"\n",
            "\n",
            "teks_input = f\"pertanyaan: {pertanyaan} konteks: {konteks_materi}\"\n",
            "\n",
            "inputs = tokenizer(teks_input, return_tensors=\"pt\").to(device)\n",
            "outputs = model.generate(**inputs, max_new_tokens=64)\n",
            "\n",
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
            "## 8. Menghubungkan Google Drive & Menyimpan Model\n",
            "Hubungkan notebook dengan Google Drive Anda untuk menyimpan bobot model dan tokenizer hasil latihan agar dapat diunduh dan digunakan kembali secara lokal."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Sel 9: Penyimpanan Model ke Google Drive\n",
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
            "print(\"Model dan tokenizer telah disimpan di Google Drive Anda.\")"
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

with open(r"c:\Punya GW\01. CODE\NLP\ModelT5Train_NLP.ipynb", "w", encoding="utf-8") as f:
    json.dump(notebook_data, f, indent=2, ensure_ascii=False)

print("SUCCESS: Notebook ModelT5Train_NLP.ipynb has been generated cleanly!")
