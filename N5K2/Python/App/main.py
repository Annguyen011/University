import tkinter as tk
from tkinter import ttk
import random
import math
import time
import os
import sqlite3
from datetime import datetime
import sys

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
        cursor.execute("SELECT * FROM stats WHERE id=1")
        if not cursor.fetchone():
            cursor.execute("INSERT INTO stats (id, total_sessions, streak, last_date) VALUES (1, 0, 0, '')")
        cursor.execute("SELECT * FROM aow_save_v3 WHERE id=1")
        if not cursor.fetchone():
            cursor.execute("INSERT INTO aow_save_v3 VALUES (1, 1000, 0, 1, 0, 0, 1000, 0, 1, 0, 0)")
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

# ===================== GAME 3: AQUARIUM =====================
class AquariumGame(MiniGame):
    def __init__(self, canvas, width, height, app):
        super().__init__(canvas, width, height, app)
        self.reset()

    def reset(self):
        self.fishes = [{"x": random.randint(50, self.width - 50),
                        "y": random.randint(30, self.height - 80),
                        "vx": random.uniform(0.5, 1.4) * random.choice([-1, 1]),
                        "vy": random.uniform(-0.2, 0.2),
                        "color": random.choice(["#FF7F50", "#F4D03F", "#5DADE2", "#F369B4", "#82E0AA", "#E67E22"]),
                        "size": random.randint(18, 30),
                        "wiggle": random.uniform(0, 6)} for _ in range(5)]
        self.bubbles = []
        self.anim_time = 0

    def update(self):
        if not self.active:
            return
        self.canvas.delete("all")
        self.anim_time += 0.05
        self.canvas.create_rectangle(0, 0, self.width, self.height, fill="#0A3D6B", outline="")
        self.canvas.create_rectangle(0, self.height - 25, self.width, self.height, fill="#C2A36B", outline="")
        for f in self.fishes:
            f["x"] += f["vx"]
            f["y"] += f["vy"] + math.sin(self.anim_time * 3 + f["wiggle"]) * 0.15
            if f["x"] > self.width - 30 or f["x"] < 30:
                f["vx"] = -f["vx"]
            if f["y"] < 20 or f["y"] > self.height - 50:
                f["vy"] = -f["vy"]
            f["wiggle"] += 0.3
            dir = 1 if f["vx"] > 0 else -1
            s, c, tw = f["size"], f["color"], math.sin(f["wiggle"]) * 5.0
            tx = f["x"] - dir * s * 0.8
            self.canvas.create_polygon(tx, f["y"], tx - dir * s * 0.6, f["y"] - s * 0.45 + tw,
                                       tx - dir * s * 0.5, f["y"], tx - dir * s * 0.6, f["y"] + s * 0.45 - tw,
                                       fill=c, outline="#1C2833", width=1, smooth=True)
            self.canvas.create_oval(f["x"] - s, f["y"] - s*0.6, f["x"] + s, f["y"] + s*0.6,
                                    fill=c, outline="#1C2833", width=1)
            ex = f["x"] + dir * s * 0.6
            self.canvas.create_oval(ex - 3, f["y"] - 3, ex + 3, f["y"] + 3, fill="white", outline="black")
        self.after_id = self.canvas.after(30, self.update)

# ===================== GAME 4: SNOWFALL =====================
class SnowfallGame(MiniGame):
    def __init__(self, canvas, width, height, app):
        super().__init__(canvas, width, height, app)
        self.reset()

    def reset(self):
        self.flakes = [{"x": random.randint(0, self.width),
                        "y": random.randint(0, self.height),
                        "vy": random.uniform(1, 3),
                        "r": random.uniform(1.5, 4)} for _ in range(50)]

    def update(self):
        if not self.active:
            return
        self.canvas.delete("all")
        self.canvas.create_rectangle(0, 0, self.width, self.height, fill="#0A0F1E", outline="")
        for f in self.flakes:
            f["y"] += f["vy"]
            self.canvas.create_oval(f["x"]-f["r"], f["y"]-f["r"], f["x"]+f["r"], f["y"]+f["r"],
                                    fill="#FFFFFF", outline="")
            if f["y"] > self.height + 10:
                f["y"], f["x"] = -10, random.randint(0, self.width)
        self.after_id = self.canvas.after(30, self.update)

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

