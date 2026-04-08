import customtkinter as ctk
from tkinter import messagebox
import json
import os
from datetime import datetime
import requests
from io import BytesIO
from PIL import Image
import threading
from spellchecker import SpellChecker
import random
import re
from gtts import gTTS
import pygame # Thư viện phát âm thanh cực nhanh

# --- 1. THIẾT LẬP HỆ THỐNG ---
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

pygame.mixer.init() # Khởi tạo bộ trộn âm thanh
spell = SpellChecker() 
FILE_NAME = "vocab_data.json"
TEMP_AUDIO = "temp_voice.mp3" # File âm thanh tạm

FONT_HEADING = ("Segoe UI", 36, "bold")
FONT_SUBHEADING = ("Segoe UI", 20, "bold")
FONT_BODY = ("Segoe UI", 15)
FONT_ITALIC = ("Segoe UI", 15, "italic")

POS_MAP = {
    "noun": "Danh từ", "verb": "Động từ", "adjective": "Tính từ",
    "adverb": "Trạng từ", "pronoun": "Đại từ", "preposition": "Giới từ",
    "conjunction": "Liên từ", "interjection": "Thán từ"
}

# --- HÀM PHÁT ÂM THANH KHÔNG DELAY ---
def read_text_async(text):
    if not text: return
    
    def speak():
        try:
            # Tạo file âm thanh từ Google TTS
            tts = gTTS(text=text, lang='en')
            tts.save(TEMP_AUDIO)
            
            # Phát âm thanh bằng pygame (không bị delay như pyttsx3)
            pygame.mixer.music.load(TEMP_AUDIO)
            pygame.mixer.music.play()
            
            while pygame.mixer.music.get_busy():
                continue
            pygame.mixer.music.unload() # Giải phóng file để lần sau dùng tiếp
        except Exception as e:
            print(f"Lỗi âm thanh: {e}")

    threading.Thread(target=speak, daemon=True).start()

