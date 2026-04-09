import customtkinter as ctk
from tkinter import messagebox
import sqlite3
import os
from datetime import datetime
import requests
from io import BytesIO
from PIL import Image
import threading
import pygame
from gtts import gTTS
from deep_translator import GoogleTranslator
import random
import hashlib
from concurrent.futures import ThreadPoolExecutor
from collections import OrderedDict
import time

# ================== CẤU HÌNH & KHỞI TẠO ==================
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "vocab.db")
CACHE_DIR = os.path.join(BASE_DIR, "image_cache")
AUDIO_CACHE_DIR = os.path.join(BASE_DIR, "audio_cache")
os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(AUDIO_CACHE_DIR, exist_ok=True)

pygame.mixer.init()
translator = GoogleTranslator(source='en', target='vi')

executor = ThreadPoolExecutor(max_workers=15)
DB_LOCK = threading.Lock()

BG_SIDEBAR = ("#F7F9FC", "#1E1E24")
BG_MAIN = ("#FFFFFF", "#141419")
BG_CARD = ("#E6EBF5", "#272730")
COLOR_ACCENT = "#5E5CE6"
COLOR_SUCCESS = ("#34C759", "#30D158")
COLOR_DANGER = ("#FF3B30", "#FF453A")
TEXT_SUB = ("#6E6E73", "#98989F")
FONT_TITLE = ("Segoe UI", 42, "bold")
FONT_VN = ("Segoe UI", 22, "bold")
FONT_BODY = ("Segoe UI", 14)
FONT_ITALIC = ("Segoe UI", 15, "italic")

POS_MAP = {
    "noun": "Danh từ", "verb": "Động từ", "adjective": "Tính từ",
    "adverb": "Trạng từ", "pronoun": "Đại từ", "preposition": "Giới từ",
    "conjunction": "Liên từ", "interjection": "Thán từ"
}