class AgeOfWarGame(MiniGame):
    def __init__(self, canvas, width, height, app):
        super().__init__(canvas, width, height, app)
        self.reset(full_reset=True)

    def reset(self, full_reset=False):
        self.units, self.projectiles, self.effects = [], [], []
        self.save_timer = 0

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
            "red": {"x": 35, "y": self.height - 40, "dir": 1, "color": "#E74C3C",
                    "hp": r_hp, "mana": r_mana, "age": r_age, "tower": r_tower, "xp": r_xp, "summon_cd": 0},
            "blue": {"x": self.width - 35, "y": self.height - 40, "dir": -1, "color": "#3498DB",
                     "hp": b_hp, "mana": b_mana, "age": b_age, "tower": b_tower, "xp": b_xp, "summon_cd": 0}
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
            self.effects.append({"x": base["x"], "y": base["y"]-60,
                                 "text": f"LÊN ĐỜI {base['age']}!", "life": 50,
                                 "color": "#F1C40F", "size": 16})

    def update(self):
        if not self.active:
            return
        self.canvas.delete("all")
        self.canvas.create_rectangle(0, 0, self.width, self.height, fill="#87CEEB", outline="")
        self.canvas.create_rectangle(0, self.height - 30, self.width, self.height, fill="#27AE60", outline="")
        for i in range(0, self.width, 25):
            self.canvas.create_rectangle(i, self.height - 32, i+6, self.height - 30, fill="#229954", outline="")

        if not self.game_over_flag:
            self.handle_ai_and_mana()
            self.handle_towers()
            self.handle_logic()

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

            if base["summon_cd"] <= 0:
                enemy_team = "blue" if team == "red" else "red"
                enemies = [u for u in self.units if u["team"] == enemy_team]
                allies = [u for u in self.units if u["team"] == team]

                closest_dist = 999
                for e in enemies:
                    d = abs(base["x"] - e["x"])
                    if d < closest_dist:
                        closest_dist = d

                mana, tower_lvl, age_lvl = base["mana"], base["tower"], base["age"]
                tower_cost = TOWER_DATA[tower_lvl]["cost"] * age_lvl if tower_lvl < 4 else 99999

                if closest_dist > 120 and mana >= tower_cost and tower_lvl < 4:
                    base["tower"] += 1
                    base["mana"] -= tower_cost
                    self.effects.append({"x": base["x"], "y": base["y"]-60,
                                         "text": "+1 TRỤ", "life": 40,
                                         "color": "#2ECC71", "size": 14})
                    continue

                if not any(u["type"] == "tank" for u in allies) and mana >= UNIT_BASE["tank"]["cost"]:
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
        self.units.append({
            "team": team, "type": u_type, "age": base["age"],
            "x": base["x"] + base["dir"]*25, "y": self.height - 30,
            "hp": stats["hp"] * mult, "max_hp": stats["hp"] * mult,
            "dmg": stats["dmg"] * mult, "range": stats["range"],
            "speed": stats["speed"], "cd": 0, "max_cd": stats["cd"],
            "action": "walk"
        })

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
            enemies = [e for e in self.units if e["team"] == enemy_team]
            target, min_d = None, tower_stats["range"]
            for e in enemies:
                d = abs(base["x"] - e["x"])
                if d <= min_d:
                    min_d, target = d, e
            if target:
                self.projectiles.append({
                    "x": base["x"] + base["dir"]*15, "y": base["y"] - 30,
                    "vx": base["dir"] * 10, "team": team,
                    "dmg": tower_stats["dmg"] * mult, "aoe": (t_lvl >= 3),
                    "is_tower": True, "age": base["age"]
                })
                self.tower_cds[team] = tower_stats["cd"]

    def handle_logic(self):
        for u in self.units:
            enemy_team = "blue" if u["team"] == "red" else "red"
            enemy_base = self.bases[enemy_team]
            enemies = [e for e in self.units if e["team"] == enemy_team]

            closest, min_dist = enemy_base, abs(u["x"] - enemy_base["x"])
            for e in enemies:
                d = abs(u["x"] - e["x"])
                if d < min_dist:
                    min_dist, closest = d, e

            if min_dist <= u["range"]:
                u["action"] = "attack"
                if u["cd"] <= 0:
                    u["cd"] = u["max_cd"]
                    if u["type"] in ["sword", "tank", "assa"]:
                        closest["hp"] -= u["dmg"]
                        if closest == enemy_base:
                            self.add_xp(u["team"], 4)
                            self.add_xp(enemy_team, 7)
                        self.effects.append({"x": closest["x"], "y": closest["y"]-15,
                                             "text": f"-{int(u['dmg'])}", "life": 10,
                                             "color": "white", "size": 10})
                    else:
                        self.projectiles.append({
                            "x": u["x"], "y": u["y"]-10,
                            "vx": (1 if u["team"] == "red" else -1)*8,
                            "team": u["team"], "dmg": u["dmg"],
                            "aoe": UNIT_BASE[u["type"]].get("aoe", False),
                            "age": u["age"]
                        })
                else:
                    u["cd"] -= 1
            else:
                u["action"] = "walk"
                u["x"] += (1 if u["team"] == "red" else -1) * u["speed"]
                if u["cd"] > 0:
                    u["cd"] -= 1

    def update_physics(self):
        alive = []
        for u in self.units:
            if u["hp"] > 0:
                alive.append(u)
            else:
                self.add_xp("blue" if u["team"] == "red" else "red", 1)
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
                self.effects.append({"x": proj["x"], "y": enemy_base["y"]-20,
                                     "text": f"-{int(proj['dmg'])}", "life": 10,
                                     "color": "yellow", "size": 12})
                hit = True

            if not hit:
                for e in self.units:
                    if e["team"] == enemy_team and abs(proj["x"] - e["x"]) < 15:
                        hit = True
                        if proj.get("aoe"):
                            for target in self.units:
                                if target["team"] == enemy_team and abs(proj["x"] - target["x"]) < 40:
                                    target["hp"] -= proj["dmg"]
                                    self.effects.append({"x": target["x"], "y": target["y"]-15,
                                                         "text": f"-{int(proj['dmg'])}", "life": 10,
                                                         "color": "#00FFFF", "size": 10})
                        else:
                            e["hp"] -= proj["dmg"]
                            self.effects.append({"x": e["x"], "y": e["y"]-15,
                                                 "text": f"-{int(proj['dmg'])}", "life": 10,
                                                 "color": "white", "size": 10})
                        break
            if hit or proj["x"] < 0 or proj["x"] > self.width:
                self.projectiles.remove(proj)

        for e in self.effects[:]:
            e["life"] -= 1
            e["y"] -= 1
            if e["life"] <= 0:
                self.effects.remove(e)

    def draw_world(self):
        def get_age_style(age):
            if age == 1:
                return {"b_color": "#D35400", "head": "#F5CBA7", "body": "#A04000", "wpn": "#8B4513", "accent": "#E67E22"}
            elif age == 2:
                return {"b_color": "#95A5A6", "head": "#BDC3C7", "body": "#7F8C8D", "wpn": "#FFFFFF", "accent": "#F1C40F"}
            elif age == 3:
                return {"b_color": "#1E8449", "head": "#F5CBA7", "body": "#117A65", "wpn": "#17202A", "accent": "#E74C3C"}
            else:
                return {"b_color": "#8E44AD", "head": "#9B59B6", "body": "#2C3E50", "wpn": "#00FFFF", "accent": "#FF00FF"}

        for u in self.units:
            x, y, t, team, age = u["x"], u["y"], u["type"], u["team"], u["age"]
            dir = 1 if team == "red" else -1
            st = get_age_style(age)
            self.canvas.create_oval(x-8, y+4, x+8, y+12, fill="#1E1E1E", outline="")
            self.canvas.create_rectangle(x-5, y+2, x+5, y+10, fill=st["body"], outline="black")
            self.canvas.create_rectangle(x-6, y-7, x+6, y+2, fill=st["body"], outline="black")
            self.canvas.create_rectangle(x-5, y-15, x+5, y-7, fill=st["head"], outline="black")
            if age >= 2:
                self.canvas.create_polygon(x-6, y-15, x, y-22, x+6, y-15, fill=st["accent"], outline="black")
            if age >= 3:
                self.canvas.create_rectangle(x-3, y-22, x+3, y-18, fill="red", outline="black")
            if t == "sword":
                if u["action"] == "attack" and u["cd"] > u["max_cd"] - 5:
                    self.canvas.create_line(x, y-5, x+dir*18, y-5, fill=st["wpn"], width=3)
                else:
                    self.canvas.create_rectangle(x+dir*4, y-12, x+dir*8, y-2, fill=st["wpn"], outline="black")
            elif t == "bow":
                self.canvas.create_line(x+dir*2, y-10, x+dir*12, y-6, fill="#8B5A2B", width=2)
                self.canvas.create_line(x+dir*10, y-10, x+dir*12, y-6, fill=st["wpn"], width=2)
            elif t == "tank":
                self.canvas.create_rectangle(x+dir*6, y-12, x+dir*12, y+2, fill="gray", outline="black")
            elif t == "assa":
                if u["action"] == "attack" and u["cd"] > u["max_cd"] - 5:
                    self.canvas.create_line(x, y-2, x+dir*16, y-2, fill="red", width=2)
                else:
                    self.canvas.create_rectangle(x+dir*4, y-8, x+dir*7, y-2, fill="silver", outline="black")
            elif t == "mage":
                self.canvas.create_polygon(x-6, y-20, x, y-26, x+6, y-20, fill=st["accent"], outline="black")
                self.canvas.create_oval(x+dir*8, y-14, x+dir*14, y-8, fill="cyan", outline="black")
            w_ratio = max(0, u["hp"]/u["max_hp"])
            self.canvas.create_rectangle(x-12, y-28, x+12, y-25, fill="#333", outline="")
            self.canvas.create_rectangle(x-12, y-28, x-12+24*w_ratio, y-25, fill="#2ECC71", outline="")

        for name, b in self.bases.items():
            st = get_age_style(b["age"])
            if b["hp"] > 0:
                if b["age"] == 1:
                    self.canvas.create_polygon(b["x"]-30, b["y"]+30, b["x"], b["y"]-20, b["x"]+30, b["y"]+30,
                                               fill=st["b_color"], outline="black", width=2)
                elif b["age"] == 2:
                    self.canvas.create_rectangle(b["x"]-25, b["y"]-15, b["x"]+25, b["y"]+30,
                                                 fill=st["b_color"], outline="black", width=2)
                    for i in range(-25, 25, 15):
                        self.canvas.create_rectangle(b["x"]+i, b["y"]-25, b["x"]+i+10, b["y"]-15,
                                                     fill=st["b_color"], outline="black", width=2)
                elif b["age"] == 3:
                    self.canvas.create_rectangle(b["x"]-30, b["y"], b["x"]+30, b["y"]+30,
                                                 fill=st["b_color"], outline="black", width=2)
                    self.canvas.create_rectangle(b["x"]-20, b["y"]-15, b["x"]+20, b["y"],
                                                 fill=st["b_color"], outline="black", width=2)
                else:
                    self.canvas.create_polygon(b["x"]-20, b["y"]+30, b["x"]-30, b["y"], b["x"]-10, b["y"]-30,
                                               b["x"]+10, b["y"]-30, b["x"]+30, b["y"], b["x"]+20, b["y"]+30,
                                               fill=st["b_color"], outline="black", width=2)
                if b["tower"] > 0:
                    t_color = TOWER_DATA[b["tower"]].get("color", "#FFF")
                    self.canvas.create_rectangle(b["x"]-10, b["y"]-45, b["x"]+10, b["y"]-30,
                                                 fill=t_color, outline="black", width=2)
                    self.canvas.create_line(b["x"]+b["dir"]*10, b["y"]-37, b["x"]+b["dir"]*22, b["y"]-37,
                                            fill="yellow", width=3)
                max_hp = AGE_DATA[b["age"]]["base_hp"]
                self.canvas.create_rectangle(b["x"]-25, b["y"]-55, b["x"]+25, b["y"]-50,
                                             fill="#641E16", outline="")
                self.canvas.create_rectangle(b["x"]-25, b["y"]-55,
                                             b["x"]-25 + max(0, (b["hp"] / max_hp) * 50), b["y"]-50,
                                             fill="#2ECC71", outline="")
            else:
                self.canvas.create_rectangle(b["x"]-25, b["y"]+15, b["x"]+25, b["y"]+30,
                                             fill="#7F8C8D", outline="black", width=2)

        for proj in self.projectiles:
            c = "#00FFFF" if proj.get("aoe") else get_age_style(proj.get("age", 1))["wpn"]
            if proj.get("is_tower"):
                c = TOWER_DATA.get(self.bases[proj["team"]]["tower"], {}).get("color", "#FFF")
            self.canvas.create_rectangle(proj["x"]-3, proj["y"]-2, proj["x"]+3, proj["y"]+2, fill=c, outline="black")

        for e in self.effects:
            self.canvas.create_text(e["x"], e["y"], text=e["text"], fill=e["color"],
                                    font=("Courier", e["size"], "bold"))

        self.draw_ui()

    def draw_ui(self):
        self.canvas.create_text(self.width/2, 20, text=f"ĐỎ: {self.red_wins}   |   XANH: {self.blue_wins}",
                                fill="#F1C40F", font=("Courier", 14, "bold"))
        r, b = self.bases["red"], self.bases["blue"]
        r_txt = f"Đời:{r['age']} Trụ:{r['tower']} XP:{r['xp']}/{r['age']*50} ${int(r['mana'])}"
        b_txt = f"${int(b['mana'])} XP:{b['xp']}/{b['age']*50} Trụ:{b['tower']} Đời:{b['age']}"
        self.canvas.create_text(10, 10, text=r_txt, fill="white", font=("Courier", 9, "bold"), anchor="nw")
        self.canvas.create_text(self.width-10, 10, text=b_txt, fill="white", font=("Courier", 9, "bold"), anchor="ne")

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
            self.effects.append({"x": self.width/2, "y": self.height/2, "text": winner,
                                 "life": 60, "color": "#F1C40F", "size": 24})
            self.canvas.after(3000, lambda: self.reset(full_reset=True))