# --- 2. XỬ LÝ DỮ LIỆU ---
def load_data():
    if os.path.exists(FILE_NAME):
        with open(FILE_NAME, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "vocab_data" not in data: data["vocab_data"] = {}
            if "daily_study_tracker" not in data: data["daily_study_tracker"] = {}
            return data
    return {"vocab_data": {}, "daily_study_tracker": {}}

def save_data(data):
    with open(FILE_NAME, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

data_json = load_data()
vocab_data = data_json["vocab_data"]
daily_study_tracker = data_json["daily_study_tracker"]
current_word = None

def get_word_info(word):
    try:
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            data = response.json()
            pos_set = set()
            example_sentence = "Chưa có câu ví dụ tự động."
            for meaning in data[0].get("meanings", []):
                pos_raw = meaning.get("partOfSpeech", "unknown").lower()
                pos_set.add(POS_MAP.get(pos_raw, pos_raw))
                for defs in meaning.get("definitions", []):
                    if "example" in defs and example_sentence == "Chưa có câu ví dụ tự động.":
                        example_sentence = defs["example"]
            return example_sentence, " | ".join(pos_set)
    except: pass
    return "Chưa có câu ví dụ tự động.", "Chưa rõ"

def update_word_list(*args):
    for widget in scroll_list.winfo_children(): widget.destroy()
    items = list(vocab_data.items())
    sort_type = sort_var.get()
    if "Tên" in sort_type: items.sort(key=lambda x: x[0])
    elif "Ngày" in sort_type: items.sort(key=lambda x: datetime.strptime(x[1].get("last_studied", "2000-01-01 00:00"), "%Y-%m-%d %H:%M"))
    elif "Số lần" in sort_type: items.sort(key=lambda x: x[1].get("study_count", 0))
    
    for word, info in items:
        count = info.get("study_count", 0)
        display_text = f"    {word} ({count} lần)"
        btn = ctk.CTkButton(
            scroll_list, text=display_text, anchor="w", fg_color="transparent", 
            text_color=("gray10", "gray90"), font=("Segoe UI", 15),
            hover_color=("gray85", "gray25"), height=40, corner_radius=8,
            command=lambda w=word: show_word_detail(w)
        )
        btn.pack(fill="x", pady=2, padx=5)

def on_add_word():
    word = entry_word.get().strip().lower()
    if not word: return
    if spell.unknown([word]):
        corrected = spell.correction(word)
        if corrected and corrected != word:
            if messagebox.askyesno("Gợi ý", f"Ý bạn là '{corrected}'?"): word = corrected
            else: return 
    entry_word.delete(0, 'end')
    if word not in vocab_data:
        sentence, pos = get_word_info(word)
        vocab_data[word] = {
            "sentence": sentence, "pos": pos,
            "last_studied": datetime.now().strftime("%Y-%m-%d %H:%M"), 
            "custom_sentence": "", "study_count": 0
        }
        save_data(data_json)
    update_word_list()
    show_word_detail(word)

def show_word_detail(word):
    global current_word
    current_word = word
    data = vocab_data[word]
    
    # Logic tăng lần học (1 lần/ngày)
    today = datetime.now().strftime("%Y-%m-%d")
    if today not in daily_study_tracker: daily_study_tracker[today] = []
    if word not in daily_study_tracker[today]:
        data["study_count"] += 1
        daily_study_tracker[today].append(word)
    
    data["last_studied"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    save_data(data_json)
    
    frame_welcome.pack_forget()
    frame_detail_inner.pack(fill="both", expand=True, padx=20, pady=20)
    
    lbl_word_title.configure(text=word.capitalize())
    lbl_pos.configure(text=data.get('pos', 'Chưa rõ'))
    lbl_auto_sentence.configure(text=f'"{data["sentence"]}"')
    lbl_count_val.configure(text=f"{data['study_count']} lần")
    lbl_date_val.configure(text=data['last_studied'])
    
    txt_custom_sentence.delete("1.0", "end")
    txt_custom_sentence.insert("1.0", data.get("custom_sentence", ""))
    
    # Tải ảnh ngầm
    threading.Thread(target=lambda: load_img(word), daemon=True).start()
    # Đọc ngay lập tức
    read_text_async(word)

def load_img(word):
    try:
        res = requests.get(f"https://picsum.photos/seed/{word}/300/300", timeout=5)
        img = Image.open(BytesIO(res.content))
        ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(180, 180))
        app.after(0, lambda: lbl_image.configure(image=ctk_img, text=""))
    except:
        app.after(0, lambda: lbl_image.configure(text="[Lỗi ảnh]"))

# --- GIAO DIỆN CHÍNH ---
app = ctk.CTk()
app.title("Vocab Master Pro")
app.geometry("1100x750")
app.grid_columnconfigure(1, weight=1)
app.grid_rowconfigure(0, weight=1)

# Sidebar
sidebar = ctk.CTkFrame(app, width=300, corner_radius=0)
sidebar.grid(row=0, column=0, sticky="nsew")
ctk.CTkLabel(sidebar, text="⚡ Vocab Pro", font=("Segoe UI", 25, "bold")).pack(pady=20)

entry_word = ctk.CTkEntry(sidebar, placeholder_text="Nhập từ mới...", height=40)
entry_word.pack(fill="x", padx=20, pady=10)
app.bind('<Return>', lambda e: on_add_word())

sort_var = ctk.StringVar(value="Sắp xếp: Ngày học")
ctk.CTkOptionMenu(sidebar, variable=sort_var, values=["Sắp xếp: Tên", "Sắp xếp: Ngày học", "Sắp xếp: Số lần"], command=update_word_list).pack(fill="x", padx=20, pady=10)

scroll_list = ctk.CTkScrollableFrame(sidebar, fg_color="transparent")
scroll_list.pack(fill="both", expand=True, padx=10, pady=10)

# Main
main_view = ctk.CTkFrame(app, corner_radius=20, fg_color=("gray95", "gray10"))
main_view.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

frame_welcome = ctk.CTkLabel(main_view, text="Chọn từ vựng để bắt đầu", font=FONT_SUBHEADING)
frame_welcome.pack(expand=True)

frame_detail_inner = ctk.CTkFrame(main_view, fg_color="transparent")

# Header Card
card_head = ctk.CTkFrame(frame_detail_inner, corner_radius=15)
card_head.pack(fill="x", pady=10, padx=10)
lbl_word_title = ctk.CTkLabel(card_head, text="Word", font=FONT_HEADING)
lbl_word_title.pack(side="left", padx=20, pady=20)
lbl_pos = ctk.CTkLabel(card_head, text="pos", font=FONT_ITALIC, text_color="gray")
lbl_pos.pack(side="left", pady=20)
ctk.CTkButton(card_head, text="🔊 Đọc", width=80, command=lambda: read_text_async(current_word)).pack(side="right", padx=20)

# Info Card
frame_info = ctk.CTkFrame(frame_detail_inner, fg_color="transparent")
frame_info.pack(fill="x", padx=10)
lbl_image = ctk.CTkLabel(frame_info, text="⌛", width=180, height=180, bg_color="gray20", corner_radius=15)
lbl_image.pack(side="left", padx=10)

stats = ctk.CTkFrame(frame_info, corner_radius=15)
stats.pack(side="left", fill="both", expand=True, padx=10)
lbl_count_val = ctk.CTkLabel(stats, text="0 lần", font=FONT_SUBHEADING)
lbl_count_val.pack(pady=10)
lbl_date_val = ctk.CTkLabel(stats, text="Date", font=FONT_BODY)
lbl_date_val.pack()
lbl_auto_sentence = ctk.CTkLabel(stats, text="Example", font=FONT_ITALIC, wraplength=300)
lbl_auto_sentence.pack(pady=10)
ctk.CTkButton(stats, text="▶ Đọc câu", width=80, fg_color="gray30", command=lambda: read_text_async(vocab_data[current_word]['sentence'])).pack()

# Note Card
card_note = ctk.CTkFrame(frame_detail_inner, corner_radius=15)
card_note.pack(fill="both", expand=True, padx=10, pady=20)
txt_custom_sentence = ctk.CTkTextbox(card_note, height=100)
txt_custom_sentence.pack(fill="x", padx=20, pady=20)
ctk.CTkButton(card_note, text="Lưu ghi chú", command=lambda: [vocab_data[current_word].update({"custom_sentence": txt_custom_sentence.get("1.0", "end-1c")}), save_data(data_json)]).pack(pady=10)

update_word_list()
app.mainloop()