import customtkinter as ctk
from tkinter import messagebox, simpledialog
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
from deep_translator import GoogleTranslator
import random
import hashlib

# ==========================================
# 0. ĐƯỜNG DẪN FILE & KHỞI TẠO THƯ VIỆN
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_NAME = os.path.join(BASE_DIR, "vocab_data.json")
TEMP_AUDIO = os.path.join(BASE_DIR, "voice.mp3")
CACHE_DIR = os.path.join(BASE_DIR, "image_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

spell = SpellChecker()
pygame.mixer.init()
translator = GoogleTranslator(source='en', target='vi')

# ==========================================
# 1. CẤU HÌNH GIAO DIỆN
# ==========================================
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

BG_SIDEBAR = ("#F7F9FC", "#1E1E24")
BG_MAIN = ("#FFFFFF", "#141419")
BG_CARD = ("#F0F3F8", "#272730")
COLOR_ACCENT = "#5E5CE6"
COLOR_SUCCESS = ("#34C759", "#30D158")
COLOR_DANGER = ("#FF3B30", "#FF453A")
COLOR_WARNING = ("#FFCC00", "#FFD60A")
TEXT_SUB = ("#6E6E73", "#98989F")

FONT_LOGO = ("Segoe UI", 24, "bold")
FONT_TITLE = ("Segoe UI", 42, "bold")
FONT_VN = ("Segoe UI", 22, "bold")
FONT_POS = ("Segoe UI", 18, "italic")
FONT_H2 = ("Segoe UI", 18, "bold")
FONT_BODY = ("Segoe UI", 15)
FONT_ITALIC = ("Segoe UI", 16, "italic")
FONT_SMALL = ("Segoe UI", 12)

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
    example = "Chưa có ví dụ mẫu cho từ này."
    pos_str = "Chưa phân loại"
    try:
        res = requests.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}", timeout=3)
        if res.status_code == 200:
            d = res.json()[0]
            pos_list = list(set([POS_MAP.get(m['partOfSpeech'], m['partOfSpeech']) for m in d['meanings']]))
            pos_str = " | ".join(pos_list)
            for m in d['meanings']:
                for df in m['definitions']:
                    if 'example' in df: example = df['example']; break
                if example != "Chưa có ví dụ mẫu cho từ này.": break
    except: pass
    try:
        vn_meaning = translator.translate(word)
    except:
        vn_meaning = "Không thể dịch"

    return example, pos_str, vn_meaning

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

def get_cached_image_path(word):
    safe_name = hashlib.md5(word.encode()).hexdigest()
    return os.path.join(CACHE_DIR, f"{safe_name}.jpg")

def download_and_cache_image(word):
    cache_path = get_cached_image_path(word)
    if os.path.exists(cache_path):
        return cache_path
    
    try:
        url = f"https://image.pollinations.ai/prompt/a minimalist illustration of '{word}' isolated on white background?width=400&height=400&nologo=true"
        res = requests.get(url, timeout=8)
        if res.status_code == 200:
            img = Image.open(BytesIO(res.content))
            img = img.convert("RGB")
            img.save(cache_path, "JPEG", quality=85)
            return cache_path
    except Exception as e:
        print(f"Lỗi tải ảnh: {e}")
    return None

def load_image(word, label_widget):
    def task():
        cache_path = download_and_cache_image(word)
        if cache_path and os.path.exists(cache_path):
            try:
                pil_img = Image.open(cache_path)
                pil_img.thumbnail((400, 400))
                ctk_img = ctk.CTkImage(pil_img, size=(180, 180))
                app.after(0, lambda: label_widget.configure(image=ctk_img, text=""))
                return
            except:
                pass
        app.after(0, lambda: label_widget.configure(text="Không tải được ảnh", image=""))
    threading.Thread(target=task, daemon=True).start()

