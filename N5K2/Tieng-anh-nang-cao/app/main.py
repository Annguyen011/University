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
# 0. ĐƯỜNG DẪN FILE & KHỞI TẠO
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_NAME = os.path.join(BASE_DIR, "vocab_data.json")
TEMP_AUDIO = os.path.join(BASE_DIR, "voice.mp3")
CACHE_DIR = os.path.join(BASE_DIR, "image_cache")
AUDIO_CACHE_DIR = os.path.join(BASE_DIR, "audio_cache")

os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(AUDIO_CACHE_DIR, exist_ok=True)

spell = SpellChecker()
pygame.mixer.init()
translator = GoogleTranslator(source='en', target='vi')

ui_row_refs = {'vocab': {}, 'phrase': {}}

# ==========================================
# 1. CẤU HÌNH GIAO DIỆN
# ==========================================
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

BG_SIDEBAR = ("#F7F9FC", "#1E1E24")
BG_MAIN = ("#FFFFFF", "#141419")
BG_CARD = ("#E6EBF5", "#272730")
COLOR_ACCENT = "#5E5CE6"
COLOR_SUCCESS = ("#34C759", "#30D158")
COLOR_DANGER = ("#FF3B30", "#FF453A")
TEXT_SUB = ("#6E6E73", "#98989F")

FONT_LOGO = ("Segoe UI", 24, "bold")
FONT_TITLE = ("Segoe UI", 42, "bold")
FONT_VN = ("Segoe UI", 22, "bold")
FONT_H2 = ("Segoe UI", 16, "bold")
FONT_BODY = ("Segoe UI", 14)
FONT_ITALIC = ("Segoe UI", 15, "italic")

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
            if "phrase_data" not in data: data["phrase_data"] = {}
            if "daily_tracker" not in data: data["daily_tracker"] = {}
            return data
    return {"vocab_data": {}, "phrase_data": {}, "daily_tracker": {}}

