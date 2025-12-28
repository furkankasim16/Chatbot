
import json
import os

notebook_structure = {
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# 🇹🇷 Türkçe Chatbot Fine-Tuning (Unsloth + Llama 3)\n",
    "\n",
    "Bu notebook, **QuizBot** projesi için Llama 3 modelini Türkçe talimatlarla eğitmek üzere hazırlanmıştır.\n",
    "**Google Colab (Ücretsiz T4 GPU)** üzerinde çalışacak şekilde optimize edilmiştir.\n",
    "\n",
    "### Adımlar:\n",
    "1. Kütüphaneleri Kurulumu\n",
    "2. Modelin Yüklenmesi\n",
    "3. Veri Seti Hazırlığı (`merve/turkish_instructions`)\n",
    "4. Eğitim (Training)\n",
    "5. GGUF Olarak Kaydetme (Ollama için)"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "# 1. Kütüphaneleri Kur (Unsloth)\n",
    "# 'unsloth[colab-new]' paketi gerekli tüm bağımlılıkları (xformers, trl, peft vb.) otomatik ve uyumlu sürümlerle kurar.\n",
    "!pip install \"unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git\"\n",
    "!pip install --no-deps \"triton\" \"peft\" \"accelerate\" \"bitsandbytes\"" 
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "# 2. Modeli Yükle (Llama-3 8B - 4bit Quantized)\n",
    "from unsloth import FastLanguageModel\n",
    "import torch\n",
    "\n",
    "max_seq_length = 2048 # Daha uzun metinler için artırılabilir (Colab RAM sınırına dikkat)\n",
    "dtype = None # Auto detection\n",
    "load_in_4bit = True # 4bit quantization (Hız ve RAM tasarrufu için şart)\n",
    "\n",
    "model, tokenizer = FastLanguageModel.from_pretrained(\n",
    "    model_name = \"unsloth/llama-3-8b-bnb-4bit\",\n",
    "    max_seq_length = max_seq_length,\n",
    "    dtype = dtype,\n",
    "    load_in_4bit = load_in_4bit,\n",
    ")"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "# 3. Veri Setini Hazırla\n",
    "from datasets import load_dataset\n",
    "\n",
    "# Alpaca formatında prompt şablonu\n",
    "alpaca_prompt = \"\"\"Below is an instruction that describes a task. Write a response that appropriately completes the request.\n",
    "\n",
    "### Instruction:\n",
    "{} \n",
    "\n",
    "### Response:\n",
    "{} \"\"\"\n",
    "\n",
    "EOS_TOKEN = tokenizer.eos_token # Cümle sonunu modele öğretmek için\n",
    "\n",
    "# Hugging Face'den Türkçe veri setini indir\n",
    "dataset = load_dataset(\"merve/turkish_instructions\", split = \"train\")\n",
    "\n",
    "# KOLON İSİMLERİNİ KONTROL ET VE DÜZELT\n",
    "print(\"Eski Kolonlar:\", dataset.column_names)\n",
    "\n",
    "# 1. Adım: Kolon isimlerindeki boşlukları temizle (' çıktı' -> 'çıktı')\n",
    "dataset = dataset.rename_columns({col: col.strip() for col in dataset.column_names})\n",
    "\n",
    "print(\"Temizlenmiş Kolonlar:\", dataset.column_names)\n",
    "\n",
    "# 2. Adım: Türkçe isimleri standart formata çevir\n",
    "column_map = {}\n",
    "if \"talimat\" in dataset.column_names:\n",
    "    column_map[\"talimat\"] = \"instruction\"\n",
    "if \"çıktı\" in dataset.column_names:\n",
    "    column_map[\"çıktı\"] = \"output\"\n",
    "if \"cevap\" in dataset.column_names:\n",
    "    column_map[\"cevap\"] = \"output\"\n",
    "if \"giriş\" in dataset.column_names:\n",
    "    column_map[\"giriş\"] = \"input\"\n",
    "\n",
    "if column_map:\n",
    "    dataset = dataset.rename_columns(column_map)\n",
    "\n",
    "print(\"Son Kolon Hali:\", dataset.column_names)\n",
    "\n",
    "def formatting_prompts_func(examples):\n",
    "    # Artık 'instruction' ve 'output' kesin var mı kontrol ediyoruz\n",
    "    instructions = examples[\"instruction\"]\n",
    "    outputs      = examples.get(\"output\", examples.get(\"input\", [])) # output yoksa input arayalım\n",
    "    \n",
    "    # Garantilemek için boş liste kontrolü\n",
    "    if not outputs and \"output\" in examples:\n",
    "        outputs = examples[\"output\"]\n",
    "\n",
    "    texts = []\n",
    "    for instruction, output in zip(instructions, outputs):\n",
    "        text = alpaca_prompt.format(instruction, output) + EOS_TOKEN\n",
    "        texts.append(text)\n",
    "    return { \"text\" : texts, }\n",
    "\n",
    "# Veri setini formatla\n",
    "dataset = dataset.map(formatting_prompts_func, batched = True)"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "# 4. Modeli Eğitime Hazırla (LoRA Ayarları)\n",
    "model = FastLanguageModel.get_peft_model(\n",
    "    model,\n",
    "    r = 16, # LoRA rank (8, 16, 32, 64... 16 genelde yeterli)\n",
    "    target_modules = [\"q_proj\", \"k_proj\", \"v_proj\", \"o_proj\",\n",
    "                      \"gate_proj\", \"up_proj\", \"down_proj\",],\n",
    "    lora_alpha = 16,\n",
    "    lora_dropout = 0, # Dropout = 0 (Optimize edilmiş)\n",
    "    bias = \"none\",\n",
    "    use_gradient_checkpointing = \"unsloth\", # VRAM tasarrufu\n",
    "    random_state = 3407,\n",
    "    use_rslora = False,\n",
    "    loftq_config = None,\n",
    ")"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "# 5. Eğitimi Başlat (Training)\n",
    "from trl import SFTTrainer\n",
    "from transformers import TrainingArguments\n",
    "\n",
    "# [FIX] Unsloth cache hatası için psutil'i GLOBAL (builtins) içine inject ediyoruz\n",
    "# Bu sayede cache'lenmiş UnslothSFTTrainer.py dosyası bile psutil'i görebilir.\n",
    "import builtins\n",
    "builtins.psutil = __import__(\"psutil\")\n",
    "\n",
    "trainer = SFTTrainer(\n",
    "    model = model,\n",
    "    tokenizer = tokenizer,\n",
    "    train_dataset = dataset,\n",
    "    dataset_text_field = \"text\",\n",
    "    max_seq_length = max_seq_length,\n",
    "    dataset_num_proc = 2,\n",
    "    packing = False, # Daha hızlı eğitim için True yapılabilir\n",
    "    args = TrainingArguments(\n",
    "        per_device_train_batch_size = 2,\n",
    "        gradient_accumulation_steps = 4,\n",
    "        warmup_steps = 5,\n",
    "        max_steps = 60, # TEST İÇİN KISA (Tam eğitim için 1000-2000 yapın)\n",
    "        learning_rate = 2e-4,\n",
    "        fp16 = not torch.cuda.is_bf16_supported(),\n",
    "        bf16 = torch.cuda.is_bf16_supported(),\n",
    "        logging_steps = 1,\n",
    "        optim = \"adamw_8bit\",\n",
    "        weight_decay = 0.01,\n",
    "        lr_scheduler_type = \"linear\",\n",
    "        seed = 3407,\n",
    "        output_dir = \"outputs\",\n",
    "    ),\n",
    ")\n",
    "\n",
    "# GPU bilgilerini göster\n",
    "gpu_stats = torch.cuda.get_device_properties(0)\n",
    "start_gpu_memory = round(torch.cuda.max_memory_reserved() / 1024 / 1024 / 1024, 3)\n",
    "max_memory = round(gpu_stats.total_memory / 1024 / 1024 / 1024, 3)\n",
    "print(f\"GPU: {gpu_stats.name} | Max Bellek: {max_memory} GB | Başlangıç Kullanımı: {start_gpu_memory} GB\")\n",
    "\n",
    "trainer_stats = trainer.train()"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "# 6. Test Et (Inference)\n",
    "FastLanguageModel.for_inference(model)\n",
    "inputs = tokenizer(\n",
    "[\"### Instruction:\\nTürkiye'nin başkenti neresidir?\\n\\n### Response:\\n\"], return_tensors = \"pt\").to(\"cuda\")\n",
    "\n",
    "outputs = model.generate(**inputs, max_new_tokens = 64, use_cache = True)\n",
    "print(tokenizer.batch_decode(outputs)[0])"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "### 7. Ollama İçin GGUF Formatında Kaydetme\n",
    "Bu adım modeli sıkıştırılmış GGUF formatına çevirir. Dosyayı indirip Ollama'ya yükleyebilirsiniz."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "# GGUF (Q4_K_M) olarak Google Drive'a veya lokale kaydet\n",
    "model.save_pretrained_gguf(\"model_gguf\", tokenizer, quantization_method = \"q4_k_m\")\n",
    "\n",
    "# İndirme bağlantısı oluştur (Colab için)\n",
    "from google.colab import files\n",
    "files.download(\"model_gguf/unsloth.Q4_K_M.gguf\")"
   ]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "codemirror_mode": {
    "name": "ipython",
    "version": 3
   },
   "file_extension": ".py",
   "mimetype": "text/x-python",
   "name": "python",
   "nbconvert_exporter": "python",
   "pygments_lexer": "ipython3",
   "version": "3.10.12"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 2
}

# Absolute path to the notebook
output_path = r"c:\Users\Furkan Talha KASIM\Documents\GitHub\Chatbot\fine_tune_tr_chatbot.ipynb"

# Write correctly
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(notebook_structure, f, indent=1, ensure_ascii=False)

print(f"Notebook written to {output_path}")