# ==========================================
# 3. LOGIC APP CHÍNH & CẢNH BÁO
# ==========================================
def refresh_list():
    for w in scroll_list.winfo_children(): w.destroy()
    items = list(vocab_data.items())
    
    for word, info in items:
        is_old = False
        try:
            diff_days = (datetime.now() - datetime.strptime(info['last_studied'], "%Y-%m-%d %H:%M")).days
            if diff_days >= 3: is_old = True
        except: pass

        icon = "⚠" if is_old else "✦"
        vn_text = info.get('vn_meaning', '')
        study_count = info.get('study_count', 0)
        # Hiển thị số lần học đẹp mắt
        if study_count >= 10:
            count_icon = "🏆"
        elif study_count >= 5:
            count_icon = "🔥"
        elif study_count > 0:
            count_icon = "📖"
        else:
            count_icon = "✨"
        count_display = f"{count_icon}{study_count}" if study_count > 0 else "✨0"
        
        display_text = f" {icon}  {word.capitalize()} - {vn_text.capitalize()}  [{count_display}]" if vn_text else f" {icon}  {word.capitalize()}  [{count_display}]"
        
        btn = ctk.CTkButton(scroll_list, text=display_text, 
                            anchor="w", fg_color="transparent", text_color=("black", "white"),
                            hover_color=BG_CARD, height=45, corner_radius=8, font=FONT_BODY,
                            command=lambda w=word: select_word(w))
        btn.pack(fill="x", pady=2, padx=5)

def edit_vn_meaning():
    if not current_word:
        return
    current_vn = vocab_data[current_word].get('vn_meaning', '')
    new_vn = simpledialog.askstring("Sửa nghĩa", f"Nhập nghĩa tiếng Việt cho từ '{current_word}':", initialvalue=current_vn)
    if new_vn and new_vn.strip():
        vocab_data[current_word]['vn_meaning'] = new_vn.strip()
        save_data(data_json)
        lbl_vn.configure(text=new_vn.strip().capitalize())
        refresh_list()

def select_word(word):
    global current_word
    current_word = word
    data = vocab_data[word]
    
    today = datetime.now().strftime("%Y-%m-%d")
    if today not in daily_tracker: daily_tracker[today] = []
    if word not in daily_tracker[today]:
        data['study_count'] = data.get('study_count', 0) + 1
        daily_tracker[today].append(word)
    
    data['last_studied'] = datetime.now().strftime("%Y-%m-%d %H:%M")
    save_data(data_json)
    refresh_list()

    frame_welcome.pack_forget()
    detail_container.pack(fill="both", expand=True, padx=40, pady=20)
    
    lbl_title.configure(text=word.lower())
    lbl_vn.configure(text=data.get('vn_meaning', 'Chưa cập nhật nghĩa').capitalize()) 
    lbl_pos_text.configure(text=data.get('pos', 'unknown'))
    lbl_ex.configure(text=f'"{data["sentence"]}"')
    
    stats_text = f"🔥 Số lần học: {data['study_count']}   •   🕒 Lần cuối: {data['last_studied']}"
    lbl_stats.configure(text=stats_text)
    
    lbl_alert.pack_forget()
    try:
        diff_days = (datetime.now() - datetime.strptime(data['last_studied'], "%Y-%m-%d %H:%M")).days
        if data.get('study_count', 0) >= 10 and diff_days >= 3:
            lbl_alert.configure(text="🚨 Cảnh báo: Từ này bạn đã học nhiều lần nhưng 3 ngày rồi chưa ôn lại!")
            lbl_alert.pack(anchor="w", padx=25, pady=(10, 0))
    except: pass
    
    txt_note.delete("1.0", "end")
    txt_note.insert("1.0", data.get("custom_sentence", ""))
    lbl_img.configure(image="", text="Đang tải ảnh...")
    
    play_sound_system(word)
    load_image(word, lbl_img)

def add_word():
    word = entry_add.get().strip().lower()
    if not word: return
    if spell.unknown([word]):
        corr = spell.correction(word)
        if corr and corr != word:
            if messagebox.askyesno("Sai chính tả?", f"Có phải ý bạn là '{corr}' không?"): word = corr
    
    if word not in vocab_data:
        ex, pos, vn = get_word_info(word)
        vocab_data[word] = {"sentence": ex, "pos": pos, "vn_meaning": vn, "last_studied": "", "study_count": 0, "custom_sentence": ""}
        save_data(data_json)
        
    entry_add.delete(0, 'end')
    refresh_list()
    select_word(word)

def delete_word():
    global current_word
    if current_word and messagebox.askyesno("Xác nhận", f"Xóa '{current_word}'?"):
        del vocab_data[current_word]
        save_data(data_json)
        detail_container.pack_forget()
        frame_welcome.pack(expand=True)
        refresh_list()
        current_word = None

