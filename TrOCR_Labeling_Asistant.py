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
        self.scale = 1.0
        self.display_w = self.display_h = 0
        self.crops_dir = os.path.join(os.getcwd(), "crops")
        self.current_mode = None 
        self.drawing = False
        self.start_x = self.start_y = 0
        self.rect = None
        self.boxes = []
        self.selected_box = None
        self.drag_data = {}

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

        self.btn_label = tk.Button(ctrl_frame, text="LABEL", font=("Segoe UI", 20), bg="#e74c3c", fg="white",
                                   width=6, relief="raised", cursor="hand2", command=lambda: self.set_mode("label"))
        self.btn_label.pack(side=tk.LEFT, padx=8)

        self.btn_edit = tk.Button(ctrl_frame, text="EDIT", font=("Segoe UI", 20), bg="#3498db", fg="white",
                                  width=6, relief="raised", cursor="hand2", command=lambda: self.set_mode("edit"))
        self.btn_edit.pack(side=tk.LEFT, padx=8)

        self.btn_export = tk.Button(ctrl_frame, text="EKSPOR", font=("Segoe UI", 12, "bold"), bg="#27ae60", fg="white",
                                    state=tk.DISABLED, relief="raised", cursor="hand2", command=self.export_all)
        self.btn_export.pack(side=tk.LEFT, padx=8)

        self.status = tk.Label(ctrl_frame, text="Pilih gambar untuk mulai", fg="#7f8c8d", bg="#ecf0f1", font=("Segoe UI", 10))
        self.status.pack(side=tk.LEFT, padx=20)

        image_frame = tk.Frame(right_panel, bg="white", relief="solid", bd=3)
        image_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        self.canvas = tk.Canvas(image_frame, bg="#f8f9fa", highlightthickness=0, cursor="arrow")
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        self.canvas.bind("<ButtonPress-1>", self.on_canvas_press)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        self.canvas.bind("<Button-3>", self.on_box_right_click)

    def set_mode(self, mode):
        if mode == self.current_mode:
            return

        if mode == "label" and self.current_idx < 0:
            messagebox.showinfo("Info", "Pilih gambar terlebih dahulu.")
            return
        if mode == "edit" and (self.current_idx < 0 or not self.boxes):
            messagebox.showinfo("Info", "Belum ada bounding box untuk diedit.")
            return

        self.current_mode = mode
        self.drawing = (mode == "label")
        self.selected_box = None
        self.drag_data = {}
        if self.rect:
            self.canvas.delete(self.rect)
            self.rect = None
        if mode == "label":
            label_bg = "#27ae60"
            label_state = tk.NORMAL
        elif mode == "edit":
            label_bg = "#e74c3c"
            label_state = tk.NORMAL if self.selected_box is None else tk.DISABLED
        else:
            label_bg = "#e74c3c"
            label_state = tk.NORMAL
        self.btn_label.config(bg=label_bg, state=label_state)

        self.btn_edit.config(
            bg="#e67e22" if mode == "edit" else "#3498db",
            state=tk.DISABLED if mode == "label" else tk.NORMAL
        )
        cursor = "cross" if mode == "label" else "hand2" if mode == "edit" else "arrow"
        self.canvas.config(cursor=cursor)

        status_text = {
            "label": "Drag kotak → ketik label (cancel = batal)",
            "edit": "Klik box → drag/resize | Klik kanan → ubah/hapus",
            None: "Pilih gambar untuk mulai"
        }[mode]
        status_color = {"label": "#27ae60", "edit": "#e67e22", None: "#7f8c8d"}[mode]
        self.status.config(text=status_text, fg=status_color)

        self.redraw_boxes()
        self.update_box_bindings()

    def update_box_bindings(self):
        for tag in ["<Button-1>", "<B1-Motion>", "<ButtonRelease-1>", "<Double-Button-1>"]:
            self.canvas.tag_unbind("box", tag)
            self.canvas.tag_unbind("handle", tag)
        self.canvas.unbind("<Button-1>")
        self.canvas.unbind("<B1-Motion>")
        self.canvas.unbind("<ButtonRelease-1>")
        self.canvas.unbind("<Double-Button-1>")

        if self.current_mode == "edit":
            self.canvas.tag_bind("box", "<Button-1>", self.on_edit_click)
            self.canvas.tag_bind("box", "<B1-Motion>", self.on_edit_drag)
            self.canvas.tag_bind("box", "<ButtonRelease-1>", self.on_edit_release)
            self.canvas.tag_bind("box", "<Double-Button-1>", self.on_edit_double_click)
            self.canvas.bind("<Button-1>", self.on_edit_click)
            self.canvas.bind("<B1-Motion>", self.on_edit_drag)
            self.canvas.bind("<ButtonRelease-1>", self.on_edit_release)
            self.canvas.bind("<Double-Button-1>", self.on_edit_double_click)
        else:
            self.canvas.bind("<Button-1>", self.on_canvas_press)
            self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
            self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
            self.canvas.bind("<Double-Button-1>", lambda e: None)

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
        self.set_mode(None)

    def redraw_boxes(self):
        self.canvas.delete("box"); self.canvas.delete("handle")
        for i, (x1,y1,x2,y2,label,_) in enumerate(self.boxes):
            sx1, sy1 = x1*self.scale, y1*self.scale
            sx2, sy2 = x2*self.scale, y2*self.scale
            selected = (self.current_mode == "edit" and i == self.selected_box)
            color = "#f1c40f" if selected else "#e74c3c"
            width = 4 if selected else 3
            self.canvas.create_rectangle(sx1,sy1,sx2,sy2, outline=color, width=width, tags="box")
            self.canvas.create_text(sx1+8, sy1+5, text=label, fill=color, font=("Segoe UI", 10, "bold"), anchor=tk.NW, tags="box")

            if selected:
                handles = [(sx1,sy1),(sx2,sy1),(sx1,sy2),(sx2,sy2),
                           (sx1+(sx2-sx1)/2,sy1),(sx1,sy1+(sy2-sy1)/2),
                           (sx2,sy1+(sy2-sy1)/2),(sx1+(sx2-sx1)/2,sy2)]
                for hx, hy in handles:
                    self.canvas.create_oval(hx-5,hy-5,hx+5,hy+5,fill="white",outline=color,width=2,tags="handle")

    def on_canvas_press(self, e):
        if self.current_mode != "label": return
        self.start_x, self.start_y = e.x, e.y
        if self.rect: self.canvas.delete(self.rect)
        self.rect = self.canvas.create_rectangle(e.x, e.y, e.x, e.y, outline="#f1c40f", width=3)

    def on_canvas_drag(self, e):
        if self.current_mode != "label" or not self.rect: return
        self.canvas.coords(self.rect, self.start_x, self.start_y, e.x, e.y)

    def on_canvas_release(self, e):
        if self.current_mode != "label" or not self.rect: return
        x1, y1 = self.start_x, self.start_y
        x2, y2 = e.x, e.y
        if x1 > x2: x1, x2 = x2, x1
        if y1 > y2: y1, y2 = y2, y1

        ox1 = int(x1 / self.scale); oy1 = int(y1 / self.scale)
        ox2 = int(x2 / self.scale); oy2 = int(y2 / self.scale)
        if ox2 - ox1 < 10 or oy2 - oy1 < 10:
            self.canvas.delete(self.rect); self.rect = None; self.set_mode(None); return

        crop = self.original_image[oy1:oy2, ox1:ox2]
        txt = simpledialog.askstring("Label", "Masukkan label\n(ketik 'cancel' untuk batal)", parent=self.root)
        if txt is None or txt.strip().lower() == "cancel":
            self.canvas.delete(self.rect); self.rect = None; self.set_mode(None); return

        label = txt.strip() or "unknown"
        self.boxes.append([ox1, oy1, ox2, oy2, label, crop])
        self.redraw_boxes(); self.canvas.delete(self.rect); self.rect = None
        self.btn_export.config(state=tk.NORMAL); self.status.config(text=f"Disimpan: {label}", fg="#27ae60")
        self.set_mode(None)

    def find_box_at(self, x, y):
        for i, (x1, y1, x2, y2, _, _) in enumerate(self.boxes):
            if x1*self.scale <= x <= x2*self.scale and y1*self.scale <= y <= y2*self.scale:
                return i
        return None

    def get_resize_handle(self, x, y, box_idx):
        if box_idx is None: return None
        x1, y1, x2, y2 = [v * self.scale for v in self.boxes[box_idx][:4]]
        tol = 12
        handles = {
            "nw": (x1, y1), "n": (x1 + (x2-x1)/2, y1), "ne": (x2, y1),
            "w": (x1, y1 + (y2-y1)/2), "e": (x2, y1 + (y2-y1)/2),
            "sw": (x1, y2), "s": (x1 + (x2-x1)/2, y2), "se": (x2, y2)
        }
        for h, (hx, hy) in handles.items():
            if abs(x - hx) <= tol and abs(y - hy) <= tol:
                return h
        return "move" if x1 <= x <= x2 and y1 <= y <= y2 else None
    
    def on_edit_drag(self, event):
        if self.current_mode != "edit" or self.selected_box is None or "handle" not in self.drag_data:
            return
        idx = self.selected_box
        box = self.boxes[idx]
        x1, y1, x2, y2 = box[:4]
        handle = self.drag_data["handle"]
        dx = (event.x - self.drag_data["start_x"]) / self.scale
        dy = (event.y - self.drag_data["start_y"]) / self.scale
        nx1, ny1, nx2, ny2 = x1, y1, x2, y2
        if handle == "move":
            nx1 = int(x1 + dx); ny1 = int(y1 + dy)
            nx2 = int(x2 + dx); ny2 = int(y2 + dy)
        else:
            if "n" in handle:
                ny1 = int(y1 + dy)
            if "s" in handle:
                ny2 = int(y2 + dy)
            if "w" in handle:
                nx1 = int(x1 + dx)
            if "e" in handle:
                nx2 = int(x2 + dx)
        nx1 = max(0, min(nx1, nx2 - 10))
        ny1 = max(0, min(ny1, ny2 - 10))
        nx2 = max(nx1 + 10, min(nx2, self.original_image.shape[1]))
        ny2 = max(ny1 + 10, min(ny2, self.original_image.shape[0]))
        crop = self.original_image[ny1:ny2, nx1:nx2]
        if crop.size == 0: return
        self.boxes[idx] = [nx1, ny1, nx2, ny2, box[4], crop]
        self.drag_data["start_x"] = event.x
        self.drag_data["start_y"] = event.y
        self.redraw_boxes()

    def on_edit_release(self, event):
        self.drag_data = {}

    def on_box_right_click(self, event):
        if self.current_mode != "edit": return
        idx = self.find_box_at(event.x, event.y)
        if idx is None: return
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Ubah Label", command=lambda: self.edit_label(idx))
        menu.add_separator()
        menu.add_command(label="Hapus Box", command=lambda: self.delete_box(idx))
        try:
            menu.post(event.x_root, event.y_root)
        except tk.TclError:
            pass

    def edit_label(self, idx):
        old = self.boxes[idx][4]
        new = simpledialog.askstring("Edit Label", "Label baru:", initialvalue=old)
        if new and new.strip():
            self.boxes[idx][4] = new.strip()
            self.redraw_boxes()

    def delete_box(self, idx):
        if messagebox.askyesno("Hapus", "Hapus bounding box ini?"):
            del self.boxes[idx]
            self.selected_box = None
            self.redraw_boxes()
            self.status.config(text="Box dihapus", fg="#e74c3c")
            if self.current_mode == "edit" and self.selected_box is None:
                self.btn_label.config(state=tk.NORMAL)
            if not self.boxes:
                self.btn_export.config(state=tk.DISABLED)
                self.set_mode(None)

    def on_edit_click(self, event):
        if self.current_mode != "edit": return
        idx = self.find_box_at(event.x, event.y)
        if idx is None:
            self.selected_box = None
            self.drag_data = {}
            self.redraw_boxes()
            self.status.config(text="Edit dibatalkan", fg="#7f8c8d")
            self.btn_label.config(state=tk.NORMAL)
            return
        handle = self.get_resize_handle(event.x, event.y, idx)
        if handle is None:
            handle = "move"
        self.selected_box = idx
        self.btn_label.config(state=tk.DISABLED)
        self.drag_data = {"start_x": event.x, "start_y": event.y, "handle": handle, "orig": self.boxes[idx][:4].copy()}
        self.redraw_boxes()
        self.status.config(text="Mulai drag/resize box", fg="#27ae60")

    def on_edit_double_click(self, event):
        if self.current_mode != "edit": return
        idx = self.find_box_at(event.x, event.y)
        if idx is None: return
        old = self.boxes[idx][4]
        new = simpledialog.askstring("Edit Label", f"Label lama: {old}\nLabel baru:", initialvalue=old)
        if new and new.strip():
            self.boxes[idx][4] = new.strip()
            self.redraw_boxes()
            self.status.config(text=f"Label diubah → {new.strip()}", fg="#27ae60")

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
        self.boxes = []; self.redraw_boxes(); self.btn_export.config(state=tk.DISABLED)
        self.status.config(text="Ekspor selesai!", fg="#27ae60"); self.set_mode(None)


if __name__ == "__main__":
    root = tk.Tk()
    app = ImageLabelingApp(root)
    root.mainloop()