# ================== RAM-FIRST DATA MANAGER (SIÊU TỐC) ==================
class DataManager:
    def __init__(self):
        self.vocab = {}
        self.phrase = {}
        self.tracker = {} # {date: set(words)}
        self._init_db()
        self._load_to_ram()

    def _init_db(self):
        with DB_LOCK:
            conn = sqlite3.connect(DB_PATH)
            conn.execute("PRAGMA journal_mode=WAL;")
            c = conn.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS vocab
                         (word TEXT PRIMARY KEY, sentence TEXT, pos TEXT, vn_meaning TEXT,
                          last_studied TEXT, study_count INTEGER DEFAULT 0, custom_sentence TEXT, item_type TEXT DEFAULT 'vocab')''')
            c.execute('''CREATE TABLE IF NOT EXISTS phrase
                         (word TEXT PRIMARY KEY, sentence TEXT, pos TEXT, vn_meaning TEXT,
                          last_studied TEXT, study_count INTEGER DEFAULT 0, custom_sentence TEXT, item_type TEXT DEFAULT 'phrase')''')
            c.execute('''CREATE TABLE IF NOT EXISTS daily_tracker
                         (date TEXT, word TEXT, PRIMARY KEY (date, word))''')
            conn.commit()
            conn.close()

    def _load_to_ram(self):
        with DB_LOCK:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            for row in c.execute("SELECT * FROM vocab"):
                self.vocab[row[0]] = {'sentence': row[1], 'pos': row[2], 'vn_meaning': row[3], 'last_studied': row[4], 'study_count': row[5], 'custom_sentence': row[6], 'item_type': row[7]}
            for row in c.execute("SELECT * FROM phrase"):
                self.phrase[row[0]] = {'sentence': row[1], 'pos': row[2], 'vn_meaning': row[3], 'last_studied': row[4], 'study_count': row[5], 'custom_sentence': row[6], 'item_type': row[7]}
            for row in c.execute("SELECT date, word FROM daily_tracker"):
                if row[0] not in self.tracker: self.tracker[row[0]] = set()
                self.tracker[row[0]].add(row[1])
            conn.close()

    def get_all(self, item_type):
        d = self.vocab if item_type == 'vocab' else self.phrase
        return [(w, v['vn_meaning'], v['study_count'], v['last_studied']) for w, v in d.items()]

    def get_detail(self, word, item_type):
        d = self.vocab if item_type == 'vocab' else self.phrase
        return d.get(word)

    def update_progress(self, word, item_type):
        """Xử lý RAM cực nhanh: Tăng số lần học 1 lần/ngày. Cập nhật thời gian thực"""
        d = self.vocab if item_type == 'vocab' else self.phrase
        if word not in d: return False
        
        today = datetime.now().strftime("%Y-%m-%d")
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        if today not in self.tracker: self.tracker[today] = set()

        increased = False
        if word not in self.tracker[today]:
            d[word]['study_count'] += 1
            self.tracker[today].add(word)
            increased = True
            
        d[word]['last_studied'] = now_str

        # Chạy đồng bộ Database ngầm (Không làm lag UI)
        def save_to_db():
            with DB_LOCK:
                conn = sqlite3.connect(DB_PATH)
                if increased:
                    conn.execute(f"UPDATE {item_type} SET study_count=?, last_studied=? WHERE word=?", (d[word]['study_count'], now_str, word))
                    conn.execute("INSERT OR IGNORE INTO daily_tracker (date, word) VALUES (?,?)", (today, word))
                else:
                    conn.execute(f"UPDATE {item_type} SET last_studied=? WHERE word=?", (now_str, word))
                conn.commit()
                conn.close()
        executor.submit(save_to_db)
        return increased

    def add_or_update(self, word, item_type, sentence, pos, vn_meaning, custom_sentence="", sync_db=True):
        d = self.vocab if item_type == 'vocab' else self.phrase
        if word in d:
            d[word].update({'sentence': sentence, 'pos': pos, 'vn_meaning': vn_meaning, 'custom_sentence': custom_sentence})
        else:
            d[word] = {'sentence': sentence, 'pos': pos, 'vn_meaning': vn_meaning, 'last_studied': "", 'study_count': 0, 'custom_sentence': custom_sentence, 'item_type': item_type}
        
        if sync_db:
            def save_to_db():
                with DB_LOCK:
                    conn = sqlite3.connect(DB_PATH)
                    c = conn.cursor()
                    if c.execute(f"SELECT 1 FROM {item_type} WHERE word=?", (word,)).fetchone():
                        conn.execute(f"UPDATE {item_type} SET sentence=?, pos=?, vn_meaning=?, custom_sentence=? WHERE word=?", (sentence, pos, vn_meaning, custom_sentence, word))
                    else:
                        conn.execute(f"INSERT INTO {item_type} (word, sentence, pos, vn_meaning, custom_sentence, last_studied, study_count) VALUES (?,?,?,?,?,?,?)", (word, sentence, pos, vn_meaning, custom_sentence, "", 0))
                    conn.commit()
                    conn.close()
            executor.submit(save_to_db)

    def update_field(self, word, item_type, field, value):
        d = self.vocab if item_type == 'vocab' else self.phrase
        if word in d:
            d[word][field] = value
            def save_to_db():
                with DB_LOCK:
                    conn = sqlite3.connect(DB_PATH)
                    conn.execute(f"UPDATE {item_type} SET {field}=? WHERE word=?", (value, word))
                    conn.commit(); conn.close()
            executor.submit(save_to_db)

    def delete(self, word, item_type):
        d = self.vocab if item_type == 'vocab' else self.phrase
        if word in d:
            del d[word]
            def save_to_db():
                with DB_LOCK:
                    conn = sqlite3.connect(DB_PATH)
                    conn.execute(f"DELETE FROM {item_type} WHERE word=?", (word,))
                    conn.commit(); conn.close()
            executor.submit(save_to_db)

data_manager = DataManager()

# ================== BỘ NHỚ ĐỆM (CACHE) ==================
class TimedLRUCache:
    def __init__(self, max_size=200, ttl=86400):
        self.cache = OrderedDict()
        self.max_size = max_size
        self.ttl = ttl
    
    def get(self, key):
        if key in self.cache:
            value, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                self.cache.move_to_end(key)
                return value
            else:
                del self.cache[key]
        return None
    
    def set(self, key, value):
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = (value, time.time())
        if len(self.cache) > self.max_size:
            self.cache.popitem(last=False)

image_cache = TimedLRUCache(max_size=150, ttl=3600)
meaning_cache = TimedLRUCache(max_size=500, ttl=86400)

# ================== API & XỬ LÝ ==================
def get_word_info(word):
    cached = meaning_cache.get(word)
    if cached: return cached
    example, pos_str = "Chưa có ví dụ tự động.", "Chưa phân loại"
    try:
        res = requests.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}", timeout=3)
        if res.status_code == 200:
            d = res.json()[0]
            pos_list = list(set([POS_MAP.get(m['partOfSpeech'], m['partOfSpeech']) for m in d['meanings']]))
            pos_str = " | ".join(pos_list)
            for m in d['meanings']:
                for df in m['definitions']:
                    if 'example' in df:
                        example = df['example']
                        break
                if example != "Chưa có ví dụ tự động.": break
    except: pass
    try: vn_meaning = translator.translate(word)
    except: vn_meaning = "Lỗi dịch"
    result = (example, pos_str, vn_meaning)
    meaning_cache.set(word, result)
    return result

def get_phrase_info(phrase):
    cached = meaning_cache.get(phrase)
    if cached: return cached
    try: vn_meaning = translator.translate(phrase)
    except: vn_meaning = "Lỗi dịch"
    result = ("Hãy tự đặt một câu ví dụ cho cụm từ này.", "Cụm từ / Câu", vn_meaning)
    meaning_cache.set(phrase, result)
    return result

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
    executor.submit(task)

def download_and_cache_image(word):
    cache_path = os.path.join(CACHE_DIR, f"{hashlib.md5(word.encode()).hexdigest()}.jpg")
    if os.path.exists(cache_path): return cache_path
    img_data = image_cache.get(word)
    if img_data:
        with open(cache_path, "wb") as f: f.write(img_data)
        return cache_path
    try:
        url = f"https://tse2.mm.bing.net/th?q={word.replace(' ', '+')}+png+isolated&w=400&h=400&c=7&rs=1"
        res = requests.get(url, timeout=4)
        if res.status_code == 200:
            with open(cache_path, "wb") as f: f.write(res.content)
            image_cache.set(word, res.content)
            return cache_path
    except: pass
    return None

def load_image_async(word, label_widget):
    def task():
        cache_path = download_and_cache_image(word)
        if cache_path and os.path.exists(cache_path):
            try:
                pil_img = Image.open(cache_path)
                pil_img.thumbnail((200, 200), Image.Resampling.BILINEAR)
                ctk_img = ctk.CTkImage(pil_img, size=(180, 180))
                app.after(0, lambda: label_widget.configure(image=ctk_img, text=""))
                return
            except: pass
        app.after(0, lambda: label_widget.configure(text="[ Không tải được ảnh ]", image=""))
    executor.submit(task)

# ================== TỐI ƯU VIRTUAL SCROLL LIST ==================
class VirtualScrollList(ctk.CTkFrame):
    def __init__(self, master, item_type, **kwargs):
        bg_color = kwargs.pop('bg', BG_SIDEBAR[1])
        super().__init__(master, fg_color="transparent", **kwargs)
        self.item_type = item_type
        self.items = []
        self.item_height = 56
        
        self.canvas = ctk.CTkCanvas(self, highlightthickness=0, bg=bg_color, borderwidth=0)
        self.scrollbar = ctk.CTkScrollbar(self, command=self.yview_with_redraw)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        
        self.canvas.bind('<Configure>', self.on_resize)
        self.bind_scroll(self.canvas)
        
        self.total_height = 0
        self.sort_criteria = "recent"
        
        self.pool_size = 35 
        self.row_pool = []
        self.init_pool()
        self.load_data()
        
    def yview_with_redraw(self, *args):
        self.canvas.yview(*args)
        self.redraw()

    def bind_scroll(self, widget):
        widget.bind('<MouseWheel>', self.on_mousewheel)
        widget.bind('<Button-4>', self.on_mousewheel)
        widget.bind('<Button-5>', self.on_mousewheel)

    def on_mousewheel(self, event):
        if event.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(1, "units")
        else:
            delta = event.delta
            units = int(-1*(delta/120)) if abs(delta) >= 120 else (-1 if delta > 0 else 1)
            self.canvas.yview_scroll(units, "units")
        self.redraw()

    def init_pool(self):
        for _ in range(self.pool_size):
            frame = ctk.CTkFrame(self.canvas, fg_color=BG_CARD, corner_radius=8, height=48)
            frame.grid_columnconfigure(1, weight=1); frame.grid_columnconfigure(2, weight=1)
            frame.grid_propagate(False)
            
            lbl_icon = ctk.CTkLabel(frame, text="", font=("Segoe UI", 18, "bold"), width=30)
            lbl_icon.grid(row=0, column=0, pady=8, padx=5)
            lbl_word = ctk.CTkLabel(frame, text="", font=("Segoe UI", 14, "bold"), anchor="w")
            lbl_word.grid(row=0, column=1, sticky="we", pady=8, padx=5)
            lbl_vn = ctk.CTkLabel(frame, text="", font=FONT_BODY, text_color=TEXT_SUB, anchor="w")
            lbl_vn.grid(row=0, column=2, sticky="we", pady=8, padx=5)
            lbl_count = ctk.CTkLabel(frame, text="", font=("Segoe UI", 14, "bold"), text_color=COLOR_SUCCESS[0], width=30)
            lbl_count.grid(row=0, column=3, pady=8, padx=5)
            btn_view = ctk.CTkButton(frame, text="Xem", width=50, height=28, font=("Segoe UI", 12, "bold"), fg_color=COLOR_ACCENT, hover_color="#4A48C0")
            btn_view.grid(row=0, column=4, padx=10, pady=8)
            
            for w in [frame, lbl_icon, lbl_word, lbl_vn, lbl_count, btn_view]:
                self.bind_scroll(w)
            
            wid = self.canvas.create_window(0, -1000, anchor='nw', window=frame)
            self.row_pool.append({
                'frame': frame, 'icon': lbl_icon, 'word': lbl_word, 
                'vn': lbl_vn, 'count': lbl_count, 'btn': btn_view, 
                'id': wid, 'data_idx': -1
            })

    def load_data(self):
        self.items = data_manager.get_all(self.item_type)
        self.set_sort(self.sort_criteria) 
    
    def set_sort(self, criteria):
        self.sort_criteria = criteria
        if criteria == "name": self.items.sort(key=lambda x: x[0])
        elif criteria == "recent": self.items.sort(key=lambda x: x[3] if x[3] else "0000", reverse=True)
        elif criteria == "oldest": self.items.sort(key=lambda x: x[3] if x[3] else "0000")
        elif criteria == "most": self.items.sort(key=lambda x: x[2], reverse=True)
        elif criteria == "least": self.items.sort(key=lambda x: x[2])
        self.update_total_height()
        for row in self.row_pool: row['data_idx'] = -1
        self.redraw()

    def update_total_height(self):
        self.total_height = max(len(self.items) * self.item_height, self.canvas.winfo_height())
        self.canvas.configure(scrollregion=(0, 0, self.canvas.winfo_width(), self.total_height))
    
    def on_resize(self, event):
        self.update_total_height()
        for row in self.row_pool:
            self.canvas.itemconfig(row['id'], width=event.width)
        self.redraw()
    
    def redraw(self):
        view_top = self.canvas.canvasy(0)
        first = max(0, int(view_top // self.item_height))
        last = min(len(self.items), first + self.pool_size)
        
        active_pool_indices = set()
        for data_idx in range(first, last):
            pool_idx = data_idx % self.pool_size
            active_pool_indices.add(pool_idx)
            row = self.row_pool[pool_idx]
            
            if row['data_idx'] != data_idx:
                word, vn_meaning, study_count, last_studied = self.items[data_idx]
                is_old = False
                if last_studied:
                    try:
                        if (datetime.now() - datetime.strptime(last_studied, "%Y-%m-%d %H:%M")).days >= 3:
                            is_old = True
                    except: pass
                
                row['icon'].configure(text="⚠" if is_old else "✦", text_color=COLOR_DANGER[0] if is_old else COLOR_ACCENT)
                row['word'].configure(text=word.capitalize())
                row['vn'].configure(text=vn_meaning.capitalize() if vn_meaning else "")
                row['count'].configure(text=str(study_count))
                row['btn'].configure(command=lambda w=word, ty=self.item_type: select_item(w, ty))
                row['data_idx'] = data_idx
            
            self.canvas.coords(row['id'], 0, data_idx * self.item_height)
            
        for i in range(self.pool_size):
            if i not in active_pool_indices and self.row_pool[i]['data_idx'] != -1:
                self.canvas.coords(self.row_pool[i]['id'], 0, -1000)
                self.row_pool[i]['data_idx'] = -1
                
    def refresh_item(self, word):
        """Cập nhật giao diện in-place cực mượt không cần reset list"""
        for i, (w, vn, count, last) in enumerate(self.items):
            if w == word:
                detail = data_manager.get_detail(word, self.item_type)
                self.items[i] = (w, detail['vn_meaning'], detail['study_count'], detail['last_studied'])
                pool_idx = i % self.pool_size
                if self.row_pool[pool_idx]['data_idx'] == i:
                    self.row_pool[pool_idx]['data_idx'] = -1 # Ép thẻ này vẽ lại ngay
                self.redraw()
                break

# ================== GIAO DIỆN CHÍNH ==================
app = ctk.CTk()
app.title("Vocab Master Premium")
app.geometry("1350x800")
app.grid_columnconfigure(1, weight=1)
app.grid_rowconfigure(1, weight=1)

top_bar = ctk.CTkFrame(app, height=45, corner_radius=0, fg_color=BG_CARD)
top_bar.grid(row=0, column=0, columnspan=2, sticky="ew")

def open_batch_add(): BatchAddDialog(app)
def show_statistics(): StatisticsWindow(app)
def backup_data():
    backup_path = os.path.join(BASE_DIR, f"backup_vocab_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
    with DB_LOCK:
        conn = sqlite3.connect(DB_PATH)
        backup_conn = sqlite3.connect(backup_path)
        conn.backup(backup_conn)
        backup_conn.close()
        conn.close()
    messagebox.showinfo("Sao lưu", f"Đã lưu cơ sở dữ liệu tại:\n{backup_path}")

ctk.CTkButton(top_bar, text="➕ Thêm hàng loạt", font=FONT_BODY, fg_color="transparent", command=open_batch_add).pack(side="left", padx=10, pady=5)
ctk.CTkButton(top_bar, text="🎮 Game Ôn Tập", font=FONT_BODY, fg_color="transparent", command=lambda: open_game_setup()).pack(side="left", padx=10, pady=5)
ctk.CTkButton(top_bar, text="📊 Thống kê", font=FONT_BODY, fg_color="transparent", command=show_statistics).pack(side="left", padx=10, pady=5)
ctk.CTkButton(top_bar, text="💾 Sao lưu", font=FONT_BODY, fg_color="transparent", command=backup_data).pack(side="left", padx=10, pady=5)
theme_menu = ctk.CTkOptionMenu(top_bar, values=["System", "Dark", "Light"], command=lambda m: ctk.set_appearance_mode(m), width=110)
theme_menu.pack(side="right", padx=10, pady=5)
theme_menu.set("Giao diện")

sidebar = ctk.CTkFrame(app, width=550, corner_radius=0, fg_color=BG_SIDEBAR)
sidebar.grid(row=1, column=0, sticky="nsew")
sidebar.grid_propagate(False)

ctk.CTkLabel(sidebar, text="V O C A B", font=("Segoe UI", 24, "bold"), text_color=COLOR_ACCENT).pack(pady=(30, 5))
ctk.CTkLabel(sidebar, text="Master Your English", font=FONT_BODY, text_color=TEXT_SUB).pack(pady=(0, 15))

add_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
add_frame.pack(fill="x", padx=20, pady=10)
entry_add = ctk.CTkEntry(add_frame, placeholder_text="Nhập nhanh 1 từ/cụm từ...", height=45, font=FONT_BODY)
entry_add.pack(side="left", fill="x", expand=True)
btn_add = ctk.CTkButton(add_frame, text="+", width=45, height=45, font=("Segoe UI", 24, "bold"), fg_color=COLOR_ACCENT, command=lambda: add_item())
btn_add.pack(side="right", padx=(10, 0))
app.bind('<Return>', lambda e: add_item())

sort_var = ctk.StringVar(value="Sắp xếp: Ngày học (Gần nhất)")
sort_options = ["Sắp xếp: Tên (A-Z)", "Sắp xếp: Ngày học (Gần nhất)", "Sắp xếp: Ngày học (Xa nhất)", "Sắp xếp: Số lần học (Nhiều nhất)", "Sắp xếp: Số lần học (Ít nhất)"]
def on_sort_change(choice):
    mapping = {"Sắp xếp: Tên (A-Z)": "name", "Sắp xếp: Ngày học (Gần nhất)": "recent", "Sắp xếp: Ngày học (Xa nhất)": "oldest", "Sắp xếp: Số lần học (Nhiều nhất)": "most", "Sắp xếp: Số lần học (Ít nhất)": "least"}
    (scroll_vocab if tab_view.get() == "Từ Đơn" else scroll_phrase).set_sort(mapping.get(choice, "recent"))
ctk.CTkOptionMenu(sidebar, variable=sort_var, values=sort_options, command=on_sort_change, font=FONT_BODY).pack(fill="x", padx=20, pady=(5,10))

tab_view = ctk.CTkTabview(sidebar, width=500)
tab_view.pack(fill="both", expand=True, padx=20, pady=5)
tab_view.add("Từ Đơn")
tab_view.add("Cụm Từ")

scroll_vocab = VirtualScrollList(tab_view.tab("Từ Đơn"), item_type='vocab', bg=BG_SIDEBAR[1])
scroll_vocab.pack(fill="both", expand=True)
scroll_phrase = VirtualScrollList(tab_view.tab("Cụm Từ"), item_type='phrase', bg=BG_SIDEBAR[1])
scroll_phrase.pack(fill="both", expand=True)

main_view = ctk.CTkFrame(app, corner_radius=0, fg_color=BG_MAIN)
main_view.grid(row=1, column=1, sticky="nsew")
frame_welcome = ctk.CTkFrame(main_view, fg_color="transparent")
frame_welcome.pack(expand=True)
ctk.CTkLabel(frame_welcome, text="📚", font=("Segoe UI", 70)).pack(pady=10)
ctk.CTkLabel(frame_welcome, text="Học thôi nào!", font=("Segoe UI", 24, "bold")).pack()

detail_container = ctk.CTkScrollableFrame(main_view, fg_color="transparent")

current_item, current_type = None, None

def refresh_lists():
    scroll_vocab.load_data()
    scroll_phrase.load_data()

def select_item(word, item_type):
    global current_item, current_type
    current_item, current_type = word, item_type
    
    # Cập nhật siêu tốc RAM-First
    data_manager.update_progress(word, item_type)
    detail = data_manager.get_detail(word, item_type)
    if not detail: return
    
    # Cập nhật danh sách in-place
    (scroll_vocab if item_type == 'vocab' else scroll_phrase).refresh_item(word)
    
    frame_welcome.pack_forget()
    detail_container.pack(fill="both", expand=True, padx=40, pady=20)
    lbl_title.configure(text=word.lower())
    lbl_vn.configure(text=detail['vn_meaning'].capitalize() if detail['vn_meaning'] else "")
    lbl_pos_text.configure(text=detail['pos'])
    lbl_ex.configure(text=f'"{detail["sentence"]}"')
    lbl_stats.configure(text=f"🔥 Số lần: {detail['study_count']}  •  🕒 Lần cuối: {detail['last_studied']}")
    lbl_alert.pack_forget()
    if detail['study_count'] >= 10 and detail['last_studied'] and (datetime.now() - datetime.strptime(detail['last_studied'], "%Y-%m-%d %H:%M")).days >= 3:
        lbl_alert.configure(text="🚨 Cảnh báo: Từ/Cụm này lâu rồi chưa ôn lại!")
        lbl_alert.pack(anchor="w", padx=25, pady=(10, 0))
    txt_note.delete("1.0", "end")
    txt_note.insert("1.0", detail.get("custom_sentence", ""))
    lbl_img.configure(image="", text="Đang tìm ảnh...")
    play_sound_system(word)
    load_image_async(word, lbl_img)

def add_item():
    word = entry_add.get().strip().lower()
    if not word: return
    
    if word in data_manager.vocab:
        entry_add.delete(0, 'end'); tab_view.set("Từ Đơn"); select_item(word, 'vocab'); return
    if word in data_manager.phrase:
        entry_add.delete(0, 'end'); tab_view.set("Cụm Từ"); select_item(word, 'phrase'); return
    
    is_single = len(word.split()) == 1
    item_type = 'vocab' if is_single else 'phrase'
    entry_add.configure(state="disabled", placeholder_text="⏳ Đang tải dữ liệu...")
    
    def fetch_and_add():
        ex, pos, vn = get_word_info(word) if is_single else get_phrase_info(word)
        data_manager.add_or_update(word, item_type, ex, pos, vn, "")
        app.after(0, lambda: [entry_add.configure(state="normal", placeholder_text="Nhập nhanh 1 từ/cụm từ..."), entry_add.delete(0, 'end'), tab_view.set("Từ Đơn" if item_type == 'vocab' else "Cụm Từ"), refresh_lists(), select_item(word, item_type)])
    executor.submit(fetch_and_add)

def edit_vn_meaning():
    if not current_item: return
    new_vn = ctk.CTkInputDialog(text=f"Sửa nghĩa tiếng Việt của '{current_item}':", title="Sửa nghĩa").get_input()
    if new_vn and new_vn.strip():
        data_manager.update_field(current_item, current_type, 'vn_meaning', new_vn.strip())
        lbl_vn.configure(text=new_vn.strip().capitalize())
        (scroll_vocab if current_type == 'vocab' else scroll_phrase).refresh_item(current_item)

def item_delete_cmd():
    global current_item, current_type
    if current_item and messagebox.askyesno("Xóa", f"Xóa '{current_item}'?"):
        data_manager.delete(current_item, current_type)
        detail_container.pack_forget(); frame_welcome.pack(expand=True)
        refresh_lists()
        current_item, current_type = None, None

def save_custom_note():
    if current_item:
        data_manager.update_field(current_item, current_type, 'custom_sentence', txt_note.get("1.0", "end-1c"))
        messagebox.showinfo("OK", "Đã lưu ghi chú")

c1 = ctk.CTkFrame(detail_container, corner_radius=15, fg_color="transparent")
c1.pack(fill="x", pady=(10, 20))
hl = ctk.CTkFrame(c1, fg_color="transparent")
hl.pack(side="left")
lbl_title = ctk.CTkLabel(hl, text="", font=FONT_TITLE, wraplength=400, justify="left")
lbl_title.pack(anchor="w")
vf = ctk.CTkFrame(hl, fg_color="transparent")
vf.pack(anchor="w")
lbl_vn = ctk.CTkLabel(vf, text="", font=FONT_VN, text_color=COLOR_SUCCESS[0], wraplength=350, justify="left")
lbl_vn.pack(side="left")
ctk.CTkButton(vf, text="✏️", width=30, height=30, fg_color="transparent", text_color=COLOR_ACCENT, command=edit_vn_meaning).pack(side="left", padx=(10, 0))
pf = ctk.CTkFrame(c1, corner_radius=20, fg_color=COLOR_ACCENT)
pf.pack(side="left", pady=(10,0), padx=20)
lbl_pos_text = ctk.CTkLabel(pf, text="", font=("Segoe UI", 14), text_color="white")
lbl_pos_text.pack(padx=15, pady=2)
ctk.CTkButton(c1, text="🔊 Nghe", width=100, height=40, corner_radius=20, fg_color=BG_CARD, command=lambda: play_sound_system(current_item) if current_item else None).pack(side="right", pady=20)

c2 = ctk.CTkFrame(detail_container, fg_color="transparent")
c2.pack(fill="x", pady=10)
img_f = ctk.CTkFrame(c2, corner_radius=15, fg_color=BG_CARD, width=180, height=180)
img_f.pack(side="left"); img_f.pack_propagate(False)
lbl_img = ctk.CTkLabel(img_f, text="⌛", font=FONT_BODY, text_color=TEXT_SUB)
lbl_img.pack(expand=True)
c2_info = ctk.CTkFrame(c2, corner_radius=15, fg_color=BG_CARD)
c2_info.pack(side="left", fill="both", expand=True, padx=(20, 0))
lbl_alert = ctk.CTkLabel(c2_info, text="", font=("Segoe UI", 13, "bold"), text_color=COLOR_DANGER[0])
lbl_stats = ctk.CTkLabel(c2_info, text="", font=FONT_BODY, text_color=TEXT_SUB)
lbl_stats.pack(anchor="w", padx=25, pady=(20, 5))
lbl_ex = ctk.CTkLabel(c2_info, text="", font=FONT_ITALIC, wraplength=450, justify="left")
lbl_ex.pack(anchor="w", padx=25, pady=(5, 15))
ctk.CTkButton(c2_info, text="▶ Nghe câu ví dụ", border_width=1, fg_color="transparent", command=lambda: play_sound_system(data_manager.get_detail(current_item, current_type)['sentence'] if current_item else "")).pack(anchor="w", padx=25)

c3 = ctk.CTkFrame(detail_container, corner_radius=15, fg_color=BG_CARD)
c3.pack(fill="x", pady=20)
ctk.CTkLabel(c3, text="📝 Ghi chú của bạn / Đặt câu tự do", font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=25, pady=(20, 10))
txt_note = ctk.CTkTextbox(c3, height=100, corner_radius=8, fg_color=BG_MAIN, font=FONT_BODY)
txt_note.pack(fill="x", padx=25, pady=(0, 20))
bf = ctk.CTkFrame(c3, fg_color="transparent")
bf.pack(fill="x", padx=25, pady=(0, 25))
ctk.CTkButton(bf, text="💾 Lưu", fg_color=COLOR_SUCCESS, width=100, command=save_custom_note).pack(side="left")
ctk.CTkButton(bf, text="🗑 Xóa Mục", fg_color="transparent", text_color=COLOR_DANGER[0], border_width=1, border_color=COLOR_DANGER[0], width=80, command=item_delete_cmd).pack(side="right")

# ================== GAME ÔN TẬP ==================
def get_game_data(source_type):
    today = datetime.now().strftime("%Y-%m-%d")
    items = []
    for t, data_dict in [('vocab', data_manager.vocab), ('phrase', data_manager.phrase)]:
        for word, d in data_dict.items():
            if source_type == "Chưa ôn hôm nay":
                if not d['last_studied'] or d['last_studied'][:10] != today:
                    items.append({"word": word, "vn_meaning": d['vn_meaning'], "item_type": t, "last_studied": d['last_studied'], "study_count": d['study_count']})
            else:
                items.append({"word": word, "vn_meaning": d['vn_meaning'], "item_type": t, "last_studied": d['last_studied'], "study_count": d['study_count']})
                
    items.sort(key=lambda x: (x['study_count'], - (datetime.now() - datetime.strptime(x['last_studied'], "%Y-%m-%d %H:%M")).days if x['last_studied'] else 0))
    return items

class GameSetupDialog(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Cài đặt Game"); self.geometry("500x500"); self.transient(master); self.grab_set()
        self.result_num, self.result_mode, self.result_data = None, None, None
        ctk.CTkLabel(self, text="CÀI ĐẶT TRÒ CHƠI", font=("Segoe UI", 20, "bold"), text_color=COLOR_ACCENT).pack(pady=(20, 10))
        self.source_mode = ctk.CTkSegmentedButton(self, values=["Ngẫu nhiên", "Chưa ôn hôm nay"], font=FONT_BODY, command=self.update_slider_max)
        self.source_mode.set("Chưa ôn hôm nay"); self.source_mode.pack(pady=10, fill="x", padx=30)
        self.lbl_empty_alert = ctk.CTkLabel(self, text="", text_color=COLOR_SUCCESS[0]); self.lbl_empty_alert.pack()
        self.game_mode = ctk.CTkSegmentedButton(self, values=["Trắc nghiệm", "Đảo chữ", "Nối từ", "Nghe & Gõ"], font=FONT_BODY)
        self.game_mode.set("Trắc nghiệm"); self.game_mode.pack(pady=10, fill="x", padx=30)
        self.lbl_val = ctk.CTkLabel(self, text="5", font=("Segoe UI", 36, "bold"), text_color=COLOR_SUCCESS[0]); self.lbl_val.pack(pady=15)
        self.slider = ctk.CTkSlider(self, from_=1, to=10, number_of_steps=9, command=lambda v: self.lbl_val.configure(text=str(int(v))))
        self.slider.pack(fill="x", padx=40, pady=10)
        btn_frame = ctk.CTkFrame(self, fg_color="transparent"); btn_frame.pack(pady=(15, 20))
        ctk.CTkButton(btn_frame, text="Hủy", width=100, fg_color="transparent", border_width=1, command=self.destroy).pack(side="left", padx=10)
        self.btn_start = ctk.CTkButton(btn_frame, text="Bắt đầu", width=100, fg_color=COLOR_SUCCESS, command=self.on_ok)
        self.btn_start.pack(side="right", padx=10)
        self.update_slider_max(self.source_mode.get())
        self.wait_window()
    
    def update_slider_max(self, mode):
        data = get_game_data(mode)
        max_words = min(len(data), 50)
        if max_words == 0:
            self.lbl_empty_alert.configure(text="🎉 Bạn đã ôn hết từ vựng hôm nay."); self.slider.configure(state="disabled"); self.btn_start.configure(state="disabled"); self.lbl_val.configure(text="0")
        else:
            self.lbl_empty_alert.configure(text=""); self.slider.configure(state="normal", from_=1, to=max_words, number_of_steps=max_words-1 if max_words>1 else 1); self.btn_start.configure(state="normal")
            self.slider.set(min(5, max_words)); self.lbl_val.configure(text=str(int(min(5, max_words))))
            
    def on_ok(self):
        self.result_num, self.result_mode, self.result_data = int(self.slider.get()), self.game_mode.get(), get_game_data(self.source_mode.get())
        self.destroy()

def open_game_setup():
    d = GameSetupDialog(app)
    if d.result_num and d.result_data:
        if d.result_mode == "Trắc nghiệm": QuizGameWindow(app, d.result_num, d.result_data)
        elif d.result_mode == "Đảo chữ": ScrambleGameWindow(app, d.result_num, d.result_data)
        elif d.result_mode == "Nối từ": MatchGameWindow(app, min(d.result_num, 10), d.result_data)
        elif d.result_mode == "Nghe & Gõ": DictationGameWindow(app, d.result_num, d.result_data)

class BaseGameWindow(ctk.CTkToplevel):
    def __init__(self, master, title):
        super().__init__(master); self.title(title); self.geometry("600x500"); self.transient(master); self.grab_set()
        self.questions = []; self.current_idx = 0; self.score = 0

class QuizGameWindow(BaseGameWindow):
    def __init__(self, master, num, data):
        super().__init__(master, "Game Trắc Nghiệm"); self.game_data = data; self.prepare(num); self.build(); self.load()
    def prepare(self, num):
        for item in random.sample(self.game_data, min(num, len(self.game_data))):
            opts = [item['word']] + random.sample([x['word'] for x in self.game_data if x['word'] != item['word']], min(3, len(self.game_data)-1))
            random.shuffle(opts); self.questions.append((item['word'], item['vn_meaning'], opts, item['item_type']))
    def build(self):
        self.lbl_progress = ctk.CTkLabel(self, text="Câu 0", font=FONT_BODY, text_color=TEXT_SUB); self.lbl_progress.pack(pady=(20, 5))
        self.lbl_q = ctk.CTkLabel(self, text="", font=("Segoe UI", 28, "bold"), text_color=COLOR_ACCENT, wraplength=500); self.lbl_q.pack(pady=(10, 30))
        self.btn_opts = [ctk.CTkButton(self, text="", height=50, corner_radius=10, font=("Segoe UI", 16, "bold"), fg_color=BG_CARD, command=lambda i=i: self.check(i)) for i in range(4)]
        for b in self.btn_opts: b.pack(fill="x", padx=40, pady=8)
    def load(self):
        if self.current_idx >= len(self.questions):
            messagebox.showinfo("Kết thúc", f"Đúng {self.score}/{len(self.questions)} câu."); refresh_lists(); self.destroy(); return
        word, vn, opts, _ = self.questions[self.current_idx]
        self.lbl_progress.configure(text=f"Câu {self.current_idx+1}/{len(self.questions)}"); self.lbl_q.configure(text=vn.capitalize())
        for i, o in enumerate(opts): self.btn_opts[i].configure(text=o.capitalize())
    def check(self, idx):
        cw, _, opts, ty = self.questions[self.current_idx]
        if opts[idx] == cw: data_manager.update_progress(cw, ty); self.score += 1; play_sound_system(cw)
        else: messagebox.showerror("Sai", f"Đáp án đúng: {cw.capitalize()}")
        self.current_idx += 1; self.load()

class ScrambleGameWindow(BaseGameWindow):
    def __init__(self, master, num, data):
        super().__init__(master, "Game Đảo Chữ"); self.game_data = data; self.prepare(num); self.build(); self.load()
    def prepare(self, num):
        for item in random.sample(self.game_data, min(num, len(self.game_data))): self.questions.append((item['word'], item['vn_meaning'], item['item_type']))
    def build(self):
        self.lbl_progress = ctk.CTkLabel(self, text="Câu 0", font=FONT_BODY, text_color=TEXT_SUB); self.lbl_progress.pack(pady=(20, 5))
        self.lbl_vn = ctk.CTkLabel(self, text="", font=("Segoe UI", 24, "bold"), text_color=COLOR_SUCCESS[0]); self.lbl_vn.pack(pady=10)
        self.lbl_scr = ctk.CTkLabel(self, text="", font=("Segoe UI", 36, "bold"), text_color=COLOR_ACCENT); self.lbl_scr.pack(pady=(10, 30))
        self.entry = ctk.CTkEntry(self, font=("Segoe UI", 24, "bold"), justify="center", height=60); self.entry.pack(fill="x", padx=60, pady=10)
        self.entry.bind('<Return>', lambda e: self.check())
        bf = ctk.CTkFrame(self, fg_color="transparent"); bf.pack(pady=20)
        ctk.CTkButton(bf, text="🔊 Nghe", width=120, height=45, fg_color=BG_CARD, command=lambda: play_sound_system(self.questions[self.current_idx][0])).pack(side="left", padx=10)
        ctk.CTkButton(bf, text="Kiểm tra", width=120, height=45, fg_color=COLOR_ACCENT, command=self.check).pack(side="right", padx=10)
    def load(self):
        if self.current_idx >= len(self.questions):
            messagebox.showinfo("Kết thúc", f"Đúng {self.score}/{len(self.questions)} từ."); refresh_lists(); self.destroy(); return
        word, vn, _ = self.questions[self.current_idx]
        self.lbl_progress.configure(text=f"Câu {self.current_idx+1}/{len(self.questions)}"); self.lbl_vn.configure(text=vn.capitalize())
        scr = []
        for w in word.split():
            chars = list(w); random.shuffle(chars)
            while ''.join(chars) == w and len(w) > 2: random.shuffle(chars)
            scr.append(''.join(chars).upper())
        self.lbl_scr.configure(text="   ".join(scr)); self.entry.delete(0, 'end'); self.entry.focus()
    def check(self):
        cw, _, ty = self.questions[self.current_idx]
        if self.entry.get().strip().lower() == cw: data_manager.update_progress(cw, ty); self.score += 1; play_sound_system(cw)
        else: messagebox.showerror("Sai", f"Từ đúng là: {cw.capitalize()}")
        self.current_idx += 1; self.load()

class DictationGameWindow(BaseGameWindow):
    def __init__(self, master, num, data):
        super().__init__(master, "Game Nghe & Gõ"); self.game_data = data; self.prepare(num); self.build(); self.load()
    def prepare(self, num):
        for item in random.sample(self.game_data, min(num, len(self.game_data))): self.questions.append((item['word'], item['vn_meaning'], item['item_type']))
    def build(self):
        self.lbl_progress = ctk.CTkLabel(self, text="Câu 0", font=FONT_BODY, text_color=TEXT_SUB); self.lbl_progress.pack(pady=(20, 5))
        ctk.CTkButton(self, text="🔊 NGHE", font=("Segoe UI", 24, "bold"), height=80, command=lambda: play_sound_system(self.questions[self.current_idx][0])).pack(pady=20)
        self.lbl_hint = ctk.CTkLabel(self, text="---", font=("Segoe UI", 18, "italic"), text_color=COLOR_SUCCESS[0]); self.lbl_hint.pack(pady=10)
        self.entry = ctk.CTkEntry(self, font=("Segoe UI", 24, "bold"), justify="center", height=60); self.entry.pack(fill="x", padx=60, pady=10)
        self.entry.bind('<Return>', lambda e: self.check())
        bf = ctk.CTkFrame(self, fg_color="transparent"); bf.pack(pady=20)
        ctk.CTkButton(bf, text="💡 Gợi ý", width=120, height=45, fg_color=BG_CARD, command=lambda: self.lbl_hint.configure(text=f"Nghĩa: {self.questions[self.current_idx][1].capitalize()}")).pack(side="left", padx=10)
        ctk.CTkButton(bf, text="Kiểm tra", width=120, height=45, fg_color=COLOR_ACCENT, command=self.check).pack(side="right", padx=10)
    def load(self):
        if self.current_idx >= len(self.questions):
            messagebox.showinfo("Kết thúc", f"Nghe đúng {self.score}/{len(self.questions)} từ."); refresh_lists(); self.destroy(); return
        self.lbl_progress.configure(text=f"Câu {self.current_idx+1}/{len(self.questions)}"); self.lbl_hint.configure(text="---")
        self.entry.delete(0, 'end'); self.entry.focus(); play_sound_system(self.questions[self.current_idx][0])
    def check(self):
        cw, _, ty = self.questions[self.current_idx]
        if self.entry.get().strip().lower() == cw: data_manager.update_progress(cw, ty); self.score += 1; play_sound_system(cw)
        else: messagebox.showerror("Sai", f"Từ đúng là: {cw.capitalize()}")
        self.current_idx += 1; self.load()

class MatchGameWindow(ctk.CTkToplevel):
    def __init__(self, master, num, data):
        super().__init__(master); self.title("Game Nối Từ"); self.geometry("800x600"); self.transient(master); self.grab_set()
        self.score = 0; self.sel_en = self.sel_vi = None; self.game_data = data; self.pairs = [(i['word'], i['vn_meaning'], i['item_type']) for i in random.sample(data, min(num, len(data)))]
        self.btn_en = {}; self.btn_vi = {}; self.build()
    def build(self):
        ctk.CTkLabel(self, text="Ghép từ tiếng Anh với nghĩa tiếng Việt", font=("Segoe UI", 18, "bold")).pack(pady=20)
        gf = ctk.CTkFrame(self, fg_color="transparent"); gf.pack(fill="both", expand=True, padx=20, pady=10)
        gf.grid_columnconfigure(0, weight=1); gf.grid_columnconfigure(1, weight=1)
        el, vl = list(self.pairs), list(self.pairs); random.shuffle(el); random.shuffle(vl)
        fe = ctk.CTkFrame(gf, fg_color="transparent"); fe.grid(row=0, column=0, sticky="nsew", padx=10)
        fv = ctk.CTkFrame(gf, fg_color="transparent"); fv.grid(row=0, column=1, sticky="nsew", padx=10)
        for w, _, _ in el:
            b = ctk.CTkButton(fe, text=w.capitalize(), height=50, corner_radius=10, fg_color=BG_CARD, command=lambda w=w: self.sel(w, 'en'))
            b.pack(fill="x", pady=8); self.btn_en[w] = b
        for _, v, _ in vl:
            b = ctk.CTkButton(fv, text=v.capitalize(), height=50, corner_radius=10, fg_color=BG_CARD, command=lambda v=v: self.sel(v, 'vi'))
            b.pack(fill="x", pady=8); self.btn_vi[v] = b
    def sel(self, val, lang):
        if lang == 'en':
            for b in self.btn_en.values(): b.configure(border_width=0)
            self.sel_en = val; self.btn_en[val].configure(border_width=2, border_color=COLOR_ACCENT)
        else:
            for b in self.btn_vi.values(): b.configure(border_width=0)
            self.sel_vi = val; self.btn_vi[val].configure(border_width=2, border_color=COLOR_SUCCESS[0])
        if self.sel_en and self.sel_vi:
            pair = next((p for p in self.pairs if p[0] == self.sel_en and p[1] == self.sel_vi), None)
            if pair:
                play_sound_system(pair[0]); data_manager.update_progress(pair[0], pair[2]); self.btn_en[pair[0]].destroy(); self.btn_vi[pair[1]].destroy()
                self.score += 1
                if self.score == len(self.pairs): messagebox.showinfo("Hoàn thành", "Nối đúng tất cả!"); refresh_lists(); self.destroy()
            else:
                messagebox.showerror("Sai", "Không khớp!")
            self.sel_en = self.sel_vi = None
            for b in self.btn_en.values(): b.configure(border_width=0)
            for b in self.btn_vi.values(): b.configure(border_width=0)

# ================== BATCH ADD ==================
class BatchAddDialog(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master); self.title("Thêm Hàng Loạt"); self.geometry("500x450"); self.transient(master); self.grab_set()
        ctk.CTkLabel(self, text="📝 THÊM TỪ VỰNG HÀNG LOẠT", font=("Segoe UI", 18, "bold"), text_color=COLOR_ACCENT).pack(pady=(20,5))
        ctk.CTkLabel(self, text="Ngăn cách nhau bằng dấu phẩy (,)", text_color=TEXT_SUB, font=("Segoe UI", 13)).pack(pady=(0,15))
        self.textbox = ctk.CTkTextbox(self, height=200, font=("Segoe UI", 15)); self.textbox.pack(fill="x", padx=25, pady=10)
        self.lbl_status = ctk.CTkLabel(self, text="Sẵn sàng...", text_color=COLOR_SUCCESS[0]); self.lbl_status.pack(pady=5)
        bf = ctk.CTkFrame(self, fg_color="transparent"); bf.pack(pady=10)
        ctk.CTkButton(bf, text="Hủy bỏ", width=100, fg_color="transparent", border_width=1, command=self.destroy).pack(side="left", padx=10)
        self.btn_start = ctk.CTkButton(bf, text="Bắt đầu", width=140, command=self.start); self.btn_start.pack(side="right", padx=10)
    
    def start(self):
        content = self.textbox.get("1.0", "end").strip()
        if not content: return
        words = list(dict.fromkeys([w.strip().lower() for w in content.split(",") if w.strip()]))
        if not words: return
        self.btn_start.configure(state="disabled"); self.textbox.configure(state="disabled")
        threading.Thread(target=self.process_parallel, args=(words,), daemon=True).start()
    
    def process_parallel(self, words):
        total = len(words)
        def fetch_word(w):
            if w in data_manager.vocab or w in data_manager.phrase: return None
            is_single = len(w.split()) == 1
            ex, pos, vn = get_word_info(w) if is_single else get_phrase_info(w)
            return (w, 'vocab' if is_single else 'phrase', ex, pos, vn, "")
        
        futures = [executor.submit(fetch_word, w) for w in words]
        results = []
        for i, future in enumerate(futures):
            app.after(0, lambda idx=i: self.lbl_status.configure(text=f"⏳ Đang gọi dữ liệu API song song ({idx+1}/{total})..."))
            res = future.result()
            if res: results.append(res)
            
        if results:
            app.after(0, lambda: self.lbl_status.configure(text=f"⏳ Đang cập nhật hệ thống..."))
            for r in results: data_manager.add_or_update(r[0], r[1], r[2], r[3], r[4], r[5], sync_db=False)
            
            def save_batch(batch):
                with DB_LOCK:
                    conn = sqlite3.connect(DB_PATH)
                    conn.execute("BEGIN TRANSACTION")
                    for r in batch:
                        conn.execute(f"INSERT INTO {r[1]} (word, sentence, pos, vn_meaning, custom_sentence, last_studied, study_count) VALUES (?,?,?,?,?,?,?)",
                                     (r[0], r[2], r[3], r[4], r[5], "", 0))
                    conn.commit()
                    conn.close()
            executor.submit(save_batch, results)
                
        app.after(0, lambda: self.finish(len(results)))
        
    def finish(self, added):
        if added == 0: self.lbl_status.configure(text="Tất cả từ đã có sẵn!", text_color="gray")
        else: self.lbl_status.configure(text=f"✅ Hoàn tất! Đã thêm cực nhanh {added} mục.", text_color=COLOR_SUCCESS[0])
        self.btn_start.configure(text="Đóng", state="normal", command=self.destroy)
        refresh_lists()

# ================== STATISTICS ==================
class StatisticsWindow(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master); self.title("Thống Kê"); self.geometry("650x550"); self.transient(master); self.grab_set()
        tv, tp, st, m, w, u = get_study_stats()
        ctk.CTkLabel(self, text="📊 TỔNG QUAN HỌC TẬP", font=("Segoe UI", 24, "bold"), text_color=COLOR_ACCENT).pack(pady=(20, 10))
        grid = ctk.CTkFrame(self, fg_color="transparent"); grid.pack(fill="both", expand=True, padx=20, pady=10)
        grid.grid_columnconfigure(0, weight=1); grid.grid_columnconfigure(1, weight=1)
        def mk(r, c, t, v, col):
            card = ctk.CTkFrame(grid, corner_radius=15, fg_color=BG_CARD); card.grid(row=r, column=c, padx=10, pady=10, sticky="nsew")
            ctk.CTkLabel(card, text=t, font=FONT_BODY, text_color=TEXT_SUB).pack(pady=(20, 5))
            ctk.CTkLabel(card, text=str(v), font=("Segoe UI", 42, "bold"), text_color=col).pack(pady=(0, 20))
        mk(0, 0, "📚 Tổng Từ Đơn", tv, COLOR_ACCENT); mk(0, 1, "💬 Tổng Cụm Từ", tp, COLOR_ACCENT)
        mk(1, 0, "🔥 Đã học hôm nay", st, COLOR_SUCCESS[0]); mk(1, 1, "✅ Đã thuộc (>15 lần)", m, COLOR_SUCCESS[0])
        mk(2, 0, "🚨 Cảnh báo (Lâu chưa ôn)", w, COLOR_DANGER[0]); mk(2, 1, "🆕 Chưa học (0 lần)", u, "gray")

if __name__ == "__main__":
    app.mainloop()