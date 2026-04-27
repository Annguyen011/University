import tkinter as tk
from tkinter import ttk
import random
import math
import time

# ===================== CÁC MINIGAME (AUTO-PLAY) =====================
class MiniGame:
    def __init__(self, canvas, width, height):
        self.canvas = canvas
        self.width = width
        self.height = height
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
        self.active = False
        if self.after_id:
            self.canvas.after_cancel(self.after_id)
            self.after_id = None

    def resume(self):
        if not self.active:
            self.active = True
            self.update()

    def reset(self):
        raise NotImplementedError

    def update(self):
        raise NotImplementedError

# --- Game 1: Dino Runner (Vẫn giữ AI nhảy tốt) ---
class DinoRunnerGame(MiniGame):
    def __init__(self, canvas, width, height):
        super().__init__(canvas, width, height)
        self.ground_y = height - 30
        self.dino = {"x": 40, "y": self.ground_y - 40, "w": 40, "h": 43, "vy": 0, "jumping": False}
        self.obstacles = []
        self.speed = 5
        self.spawn_timer = 0
        self.spawn_delay = 60
        self.frame = 0
        self.score = 0
        self.ground_dots = []

    def reset(self):
        self.dino["y"] = self.ground_y - self.dino["h"]
        self.dino["vy"] = 0
        self.dino["jumping"] = False
        self.obstacles.clear()
        self.speed = 5
        self.spawn_timer = 0
        self.score = 0
        self.frame = 0
        self.ground_dots = [{"x": random.randint(0, self.width), "y": random.randint(self.ground_y + 2, self.ground_y + 10)} for _ in range(15)]

    def start(self):
        self.reset()
        super().start()

    def update(self):
        if not self.active:
            return
        self.canvas.delete("all")
        
        bg_color = "#F7F7F7"
        self.canvas.create_rectangle(0, 0, self.width, self.height, fill=bg_color, outline="")
        self.canvas.create_line(0, self.ground_y, self.width, self.ground_y, fill="#535353", width=1)
        
        for dot in self.ground_dots:
            dot["x"] -= self.speed
            if dot["x"] < 0:
                dot["x"] = self.width + random.randint(0, 50)
            self.canvas.create_rectangle(dot["x"], dot["y"], dot["x"]+2, dot["y"]+2, fill="#535353", outline="")

        self.draw_cloud(80, 30)
        self.draw_cloud(220, 15)

        self.spawn_timer += 1
        if self.spawn_timer >= self.spawn_delay:
            self.spawn_obstacle()
            self.spawn_timer = random.randint(-20, 10) 
            self.speed = min(12, self.speed + 0.05)

        for obs in self.obstacles[:]:
            obs["x"] -= self.speed
            if obs["x"] + obs["w"] < 0:
                self.obstacles.remove(obs)
                self.score += 10

        if self.dino["jumping"]:
            self.dino["vy"] += 0.9  
            self.dino["y"] += self.dino["vy"]
            if self.dino["y"] >= self.ground_y - self.dino["h"]:
                self.dino["y"] = self.ground_y - self.dino["h"]
                self.dino["vy"] = 0
                self.dino["jumping"] = False

        if not self.dino["jumping"]:
            for obs in self.obstacles:
                if obs["x"] + obs["w"] > self.dino["x"]:
                    dist = obs["x"] - (self.dino["x"] + self.dino["w"])
                    jump_dist = 35 + self.speed * 7 
                    if dist < jump_dist: 
                        self.dino["vy"] = -14
                        self.dino["jumping"] = True
                    break 

        dino_bbox = (self.dino["x"]+5, self.dino["y"]+5, self.dino["x"]+self.dino["w"]-5, self.dino["y"]+self.dino["h"]-5)
        for obs in self.obstacles:
            obs_bbox = (obs["x"], obs["y"], obs["x"]+obs["w"], obs["y"]+obs["h"])
            if self.rect_collide(dino_bbox, obs_bbox):
                self.game_over()
                return

        self.draw_obstacles()
        self.draw_dino()
        
        self.canvas.create_text(self.width-40, 20, text=f"{self.score:05d}", font=("Courier", 12, "bold"), fill="#535353")
        self.after_id = self.canvas.after(20, self.update)

    def draw_cloud(self, cx, cy):
        color = "#E0E0E0"
        self.canvas.create_rectangle(cx, cy, cx+30, cy+10, fill=color, outline="")
        self.canvas.create_rectangle(cx+5, cy-5, cx+25, cy+15, fill=color, outline="")
        self.canvas.create_rectangle(cx+10, cy-10, cx+20, cy+20, fill=color, outline="")

    def spawn_obstacle(self):
        types = ["small1", "small2", "big"]
        choice = random.choice(types)
        if choice == "small1": w, h = 15, 33
        elif choice == "small2": w, h = 30, 33 
        else: w, h = 23, 46 
        self.obstacles.append({"x": self.width, "y": self.ground_y - h, "w": w, "h": h, "type": choice})

    def draw_dino(self):
        x, y = self.dino["x"], self.dino["y"]
        c = "#535353"
        self.canvas.create_rectangle(x+20, y, x+38, y+16, fill=c, outline="")
        self.canvas.create_rectangle(x+22, y+2, x+26, y+6, fill="#F7F7F7", outline="")
        self.canvas.create_rectangle(x+20, y+16, x+28, y+20, fill=c, outline="")
        self.canvas.create_rectangle(x+30, y+16, x+38, y+18, fill=c, outline="")
        self.canvas.create_rectangle(x+10, y+16, x+26, y+32, fill=c, outline="")
        self.canvas.create_rectangle(x+6, y+20, x+10, y+28, fill=c, outline="")
        self.canvas.create_rectangle(x+2, y+24, x+6, y+28, fill=c, outline="")
        self.canvas.create_rectangle(x, y+18, x+4, y+24, fill=c, outline="")
        self.canvas.create_rectangle(x+26, y+18, x+32, y+22, fill=c, outline="")
        self.canvas.create_rectangle(x+30, y+22, x+32, y+24, fill=c, outline="")

        if not self.dino["jumping"]:
            self.frame = (self.frame + 1) % 10
            if self.frame < 5:
                self.canvas.create_rectangle(x+10, y+32, x+14, y+38, fill=c, outline="")
                self.canvas.create_rectangle(x+18, y+32, x+22, y+42, fill=c, outline="")
                self.canvas.create_rectangle(x+22, y+40, x+26, y+42, fill=c, outline="")
            else:
                self.canvas.create_rectangle(x+10, y+32, x+14, y+42, fill=c, outline="")
                self.canvas.create_rectangle(x+14, y+40, x+18, y+42, fill=c, outline="")
                self.canvas.create_rectangle(x+18, y+32, x+22, y+38, fill=c, outline="")
        else:
            self.canvas.create_rectangle(x+10, y+32, x+14, y+36, fill=c, outline="")
            self.canvas.create_rectangle(x+20, y+32, x+24, y+36, fill=c, outline="")

    def draw_obstacles(self):
        c = "#535353"
        for obs in self.obstacles:
            x, y, w, h = obs["x"], obs["y"], obs["w"], obs["h"]
            if obs["type"] == "small1" or obs["type"] == "small2":
                self.canvas.create_rectangle(x+w//2-3, y, x+w//2+3, y+h, fill=c, outline="")
                self.canvas.create_rectangle(x, y+10, x+w//2-3, y+14, fill=c, outline="")
                self.canvas.create_rectangle(x, y+4, x+4, y+14, fill=c, outline="")
                self.canvas.create_rectangle(x+w//2+3, y+14, x+w, y+18, fill=c, outline="")
                self.canvas.create_rectangle(x+w-4, y+6, x+w, y+18, fill=c, outline="")
                if obs["type"] == "small2":
                    offset = 15
                    self.canvas.create_rectangle(x+offset+w//2-3, y+4, x+offset+w//2+3, y+h, fill=c, outline="")
                    self.canvas.create_rectangle(x+offset, y+14, x+offset+w//2-3, y+18, fill=c, outline="")
                    self.canvas.create_rectangle(x+offset, y+8, x+offset+4, y+18, fill=c, outline="")
            elif obs["type"] == "big":
                self.canvas.create_rectangle(x+8, y, x+16, y+h, fill=c, outline="")
                self.canvas.create_rectangle(x, y+15, x+8, y+20, fill=c, outline="")
                self.canvas.create_rectangle(x, y+5, x+6, y+20, fill=c, outline="")
                self.canvas.create_rectangle(x+16, y+20, x+24, y+25, fill=c, outline="")
                self.canvas.create_rectangle(x+18, y+10, x+24, y+25, fill=c, outline="")

    def game_over(self):
        self.active = False
        if self.after_id:
            self.canvas.after_cancel(self.after_id)
        self.canvas.create_text(self.width/2, self.height/2-20, text="G A M E  O V E R", font=("Courier", 14, "bold"), fill="#535353")
        self.canvas.create_text(self.width/2, self.height/2+10, text="Tự chạy lại sau 2s...", font=("Arial", 9), fill="#535353")
        self.canvas.after(2000, self.start)

    def rect_collide(self, r1, r2):
        return (r1[0] < r2[2] and r1[2] > r2[0] and r1[1] < r2[3] and r1[3] > r2[1])


# --- Game 2: Bóng Bàn Tự Chơi ---
class AutoPongGame(MiniGame):
    def __init__(self, canvas, width, height):
        super().__init__(canvas, width, height)
        self.paddle_w = 8
        self.paddle_h = 40
        self.ball_r = 5
        self.reset()

    def reset(self):
        self.ball_x = self.width / 2
        self.ball_y = self.height / 2
        self.ball_vx = random.choice([-5, 5])
        self.ball_vy = random.choice([-4, 4])
        self.pad1_y = self.height / 2 - self.paddle_h / 2
        self.pad2_y = self.height / 2 - self.paddle_h / 2

    def update(self):
        if not self.active: return
        self.canvas.delete("all")
        
        self.canvas.create_rectangle(0, 0, self.width, self.height, fill="#111111", outline="")
        self.canvas.create_line(self.width/2, 0, self.width/2, self.height, fill="#333333", dash=(4, 4))

        self.ball_x += self.ball_vx
        self.ball_y += self.ball_vy

        if self.ball_y - self.ball_r <= 0 or self.ball_y + self.ball_r >= self.height:
            self.ball_vy = -self.ball_vy

        if self.ball_vx < 0:
            target1 = self.ball_y - self.paddle_h/2
            target2 = self.height/2 - self.paddle_h/2 
        else:
            target2 = self.ball_y - self.paddle_h/2
            target1 = self.height/2 - self.paddle_h/2 

        self.pad1_y += (target1 - self.pad1_y) * 0.15
        self.pad2_y += (target2 - self.pad2_y) * 0.15

        self.pad1_y = max(0, min(self.height - self.paddle_h, self.pad1_y))
        self.pad2_y = max(0, min(self.height - self.paddle_h, self.pad2_y))

        if self.ball_x - self.ball_r <= 15 + self.paddle_w and self.pad1_y <= self.ball_y <= self.pad1_y + self.paddle_h:
            self.ball_x = 15 + self.paddle_w + self.ball_r
            self.ball_vx = -self.ball_vx
        
        if self.ball_x + self.ball_r >= self.width - 15 - self.paddle_w and self.pad2_y <= self.ball_y <= self.pad2_y + self.paddle_h:
            self.ball_x = self.width - 15 - self.paddle_w - self.ball_r
            self.ball_vx = -self.ball_vx

        self.canvas.create_rectangle(15, self.pad1_y, 15+self.paddle_w, self.pad1_y+self.paddle_h, fill="#00FF00", outline="")
        self.canvas.create_rectangle(self.width-15-self.paddle_w, self.pad2_y, self.width-15, self.pad2_y+self.paddle_h, fill="#FF00FF", outline="")
        self.canvas.create_oval(self.ball_x-self.ball_r, self.ball_y-self.ball_r, self.ball_x+self.ball_r, self.ball_y+self.ball_r, fill="#FFFFFF", outline="")

        self.after_id = self.canvas.after(20, self.update)

class SolarOrbitGame(MiniGame):
    def __init__(self, canvas, width, height):
        super().__init__(canvas, width, height)
        self.planets = []
        self.moons = []         # Mặt trăng của các hành tinh
        self.asteroids = []     # Vành đai tiểu hành tinh
        self.stars = []
        self.reset()

    def reset(self):
        self.planets = [
            {"r": 35, "speed": 0.06, "angle": 0, "size": 9, "color": "#D5D8DC",
             "type": "rocky", "self_rot": 0},
            {"r": 60, "speed": 0.03, "angle": 45, "size": 15, "color": "#2E86C1",
             "type": "gas", "self_rot": 0},
            {"r": 88, "speed": 0.015, "angle": 120, "size": 20, "color": "#AF7AC5",
             "type": "ringed", "self_rot": 0},
            {"r": 115, "speed": 0.008, "angle": 210, "size": 25, "color": "#E67E22",
             "type": "jupiter", "self_rot": 0},
        ]
        self.moons = []
        # Mặt trăng cho hành tinh thứ 3 (ringed)
        self.moons.append({"planet_idx": 2, "distance": 14, "size": 2.5, "speed": 0.08, "angle": 0, "color": "#BDC3C7"})
        # Mặt trăng cho hành tinh thứ 4
        self.moons.append({"planet_idx": 3, "distance": 18, "size": 3.5, "speed": 0.05, "angle": 45, "color": "#F1C40F"})
        self.moons.append({"planet_idx": 3, "distance": 22, "size": 2.0, "speed": 0.04, "angle": 180, "color": "#BFC9CA"})

        # Vành đai tiểu hành tinh giữa hành tinh 2 và 3
        self.asteroids = []
        for _ in range(80):
            self.asteroids.append({
                "r": 75 + random.randint(-3, 3),
                "angle": random.uniform(0, 2 * math.pi),
                "size": random.uniform(0.5, 1.2),
                "speed": random.uniform(0.008, 0.02)
            })
        self.stars = [(random.randint(0, self.width), random.randint(0, self.height),
                       random.uniform(0.5, 1.5)) for _ in range(50)]

    def update(self):
        if not self.active:
            return
        self.canvas.delete("all")

        # Nền vũ trụ
        self.canvas.create_rectangle(0, 0, self.width, self.height, fill="#050510", outline="")

        # Sao nền nhấp nháy
        for sx, sy, br in self.stars:
            pulse = 0.6 + 0.4 * math.sin(time.time() * 2 + sx * 0.1)
            gray = int(200 * pulse * br)
            color = "#%02x%02x%02x" % (gray, gray, gray)
            self.canvas.create_oval(sx, sy, sx + 1.5, sy + 1.5, fill=color, outline="")

        cx, cy = self.width / 2, self.height / 2

        # === Mặt Trời ===
        # Quầng ngoài
        for i in range(3):
            r_sun = 25 + i * 5
            alpha = 0.4 - i * 0.1
            fill_color = "#%02x%02x%02x" % (255, 200 - i * 20, 0)
            self.canvas.create_oval(cx - r_sun, cy - r_sun, cx + r_sun, cy + r_sun,
                                    fill=fill_color, outline="", stipple="gray25")
        # Thân chính
        self.canvas.create_oval(cx - 22, cy - 22, cx + 22, cy + 22, fill="#F9E79F", outline="")
        self.canvas.create_oval(cx - 18, cy - 18, cx + 18, cy + 18, fill="#F1C40F", outline="#E67E22", width=1)
        # Tia lửa mặt trời
        for a in range(0, 360, 30):
            rad = math.radians(a + time.time() * 10)
            x1 = cx + 26 * math.cos(rad)
            y1 = cy + 26 * math.sin(rad)
            x2 = cx + 32 * math.cos(rad + 0.2)
            y2 = cy + 32 * math.sin(rad + 0.2)
            self.canvas.create_line(x1, y1, x2, y2, fill="#FFC300", width=2)

        # Vẽ vành đai tiểu hành tinh (giữa hành tinh 2 và 3)
        for ast in self.asteroids:
            ast["angle"] += ast["speed"]
            px = cx + ast["r"] * math.cos(ast["angle"])
            py = cy + ast["r"] * math.sin(ast["angle"])
            self.canvas.create_oval(px - ast["size"], py - ast["size"],
                                    px + ast["size"], py + ast["size"],
                                    fill="#BDC3C7", outline="")

        # Vẽ các hành tinh
        for idx, p in enumerate(self.planets):
            p["angle"] += p["speed"]
            px = cx + p["r"] * math.cos(p["angle"])
            py = cy + p["r"] * math.sin(p["angle"])
            s, c = p["size"], p["color"]
            p["self_rot"] += 0.02  # tự quay

            # Quỹ đạo
            self.canvas.create_oval(cx - p["r"], cy - p["r"],
                                    cx + p["r"], cy + p["r"],
                                    outline="#1B2631", dash=(2, 5))

            # Vẽ hành tinh
            self.canvas.create_oval(px - s, py - s, px + s, py + s, fill=c, outline="#2C3E50", width=1)

            # Chi tiết bề mặt theo loại
            if p["type"] == "rocky":
                # Miệng núi lửa
                for _ in range(4):
                    a_crat = random.uniform(0, 2 * math.pi) + p["self_rot"]
                    cr = random.uniform(s * 0.15, s * 0.3)
                    cx_c = px + (s - cr) * 0.5 * math.cos(a_crat)
                    cy_c = py + (s - cr) * 0.5 * math.sin(a_crat)
                    self.canvas.create_oval(cx_c - cr, cy_c - cr, cx_c + cr, cy_c + cr,
                                            fill="#95A5A6", outline="#7F8C8D")
            elif p["type"] == "gas":
                # Dải mây
                for i in range(-2, 3):
                    self.canvas.create_line(px - s * 0.9, py + i * s * 0.25,
                                            px + s * 0.9, py + i * s * 0.25,
                                            fill="#1B4F72", width=2, stipple="gray25")
            elif p["type"] == "ringed":
                # Vành đai nghiêng
                ring_angle = p["angle"] * 0.8
                dx = math.cos(ring_angle)
                dy = math.sin(ring_angle)
                for w in [1, 2, 3]:
                    self.canvas.create_oval(px + dx * (s + w * 3) - s * 0.6,
                                            py + dy * (s + w * 3) * 0.3 - s * 0.3,
                                            px + dx * (s + w * 3) + s * 0.6,
                                            py + dy * (s + w * 3) * 0.3 + s * 0.3,
                                            outline="#8E44AD", width=1, dash=(3, 3))
                # Bề mặt khí
                self.canvas.create_arc(px - s, py - s, px + s, py + s,
                                       start=p["self_rot"] * 50, extent=120,
                                       fill="#D2B4DE", outline="", stipple="gray25")
            elif p["type"] == "jupiter":
                # Dải màu
                stripes_colors = ["#D35400", "#F39C12", "#E67E22", "#A04000"]
                for i, stripe_c in enumerate(stripes_colors):
                    self.canvas.create_rectangle(px - s, py - s + i * s * 0.35,
                                                 px + s, py - s + (i + 1) * s * 0.35,
                                                 fill=stripe_c, outline="", stipple="gray25")
                # Bão đỏ
                self.canvas.create_oval(px + s * 0.3, py - s * 0.2,
                                        px + s * 0.7, py + s * 0.2,
                                        fill="#E74C3C", outline="")

        # Vẽ mặt trăng
        for moon in self.moons:
            p = self.planets[moon["planet_idx"]]
            moon["angle"] += moon["speed"]
            mx = cx + p["r"] * math.cos(p["angle"]) + moon["distance"] * math.cos(moon["angle"])
            my = cy + p["r"] * math.sin(p["angle"]) + moon["distance"] * math.sin(moon["angle"])
            self.canvas.create_oval(mx - moon["size"], my - moon["size"],
                                    mx + moon["size"], my + moon["size"],
                                    fill=moon["color"], outline="#FFFFFF")

        self.after_id = self.canvas.after(30, self.update)
class AquariumGame(MiniGame):
    def __init__(self, canvas, width, height):
        super().__init__(canvas, width, height)
        self.fishes = []
        self.bubbles = []
        self.seaweeds = []      # vị trí rong biển
        self.light_rays = []    # tia nắng
        self.reset()

    def reset(self):
        self.fishes = []
        colors = ["#FF7F50", "#F4D03F", "#5DADE2", "#F369B4", "#82E0AA", "#E67E22",
                  "#C39BD3", "#48C9B0", "#F5B041", "#EC7063"]
        for _ in range(6):
            self.fishes.append({
                "x": random.randint(50, self.width - 50),
                "y": random.randint(30, self.height - 80),
                "vx": random.uniform(0.5, 1.4) * random.choice([-1, 1]),
                "vy": random.uniform(-0.2, 0.2),
                "color": random.choice(colors),
                "size": random.randint(18, 30),
                "wiggle": random.uniform(0, 6),
                "type": random.choice(["normal", "flat", "long"]),
                "bubble_timer": random.randint(0, 30)
            })
        self.bubbles = []
        # Rong biển mọc cố định ở đáy
        self.seaweeds = [{"x": x, "ph": random.randint(30, 60)} for x in range(40, self.width, 50)]
        # Tia nắng
        self.light_rays = [{"x": x, "alpha": random.uniform(0.3, 0.7)} for x in range(20, self.width, 30)]
        self.anim_time = 0

    def update(self):
        if not self.active:
            return
        self.canvas.delete("all")
        self.anim_time += 0.05

        # Nền xanh đại dương
        self.canvas.create_rectangle(0, 0, self.width, self.height, fill="#0A3D6B", outline="")
        # Lớp nước sâu có gradient giả
        for i in range(5):
            alpha = abs(math.sin(self.anim_time * 0.4 + i))
            shade = "#%02x%02x%02x" % (10, 50 + int(alpha * 20), 100 + int(alpha * 30))
            self.canvas.create_rectangle(0, self.height // 5 * i, self.width, self.height // 5 * (i + 1),
                                         fill=shade, outline="", stipple="gray25")

        # Đáy cát
        self.canvas.create_rectangle(0, self.height - 25, self.width, self.height,
                                     fill="#C2A36B", outline="")
        for _ in range(20):
            sx, sy = random.randint(0, self.width), self.height - 25 + random.randint(0, 20)
            self.canvas.create_oval(sx, sy, sx + random.randint(2, 4), sy + 2,
                                    fill="#D4B87A", outline="")

        # Tia nắng từ mặt nước
        for ray in self.light_rays:
            rx = ray["x"] + math.sin(self.anim_time + ray["x"]) * 10
            self.canvas.create_polygon(rx, 0, rx + 10, 0, rx + 30, self.height - 30,
                                       rx - 20, self.height - 30,
                                       fill="#FFFF99", outline="", stipple="gray12")

        # Rong biển mềm mại uốn lượn
        for sw in self.seaweeds:
            points = []
            for i in range(sw["ph"] // 5):
                offset = math.sin(self.anim_time * 2 + sw["x"] * 0.1 + i * 0.4) * (4 + i * 0.3)
                points.extend([sw["x"] + offset, self.height - 25 - i * 5])
            self.canvas.create_line(points, fill="#1E8449", width=3, smooth=True)

        # Cập nhật cá
        for f in self.fishes:
            # Chuyển động ngang + dọc nhẹ
            f["x"] += f["vx"]
            f["y"] += f["vy"] + math.sin(self.anim_time * 3 + f["wiggle"]) * 0.15
            if f["x"] > self.width - 30 or f["x"] < 30:
                f["vx"] = -f["vx"]
            if f["y"] < 20 or f["y"] > self.height - 50:
                f["vy"] = -f["vy"]
            f["wiggle"] += 0.3

            dir = 1 if f["vx"] > 0 else -1
            s, c = f["size"], f["color"]
            tw = math.sin(f["wiggle"]) * 5.0      # đuôi vẫy
            bw = math.cos(f["wiggle"] * 1.3) * 3.0 # vây bụng

            # --- Vẽ đuôi (tùy loại cá) ---
            tx = f["x"] - dir * s * 0.8
            if f["type"] == "flat":
                # Đuôi xòe ngang
                self.canvas.create_polygon(
                    tx, f["y"],
                    tx - dir * s * 0.8, f["y"] - s * 0.4 + tw,
                    tx - dir * s * 0.6, f["y"],
                    tx - dir * s * 0.8, f["y"] + s * 0.4 - tw,
                    fill=c, outline="#1C2833", width=1, smooth=True
                )
            elif f["type"] == "long":
                # Đuôi dài, mảnh
                self.canvas.create_polygon(
                    tx, f["y"],
                    tx - dir * s * 1.2, f["y"] - s * 0.2 + tw,
                    tx - dir * s * 1.0, f["y"],
                    tx - dir * s * 1.2, f["y"] + s * 0.2 - tw,
                    fill=c, outline="#1C2833", width=1, smooth=True
                )
            else:  # normal
                self.canvas.create_polygon(
                    tx, f["y"],
                    tx - dir * s * 0.6, f["y"] - s * 0.45 + tw,
                    tx - dir * s * 0.5, f["y"],
                    tx - dir * s * 0.6, f["y"] + s * 0.45 - tw,
                    fill=c, outline="#1C2833", width=1, smooth=True
                )

            # Vây lưng & vây bụng mờ
            self.canvas.create_polygon(
                f["x"] - dir * s * 0.2, f["y"] - s * 0.45,
                f["x"] - dir * s * 0.6, f["y"] - s * 0.8 + bw,
                f["x"] - dir * s * 0.9, f["y"] - s * 0.3,
                fill="#1C2833", outline="", stipple="gray25", smooth=True
            )
            self.canvas.create_polygon(
                f["x"] - dir * s * 0.2, f["y"] + s * 0.45,
                f["x"] - dir * s * 0.6, f["y"] + s * 0.8 - bw,
                f["x"] - dir * s * 0.9, f["y"] + s * 0.3,
                fill="#1C2833", outline="", stipple="gray25", smooth=True
            )

            # Thân cá (hình oval chính)
            body_w = s * (1.6 if f["type"] == "flat" else 1.0)
            body_h = s * (0.6 if f["type"] == "flat" else 0.9 if f["type"] == "long" else 1.0)
            self.canvas.create_oval(f["x"] - body_w, f["y"] - body_h * 0.6,
                                    f["x"] + body_w, f["y"] + body_h * 0.6,
                                    fill=c, outline="#1C2833", width=1)

            # Vân sáng trên thân
            self.canvas.create_polygon(
                f["x"] - body_w * 0.3, f["y"] - body_h * 0.2,
                f["x"] + body_w * 0.4, f["y"],
                f["x"] - body_w * 0.3, f["y"] + body_h * 0.2,
                fill="#FFFFFF", outline="", stipple="gray25", smooth=True
            )

            # Mắt + mang
            ex = f["x"] + dir * body_w * 0.6
            mx = f["x"] + dir * body_w * 0.3
            self.canvas.create_arc(mx - body_w * 0.15, f["y"] - body_h * 0.35,
                                   mx + body_w * 0.15, f["y"] + body_h * 0.35,
                                   start=120 * dir, extent=120, style=tk.ARC,
                                   outline="#1C2833", width=1)
            self.canvas.create_oval(ex - 4, f["y"] - 4, ex + 4, f["y"] + 4,
                                    fill="white", outline="black")
            self.canvas.create_oval(ex - 1.5, f["y"] - 2, ex + 2, f["y"] + 1.5,
                                    fill="black", outline="")

            # Bong bóng từ cá (ngẫu nhiên)
            f["bubble_timer"] -= 1
            if f["bubble_timer"] <= 0:
                f["bubble_timer"] = random.randint(25, 70)
                bx = f["x"] + dir * body_w * 0.7
                by = f["y"] - 2
                self.bubbles.append({"x": bx, "y": by, "r": random.uniform(2, 5)})

        # Xử lý bọt nước chung
        for b in self.bubbles[:]:
            b["y"] -= random.uniform(1.0, 2.8)
            b["x"] += math.sin(self.anim_time * 5 + b["x"] * 0.1) * 0.5
            self.canvas.create_oval(b["x"] - b["r"], b["y"] - b["r"],
                                    b["x"] + b["r"], b["y"] + b["r"],
                                    outline="#AED6F1", width=1)
            if b["y"] < -10:
                self.bubbles.remove(b)

        self.after_id = self.canvas.after(30, self.update)
# --- Game 5 MỚI: Tuyết Rơi thư giãn (Snowfall) ---
class SnowfallGame(MiniGame):
    def __init__(self, canvas, width, height):
        super().__init__(canvas, width, height)
        self.flakes = []
        self.reset()

    def reset(self):
        self.flakes = []
        for _ in range(50):
            self.flakes.append(self.create_flake(True))

    def create_flake(self, random_y=False):
        return {
            "x": random.randint(0, self.width),
            "y": random.randint(0, self.height) if random_y else -10,
            "vy": random.uniform(1, 3),
            "r": random.uniform(1.5, 4),
            "drift": random.uniform(-0.5, 0.5)
        }

    def update(self):
        if not self.active: return
        self.canvas.delete("all")
        
        # Nền trời đông tối
        self.canvas.create_rectangle(0, 0, self.width, self.height, fill="#0A0F1E", outline="")

        # Tuyết rơi
        for f in self.flakes:
            f["y"] += f["vy"]
            f["x"] += f["drift"] + math.sin(time.time() + f["vy"]) * 0.3
            
            self.canvas.create_oval(f["x"]-f["r"], f["y"]-f["r"], f["x"]+f["r"], f["y"]+f["r"], fill="#FFFFFF", outline="")
            
            # Reset khi tuyết rơi xuống đáy
            if f["y"] > self.height + 10:
                f["y"] = -10
                f["x"] = random.randint(0, self.width)

        self.after_id = self.canvas.after(30, self.update)


# =========================== ỨNG DỤNG ĐỒNG HỒ ===========================
class StudyTimer:
    def __init__(self, root):
        self.root = root
        self.root.title("⏳ Study Timer - Giao diện Đẹp")
        self.root.geometry("780x500")
        
        self.bg_color = "#121212"       
        self.frame_bg = "#1E1E1E"       
        
        # Cập nhật tông màu DỊU HƠN để mitigate răng cưa
        self.green_accent = "#20B2AA"   # Xanh ngọc sẫm (LightSeaGreen) dịu mắt
        self.red_accent = "#CD5C5C"     # Đỏ sẫm nhạt (IndianRed)
        
        self.text_color = "#FFFFFF"     
        self.sub_color = "#AAAAAA"      
        
        self.root.configure(bg=self.bg_color)
        self.root.resizable(False, False)

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

        self.current_game = None
        self.game_map = {}

        self.build_ui()
        self.switch_game("dino_runner")
        self.update_timer_display()

    def build_ui(self):
        left_frame = tk.Frame(self.root, bg=self.bg_color, width=400, height=500)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=15, pady=15)
        left_frame.pack_propagate(False)

        tk.Label(left_frame, text="⏳ STUDY TIMER", font=("Segoe UI", 20, "bold"), fg=self.text_color, bg=self.bg_color).pack(pady=(5,2))
        tk.Label(left_frame, text="Phương pháp Pomodoro", font=("Segoe UI", 10), fg=self.sub_color, bg=self.bg_color).pack(pady=(0, 10))

        canvas_frame = tk.Frame(left_frame, bg=self.bg_color)
        canvas_frame.pack()
        self.canvas = tk.Canvas(canvas_frame, width=240, height=240, bg=self.bg_color, highlightthickness=0)
        self.canvas.pack()
        self.canvas.create_oval(20, 20, 220, 220, outline="#2A2A2A", width=12)
        # Thanh progress, mặc định màu xanh dịu
        self.progress_arc = self.canvas.create_arc(20, 20, 220, 220, start=90, extent=-360, outline=self.green_accent, width=12, style=tk.ARC)
        
        self.timer_text = self.canvas.create_text(120, 100, text="25:00", font=("Segoe UI", 40, "bold"), fill=self.text_color)
        self.status_text = self.canvas.create_text(120, 145, text="HỌC TẬP", font=("Segoe UI", 12, "bold"), fill=self.green_accent)
        self.count_text = self.canvas.create_text(120, 175, text="🍅 x 0", font=("Segoe UI", 11), fill=self.sub_color)

        self.notif_label = tk.Label(left_frame, text="", font=("Segoe UI", 10, "italic"), fg="#FFD700", bg=self.bg_color)
        self.notif_label.pack(pady=5)

        btn_frame = tk.Frame(left_frame, bg=self.bg_color)
        btn_frame.pack(pady=5)
        
        self.start_pause_btn = tk.Button(btn_frame, text="▶ BẮT ĐẦU", font=("Segoe UI", 11, "bold"), bg=self.green_accent, fg="#000000", activebackground="#32CD32", relief=tk.FLAT, bd=0, width=12, pady=5, cursor="hand2", command=self.start_pause)
        self.start_pause_btn.grid(row=0, column=0, padx=5)
        
        self.reset_btn = tk.Button(btn_frame, text="↺ ĐẶT LẠI", font=("Segoe UI", 11, "bold"), bg="#333333", fg=self.text_color, activebackground="#555555", relief=tk.FLAT, bd=0, width=10, pady=5, cursor="hand2", command=self.reset)
        self.reset_btn.grid(row=0, column=1, padx=5)
        
        self.skip_btn = tk.Button(btn_frame, text="⏭ BỎ QUA", font=("Segoe UI", 11, "bold"), bg=self.red_accent, fg="#FFFFFF", activebackground="#FF6347", relief=tk.FLAT, bd=0, width=10, pady=5, cursor="hand2", command=self.skip)
        self.skip_btn.grid(row=0, column=2, padx=5)

        setting_frame = tk.Frame(left_frame, bg=self.frame_bg)
        setting_frame.pack(pady=15, fill=tk.X, padx=10)
        
        fields = [("📚 Học:", "study", 25), ("☕ Nghỉ ngắn:", "short_break", 5), ("😴 Nghỉ dài:", "long_break", 15)]
        
        for i, (label_text, attr, default) in enumerate(fields):
            tk.Label(setting_frame, text=label_text, font=("Segoe UI", 10), fg=self.sub_color, bg=self.frame_bg).grid(row=0, column=i*2, padx=(10, 2), pady=10)
            entry = tk.Entry(setting_frame, font=("Segoe UI", 10, "bold"), bg="#333333", fg=self.text_color, relief=tk.FLAT, width=4, justify=tk.CENTER)
            entry.insert(0, str(default))
            entry.grid(row=0, column=i*2+1, padx=(0, 10))
            setattr(self, f"{attr}_entry", entry)

        self.apply_btn = tk.Button(setting_frame, text="✓ LƯU", font=("Segoe UI", 9, "bold"), bg="#333333", fg=self.text_color, relief=tk.FLAT, command=self.apply_settings, cursor="hand2")
        self.apply_btn.grid(row=1, column=0, columnspan=6, pady=(0, 10), ipadx=20)

        right_frame = tk.Frame(self.root, bg=self.frame_bg, width=340, height=500)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(0,15), pady=15)
        right_frame.pack_propagate(False)

        tk.Label(right_frame, text="🎮 CHILL MINI GAME", font=("Segoe UI", 13, "bold"), fg=self.text_color, bg=self.frame_bg).pack(pady=(15, 5))

        game_select = tk.Frame(right_frame, bg=self.frame_bg)
        game_select.pack(pady=5)
        
        self.game_var = tk.StringVar(value="dino_runner")
        style = ttk.Style()
        style.theme_use('clam')
        
        game_combo = ttk.Combobox(game_select, textvariable=self.game_var, state="readonly", width=18, font=("Segoe UI", 10))
        # ---> ĐÃ THÊM TUYẾT RƠI VÀO DANH SÁCH <---
        game_combo['values'] = ("dino_runner", "auto_pong", "solar_orbit", "aquarium", "snowfall")
        game_combo.current(0)
        game_combo.pack()
        game_combo.bind("<<ComboboxSelected>>", lambda e: self.switch_game(self.game_var.get()))

        self.game_canvas = tk.Canvas(right_frame, width=300, height=200, bg="#F7F7F7", highlightthickness=2, highlightbackground="#333333")
        self.game_canvas.pack(pady=15)

        tk.Label(right_frame, text="Nhìn game tự chơi để mắt được nghỉ ngơi nhé 👀", font=("Segoe UI", 9, "italic"), fg=self.sub_color, bg=self.frame_bg).pack()

    def init_game(self, game_key):
        if self.current_game:
            self.current_game.stop()
        w, h = 300, 200
        if game_key == "dino_runner": game = DinoRunnerGame(self.game_canvas, w, h)
        elif game_key == "auto_pong": game = AutoPongGame(self.game_canvas, w, h)
        elif game_key == "solar_orbit": game = SolarOrbitGame(self.game_canvas, w, h)
        elif game_key == "aquarium": game = AquariumGame(self.game_canvas, w, h)
        elif game_key == "snowfall": game = SnowfallGame(self.game_canvas, w, h)
        else: return
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
        # Dùng ceil để làm tròn giây lên khi hiển thị số
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
            # Cập nhật liên tục mỗi 50ms để progress bar mượt
            self.current_time_left = max(0, self.end_time - time.time())
            self.update_timer_display()
            if self.current_time_left > 0:
                # Chạy lại sau 50ms (20 frame/giây)
                self.after_id = self.root.after(50, self.countdown)
            else:
                self.timer_finished()

    def timer_finished(self):
        self.is_running = False
        self.start_pause_btn.config(text="▶ BẮT ĐẦU", bg=self.green_accent, fg="#000000")
        if self.current_game:
            self.current_game.stop() 

        if self.is_study:
            self.pomodoro_count += 1
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
            
            # Tính thời điểm kết thúc dựa trên thời gian hiện tại
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
            
            # Tính lại thời điểm kết thúc mới
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
            self.current_game.stop()
        self.update_timer_display()
        self.show_notification(msg)

    def apply_settings(self):
        try:
            study = int(self.study_entry.get())
            short = int(self.short_break_entry.get())
            long = int(self.long_break_entry.get())
            if study <= 0 or short <= 0 or long <= 0: raise ValueError
            self.study_time = study * 60
            self.short_break = short * 60
            self.long_break = long * 60
            if self.after_id: self.root.after_cancel(self.after_id)
            self.is_running = False
            self.is_paused = False
            self.is_study = True
            self.current_time_left = self.study_time
            self.start_pause_btn.config(text="▶ BẮT ĐẦU", bg=self.green_accent, fg="#000000")
            if self.current_game: self.current_game.stop()
            self.update_timer_display()
            self.show_notification("✓ Đã lưu cài đặt mới")
        except ValueError:
            self.show_notification("⚠️ Hãy nhập số phút hợp lệ nhé!")

if __name__ == "__main__":
    root = tk.Tk()
    app = StudyTimer(root)
    root.mainloop()