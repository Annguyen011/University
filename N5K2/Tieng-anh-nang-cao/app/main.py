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
import pygame
from gtts import gTTS

# ==========================================
# 0. ĐƯỜNG DẪN FILE & KHỞI TẠO THƯ VIỆN
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_NAME = os.path.join(BASE_DIR, "vocab_data.json")
TEMP_AUDIO = os.path.join(BASE_DIR, "voice.mp3")

spell = SpellChecker()
pygame.mixer.init()

# ==========================================
# 1. CẤU HÌNH GIAO DIỆN HIỆN ĐẠI
# ==========================================
ctk.set_appearance_mode("System")  # Chuyển theo hệ điều hành (Light/Dark)
ctk.set_default_color_theme("blue")

# --- Bảng màu (Light Mode, Dark Mode) ---
BG_SIDEBAR = ("#F7F9FC", "#1E1E24")
BG_MAIN = ("#FFFFFF", "#141419")
BG_CARD = ("#F0F3F8", "#272730")
COLOR_ACCENT = "#5E5CE6"  # Tím xanh hiện đại
COLOR_SUCCESS = ("#34C759", "#30D158")
COLOR_DANGER = ("#FF3B30", "#FF453A")
TEXT_SUB = ("#6E6E73", "#98989F")

# --- Typography ---
FONT_LOGO = ("Segoe UI", 24, "bold")
FONT_TITLE = ("Segoe UI", 42, "bold")
FONT_POS = ("Segoe UI", 18, "italic")
FONT_H2 = ("Segoe UI", 18, "bold")
FONT_BODY = ("Segoe UI", 15)
FONT_ITALIC = ("Segoe UI", 16, "italic")

POS_MAP = {
    "noun": "Danh từ", "verb": "Động từ", "adjective": "Tính từ",
    "adverb": "Trạng từ", "pronoun": "Đại từ", "preposition": "Giới từ",
    "conjunction": "Liên từ", "interjection": "Thán từ"
}

