import tkinter as tk
from tkinter import ttk
import random
import math
import time
import os
import sqlite3
from datetime import datetime
import sys
import customtkinter as ctk

import threading
try:
    import pystray
    from PIL import Image, ImageDraw
    HAS_SYSTRAY = True
except ImportError:
    HAS_SYSTRAY = False

# Xử lý âm thanh báo thức đa nền tảng
try:
    import winsound
    def play_beep():
        winsound.Beep(1000, 300)
except ImportError:
    def play_beep():
        print('\a')

# ===================== QUẢN LÝ DỮ LIỆU (SQLITE) =====================
class DBManager:
    def __init__(self):
        appdata_path = os.getenv('APPDATA')
        if not appdata_path:
            appdata_path = os.path.expanduser('~')
        self.app_dir = os.path.join(appdata_path, 'StudyTimerApp')
        if not os.path.exists(self.app_dir):
            os.makedirs(self.app_dir)
        self.db_path = os.path.join(self.app_dir, 'userdata.db')
        self.init_db()

    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS stats
                          (id INTEGER PRIMARY KEY,
                           total_sessions INTEGER,
                           streak INTEGER,
                           last_date TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS highscores
                          (game_name TEXT PRIMARY KEY, score INTEGER)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS aow_save_v3
                          (id INTEGER PRIMARY KEY,
                           r_hp REAL, r_mana REAL, r_age INTEGER, r_tower INTEGER, r_xp INTEGER,
                           b_hp REAL, b_mana REAL, b_age INTEGER, b_tower INTEGER, b_xp INTEGER)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS space_shooter_save
                          (id INTEGER PRIMARY KEY,
                           coins INTEGER, w_lvl INTEGER, f_lvl INTEGER, d_lvl INTEGER, s_lvl INTEGER)''')
        cursor.execute("SELECT * FROM stats WHERE id=1")
        if not cursor.fetchone():
            cursor.execute("INSERT INTO stats (id, total_sessions, streak, last_date) VALUES (1, 0, 0, '')")
        cursor.execute("SELECT * FROM aow_save_v3 WHERE id=1")
        if not cursor.fetchone():
            cursor.execute("INSERT INTO aow_save_v3 VALUES (1, 1000, 0, 1, 0, 0, 1000, 0, 1, 0, 0)")
        cursor.execute("SELECT * FROM space_shooter_save WHERE id=1")
        if not cursor.fetchone():
            cursor.execute("INSERT INTO space_shooter_save VALUES (1, 0, 1, 1, 0, 0)")
        conn.commit()
        conn.close()

    def get_stats(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT total_sessions, streak, last_date FROM stats WHERE id=1")
        res = cursor.fetchone()
        conn.close()
        return res if res else (0, 0, "")

    def update_session(self):
        total, streak, last_date_str = self.get_stats()
        today = datetime.now().date()
        if last_date_str:
            last_date = datetime.strptime(last_date_str, "%Y-%m-%d").date()
            delta = (today - last_date).days
            if delta == 1:
                streak += 1
            elif delta > 1:
                streak = 1
        else:
            streak = 1
        total += 1
        conn = sqlite3.connect(self.db_path)
        conn.cursor().execute("UPDATE stats SET total_sessions=?, streak=?, last_date=? WHERE id=1",
                              (total, streak, today.strftime("%Y-%m-%d")))
        conn.commit()
        conn.close()
        return streak, total

    def get_highscore(self, game_name):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT score FROM highscores WHERE game_name=?", (game_name,))
        res = cursor.fetchone()
        conn.close()
        return res[0] if res else 0

    def increment_score(self, game_name):
        new_val = self.get_highscore(game_name) + 1
        conn = sqlite3.connect(self.db_path)
        conn.cursor().execute("INSERT OR REPLACE INTO highscores (game_name, score) VALUES (?, ?)",
                              (game_name, new_val))
        conn.commit()
        conn.close()
        return new_val

    def get_aow_save(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT r_hp, r_mana, r_age, r_tower, r_xp, b_hp, b_mana, b_age, b_tower, b_xp FROM aow_save_v3 WHERE id=1")
        res = cursor.fetchone()
        conn.close()
        return res

    def save_aow_state(self, r_hp, r_mana, r_age, r_tower, r_xp, b_hp, b_mana, b_age, b_tower, b_xp):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''UPDATE aow_save_v3 SET 
                          r_hp=?, r_mana=?, r_age=?, r_tower=?, r_xp=?, 
                          b_hp=?, b_mana=?, b_age=?, b_tower=?, b_xp=? WHERE id=1''',
                       (r_hp, r_mana, r_age, r_tower, r_xp, b_hp, b_mana, b_age, b_tower, b_xp))
        conn.commit()
        conn.close()

    def get_space_shooter_save(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT coins, w_lvl, f_lvl, d_lvl, s_lvl FROM space_shooter_save WHERE id=1")
        res = cursor.fetchone()
        conn.close()
        return res

    def save_space_shooter_state(self, coins, w_lvl, f_lvl, d_lvl, s_lvl):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE space_shooter_save SET coins=?, w_lvl=?, f_lvl=?, d_lvl=?, s_lvl=? WHERE id=1",
                       (coins, w_lvl, f_lvl, d_lvl, s_lvl))
        conn.commit()
        conn.close()

# ===================== KHUNG MINIGAME =====================
class MiniGame:
    def __init__(self, canvas, width, height, app=None):
        self.canvas = canvas
        self.width = width
        self.height = height
        self.app = app
        self.active = False
        self.after_id = None

    def start(self):
        self.reset()
        self.active = True
        self.update()

    def stop(self):
        self.active = False
        if self.after_id:
            self.canvas.after_cancel(self.after_id)
            self.after_id = None

    def pause(self):
        self.stop()

    def resume(self):
        if not self.active:
            self.active = True
            self.update()

    def reset(self):
        pass

    def update(self):
        pass

