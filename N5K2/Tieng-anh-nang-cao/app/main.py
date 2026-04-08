import customtkinter as ctk
from tkinter import messagebox
import json
import os
from datetime import datetime
import pyttsx3
import requests
from io import BytesIO
from PIL import Image
import threading
import queue
from spellchecker import SpellChecker
import random
import re

# --- 1. THIẾT LẬP GIAO DIỆN & TỔNG QUAN ---
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

spell = SpellChecker() 
FILE_NAME = "vocab_data.json"

FONT_HEADING = ("Segoe UI", 36, "bold")
FONT_SUBHEADING = ("Segoe UI", 20, "bold")
FONT_BODY = ("Segoe UI", 15)
FONT_ITALIC = ("Segoe UI", 15, "italic")

# Từ điển dịch từ loại sang tiếng Việt
POS_MAP = {
    "noun": "Danh từ",
    "verb": "Động từ",
    "adjective": "Tính từ",
    "adverb": "Trạng từ",
    "pronoun": "Đại từ",
    "preposition": "Giới từ",
    "conjunction": "Liên từ",
    "interjection": "Thán từ"
}

# --- HÀNG ĐỢI ÂM THANH (FIX LỖI DELAY) ---
tts_queue = queue.Queue()

def tts_worker():
    # Khởi tạo engine bên trong luồng để tránh kẹt trên Windows
    engine = pyttsx3.init()
    while True:
        text = tts_queue.get()
        if text is None: break
        engine.say(text)
        engine.runAndWait()
        tts_queue.task_done()

# Chạy luồng âm thanh ngầm ngay khi mở app
threading.Thread(target=tts_worker, daemon=True).start()

def read_text_async(text):
    if text:
        tts_queue.put(text) # Đẩy chữ vào hàng đợi, sẽ đọc ngay lập tức

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
game_window = None 

def get_word_info(word):
    try:
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            data = response.json()
            pos_set = set()
            example_sentence = "Chưa có câu ví dụ tự động."
            
            for meaning in data[0].get("meanings", []):
                # Lấy và dịch từ loại
                pos_raw = meaning.get("partOfSpeech", "unknown").lower()
                pos_vn = POS_MAP.get(pos_raw, pos_raw)
                pos_set.add(pos_vn)
                
                # Lấy câu ví dụ đầu tiên có
                for defs in meaning.get("definitions", []):
                    if "example" in defs and example_sentence == "Chưa có câu ví dụ tự động.":
                        example_sentence = defs["example"]
            
            pos_str = " | ".join(pos_set) if pos_set else "Chưa rõ"
            return example_sentence, pos_str
    except: pass
    return "Chưa có câu ví dụ tự động.", "Chưa rõ"

def check_warning(data):
    if data.get("study_count", 0) >= 10: return False
    last_studied_str = data.get("last_studied", "")
    try:
        days_diff = (datetime.now() - datetime.strptime(last_studied_str, "%Y-%m-%d %H:%M")).days
        if days_diff > 5: return True
    except: pass
    return False

# --- 3. ĐA LUỒNG TẢI ẢNH ---
def load_image_async(word):
    lbl_image.configure(image=None, text="⏳ Tải ảnh...")
    def fetch():
        try:
            url = f"https://picsum.photos/seed/{word}/300/300"
            response = requests.get(url, timeout=5)
            img = Image.open(BytesIO(response.content))
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(180, 180))
            def update_ui():
                if current_word == word:
                    lbl_image.configure(image=ctk_img, text="")
                    lbl_image.image = ctk_img
            app.after(0, update_ui)
        except:
            def update_ui_error():
                if current_word == word:
                    lbl_image.configure(image=None, text="[Mất kết nối]")
            app.after(0, update_ui_error)
    threading.Thread(target=fetch, daemon=True).start()