# ===================== ỨNG DỤNG ĐỒNG HỒ + BÁO THỨC (GIAO DIỆN LỚN HƠN) =====================
class StudyTimer:
    def __init__(self, root):
        self.root = root
        self.root.title("⏳ Study Timer - Tactical Defense (Age of War)")
        self.root.geometry("900x600")   # Tăng kích thước cửa sổ
        self.bg_color = "#121212"
        self.frame_bg = "#1E1E1E"
        self.green_accent = "#20B2AA"
        self.red_accent = "#CD5C5C"
        self.text_color = "#FFFFFF"
        self.sub_color = "#AAAAAA"
        self.root.configure(bg=self.bg_color)
        self.root.resizable(False, False)

        self.db = DBManager()

        self.study_time = 25 * 60
        self.short_break = 5 * 60
        self.long_break = 15 * 60
        self.current_time_left = self.study_time
        self.end_time = 0
        self.is_running = False
        self.is_paused = False
        self.is_study = True
        self.pomodoro_count = 0
        self.after_id = None

        # Báo thức
        self.alarm_time = None
        self.alarm_active = False
        self.alarm_after_id = None

        self.current_game = None
        self.game_map = {}

        self.build_ui()
        self.switch_game("age_of_war")
        self.update_timer_display()
        self.start_alarm_check()

    def build_ui(self):
        # Left frame rộng hơn để chứa hết các thành phần
        left_frame = tk.Frame(self.root, bg=self.bg_color, width=460, height=600)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=15, pady=15)
        left_frame.pack_propagate(False)

        tk.Label(left_frame, text="⏳ STUDY TIMER", font=("Segoe UI", 20, "bold"),
                 fg=self.text_color, bg=self.bg_color).pack(pady=(5,2))

        total, streak, _ = self.db.get_stats()
        self.stats_label = tk.Label(left_frame, text=f"🔥 Chuỗi: {streak} ngày | 📚 Tổng: {total} lần",
                                    font=("Segoe UI", 10, "bold"), fg="#F39C12", bg=self.bg_color)
        self.stats_label.pack(pady=(0, 10))

        # ======== KHUNG BÁO THỨC (đặt lên trên, dễ thấy) ========
        alarm_frame = tk.Frame(left_frame, bg=self.frame_bg)
        alarm_frame.pack(pady=5, fill=tk.X, padx=10)

        tk.Label(alarm_frame, text="⏰ BÁO THỨC (hh:mm)", font=("Segoe UI", 11, "bold"),
                 fg=self.text_color, bg=self.frame_bg).pack(side=tk.LEFT, padx=(10,5))

        self.alarm_hour_var = tk.StringVar(value="07")
        self.alarm_min_var = tk.StringVar(value="00")
        hour_spin = tk.Spinbox(alarm_frame, from_=0, to=23, textvariable=self.alarm_hour_var,
                               width=3, font=("Segoe UI", 11), bg="#333333", fg=self.text_color,
                               buttonbackground="#555555", readonlybackground="#333333")
        hour_spin.pack(side=tk.LEFT)
        tk.Label(alarm_frame, text=":", font=("Segoe UI", 11, "bold"),
                 fg=self.text_color, bg=self.frame_bg).pack(side=tk.LEFT)
        min_spin = tk.Spinbox(alarm_frame, from_=0, to=59, textvariable=self.alarm_min_var,
                              width=3, font=("Segoe UI", 11), bg="#333333", fg=self.text_color,
                              buttonbackground="#555555", readonlybackground="#333333")
        min_spin.pack(side=tk.LEFT, padx=(0,10))

        self.alarm_btn = tk.Button(alarm_frame, text="⏰ ĐẶT", font=("Segoe UI", 10, "bold"),
                                   bg="#333333", fg=self.text_color, relief=tk.FLAT,
                                   command=self.toggle_alarm, cursor="hand2", width=6)
        self.alarm_btn.pack(side=tk.LEFT, padx=5)

        self.alarm_status_label = tk.Label(alarm_frame, text="", font=("Segoe UI", 10),
                                           fg="#AAAAAA", bg=self.frame_bg)
        self.alarm_status_label.pack(side=tk.LEFT, padx=5)

        # Canvas đồng hồ tròn
        canvas_frame = tk.Frame(left_frame, bg=self.bg_color)
        canvas_frame.pack(pady=10)
        self.canvas = tk.Canvas(canvas_frame, width=240, height=240, bg=self.bg_color, highlightthickness=0)
        self.canvas.pack()
        self.canvas.create_oval(20, 20, 220, 220, outline="#2A2A2A", width=12)
        self.progress_arc = self.canvas.create_arc(20, 20, 220, 220, start=90, extent=-360,
                                                   outline=self.green_accent, width=12, style=tk.ARC)
        self.timer_text = self.canvas.create_text(120, 100, text="25:00", font=("Segoe UI", 40, "bold"),
                                                  fill=self.text_color)
        self.status_text = self.canvas.create_text(120, 145, text="HỌC TẬP", font=("Segoe UI", 12, "bold"),
                                                   fill=self.green_accent)
        self.count_text = self.canvas.create_text(120, 175, text="🍅 x 0", font=("Segoe UI", 11),
                                                  fill=self.sub_color)

        self.notif_label = tk.Label(left_frame, text="", font=("Segoe UI", 10, "italic"),
                                    fg="#FFD700", bg=self.bg_color, wraplength=400)
        self.notif_label.pack(pady=5)

        btn_frame = tk.Frame(left_frame, bg=self.bg_color)
        btn_frame.pack(pady=5)
        self.start_pause_btn = tk.Button(btn_frame, text="▶ BẮT ĐẦU", font=("Segoe UI", 11, "bold"),
                                         bg=self.green_accent, fg="#000000", activebackground="#32CD32",
                                         relief=tk.FLAT, bd=0, width=12, pady=5, cursor="hand2",
                                         command=self.start_pause)
        self.start_pause_btn.grid(row=0, column=0, padx=5)
        self.reset_btn = tk.Button(btn_frame, text="↺ ĐẶT LẠI", font=("Segoe UI", 11, "bold"),
                                   bg="#333333", fg=self.text_color, activebackground="#555555",
                                   relief=tk.FLAT, bd=0, width=10, pady=5, cursor="hand2", command=self.reset)
        self.reset_btn.grid(row=0, column=1, padx=5)
        self.skip_btn = tk.Button(btn_frame, text="⏭ BỎ QUA", font=("Segoe UI", 11, "bold"),
                                  bg=self.red_accent, fg="#FFFFFF", activebackground="#FF6347",
                                  relief=tk.FLAT, bd=0, width=10, pady=5, cursor="hand2", command=self.skip)
        self.skip_btn.grid(row=0, column=2, padx=5)

        setting_frame = tk.Frame(left_frame, bg=self.frame_bg)
        setting_frame.pack(pady=10, fill=tk.X, padx=10)
        fields = [("📚 Học:", "study", 25), ("☕ Ngắn:", "short_break", 5), ("😴 Dài:", "long_break", 15)]
        for i, (label_text, attr, default) in enumerate(fields):
            tk.Label(setting_frame, text=label_text, font=("Segoe UI", 10),
                     fg=self.sub_color, bg=self.frame_bg).grid(row=0, column=i*2, padx=(10, 2), pady=10)
            entry = tk.Entry(setting_frame, font=("Segoe UI", 10, "bold"), bg="#333333",
                             fg=self.text_color, relief=tk.FLAT, width=4, justify=tk.CENTER)
            entry.insert(0, str(default))
            entry.grid(row=0, column=i*2+1, padx=(0, 10))
            setattr(self, f"{attr}_entry", entry)
        self.apply_btn = tk.Button(setting_frame, text="✓ LƯU", font=("Segoe UI", 9, "bold"),
                                   bg="#333333", fg=self.text_color, relief=tk.FLAT,
                                   command=self.apply_settings, cursor="hand2")
        self.apply_btn.grid(row=1, column=0, columnspan=6, pady=(0, 10), ipadx=20)

        # Phần game bên phải
        right_frame = tk.Frame(self.root, bg=self.frame_bg, width=400, height=600)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(0,15), pady=15)
        right_frame.pack_propagate(False)

        tk.Label(right_frame, text="🎮 CHILL MINI GAME", font=("Segoe UI", 13, "bold"),
                 fg=self.text_color, bg=self.frame_bg).pack(pady=(15, 5))

        game_select = tk.Frame(right_frame, bg=self.frame_bg)
        game_select.pack(pady=5)
        self.game_var = tk.StringVar(value="age_of_war")
        style = ttk.Style()
        style.theme_use('clam')
        game_combo = ttk.Combobox(game_select, textvariable=self.game_var, state="readonly",
                                  width=18, font=("Segoe UI", 10))
        game_combo['values'] = ("age_of_war", "dino_runner", "auto_pong", "aquarium", "snowfall")
        game_combo.current(0)
        game_combo.pack()
        game_combo.bind("<<ComboboxSelected>>", lambda e: self.switch_game(self.game_var.get()))

        # Canvas game to hơn
        self.game_canvas = tk.Canvas(right_frame, width=350, height=250, bg="#F7F7F7",
                                     highlightthickness=2, highlightbackground="#333333")
        self.game_canvas.pack(pady=15)

        tk.Label(right_frame, text="Nhìn game tự chơi để mắt được nghỉ ngơi nhé 👀",
                 font=("Segoe UI", 9, "italic"), fg=self.sub_color, bg=self.frame_bg).pack()

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
                self.alarm_btn.config(text="🔕 TẮT", bg="#E74C3C", fg="#FFFFFF")
                self.alarm_status_label.config(text=f"Đã đặt {h:02d}:{m:02d}", fg="#2ECC71")
                self.show_notification(f"⏰ Báo thức lúc {h:02d}:{m:02d}")
            else:
                self.show_notification("Giờ không hợp lệ!")
        except ValueError:
            self.show_notification("Nhập số giờ/phút hợp lệ!")

    def cancel_alarm(self):
        self.alarm_active = False
        self.alarm_time = None
        self.alarm_btn.config(text="⏰ ĐẶT", bg="#333333", fg=self.text_color)
        self.alarm_status_label.config(text="", fg="#AAAAAA")

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
        top = tk.Toplevel(self.root)
        top.title("Báo thức")
        top.geometry("250x100")
        top.configure(bg=self.frame_bg)
        tk.Label(top, text="⏰ ĐÃ ĐẾN GIỜ HẸN!", font=("Segoe UI", 12, "bold"),
                 fg="#F1C40F", bg=self.frame_bg).pack(expand=True)
        tk.Button(top, text="OK", command=top.destroy, bg=self.green_accent, fg="#000").pack(pady=10)
        top.attributes('-topmost', True)

    # ==================== CÁC HÀM CÒN LẠI (giữ nguyên) ====================
    def update_stats_ui(self):
        total, streak, _ = self.db.get_stats()
        self.stats_label.config(text=f"🔥 Chuỗi: {streak} ngày | 📚 Tổng: {total} lần")

    def init_game(self, game_key):
        if self.current_game:
            if isinstance(self.current_game, AgeOfWarGame):
                self.current_game.save_state_to_db()
            self.current_game.stop()
        w, h = 350, 250   # Kích thước game canvas mới
        if game_key == "dino_runner":
            game = DinoRunnerGame(self.game_canvas, w, h, self)
        elif game_key == "age_of_war":
            game = AgeOfWarGame(self.game_canvas, w, h, self)
        elif game_key == "auto_pong":
            game = AutoPongGame(self.game_canvas, w, h, self)
        elif game_key == "aquarium":
            game = AquariumGame(self.game_canvas, w, h, self)
        elif game_key == "snowfall":
            game = SnowfallGame(self.game_canvas, w, h, self)
        else:
            return
        self.game_map[game_key] = game
        self.current_game = game
        if self.is_running and not self.is_paused and self.is_study:
            self.current_game.start()

    def switch_game(self, game_key):
        self.init_game(game_key)

    def draw_progress(self):
        total = self.study_time if self.is_study else self.short_break
        extent = -(360 * (self.current_time_left / total)) if total > 0 else 0
        color = self.green_accent if self.is_study else self.red_accent
        self.canvas.itemconfig(self.progress_arc, extent=extent, outline=color)

    def update_timer_display(self):
        current_secs = int(math.ceil(self.current_time_left))
        mins, secs = divmod(current_secs, 60)
        self.canvas.itemconfig(self.timer_text, text=f"{mins:02d}:{secs:02d}")
        status = "HỌC TẬP" if self.is_study else "NGHỈ NGƠI"
        color = self.green_accent if self.is_study else self.red_accent
        self.canvas.itemconfig(self.status_text, text=status, fill=color)
        self.canvas.itemconfig(self.count_text, text=f"🍅 x {self.pomodoro_count}")
        self.draw_progress()

    def countdown(self):
        if self.is_running and not self.is_paused:
            self.current_time_left = max(0, self.end_time - time.time())
            self.update_timer_display()
            if self.current_time_left > 0:
                self.after_id = self.root.after(50, self.countdown)
            else:
                self.timer_finished()

    def timer_finished(self):
        self.is_running = False
        self.start_pause_btn.config(text="▶ BẮT ĐẦU", bg=self.green_accent, fg="#000000")
        if self.current_game:
            if isinstance(self.current_game, AgeOfWarGame):
                self.current_game.save_state_to_db()
            self.current_game.stop()
        if self.is_study:
            self.pomodoro_count += 1
            self.db.update_session()
            self.update_stats_ui()
            self.update_timer_display()
            if self.pomodoro_count % 4 == 0:
                self.current_time_left = self.long_break
                msg = "🎉 Bạn rất giỏi! Nghỉ dài 15 phút nhé."
            else:
                self.current_time_left = self.short_break
                msg = "✅ Hoàn thành! Nghỉ ngắn 5 phút nào."
            self.is_study = False
        else:
            self.current_time_left = self.study_time
            self.is_study = True
            msg = "📚 Hết giờ nghỉ! Quay lại học thôi."
        self.show_notification(msg)
        self.update_timer_display()

    def show_notification(self, message):
        self.notif_label.config(text=message)
        self.root.after(4000, lambda: self.notif_label.config(text=""))

    def start_pause(self):
        if not self.is_running:
            self.is_running = True
            self.is_paused = False
            self.start_pause_btn.config(text="⏸ TẠM DỪNG", bg=self.red_accent, fg="#FFFFFF")
            self.end_time = time.time() + self.current_time_left
            if self.is_study and self.current_game:
                self.current_game.start()
            self.countdown()
        elif self.is_running and not self.is_paused:
            self.is_paused = True
            self.start_pause_btn.config(text="▶ TIẾP TỤC", bg=self.green_accent, fg="#000000")
            if self.after_id:
                self.root.after_cancel(self.after_id)
            if self.current_game:
                self.current_game.pause()
        elif self.is_running and self.is_paused:
            self.is_paused = False
            self.start_pause_btn.config(text="⏸ TẠM DỪNG", bg=self.red_accent, fg="#FFFFFF")
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
        self.start_pause_btn.config(text="▶ BẮT ĐẦU", bg=self.green_accent, fg="#000000")
        if self.current_game:
            if isinstance(self.current_game, AgeOfWarGame):
                self.current_game.save_state_to_db()
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
            self.is_study = False
            msg = "⏩ Chuyển sang giờ nghỉ."
        else:
            self.current_time_left = self.study_time
            self.is_study = True
            msg = "⏩ Quay lại học tập."
        self.start_pause_btn.config(text="▶ BẮT ĐẦU", bg=self.green_accent, fg="#000000")
        if self.current_game:
            if isinstance(self.current_game, AgeOfWarGame):
                self.current_game.save_state_to_db()
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
            self.start_pause_btn.config(text="▶ BẮT ĐẦU", bg=self.green_accent, fg="#000000")
            if self.current_game:
                if isinstance(self.current_game, AgeOfWarGame):
                    self.current_game.save_state_to_db()
                self.current_game.stop()
            self.update_timer_display()
            self.show_notification("✓ Đã lưu cài đặt mới")
        except ValueError:
            self.show_notification("⚠️ Hãy nhập số phút hợp lệ nhé!")

if __name__ == "__main__":
    root = tk.Tk()
    app = StudyTimer(root)
    root.mainloop()