# ==========================================
# 4. MINI GAME: THUẬT TOÁN ƯU TIÊN & TRẮC NGHIỆM
# ==========================================
class MiniGameWindow(ctk.CTkToplevel):
    def __init__(self, master, num_words):
        super().__init__(master)
        self.title("🎮 Mini Game Học Nhanh")
        self.geometry("600x500")
        self.transient(master)
        self.grab_set()
        
        self.questions = []
        self.current_idx = 0
        self.score = 0
        self.prepare_game(num_words)
        self.build_ui()
        self.load_question()

    def prepare_game(self, num_words):
        all_words = list(vocab_data.keys())
        if len(all_words) == 0:
            return
        
        def priority(w):
            count = vocab_data[w].get('study_count', 0)
            date_str = vocab_data[w].get('last_studied', '')
            if not date_str:
                days_ago = 9999
            else:
                try:
                    days_ago = (datetime.now() - datetime.strptime(date_str, "%Y-%m-%d %H:%M")).days
                except: days_ago = 9999
            return (count, -days_ago)
            
        sorted_words = sorted(all_words, key=priority)
        selected_words = sorted_words[:min(num_words, len(sorted_words))]
        
        for w in selected_words:
            options = [w]
            candidates = [x for x in all_words if x != w]
            random.shuffle(candidates)
            while len(options) < 4 and candidates:
                opt = candidates.pop()
                if opt not in options:
                    options.append(opt)
            random.shuffle(options)
            vn = vocab_data[w].get('vn_meaning', 'Chưa có nghĩa')
            self.questions.append((w, vn, options))

    def build_ui(self):
        self.lbl_progress = ctk.CTkLabel(self, text="Câu 0/0", font=FONT_BODY, text_color=TEXT_SUB)
        self.lbl_progress.pack(pady=(20, 5))
        
        self.lbl_question = ctk.CTkLabel(self, text="Từ nào có nghĩa là:\n...", font=FONT_TITLE, text_color=COLOR_ACCENT)
        self.lbl_question.pack(pady=(10, 30))
        
        self.btn_opts = []
        for i in range(4):
            btn = ctk.CTkButton(self, text="", height=50, corner_radius=15, font=FONT_H2, 
                                fg_color=BG_CARD, text_color=("black", "white"), hover_color=COLOR_ACCENT,
                                command=lambda idx=i: self.check_answer(idx))
            btn.pack(fill="x", padx=40, pady=8)
            self.btn_opts.append(btn)

    def load_question(self):
        if self.current_idx >= len(self.questions):
            messagebox.showinfo("Hoàn thành", f"🎉 Bạn đã ôn xong! Đúng {self.score}/{len(self.questions)} từ.")
            self.destroy()
            refresh_list()
            return
            
        q_word, q_vn, q_opts = self.questions[self.current_idx]
        self.lbl_progress.configure(text=f"Câu {self.current_idx + 1} / {len(self.questions)}")
        self.lbl_question.configure(text=f"Từ nào có nghĩa là:\n{q_vn.capitalize()}")
        
        for i in range(4):
            self.btn_opts[i].configure(text=q_opts[i].capitalize())

    def check_answer(self, btn_idx):
        correct_word, _, options = self.questions[self.current_idx]
        selected_word = options[btn_idx]
        
        if selected_word == correct_word:
            today = datetime.now().strftime("%Y-%m-%d")
            if today not in daily_tracker: daily_tracker[today] = []
            if correct_word not in daily_tracker[today]:
                vocab_data[correct_word]['study_count'] = vocab_data[correct_word].get('study_count', 0) + 1
                daily_tracker[today].append(correct_word)
                vocab_data[correct_word]['last_studied'] = datetime.now().strftime("%Y-%m-%d %H:%M")
                save_data(data_json)
                
            self.score += 1
            play_sound_system(correct_word)
        else:
            messagebox.showerror("Sai rồi", f"❌ Đáp án đúng phải là:\n{correct_word.capitalize()}")
            
        self.current_idx += 1
        self.load_question()

def open_game_setup():
    if len(vocab_data) < 4:
        messagebox.showwarning("Thiếu dữ liệu", "Bạn cần thêm ít nhất 4 từ vựng để có thể chơi game!")
        return
    
    max_words = min(len(vocab_data), 50)
    num = simpledialog.askinteger("Cài đặt Game", f"Bạn muốn ôn bao nhiêu từ hôm nay? (Tối đa {max_words})", minvalue=1, maxvalue=max_words)
    if num:
        MiniGameWindow(app, num)

