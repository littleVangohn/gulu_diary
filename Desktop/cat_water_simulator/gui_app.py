# gui_app.py
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import numpy as np
import random
from core.water_recommender import get_recommended_range

class CatWaterSimulator:
    def __init__(self, root):
        self.root = root
        self.root.title("🐱 小猫饮水模拟器 - 阶段一")
        self.root.geometry("420x540")
        self.root.resizable(False, False)

        self.recommended_min = 0
        self.recommended_max = 0
        self.actual = 0.0
        self.is_running = False
        self.drinks = []

        self.create_widgets()

    def create_widgets(self):
        ttk.Label(self.root, text="请选择猫的品种：", font=("Arial", 10)).pack(pady=(15, 5))
        self.breed_var = tk.StringVar()
        breeds = ["英国短毛猫", "美国短毛猫", "布偶猫", "暹罗猫", "波斯猫", "缅因猫", "其他"]
        self.breed_combo = ttk.Combobox(self.root, textvariable=self.breed_var, values=breeds, state="readonly", width=15)
        self.breed_combo.pack()
        self.breed_combo.set("英国短毛猫")

        ttk.Label(self.root, text="请输入猫的年龄（岁）：", font=("Arial", 10)).pack(pady=(15, 5))
        self.age_var = tk.StringVar(value="2")
        age_frame = ttk.Frame(self.root)
        age_frame.pack()
        ttk.Entry(age_frame, textvariable=self.age_var, width=10).pack(side=tk.LEFT)
        ttk.Label(age_frame, text="岁").pack(side=tk.LEFT, padx=(5, 0))

        self.start_button = ttk.Button(self.root, text="开始模拟", command=self.start_simulation)
        self.start_button.pack(pady=15)

        self.info_label = ttk.Label(self.root, text="", font=("Arial", 10), foreground="gray")
        self.info_label.pack()

        self.status_label = ttk.Label(self.root, text="", font=("Arial", 12, "bold"))
        self.status_label.pack(pady=5)

        self.tip_label = ttk.Label(self.root, text="", font=("Arial", 9), foreground="gray")
        self.tip_label.pack()

        self.log_text = tk.Text(self.root, height=14, width=50, wrap="word", font=("Consolas", 9))
        self.log_text.pack(pady=10, padx=10)

    def start_simulation(self):
        if self.is_running:
            return
        try:
            age = int(self.age_var.get())
            if age < 0 or age > 30:
                raise ValueError("年龄应在 0~30 之间")
            breed = self.breed_var.get()
            
            self.recommended_min, self.recommended_max = get_recommended_range(breed, age)
            self.is_running = True
            
            self.log_text.delete('1.0', tk.END)
            self.info_label.config(text=f"推荐每日饮水量：{self.recommended_min} ~ {self.recommended_max} ml")
            self.status_label.config(text="正在模拟...", foreground="blue")
            self.tip_label.config(text="")
            self.start_button.config(state="disabled")
            
            thread = threading.Thread(target=self._simulate_drinking, args=(breed, age))
            thread.daemon = True
            thread.start()
            
        except ValueError as e:
            messagebox.showerror("输入错误", f"请输入有效的年龄数字！\n{str(e)}")

    def _simulate_drinking(self, breed, age):
        # ✅ 使用 numpy 正态分布生成总量
        loc = (self.recommended_min + self.recommended_max) / 2.0
        scale = max(5.0, (self.recommended_max - self.recommended_min) / 4.0)
        total_ml = np.random.normal(loc=loc, scale=scale, size=1)[0]

        # ✅ 截断防止极端值
        total_ml = max(self.recommended_min * 0.7, min(total_ml, self.recommended_max * 1.3))
        self.actual = round(max(10.0, total_ml), 1)

        # 分解为多次饮水事件
        drinks_list = []
        num_drinks = random.randint(4, 8)
        min_per = 5.0
        if self.actual < num_drinks * min_per:
            num_drinks = max(1, int(self.actual / min_per))

        proportions = [random.random() for _ in range(num_drinks)]
        total_prop = sum(proportions)
        remaining = self.actual

        for i in range(num_drinks - 1):
            amount = max(min_per, (proportions[i] / total_prop) * self.actual)
            amount = min(amount, remaining - (num_drinks - i - 1) * min_per)
            drinks_list.append(round(amount, 1))
            remaining -= amount
        drinks_list.append(round(remaining, 1))

        # 生成时间序列
        current_time_min = random.randint(0, 360)
        self.drinks = []

        for i, amount in enumerate(drinks_list):
            hour = current_time_min // 60
            minute = current_time_min % 60
            time_str = f"{hour:02d}:{minute:02d}"
            self.drinks.append((time_str, amount))

            self.root.after(0, lambda ts=time_str, amt=amount: self._append_log(ts, amt))
            time.sleep(random.uniform(2, 5))

            if i < len(drinks_list) - 1:
                interval = random.randint(30, 150) if i < 2 else random.randint(120, 300)
                current_time_min = min(1439, current_time_min + interval)

        self.is_running = False
        self.root.after(0, self._final_evaluation)

    def _append_log(self, time_str, amount):
        self.log_text.insert(tk.END, f"[{time_str}] 饮水 {amount} ml\n")
        self.log_text.see(tk.END)

    def _final_evaluation(self):
        if self.actual < self.recommended_min:
            status_text = f"今日总量：{self.actual:.1f} ml → ❌ 未达标（不足）"
            color = "orange"
            tip = "💧 温馨提醒：你家小猫该多喝点水啦！"
        elif self.actual > self.recommended_max:
            status_text = f"今日总量：{self.actual:.1f} ml → ⚠️ 超标（过多）"
            color = "red"
            tip = ""
        else:
            status_text = f"今日总量：{self.actual:.1f} ml → ✅ 达标"
            color = "green"
            tip = ""
            
        self.status_label.config(text=status_text, foreground=color)
        self.tip_label.config(text=tip)
        self.start_button.config(state="normal")

if __name__ == "__main__":
    root = tk.Tk()
    app = CatWaterSimulator(root)
    root.mainloop()