# --- 4. MINI GAME: ÔN TẬP TỪ VỰNG ---
def open_game_setup():
    global game_window
    if len(vocab_data) < 4:
        messagebox.showwarning("Thiếu từ vựng", "Cần ít nhất 4 từ vựng để chơi!")
        return

    if game_window and game_window.winfo_exists():
        game_window.focus()
        return

    game_window = ctk.CTkToplevel(app)
    game_window.title("Cài đặt Game")
    game_window.geometry("400x300")
    game_window.attributes('-topmost', True)

    ctk.CTkLabel(game_window, text="🎮 ÔN TẬP", font=FONT_SUBHEADING).pack(pady=(30, 10))
    ctk.CTkLabel(game_window, text="Ưu tiên từ ít học, lâu chưa ôn.", font=("Segoe UI", 13), text_color="gray").pack(pady=5)

    max_words = len(vocab_data)
    options = [str(i) for i in [5, 10, 15, 20] if i <= max_words]
    if str(max_words) not in options:
        options.append(str(max_words))

    ctk.CTkLabel(game_window, text="Số lượng câu hỏi:", font=FONT_BODY).pack(pady=(15, 5))
    combo_qty = ctk.CTkComboBox(game_window, values=options, state="readonly", font=FONT_BODY)
    combo_qty.set(options[0])
    combo_qty.pack(pady=5)

    def start_game():
        qty = int(combo_qty.get())
        game_window.destroy()
        run_game_ui(qty)

    ctk.CTkButton(game_window, text="Bắt Đầu", font=("Segoe UI", 16, "bold"), height=40, command=start_game, fg_color="#27ae60", hover_color="#2ecc71").pack(pady=20)