# ==========================================
# 5. GIAO DIỆN CHÍNH (MAIN UI)
# ==========================================
app = ctk.CTk()
app.title("Vocab Master Premium")
app.geometry("1100x750")
app.grid_columnconfigure(1, weight=1)
app.grid_rowconfigure(0, weight=1)

# ----- SIDEBAR -----
sidebar = ctk.CTkFrame(app, width=350, corner_radius=0, fg_color=BG_SIDEBAR)
sidebar.grid(row=0, column=0, sticky="nsew")
sidebar.grid_propagate(False)

ctk.CTkLabel(sidebar, text="V O C A B", font=FONT_LOGO, text_color=COLOR_ACCENT).pack(pady=(40, 5))
ctk.CTkLabel(sidebar, text="Master Your English", font=("Segoe UI", 12), text_color=TEXT_SUB).pack(pady=(0, 25))

add_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
add_frame.pack(fill="x", padx=20, pady=10)
entry_add = ctk.CTkEntry(add_frame, placeholder_text="Nhập từ mới để tra...", height=45, corner_radius=12, font=FONT_BODY, border_width=1)
entry_add.pack(side="left", fill="x", expand=True)
btn_add = ctk.CTkButton(add_frame, text="+", width=45, height=45, corner_radius=12, font=("Segoe UI", 20, "bold"), fg_color=COLOR_ACCENT, command=add_word)
btn_add.pack(side="right", padx=(10, 0))
app.bind('<Return>', lambda e: add_word())

ctk.CTkLabel(sidebar, text="TỪ VỰNG CỦA BẠN", font=("Segoe UI", 12, "bold"), text_color=TEXT_SUB, anchor="w").pack(fill="x", padx=25, pady=(20, 5))
scroll_list = ctk.CTkScrollableFrame(sidebar, fg_color="transparent")
scroll_list.pack(fill="both", expand=True, padx=15, pady=(0, 10))

btn_game = ctk.CTkButton(sidebar, text="🎮 GAME ÔN TẬP NHANH", height=50, corner_radius=10, 
                         fg_color=COLOR_SUCCESS, hover_color="#28a745", font=FONT_H2, command=open_game_setup)
btn_game.pack(fill="x", padx=20, pady=(0, 20))

# ----- MAIN VIEW -----
main_view = ctk.CTkFrame(app, corner_radius=0, fg_color=BG_MAIN)
main_view.grid(row=0, column=1, sticky="nsew")

frame_welcome = ctk.CTkFrame(main_view, fg_color="transparent")
frame_welcome.pack(expand=True)
ctk.CTkLabel(frame_welcome, text="📚", font=("Segoe UI", 70)).pack(pady=10)
ctk.CTkLabel(frame_welcome, text="Sẵn sàng học chưa?", font=("Segoe UI", 24, "bold")).pack(pady=5)
ctk.CTkLabel(frame_welcome, text="Chọn một từ, thêm từ mới hoặc chơi Game để ôn bài.", font=FONT_BODY, text_color=TEXT_SUB).pack()

detail_container = ctk.CTkScrollableFrame(main_view, fg_color="transparent")

# --- Card 1: Header ---
c1 = ctk.CTkFrame(detail_container, corner_radius=15, fg_color="transparent")
c1.pack(fill="x", pady=(10, 20))

header_left = ctk.CTkFrame(c1, fg_color="transparent")
header_left.pack(side="left", padx=(0, 15))

lbl_title = ctk.CTkLabel(header_left, text="word", font=FONT_TITLE)
lbl_title.pack(anchor="w")

vn_frame = ctk.CTkFrame(header_left, fg_color="transparent")
vn_frame.pack(anchor="w", pady=(0, 5))
lbl_vn = ctk.CTkLabel(vn_frame, text="nghĩa tiếng việt", font=FONT_VN, text_color=COLOR_SUCCESS[0])
lbl_vn.pack(side="left")
edit_btn = ctk.CTkButton(vn_frame, text="✏️", width=30, height=30, corner_radius=15,
                         fg_color="transparent", hover_color=BG_CARD, text_color=COLOR_ACCENT,
                         command=edit_vn_meaning)