# ===================== GAME 1: DINO RUNNER =====================
class DinoRunnerGame(MiniGame):
    def __init__(self, canvas, width, height, app):
        super().__init__(canvas, width, height, app)
        self.COLOR = "#535353"
        self.BG_COLOR = "#F7F7F7"
        self.ground_y = height - 35
        self.reset()

    def reset(self):
        self.dino = {"x": 50, "y": self.ground_y - 44, "vy": 0, "jumping": False, "frame": 0}
        self.obstacles = []
        self.ground_pixels = [{"x": random.randint(0, self.width), "y": random.randint(self.ground_y+2, self.height-5)} for _ in range(20)]
        self.clouds = [{"x": random.randint(0, self.width), "y": random.randint(30, 80)} for _ in range(3)]
        self.speed = 7
        self.score = 0
        self.frame_count = 0
        self.high_score = self.app.db.get_highscore("dino_runner") if self.app else 0

    def draw_dino(self, x, y):
        c = self.COLOR
        leg_frame = (self.frame_count // 6) % 2
        self.canvas.create_rectangle(x+22, y, x+44, y+16, fill=c, outline="")
        self.canvas.create_rectangle(x+24, y+2, x+28, y+6, fill=self.BG_COLOR, outline="")
        self.canvas.create_rectangle(x+2, y+16, x+24, y+32, fill=c, outline="")
        self.canvas.create_rectangle(x, y+18, x+5, y+28, fill=c, outline="")
        self.canvas.create_rectangle(x+24, y+16, x+30, y+24, fill=c, outline="")
        if self.dino["jumping"]:
            self.canvas.create_rectangle(x+10, y+32, x+16, y+38, fill=c, outline="")
            self.canvas.create_rectangle(x+20, y+32, x+26, y+38, fill=c, outline="")
        elif leg_frame == 0:
            self.canvas.create_rectangle(x+10, y+32, x+18, y+36, fill=c, outline="")
            self.canvas.create_rectangle(x+20, y+32, x+26, y+44, fill=c, outline="")
            self.canvas.create_rectangle(x+26, y+40, x+32, y+44, fill=c, outline="")
        else:
            self.canvas.create_rectangle(x+10, y+32, x+16, y+44, fill=c, outline="")
            self.canvas.create_rectangle(x+10, y+40, x+16, y+44, fill=c, outline="")
            self.canvas.create_rectangle(x+18, y+32, x+26, y+36, fill=c, outline="")

    def draw_cactus(self, x, y, size_type):
        c = self.COLOR
        if size_type == 0:
            self.canvas.create_rectangle(x+5, y, x+10, y+30, fill=c, outline="")
            self.canvas.create_rectangle(x, y+5, x+5, y+15, fill=c, outline="")
            self.canvas.create_rectangle(x+10, y+10, x+15, y+20, fill=c, outline="")
        else:
            self.canvas.create_rectangle(x+7, y, x+15, y+45, fill=c, outline="")
            self.canvas.create_rectangle(x, y+10, x+7, y+25, fill=c, outline="")
            self.canvas.create_rectangle(x+15, y+15, x+22, y+30, fill=c, outline="")

    def draw_bird(self, x, y):
        c = self.COLOR
        wing_up = (self.frame_count // 10) % 2
        self.canvas.create_rectangle(x+10, y+5, x+30, y+15, fill=c, outline="")
        self.canvas.create_rectangle(x, y+8, x+10, y+12, fill=c, outline="")
        if wing_up:
            self.canvas.create_polygon(x+15, y+5, x+25, y+5, x+20, y-10, fill=c)
        else:
            self.canvas.create_polygon(x+15, y+15, x+25, y+15, x+20, y+25, fill=c)

    def update(self):
        if not self.active:
            return
        self.frame_count += 1
        self.canvas.delete("all")
        self.canvas.create_rectangle(0, 0, self.width, self.height, fill=self.BG_COLOR, outline="")
        self.canvas.create_line(0, self.ground_y, self.width, self.ground_y, fill=self.COLOR)
        for p in self.ground_pixels:
            p["x"] -= self.speed
            if p["x"] < 0:
                p["x"] = self.width + 10
            self.canvas.create_rectangle(p["x"], p["y"], p["x"]+2, p["y"]+1, fill=self.COLOR, outline="")
        for cl in self.clouds:
            cl["x"] -= self.speed * 0.1
            if cl["x"] < -60:
                cl["x"] = self.width + 20
                cl["y"] = random.randint(30, 80)
            self.canvas.create_rectangle(cl["x"], cl["y"], cl["x"]+30, cl["y"]+2, fill="#E1E1E1", outline="")

        if not self.dino["jumping"]:
            for obs in self.obstacles:
                dist = obs["x"] - (self.dino["x"] + 40)
                if 0 < dist < (50 + self.speed * 8):
                    if obs["type"] != "bird" or obs["y"] > self.ground_y - 50:
                        self.dino["vy"] = -13
                        self.dino["jumping"] = True
                        break
        if self.dino["jumping"]:
            self.dino["vy"] += 0.8
            self.dino["y"] += self.dino["vy"]
            if self.dino["y"] >= self.ground_y - 44:
                self.dino["y"] = self.ground_y - 44
                self.dino["jumping"] = False

        if self.frame_count % random.randint(50, 100) == 0:
            r = random.random()
            if self.score > 500 and r > 0.8:
                by = random.choice([self.ground_y-65, self.ground_y-40, self.ground_y-15])
                self.obstacles.append({"x": self.width, "y": by, "w": 40, "h": 20, "type": "bird"})
            elif r > 0.4:
                count = random.randint(1, 3)
                self.obstacles.append({"x": self.width, "y": self.ground_y-30, "w": 15*count, "h": 30, "type": "cactus", "st": 0, "cnt": count})
            else:
                self.obstacles.append({"x": self.width, "y": self.ground_y-45, "w": 25, "h": 45, "type": "cactus", "st": 1, "cnt": 1})

        for obs in self.obstacles[:]:
            obs["x"] -= self.speed
            if obs["type"] == "cactus":
                for i in range(obs.get("cnt", 1)):
                    self.draw_cactus(obs["x"] + i*15, obs["y"], obs["st"])
            else:
                self.draw_bird(obs["x"], obs["y"])
            if obs["x"] + obs["w"] < 0:
                self.obstacles.remove(obs)
                self.score += 1
                self.speed += 0.01
            dx, dy = self.dino["x"], self.dino["y"]
            if (dx + 10 < obs["x"] + obs["w"] and dx + 35 > obs["x"] and
                dy + 10 < obs["y"] + obs["h"] and dy + 40 > obs["y"]):
                self.active = False
                if self.app and self.score > self.high_score:
                    self.app.db.increment_score("dino_runner")
                self.canvas.create_text(self.width/2, self.height/2, text="G A M E  O V E R",
                                        font=("Courier", 15, "bold"), fill=self.COLOR)
                self.canvas.after(1500, self.start)
                return
        self.draw_dino(self.dino["x"], self.dino["y"])
        score_str = f"HI {int(self.high_score):05d}  {int(self.score):05d}"
        self.canvas.create_text(self.width-15, 20, text=score_str,
                                font=("Courier", 10, "bold"), fill=self.COLOR, anchor="ne")
        self.after_id = self.canvas.after(16, self.update)

# ===================== GAME 2: AUTO PONG =====================
class AutoPongGame(MiniGame):
    def __init__(self, canvas, width, height, app):
        super().__init__(canvas, width, height, app)
        self.paddle_w, self.paddle_h, self.ball_r = 8, 40, 5
        self.reset()

    def reset(self):
        self.ball_x, self.ball_y = self.width / 2, self.height / 2
        self.ball_vx, self.ball_vy = random.choice([-5, 5]), random.choice([-4, 4])
        self.pad1_y = self.pad2_y = self.height / 2 - self.paddle_h / 2

    def update(self):
        if not self.active:
            return
        self.canvas.delete("all")
        self.canvas.create_rectangle(0, 0, self.width, self.height, fill="#111111", outline="")
        self.canvas.create_line(self.width/2, 0, self.width/2, self.height, fill="#333333", dash=(4, 4))
        self.ball_x += self.ball_vx
        self.ball_y += self.ball_vy
        if self.ball_y - self.ball_r <= 0 or self.ball_y + self.ball_r >= self.height:
            self.ball_vy = -self.ball_vy
        t1 = self.ball_y - 20 if self.ball_vx > 0 else self.height/2 - 20
        t2 = self.height/2 - 20 if self.ball_vx > 0 else self.ball_y - 20
        self.pad1_y += (t1 - self.pad1_y) * 0.15
        self.pad2_y += (t2 - self.pad2_y) * 0.15
        self.pad1_y = max(0, min(self.height - 40, self.pad1_y))
        self.pad2_y = max(0, min(self.height - 40, self.pad2_y))
        if self.ball_x - 5 <= 23 and self.pad1_y <= self.ball_y <= self.pad1_y + 40:
            self.ball_x, self.ball_vx = 28, -self.ball_vx
        if self.ball_x + 5 >= self.width - 23 and self.pad2_y <= self.ball_y <= self.pad2_y + 40:
            self.ball_x, self.ball_vx = self.width - 28, -self.ball_vx
        self.canvas.create_rectangle(15, self.pad1_y, 23, self.pad1_y+40, fill="#00FF00", outline="")
        self.canvas.create_rectangle(self.width-23, self.pad2_y, self.width-15, self.pad2_y+40, fill="#FF00FF", outline="")
        self.canvas.create_oval(self.ball_x-5, self.ball_y-5, self.ball_x+5, self.ball_y+5, fill="#FFFFFF", outline="")
        self.after_id = self.canvas.after(20, self.update)

# ===================== GAME 3: AUTO AGE OF EMPIRES (ĐẾ CHẾ TỰ CHƠI) =====================
class AutoAOEGame(MiniGame):
    def __init__(self, canvas, width, height, app):
        super().__init__(canvas, width, height, app)
        self.reset()

    def reset(self):
        self.resources = []
        for _ in range(30):
            self.resources.append({"type": "wood", "x": random.randint(50, self.width-50), "y": random.randint(50, self.height-50), "amount": 300})
        for _ in range(20):
            self.resources.append({"type": "food", "x": random.randint(50, self.width-50), "y": random.randint(50, self.height-50), "amount": 200})

        self.teams = {
            "red": {"food": 100, "wood": 50, "color": "#E74C3C", "pop": 1, "max_pop": 10},
            "blue": {"food": 100, "wood": 50, "color": "#3498DB", "pop": 1, "max_pop": 10}
        }
        self.buildings = [
            {"team": "red", "type": "TC", "x": 40, "y": self.height/2, "hp": 1000, "max_hp": 1000, "size": 18},
            {"team": "blue", "type": "TC", "x": self.width-40, "y": self.height/2, "hp": 1000, "max_hp": 1000, "size": 18}
        ]
        self.units = [
            {"team": "red", "type": "vill", "x": 60, "y": self.height/2, "hp": 30, "max_hp": 30, "state": "idle", "target": None, "carry": 0, "ctype": "", "cd": 0, "build_progress": 0},
            {"team": "blue", "type": "vill", "x": self.width-60, "y": self.height/2, "hp": 30, "max_hp": 30, "state": "idle", "target": None, "carry": 0, "ctype": "", "cd": 0, "build_progress": 0}
        ]
        self.particles = []
        self.game_over = False
        self.timer = 0

    def update(self):
        if not self.active: return
        
        # --- LOGIC ---
        if not self.game_over:
            self.timer += 1
            self.update_macro()
            self.update_units()
            
            # Dọn dẹp xác chết/tài nguyên cạn kiệt
            self.resources = [r for r in self.resources if r["amount"] > 0]
            self.units = [u for u in self.units if u["hp"] > 0]
            self.buildings = [b for b in self.buildings if b["hp"] > 0]
            
            # Cập nhật hạt hiệu ứng
            for p in self.particles[:]:
                p["life"] -= 1
                if p["life"] <= 0: self.particles.remove(p)

        # --- VẼ HÌNH ---
        self.canvas.delete("all")
        self.canvas.create_rectangle(0, 0, self.width, self.height, fill="#27AE60", outline="")
        
        # Vẽ Tài nguyên
        for r in self.resources:
            self.draw_resource(r)

        # Vẽ Công trình
        for b in self.buildings:
            self.draw_building(b)

        # Vẽ Lính / Nông dân
        for u in self.units:
            self.draw_unit(u)

        # Vẽ Hiệu ứng (Text bay lên hoặc mảnh vỡ)
        for p in self.particles:
            if "text" in p:
                self.canvas.create_text(p["x"], p["y"]-(20-p["life"]), text=p["text"], fill=p["c"], font=("Arial", 8, "bold"))
            elif p.get("type") == "blood":
                r = (8 - p["life"]) / 2
                self.canvas.create_oval(p["x"]-r, p["y"]-r, p["x"]+r, p["y"]+r, fill=p["c"], outline="")
            else:
                self.canvas.create_oval(p["x"]-2, p["y"]-2, p["x"]+2, p["y"]+2, fill=p["c"], outline="")

        # Bảng HUD hiển thị tài nguyên 2 bên
        r, b = self.teams['red'], self.teams['blue']
        self.canvas.create_text(10, 10, text=f"🔴 ĐỎ: {r['food']}🍎 {r['wood']}🪵 {r['pop']}/{r['max_pop']}🧑‍🤝‍🧑", anchor="nw", fill="#E74C3C", font=("Segoe UI", 10, "bold"))
        self.canvas.create_text(self.width-10, 10, text=f"🧑‍🤝‍🧑{b['pop']}/{b['max_pop']} 🪵{b['wood']} 🍎{b['food']} :XANH 🔵", anchor="ne", fill="#3498DB", font=("Segoe UI", 10, "bold"))

        # Check Win/Lose
        tcs = [b for b in self.buildings if b["type"] == "TC"]
        if len(tcs) < 2 and not self.game_over:
            self.game_over = True
            winner = tcs[0]["team"].upper() if tcs else "HÒA NHAU!"
            self.canvas.create_rectangle(self.width/2-80, self.height/2-25, self.width/2+80, self.height/2+25, fill="#2C3E50", outline="#F1C40F", width=2)
            self.canvas.create_text(self.width/2, self.height/2, text=f"ĐỘI {winner} ĐÃ THẮNG!", fill="#F1C40F", font=("Segoe UI", 12, "bold"))
            self.canvas.after(4000, lambda: self.reset() if self.active else None) # Tự reset chơi lại

        self.after_id = self.canvas.after(30, self.update)

    def draw_resource(self, r):
        if r["type"] == "wood":
            self.canvas.create_rectangle(r["x"]-2, r["y"]-10, r["x"]+2, r["y"]+5, fill="#8B4513", outline="")
            self.canvas.create_oval(r["x"]-10, r["y"]-20, r["x"]+10, r["y"], fill="#229954", outline="#1E8449")
            self.canvas.create_oval(r["x"]-8, r["y"]-25, r["x"]+8, r["y"]-5, fill="#2ECC71", outline="")
        else: # food
            self.canvas.create_oval(r["x"]-8, r["y"]-8, r["x"]+8, r["y"]+8, fill="#145A32", outline="")
            self.canvas.create_oval(r["x"]-4, r["y"]-10, r["x"]+10, r["y"]-2, fill="#1E8449", outline="")
            self.canvas.create_oval(r["x"]-10, r["y"]-2, r["x"]+4, r["y"]+6, fill="#1E8449", outline="")
            for _ in range(3):
                rx, ry = r["x"]+random.randint(-6,6), r["y"]+random.randint(-6,6)
                self.canvas.create_oval(rx-2, ry-2, rx+2, ry+2, fill="#C0392B", outline="")

    def draw_building(self, b):
        c = self.teams[b["team"]]["color"]
        s = b["size"]
        if b["type"] == "TC":
            self.canvas.create_rectangle(b["x"]-s, b["y"]-s, b["x"]+s, b["y"]+s, fill=c, outline="#2C3E50", width=2)
            self.canvas.create_polygon(b["x"]-s-4, b["y"]-s, b["x"], b["y"]-s-10, b["x"]+s+4, b["y"]-s, fill="#E67E22", outline="#D35400")
        elif b["type"] == "Barracks":
            self.canvas.create_rectangle(b["x"]-s, b["y"]-s, b["x"]+s, b["y"]+s, fill="#A04000", outline="#2C3E50", width=2)
            self.canvas.create_rectangle(b["x"]-s+2, b["y"]-s-8, b["x"]+s-2, b["y"]-s, fill=c, outline="#2C3E50")
        elif b["type"] == "House":
            self.canvas.create_rectangle(b["x"]-s, b["y"]-s, b["x"]+s, b["y"]+s, fill="#D2B48C", outline="#8B4513")
            self.canvas.create_polygon(b["x"]-s-2, b["y"]-s, b["x"], b["y"]-s-8, b["x"]+s+2, b["y"]-s, fill="#A0522D", outline="#8B4513")
        elif b["type"] == "House_Found":
            self.canvas.create_rectangle(b["x"]-s, b["y"]-s, b["x"]+s, b["y"]+s, fill="", outline="#F1C40F", dash=(4,4))

        # Thanh Máu (HP bar)
        ratio = b["hp"] / b["max_hp"]
        self.canvas.create_rectangle(b["x"]-s, b["y"]-s-8, b["x"]+s, b["y"]-s-5, fill="#000", outline="")
        self.canvas.create_rectangle(b["x"]-s, b["y"]-s-8, b["x"]-s + (2*s*ratio), b["y"]-s-5, fill="#2ECC71", outline="")

    def draw_unit(self, u):
        c = self.teams[u["team"]]["color"]
        # Shadow
        self.canvas.create_oval(u["x"]-5, u["y"]+2, u["x"]+5, u["y"]+5, fill="#000", stipple="gray50", outline="")
        if u["type"] == "vill":
            self.canvas.create_rectangle(u["x"]-3, u["y"]-8, u["x"]+3, u["y"]+4, fill="#F5CBA7", outline="#000") # Body
            self.canvas.create_oval(u["x"]-4, u["y"]-14, u["x"]+4, u["y"]-6, fill="#F5CBA7", outline="#000") # Head
            if u["carry"] > 0: # Đang vác đồ
                cc = "#8B4513" if u["ctype"] == "wood" else "#E74C3C"
                self.canvas.create_rectangle(u["x"]-5, u["y"]-18, u["x"]+5, u["y"]-12, fill=cc, outline="")
        else: # Military
            self.canvas.create_rectangle(u["x"]-5, u["y"]-10, u["x"]+5, u["y"]+4, fill=c, outline="#000") # Body
            self.canvas.create_oval(u["x"]-4, u["y"]-16, u["x"]+4, u["y"]-8, fill="#F5CBA7", outline="#000") # Head
            self.canvas.create_rectangle(u["x"]-6, u["y"]-18, u["x"]+6, u["y"]-14, fill="#7F8C8D", outline="#000") # Helmet
            # Weapon
            if u["state"] == "attack" and u["cd"] > 15: # Chém
                self.canvas.create_line(u["x"]+4, u["y"]-8, u["x"]+15, u["y"]-2, fill="#BDC3C7", width=3)
            else: # Thủ
                self.canvas.create_line(u["x"]+4, u["y"]-8, u["x"]+10, u["y"]-14, fill="#BDC3C7", width=3)
            # Shield
            self.canvas.create_oval(u["x"]-12, u["y"]-8, u["x"]-2, u["y"]+4, fill="#A04000", outline="#000")

    def update_macro(self):
        # AI Quản lý vĩ mô (Xây nhà, đẻ quân)
        if self.timer % 30 != 0: return
        
        # Nạp lại tài nguyên bản đồ để game chơi được mãi mãi
        if len([r for r in self.resources if r["type"] == "wood"]) < 5:
            self.resources.append({"type": "wood", "x": random.randint(50, self.width-50), "y": random.randint(50, self.height-50), "amount": 300})
        if len([r for r in self.resources if r["type"] == "food"]) < 5:
            self.resources.append({"type": "food", "x": random.randint(50, self.width-50), "y": random.randint(50, self.height-50), "amount": 200})
        
        for t_name, t_data in self.teams.items():
            t_bldgs = [b for b in self.buildings if b["team"] == t_name]
            t_units = [u for u in self.units if u["team"] == t_name]
            tcs = [b for b in t_bldgs if b["type"] == "TC"]
            barracks = [b for b in t_bldgs if b["type"] == "Barracks"]
            houses = len([b for b in t_bldgs if b["type"] == "House" or b["type"] == "House_Found"])

            vills = len([u for u in t_units if u["type"] == "vill"])
            mils = len([u for u in t_units if u["type"] == "mil"])
            t_data["pop"] = vills + mils
            
            if tcs:
                tc = tcs[0]
                # Đẻ nông dân
                if vills < 6 and t_data["food"] >= 50 and t_data["pop"] < t_data["max_pop"]:
                    t_data["food"] -= 50
                    self.units.append({"team": t_name, "type": "vill", "x": tc["x"], "y": tc["y"]+20, "hp": 30, "max_hp": 30, "state": "idle", "target": None, "carry": 0, "ctype": "", "cd": 0})
                
                # Xây nhà ở (House)
                if vills > 0 and houses < 3 and t_data["pop"] >= t_data["max_pop"] - 1 and t_data["wood"] >= 30:
                    idle_vill = next((u for u in t_units if u["type"] == "vill" and u["state"] == "idle"), None)
                    if idle_vill:
                        t_data["wood"] -= 30
                        hx, hy = tc["x"] + random.randint(-60, 60), tc["y"] + random.randint(-60, 60)
                        foundation = {"team": t_name, "type": "House_Found", "x": hx, "y": hy, "hp": 1, "max_hp": 100, "size": 10}
                        self.buildings.append(foundation)
                        idle_vill["state"] = "build"; idle_vill["target"] = foundation

                # Xây trại lính (Barracks)
                if len(barracks) < 2 and t_data["wood"] >= 100:
                    t_data["wood"] -= 100
                    bx = tc["x"] + random.choice([-50, 50, 0])
                    by = tc["y"] + random.choice([-50, 50])
                    bx = max(20, min(self.width-20, bx))
                    by = max(20, min(self.height-20, by))
                    self.buildings.append({"team": t_name, "type": "Barracks", "x": bx, "y": by, "hp": 300, "max_hp": 300, "size": 15})
                    self.particles.append({"x": bx, "y": by, "life": 20, "c": "#F1C40F", "text": "XÂY!"})
                    
            # Đẻ quân đội
            if barracks:
                brk = random.choice(barracks)
                if mils < 15 and t_data["food"] >= 40 and t_data["wood"] >= 15 and t_data["pop"] < t_data["max_pop"]:
                    t_data["food"] -= 40
                    t_data["wood"] -= 15
                    self.units.append({"team": t_name, "type": "mil", "x": brk["x"], "y": brk["y"]+15, "hp": 80, "max_hp": 80, "state": "idle", "target": None, "cd": 0})

    def update_units(self):
        # AI Quản lý vi mô (Di chuyển, chặt gỗ, chém nhau)
        for u in self.units:
            if u["hp"] <= 0: continue
            
            if u["type"] == "vill":
                # --- NÔNG DÂN ---
                enemy_mils = [e for e in self.units if e["team"] != u["team"] and e["type"] == "mil"]
                closest_enemy = min(enemy_mils, key=lambda e: math.hypot(e["x"]-u["x"], e["y"]-u["y"]), default=None)
                if closest_enemy and math.hypot(closest_enemy["x"]-u["x"], closest_enemy["y"]-u["y"]) < 70:
                    u["state"] = "flee"
                    tcs = [b for b in self.buildings if b["team"] == u["team"] and b["type"] == "TC"]
                    if tcs: u["target"] = tcs[0]
                    u["carry"] = 0 # Sợ quá vứt đồ

                if u["carry"] >= 10 or (u["target"] and u["target"].get("amount", 0) <= 0):
                    u["state"] = "return"
                    tcs = [b for b in self.buildings if b["team"] == u["team"] and b["type"] == "TC"]
                    if tcs: 
                        u["target"] = tcs[0]
                    else: 
                        u["state"] = "idle"
                        
                if u["state"] == "idle" or (u["state"] == "flee" and not u["target"]):
                    team_data = self.teams[u["team"]]
                    barracks_count = len([b for b in self.buildings if b["team"] == u["team"] and b["type"] == "Barracks" or b["type"] == "House_Found"])
                    pref = "wood" if team_data["wood"] < 100 and barracks_count < 2 else "food" # Ưu tiên gỗ nếu chưa có trại lính
                    
                    valid_res = [r for r in self.resources if r["type"] == pref]
                    if not valid_res: valid_res = self.resources
                    
                    if valid_res:
                        u["target"] = min(valid_res, key=lambda r: math.hypot(r["x"]-u["x"], r["y"]-u["y"]))
                        u["state"] = "gather"
                        
                if u["state"] in ["gather", "return", "flee"] and u["target"]:
                    d = math.hypot(u["target"]["x"] - u["x"], u["target"]["y"] - u["y"])
                    if d > 12:
                        u["x"] += (u["target"]["x"] - u["x"]) / d * 2.0
                        u["y"] += (u["target"]["y"] - u["y"]) / d * 2.0
                    else:
                        if u["state"] == "gather":
                            u["cd"] -= 1
                            if u["cd"] <= 0:
                                u["carry"] += 2
                                u["target"]["amount"] -= 2
                                u["ctype"] = u["target"]["type"]
                                self.particles.append({"x": u["x"], "y": u["y"]-10, "life": 15, "c": "#FFF", "text": "+2"})
                                u["cd"] = 10
                        elif u["state"] == "return":
                            self.teams[u["team"]][u["ctype"]] += u["carry"]
                            u["carry"] = 0
                            u["state"] = "idle"
                        elif u["state"] == "flee":
                            u["state"] = "idle" # Đã về đến nhà an toàn
                elif u["state"] == "build" and u["target"]:
                    d = math.hypot(u["target"]["x"] - u["x"], u["target"]["y"] - u["y"])
                    if d > 15:
                        u["x"] += (u["target"]["x"] - u["x"]) / d * 2.0
                        u["y"] += (u["target"]["y"] - u["y"]) / d * 2.0
                    else:
                        u["target"]["hp"] += 2
                        if u["target"]["hp"] >= u["target"]["max_hp"]:
                            u["target"]["type"] = "House"; self.teams[u["team"]]["max_pop"] += 5
                            u["state"] = "idle"
                            
            elif u["type"] == "mil":
                # --- QUÂN ĐỘI ---
                if not u["target"] or u["target"].get("hp", 0) <= 0:
                    enemies = [e for e in self.units + self.buildings if e["team"] != u["team"] and e["hp"] > 0]
                    if enemies:
                        def score(e):
                            dist = math.hypot(e["x"]-u["x"], e["y"]-u["y"])
                            prio = 0
                            if e.get("type") == "mil": prio = -200
                            elif e.get("type") == "vill": prio = 50
                            elif e.get("type") == "Barracks": prio = -50
                            elif e.get("type") == "TC": prio = -100
                            dist += prio
                            return dist
                        u["target"] = min(enemies, key=score)
                    else:
                        u["state"] = "idle"
                
                if u["target"]:
                    d = math.hypot(u["target"]["x"] - u["x"], u["target"]["y"] - u["y"])
                    attack_range = 15 if "size" not in u["target"] else u["target"]["size"] + 10
                    if d > attack_range:
                        u["x"] += (u["target"]["x"] - u["x"]) / d * 1.5
                        u["y"] += (u["target"]["y"] - u["y"]) / d * 1.5
                    else:
                        u["cd"] -= 1
                        if u["cd"] <= 0:
                            u["target"]["hp"] -= 15 # Sát thương 1 nhát chém
                            u["cd"] = 25
                            self.particles.append({"x": u["target"]["x"], "y": u["target"]["y"], "life": 8, "c": "#E74C3C", "type": "blood"})

# ===================== GAME 4: AUTO SPACE SHOOTER =====================
class AutoSpaceShooterGame(MiniGame):
    def __init__(self, canvas, width, height, app):
        super().__init__(canvas, width, height, app)
        self.reset()

    def reset(self):
        # Load save data
        if self.app:
            sv = self.app.db.get_space_shooter_save()
            self.coins, self.w_lvl, self.f_lvl, self.d_lvl, self.s_lvl = sv if sv else (0, 1, 1, 0, 0)
        else:
            self.coins, self.w_lvl, self.f_lvl, self.d_lvl, self.s_lvl = 0, 1, 1, 0, 0
            
        self.ship_x = self.width / 2
        self.ship_y = self.height - 30
        self.lasers = []
        self.enemies = []
        self.particles = []
        self.stars = [{"x": random.randint(0, self.width), "y": random.randint(0, self.height), "speed": random.uniform(0.5, 2)} for _ in range(40)]
        self.score = 0
        self.fire_cd = 0
        self.skill_timer = 0
        self.beam_active = 0
        
        self.save_timer = 0

    def stop(self):
        super().stop()
        if self.app:
            self.app.db.save_space_shooter_state(self.coins, self.w_lvl, self.f_lvl, self.d_lvl, self.s_lvl)

    def update(self):
        if not self.active:
            return
        self.canvas.delete("all")
        self.canvas.create_rectangle(0, 0, self.width, self.height, fill="#0B0C10", outline="")

        # Vẽ và cập nhật sao băng (Background)
        for s in self.stars:
            s["y"] += s["speed"]
            if s["y"] > self.height:
                s["y"] = 0
                s["x"] = random.randint(0, self.width)
            c = "#555555" if s["speed"] < 1 else "#AAAAAA"
            self.canvas.create_oval(s["x"], s["y"], s["x"]+2, s["y"]+2, fill=c, outline="")

        self.update_gameplay()
            
        self.after_id = self.canvas.after(30, self.update)

    def update_gameplay(self):
        # AI TỰ ĐỘNG MUA NÂNG CẤP TỐI ƯU
        upgrades = [
            ("w_lvl", 50 * self.w_lvl, 5, "Vũ khí"),
            ("f_lvl", 40 * self.f_lvl, 5, "Tốc bắn"),
            ("d_lvl", 100 * (self.d_lvl + 1), 3, "Thuyền con"),
            ("s_lvl", 150 * (self.s_lvl + 1), 3, "Siêu Laser")
        ]
        affordable = [u for u in upgrades if getattr(self, u[0]) < u[2] and self.coins >= u[1]]
        if affordable:
            affordable.sort(key=lambda x: x[1]) # Mua từ rẻ nhất đến đắt nhất
            best_upg = affordable[0]
            self.coins -= best_upg[1]
            setattr(self, best_upg[0], getattr(self, best_upg[0]) + 1)
            
            # Hiệu ứng nổ hạt xanh lá báo hiệu nâng cấp thành công
            for _ in range(15):
                self.particles.append({"x": self.ship_x, "y": self.ship_y, "vx": random.uniform(-4, 4), "vy": random.uniform(-4, 4), "life": 25, "c": "#2ECC71"})
            if self.app:
                self.app.db.save_space_shooter_state(self.coins, self.w_lvl, self.f_lvl, self.d_lvl, self.s_lvl)

        # Độ khó tăng theo điểm
        diff_mult = 1 + (self.score / 1000)
        spawn_rate = min(0.1, 0.03 * diff_mult)
        
        # Sinh quái vật
        if random.random() < spawn_rate:
            r = random.random()
            base_hp = 2 + (self.score // 300)
            if r < 0.6: # Meteor
                self.enemies.append({"type": "meteor", "x": random.randint(20, self.width-20), "y": -20, "r": random.randint(12, 22), "hp": base_hp, "speed": random.uniform(1.2, 2.0)})
            elif r < 0.9: # Fighter (Zig-zag)
                self.enemies.append({"type": "fighter", "x": random.randint(20, self.width-20), "y": -20, "r": 12, "hp": base_hp - 1, "speed": random.uniform(2.0, 3.5), "dx": random.choice([-1.5, 1.5])})
            else: # Tank
                self.enemies.append({"type": "tank", "x": random.randint(30, self.width-30), "y": -30, "r": 25, "hp": base_hp * 3, "speed": random.uniform(0.5, 1.0)})

        # AI Tự động điều khiển Tàu (Targeting)
        target = None
        max_y = -100
        for m in self.enemies:
            if m["y"] > max_y:
                max_y = m["y"]
                target = m

        if target:
            speed = 4 + self.f_lvl * 0.5
            if self.ship_x < target["x"] - 5:
                self.ship_x += speed
            elif self.ship_x > target["x"] + 5:
                self.ship_x -= speed
            self.ship_x = max(20, min(self.width-20, self.ship_x))

        # Bắn đạn cơ bản & Drones
        if self.fire_cd > 0:
            self.fire_cd -= 1
        if target and abs(self.ship_x - target["x"]) < 25 and self.fire_cd == 0:
            dmg = self.w_lvl
            if self.w_lvl >= 3:
                self.lasers.append({"x": self.ship_x - 10, "y": self.ship_y - 10, "dmg": dmg, "color": "#00FFFF"})
                self.lasers.append({"x": self.ship_x, "y": self.ship_y - 15, "dmg": dmg, "color": "#00FFFF"})
                self.lasers.append({"x": self.ship_x + 10, "y": self.ship_y - 10, "dmg": dmg, "color": "#00FFFF"})
            else:
                self.lasers.append({"x": self.ship_x - 6, "y": self.ship_y - 10, "dmg": dmg, "color": "#00FFFF"})
                self.lasers.append({"x": self.ship_x + 6, "y": self.ship_y - 10, "dmg": dmg, "color": "#00FFFF"})
            
            # Drones fire
            if self.d_lvl > 0:
                d_dmg = self.d_lvl
                self.lasers.append({"x": self.ship_x - 25, "y": self.ship_y + 5, "dmg": d_dmg, "color": "#2ECC71"})
                self.lasers.append({"x": self.ship_x + 25, "y": self.ship_y + 5, "dmg": d_dmg, "color": "#2ECC71"})
                
            self.fire_cd = max(3, 12 - self.f_lvl)

        # Chiêu thức Siêu Laser
        if self.s_lvl > 0:
            if self.beam_active > 0:
                self.beam_active -= 1
                # Vẽ Beam
                bw = 15 + self.s_lvl * 5
                self.canvas.create_rectangle(self.ship_x - bw/2, 0, self.ship_x + bw/2, self.ship_y, fill="#9B59B6", outline="#8E44AD", stipple="gray50")
                self.canvas.create_line(self.ship_x, 0, self.ship_x, self.ship_y, fill="#FFFFFF", width=3)
                # Beam sát thương lập tức kẻ địch
                for e in self.enemies[:]:
                    if abs(e["x"] - self.ship_x) < e["r"] + bw/2:
                        e["hp"] -= self.s_lvl * 0.5
            else:
                self.skill_timer -= 1
                if self.skill_timer <= 0:
                    self.beam_active = 20 + self.s_lvl * 5
                    self.skill_timer = 200 - (self.s_lvl * 10)

        # Cập nhật tia Laser
        for l in self.lasers[:]:
            l["y"] -= 8
            w = 2 if l["color"] == "#00FFFF" else 1
            self.canvas.create_line(l["x"], l["y"], l["x"], l["y"]+12, fill=l["color"], width=w)
            if l["y"] < 0:
                self.lasers.remove(l)

        # Cập nhật hiệu ứng hạt (Particles) nổ tung
        for p in self.particles[:]:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["life"] -= 1
            self.canvas.create_oval(p["x"]-2, p["y"]-2, p["x"]+2, p["y"]+2, fill=p["c"], outline="")
            if p["life"] <= 0:
                self.particles.remove(p)

        # Cập nhật Quái & Va chạm
        for m in self.enemies[:]:
            if m["type"] == "fighter":
                m["x"] += m["dx"]
                m["y"] += m["speed"]
                if m["x"] < 15 or m["x"] > self.width - 15: m["dx"] *= -1
                self.canvas.create_polygon(m["x"], m["y"]+m["r"], m["x"]-m["r"], m["y"]-m["r"], m["x"]+m["r"], m["y"]-m["r"], fill="#E74C3C", outline="#C0392B")
                self.canvas.create_oval(m["x"]-4, m["y"]-4, m["x"]+4, m["y"], fill="#F1C40F", outline="")
            elif m["type"] == "tank":
                m["y"] += m["speed"]
                self.canvas.create_rectangle(m["x"]-m["r"], m["y"]-m["r"]*0.6, m["x"]+m["r"], m["y"]+m["r"]*0.6, fill="#7F8C8D", outline="#2C3E50", width=2)
                self.canvas.create_rectangle(m["x"]-m["r"]*0.5, m["y"]-m["r"]*0.8, m["x"]+m["r"]*0.5, m["y"]+m["r"]*0.8, fill="#95A5A6", outline="")
            else: # Meteor
                m["y"] += m["speed"]
                self.canvas.create_oval(m["x"]-m["r"], m["y"]-m["r"], m["x"]+m["r"], m["y"]+m["r"], fill="#5D4037", outline="#3E2723")
                self.canvas.create_oval(m["x"]-m["r"]/2, m["y"]-m["r"]/2, m["x"], m["y"], fill="#4E342E", outline="")
            
            if m["y"] - m["r"] > self.height and m in self.enemies:
                self.enemies.remove(m)
                continue
                
            if m["hp"] <= 0:
                if m in self.enemies: self.enemies.remove(m)
                self.score += 10
                self.coins += 1 + (m["r"] // 10)
                for _ in range(m["r"] // 2): # Hiệu ứng nổ
                    self.particles.append({"x": m["x"], "y": m["y"], "vx": random.uniform(-3,3), "vy": random.uniform(-3,3), "life": 15, "c": "#E74C3C"})
                continue

            for l in self.lasers[:]:
                if abs(l["x"] - m["x"]) < m["r"] and abs(l["y"] - m["y"]) < m["r"]:
                    if l in self.lasers: self.lasers.remove(l)
                    m["hp"] -= l["dmg"]
                    for _ in range(3): # Hiệu ứng tóe lửa khi trúng đạn
                        self.particles.append({"x": l["x"], "y": l["y"], "vx": random.uniform(-2,2), "vy": random.uniform(-2,2), "life": 10, "c": "#F1C40F"})
                    break

        # Vẽ Tàu vũ trụ tùy theo cấp độ vũ khí (Ngoại hình tiến hóa)
        sx, sy = self.ship_x, self.ship_y
        
        if self.w_lvl == 1:
            self.canvas.create_polygon(sx, sy-15, sx-12, sy+10, sx+12, sy+10, fill="#2ECC71", outline="#27AE60", width=2)
        elif self.w_lvl == 2:
            self.canvas.create_polygon(sx, sy-18, sx-14, sy+12, sx+14, sy+12, fill="#3498DB", outline="#2980B9", width=2)
            self.canvas.create_polygon(sx-14, sy+12, sx-18, sy+18, sx-10, sy+10, fill="#E67E22", outline="")
            self.canvas.create_polygon(sx+14, sy+12, sx+18, sy+18, sx+10, sy+10, fill="#E67E22", outline="")
        else:
            self.canvas.create_polygon(sx, sy-20, sx-16, sy+12, sx+16, sy+12, fill="#9B59B6", outline="#8E44AD", width=2)
            self.canvas.create_polygon(sx-16, sy+5, sx-22, sy+15, sx-12, sy+15, fill="#F1C40F", outline="")
            self.canvas.create_polygon(sx+16, sy+5, sx+22, sy+15, sx+12, sy+15, fill="#F1C40F", outline="")
            self.canvas.create_oval(sx-6, sy-5, sx+6, sy+5, fill="#00FFFF", outline="")
            
        # Lửa động cơ
        self.canvas.create_polygon(sx-6, sy+10, sx+6, sy+10, sx, sy+18+random.uniform(-3,3), fill="#F1C40F", outline="") 
        self.canvas.create_oval(sx-4, sy-2, sx+4, sy+6, fill="#2980B9", outline="")

        # Vẽ Drones (Thuyền con)
        if self.d_lvl > 0:
            dx1, dx2 = sx - 25, sx + 25
            dy = sy + 10 + math.sin(self.score * 0.1) * 3
            self.canvas.create_polygon(dx1, dy-6, dx1-5, dy+4, dx1+5, dy+4, fill="#2ECC71", outline="")
            self.canvas.create_polygon(dx2, dy-6, dx2-5, dy+4, dx2+5, dy+4, fill="#2ECC71", outline="")

        # Vẽ Điểm
        self.canvas.create_text(10, 10, text=f"SCORE: {self.score}", anchor="nw", fill="#F1C40F", font=("Courier", 12, "bold"))
        self.canvas.create_text(10, 25, text=f"COINS: {self.coins}", anchor="nw", fill="#F39C12", font=("Courier", 11, "bold"))
        
        # Trạng thái AI
        self.canvas.create_text(self.width - 10, 15, text="🤖 AI AUTO-BUY: ON", anchor="ne", fill="#2ECC71", font=("Courier", 10, "bold"))
        self.canvas.create_text(self.width - 10, 30, text=f"W:{self.w_lvl} F:{self.f_lvl} D:{self.d_lvl} S:{self.s_lvl}", anchor="ne", fill="#AAAAAA", font=("Courier", 8, "bold"))

        # Auto Save
        self.save_timer += 1
        if self.save_timer > 100:
            if self.app: self.app.db.save_space_shooter_state(self.coins, self.w_lvl, self.f_lvl, self.d_lvl, self.s_lvl)
            self.save_timer = 0

# ===================== GAME 5: AGE OF WAR =====================
UNIT_BASE = {
    "sword": {"cost": 15, "hp": 100, "dmg": 10, "range": 20, "speed": 1.8, "cd": 20},
    "bow":   {"cost": 25, "hp": 50,  "dmg": 8,  "range": 120, "speed": 1.2, "cd": 35},
    "tank":  {"cost": 40, "hp": 300, "dmg": 5,  "range": 20, "speed": 0.8, "cd": 40},
    "assa":  {"cost": 25, "hp": 80,  "dmg": 25, "range": 25, "speed": 3.0, "cd": 15},
    "mage":  {"cost": 60, "hp": 60,  "dmg": 15, "range": 100, "speed": 1.0, "cd": 45, "aoe": True}
}

AGE_DATA = {
    1: {"name": "Đồ Đá",   "base_hp": 1000, "mult": 1.0},
    2: {"name": "Trung Cổ", "base_hp": 2500, "mult": 2.0},
    3: {"name": "Hiện Đại", "base_hp": 6000, "mult": 4.5},
    4: {"name": "Tương Lai","base_hp": 15000,"mult": 10.0}
}

TOWER_DATA = {
    0: {"cost": 50,  "dmg": 0,   "cd": 999, "range": 0,    "color": "#555"},
    1: {"cost": 100, "dmg": 8,   "cd": 60,  "range": 90,   "color": "#F39C12"},
    2: {"cost": 300, "dmg": 20,  "cd": 70,  "range": 110,  "color": "#E67E22"},
    3: {"cost": 800, "dmg": 50,  "cd": 60,  "range": 130,  "color": "#2ECC71"},
    4: {"cost": 99999,"dmg": 120, "cd": 50,  "range": 150,  "color": "#E74C3C"}
}

# ===================== UNIT CLASSES =====================
class BaseUnit:
    def __init__(self, team, u_type, age, x, y, stats, mult):
        self.team = team
        self.type = u_type
        self.age = age
        self.x = x
        self.y = y
        self.dir = 1 if team == "red" else -1
        self.hp = stats["hp"] * mult
        self.max_hp = stats["hp"] * mult
        self.dmg = stats["dmg"] * mult
        self.range = stats["range"]
        self.speed = stats["speed"]
        self.cd = 0
        self.max_cd = stats["cd"]
        self.action = "walk"
        self.styles = {
            1: {"head": "#F5CBA7", "body": "#A04000", "weapon": "#8B4513", "hat": "#2C3E50"},
            2: {"head": "#BDC3C7", "body": "#7F8C8D", "weapon": "#FFFFFF", "hat": "#95A5A6"},
            3: {"head": "#F5CBA7", "body": "#1E8449", "weapon": "#BDC3C7", "hat": "#145A32"},
            4: {"head": "#9B59B6", "body": "#2C3E50", "weapon": "#00FFFF", "hat": "#8E44AD"}
        }

    def draw_shadow_and_hp(self, canvas):
        w_ratio = max(0, self.hp/self.max_hp)
        canvas.create_oval(self.x-8, self.y+8, self.x+8, self.y+12, fill="#111111", outline="")
        canvas.create_rectangle(self.x-8, self.y-28, self.x+8, self.y-26, fill="#000000", outline="")
        canvas.create_rectangle(self.x-8, self.y-28, self.x-8 + int(16*w_ratio), self.y-26, fill="#32CD32", outline="")

    def get_anim_frames(self, frame_count):
        is_atk = self.action == "attack"
        walk_f = (frame_count // 4) % 4 if not is_atk else 0
        atk_f = (self.max_cd - self.cd) / max(1, self.max_cd)
        return is_atk, walk_f, atk_f

    def draw_legs(self, canvas, walk_frame):
        lx1, lx2 = self.x - 3, self.x + 1
        ly1, ly2 = self.y + 5, self.y + 10
        if walk_frame == 1: lx1 -= 2*self.dir; lx2 += 2*self.dir
        elif walk_frame == 3: lx1 += 2*self.dir; lx2 -= 2*self.dir
        canvas.create_rectangle(lx1, ly1, lx1+2, ly2, fill="#000000", outline="")
        canvas.create_rectangle(lx2, ly1, lx2+2, ly2, fill="#000000", outline="")

    def draw_body(self, canvas, bounce, st):
        by = self.y + bounce
        canvas.create_rectangle(self.x-5, by-10, self.x+5, by+5, fill=st["body"], outline="black")
        canvas.create_rectangle(self.x-4, by-18, self.x+4, by-10, fill=st["head"], outline="black")
        canvas.create_rectangle(self.x + self.dir*1, by-16, self.x + self.dir*3, by-14, fill="black", outline="")
        if self.age == 1:
            canvas.create_rectangle(self.x-5, by-20, self.x+5, by-18, fill=st["hat"], outline="")
        else:
            canvas.create_rectangle(self.x-6, by-21, self.x+6, by-17, fill=st["hat"], outline="black")
            if self.age >= 3: 
                canvas.create_rectangle(self.x+self.dir*2, by-19, self.x+self.dir*5, by-17, fill="#E74C3C" if self.team=="red" else "#3498DB", outline="")

class SwordUnit(BaseUnit):
    def draw(self, canvas, frame_count):
        self.draw_shadow_and_hp(canvas)
        is_atk, w_f, a_f = self.get_anim_frames(frame_count)
        self.draw_legs(canvas, w_f)
        bounce = -1 if w_f in (1, 3) else 0
        self.draw_body(canvas, bounce, self.styles[self.age])
        by = self.y + bounce
        wx, wy = self.x + self.dir*4, by - 5
        st = self.styles[self.age]
        
        if self.age < 3: canvas.create_oval(self.x+self.dir*2, by-3, self.x+self.dir*6, by+7, fill="#555", outline="black") # Shield
        else: canvas.create_line(self.x+self.dir*6, by-6, self.x+self.dir*6, by+10, fill="#00FFFF", width=2) # Force field
        
        if is_atk and a_f > 0.5: canvas.create_line(wx, wy, wx+self.dir*14, wy+10, fill=st["weapon"], width=3) # Slash
        else: canvas.create_line(wx, wy, wx+self.dir*8, wy-10, fill=st["weapon"], width=2)

class BowUnit(BaseUnit):
    def draw(self, canvas, frame_count):
        self.draw_shadow_and_hp(canvas)
        is_atk, w_f, a_f = self.get_anim_frames(frame_count)
        self.draw_legs(canvas, w_f)
        bounce = -1 if w_f in (1, 3) else 0
        self.draw_body(canvas, bounce, self.styles[self.age])
        by = self.y + bounce
        wx, wy = self.x + self.dir*4, by - 5
        st = self.styles[self.age]
        
        if self.age < 3:
            canvas.create_rectangle(self.x-self.dir*6, by-8, self.x-self.dir*3, by, fill="#8B4513", outline="") # Quiver
            canvas.create_arc(wx-self.dir*4, wy-8, wx+self.dir*6, wy+8, start=90 if self.dir==1 else 270, extent=180, style=tk.ARC, outline=st["weapon"], width=2)
            if is_atk and a_f < 0.8: canvas.create_line(wx, wy, wx+self.dir*8, wy, fill="white", width=1) # Draw string
        else:
            canvas.create_line(wx-self.dir*2, wy, wx+self.dir*10, wy, fill=st["weapon"], width=3) # Gun
            if is_atk and a_f > 0.8: canvas.create_oval(wx+self.dir*10, wy-3, wx+self.dir*16, wy+3, fill="#FFD700", outline="") # Muzzle flash

class TankUnit(BaseUnit):
    def draw(self, canvas, frame_count):
        self.draw_shadow_and_hp(canvas)
        is_atk, w_f, a_f = self.get_anim_frames(frame_count)
        st = self.styles[self.age]
        
        if self.age < 3:
            self.draw_legs(canvas, w_f)
            bounce = -1 if w_f in (1, 3) else 0
            by = self.y + bounce
            canvas.create_rectangle(self.x-8, by-12, self.x+8, by+6, fill=st["body"], outline="black")
            canvas.create_rectangle(self.x-6, by-20, self.x+6, by-12, fill=st["head"], outline="black")
            canvas.create_rectangle(self.x-7, by-22, self.x+7, by-18, fill=st["hat"], outline="black")
            wx, wy = self.x + self.dir*6, by - 2
            if is_atk and a_f > 0.5: canvas.create_oval(wx, wy-4, wx+self.dir*16, wy+4, fill="#CCC", outline="black")
            else: canvas.create_oval(wx-self.dir*2, wy-4, wx+self.dir*6, wy+4, fill="#CCC", outline="black")
        else:
            canvas.create_rectangle(self.x-14, self.y-5, self.x+14, self.y+10, fill=st["hat"], outline="black")
            canvas.create_oval(self.x-16, self.y+5, self.x+16, self.y+12, fill="#333", outline="") # Treads
            canvas.create_rectangle(self.x-8, self.y-12, self.x+8, self.y-5, fill=st["body"], outline="black")
            bx, by_ = self.x, self.y - 8
            canvas.create_line(bx, by_, bx+self.dir*18, by_, fill=st["weapon"], width=4)
            if is_atk and a_f > 0.8: canvas.create_oval(bx+self.dir*18, by_-5, bx+self.dir*28, by_+5, fill="#FF4500", outline="")

class AssaUnit(BaseUnit):
    def draw(self, canvas, frame_count):
        self.draw_shadow_and_hp(canvas)
        is_atk, w_f, a_f = self.get_anim_frames(frame_count)
        self.draw_legs(canvas, w_f)
        bounce = -1 if w_f in (1, 3) else 0
        by = self.y + bounce + 3 
        st = self.styles[self.age]
        canvas.create_rectangle(self.x-4, by-8, self.x+6, by+4, fill=st["body"], outline="black")
        canvas.create_rectangle(self.x-2, by-14, self.x+6, by-8, fill=st["head"], outline="black")
        wx, wy = self.x + self.dir*6, by - 2
        if is_atk and a_f > 0.4: canvas.create_line(wx, wy, wx+self.dir*14, wy, fill="#E74C3C", width=2)
        else: canvas.create_line(wx, wy, wx+self.dir*8, wy+4, fill=st["weapon"], width=2)
        canvas.create_line(self.x-self.dir*4, by-10, self.x-self.dir*12, by-8+math.sin(frame_count*0.5)*3, fill=st["hat"], width=2)

class MageUnit(BaseUnit):
    def draw(self, canvas, frame_count):
        self.draw_shadow_and_hp(canvas)
        is_atk, w_f, a_f = self.get_anim_frames(frame_count)
        by = self.y + math.sin(frame_count * 0.2) * 3 - 5
        st = self.styles[self.age]
        canvas.create_polygon(self.x, by-12, self.x+self.dir*8, by+8, self.x-self.dir*8, by+8, fill=st["body"], outline="black")
        canvas.create_rectangle(self.x-4, by-20, self.x+4, by-12, fill=st["head"], outline="black")
        canvas.create_polygon(self.x-6, by-20, self.x+6, by-20, self.x, by-28, fill=st["hat"], outline="black")
        wx, wy = self.x + self.dir*8, by - 5
        canvas.create_line(wx, wy+12, wx, wy-10, fill=st["weapon"], width=2)
        aura_r = 3 + math.sin(frame_count * 0.4) * 2
        if is_atk and a_f > 0.5: canvas.create_oval(wx-8, wy-18, wx+8, wy-2, fill="#00FFFF", outline="#FFFFFF")
        else: canvas.create_oval(wx-aura_r, wy-10-aura_r, wx+aura_r, wy-10+aura_r, fill="#8A2BE2", outline="")

UNIT_CLASSES = { "sword": SwordUnit, "bow": BowUnit, "tank": TankUnit, "assa": AssaUnit, "mage": MageUnit }

class AgeOfWarGame(MiniGame):
    def __init__(self, canvas, width, height, app):
        super().__init__(canvas, width, height, app)
        self.reset(full_reset=True)

    def reset(self, full_reset=False):
        self.units, self.projectiles, self.effects = [], [], []
        self.save_timer = 0
        self.frame_count = 0
        self.clouds = [{"x": random.randint(0, self.width), "y": random.randint(10, 60), "speed": random.uniform(0.1, 0.4)} for _ in range(4)]
        self.base_shake = {"red": 0, "blue": 0}

        if full_reset:
            r_hp, r_mana, r_age, r_tower, r_xp = AGE_DATA[1]["base_hp"], 0, 1, 0, 0
            b_hp, b_mana, b_age, b_tower, b_xp = AGE_DATA[1]["base_hp"], 0, 1, 0, 0
        else:
            res = self.app.db.get_aow_save() if self.app else None
            if not res:
                res = (1000, 0, 1, 0, 0, 1000, 0, 1, 0, 0)
            r_hp, r_mana, r_age, r_tower, r_xp, b_hp, b_mana, b_age, b_tower, b_xp = res
            r_age, b_age = min(4, max(1, int(r_age))), min(4, max(1, int(b_age)))
            r_tower, b_tower = min(4, max(0, int(r_tower))), min(4, max(0, int(b_tower)))
            if r_hp <= 0:
                r_hp = AGE_DATA[r_age]["base_hp"]
            if b_hp <= 0:
                b_hp = AGE_DATA[b_age]["base_hp"]

        self.bases = {
            "red": {"team": "red", "x": 35, "y": self.height - 40, "dir": 1, "color": "#E74C3C",
                    "hp": r_hp, "mana": r_mana, "age": r_age, "tower": r_tower, "xp": r_xp, "summon_cd": 0,
                    "ult_cd": 0, "max_ult_cd": 800},
            "blue": {"team": "blue", "x": self.width - 35, "y": self.height - 40, "dir": -1, "color": "#3498DB",
                     "hp": b_hp, "mana": b_mana, "age": b_age, "tower": b_tower, "xp": b_xp, "summon_cd": 0,
                     "ult_cd": 0, "max_ult_cd": 800}
        }

        self.tower_cds = {"red": 0, "blue": 0}
        self.red_wins = self.app.db.get_highscore("red_wins") if self.app else 0
        self.blue_wins = self.app.db.get_highscore("blue_wins") if self.app else 0
        self.game_over_flag = False

    def save_state_to_db(self):
        if not self.app:
            return
        r, b = self.bases["red"], self.bases["blue"]
        self.app.db.save_aow_state(r["hp"], r["mana"], r["age"], r["tower"], r["xp"],
                                    b["hp"], b["mana"], b["age"], b["tower"], b["xp"])

    def add_xp(self, team, amount):
        base = self.bases[team]
        if base["age"] >= 4:
            return
        base["xp"] += amount
        req_xp = base["age"] * 50
        if base["xp"] >= req_xp:
            base["xp"] -= req_xp
            base["age"] += 1
            base["hp"] += AGE_DATA[base["age"]]["base_hp"] * 0.5
            self.effects.append({"x": base["x"], "y": base["y"]-80,
                                 "text": f"LÊN ĐỜI {AGE_DATA[base['age']]['name'].upper()}!", "life": 80,
                                 "color": "#FFD700", "size": 20})

    def update(self):
        if not self.active:
            return
        self.canvas.delete("all")
        self.canvas.create_rectangle(0, 0, self.width, self.height, fill="#87CEEB", outline="")
        self.canvas.create_rectangle(0, self.height - 30, self.width, self.height, fill="#27AE60", outline="")
        for i in range(0, self.width, 25):
            self.canvas.create_rectangle(i, self.height - 32, i+6, self.height - 30, fill="#229954", outline="")

        self.frame_count += 1
        if not self.game_over_flag:
            self.handle_ai_and_mana()
            self.handle_towers()
            self.handle_logic()

        for c in self.clouds:
            c["x"] -= c["speed"]
            if c["x"] < -40:
                c["x"] = self.width + 40
                c["y"] = random.randint(10, 60)
        for k in self.base_shake:
            if self.base_shake[k] > 0: self.base_shake[k] -= 1

        self.update_physics()
        self.draw_world()
        self.check_win()

        self.save_timer += 1
        if self.save_timer > 50:
            self.save_state_to_db()
            self.save_timer = 0

        self.after_id = self.canvas.after(40, self.update)

    def handle_ai_and_mana(self):
        for team, base in self.bases.items():
            base["mana"] += 0.5 * base["age"]
            if base["summon_cd"] > 0:
                base["summon_cd"] -= 1
            if base["ult_cd"] < base["max_ult_cd"]:
                base["ult_cd"] += 1

            if base["summon_cd"] <= 0:
                enemy_team = "blue" if team == "red" else "red"
                enemies = [u for u in self.units if u.team == enemy_team]
                allies = [u for u in self.units if u.team == team]

                # Kỹ Năng Tối Thượng (Lật kèo)
                max_hp = AGE_DATA[base["age"]]["base_hp"]
                if base["ult_cd"] >= base["max_ult_cd"] and (base["hp"] < max_hp * 0.4 or len(enemies) >= 4):
                    self.cast_ultimate(team, base["age"])
                    base["ult_cd"] = 0

                closest_dist = 999
                for e in enemies:
                    d = abs(base["x"] - e.x)
                    if d < closest_dist:
                        closest_dist = d

                mana, tower_lvl, age_lvl = base["mana"], base["tower"], base["age"]
                tower_cost = TOWER_DATA[tower_lvl]["cost"] * age_lvl if tower_lvl < 4 else 99999

                if closest_dist > 120 and mana >= tower_cost and tower_lvl < 4:
                    base["tower"] += 1
                    base["mana"] -= tower_cost
                    self.effects.append({"x": base["x"], "y": base["y"]-70,
                                         "text": "NÂNG CẤP TRỤ!", "life": 50,
                                         "color": "#2ECC71", "size": 14})
                    continue

                if not any(u.type == "tank" for u in allies) and mana >= UNIT_BASE["tank"]["cost"]:
                    self.spawn_unit(team, "tank")
                    continue
                if len(enemies) >= 3 and mana >= UNIT_BASE["mage"]["cost"]:
                    self.spawn_unit(team, "mage")
                    continue
                if closest_dist < 80 and mana >= UNIT_BASE["sword"]["cost"]:
                    self.spawn_unit(team, "sword")
                    continue
                if mana >= 60:
                    options = [k for k, v in UNIT_BASE.items() if mana >= v["cost"]]
                    if options:
                        self.spawn_unit(team, random.choice(options))

    def spawn_unit(self, team, u_type):
        base = self.bases[team]
        mult = AGE_DATA[base["age"]]["mult"]
        stats = UNIT_BASE[u_type]
        base["mana"] -= stats["cost"]
        base["summon_cd"] = 30
        UnitClass = UNIT_CLASSES[u_type]
        self.units.append(UnitClass(team, u_type, base["age"], base["x"] + base["dir"]*25, self.height - 30, stats, mult))

    def cast_ultimate(self, team, age):
        base = self.bases[team]
        enemy_team = "blue" if team == "red" else "red"
        mult = AGE_DATA[age]["mult"]
        
        if age == 1:
            self.effects.append({"x": self.width/2, "y": self.height/2, "text": "🔥 MƯA THIÊN THẠCH!", "life": 50, "color": "#FF4500", "size": 18})
            for u in self.units:
                if u.team == enemy_team:
                    u.hp -= 80 * mult
                    self.effects.append({"x": u.x, "y": u.y, "life": 20, "radius": 25, "type": "explosion"})
        elif age == 2:
            self.effects.append({"x": self.width/2, "y": self.height/2, "text": "✨ ÁNH SÁNG THÁNH THẦN!", "life": 50, "color": "#FFD700", "size": 18})
            heal_amount = AGE_DATA[age]["base_hp"] * 0.3
            base["hp"] = min(AGE_DATA[age]["base_hp"], base["hp"] + heal_amount)
            self.effects.append({"x": base["x"], "y": base["y"]-80, "text": f"+{int(heal_amount)}", "life": 30, "color": "#2ECC71", "size": 14})
            for u in self.units:
                if u.team == team:
                    u.hp = min(u.max_hp, u.hp + 80 * mult)
                    self.effects.append({"x": u.x, "y": u.y-20, "text": "+HP", "life": 20, "color": "#2ECC71", "size": 10})
        elif age == 3:
            self.effects.append({"x": self.width/2, "y": self.height/2, "text": "✈️ KHÔNG KÍCH!", "life": 50, "color": "#FFFFFF", "size": 18})
            for i in range(6):
                ex = random.randint(30, self.width-30)
                self.effects.append({"x": ex, "y": self.height-30, "life": 30, "radius": 40, "type": "explosion"})
            for u in self.units:
                if u.team == enemy_team:
                    u.hp -= 150 * mult
        elif age == 4:
            self.effects.append({"x": self.width/2, "y": self.height/2, "text": "🛰️ HỦY DIỆT VỆ TINH!", "life": 50, "color": "#00FFFF", "size": 18})
            self.effects.append({"x": self.width/2, "y": self.height/2, "life": 15, "type": "orbital_laser", "team": team})
            for u in self.units:
                if u.team == enemy_team:
                    u.hp -= 500 * mult
            self.bases[enemy_team]["hp"] -= AGE_DATA[4]["base_hp"] * 0.15 # 15% damage to enemy base
            self.base_shake[enemy_team] = 20

    def handle_towers(self):
        for team, base in self.bases.items():
            t_lvl = base["tower"]
            if t_lvl == 0 or base["hp"] <= 0:
                continue
            if self.tower_cds[team] > 0:
                self.tower_cds[team] -= 1
                continue

            tower_stats = TOWER_DATA[t_lvl]
            mult = AGE_DATA[base["age"]]["mult"]
            enemy_team = "blue" if team == "red" else "red"
            enemies = [e for e in self.units if e.team == enemy_team]
            target, min_d = None, tower_stats["range"]
            for e in enemies:
                d = abs(base["x"] - e.x)
                if d <= min_d:
                    min_d, target = d, e
            if target:
                self.projectiles.append({
                    "x": base["x"] + base["dir"]*15, "y": base["y"] - 40,
                    "vx": base["dir"] * 10, "team": team,
                    "dmg": tower_stats["dmg"] * mult, "aoe": (t_lvl >= 3),
                    "is_tower": True, "age": base["age"],
                    "target_y": target.y - 10
                })
                self.tower_cds[team] = tower_stats["cd"]

    def handle_logic(self):
        for u in self.units:
            enemy_team = "blue" if u.team == "red" else "red"
            enemy_base = self.bases[enemy_team]
            enemies = [e for e in self.units if e.team == enemy_team]

            closest, min_dist = enemy_base, abs(u.x - enemy_base["x"])
            for e in enemies:
                d = abs(u.x - e.x)
                if d < min_dist:
                    min_dist, closest = d, e

            if min_dist <= u.range:
                u.action = "attack"
                if u.cd <= 0:
                    u.cd = u.max_cd
                    if u.type in ["sword", "tank", "assa"]:
                        if type(closest) is dict:
                            closest["hp"] -= u.dmg
                            cx, cy = closest["x"], closest["y"]
                            if closest == enemy_base:
                                self.add_xp(u.team, 4)
                                self.add_xp(enemy_team, 7)
                        else:
                            closest.hp -= u.dmg
                            cx, cy = closest.x, closest.y
                            
                        self.effects.append({"x": cx + random.randint(-5, 5), "y": cy-20,
                                             "text": f"-{int(u.dmg)}", "life": 20,
                                             "color": "#FFFFFF", "size": 11, "type": "hit_spark"})
                    else:
                        self.projectiles.append({
                            "x": u.x, "y": u.y-15,
                            "vx": (1 if u.team == "red" else -1)*8,
                            "team": u.team, "dmg": u.dmg,
                            "aoe": UNIT_BASE[u.type].get("aoe", False),
                            "age": u.age,
                            "target_y": (closest["y"] if type(closest) is dict else closest.y) - 10
                        })
                else:
                    u.cd -= 1
            else:
                u.action = "walk"
                u.x += (1 if u.team == "red" else -1) * u.speed
                if u.cd > 0:
                    u.cd -= 1

    def update_physics(self):
        alive = []
        for u in self.units:
            if u.hp > 0:
                alive.append(u)
            else:
                killer = "blue" if u.team == "red" else "red"
                self.add_xp(killer, 5)
                self.bases[killer]["mana"] += 10
                self.effects.append({"x": u.x, "y": u.y-20, "text": "+10 💧", "life": 30, "color": "#3498DB", "size": 10})
        self.units = alive

        for proj in self.projectiles[:]:
            proj["x"] += proj["vx"]
            hit = False
            enemy_team = "blue" if proj["team"] == "red" else "red"
            enemy_base = self.bases[enemy_team]

            if abs(proj["x"] - enemy_base["x"]) < 25:
                enemy_base["hp"] -= proj["dmg"]
                self.add_xp(proj["team"], 4)
                self.add_xp(enemy_team, 7)
                self.base_shake[enemy_team] = 8 # Rung màn hình khi nhà bị bắn
                self.effects.append({"x": proj["x"], "y": enemy_base["y"]-30,
                                     "text": f"-{int(proj['dmg'])}", "life": 20,
                                     "color": "yellow", "size": 14, "type": "hit_spark"})
                hit = True

            if not hit:
                for e in self.units:
                    if e.team == enemy_team and abs(proj["x"] - e.x) < 15:
                        hit = True
                        if proj.get("aoe"):
                            for target in self.units:
                                self.effects.append({"x": proj["x"], "y": proj.get("target_y", e.y-15), "life": 15, "radius": 20, "type": "explosion"})
                                if target.team == enemy_team and abs(proj["x"] - target.x) < 40:
                                    target.hp -= proj["dmg"]
                                    self.effects.append({"x": target.x, "y": target.y-15,
                                                         "text": f"-{int(proj['dmg'])}", "life": 15,
                                                         "color": "#FFA500", "size": 10})
                        else:
                            e.hp -= proj["dmg"]
                            self.effects.append({"x": e.x, "y": e.y-15,
                                                 "text": f"-{int(proj['dmg'])}", "life": 15,
                                                 "color": "white", "size": 10, "type": "hit_spark"})
                        break
            if hit or proj["x"] < 0 or proj["x"] > self.width:
                self.projectiles.remove(proj)

        for e in self.effects[:]:
            e["life"] -= 1
            if e.get("type") != "explosion":
                e["y"] -= 1
            if e["life"] <= 0:
                self.effects.remove(e)

    def draw_world(self):
        self.draw_background()
        for u in self.units:
            u.draw(self.canvas, self.frame_count)

        for name, b in self.bases.items():
            self.draw_base(b)

        self.draw_projectiles()
        self.draw_effects()
        self.draw_ui()

    def draw_ui(self):
        # Top bar background
        self.canvas.create_rectangle(0, 0, self.width, 48, fill="#1C2833", outline="")
        self.canvas.create_line(0, 48, self.width, 48, fill="#34495E")
        
        r, b = self.bases["red"], self.bases["blue"]
        
        # Red (Player) UI - Góc trái (Chia 2 dòng cho gọn)
        r_name = AGE_DATA[r['age']]['name']
        self.canvas.create_text(8, 12, text=f"🏛️ {r_name}  🏹 {r['tower']}", anchor="w", fill="#E74C3C", font=("Segoe UI", 9, "bold"))
        self.canvas.create_text(8, 28, text=f"💧 {int(r['mana'])}  ⭐ {r['xp']}/{r['age']*50}", anchor="w", fill="white", font=("Segoe UI", 9))

        # Blue (AI) UI - Góc phải
        b_name = AGE_DATA[b['age']]['name']
        self.canvas.create_text(self.width - 8, 12, text=f"🏹 {b['tower']}  🏛️ {b_name}", anchor="e", fill="#3498DB", font=("Segoe UI", 9, "bold"))
        self.canvas.create_text(self.width - 8, 28, text=f"💧 {int(b['mana'])}", anchor="e", fill="white", font=("Segoe UI", 9))

        # Tỉ số (Wins) - Ở giữa
        self.canvas.create_text(self.width/2, 20, text=f"{self.red_wins} - {self.blue_wins}", fill="#FFD700", font=("Segoe UI", 16, "bold"))
        
        # Thanh XP mỏng ở mép dưới của top bar (tiết kiệm diện tích)
        xp_req = r['age'] * 50
        xp_ratio = min(1.0, r['xp'] / xp_req) if xp_req > 0 else 1.0
        self.canvas.create_rectangle(0, 38, self.width, 41, fill="#4A235A", outline="")
        self.canvas.create_rectangle(0, 38, self.width * xp_ratio, 41, fill="#F1C40F", outline="")

    def draw_background(self):
        # Retro 8-bit sky gradient
        self.canvas.create_rectangle(0, 0, self.width, 50, fill="#191970", outline="")
        self.canvas.create_rectangle(0, 50, self.width, 100, fill="#00008B", outline="")
        self.canvas.create_rectangle(0, 100, self.width, self.height, fill="#4169E1", outline="")
        
        # Pixel Sun
        self.canvas.create_rectangle(self.width - 60, 20, self.width - 20, 60, fill="#FFD700", outline="")
        self.canvas.create_rectangle(self.width - 55, 15, self.width - 25, 65, fill="#FFD700", outline="")

        # Clouds
        for c in self.clouds:
            x, y = c["x"], c["y"]
            self.canvas.create_rectangle(x, y, x+30, y+10, fill="#FFFFFF", outline="")
            self.canvas.create_rectangle(x+5, y-5, x+25, y+15, fill="#FFFFFF", outline="")

        # Distant Mountains (Polygons)
        self.canvas.create_polygon(0, self.height-30, 60, self.height-90, 120, self.height-30, fill="#2C3E50", outline="")
        self.canvas.create_polygon(90, self.height-30, 160, self.height-110, 230, self.height-30, fill="#34495E", outline="")
        self.canvas.create_polygon(210, self.height-30, 290, self.height-80, 370, self.height-30, fill="#2C3E50", outline="")
        self.canvas.create_polygon(340, self.height-30, 420, self.height-100, 500, self.height-30, fill="#34495E", outline="")

        # Ground & Pixel Grass
        self.canvas.create_rectangle(0, self.height - 30, self.width, self.height, fill="#27AE60", outline="")
        for i in range(10, self.width, 20):
            self.canvas.create_rectangle(i, self.height - 30, i+3, self.height - 26, fill="#2ECC71", outline="")
            self.canvas.create_rectangle(i+5, self.height - 30, i+8, self.height - 28, fill="#2ECC71", outline="")

    def draw_base(self, b):
        # Screen Shake (Rung lắc nhà)
        shake = self.base_shake["red" if b["dir"] == 1 else "blue"]
        sx, sy = random.randint(-shake, shake), random.randint(-shake, shake)
        age, x, y, dir = b["age"], b["x"] + sx, b["y"] + sy, b["dir"]
        
        if b["hp"] <= 0:
            self.canvas.create_rectangle(x-25, y+15, x+25, y+30, fill="#7F8C8D", outline="black")
            self.canvas.create_rectangle(x-15, y, x, y+15, fill="#7F8C8D", outline="black")
            return
        
        if age == 1:
            self.canvas.create_oval(x-35, y-20, x+35, y+10, fill="#5C4033", outline="black")
            self.canvas.create_oval(x-20, y-35, x+20, y, fill="#8B4513", outline="black")
            self.canvas.create_arc(x-15, y-5, x+15, y+15, start=0, extent=180, fill="#000000", outline="")
        elif age == 2:
            self.canvas.create_rectangle(x-30, y-10, x+30, y+10, fill="#7F8C8D", outline="black")
            self.canvas.create_rectangle(x-20, y-30, x+20, y-10, fill="#95A5A6", outline="black")
            for i in range(-25, 26, 12):
                self.canvas.create_rectangle(x+i-4, y-38, x+i+4, y-30, fill="#95A5A6", outline="black")
            self.canvas.create_arc(x-12, y-10, x+12, y+20, start=0, extent=180, fill="#3E2723", outline="black")
            self.canvas.create_line(x-dir*10, y-38, x-dir*10, y-55, fill="black", width=2)
            self.canvas.create_polygon(x-dir*10, y-55, x-dir*10+dir*12, y-50, x-dir*10, y-45, fill=b["color"], outline="black")
        elif age == 3:
            self.canvas.create_polygon(x-35, y+10, x-25, y-15, x+25, y-15, x+35, y+10, fill="#2E4053", outline="black")
            self.canvas.create_rectangle(x-15, y-25, x+15, y-15, fill="#1B2631", outline="black")
            rx, ry = x - dir*10, y-25
            self.canvas.create_line(rx, ry, rx, ry-10, fill="gray", width=2)
            rw = 8 * math.cos(self.frame_count * 0.15)
            self.canvas.create_oval(rx-8, ry-15, rx+8, ry-5, fill="#7F8C8D", outline="black")
            self.canvas.create_line(rx, ry-10, rx+rw, ry-15, fill="#2ECC71", width=2)
        else:
            glow = "#00FFFF" if b["team"] == "blue" else "#FF4500"
            y_float = y - 5 + math.sin(self.frame_count * 0.1) * 3
            self.canvas.create_polygon(x, y_float-35, x+25, y_float+5, x-25, y_float+5, fill="#17202A", outline=glow, width=2)
            self.canvas.create_polygon(x, y_float-20, x+15, y_float, x-15, y_float, fill="#212F3C", outline=glow)
            self.canvas.create_oval(x-6, y_float-10, x+6, y_float+2, fill="#FDFEFE", outline=glow, width=2)
            self.canvas.create_line(x, y_float+5, x, y+10, fill=glow, width=4, dash=(4,2))
            self.canvas.create_oval(x-15, y+5, x+15, y+15, outline=glow, fill="")

        if b["tower"] > 0:
            t_color = TOWER_DATA[b["tower"]].get("color", "#FFF")
            if age == 1: tx, ty = x + dir*15, y-25
            elif age == 2: tx, ty = x + dir*25, y-20
            elif age == 3: tx, ty = x + dir*20, y-10
            elif age == 4: tx, ty = x + dir*25, y-20
            self.canvas.create_rectangle(tx-6, ty-8, tx+6, ty+8, fill="#555555", outline="black")
            self.canvas.create_rectangle(tx-8, ty-12, tx+8, ty-8, fill=t_color, outline="black")
            self.canvas.create_rectangle(tx, ty-11, tx+dir*12, ty-8, fill="black", outline="")

        max_hp = AGE_DATA[age]["base_hp"]
        hp_ratio = max(0, b["hp"] / max_hp)
        self.canvas.create_rectangle(x-30, y-60, x+30, y-55, fill="#000000", outline="")
        self.canvas.create_rectangle(x-30, y-60, x-30 + int(60 * hp_ratio), y-55, fill="#32CD32", outline="")

    def draw_projectiles(self):
        for proj in self.projectiles:
            age = proj.get("age", 1)
            x, y = proj["x"], proj["y"]
            
            if proj.get("is_tower"):
                color = TOWER_DATA.get(self.bases[proj["team"]]["tower"], {}).get("color", "#FFF")
                self.canvas.create_rectangle(x-3, y-3, x+3, y+3, fill=color, outline="")
            elif age == 1 or age == 2:
                dir = proj["vx"] / abs(proj["vx"])
                self.canvas.create_rectangle(x-4, y-1, x+4, y+1, fill="#8B4513", outline="")
                self.canvas.create_rectangle(x+dir*4, y-2, x+dir*6, y+2, fill="#FFFFFF", outline="")
            elif age == 3:
                self.canvas.create_rectangle(x-2, y-2, x+2, y+2, fill="#FFD700", outline="")
            else:
                self.canvas.create_rectangle(x-6, y-1, x+6, y+1, fill="#00FFFF", outline="")

    def draw_effects(self):
        for e in self.effects:
            if e.get("type") == "hit_spark":
                x, y, life = e["x"], e["y"], e["life"]
                if life > 10:
                    self.canvas.create_text(x, y, text=e["text"], fill=e["color"], font=("Courier", e["size"], "bold"))
                    for i in range(4):
                        angle = i * math.pi / 2
                        l = (20 - life) * 0.5
                        self.canvas.create_line(x, y, x + math.cos(angle)*l, y + math.sin(angle)*l, fill="white", width=1)
            elif e.get("type") == "explosion":
                radius = e["radius"] * (1 - e["life"]/15)
                color = random.choice(["#FFA500", "#FF4500", "#FFD700"])
                self.canvas.create_oval(e["x"]-radius, e["y"]-radius, e["x"]+radius, e["y"]+radius, fill=color, outline="")
            elif e.get("type") == "orbital_laser":
                c = "#00FFFF" if e["team"] == "blue" else "#FF4500"
                if e["life"] % 4 > 1:
                    self.canvas.create_rectangle(0, self.height - 80, self.width, self.height, fill=c, outline="")
                    self.canvas.create_rectangle(0, self.height - 60, self.width, self.height, fill="#FFFFFF", outline="")
            else:
                self.canvas.create_text(e["x"], e["y"], text=e["text"], fill=e["color"], font=("Courier", e["size"], "bold"))

    def check_win(self):
        if self.game_over_flag:
            return
        if self.bases["red"]["hp"] <= 0 or self.bases["blue"]["hp"] <= 0:
            self.game_over_flag = True
            if self.bases["red"]["hp"] <= 0:
                winner = "XANH THẮNG!"
                if self.app:
                    self.blue_wins = self.app.db.increment_score("blue_wins")
            else:
                winner = "ĐỎ THẮNG!"
                if self.app:
                    self.red_wins = self.app.db.increment_score("red_wins")
            self.effects.append({"x": self.width/2, "y": self.height/2, "text": winner, "life": 90, 
                                 "color": "#FFD700", "size": 30})
            self.canvas.after(3000, lambda: self.reset(full_reset=True))

# ===================== ỨNG DỤNG ĐỒNG HỒ + BÁO THỨC (GIAO DIỆN LỚN HƠN) =====================
class StudyTimer:
    def __init__(self, root):
        self.root = root
        self.root.title("⏳ Study Timer Premium - Relax & Focus")
        self.root.geometry("1000x700")
        self.bg_color = "#0F172A"       # Zinc-900 / Slate-900
        self.frame_bg = "#1E293B"       # Slate-800
        self.card_bg = "#334155"        # Slate-700
        self.green_accent = "#10B981"   # Emerald-500
        self.red_accent = "#F43F5E"     # Rose-500
        self.text_color = "#F8FAFC"     # Slate-50
        self.sub_color = "#94A3B8"      # Slate-400
        self.root.configure(bg=self.bg_color)
        self.root.minsize(900, 650)
        self.root.resizable(True, True)

        self.db = DBManager()

        self.study_time = 25 * 60
        self.short_break = 5 * 60
        self.long_break = 15 * 60
        self.current_time_left = self.study_time
        self.current_total_time = self.study_time
        self.end_time = 0
        self.is_running = False
        self.is_paused = False
        self.is_study = True
        self.pomodoro_count = 0
        self.after_id = None
        self.last_tick_time = 0

        # Báo thức
        self.alarm_time = None
        self.alarm_active = False
        self.alarm_after_id = None

        self.current_game = None
        self.game_map = {}

        self.build_ui()
        self.switch_game("space_shooter")
        self.update_timer_display()
        self.start_alarm_check()
        
        # Bắt sự kiện khi nhấn nút [X] đóng cửa sổ
        self.root.protocol('WM_DELETE_WINDOW', self.hide_window)

    def build_ui(self):
        # Tối ưu giao diện (Style) cho các phần tử ttk
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TCombobox", fieldbackground=self.card_bg, background=self.card_bg, foreground=self.text_color, arrowcolor=self.text_color, borderwidth=0, lightcolor=self.card_bg, darkcolor=self.card_bg)

        # Top taskbar
        top_bar = ctk.CTkFrame(self.root, fg_color=self.frame_bg, corner_radius=0, height=60)
        top_bar.pack(fill=tk.X, side=tk.TOP, pady=(0, 20))
        
        title_label = ctk.CTkLabel(top_bar, text="⏳ Study Timer Premium", font=("Segoe UI", 20, "bold"), text_color=self.text_color)
        title_label.pack(side=tk.LEFT, padx=20, pady=15)
        
        self.mini_btn = ctk.CTkButton(top_bar, text="⛶ Thu Gọn", font=("Segoe UI", 12, "bold"), fg_color=self.card_bg, text_color=self.text_color, hover_color="#475569", width=80, height=30, corner_radius=10, command=self.toggle_mini_mode)
        self.mini_btn.pack(side=tk.LEFT, padx=10, pady=15)
        
        total, streak, _ = self.db.get_stats()
        self.stats_label = ctk.CTkLabel(top_bar, text=f"🔥 Chuỗi: {streak} ngày   •   📚 Tổng: {total} phiên", font=("Segoe UI", 14, "bold"), text_color="#F59E0B")
        self.stats_label.pack(side=tk.RIGHT, padx=20, pady=15)

        # Main container (dưới taskbar)
        main_container = ctk.CTkFrame(self.root, fg_color=self.bg_color, corner_radius=0)
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))

        # --- BẢNG BÊN TRÁI (TIMER) ---
        left_panel = ctk.CTkFrame(main_container, fg_color=self.frame_bg, corner_radius=20, width=350)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, expand=False, padx=(0, 20))
        left_panel.pack_propagate(False)

        # Vòng tròn đồng hồ hiện đại
        self.canvas = tk.Canvas(left_panel, width=280, height=280, bg=self.frame_bg, highlightthickness=0)
        self.canvas.pack(pady=(30, 10))
        self.canvas.create_oval(10, 10, 270, 270, outline=self.card_bg, width=12)
        self.progress_arc = self.canvas.create_arc(10, 10, 270, 270, start=90, extent=-360, outline=self.green_accent, width=12, style=tk.ARC)
        self.timer_text = self.canvas.create_text(140, 120, text="25:00", font=("Segoe UI", 50, "bold"), fill=self.text_color)
        self.status_text = self.canvas.create_text(140, 175, text="HỌC TẬP", font=("Segoe UI", 16, "bold"), fill=self.green_accent)
        self.count_text = self.canvas.create_text(140, 210, text="🍅 x 0", font=("Segoe UI", 13), fill=self.sub_color)

        self.notif_label = ctk.CTkLabel(left_panel, text="Sẵn sàng để bắt đầu!", font=("Segoe UI", 14, "italic"), text_color="#38BDF8")
        self.notif_label.pack(pady=(0, 20))

        # Khu vực nút bấm
        btn_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        btn_frame.pack(pady=5)
        
        self.start_pause_btn = ctk.CTkButton(btn_frame, text="▶ BẮT ĐẦU", font=("Segoe UI", 16, "bold"), fg_color=self.green_accent, text_color="#000000", hover_color="#059669", width=220, height=50, corner_radius=25, command=self.start_pause)
        self.start_pause_btn.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        self.reset_btn = ctk.CTkButton(btn_frame, text="↺ Đặt Lại", font=("Segoe UI", 14, "bold"), fg_color=self.card_bg, text_color=self.text_color, hover_color="#475569", width=105, height=40, corner_radius=10, command=self.reset)
        self.reset_btn.grid(row=1, column=0, padx=5)
        
        self.skip_btn = ctk.CTkButton(btn_frame, text="⏭ Bỏ Qua", font=("Segoe UI", 14, "bold"), fg_color=self.card_bg, text_color=self.text_color, hover_color="#475569", width=105, height=40, corner_radius=10, command=self.skip)
        self.skip_btn.grid(row=1, column=1, padx=5)

        # --- BẢNG BÊN PHẢI ---
        right_panel = ctk.CTkFrame(main_container, fg_color="transparent")
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Card 1: Gộp Settings & Alarm nằm ngang để tối ưu khoảng trống
        top_right_card = ctk.CTkFrame(right_panel, fg_color=self.frame_bg, corner_radius=20)
        top_right_card.pack(fill=tk.X, pady=(0, 15), ipadx=10, ipady=10)
        
        grid_container = ctk.CTkFrame(top_right_card, fg_color="transparent")
        grid_container.pack(fill=tk.X, padx=10, pady=5)
        
        settings_frame = ctk.CTkFrame(grid_container, fg_color="transparent")
        settings_frame.pack(side=tk.LEFT, fill=tk.Y, expand=True)
        ctk.CTkLabel(settings_frame, text="⚙️ CÀI ĐẶT THỜI GIAN", font=("Segoe UI", 14, "bold"), text_color=self.text_color).pack(anchor="w", padx=10, pady=(5, 10))
        
        set_grid = ctk.CTkFrame(settings_frame, fg_color="transparent")
        set_grid.pack(fill=tk.X)
        fields = [("📚 Học", "study", 25), ("☕ Ngắn", "short_break", 5), ("😴 Dài", "long_break", 15)]
        for i, (label_text, attr, default) in enumerate(fields):
            ctk.CTkLabel(set_grid, text=label_text, font=("Segoe UI", 12, "bold"), text_color=self.sub_color).grid(row=0, column=i, padx=5)
            entry = ctk.CTkEntry(set_grid, font=("Segoe UI", 16, "bold"), fg_color=self.card_bg, text_color=self.text_color, border_width=0, width=55, justify=tk.CENTER, corner_radius=10)
            entry.insert(0, str(default))
            entry.grid(row=1, column=i, padx=5, pady=(5, 5))
            setattr(self, f"{attr}_entry", entry)
            
        self.apply_btn = ctk.CTkButton(settings_frame, text="✓ LƯU", font=("Segoe UI", 12, "bold"), fg_color=self.card_bg, text_color=self.green_accent, hover_color="#475569", corner_radius=10, command=self.apply_settings, height=30)
        self.apply_btn.pack(fill=tk.X, padx=10, pady=(10, 5))
        
        ctk.CTkFrame(grid_container, width=2, fg_color=self.card_bg).pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

        alarm_frame = ctk.CTkFrame(grid_container, fg_color="transparent")
        alarm_frame.pack(side=tk.RIGHT, fill=tk.Y, expand=True)
        ctk.CTkLabel(alarm_frame, text="⏰ BÁO THỨC", font=("Segoe UI", 14, "bold"), text_color=self.text_color).pack(anchor="w", padx=10, pady=(5, 10))
        
        spin_frame = ctk.CTkFrame(alarm_frame, fg_color="transparent")
        spin_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.alarm_hour_var = tk.StringVar(value="07")
        self.alarm_min_var = tk.StringVar(value="00")
        
        hours = [f"{i:02d}" for i in range(24)]
        mins = [f"{i:02d}" for i in range(60)]
        
        self.hour_menu = ctk.CTkOptionMenu(spin_frame, values=hours, variable=self.alarm_hour_var, width=55, font=("Segoe UI", 14, "bold"), fg_color=self.card_bg, button_color=self.card_bg, dropdown_fg_color=self.card_bg)
        self.hour_menu.pack(side=tk.LEFT, padx=(10, 2))
        
        ctk.CTkLabel(spin_frame, text=":", font=("Segoe UI", 16, "bold"), text_color=self.text_color).pack(side=tk.LEFT, padx=5)
        
        self.min_menu = ctk.CTkOptionMenu(spin_frame, values=mins, variable=self.alarm_min_var, width=55, font=("Segoe UI", 14, "bold"), fg_color=self.card_bg, button_color=self.card_bg, dropdown_fg_color=self.card_bg)
        self.min_menu.pack(side=tk.LEFT, padx=(2, 10))
        
        self.alarm_btn = ctk.CTkButton(alarm_frame, text="BẬT BÁO THỨC", font=("Segoe UI", 12, "bold"), fg_color=self.card_bg, text_color=self.text_color, hover_color="#475569", corner_radius=10, command=self.toggle_alarm, height=30)
        self.alarm_btn.pack(fill=tk.X, padx=10, pady=(10, 5))
        
        self.alarm_status_label = ctk.CTkLabel(alarm_frame, text="Báo thức đang tắt", font=("Segoe UI", 12, "italic"), text_color=self.sub_color)
        self.alarm_status_label.pack(pady=(0, 5))

        # Card 3: Game
        game_card = ctk.CTkFrame(right_panel, fg_color=self.frame_bg, corner_radius=20)
        game_card.pack(fill=tk.BOTH, expand=True)
        
        game_top = ctk.CTkFrame(game_card, fg_color="transparent")
        game_top.pack(fill=tk.X, padx=20, pady=(15, 10))
        ctk.CTkLabel(game_top, text="🎮 CHILL MINI GAME", font=("Segoe UI", 14, "bold"), text_color=self.text_color).pack(side=tk.LEFT)
        
        self.game_var = tk.StringVar(value="space_shooter")
        games = ["space_shooter", "age_of_war", "dino_runner", "auto_pong"]
        game_combo = ctk.CTkOptionMenu(game_top, values=games, variable=self.game_var, font=("Segoe UI", 13, "bold"), fg_color=self.card_bg, button_color=self.card_bg, dropdown_fg_color=self.card_bg, width=150, command=self.switch_game)
        game_combo.pack(side=tk.RIGHT)

        gc_container = ctk.CTkFrame(game_card, fg_color=self.card_bg, corner_radius=10)
        gc_container.pack(expand=True, fill=tk.BOTH, padx=20, pady=(0, 10))
        self.game_canvas = tk.Canvas(gc_container, width=520, height=320, bg="#0B0C10", highlightthickness=0, bd=0)
        self.game_canvas.pack(expand=True)  # Không dùng fill=BOTH để giữ cố định size tỷ lệ chuẩn, ép ra giữa

        ctk.CTkLabel(game_card, text="Nhìn game tự chơi để mắt được nghỉ ngơi nhé 👀", font=("Segoe UI", 12, "italic"), text_color=self.sub_color).pack(pady=(5, 5))
        
        if HAS_SYSTRAY:
            ctk.CTkLabel(game_card, text="💡 Bấm (X) thu nhỏ để chạy ngầm ở System Tray", font=("Segoe UI", 11), text_color="#38BDF8").pack(side=tk.BOTTOM, pady=(0, 15))

    # ==================== MINI MODE (GÓC MÀN HÌNH) ====================
    def toggle_mini_mode(self):
        self.root.withdraw() # Ẩn cửa sổ chính
        self.mini_window = ctk.CTkToplevel(self.root)
        self.mini_window.title("Mini Timer")

        # Đặt cửa sổ ở góc dưới cùng bên phải
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = screen_width - 260
        y = screen_height - 160
        self.mini_window.geometry(f"240x110+{x}+{y}")
        self.mini_window.attributes('-topmost', True) # Luôn nổi trên cùng
        self.mini_window.resizable(False, False)
        self.mini_window.configure(fg_color=self.bg_color)
        self.mini_window.protocol("WM_DELETE_WINDOW", self.restore_main_window)

        flip_frame = ctk.CTkFrame(self.mini_window, fg_color=self.frame_bg, corner_radius=15)
        flip_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.mini_status_label = ctk.CTkLabel(flip_frame, text="HỌC TẬP", font=("Segoe UI", 12, "bold"), text_color=self.green_accent)
        self.mini_status_label.pack(pady=(5, 0))

        # Khung đồng hồ mô phỏng phong cách tối giản / lật giấy
        time_container = ctk.CTkFrame(flip_frame, fg_color="#000000", corner_radius=8)
        time_container.pack(pady=(5, 5), padx=15, fill=tk.X)

        self.mini_time_label = ctk.CTkLabel(time_container, text="25:00", font=("Courier", 26, "bold"), text_color="#FFFFFF")
        self.mini_time_label.pack(pady=2)

        btn_frame = ctk.CTkFrame(flip_frame, fg_color="transparent")
        btn_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=(0, 5))

        self.mini_play_btn = ctk.CTkButton(btn_frame, text="⏸" if self.is_running and not self.is_paused else "▶", width=40, height=24, fg_color=self.card_bg, hover_color="#475569", command=self.start_pause)
        self.mini_play_btn.pack(side=tk.LEFT, padx=(15, 5))

        expand_btn = ctk.CTkButton(btn_frame, text="🗖 Phóng to", width=70, height=24, fg_color=self.card_bg, hover_color="#475569", command=self.restore_main_window)
        expand_btn.pack(side=tk.RIGHT, padx=(5, 15))

        self.update_timer_display()

    def restore_main_window(self):
        if hasattr(self, 'mini_window') and self.mini_window:
            self.mini_window.destroy()
            self.mini_window = None
        self.root.deiconify() # Hiện lại cửa sổ chính

    # ==================== SYSTEM TRAY ====================
    def hide_window(self):
        if HAS_SYSTRAY:
            self.root.withdraw() # Ẩn cửa sổ
            image = self.create_image()
            menu = pystray.Menu(
                pystray.MenuItem('Mở Ứng Dụng', self.show_window, default=True),
                pystray.MenuItem('Thoát', self.quit_window)
            )
            self.tray_icon = pystray.Icon("StudyTimer", image, "Study Timer", menu)
            threading.Thread(target=self.tray_icon.run, daemon=True).start()
        else:
            self.quit_window(None, None)

    def show_window(self, icon, item):
        icon.stop()
        self.root.after(0, self.root.deiconify)

    def quit_window(self, icon, item):
        if HAS_SYSTRAY and icon:
            icon.stop()
        self.root.after(0, self.root.destroy)
        os._exit(0)

    def create_image(self):
        image = Image.new('RGB', (64, 64), color=self.bg_color)
        dc = ImageDraw.Draw(image)
        dc.rectangle((16, 16, 48, 48), fill=self.green_accent)
        return image

    # ==================== BÁO THỨC ====================
    def toggle_alarm(self):
        if self.alarm_active:
            self.cancel_alarm()
            return
        try:
            h = int(self.alarm_hour_var.get())
            m = int(self.alarm_min_var.get())
            if 0 <= h <= 23 and 0 <= m <= 59:
                self.alarm_time = (h, m)
                self.alarm_active = True
                self.alarm_btn.configure(text="TẮT", fg_color=self.red_accent, text_color="#FFFFFF", hover_color="#E11D48")
                self.alarm_status_label.configure(text=f"Đã đặt {h:02d}:{m:02d}", text_color=self.green_accent)
                self.show_notification(f"⏰ Báo thức lúc {h:02d}:{m:02d}")
            else:
                self.show_notification("Giờ không hợp lệ!")
        except ValueError:
            self.show_notification("Nhập số giờ/phút hợp lệ!")

    def cancel_alarm(self):
        self.alarm_active = False
        self.alarm_time = None
        self.alarm_btn.configure(text="BẬT", fg_color=self.card_bg, text_color=self.text_color, hover_color="#475569")
        self.alarm_status_label.configure(text="Đang tắt", text_color=self.sub_color)

    def start_alarm_check(self):
        self._check_alarm()
        self.alarm_after_id = self.root.after(1000, self.start_alarm_check)

    def _check_alarm(self):
        if self.alarm_active and self.alarm_time:
            now = datetime.now()
            if now.hour == self.alarm_time[0] and now.minute == self.alarm_time[1]:
                self.trigger_alarm()
                self.cancel_alarm()

    def trigger_alarm(self):
        for _ in range(3):
            try:
                play_beep()
                time.sleep(0.2)
            except:
                pass
        self.show_notification("🔔 ĐẾN GIỜ RỒI! Báo thức đã reo.")
        
        top = ctk.CTkToplevel(self.root)
        top.title("Báo thức")
        top.geometry("300x150")
        top.configure(fg_color=self.frame_bg)
        top.attributes('-alpha', 0.0) # Start fully transparent
        top.attributes('-topmost', True)
        top.transient(self.root)

    # ==================== CÁC HÀM CÒN LẠI (giữ nguyên) ====================
        ctk.CTkLabel(top, text="⏰ ĐÃ ĐẾN GIỜ HẸN!", font=("Segoe UI", 16, "bold"),
                     text_color="#F1C40F").pack(expand=True, padx=20, pady=(20, 10))
        
        ok_button = ctk.CTkButton(top, text="OK", fg_color=self.green_accent, text_color="#000", hover_color="#059669")
        ok_button.pack(pady=(10, 20))
        ok_button.configure(command=lambda: self.fade_out_window(top))

        self.fade_in_window(top)

    def fade_in_window(self, window, step=0.05):
        alpha = window.attributes('-alpha')
        if alpha < 1.0:
            alpha = min(alpha + step, 1.0)
            window.attributes('-alpha', alpha)
            self.root.after(20, lambda: self.fade_in_window(window, step))

    def fade_out_window(self, window, step=0.05):
        alpha = window.attributes('-alpha')
        if alpha > 0.0:
            alpha = max(alpha - step, 0.0)
            window.attributes('-alpha', alpha)
            self.root.after(20, lambda: self.fade_out_window(window, step))
        else:
            window.destroy()

    def update_stats_ui(self):
        total, streak, _ = self.db.get_stats()
        self.stats_label.configure(text=f"🔥 Chuỗi: {streak} ngày   •   📚 Tổng: {total} phiên")

    def init_game(self, game_key):
        if self.current_game:
            if isinstance(self.current_game, AgeOfWarGame):
                self.current_game.save_state_to_db()
            elif isinstance(self.current_game, AutoSpaceShooterGame):
                self.db.save_space_shooter_state(self.current_game.coins, self.current_game.w_lvl, self.current_game.f_lvl, self.current_game.d_lvl, self.current_game.s_lvl)
            self.current_game.stop()
        w, h = 520, 320
        if game_key == "dino_runner":
            game = DinoRunnerGame(self.game_canvas, w, h, self)
        elif game_key == "age_of_war":
            game = AgeOfWarGame(self.game_canvas, w, h, self)
        elif game_key == "auto_pong":
            game = AutoPongGame(self.game_canvas, w, h, self)
        elif game_key == "auto_aoe":
            game = AutoAOEGame(self.game_canvas, w, h, self)
        elif game_key == "space_shooter":
            game = AutoSpaceShooterGame(self.game_canvas, w, h, self)
        else:
            return
        self.game_map[game_key] = game
        self.current_game = game
        if self.is_running and not self.is_paused and self.is_study:
            self.current_game.start()

    def switch_game(self, game_key):
        self.init_game(game_key)

    def draw_progress(self):
        total = self.current_total_time
        extent = -(360 * (self.current_time_left / total)) if total > 0 else 0
        color = self.green_accent if self.is_study else self.red_accent
        self.canvas.itemconfig(self.progress_arc, extent=extent, outline=color)

    def update_timer_display(self):
        current_secs = int(math.ceil(self.current_time_left))
        mins, secs = divmod(current_secs, 60)
        time_str = f"{mins:02d}:{secs:02d}"
        self.canvas.itemconfig(self.timer_text, text=time_str)
        status = "HỌC TẬP" if self.is_study else "NGHỈ NGƠI"
        color = self.green_accent if self.is_study else self.red_accent
        self.canvas.itemconfig(self.status_text, text=status, fill=color)
        self.canvas.itemconfig(self.count_text, text=f"🍅 x {self.pomodoro_count}")
        self.draw_progress()

        # Đồng bộ giao diện của cửa sổ Mini nếu nó đang được mở
        if hasattr(self, 'mini_window') and self.mini_window and self.mini_window.winfo_exists():
            self.mini_time_label.configure(text=time_str)
            self.mini_status_label.configure(text=status, text_color=color)
            self.mini_play_btn.configure(text="⏸" if self.is_running and not self.is_paused else "▶")

    def countdown(self):
        if self.is_running and not self.is_paused:
            time_now = time.time()
            self.current_time_left = max(0, self.end_time - time_now)

            self.update_timer_display()
            if self.current_time_left > 0:
                self.after_id = self.root.after(50, self.countdown)
            else:
                self.timer_finished()

    def play_chime(self):
        try:
            import winsound
            winsound.Beep(880, 200) # Nhịp 1 thấp
            winsound.Beep(1046, 400) # Nhịp 2 cao và dài hơn
        except:
            play_beep()

    def timer_finished(self):
        self.is_running = False
        self.start_pause_btn.configure(text="▶ BẮT ĐẦU", fg_color=self.green_accent, text_color="#000000", hover_color="#059669")
        if self.current_game:
            if isinstance(self.current_game, AgeOfWarGame):
                self.current_game.save_state_to_db()
            elif isinstance(self.current_game, AutoSpaceShooterGame):
                self.db.save_space_shooter_state(self.current_game.coins, self.current_game.w_lvl, self.current_game.f_lvl, self.current_game.d_lvl, self.current_game.s_lvl)
            self.current_game.stop()
        if self.is_study:
            # Phát âm thanh báo hiệu khi vừa hết giờ học ở dưới nền
            threading.Thread(target=self.play_chime, daemon=True).start()
            
            self.pomodoro_count += 1
            self.db.update_session()
            self.update_stats_ui()
            self.update_timer_display()
            if self.pomodoro_count % 4 == 0:
                self.current_time_left = self.long_break
                self.current_total_time = self.long_break
                msg = "🎉 Bạn rất giỏi! Nghỉ dài 15 phút nhé."
            else:
                self.current_time_left = self.short_break
                self.current_total_time = self.short_break
                msg = "✅ Hoàn thành! Nghỉ ngắn 5 phút nào."
            self.is_study = False
        else:
            self.current_time_left = self.study_time
            self.current_total_time = self.study_time
            self.is_study = True
            msg = "📚 Hết giờ nghỉ! Quay lại học thôi."
        self.show_notification(msg)
        self.update_timer_display()

    def show_notification(self, message):
        self.notif_label.configure(text=message, text_color="#38BDF8")
        self.root.after(4000, lambda: self.notif_label.configure(text="Sẵn sàng để bắt đầu!"))

    def start_pause(self):
        if not self.is_running:
            self.is_running = True
            self.is_paused = False
            self.start_pause_btn.configure(text="⏸ TẠM DỪNG", fg_color=self.red_accent, text_color="#FFFFFF", hover_color="#E11D48")
            self.end_time = time.time() + self.current_time_left
            if self.is_study and self.current_game:
                self.current_game.start()
            self.countdown()
        elif self.is_running and not self.is_paused:
            self.is_paused = True
            self.start_pause_btn.configure(text="▶ TIẾP TỤC", fg_color=self.green_accent, text_color="#000000", hover_color="#059669")
            if self.after_id:
                self.root.after_cancel(self.after_id)
            if self.current_game:
                self.current_game.pause()
            self.update_timer_display()
        elif self.is_running and self.is_paused:
            self.is_paused = False
            self.start_pause_btn.configure(text="⏸ TẠM DỪNG", fg_color=self.red_accent, text_color="#FFFFFF", hover_color="#E11D48")
            self.end_time = time.time() + self.current_time_left
            if self.is_study and self.current_game:
                self.current_game.resume()
            self.countdown()

    def reset(self):
        if self.after_id:
            self.root.after_cancel(self.after_id)
        self.is_running = False
        self.is_paused = False
        self.is_study = True
        self.current_time_left = self.study_time
        self.current_total_time = self.study_time
        self.last_tick_time = 0
        self.start_pause_btn.configure(text="▶ BẮT ĐẦU", fg_color=self.green_accent, text_color="#000000", hover_color="#059669")
        if self.current_game:
            if isinstance(self.current_game, AgeOfWarGame):
                self.current_game.save_state_to_db()
            elif isinstance(self.current_game, AutoSpaceShooterGame):
                self.db.save_space_shooter_state(self.current_game.coins, self.current_game.w_lvl, self.current_game.f_lvl, self.current_game.d_lvl, self.current_game.s_lvl)
            self.current_game.stop()
        self.update_timer_display()
        self.show_notification("↺ Đã đặt lại thời gian")

    def skip(self):
        if self.after_id:
            self.root.after_cancel(self.after_id)
        self.is_running = False
        self.is_paused = False
        if self.is_study:
            self.current_time_left = self.short_break
            self.current_total_time = self.short_break
            self.is_study = False
            msg = "⏩ Chuyển sang giờ nghỉ."
        else:
            self.current_time_left = self.study_time
            self.current_total_time = self.study_time
            self.is_study = True
            msg = "⏩ Quay lại học tập."
        self.start_pause_btn.configure(text="▶ BẮT ĐẦU", fg_color=self.green_accent, text_color="#000000", hover_color="#059669")
        if self.current_game:
            if isinstance(self.current_game, AgeOfWarGame):
                self.current_game.save_state_to_db()
            elif isinstance(self.current_game, AutoSpaceShooterGame):
                self.db.save_space_shooter_state(self.current_game.coins, self.current_game.w_lvl, self.current_game.f_lvl, self.current_game.d_lvl, self.current_game.s_lvl)
            self.current_game.stop()
        self.last_tick_time = 0
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
            self.current_total_time = self.study_time
            self.last_tick_time = 0
            self.start_pause_btn.configure(text="▶ BẮT ĐẦU", fg_color=self.green_accent, text_color="#000000", hover_color="#059669")
            if self.current_game:
                if isinstance(self.current_game, AgeOfWarGame):
                    self.current_game.save_state_to_db()
                elif isinstance(self.current_game, AutoSpaceShooterGame):
                    self.db.save_space_shooter_state(self.current_game.coins, self.current_game.w_lvl, self.current_game.f_lvl, self.current_game.d_lvl, self.current_game.s_lvl)
                self.current_game.stop()
            self.update_timer_display()
            self.show_notification("✓ Đã lưu cài đặt mới")
        except ValueError:
            self.show_notification("⚠️ Hãy nhập số phút hợp lệ nhé!")

if __name__ == "__main__":
    import customtkinter as ctk
    ctk.set_appearance_mode("dark")
    root = ctk.CTk()
    app = StudyTimer(root)
    root.mainloop()
    