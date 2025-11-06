import os
import tkinter as tk
from tkinter import filedialog, Listbox, Scrollbar, END, simpledialog, messagebox
from PIL import Image, ImageTk
import cv2

class ImageLabelingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("TrOCR Labeling (BETA)")
        self.root.geometry("1350x760")
        self.root.minsize(1000, 600)

        icon_path = "label.ico"
        if os.path.exists(icon_path):
            self.root.iconbitmap(icon_path)

        self.image_dir = ""
        self.image_files = []
        self.current_idx = -1
        self.original_image = None
        self.photo = None
        self.drawing = False
        self.start_x = self.start_y = 0
        self.rect = None
        self.boxes = []
        self.scale = 1.0
        self.display_w = self.display_h = 0
        self.crops_dir = os.path.join(os.getcwd(), "crops")

        self.setup_ui()
        os.makedirs(self.crops_dir, exist_ok=True)

    def setup_ui(self):
        left_panel = tk.Frame(self.root, bg="#2c3e50", width=320)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(10, 5), pady=10)
        left_panel.pack_propagate(False)

        title = tk.Label(left_panel, text="Daftar Gambar", font=("Segoe UI", 13, "bold"), fg="white", bg="#2c3e50")
        title.pack(pady=(20, 10))

        btn_open = tk.Button(left_panel, text="Buka Folder", command=self.open_folder,
                             bg="#3498db", fg="white", font=("Segoe UI", 10, "bold"), relief="flat", cursor="hand2")
        btn_open.pack(pady=8, padx=20, fill=tk.X)

        list_frame = tk.Frame(left_panel, bg="white", relief="sunken", bd=2)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        self.scrollbar = Scrollbar(list_frame, bg="#bdc3c7")
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox = Listbox(list_frame, yscrollcommand=self.scrollbar.set, font=("Consolas", 10),
                               bg="white", fg="#2c3e50", selectbackground="#3498db", relief="flat")
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.config(command=self.listbox.yview)
        self.listbox.bind('<<ListboxSelect>>', self.on_select_image)

        right_panel = tk.Frame(self.root, bg="#ecf0f1")
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 10), pady=10)

        ctrl_frame = tk.Frame(right_panel, bg="#ecf0f1")
        ctrl_frame.pack(pady=(10, 5), fill=tk.X)

        self.btn_label = tk.Button(ctrl_frame, text="Label", font=("Segoe UI", 20), bg="#e74c3c", fg="white",
                                   width=4, relief="raised", cursor="hand2", command=self.toggle_label_mode)
        self.btn_label.pack(side=tk.LEFT, padx=8)

        self.btn_export = tk.Button(ctrl_frame, text="EKSPOR", font=("Segoe UI", 12, "bold"), bg="#27ae60", fg="white",
                                    state=tk.DISABLED, relief="raised", cursor="hand2", command=self.export_all)
        self.btn_export.pack(side=tk.LEFT, padx=8)

        self.status = tk.Label(ctrl_frame, text="Pilih gambar untuk mulai", fg="#7f8c8d", bg="#ecf0f1", font=("Segoe UI", 10))
        self.status.pack(side=tk.LEFT, padx=20)
        image_frame = tk.Frame(right_panel, bg="white", relief="solid", bd=3)
        image_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        self.canvas = tk.Canvas(image_frame, bg="#f8f9fa", highlightthickness=0, cursor="cross")
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

    def open_folder(self):
        self.image_dir = filedialog.askdirectory(title="Pilih Folder Gambar")
        if not self.image_dir: return
        self.image_files = sorted([f for f in os.listdir(self.image_dir)
                                   if f.lower().endswith(('.jpg','.jpeg','.png','.bmp'))])
        self.listbox.delete(0, END)
        for f in self.image_files: self.listbox.insert(END, f)
        if self.image_files:
            self.listbox.select_set(0)
            self.on_select_image()

    def on_select_image(self, event=None):
        sel = self.listbox.curselection()
        if not sel: return
        self.current_idx = sel[0]
        path = os.path.join(self.image_dir, self.image_files[self.current_idx])

        img = cv2.imread(path)
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        self.original_image = img_rgb.copy()

        h, w = img_rgb.shape[:2]
        max_w, max_h = 900, 600
        self.scale = min(max_w/w, max_h/h)
        self.display_w = int(w * self.scale)
        self.display_h = int(h * self.scale)

        disp = cv2.resize(img_rgb, (self.display_w, self.display_h))
        self.photo = ImageTk.PhotoImage(Image.fromarray(disp))
        self.canvas.config(width=self.display_w, height=self.display_h)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)

        self.boxes = []
        self.redraw_boxes()
        self.btn_export.config(state=tk.DISABLED)
        self.status.config(text=f"Loaded: {self.image_files[self.current_idx]}")

    def redraw_boxes(self):
        self.canvas.delete("box")
        for x1,y1,x2,y2,label,_ in self.boxes:
            sx1 = x1 * self.scale
            sy1 = y1 * self.scale
            sx2 = x2 * self.scale
            sy2 = y2 * self.scale
            self.canvas.create_rectangle(sx1,sy1,sx2,sy2, outline="#e74c3c", width=3, tags="box")
            self.canvas.create_text(sx1+8, sy1+5, text=label, fill="#e74c3c", font=("Segoe UI", 10, "bold"), anchor=tk.NW, tags="box")

    def toggle_label_mode(self):
        if self.current_idx < 0: return
        self.drawing = True
        self.btn_label.config(bg="#27ae60")
        self.status.config(text="Drag kotak → ketik label (cancel = batal)", fg="#27ae60")

    def on_press(self, e):
        if not self.drawing: return
        self.start_x, self.start_y = e.x, e.y
        if self.rect: self.canvas.delete(self.rect)
        self.rect = self.canvas.create_rectangle(e.x, e.y, e.x, e.y, outline="#f1c40f", width=3)

    def on_drag(self, e):
        if not self.drawing or not self.rect: return
        self.canvas.coords(self.rect, self.start_x, self.start_y, e.x, e.y)

    def on_release(self, e):
        if not self.drawing or not self.rect: return

        x1, y1 = self.start_x, self.start_y
        x2, y2 = e.x, e.y
        if x1 > x2: x1, x2 = x2, x1
        if y1 > y2: y1, y2 = y2, y1

        ox1 = int(x1 / self.scale)
        oy1 = int(y1 / self.scale)
        ox2 = int(x2 / self.scale)
        oy2 = int(y2 / self.scale)

        crop = self.original_image[oy1:oy2, ox1:ox2]

        txt = simpledialog.askstring("Label", "Masukkan label\n(ketik 'cancel' untuk batal)", parent=self.root)
        if txt is None or txt.strip().lower() == "cancel":
            self.canvas.delete(self.rect)
            self.rect = None
            self.drawing = False
            self.btn_label.config(bg="#e74c3c")
            self.status.config(text="Dibatalkan", fg="orange")
            return

        label = txt.strip() or "unknown"
        self.boxes.append([ox1, oy1, ox2, oy2, label, crop])
        self.redraw_boxes()

        self.canvas.delete(self.rect)
        self.rect = None
        self.drawing = False
        self.btn_label.config(bg="#e74c3c")
        self.status.config(text=f"Disimpan: {label}", fg="#27ae60")
        self.btn_export.config(state=tk.NORMAL)

    def export_all(self):
        if not self.boxes:
            messagebox.showinfo("Info", "Belum ada objek")
            return

        base = os.path.splitext(self.image_files[self.current_idx])[0]
        lines = []

        for i, (x1,y1,x2,y2,label,crop) in enumerate(self.boxes, 1):
            name = f"{base}_{i:03d}.jpg"
            cv2.imwrite(os.path.join(self.crops_dir, name), cv2.cvtColor(crop, cv2.COLOR_RGB2BGR))
            lines.append(f"{name}\t{label}")

        with open("labels.txt", "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

        messagebox.showinfo("Sukses!", f"{len(lines)} objek diekspor ke crops/ & labels.txt")
        self.boxes = []
        self.redraw_boxes()
        self.btn_export.config(state=tk.DISABLED)
        self.status.config(text="Ekspor selesai!", fg="#27ae60")


if __name__ == "__main__":
    root = tk.Tk()
    app = ImageLabelingApp(root)
    root.mainloop()