edit_btn.pack(side="left", padx=(10, 0))

pos_frame = ctk.CTkFrame(c1, corner_radius=20, fg_color=COLOR_ACCENT)
pos_frame.pack(side="left", pady=(10,0))
lbl_pos_text = ctk.CTkLabel(pos_frame, text="pos", font=("Segoe UI", 14), text_color="white", width=80, height=30)
lbl_pos_text.pack(padx=15, pady=2)

btn_pronounce = ctk.CTkButton(c1, text="🔊 Phát âm", width=110, height=40, corner_radius=20, 
                              fg_color=BG_CARD, text_color=("black", "white"), hover_color=COLOR_ACCENT,
                              command=lambda: play_sound_system(current_word))
btn_pronounce.pack(side="right", pady=20)

# --- Card 2: Hình ảnh, Ví dụ & Cảnh báo ---
c2_wrap = ctk.CTkFrame(detail_container, fg_color="transparent")
c2_wrap.pack(fill="x", pady=10)

img_frame = ctk.CTkFrame(c2_wrap, corner_radius=15, fg_color=BG_CARD, width=180, height=180)
img_frame.pack(side="left", fill="y")
img_frame.pack_propagate(False)
lbl_img = ctk.CTkLabel(img_frame, text="⌛", font=("Segoe UI", 14), text_color=TEXT_SUB)
lbl_img.pack(expand=True)

c2_info = ctk.CTkFrame(c2_wrap, corner_radius=15, fg_color=BG_CARD)
c2_info.pack(side="left", fill="both", expand=True, padx=(20, 0))

lbl_alert = ctk.CTkLabel(c2_info, text="", font=("Segoe UI", 13, "bold"), text_color=COLOR_DANGER[0], wraplength=450, justify="left")

lbl_stats = ctk.CTkLabel(c2_info, text="Stats", font=("Segoe UI", 13), text_color=TEXT_SUB)
lbl_stats.pack(anchor="w", padx=25, pady=(20, 5))

lbl_ex = ctk.CTkLabel(c2_info, text="Example", font=FONT_ITALIC, wraplength=450, justify="left")
lbl_ex.pack(anchor="w", padx=25, pady=(5, 15))

ctk.CTkButton(c2_info, text="▶ Nghe câu ví dụ", width=140, height=35, corner_radius=8, 
              fg_color="transparent", border_width=1.5, border_color=COLOR_ACCENT, text_color=COLOR_ACCENT,
              hover_color=COLOR_ACCENT, hover=True,
              command=lambda: play_sound_system(vocab_data[current_word]['sentence'] if current_word else "")).pack(anchor="w", padx=25, pady=(0, 20))

# --- Card 3: Ghi chú ---
c3 = ctk.CTkFrame(detail_container, corner_radius=15, fg_color=BG_CARD)
c3.pack(fill="x", pady=20)

ctk.CTkLabel(c3, text="📝 Ghi chú cá nhân", font=FONT_H2).pack(anchor="w", padx=25, pady=(20, 10))
txt_note = ctk.CTkTextbox(c3, height=120, corner_radius=10, border_width=0, fg_color=BG_MAIN, font=FONT_BODY)
txt_note.pack(fill="x", padx=25, pady=(0, 20))

btn_f = ctk.CTkFrame(c3, fg_color="transparent")
btn_f.pack(fill="x", padx=25, pady=(0, 25))

def save_note():
    if current_word:
        vocab_data[current_word]["custom_sentence"] = txt_note.get("1.0", "end-1c")
        save_data(data_json)
        messagebox.showinfo("Thành công", "Đã lưu ghi chú!")

ctk.CTkButton(btn_f, text="💾 Lưu thay đổi", fg_color=COLOR_SUCCESS, hover_color="#28a745", height=40, width=140, corner_radius=8, font=FONT_BODY,
              command=save_note).pack(side="left")

ctk.CTkButton(btn_f, text="🗑 Xóa từ", fg_color="transparent", text_color=COLOR_DANGER[0], border_width=1, border_color=COLOR_DANGER[0], hover_color="#FADBD8", height=40, width=100, corner_radius=8, font=FONT_BODY, command=delete_word).pack(side="right")

refresh_list()
app.mainloop()