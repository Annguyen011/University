import tkinter as tk
from tkinter import ttk
import random

# ===================== CÁC MINIGAME (AUTO-PLAY) =====================
class MiniGame:
    def __init__(self, canvas, width, height):
        self.canvas = canvas
        self.width = width
        self.height = height
        self.active = False
        self.after_id = None

    def start(self):
        self.active = True
        self.update()

    def stop(self):
        self.active = False
        if self.after_id:
            self.canvas.after_cancel(self.after_id)
            self.after_id = None

    def update(self):
        raise NotImplementedError

# --- Game 1: Chú mèo học bài chạy qua sách (Dino style) ---
class CatBookRunner(MiniGame):
    def __init__(self, canvas, width, height):
        super().__init__(canvas, width, height)
        self.ground_y = height - 30
        self.cat = {"x": 50, "y": self.ground_y - 40, "w": 32, "h": 40, "vy": 0, "jumping": False}
        self.obstacles = []
        self.speed = 4
        self.spawn_timer = 0
        self.spawn_delay = 70
        self.frame = 0
        self.score = 0

    def start(self):
        self.cat["y"] = self.ground_y - self.cat["h"]
        self.cat["vy"] = 0
        self.cat["jumping"] = False
        self.obstacles.clear()
        self.speed = 4
        self.spawn_timer = 0
        self.score = 0
        super().start()

    def update(self):
        if not self.active:
            return
        self.canvas.delete("all")
        # Nền
        self.canvas.create_rectangle(0, 0, self.width, self.height, fill="#E8F4FD", outline="")
        self.canvas.create_line(0, self.ground_y, self.width, self.ground_y, fill="#B0C4DE", width=2)
        # Mây
        self.canvas.create_oval(80, 15, 130, 40, fill="white", outline="")
        self.canvas.create_oval(300, 10, 340, 35, fill="white", outline="")

        # Sinh & di chuyển chướng ngại
        self.spawn_timer += 1
        if self.spawn_timer >= self.spawn_delay:
            self.spawn_obstacle()
            self.spawn_timer = 0
            self.speed = min(9, self.speed + 0.05)

        for obs in self.obstacles[:]:
            obs["x"] -= self.speed
            if obs["x"] + obs["w"] < 0:
                self.obstacles.remove(obs)
                self.score += 1

        # Nhảy
        if self.cat["jumping"]:
            self.cat["vy"] += 0.6
            self.cat["y"] += self.cat["vy"]
            if self.cat["y"] >= self.ground_y - self.cat["h"]:
                self.cat["y"] = self.ground_y - self.cat["h"]
                self.cat["vy"] = 0
                self.cat["jumping"] = False

        # Tự động nhảy
        if not self.cat["jumping"]:
            for obs in self.obstacles:
                dist = obs["x"] - (self.cat["x"] + self.cat["w"])
                if 0 < dist < 60:
                    self.cat["vy"] = -10
                    self.cat["jumping"] = True
                    break

        # Va chạm
        cat_bbox = (self.cat["x"], self.cat["y"], self.cat["x"]+self.cat["w"], self.cat["y"]+self.cat["h"])
        for obs in self.obstacles:
            obs_bbox = (obs["x"], obs["y"], obs["x"]+obs["w"], obs["y"]+obs["h"])
            if self.rect_collide(cat_bbox, obs_bbox):
                self.game_over()
                return

        # Vẽ mèo
        self.draw_cat()
        # Vẽ chướng ngại (sách vui nhộn)
        self.draw_obstacles()
        # Điểm
        self.canvas.create_text(self.width-70, 15, text=f"⭐ {self.score}",
                                font=("Arial", 12, "bold"), fill="#FF8C00")
        self.after_id = self.canvas.after(20, self.update)

    def spawn_obstacle(self):
        types = ["closed", "open", "tall"]
        if types[0] == "closed":
            w, h = 18, 35
        elif types[1] == "open":
            w, h = 38, 24
        else:
            w, h = 14, 45
        self.obstacles.append({"x": self.width, "y": self.ground_y - h,
                               "w": w, "h": h, "type": random.choice(types)})

    def draw_cat(self):
        x, y, w, h = self.cat["x"], self.cat["y"], self.cat["w"], self.cat["h"]
        # Thân mèo (cam)
        self.canvas.create_oval(x, y+10, x+w, y+h, fill="#FFA500", outline="#FF8C00", width=2)
        # Đầu
        self.canvas.create_oval(x-2, y, x+w-4, y+20, fill="#FFA500", outline="#FF8C00", width=2)
        # Tai
        self.canvas.create_polygon(x, y+2, x+6, y-8, x+12, y+2, fill="#FFA500", outline="#FF8C00")
        self.canvas.create_polygon(x+14, y+2, x+20, y-8, x+26, y+2, fill="#FFA500", outline="#FF8C00")
        # Mắt
        self.canvas.create_oval(x+6, y+8, x+12, y+14, fill="white")
        self.canvas.create_oval(x+16, y+8, x+22, y+14, fill="white")
        self.canvas.create_oval(x+9, y+10, x+11, y+12, fill="black")
        self.canvas.create_oval(x+19, y+10, x+21, y+12, fill="black")
        # Râu
        self.canvas.create_line(x-2, y+12, x+4, y+12, fill="#333", width=1)
        self.canvas.create_line(x-2, y+16, x+4, y+16, fill="#333", width=1)
        self.canvas.create_line(x+26, y+12, x+30, y+12, fill="#333", width=1)
        self.canvas.create_line(x+26, y+16, x+30, y+16, fill="#333", width=1)
        # Mũi
        self.canvas.create_oval(x+12, y+14, x+14, y+16, fill="pink")
        # Chân
        if not self.cat["jumping"]:
            self.frame = (self.frame + 1) % 2
            if self.frame == 0:
                self.canvas.create_line(x+8, y+h, x+4, y+h+12, fill="#FF8C00", width=3)
                self.canvas.create_line(x+20, y+h, x+24, y+h+8, fill="#FF8C00", width=3)
            else:
                self.canvas.create_line(x+8, y+h, x+12, y+h+8, fill="#FF8C00", width=3)
                self.canvas.create_line(x+20, y+h, x+16, y+h+12, fill="#FF8C00", width=3)
        else:
            self.canvas.create_line(x+10, y+h, x+14, y+h+5, fill="#FF8C00", width=2)
            self.canvas.create_line(x+18, y+h, x+14, y+h+5, fill="#FF8C00", width=2)

    def draw_obstacles(self):
        for obs in self.obstacles:
            x, y, w, h = obs["x"], obs["y"], obs["w"], obs["h"]
            if obs["type"] == "closed":
                self.canvas.create_rectangle(x, y, x+w, y+h, fill="#D2691E", outline="#8B4513", width=2)
                self.canvas.create_text(x+w/2, y+h/2, text="📕", font=("Arial", h//2), anchor="center")
            elif obs["type"] == "open":
                self.canvas.create_polygon(x, y+h//2, x+12, y, x+w, y, x+w-12, y+h//2,
                                         fill="#B8860B", outline="#8B6508", width=2)
                self.canvas.create_text(x+w/2, y+h//2-2, text="📖", font=("Arial", h//2), anchor="center")
            else:  # tall
                self.canvas.create_rectangle(x, y, x+w, y+h, fill="#4682B4", outline="#2F4F4F", width=2)
                self.canvas.create_text(x+w/2, y+h/2, text="📚", font=("Arial", h//2), anchor="center")

    def game_over(self):
        self.active = False
        if self.after_id:
            self.canvas.after_cancel(self.after_id)
        self.canvas.create_text(self.width/2, self.height/2-15, text="😿 Ú òa!",
                                font=("Arial", 16, "bold"), fill="#DC143C")
        self.canvas.create_text(self.width/2, self.height/2+15, text="Tự chạy lại sau 2s...",
                                font=("Arial", 10), fill="#555")
        self.canvas.after(2000, self.start)

    def rect_collide(self, r1, r2):
        return (r1[0] < r2[2] and r1[2] > r2[0] and r1[1] < r2[3] and r1[3] > r2[1])

# --- Game 2: Những quyển sách bay (thư giãn) ---
class FloatingBooksGame(MiniGame):
    def __init__(self, canvas, width, height):
        super().__init__(canvas, width, height)
        self.books = []

    def start(self):
        self.books = []
        for _ in range(8):
            self.books.append(self.new_book(random.randint(0, self.width), random.randint(0, self.height)))
        super().start()

    def new_book(self, x, y):
        return {
            "x": x, "y": y,
            "vx": random.uniform(-0.8, 0.8),
            "vy": random.uniform(-1.0, -0.3),
            "size": random.randint(14, 22),
            "color": random.choice(["#FF6347", "#3CB371", "#6A5ACD", "#FF8C00", "#20B2AA"]),
            "rotation": random.uniform(-20, 20)
        }

    def update(self):
        if not self.active:
            return
        self.canvas.delete("all")
        self.canvas.create_rectangle(0, 0, self.width, self.height, fill="#FFF5E1", outline="")
        # Vẽ vài ngôi sao nhỏ
        for _ in range(10):
            sx = random.randint(0, self.width)
            sy = random.randint(0, self.height)
            self.canvas.create_oval(sx, sy, sx+3, sy+3, fill="#FFD700", outline="")

        for book in self.books:
            book["x"] += book["vx"]
            book["y"] += book["vy"]
            # Bọc lại khi ra khỏi khung
            if book["x"] < -30:
                book["x"] = self.width + 30
            if book["x"] > self.width + 30:
                book["x"] = -30
            if book["y"] < -30:
                book["y"] = self.height + 30
            if book["y"] > self.height + 30:
                book["y"] = -30
            book["rotation"] += random.uniform(-1, 1)

            # Vẽ quyển sách nhỏ với emoji
            self.canvas.create_text(book["x"], book["y"],
                                    text="📘" if random.random()>0.5 else "📗",
                                    font=("Arial", book["size"]), angle=book["rotation"])

        self.after_id = self.canvas.after(40, self.update)

# --- Game 3: Cốc cà phê nhảy múa (vui mắt) ---
class DancingCupGame(MiniGame):
    def __init__(self, canvas, width, height):
        super().__init__(canvas, width, height)
        self.cup_x = width//2
        self.cup_y = 60
        self.vy = 2
        self.vx = 3
        self.angle = 0

    def start(self):
        self.cup_x = self.width//2
        self.cup_y = 60
        self.vy = 2
        self.vx = 3
        self.angle = 0
        super().start()

    def update(self):
        if not self.active:
            return
        self.canvas.delete("all")
        self.canvas.create_rectangle(0, 0, self.width, self.height, fill="#FDF5E6", outline="")
        # Nền hạt cà phê
        for _ in range(6):
            bx = random.randint(0, self.width)
            by = random.randint(0, self.height)
            self.canvas.create_text(bx, by, text="☕", font=("Arial", 10), fill="#D2B48C")

        self.cup_x += self.vx
        self.cup_y += self.vy
        self.vy += 0.25  # trọng lực nhẹ
        # Bounce
        if self.cup_y + 25 >= self.height:
            self.cup_y = self.height - 25
            self.vy = -abs(self.vy) * 0.8
        if self.cup_x - 20 <= 0:
            self.cup_x = 20
            self.vx = abs(self.vx) * 0.9
        elif self.cup_x + 20 >= self.width:
            self.cup_x = self.width - 20
            self.vx = -abs(self.vx) * 0.9

        self.angle += 5
        # Vẽ cốc cà phê xoay
        self.canvas.create_text(self.cup_x, self.cup_y, text="☕", font=("Arial", 30),
                                angle=self.angle, fill="#6F4E37")
        self.canvas.create_text(self.width-50, 15, text="☕ Nhảy điệu",
                                font=("Arial", 9, "italic"), fill="#8B4513")
        self.after_id = self.canvas.after(25, self.update)

# =========================== ỨNG DỤNG ĐỒNG HỒ HỌC TẬP ===========================
class StudyTimer:
    def __init__(self, root):
        self.root = root
        self.root.title("⏳ Study Timer - Pomodoro & Mini Games")
        self.root.geometry("760x480")  # cửa sổ rộng hơn để chứa game bên phải
        self.root.configure(bg="#1E1E2E")
        self.root.resizable(False, False)

        # Biến trạng thái
        self.study_time = 25 * 60
        self.short_break = 5 * 60
        self.long_break = 15 * 60
        self.current_time_left = self.study_time
        self.is_running = False
        self.is_paused = False
        self.is_study = True
        self.pomodoro_count = 0
        self.after_id = None

        # Màu sắc
        self.bg_color = "#1E1E2E"
        self.frame_bg = "#2A2A3E"
        self.green_accent = "#4ECDC4"
        self.red_accent = "#FF6B6B"
        self.text_color = "#FFFFFF"
        self.sub_color = "#B0B0C0"

        self.current_game = None
        self.game_map = {}

        self.build_ui()
        self.switch_game("cat_book_runner")  # game mặc định
        self.update_timer_display()

    def build_ui(self):
        # --- Khung trái (đồng hồ + điều khiển) ---
        left_frame = tk.Frame(self.root, bg=self.bg_color, width=380, height=480)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(15,0), pady=15)
        left_frame.pack_propagate(False)

        # Header
        tk.Label(left_frame, text="⏳ STUDY TIMER", font=("Helvetica", 18, "bold"),
                 fg=self.text_color, bg=self.bg_color).pack(pady=(10,0))
        tk.Label(left_frame, text="Pomodoro Technique", font=("Helvetica", 9),
                 fg=self.sub_color, bg=self.bg_color).pack()

        # Canvas đồng hồ tròn
        canvas_frame = tk.Frame(left_frame, bg=self.bg_color)
        canvas_frame.pack(pady=5)
        self.canvas = tk.Canvas(canvas_frame, width=220, height=220,
                                bg=self.bg_color, highlightthickness=0)
        self.canvas.pack()
        self.canvas.create_oval(20, 20, 200, 200, outline="#3A3A52", width=14)
        self.progress_arc = self.canvas.create_arc(20, 20, 200, 200,
                                                   start=90, extent=0,
                                                   outline=self.green_accent,
                                                   width=14, style=tk.ARC)
        self.timer_text = self.canvas.create_text(110, 90, text="25:00",
                                                  font=("Helvetica", 30, "bold"),
                                                  fill=self.text_color)
        self.status_text = self.canvas.create_text(110, 130, text="HỌC TẬP",
                                                   font=("Helvetica", 10, "bold"),
                                                   fill=self.green_accent)
        self.count_text = self.canvas.create_text(110, 155, text="🍅 x 0",
                                                  font=("Helvetica", 10),
                                                  fill=self.sub_color)

        # Dòng thông báo (không pop-up)
        self.notif_label = tk.Label(left_frame, text="", font=("Helvetica", 9, "italic"),
                                    fg="#FFD700", bg=self.bg_color, wraplength=340)
        self.notif_label.pack(pady=2)

        # Nút điều khiển
        btn_frame = tk.Frame(left_frame, bg=self.bg_color)
        btn_frame.pack(pady=8)
        self.start_pause_btn = tk.Button(btn_frame, text="▶ BẮT ĐẦU",
                                         font=("Helvetica", 11, "bold"),
                                         bg=self.green_accent, fg="#1E1E2E",
                                         activebackground="#3DBDB5",
                                         relief=tk.FLAT, bd=0,
                                         padx=18, pady=6, cursor="hand2",
                                         command=self.start_pause)
        self.start_pause_btn.grid(row=0, column=0, padx=5)
        self.reset_btn = tk.Button(btn_frame, text="↺ ĐẶT LẠI",
                                   font=("Helvetica", 11, "bold"),
                                   bg="#5A5A7A", fg=self.text_color,
                                   activebackground="#4A4A6A",
                                   relief=tk.FLAT, bd=0,
                                   padx=14, pady=6, cursor="hand2",
                                   command=self.reset)
        self.reset_btn.grid(row=0, column=1, padx=5)
        self.skip_btn = tk.Button(btn_frame, text="⏭ BỎ QUA",
                                   font=("Helvetica", 11, "bold"),
                                   bg=self.red_accent, fg="#1E1E2E",
                                   activebackground="#E55A5A",
                                   relief=tk.FLAT, bd=0,
                                   padx=14, pady=6, cursor="hand2",
                                   command=self.skip)
        self.skip_btn.grid(row=0, column=2, padx=5)

        # Frame tùy chỉnh thời gian
        setting_frame = tk.Frame(left_frame, bg=self.frame_bg,
                                 highlightbackground="#3A3A52",
                                 highlightthickness=1)
        setting_frame.pack(pady=8, ipadx=10, ipady=5, fill=tk.X, padx=10)
        tk.Label(setting_frame, text="⚙️ THỜI GIAN (phút)", font=("Helvetica", 9, "bold"),
                 fg=self.text_color, bg=self.frame_bg).pack(pady=(4,5))

        fields = [("📚 Học:", "study", 25), ("☕ Nghỉ ngắn:", "short_break", 5),
                  ("😴 Nghỉ dài:", "long_break", 15)]
        for label_text, attr, default in fields:
            row = tk.Frame(setting_frame, bg=self.frame_bg)
            row.pack(pady=2)
            tk.Label(row, text=label_text, font=("Helvetica", 9),
                     fg=self.sub_color, bg=self.frame_bg, width=14, anchor="w").pack(side=tk.LEFT)
            entry = tk.Entry(row, font=("Helvetica", 10), bg="#3A3A52", fg=self.text_color,
                             insertbackground=self.text_color, relief=tk.FLAT, width=5,
                             justify=tk.CENTER)
            entry.insert(0, str(default))
            entry.pack(side=tk.LEFT, padx=4)
            setattr(self, f"{attr}_entry", entry)

        self.apply_btn = tk.Button(setting_frame, text="✓ ÁP DỤNG",
                                   font=("Helvetica", 9, "bold"),
                                   bg=self.green_accent, fg="#1E1E2E",
                                   activebackground="#3DBDB5",
                                   relief=tk.FLAT, bd=0,
                                   padx=12, pady=4, cursor="hand2",
                                   command=self.apply_settings)
        self.apply_btn.pack(pady=(6, 4))

        # --- Khung phải (game) ---
        right_frame = tk.Frame(self.root, bg="#2A2A3E", width=340, height=480)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10,10), pady=10)
        right_frame.pack_propagate(False)

        tk.Label(right_frame, text="🎮 MINI GAME", font=("Helvetica", 12, "bold"),
                 fg=self.text_color, bg="#2A2A3E").pack(pady=(8,2))

        # Combobox chọn game
        game_select = tk.Frame(right_frame, bg="#2A2A3E")
        game_select.pack(pady=2)
        tk.Label(game_select, text="Chọn game:", font=("Helvetica", 9),
                 fg=self.sub_color, bg="#2A2A3E").pack(side=tk.LEFT, padx=5)
        self.game_var = tk.StringVar(value="cat_book_runner")
        game_combo = ttk.Combobox(game_select, textvariable=self.game_var,
                                  state="readonly", width=16, font=("Helvetica", 9))
        game_combo['values'] = ("cat_book_runner", "floating_books", "dancing_cup")
        game_combo.current(0)
        game_combo.pack(side=tk.LEFT, padx=5)
        game_combo.bind("<<ComboboxSelected>>", lambda e: self.switch_game(self.game_var.get()))

        # Canvas game
        self.game_canvas = tk.Canvas(right_frame, width=300, height=200,
                                     bg="#F5F5DC", highlightbackground="#4ECDC4",
                                     highlightthickness=2)
        self.game_canvas.pack(pady=10, padx=10)

        # Thêm chú thích
        tk.Label(right_frame, text="Game tự chơi để bạn thư giãn 👀",
                 font=("Helvetica", 8, "italic"), fg="#B0B0C0", bg="#2A2A3E").pack(pady=2)

    def init_game(self, game_key):
        if self.current_game:
            self.current_game.stop()
        w, h = 300, 200
        if game_key == "cat_book_runner":
            game = CatBookRunner(self.game_canvas, w, h)
        elif game_key == "floating_books":
            game = FloatingBooksGame(self.game_canvas, w, h)
        elif game_key == "dancing_cup":
            game = DancingCupGame(self.game_canvas, w, h)
        else:
            return
        self.game_map[game_key] = game
        self.current_game = game
        if self.is_running and not self.is_paused and self.is_study:
            self.current_game.start()
        else:
            self.current_game.stop()

    def switch_game(self, game_key):
        self.init_game(game_key)

    # ================== ĐỒNG HỒ & VÒNG TRÒN ==================
    def draw_progress(self):
        total = self.study_time if self.is_study else self.short_break
        extent = 360 * (1 - self.current_time_left / total) if total > 0 else 0
        self.canvas.delete(self.progress_arc)
        color = self.green_accent if self.is_study else self.red_accent
        self.progress_arc = self.canvas.create_arc(20, 20, 200, 200,
                                                   start=90, extent=extent,
                                                   outline=color, width=14, style=tk.ARC)
        self.canvas.create_oval(20, 20, 200, 200, outline="#2A2A3E", width=14)

    def update_timer_display(self):
        mins, secs = divmod(self.current_time_left, 60)
        self.canvas.itemconfig(self.timer_text, text=f"{mins:02d}:{secs:02d}")
        status = "HỌC TẬP" if self.is_study else "NGHỈ NGƠI"
        color = self.green_accent if self.is_study else self.red_accent
        self.canvas.itemconfig(self.status_text, text=status, fill=color)
        self.canvas.itemconfig(self.count_text, text=f"🍅 x {self.pomodoro_count}")
        self.draw_progress()

    def countdown(self):
        if self.is_running and not self.is_paused and self.current_time_left > 0:
            self.current_time_left -= 1
            self.update_timer_display()
            self.after_id = self.root.after(1000, self.countdown)
        elif self.current_time_left == 0:
            self.timer_finished()

    def timer_finished(self):
        self.is_running = False
        self.start_pause_btn.config(text="▶ BẮT ĐẦU", bg=self.green_accent)
        if self.current_game:
            self.current_game.stop()

        if self.is_study:
            self.pomodoro_count += 1
            self.update_timer_display()
            if self.pomodoro_count % 4 == 0:
                self.current_time_left = self.long_break
                msg = "🎉 4 Pomodoro! Nghỉ dài 15 phút."
            else:
                self.current_time_left = self.short_break
                msg = "✅ Hoàn thành 1 Pomodoro! Nghỉ ngắn 5 phút."
            self.is_study = False
        else:
            self.current_time_left = self.study_time
            self.is_study = True
            msg = "📚 Hết giờ nghỉ! Học tiếp nào!"

        self.show_notification(msg)
        self.update_timer_display()

    def show_notification(self, message):
        self.notif_label.config(text=message)
        self.root.after(4000, lambda: self.notif_label.config(text=""))

    # ================== ĐIỀU KHIỂN ==================
    def start_pause(self):
        if not self.is_running:
            self.is_running = True
            self.is_paused = False
            self.start_pause_btn.config(text="⏸ TẠM DỪNG", bg=self.red_accent)
            if self.is_study and self.current_game:
                self.current_game.start()
            self.countdown()
        elif self.is_running and not self.is_paused:
            self.is_paused = True
            self.start_pause_btn.config(text="▶ TIẾP TỤC", bg=self.green_accent)
            if self.after_id:
                self.root.after_cancel(self.after_id)
            if self.current_game:
                self.current_game.stop()
        elif self.is_running and self.is_paused:
            self.is_paused = False
            self.start_pause_btn.config(text="⏸ TẠM DỪNG", bg=self.red_accent)
            if self.is_study and self.current_game:
                self.current_game.start()
            self.countdown()

    def reset(self):
        if self.after_id:
            self.root.after_cancel(self.after_id)
        self.is_running = False
        self.is_paused = False
        self.is_study = True
        self.current_time_left = self.study_time
        self.start_pause_btn.config(text="▶ BẮT ĐẦU", bg=self.green_accent)
        if self.current_game:
            self.current_game.stop()
        self.update_timer_display()
        self.show_notification("↺ Đã đặt lại thời gian học")

    def skip(self):
        if self.after_id:
            self.root.after_cancel(self.after_id)
        self.is_running = False
        self.is_paused = False
        if self.is_study:
            self.current_time_left = self.short_break
            self.is_study = False
            msg = "⏩ Chuyển sang nghỉ ngắn."
        else:
            self.current_time_left = self.study_time
            self.is_study = True
            msg = "⏩ Quay lại học tập."
        self.start_pause_btn.config(text="▶ BẮT ĐẦU", bg=self.green_accent)
        if self.current_game:
            self.current_game.stop()
        self.update_timer_display()
        self.show_notification(msg)

    def apply_settings(self):
        try:
            study = int(self.study_entry.get())
            short = int(self.short_break_entry.get())
            long = int(self.long_break_entry.get())
            if study <= 0 or short <= 0 or long <= 0:
                raise ValueError
            self.study_time = study * 60
            self.short_break = short * 60
            self.long_break = long * 60
            if self.after_id:
                self.root.after_cancel(self.after_id)
            self.is_running = False
            self.is_paused = False
            self.is_study = True
            self.current_time_left = self.study_time
            self.start_pause_btn.config(text="▶ BẮT ĐẦU", bg=self.green_accent)
            if self.current_game:
                self.current_game.stop()
            self.update_timer_display()
            self.show_notification("✓ Đã áp dụng thời gian mới")
        except ValueError:
            self.show_notification("⚠️ Vui lòng nhập số phút hợp lệ")

# =========================== CHẠY ỨNG DỤNG ===========================
if __name__ == "__main__":
    root = tk.Tk()
    app = StudyTimer(root)
    root.mainloop()