def run_game_ui(quantity):
    now = datetime.now()
    def sort_key(word):
        info = vocab_data[word]
        count = info.get("study_count", 0)
        try:
            last_date = datetime.strptime(info.get("last_studied", "2000-01-01 00:00"), "%Y-%m-%d %H:%M")
            days_old = (now - last_date).days
        except:
            days_old = 999
        return (count, -days_old) 
    
    sorted_words = sorted(vocab_data.keys(), key=sort_key)
    target_words = sorted_words[:quantity]
    random.shuffle(target_words)

    all_words_list = list(vocab_data.keys())

    play_win = ctk.CTkToplevel(app)
    play_win.title("Game Ôn Tập")
    play_win.geometry("700x500")
    play_win.attributes('-topmost', True)
    
    current_q_idx = 0
    score = 0
    buttons = []

    lbl_progress = ctk.CTkLabel(play_win, text="", font=("Segoe UI", 16, "bold"), text_color="#2980b9")
    lbl_progress.pack(pady=(20, 10))

    frame_question = ctk.CTkFrame(play_win, corner_radius=15, fg_color=("gray90", "gray15"))
    frame_question.pack(fill="x", padx=40, pady=10)

    lbl_question = ctk.CTkLabel(frame_question, text="", font=("Segoe UI", 20, "italic"), wraplength=550)
    lbl_question.pack(pady=30, padx=20)

    frame_answers = ctk.CTkFrame(play_win, fg_color="transparent")
    frame_answers.pack(fill="both", expand=True, padx=40, pady=10)
    
    frame_answers.grid_columnconfigure((0, 1), weight=1)
    frame_answers.grid_rowconfigure((0, 1), weight=1)

    def mark_word_studied(word):
        today_str = datetime.now().strftime("%Y-%m-%d")
        if today_str not in daily_study_tracker:
            daily_study_tracker[today_str] = []
        if word not in daily_study_tracker[today_str]:
            vocab_data[word]["study_count"] += 1
            daily_study_tracker[today_str].append(word)
        
        vocab_data[word]["last_studied"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        save_data(data_json)
        update_word_list() 

    def check_answer(selected_word, correct_word, btn_clicked):
        nonlocal score, current_q_idx
        for b in buttons: b.configure(state="disabled")

        if selected_word == correct_word:
            btn_clicked.configure(fg_color="#27ae60", border_color="#27ae60") 
            score += 1
            mark_word_studied(correct_word)
        else:
            btn_clicked.configure(fg_color="#e74c3c", border_color="#e74c3c") 
            for b in buttons:
                if b.cget("text") == correct_word:
                    b.configure(fg_color="#27ae60")

        current_q_idx += 1
        play_win.after(1200, load_question)

    def load_question():
        if current_q_idx >= quantity:
            for widget in play_win.winfo_children(): widget.destroy()
            ctk.CTkLabel(play_win, text="🎉 HOÀN THÀNH!", font=("Segoe UI", 40, "bold"), text_color="#f1c40f").pack(pady=(100, 20))
            ctk.CTkLabel(play_win, text=f"Điểm số: {score} / {quantity}", font=("Segoe UI", 24)).pack(pady=10)
            ctk.CTkButton(play_win, text="Đóng", command=play_win.destroy, height=45, font=FONT_BODY).pack(pady=30)
            return

        for b in buttons: b.destroy()
        buttons.clear()

        correct_word = target_words[current_q_idx]
        sentence = vocab_data[correct_word].get("sentence", "I need to remember the word ___.")
        
        display_sentence = re.sub(re.escape(correct_word), "___", sentence, flags=re.IGNORECASE)
        if "___" not in display_sentence:
            display_sentence = f"Từ nào phù hợp?\n'{sentence}'"
        
        lbl_progress.configure(text=f"Tiến độ: Câu {current_q_idx + 1} / {quantity}")
        lbl_question.configure(text=f'"{display_sentence}"')

        wrong_choices = [w for w in all_words_list if w != correct_word]
        choices = [correct_word] + random.sample(wrong_choices, min(3, len(wrong_choices)))
        random.shuffle(choices)

        for i, choice in enumerate(choices):
            row = i // 2
            col = i % 2
            btn = ctk.CTkButton(
                frame_answers, text=choice, font=("Segoe UI", 18, "bold"), 
                height=60, corner_radius=15, fg_color=("gray85", "gray25"), 
                text_color=("black", "white"), hover_color="#3498db", border_width=2, border_color=("gray70", "gray40"),
            )
            btn.configure(command=lambda c=choice, w=correct_word, b=btn: check_answer(c, w, b))
            btn.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
            buttons.append(btn)

    load_question()


# --- 5. CÁC HÀM XỬ LÝ SỰ KIỆN CHÍNH ---
def on_add_word():
    word = entry_word.get().strip().lower()
    if not word: return
    
    if spell.unknown([word]):
        corrected = spell.correction(word)
        if corrected and corrected != word:
            msg = f"'{word}' sai chính tả.\nÝ bạn là '{corrected}'?\n\n(YES để sửa. NO để hủy)"
            if messagebox.askyesno("Sai chính tả?", msg): word = corrected
            else: return 
    
    entry_word.delete(0, 'end')
    btn_add.configure(text="...", state="disabled")
    app.update_idletasks()
    
    if word not in vocab_data:
        sentence, pos = get_word_info(word)
        today = datetime.now().strftime("%Y-%m-%d %H:%M")
        vocab_data[word] = {
            "sentence": sentence, "pos": pos,
            "last_studied": today, "custom_sentence": "", "study_count": 0
        }
        save_data(data_json)
    
    btn_add.configure(text="Thêm", state="normal")
    update_word_list()
    show_word_detail(word)

def show_word_detail(word):
    global current_word
    current_word = word
    data = vocab_data[word]
    today_str = datetime.now().strftime("%Y-%m-%d")

    if today_str not in daily_study_tracker: daily_study_tracker[today_str] = []
    if word not in daily_study_tracker[today_str]:
        data["study_count"] += 1
        daily_study_tracker[today_str].append(word)
    
    data["last_studied"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    save_data(data_json)
    update_word_list()

    frame_welcome.pack_forget()
    frame_detail_inner.pack(fill="both", expand=True, padx=20, pady=20)
    
    lbl_word_title.configure(text=word.capitalize())
    lbl_pos.configure(text=data.get('pos', 'Chưa rõ'))
    lbl_auto_sentence.configure(text=f'"{data["sentence"]}"')
    
    count = data['study_count']
    color_count = "#e74c3c" if count < 5 else ("#f39c12" if count < 10 else "#27ae60")
    lbl_count_val.configure(text=f"{count} lần", text_color=color_count)
    lbl_date_val.configure(text=data['last_studied'])
    
    txt_custom_sentence.delete("1.0", "end")
    txt_custom_sentence.insert("1.0", data.get("custom_sentence", ""))

    app.update_idletasks() 
    load_image_async(word)
    read_text_async(word)

def save_custom_sentence():
    if current_word:
        vocab_data[current_word]["custom_sentence"] = txt_custom_sentence.get("1.0", "end-1c")
        save_data(data_json)
        btn_save_custom.configure(fg_color="#2ecc71", text="✔ Đã lưu")
        app.after(1500, lambda: btn_save_custom.configure(fg_color="#2980b9", text="Lưu Ghi Chú"))

def on_delete_word():
    if current_word:
        if messagebox.askyesno("Cảnh báo", f"Xóa '{current_word}'?"):
            del vocab_data[current_word]
            for date, w_list in daily_study_tracker.items():
                if current_word in w_list: w_list.remove(current_word)
            save_data(data_json)
            update_word_list()
            clear_details()

def update_word_list(*args):
    for widget in scroll_list.winfo_children(): widget.destroy()
    
    items = list(vocab_data.items())
    sort_type = sort_var.get()
    if "Tên" in sort_type: items.sort(key=lambda x: x[0])
    elif "Ngày" in sort_type: items.sort(key=lambda x: datetime.strptime(x[1].get("last_studied", "2000-01-01 00:00"), "%Y-%m-%d %H:%M"))
    elif "Số lần" in sort_type: items.sort(key=lambda x: x[1].get("study_count", 0))
    
    for word, info in items:
        is_warning = check_warning(info)
        count = info.get("study_count", 0)
        
        display_text = f"⚠  {word}" if is_warning else f"    {word}"
        text_color = "#e74c3c" if is_warning else ("gray10", "gray90")
        
        btn = ctk.CTkButton(
            scroll_list, text=display_text, anchor="w", fg_color="transparent", 
            text_color=text_color, font=("Segoe UI", 16, "bold" if is_warning else "normal"),
            hover_color=("gray85", "gray25"), height=40, corner_radius=8,
            command=lambda w=word: show_word_detail(w)
        )
        btn.pack(fill="x", pady=2, padx=5)

def clear_details():
    global current_word
    current_word = None
    frame_detail_inner.pack_forget()
    frame_welcome.pack(fill="both", expand=True)

# ==========================================
# 6. BỐ CỤC UI
# ==========================================
app = ctk.CTk()
app.title("Vocab Master")
app.geometry("1100x750")

app.grid_columnconfigure(1, weight=1)
app.grid_rowconfigure(0, weight=1)

frame_sidebar = ctk.CTkFrame(app, width=320, corner_radius=0, fg_color=("gray95", "gray13"))
frame_sidebar.grid(row=0, column=0, sticky="nsew")

lbl_app_name = ctk.CTkLabel(frame_sidebar, text="⚡ Vocab Master", font=("Segoe UI", 26, "bold"), text_color=("#2980b9", "#3498db"))
lbl_app_name.pack(pady=(35, 10), padx=20, anchor="w")

btn_open_game = ctk.CTkButton(frame_sidebar, text="🎮 CHƠI GAME ÔN TẬP", font=("Segoe UI", 14, "bold"), height=45, fg_color="#e67e22", hover_color="#d35400", command=open_game_setup)
btn_open_game.pack(fill="x", padx=20, pady=(0, 20))

frame_add = ctk.CTkFrame(frame_sidebar, fg_color="transparent")
frame_add.pack(fill="x", padx=20, pady=5)

entry_word = ctk.CTkEntry(frame_add, placeholder_text="Nhập từ...", height=45, font=FONT_BODY, corner_radius=10, border_width=1)
entry_word.pack(side="left", fill="x", expand=True, padx=(0, 10))
app.bind('<Return>', lambda event: on_add_word())

btn_add = ctk.CTkButton(frame_add, text="Thêm", command=on_add_word, width=70, height=45, font=("Segoe UI", 14, "bold"), corner_radius=10)
btn_add.pack(side="right")

sort_var = ctk.StringVar(value="Sắp xếp: Ngày học")
sort_menu = ctk.CTkOptionMenu(
    frame_sidebar, variable=sort_var, 
    values=["Sắp xếp: Ngày học", "Sắp xếp: Tên (A-Z)", "Sắp xếp: Số lần học"],
    command=update_word_list, height=40, font=FONT_BODY, corner_radius=10,
    fg_color=("gray90", "gray20"), text_color=("gray10", "gray90"), button_color=("gray85", "gray25")
)
sort_menu.pack(pady=(15, 10), padx=20, fill="x")

scroll_list = ctk.CTkScrollableFrame(frame_sidebar, fg_color="transparent")
scroll_list.pack(fill="both", expand=True, padx=10, pady=(0, 10))

frame_main = ctk.CTkFrame(app, corner_radius=0, fg_color=("gray100", "gray8"))
frame_main.grid(row=0, column=1, sticky="nsew")

frame_welcome = ctk.CTkFrame(frame_main, fg_color="transparent")
frame_welcome.pack(fill="both", expand=True)
ctk.CTkLabel(frame_welcome, text="📖", font=("Segoe UI", 80)).pack(pady=(200, 10))
ctk.CTkLabel(frame_welcome, text="Chọn một từ vựng để bắt đầu học", font=FONT_SUBHEADING, text_color="gray").pack()

frame_detail_inner = ctk.CTkScrollableFrame(frame_main, fg_color="transparent")

card_header = ctk.CTkFrame(frame_detail_inner, fg_color=("gray95", "gray13"), corner_radius=20)
card_header.pack(fill="x", pady=(0, 20))

frame_header_top = ctk.CTkFrame(card_header, fg_color="transparent")
frame_header_top.pack(fill="x", padx=30, pady=(25, 5))

lbl_word_title = ctk.CTkLabel(frame_header_top, text="Word", font=FONT_HEADING)
lbl_word_title.pack(side="left")

lbl_pos = ctk.CTkLabel(frame_header_top, text="Từ loại", font=("Segoe UI", 16, "italic"), text_color="gray", fg_color=("gray85", "gray25"), corner_radius=10, padx=15, pady=5)
lbl_pos.pack(side="left", padx=20, pady=5)

btn_read = ctk.CTkButton(card_header, text="🔊 Nghe", command=lambda: read_text_async(current_word), height=45, font=("Segoe UI", 15, "bold"), fg_color="#8e44ad", hover_color="#9b59b6", corner_radius=25)
btn_read.pack(anchor="w", padx=30, pady=(0, 25))

frame_middle = ctk.CTkFrame(frame_detail_inner, fg_color="transparent")
frame_middle.pack(fill="x", pady=10)

card_image = ctk.CTkFrame(frame_middle, fg_color=("gray95", "gray13"), corner_radius=20)
card_image.pack(side="left", padx=(0, 20))
lbl_image = ctk.CTkLabel(card_image, text="", width=180, height=180, corner_radius=20)
lbl_image.pack(padx=10, pady=10)

card_stats = ctk.CTkFrame(frame_middle, fg_color=("gray95", "gray13"), corner_radius=20)
card_stats.pack(side="left", fill="both", expand=True)

card_stats.grid_columnconfigure(1, weight=1)

ctk.CTkLabel(card_stats, text="Trạng thái:", font=("Segoe UI", 14), text_color="gray").grid(row=0, column=0, sticky="w", padx=25, pady=(25, 5))
lbl_count_val = ctk.CTkLabel(card_stats, text="0 lần", font=("Segoe UI", 18, "bold"))
lbl_count_val.grid(row=0, column=1, sticky="w", pady=(25, 5))

ctk.CTkLabel(card_stats, text="Học gần nhất:", font=("Segoe UI", 14), text_color="gray").grid(row=1, column=0, sticky="w", padx=25, pady=5)
lbl_date_val = ctk.CTkLabel(card_stats, text="YYYY-MM-DD", font=("Segoe UI", 16))
lbl_date_val.grid(row=1, column=1, sticky="w", pady=5)

frame_ex = ctk.CTkFrame(card_stats, fg_color="transparent")
frame_ex.grid(row=2, column=0, columnspan=2, sticky="ew", padx=25, pady=(15, 25))

lbl_auto_sentence = ctk.CTkLabel(frame_ex, text='"Ví dụ"', font=FONT_ITALIC, wraplength=350, justify="left", text_color=("#2c3e50", "#ecf0f1"))
lbl_auto_sentence.pack(side="left", expand=True, fill="x")

btn_read_sentence = ctk.CTkButton(frame_ex, text="▶", width=40, height=40, corner_radius=20, command=lambda: read_text_async(vocab_data[current_word].get("sentence", "")), fg_color=("gray80", "gray30"), text_color=("black", "white"), hover_color=("#3498db", "#2980b9"))
btn_read_sentence.pack(side="right", padx=(15, 0))

card_notes = ctk.CTkFrame(frame_detail_inner, fg_color=("gray95", "gray13"), corner_radius=20)
card_notes.pack(fill="x", pady=30)

ctk.CTkLabel(card_notes, text="📝 Ghi chú", font=FONT_SUBHEADING).pack(anchor="w", padx=30, pady=(25, 10))

txt_custom_sentence = ctk.CTkTextbox(card_notes, height=120, font=FONT_BODY, corner_radius=15, border_width=1, border_color=("gray85", "gray25"), fg_color=("white", "gray10"))
txt_custom_sentence.pack(fill="x", padx=30, pady=(0, 20))

frame_actions = ctk.CTkFrame(card_notes, fg_color="transparent")
frame_actions.pack(fill="x", padx=30, pady=(0, 25))

btn_save_custom = ctk.CTkButton(frame_actions, text="Lưu", command=save_custom_sentence, font=("Segoe UI", 15, "bold"), height=45, corner_radius=10, fg_color="#2980b9", hover_color="#3498db")
btn_save_custom.pack(side="left")

btn_delete = ctk.CTkButton(frame_actions, text="Xóa", command=on_delete_word, font=("Segoe UI", 14), height=45, corner_radius=10, fg_color="transparent", border_color="#e74c3c", border_width=1.5, text_color="#e74c3c", hover_color="#fadbd8")
btn_delete.pack(side="right")

update_word_list()
app.mainloop()