# ==========================================
# 2. XỬ LÝ DỮ LIỆU & API
# ==========================================
def load_data():
    if os.path.exists(FILE_NAME):
        with open(FILE_NAME, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "vocab_data" not in data: data["vocab_data"] = {}
            if "daily_tracker" not in data: data["daily_tracker"] = {}
            return data
    return {"vocab_data": {}, "daily_tracker": {}}

def save_data(data):
    with open(FILE_NAME, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

data_json = load_data()
vocab_data = data_json["vocab_data"]
daily_tracker = data_json["daily_tracker"]
current_word = None

def get_word_info(word):
    try:
        res = requests.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}", timeout=3)
        if res.status_code == 200:
            d = res.json()[0]
            pos_list = list(set([POS_MAP.get(m['partOfSpeech'], m['partOfSpeech']) for m in d['meanings']]))
            example = "Chưa có ví dụ mẫu cho từ này."
            for m in d['meanings']:
                for df in m['definitions']:
                    if 'example' in df: example = df['example']; break
                if example != "Chưa có ví dụ mẫu cho từ này.": break
            return example, " | ".join(pos_list)
    except: pass
    return "Hãy tự viết một ví dụ để nhớ lâu hơn nhé.", "Chưa phân loại"

def play_sound_system(text):
    if not text: return
    def task():
        try:
            tts = gTTS(text=text, lang='en')
            tts.save(TEMP_AUDIO)
            pygame.mixer.music.load(TEMP_AUDIO)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
            pygame.mixer.music.unload()
        except Exception as e: print(f"Audio error: {e}")
    threading.Thread(target=task, daemon=True).start()

# ==========================================
# 3. LOGIC APP
# ==========================================
def refresh_list():
    for w in scroll_list.winfo_children(): w.destroy()
    items = list(vocab_data.items())
    items.sort(key=lambda x: x[1].get('last_studied', ''))
    
    for word, info in items:
        count = info.get('study_count', 0)
        is_old = False
        try:
            diff = datetime.now() - datetime.strptime(info['last_studied'], "%Y-%m-%d %H:%M")
            if diff.days > 5: is_old = True
        except: pass

        icon = "⚠" if is_old else "✦"
        btn = ctk.CTkButton(scroll_list, text=f" {icon}  {word.capitalize()}", 
                            anchor="w", fg_color="transparent", text_color=("black", "white"),
                            hover_color=BG_CARD, height=45, corner_radius=8, font=FONT_BODY,
                            command=lambda w=word: select_word(w))
        btn.pack(fill="x", pady=2, padx=5)

def select_word(word):
    global current_word
    current_word = word
    data = vocab_data[word]
    
    # Cập nhật tiến độ
    today = datetime.now().strftime("%Y-%m-%d")
    if today not in daily_tracker: daily_tracker[today] = []
    if word not in daily_tracker[today]:
        data['study_count'] = data.get('study_count', 0) + 1
        daily_tracker[today].append(word)
    
    data['last_studied'] = datetime.now().strftime("%Y-%m-%d %H:%M")
    save_data(data_json)
    refresh_list()

    # Chuyển đổi View
    frame_welcome.pack_forget()
    detail_container.pack(fill="both", expand=True, padx=40, pady=20)
    
    # Cập nhật UI
    lbl_title.configure(text=word.lower())
    lbl_pos.configure(text=data.get('pos', 'unknown'))
    lbl_ex.configure(text=f'"{data["sentence"]}"')
    
    stats_text = f"🔥 Số lần ôn tập: {data['study_count']}   •   🕒 Lần cuối: {data['last_studied']}"
    lbl_stats.configure(text=stats_text)
    
    txt_note.delete("1.0", "end")
    txt_note.insert("1.0", data.get("custom_sentence", ""))
    
    # Đặt lại ảnh mặc định trong lúc tải
    lbl_img.configure(image="", text="Đang tải ảnh...")
    
    play_sound_system(word)
    threading.Thread(target=lambda: load_image(word), daemon=True).start()

def load_image(word):
    try:
        res = requests.get(f"https://picsum.photos/seed/{word}/400/400", timeout=5)
        img_data = Image.open(BytesIO(res.content))
        # Bo góc ảnh (Mô phỏng bằng cách tạo ảnh vuông vắn cho CTkImage)
        img = ctk.CTkImage(img_data, size=(180, 180))
        app.after(0, lambda: lbl_img.configure(image=img, text=""))
    except: 
        app.after(0, lambda: lbl_img.configure(text="Không tìm thấy ảnh"))

def add_word():
    word = entry_add.get().strip().lower()
    if not word: return
    
    # Kiểm tra chính tả
    if spell.unknown([word]):
        corr = spell.correction(word)
        if corr and corr != word:
            if messagebox.askyesno("Sai chính tả?", f"Có phải ý bạn là '{corr}' không?"): 
                word = corr
    
    if word not in vocab_data:
        ex, pos = get_word_info(word)
        vocab_data[word] = {"sentence": ex, "pos": pos, "last_studied": "", "study_count": 0, "custom_sentence": ""}
        save_data(data_json)
        
    entry_add.delete(0, 'end')
    refresh_list()
    select_word(word)

def delete_word():
    if current_word and messagebox.askyesno("Xác nhận", f"Bạn có chắc chắn muốn xóa từ '{current_word}' khỏi bộ nhớ?"):
        del vocab_data[current_word]
        save_data(data_json)
        detail_container.pack_forget()
        frame_welcome.pack(expand=True)
        refresh_list()

# ==========================================
# 4. GIAO DIỆN CHÍNH (MAIN UI)
# ==========================================
app = ctk.CTk()
app.title("Vocab Master Premium")
app.geometry("1100x750")
app.grid_columnconfigure(1, weight=1)
app.grid_rowconfigure(0, weight=1)

# ----- SIDEBAR (CỘT TRÁI) -----
sidebar = ctk.CTkFrame(app, width=320, corner_radius=0, fg_color=BG_SIDEBAR)
sidebar.grid(row=0, column=0, sticky="nsew")
sidebar.grid_propagate(False)

# Logo
ctk.CTkLabel(sidebar, text="V O C A B", font=FONT_LOGO, text_color=COLOR_ACCENT).pack(pady=(40, 5))
ctk.CTkLabel(sidebar, text="Master Your English", font=("Segoe UI", 12), text_color=TEXT_SUB).pack(pady=(0, 25))

# Ô nhập từ
add_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
add_frame.pack(fill="x", padx=20, pady=10)
entry_add = ctk.CTkEntry(add_frame, placeholder_text="Nhập từ mới để tra...", height=45, corner_radius=12, font=FONT_BODY, border_width=1)
entry_add.pack(side="left", fill="x", expand=True)
btn_add_icon = ctk.CTkButton(add_frame, text="+", width=45, height=45, corner_radius=12, font=("Segoe UI", 20, "bold"), fg_color=COLOR_ACCENT, command=add_word)
btn_add_icon.pack(side="right", padx=(10, 0))
app.bind('<Return>', lambda e: add_word())

# Danh sách từ
ctk.CTkLabel(sidebar, text="TỪ VỰNG CỦA BẠN", font=("Segoe UI", 12, "bold"), text_color=TEXT_SUB, anchor="w").pack(fill="x", padx=25, pady=(20, 5))
scroll_list = ctk.CTkScrollableFrame(sidebar, fg_color="transparent")
scroll_list.pack(fill="both", expand=True, padx=15, pady=(0, 15))


# ----- MAIN VIEW (MÀN HÌNH CHÍNH) -----
main_view = ctk.CTkFrame(app, corner_radius=0, fg_color=BG_MAIN)
main_view.grid(row=0, column=1, sticky="nsew")

# Màn hình chờ (Welcome)
frame_welcome = ctk.CTkFrame(main_view, fg_color="transparent")
frame_welcome.pack(expand=True)
ctk.CTkLabel(frame_welcome, text="📚", font=("Segoe UI", 70)).pack(pady=10)
ctk.CTkLabel(frame_welcome, text="Sẵn sàng học chưa?", font=("Segoe UI", 24, "bold")).pack(pady=5)
ctk.CTkLabel(frame_welcome, text="Chọn một từ bên trái hoặc thêm từ mới để bắt đầu.", font=FONT_BODY, text_color=TEXT_SUB).pack()

# Vùng hiển thị chi tiết (Ẩn lúc đầu)
detail_container = ctk.CTkScrollableFrame(main_view, fg_color="transparent")

# --- Card 1: Header (Từ vựng & Phát âm) ---
c1 = ctk.CTkFrame(detail_container, corner_radius=15, fg_color="transparent")
c1.pack(fill="x", pady=(10, 20))

lbl_title = ctk.CTkLabel(c1, text="word", font=FONT_TITLE)
lbl_title.pack(side="left", padx=(0, 15))

lbl_pos = ctk.CTkFrame(c1, corner_radius=20, fg_color=COLOR_ACCENT)
lbl_pos.pack(side="left")
lbl_pos_text = ctk.CTkLabel(lbl_pos, text="pos", font=("Segoe UI", 14), text_color="white", width=80, height=30)
lbl_pos_text.pack(padx=15, pady=2)
lbl_pos = lbl_pos_text # Gán lại reference để dễ update

btn_pronounce = ctk.CTkButton(c1, text="🔊 Phát âm", width=110, height=40, corner_radius=20, 
                              fg_color=BG_CARD, text_color=("black", "white"), hover_color=COLOR_ACCENT,
                              command=lambda: play_sound_system(current_word))
btn_pronounce.pack(side="right", pady=10)


# --- Card 2: Hình ảnh & Ví dụ ---
c2_wrap = ctk.CTkFrame(detail_container, fg_color="transparent")
c2_wrap.pack(fill="x", pady=10)

# Khung chứa ảnh
img_frame = ctk.CTkFrame(c2_wrap, corner_radius=15, fg_color=BG_CARD, width=180, height=180)
img_frame.pack(side="left", fill="y")
img_frame.pack_propagate(False)
lbl_img = ctk.CTkLabel(img_frame, text="⌛", font=("Segoe UI", 20))
lbl_img.pack(expand=True)

# Khung chứa thông tin
c2_info = ctk.CTkFrame(c2_wrap, corner_radius=15, fg_color=BG_CARD)
c2_info.pack(side="left", fill="both", expand=True, padx=(20, 0))

lbl_stats = ctk.CTkLabel(c2_info, text="Stats", font=("Segoe UI", 13), text_color=TEXT_SUB)
lbl_stats.pack(anchor="w", padx=25, pady=(20, 5))

lbl_ex = ctk.CTkLabel(c2_info, text="Example", font=FONT_ITALIC, wraplength=450, justify="left")
lbl_ex.pack(anchor="w", padx=25, pady=(5, 15))

ctk.CTkButton(c2_info, text="▶ Nghe câu ví dụ", width=130, height=35, corner_radius=8, 
              fg_color="transparent", border_width=1, border_color=COLOR_ACCENT, text_color=COLOR_ACCENT,
              command=lambda: play_sound_system(vocab_data[current_word]['sentence'])).pack(anchor="w", padx=25, pady=(0, 20))


# --- Card 3: Ghi chú cá nhân ---
c3 = ctk.CTkFrame(detail_container, corner_radius=15, fg_color=BG_CARD)
c3.pack(fill="x", pady=20)

ctk.CTkLabel(c3, text="📝 Ghi chú cá nhân", font=FONT_H2).pack(anchor="w", padx=25, pady=(20, 10))

txt_note = ctk.CTkTextbox(c3, height=120, corner_radius=10, border_width=0, fg_color=BG_MAIN, font=FONT_BODY)
txt_note.pack(fill="x", padx=25, pady=(0, 20))

# Nút hành động
btn_f = ctk.CTkFrame(c3, fg_color="transparent")
btn_f.pack(fill="x", padx=25, pady=(0, 25))

ctk.CTkButton(btn_f, text="💾 Lưu thay đổi", fg_color=COLOR_SUCCESS, hover_color="#28a745", height=40, width=140, corner_radius=8, font=FONT_BODY,
              command=lambda: [vocab_data[current_word].update({"custom_sentence": txt_note.get("1.0", "end-1c")}), save_data(data_json), messagebox.showinfo("Thành công", "Đã lưu ghi chú!")]).pack(side="left")

ctk.CTkButton(btn_f, text="🗑 Xóa từ", fg_color="transparent", text_color=COLOR_DANGER[0], border_width=1, border_color=COLOR_DANGER[0], hover_color="#FADBD8", height=40, width=100, corner_radius=8, font=FONT_BODY, command=delete_word).pack(side="right")


# Khởi chạy ứng dụng
refresh_list()
app.mainloop()