def save_data(data):
    with open(FILE_NAME, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

data_json = load_data()
vocab_data = data_json["vocab_data"]
phrase_data = data_json["phrase_data"]
daily_tracker = data_json["daily_tracker"]

current_item = None
current_type = None

def update_study_progress(text, item_type):
    target_dict = vocab_data if item_type == 'vocab' else phrase_data
    today = datetime.now().strftime("%Y-%m-%d")
    if today not in daily_tracker: daily_tracker[today] = []
    if text not in daily_tracker[today]:
        target_dict[text]['study_count'] = target_dict[text].get('study_count', 0) + 1
        daily_tracker[today].append(text)
    target_dict[text]['last_studied'] = datetime.now().strftime("%Y-%m-%d %H:%M")
    save_data(data_json)

def get_word_info(word):
    example = "Chưa có ví dụ tự động."
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
                if example != "Chưa có ví dụ tự động.": break
    except: pass
    try: vn_meaning = translator.translate(word)
    except: vn_meaning = "Lỗi dịch"
    return example, pos_str, vn_meaning

def get_phrase_info(phrase):
    try: vn_meaning = translator.translate(phrase)
    except: vn_meaning = "Lỗi dịch"
    return "Hãy tự đặt một câu ví dụ cho cụm từ này.", "Cụm từ / Câu", vn_meaning

def play_sound_system(text):
    if not text: return
    safe_name = hashlib.md5(text.encode()).hexdigest()
    audio_path = os.path.join(AUDIO_CACHE_DIR, f"{safe_name}.mp3")
    def task():
        try:
            if not os.path.exists(audio_path):
                tts = gTTS(text=text, lang='en')
                tts.save(audio_path)
            pygame.mixer.music.load(audio_path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy(): pygame.time.Clock().tick(10)
            pygame.mixer.music.unload()
        except: pass
    threading.Thread(target=task, daemon=True).start()

def get_cached_image_path(text):
    safe_name = hashlib.md5(text.encode()).hexdigest()
    return os.path.join(CACHE_DIR, f"{safe_name}.jpg")

def download_and_cache_image(text):
    cache_path = get_cached_image_path(text)
    if os.path.exists(cache_path): return cache_path
    try:
        search_term = text.replace(" ", "+")
        url = f"https://tse2.mm.bing.net/th?q={search_term}+png+isolated&w=800&h=800&c=7&rs=1"
        res = requests.get(url, timeout=4)
        if res.status_code == 200:
            img = Image.open(BytesIO(res.content)).convert("RGB")
            img.save(cache_path, "JPEG", quality=85)
            return cache_path
    except: pass
    return None

def load_image(text, label_widget):
    def task():
        cache_path = download_and_cache_image(text)
        if cache_path and os.path.exists(cache_path):
            try:
                pil_img = Image.open(cache_path)
                pil_img.thumbnail((400, 400))
                ctk_img = ctk.CTkImage(pil_img, size=(180, 180))
                app.after(0, lambda: label_widget.configure(image=ctk_img, text=""))
                return
            except: pass
        app.after(0, lambda: label_widget.configure(text="[ Không tải được ảnh ]", image="None"))
    threading.Thread(target=task, daemon=True).start()

# ==========================================
# 3. LOGIC GIAO DIỆN CHÍNH
# ==========================================
def render_scroll_list(scroll_widget, data_dict, item_type):
    for w in scroll_widget.winfo_children(): w.destroy()
    ui_row_refs[item_type].clear()
    
    items = list(data_dict.items())
    sort_type = sort_var.get()
    
    def get_date(item):
        d = item[1].get("last_studied", "")
        return d if d else "0000-00-00 00:00"

    if "Tên" in sort_type: items.sort(key=lambda x: x[0])
    elif "Gần nhất" in sort_type: items.sort(key=get_date, reverse=True)
    elif "Xa nhất" in sort_type: items.sort(key=get_date)
    elif "Nhiều nhất" in sort_type: items.sort(key=lambda x: x[1].get("study_count", 0), reverse=True)
    elif "Ít nhất" in sort_type: items.sort(key=lambda x: x[1].get("study_count", 0))

    items = items[:300] 

    header = ctk.CTkFrame(scroll_widget, fg_color="transparent")
    header.pack(fill="x", pady=(0, 5))
    header.grid_columnconfigure(1, weight=1) 
    header.grid_columnconfigure(2, weight=1) 
    
    ctk.CTkLabel(header, text="TT", font=("Segoe UI", 12, "bold"), text_color=TEXT_SUB, width=30).grid(row=0, column=0)
    ctk.CTkLabel(header, text="Nội dung", font=("Segoe UI", 12, "bold"), text_color=TEXT_SUB, anchor="w").grid(row=0, column=1, sticky="w")
    ctk.CTkLabel(header, text="Nghĩa VN", font=("Segoe UI", 12, "bold"), text_color=TEXT_SUB, anchor="w").grid(row=0, column=2, sticky="w")
    ctk.CTkLabel(header, text="Ôn", font=("Segoe UI", 12, "bold"), text_color=TEXT_SUB, width=30).grid(row=0, column=3)
    ctk.CTkLabel(header, text="", width=60).grid(row=0, column=4)
    
    for text, info in items:
        is_old = False
        try:
            diff_days = (datetime.now() - datetime.strptime(info.get('last_studied', "2000-01-01 00:00"), "%Y-%m-%d %H:%M")).days
            if diff_days >= 3: is_old = True
        except: pass

        icon = "⚠" if is_old else "✦"
        color_icon = COLOR_DANGER[0] if is_old else COLOR_ACCENT
        vn_text = info.get('vn_meaning', '')
        study_count = info.get('study_count', 0)
        
        row = ctk.CTkFrame(scroll_widget, fg_color=BG_CARD, corner_radius=8)
        row.pack(fill="x", pady=2)
        row.grid_columnconfigure(1, weight=1)
        row.grid_columnconfigure(2, weight=1)
        
        lbl_icon = ctk.CTkLabel(row, text=icon, font=("Segoe UI", 18, "bold"), text_color=color_icon, width=30)
        lbl_icon.grid(row=0, column=0, pady=8)
        lbl_w = ctk.CTkLabel(row, text=text.capitalize(), font=("Segoe UI", 14, "bold"), anchor="w", justify="left")
        lbl_w.grid(row=0, column=1, sticky="we", pady=8, padx=(0,5))
        lbl_v = ctk.CTkLabel(row, text=vn_text.capitalize(), font=FONT_BODY, text_color=TEXT_SUB, anchor="w", justify="left")
        lbl_v.grid(row=0, column=2, sticky="we", pady=8, padx=(0,5))
        lbl_count = ctk.CTkLabel(row, text=str(study_count), font=("Segoe UI", 14, "bold"), text_color=COLOR_SUCCESS[0], width=30)
        lbl_count.grid(row=0, column=3, pady=8)
        btn_view = ctk.CTkButton(row, text="Xem", width=50, height=28, font=("Segoe UI", 12, "bold"), fg_color=COLOR_ACCENT, hover_color="#4A48C0", command=lambda t=text, ty=item_type: select_item(t, ty))
        btn_view.grid(row=0, column=4, padx=5, pady=8)
        ui_row_refs[item_type][text] = {'icon': lbl_icon, 'count': lbl_count}

def refresh_list(*args):
    render_scroll_list(scroll_vocab, vocab_data, 'vocab')
    render_scroll_list(scroll_phrase, phrase_data, 'phrase')

def edit_vn_meaning():
    if not current_item: return
    target_dict = vocab_data if current_type == 'vocab' else phrase_data
    current_vn = target_dict[current_item].get('vn_meaning', '')
    dialog = ctk.CTkInputDialog(text=f"Sửa nghĩa tiếng Việt của '{current_item}':", title="Sửa nghĩa")
    new_vn = dialog.get_input()
    if new_vn and new_vn.strip():
        target_dict[current_item]['vn_meaning'] = new_vn.strip()
        save_data(data_json)
        lbl_vn.configure(text=new_vn.strip().capitalize())
        refresh_list()

def select_item(text, item_type):
    global current_item, current_type
    current_item = text
    current_type = item_type
    target_dict = vocab_data if item_type == 'vocab' else phrase_data
    update_study_progress(text, item_type)
    data = target_dict[text]
    
    if text in ui_row_refs[item_type]:
        ui_row_refs[item_type][text]['count'].configure(text=str(data['study_count']))
        ui_row_refs[item_type][text]['icon'].configure(text="✦", text_color=COLOR_ACCENT)

    frame_welcome.pack_forget()
    detail_container.pack(fill="both", expand=True, padx=40, pady=20)
    lbl_title.configure(text=text.lower())
    lbl_vn.configure(text=data.get('vn_meaning', '...').capitalize()) 
    lbl_pos_text.configure(text=data.get('pos', 'unknown'))
    lbl_ex.configure(text=f'"{data["sentence"]}"')
    lbl_stats.configure(text=f"🔥 Số lần: {data['study_count']}  •  🕒 Lần cuối: {data['last_studied']}")
    
    lbl_alert.pack_forget()
    try:
        if data.get('study_count', 0) >= 10 and (datetime.now() - datetime.strptime(data['last_studied'], "%Y-%m-%d %H:%M")).days >= 3:
            lbl_alert.configure(text="🚨 Cảnh báo: Từ/Cụm này lâu rồi chưa ôn lại!")
            lbl_alert.pack(anchor="w", padx=25, pady=(10, 0))
    except: pass
    
    txt_note.delete("1.0", "end")
    txt_note.insert("1.0", data.get("custom_sentence", ""))
    lbl_img.configure(image="", text="Đang tìm ảnh...")
    
    play_sound_system(text)
    load_image(text, lbl_img)

def add_item():
    # Đưa tất cả về chữ thường để loại bỏ lỗi phân biệt hoa thường
    text = entry_add.get().strip().lower()
    if not text: return
    
    # Quét xem từ đã tồn tại chưa (Im lặng chọn nếu đã có)
    if text in vocab_data:
        entry_add.delete(0, 'end')
        tab_view.set("Từ Đơn")
        select_item(text, 'vocab')
        return
    elif text in phrase_data:
        entry_add.delete(0, 'end')
        tab_view.set("Cụm Từ")
        select_item(text, 'phrase')
        return

    # Tự động nhận diện từ hay cụm từ
    is_single_word = len(text.split()) == 1
    target_type = 'vocab' if is_single_word else 'phrase'
    target_dict = vocab_data if is_single_word else phrase_data

    # Check chính tả nếu là từ đơn
    if is_single_word and spell.unknown([text]):
        corr = spell.correction(text)
        if corr and corr != text:
            if messagebox.askyesno("Sai chữ?", f"Ý bạn là '{corr}'?"): 
                text = corr
                # Sau khi sửa chính tả, check lại xem có bị trùng không
                if text in vocab_data:
                    entry_add.delete(0, 'end')
                    tab_view.set("Từ Đơn")
                    select_item(text, 'vocab')
                    return
            else: return

    entry_add.delete(0, 'end')
    entry_add.configure(placeholder_text="⏳ Đang tải dữ liệu...", state="disabled")

    def fetch_api_background():
        if is_single_word: ex, pos, vn = get_word_info(text)
        else: ex, pos, vn = get_phrase_info(text)
            
        def update_ui_after_fetch():
            target_dict[text] = {"sentence": ex, "pos": pos, "vn_meaning": vn, "last_studied": "", "study_count": 0, "custom_sentence": ""}
            save_data(data_json)
            entry_add.configure(state="normal", placeholder_text="Nhập nhanh 1 từ/cụm từ...")
            tab_view.set("Từ Đơn" if is_single_word else "Cụm Từ")
            refresh_list()
            select_item(text, target_type)
            
        app.after(0, update_ui_after_fetch)
    threading.Thread(target=fetch_api_background, daemon=True).start()

def delete_item():
    global current_item, current_type
    if current_item and messagebox.askyesno("Xóa", f"Xóa '{current_item}'?"):
        if current_type == 'vocab': del vocab_data[current_item]
        else: del phrase_data[current_item]
        save_data(data_json)
        detail_container.pack_forget()
        frame_welcome.pack(expand=True)
        refresh_list()
        current_item, current_type = None, None

# ==========================================
# CHỨC NĂNG THÊM HÀNG LOẠT VÀ THỐNG KÊ
# ==========================================
class BatchAddDialog(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Thêm Hàng Loạt")
        self.geometry("500x450")
        self.transient(master)
        self.grab_set()

        ctk.CTkLabel(self, text="📝 THÊM TỪ VỰNG HÀNG LOẠT", font=("Segoe UI", 18, "bold"), text_color=COLOR_ACCENT).pack(pady=(20,5))
        guide_text = ("Hướng dẫn: Nhập các từ/cụm từ, ngăn cách nhau bằng dấu phẩy (,)\nPhần mềm sẽ tự động phân loại Từ đơn/Cụm từ.\nVí dụ: hello, how are you, make sense, apple")
        ctk.CTkLabel(self, text=guide_text, text_color=TEXT_SUB, font=("Segoe UI", 13), justify="center").pack(pady=(0,15))

        self.textbox = ctk.CTkTextbox(self, height=200, font=("Segoe UI", 15), corner_radius=10, border_width=1)
        self.textbox.pack(fill="x", padx=25, pady=10)

        self.lbl_status = ctk.CTkLabel(self, text="Sẵn sàng...", font=("Segoe UI", 14, "italic"), text_color=COLOR_SUCCESS[0])
        self.lbl_status.pack(pady=5)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=10)
        ctk.CTkButton(btn_frame, text="Hủy bỏ", width=100, fg_color="transparent", border_width=1, text_color="gray", command=self.destroy).pack(side="left", padx=10)
        self.btn_start = ctk.CTkButton(btn_frame, text="Bắt đầu", width=140, font=FONT_H2, command=self.start_batch_add)
        self.btn_start.pack(side="right", padx=10)

    def start_batch_add(self):
        content = self.textbox.get("1.0", "end").strip()
        if not content: return
        
        # In-place xử lý chữ thường và cắt khoảng trắng
        raw_words = [w.strip().lower() for w in content.split(",") if w.strip()]
        # Lọc bỏ từ bị trùng lặp ngay trong danh sách nhập vào
        words = list(dict.fromkeys(raw_words))
        
        if not words: return

        self.btn_start.configure(state="disabled")
        self.textbox.configure(state="disabled")
        threading.Thread(target=self.process_words, args=(words,), daemon=True).start()

    def process_words(self, words):
        added_count = 0
        for i, w in enumerate(words):
            app.after(0, lambda idx=i, total=len(words), curr=w: self.lbl_status.configure(text=f"⏳ Đang xử lý ({idx+1}/{total}): '{curr}' ...", text_color=COLOR_ACCENT))
            
            # Quét trùng lặp im lặng
            if w in vocab_data or w in phrase_data: 
                continue
            
            is_single = len(w.split()) == 1
            target_dict = vocab_data if is_single else phrase_data
            
            if is_single: ex, pos, vn = get_word_info(w)
            else: ex, pos, vn = get_phrase_info(w)
            
            target_dict[w] = {"sentence": ex, "pos": pos, "vn_meaning": vn, "last_studied": "", "study_count": 0, "custom_sentence": ""}
            added_count += 1

        save_data(data_json)
        app.after(0, refresh_list)
        app.after(0, lambda: self.finish_processing(added_count, len(words)))

    def finish_processing(self, added, total):
        if added == 0:
            self.lbl_status.configure(text=f"Tất cả từ bạn nhập đều đã có sẵn trong danh sách!", text_color="gray")
        else:
            self.lbl_status.configure(text=f"✅ Hoàn tất! Đã thêm {added} mục mới.", text_color=COLOR_SUCCESS[0])
        self.btn_start.configure(text="Đóng cửa sổ", state="normal", command=self.destroy)

def open_batch_add():
    BatchAddDialog(app)

class StatisticsWindow(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("📊 Thống Kê Học Tập")
        self.geometry("650x550")
        self.transient(master)
        self.grab_set()

        t_vocab = len(vocab_data)
        t_phrase = len(phrase_data)
        today = datetime.now().strftime("%Y-%m-%d")
        studied_today = len(daily_tracker.get(today, []))

        mastered, warned, unlearned = 0, 0, 0

        for d in [vocab_data, phrase_data]:
            for k, v in d.items():
                c = v.get("study_count", 0)
                if c == 0: unlearned += 1
                elif c >= 15: mastered += 1

                if c >= 10:
                    try:
                        diff = (datetime.now() - datetime.strptime(v.get('last_studied', "2000-01-01 00:00"), "%Y-%m-%d %H:%M")).days
                        if diff >= 3: warned += 1
                    except: pass

        ctk.CTkLabel(self, text="📊 TỔNG QUAN HỌC TẬP", font=("Segoe UI", 24, "bold"), text_color=COLOR_ACCENT).pack(pady=(20, 10))

        grid = ctk.CTkFrame(self, fg_color="transparent")
        grid.pack(fill="both", expand=True, padx=20, pady=10)
        grid.grid_columnconfigure(0, weight=1)
        grid.grid_columnconfigure(1, weight=1)

        def make_card(parent, row, col, title, value, color):
            card = ctk.CTkFrame(parent, corner_radius=15, fg_color=BG_CARD)
            card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
            ctk.CTkLabel(card, text=title, font=FONT_BODY, text_color=TEXT_SUB).pack(pady=(20, 5))
            ctk.CTkLabel(card, text=str(value), font=("Segoe UI", 42, "bold"), text_color=color).pack(pady=(0, 20))

        make_card(grid, 0, 0, "📚 Tổng Từ Đơn", t_vocab, COLOR_ACCENT)
        make_card(grid, 0, 1, "💬 Tổng Cụm Từ", t_phrase, COLOR_ACCENT)
        make_card(grid, 1, 0, "🔥 Đã học hôm nay", studied_today, COLOR_SUCCESS[0])
        make_card(grid, 1, 1, "✅ Đã thuộc (>15 lần)", mastered, COLOR_SUCCESS[0])
        make_card(grid, 2, 0, "🚨 Cảnh báo (Lâu chưa ôn)", warned, COLOR_DANGER[0])
        make_card(grid, 2, 1, "🆕 Chưa học (0 lần)", unlearned, "gray")

def show_statistics():
    StatisticsWindow(app)

def backup_data():
    backup_file = os.path.join(BASE_DIR, f"backup_vocab_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    try:
        with open(backup_file, "w", encoding="utf-8") as f:
            json.dump(data_json, f, ensure_ascii=False, indent=4)
        messagebox.showinfo("Sao lưu", f"Đã lưu bản sao dữ liệu tại:\n{backup_file}")
    except Exception as e:
        messagebox.showerror("Lỗi", f"Không thể sao lưu: {e}")

def change_theme(new_mode: str):
    ctk.set_appearance_mode(new_mode)

def show_source_code():
    src_win = ctk.CTkToplevel(app)
    src_win.title("📄 Mã nguồn")
    src_win.geometry("900x700")
    src_win.transient(app)
    txt = ctk.CTkTextbox(src_win, font=("Consolas", 14), wrap="none", fg_color=BG_MAIN)
    txt.pack(fill="both", expand=True, padx=20, pady=20)
    try:
        with open(__file__, "r", encoding="utf-8") as f: txt.insert("1.0", f.read())
    except Exception as e: txt.insert("1.0", f"Lỗi: {e}")
    txt.configure(state="disabled")

# ==========================================
# 4. GAME ÔN TẬP
# ==========================================
def get_game_data(source_type):
    today_str = datetime.now().strftime("%Y-%m-%d")
    combined = {}
    for k, v in vocab_data.items():
        if source_type == "Chưa ôn hôm nay":
            last_date = v.get("last_studied", "").split(" ")[0]
            count = v.get("study_count", 0)
            if last_date != today_str and count < 15: combined[k] = {**v, "type": "vocab"}
        else: combined[k] = {**v, "type": "vocab"}
    for k, v in phrase_data.items():
        if source_type == "Chưa ôn hôm nay":
            last_date = v.get("last_studied", "").split(" ")[0]
            count = v.get("study_count", 0)
            if last_date != today_str and count < 15: combined[k] = {**v, "type": "phrase"}
        else: combined[k] = {**v, "type": "phrase"}
    return combined

class GameSetupDialog(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Cài đặt Game")
        self.geometry("500x500")
        self.transient(master)
        self.grab_set()
        
        self.result_num, self.result_mode, self.result_data = None, None, None
        
        ctk.CTkLabel(self, text="CÀI ĐẶT TRÒ CHƠI", font=("Segoe UI", 20, "bold"), text_color=COLOR_ACCENT).pack(pady=(20, 10))
        ctk.CTkLabel(self, text="Nguồn từ vựng:", font=FONT_BODY).pack(pady=(10, 0))
        self.source_mode = ctk.CTkSegmentedButton(self, values=["Ngẫu nhiên", "Chưa ôn hôm nay"], font=FONT_BODY, command=self.update_slider_max)
        self.source_mode.set("Chưa ôn hôm nay")
        self.source_mode.pack(pady=10, fill="x", padx=30)
        
        self.lbl_empty_alert = ctk.CTkLabel(self, text="", text_color=COLOR_SUCCESS[0], font=FONT_BODY)
        self.lbl_empty_alert.pack()

        ctk.CTkLabel(self, text="Thể loại Game:", font=FONT_BODY).pack(pady=(10, 0))
        self.game_mode = ctk.CTkSegmentedButton(self, values=["Trắc nghiệm", "Đảo chữ", "Nối từ", "Nghe & Gõ"], font=FONT_BODY)
        self.game_mode.set("Trắc nghiệm")
        self.game_mode.pack(pady=10, fill="x", padx=30)

        self.lbl_slider_title = ctk.CTkLabel(self, text="Số lượng từ:", font=FONT_BODY)
        self.lbl_slider_title.pack(pady=(15, 0))
        self.lbl_val = ctk.CTkLabel(self, text="5", font=("Segoe UI", 36, "bold"), text_color=COLOR_SUCCESS[0])
        self.lbl_val.pack(pady=5)
        self.slider = ctk.CTkSlider(self, from_=1, to=10, number_of_steps=9, button_color=COLOR_SUCCESS[0], progress_color=COLOR_SUCCESS[0], command=self.update_val)
        self.slider.pack(fill="x", padx=40, pady=10)
        
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=(15, 20))
        ctk.CTkButton(btn_frame, text="Hủy", width=100, fg_color="transparent", border_width=1, text_color="gray", command=self.destroy).pack(side="left", padx=10)
        self.btn_start = ctk.CTkButton(btn_frame, text="Bắt đầu", width=100, fg_color=COLOR_SUCCESS, hover_color="#28a745", command=self.on_ok)
        self.btn_start.pack(side="right", padx=10)
        
        self.update_slider_max(self.source_mode.get())
        self.wait_window()

    def update_slider_max(self, mode):
        data = get_game_data(mode)
        max_words = min(len(data), 50)
        if max_words == 0:
            self.lbl_empty_alert.configure(text="🎉 Bạn đã ôn hết từ vựng hôm nay.")
            self.slider.configure(state="disabled")
            self.btn_start.configure(state="disabled")
            self.lbl_val.configure(text="0")
        else:
            self.lbl_empty_alert.configure(text="")
            self.slider.configure(state="normal", from_=1, to=max_words, number_of_steps=max_words-1 if max_words>1 else 1)
            self.btn_start.configure(state="normal")
            default_val = min(5, max_words)
            self.slider.set(default_val)
            self.update_val(default_val)

    def update_val(self, val): self.lbl_val.configure(text=str(int(val)))

    def on_ok(self):
        self.result_num = int(self.slider.get())
        self.result_mode = self.game_mode.get()
        self.result_data = get_game_data(self.source_mode.get())
        self.destroy()

class QuizGameWindow(ctk.CTkToplevel):
    def __init__(self, master, num_words, game_data):
        super().__init__(master)
        self.title("🎮 Game Trắc Nghiệm")
        self.geometry("600x500")
        self.transient(master)
        self.grab_set()
        self.questions, self.current_idx, self.score = [], 0, 0
        self.all_data = game_data
        self.prepare_game(num_words)
        self.build_ui()
        self.load_question()

    def prepare_game(self, num_words):
        all_words = list(self.all_data.keys())
        def priority(w):
            c = self.all_data[w].get('study_count', 0)
            try: d = (datetime.now() - datetime.strptime(self.all_data[w].get('last_studied', ''), "%Y-%m-%d %H:%M")).days
            except: d = 9999
            return (c, -d)
        sorted_w = sorted(all_words, key=priority)[:min(num_words, len(all_words))]
        for w in sorted_w:
            options = [w]
            cands = [x for x in all_words if x != w]
            random.shuffle(cands)
            while len(options) < 4 and cands:
                o = cands.pop()
                if o not in options: options.append(o)
            random.shuffle(options)
            self.questions.append((w, self.all_data[w].get('vn_meaning', ''), options, self.all_data[w]['type']))

    def build_ui(self):
        self.lbl_progress = ctk.CTkLabel(self, text="Câu 0", font=FONT_BODY, text_color=TEXT_SUB)
        self.lbl_progress.pack(pady=(20, 5))
        self.lbl_question = ctk.CTkLabel(self, text="Nghĩa là:", font=("Segoe UI", 28, "bold"), text_color=COLOR_ACCENT, wraplength=500)
        self.lbl_question.pack(pady=(10, 30))
        self.btn_opts = []
        for i in range(4):
            btn = ctk.CTkButton(self, text="", height=50, corner_radius=10, font=("Segoe UI", 16, "bold"), 
                                fg_color=BG_CARD, text_color=("black", "white"), hover_color=COLOR_ACCENT,
                                command=lambda idx=i: self.check_answer(idx))
            btn.pack(fill="x", padx=40, pady=8)
            self.btn_opts.append(btn)

    def load_question(self):
        if self.current_idx >= len(self.questions):
            messagebox.showinfo("Xong", f"Đúng {self.score}/{len(self.questions)} câu.")
            self.destroy(); refresh_list(); return
        q_word, q_vn, q_opts, _ = self.questions[self.current_idx]
        self.lbl_progress.configure(text=f"Câu {self.current_idx + 1} / {len(self.questions)}")
        self.lbl_question.configure(text=f"{q_vn.capitalize()}")
        for i in range(4): self.btn_opts[i].configure(text=q_opts[i].capitalize())

    def check_answer(self, btn_idx):
        correct_word, _, options, i_type = self.questions[self.current_idx]
        selected_word = options[btn_idx]
        if selected_word == correct_word:
            update_study_progress(correct_word, i_type)
            self.score += 1
            play_sound_system(correct_word)
        else: messagebox.showerror("Sai", f"Đáp án đúng:\n{correct_word.capitalize()}")
        self.current_idx += 1
        self.load_question()

class ScrambleGameWindow(ctk.CTkToplevel):
    def __init__(self, master, num_words, game_data):
        super().__init__(master)
        self.title("🎮 Game Đảo Chữ")
        self.geometry("600x500")
        self.transient(master)
        self.grab_set()
        self.questions, self.current_idx, self.score = [], 0, 0
        self.all_data = game_data
        self.prepare_game(num_words)
        self.build_ui()
        self.load_question()

    def prepare_game(self, num_words):
        all_words = list(self.all_data.keys())
        def priority(w):
            c = self.all_data[w].get('study_count', 0)
            try: d = (datetime.now() - datetime.strptime(self.all_data[w].get('last_studied', ''), "%Y-%m-%d %H:%M")).days
            except: d = 9999
            return (c, -d)
        sorted_w = sorted(all_words, key=priority)[:min(num_words, len(all_words))]
        for w in sorted_w:
            vn = self.all_data[w].get('vn_meaning', 'Chưa có nghĩa')
            self.questions.append((w, vn, self.all_data[w]['type']))

    def build_ui(self):
        self.lbl_progress = ctk.CTkLabel(self, text="Câu 0", font=FONT_BODY, text_color=TEXT_SUB)
        self.lbl_progress.pack(pady=(20, 5))
        self.lbl_vn = ctk.CTkLabel(self, text="Nghĩa TV", font=("Segoe UI", 24, "bold"), text_color=COLOR_SUCCESS[0], wraplength=500)
        self.lbl_vn.pack(pady=10)
        self.lbl_scrambled = ctk.CTkLabel(self, text="W O R D", font=("Segoe UI", 36, "bold"), text_color=COLOR_ACCENT, wraplength=500)
        self.lbl_scrambled.pack(pady=(10, 30))
        self.entry_ans = ctk.CTkEntry(self, font=("Segoe UI", 24, "bold"), justify="center", height=60, corner_radius=15)
        self.entry_ans.pack(fill="x", padx=60, pady=10)
        self.entry_ans.bind('<Return>', lambda e: self.check_answer())

        btn_f = ctk.CTkFrame(self, fg_color="transparent")
        btn_f.pack(pady=20)
        ctk.CTkButton(btn_f, text="🔊 Nghe gợi ý", width=120, height=45, fg_color=BG_CARD, text_color=("black", "white"), hover_color="gray80", command=self.play_hint).pack(side="left", padx=10)
        ctk.CTkButton(btn_f, text="Kiểm tra", width=120, height=45, fg_color=COLOR_ACCENT, font=FONT_H2, command=self.check_answer).pack(side="right", padx=10)

    def play_hint(self):
        correct_word, _, _ = self.questions[self.current_idx]
        play_sound_system(correct_word)

    def load_question(self):
        if self.current_idx >= len(self.questions):
            messagebox.showinfo("Xong", f"Bạn gõ đúng {self.score}/{len(self.questions)} từ.")
            self.destroy(); refresh_list(); return
            
        q_word, q_vn, _ = self.questions[self.current_idx]
        self.lbl_progress.configure(text=f"Câu {self.current_idx + 1} / {len(self.questions)}")
        self.lbl_vn.configure(text=f"{q_vn.capitalize()}")
        
        words_in_phrase = q_word.split()
        scrambled_words = []
        for w in words_in_phrase:
            chars = list(w)
            random.shuffle(chars)
            while "".join(chars) == w and len(w) > 2: random.shuffle(chars)
            scrambled_words.append("".join(chars).upper())
            
        self.lbl_scrambled.configure(text="   ".join(scrambled_words))
        self.entry_ans.delete(0, "end")
        self.entry_ans.focus()

    def check_answer(self):
        correct_word, _, i_type = self.questions[self.current_idx]
        ans = self.entry_ans.get().strip().lower()
        if ans == correct_word:
            update_study_progress(correct_word, i_type)
            self.score += 1
            play_sound_system(correct_word)
        else: messagebox.showerror("Sai", f"Chính tả đúng phải là:\n{correct_word.upper()}")
        self.current_idx += 1
        self.load_question()

class MatchGameWindow(ctk.CTkToplevel):
    def __init__(self, master, num_words, game_data):
        super().__init__(master)
        self.title("🎮 Game Nối Từ")
        self.geometry("800x600")
        self.transient(master)
        self.grab_set()
        self.pairs, self.score, self.total_pairs = [], 0, num_words
        self.selected_en, self.selected_vi = None, None
        self.all_data = game_data
        self.prepare_game(num_words)
        self.build_ui()

    def prepare_game(self, num_words):
        all_words = list(self.all_data.keys())
        def priority(w):
            c = self.all_data[w].get('study_count', 0)
            try: d = (datetime.now() - datetime.strptime(self.all_data[w].get('last_studied', ''), "%Y-%m-%d %H:%M")).days
            except: d = 9999
            return (c, -d)
        sorted_w = sorted(all_words, key=priority)[:min(num_words, len(all_words))]
        for w in sorted_w:
            vn = self.all_data[w].get('vn_meaning', 'Chưa có nghĩa')
            self.pairs.append({"en": w, "vi": vn, "type": self.all_data[w]['type']})

    def build_ui(self):
        ctk.CTkLabel(self, text="Ghép từ tiếng Anh với nghĩa tiếng Việt", font=FONT_H2).pack(pady=20)
        self.game_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.game_frame.pack(fill="both", expand=True, padx=20, pady=10)
        self.game_frame.grid_columnconfigure(0, weight=1)
        self.game_frame.grid_columnconfigure(1, weight=1)
        
        en_list = [p for p in self.pairs]
        vi_list = [p for p in self.pairs]
        random.shuffle(en_list)
        random.shuffle(vi_list)
        
        self.btn_en_dict, self.btn_vi_dict = {}, {}
        
        frame_en = ctk.CTkFrame(self.game_frame, fg_color="transparent")
        frame_en.grid(row=0, column=0, sticky="nsew", padx=10)
        for item in en_list:
            w = item["en"]
            btn = ctk.CTkButton(frame_en, text=w.capitalize(), height=50, corner_radius=10, 
                                font=("Segoe UI", 14, "bold"), fg_color=BG_CARD, text_color=("black", "white"),
                                command=lambda x=w: self.on_select_en(x))
            btn.pack(fill="x", pady=8)
            self.btn_en_dict[w] = btn
            
        frame_vi = ctk.CTkFrame(self.game_frame, fg_color="transparent")
        frame_vi.grid(row=0, column=1, sticky="nsew", padx=10)
        for item in vi_list:
            v = item["vi"]
            btn = ctk.CTkButton(frame_vi, text=v.capitalize(), height=50, corner_radius=10, 
                                font=("Segoe UI", 14), fg_color=BG_CARD, text_color=("black", "white"),
                                command=lambda x=v: self.on_select_vi(x))
            btn.pack(fill="x", pady=8)
            self.btn_vi_dict[v] = btn

    def on_select_en(self, word):
        for w, btn in self.btn_en_dict.items():
            if btn.winfo_exists(): btn.configure(border_width=0)
        self.selected_en = word
        if self.btn_en_dict[word].winfo_exists(): self.btn_en_dict[word].configure(border_width=2, border_color=COLOR_ACCENT)
        self.check_match()

    def on_select_vi(self, word):
        for w, btn in self.btn_vi_dict.items():
            if btn.winfo_exists(): btn.configure(border_width=0)
        self.selected_vi = word
        if self.btn_vi_dict[word].winfo_exists(): self.btn_vi_dict[word].configure(border_width=2, border_color=COLOR_SUCCESS[0])
        self.check_match()

    def check_match(self):
        if self.selected_en and self.selected_vi:
            match_item = next((p for p in self.pairs if p["en"] == self.selected_en and p["vi"] == self.selected_vi), None)
            if match_item:
                play_sound_system(self.selected_en)
                update_study_progress(self.selected_en, match_item["type"])
                if self.btn_en_dict[self.selected_en].winfo_exists(): self.btn_en_dict[self.selected_en].destroy()
                if self.btn_vi_dict[self.selected_vi].winfo_exists(): self.btn_vi_dict[self.selected_vi].destroy()
                self.score += 1
                self.selected_en, self.selected_vi = None, None
                if self.score == self.total_pairs:
                    messagebox.showinfo("Tuyệt vời", "Bạn đã nối đúng tất cả các từ!")
                    self.destroy(); refresh_list()
            else:
                messagebox.showerror("Sai rồi", "Hai mục này không khớp nhau!")
                for w, btn in self.btn_en_dict.items():
                    if btn.winfo_exists(): btn.configure(border_width=0)
                for w, btn in self.btn_vi_dict.items():
                    if btn.winfo_exists(): btn.configure(border_width=0)
                self.selected_en, self.selected_vi = None, None

class DictationGameWindow(ctk.CTkToplevel):
    def __init__(self, master, num_words, game_data):
        super().__init__(master)
        self.title("🎮 Game Nghe & Gõ")
        self.geometry("600x500")
        self.transient(master)
        self.grab_set()
        self.questions, self.current_idx, self.score = [], 0, 0
        self.all_data = game_data
        self.prepare_game(num_words)
        self.build_ui()
        self.load_question()

    def prepare_game(self, num_words):
        all_words = list(self.all_data.keys())
        def priority(w):
            c = self.all_data[w].get('study_count', 0)
            try: d = (datetime.now() - datetime.strptime(self.all_data[w].get('last_studied', ''), "%Y-%m-%d %H:%M")).days
            except: d = 9999
            return (c, -d)
        sorted_w = sorted(all_words, key=priority)[:min(num_words, len(all_words))]
        for w in sorted_w:
            vn = self.all_data[w].get('vn_meaning', 'Chưa có nghĩa')
            self.questions.append((w, vn, self.all_data[w]['type']))

    def build_ui(self):
        self.lbl_progress = ctk.CTkLabel(self, text="Câu 0", font=FONT_BODY, text_color=TEXT_SUB)
        self.lbl_progress.pack(pady=(20, 5))
        self.btn_audio = ctk.CTkButton(self, text="🔊 NGHE TỪ VỰNG", font=("Segoe UI", 24, "bold"), height=80, corner_radius=15, command=self.play_audio)
        self.btn_audio.pack(pady=20)
        self.lbl_hint = ctk.CTkLabel(self, text="---", font=("Segoe UI", 18, "italic"), text_color=COLOR_SUCCESS[0], wraplength=500)
        self.lbl_hint.pack(pady=10)
        self.entry_ans = ctk.CTkEntry(self, font=("Segoe UI", 24, "bold"), justify="center", height=60, corner_radius=15)
        self.entry_ans.pack(fill="x", padx=60, pady=10)
        self.entry_ans.bind('<Return>', lambda e: self.check_answer())

        btn_f = ctk.CTkFrame(self, fg_color="transparent")
        btn_f.pack(pady=20)
        ctk.CTkButton(btn_f, text="💡 Gợi ý nghĩa", width=120, height=45, fg_color=BG_CARD, text_color=("black", "white"), hover_color="gray80", command=self.show_hint).pack(side="left", padx=10)
        ctk.CTkButton(btn_f, text="Kiểm tra", width=120, height=45, fg_color=COLOR_ACCENT, font=FONT_H2, command=self.check_answer).pack(side="right", padx=10)

    def play_audio(self):
        q_word, _, _ = self.questions[self.current_idx]
        play_sound_system(q_word)

    def show_hint(self):
        _, q_vn, _ = self.questions[self.current_idx]
        self.lbl_hint.configure(text=f"Nghĩa: {q_vn.capitalize()}")

    def load_question(self):
        if self.current_idx >= len(self.questions):
            messagebox.showinfo("Xong", f"Bạn nghe gõ đúng {self.score}/{len(self.questions)} mục.")
            self.destroy(); refresh_list(); return
            
        self.lbl_progress.configure(text=f"Câu {self.current_idx + 1} / {len(self.questions)}")
        self.lbl_hint.configure(text="---")
        self.entry_ans.delete(0, "end")
        self.entry_ans.focus()
        self.play_audio()

    def check_answer(self):
        correct_word, _, i_type = self.questions[self.current_idx]
        ans = self.entry_ans.get().strip().lower()
        if ans == correct_word:
            update_study_progress(correct_word, i_type)
            self.score += 1
            play_sound_system(correct_word) 
        else: messagebox.showerror("Sai", f"Từ đúng phải là:\n{correct_word.upper()}")
        self.current_idx += 1
        self.load_question()

def open_game_setup():
    dialog = GameSetupDialog(app)
    if dialog.result_num and dialog.result_data:
        num = dialog.result_num
        data = dialog.result_data
        mode = dialog.result_mode
        
        if "Trắc nghiệm" in mode: QuizGameWindow(app, num, data)
        elif "Đảo chữ" in mode: ScrambleGameWindow(app, num, data)
        elif "Nối từ" in mode: MatchGameWindow(app, min(num, 10), data) 
        elif "Nghe & Gõ" in mode: DictationGameWindow(app, num, data)

# ==========================================
# 5. GIAO DIỆN CHÍNH (CÓ THANH TASKBAR MỚI)
# ==========================================
app = ctk.CTk()
app.title("Vocab Master Premium")
app.geometry("1350x800")
app.grid_columnconfigure(1, weight=1)
app.grid_rowconfigure(1, weight=1) 

# ----- THANH TASKBAR Ở TRÊN CÙNG -----
top_bar = ctk.CTkFrame(app, height=45, corner_radius=0, fg_color=BG_CARD)
top_bar.grid(row=0, column=0, columnspan=2, sticky="ew")

ctk.CTkButton(top_bar, text="➕ Thêm hàng loạt", font=FONT_BODY, fg_color="transparent", text_color=("black", "white"), hover_color="gray80", command=open_batch_add).pack(side="left", padx=10, pady=5)
ctk.CTkButton(top_bar, text="🎮 Game Ôn Tập", font=FONT_BODY, fg_color="transparent", text_color=("black", "white"), hover_color="gray80", command=open_game_setup).pack(side="left", padx=10, pady=5)
ctk.CTkButton(top_bar, text="📊 Thống kê", font=FONT_BODY, fg_color="transparent", text_color=("black", "white"), hover_color="gray80", command=show_statistics).pack(side="left", padx=10, pady=5)
ctk.CTkButton(top_bar, text="💾 Sao lưu", font=FONT_BODY, fg_color="transparent", text_color=("black", "white"), hover_color="gray80", command=backup_data).pack(side="left", padx=10, pady=5)

theme_menu = ctk.CTkOptionMenu(top_bar, values=["System", "Dark", "Light"], command=change_theme, width=110, font=FONT_BODY, fg_color=BG_CARD, button_color=BG_CARD, button_hover_color="gray80", text_color=("black", "white"))
theme_menu.pack(side="right", padx=10, pady=5)
theme_menu.set("Giao diện")
ctk.CTkButton(top_bar, text="📄 Mã nguồn", font=FONT_BODY, fg_color="transparent", text_color=("black", "white"), hover_color="gray80", command=show_source_code).pack(side="right", padx=10, pady=5)

# ----- CỘT TRÁI (SIDEBAR) -----
sidebar = ctk.CTkFrame(app, width=550, corner_radius=0, fg_color=BG_SIDEBAR)
sidebar.grid(row=1, column=0, sticky="nsew")
sidebar.grid_propagate(False)

ctk.CTkLabel(sidebar, text="V O C A B", font=FONT_LOGO, text_color=COLOR_ACCENT).pack(pady=(30, 5))
ctk.CTkLabel(sidebar, text="Master Your English", font=FONT_BODY, text_color=TEXT_SUB).pack(pady=(0, 15))

# Khu vực tìm / thêm nhanh
add_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
add_frame.pack(fill="x", padx=20, pady=10)
entry_add = ctk.CTkEntry(add_frame, placeholder_text="Nhập nhanh 1 từ/cụm từ...", height=45, font=FONT_BODY)
entry_add.pack(side="left", fill="x", expand=True)
btn_add = ctk.CTkButton(add_frame, text="+", width=45, height=45, font=FONT_LOGO, fg_color=COLOR_ACCENT, command=add_item)
btn_add.pack(side="right", padx=(10, 0))
app.bind('<Return>', lambda e: add_item())

# Sắp xếp
sort_var = ctk.StringVar(value="Sắp xếp: Ngày học (Gần nhất)")
sort_opts = ["Sắp xếp: Tên (A-Z)", "Sắp xếp: Ngày học (Gần nhất)", "Sắp xếp: Ngày học (Xa nhất)", "Sắp xếp: Số lần học (Nhiều nhất)", "Sắp xếp: Số lần học (Ít nhất)"]
ctk.CTkOptionMenu(sidebar, variable=sort_var, values=sort_opts, command=refresh_list, font=FONT_BODY).pack(fill="x", padx=20, pady=(5,10))

# Tabs
tab_view = ctk.CTkTabview(sidebar, width=500)
tab_view.pack(fill="both", expand=True, padx=20, pady=5)
tab_view.add("Từ Đơn")
tab_view.add("Cụm Từ")

scroll_vocab = ctk.CTkScrollableFrame(tab_view.tab("Từ Đơn"), fg_color="transparent")
scroll_vocab.pack(fill="both", expand=True)
scroll_phrase = ctk.CTkScrollableFrame(tab_view.tab("Cụm Từ"), fg_color="transparent")
scroll_phrase.pack(fill="both", expand=True)

# ----- CỘT PHẢI (MAIN VIEW) -----
main_view = ctk.CTkFrame(app, corner_radius=0, fg_color=BG_MAIN)
main_view.grid(row=1, column=1, sticky="nsew")

frame_welcome = ctk.CTkFrame(main_view, fg_color="transparent")
frame_welcome.pack(expand=True)
ctk.CTkLabel(frame_welcome, text="📚", font=("Segoe UI", 70)).pack(pady=10)
ctk.CTkLabel(frame_welcome, text="Học thôi nào!", font=("Segoe UI", 24, "bold")).pack()

detail_container = ctk.CTkScrollableFrame(main_view, fg_color="transparent")

c1 = ctk.CTkFrame(detail_container, corner_radius=15, fg_color="transparent")
c1.pack(fill="x", pady=(10, 20))
hl = ctk.CTkFrame(c1, fg_color="transparent")
hl.pack(side="left")
lbl_title = ctk.CTkLabel(hl, text="word", font=FONT_TITLE, wraplength=400, justify="left")
lbl_title.pack(anchor="w")
vf = ctk.CTkFrame(hl, fg_color="transparent")
vf.pack(anchor="w")
lbl_vn = ctk.CTkLabel(vf, text="nghĩa", font=FONT_VN, text_color=COLOR_SUCCESS[0], wraplength=350, justify="left")
lbl_vn.pack(side="left")
ctk.CTkButton(vf, text="✏️", width=30, height=30, fg_color="transparent", text_color=COLOR_ACCENT, command=edit_vn_meaning).pack(side="left", padx=(10, 0))

pf = ctk.CTkFrame(c1, corner_radius=20, fg_color=COLOR_ACCENT)
pf.pack(side="left", pady=(10,0), padx=20)
lbl_pos_text = ctk.CTkLabel(pf, text="pos", font=("Segoe UI", 14), text_color="white")
lbl_pos_text.pack(padx=15, pady=2)
ctk.CTkButton(c1, text="🔊 Nghe", width=100, height=40, corner_radius=20, fg_color=BG_CARD, text_color=("black", "white"), command=lambda: play_sound_system(current_item)).pack(side="right", pady=20)

c2 = ctk.CTkFrame(detail_container, fg_color="transparent")
c2.pack(fill="x", pady=10)
img_f = ctk.CTkFrame(c2, corner_radius=15, fg_color=BG_CARD, width=180, height=180)
img_f.pack(side="left")
img_f.pack_propagate(False)
lbl_img = ctk.CTkLabel(img_f, text="⌛", font=FONT_BODY, text_color=TEXT_SUB)
lbl_img.pack(expand=True)

c2_info = ctk.CTkFrame(c2, corner_radius=15, fg_color=BG_CARD)
c2_info.pack(side="left", fill="both", expand=True, padx=(20, 0))
lbl_alert = ctk.CTkLabel(c2_info, text="", font=("Segoe UI", 13, "bold"), text_color=COLOR_DANGER[0])
lbl_stats = ctk.CTkLabel(c2_info, text="Stats", font=("Segoe UI", 13), text_color=TEXT_SUB)
lbl_stats.pack(anchor="w", padx=25, pady=(20, 5))
lbl_ex = ctk.CTkLabel(c2_info, text="Example", font=FONT_ITALIC, wraplength=450, justify="left")
lbl_ex.pack(anchor="w", padx=25, pady=(5, 15))
ctk.CTkButton(c2_info, text="▶ Nghe câu ví dụ", border_width=1, fg_color="transparent", text_color=COLOR_ACCENT, command=lambda: play_sound_system((vocab_data if current_type == 'vocab' else phrase_data)[current_item]['sentence'])).pack(anchor="w", padx=25)

c3 = ctk.CTkFrame(detail_container, corner_radius=15, fg_color=BG_CARD)
c3.pack(fill="x", pady=20)
ctk.CTkLabel(c3, text="📝 Ghi chú của bạn / Đặt câu tự do", font=FONT_H2).pack(anchor="w", padx=25, pady=(20, 10))
txt_note = ctk.CTkTextbox(c3, height=100, corner_radius=8, fg_color=BG_MAIN, font=FONT_BODY)
txt_note.pack(fill="x", padx=25, pady=(0, 20))

bf = ctk.CTkFrame(c3, fg_color="transparent")
bf.pack(fill="x", padx=25, pady=(0, 25))
ctk.CTkButton(bf, text="💾 Lưu", fg_color=COLOR_SUCCESS, width=100, command=lambda: [(vocab_data if current_type == 'vocab' else phrase_data)[current_item].update({"custom_sentence": txt_note.get("1.0", "end-1c")}), save_data(data_json), messagebox.showinfo("OK", "Đã lưu")]).pack(side="left")
ctk.CTkButton(bf, text="🗑 Xóa Mục", fg_color="transparent", text_color=COLOR_DANGER[0], border_width=1, border_color=COLOR_DANGER[0], width=80, command=delete_item).pack(side="right")

refresh_list()
app.mainloop()