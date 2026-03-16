import socket
import threading
import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
import tkinter.font as tkfont
import json
import base64
import os
import time

HOST = "127.0.0.1"
PORT = 12345

# ─── THEME ────────────────────────────────────────────────────────────────────
COLORS = {
    "bg_dark":      "#0f1117",
    "bg_mid":       "#1a1d27",
    "bg_panel":     "#1e2130",
    "bg_input":     "#252836",
    "accent":       "#7c6ef7",
    "accent_light": "#9d8fff",
    "accent_dim":   "#3d3680",
    "sent_bg":      "#2c2470",
    "recv_bg":      "#1e2130",
    "system_fg":    "#6b7280",
    "text_main":    "#e8eaf6",
    "text_sub":     "#9ca3af",
    "text_time":    "#6b7280",
    "green":        "#34d399",
    "red":          "#f87171",
    "yellow":       "#fbbf24",
    "border":       "#2d3149",
    "hover":        "#2a2d3e",
    "scrollbar":    "#2d3149",
    "online_dot":   "#34d399",
}

FONTS = {
    "title":    ("Helvetica Neue", 15, "bold"),
    "subtitle": ("Helvetica Neue", 9),
    "body":     ("Helvetica Neue", 11),
    "body_b":   ("Helvetica Neue", 11, "bold"),
    "small":    ("Helvetica Neue", 9),
    "time":     ("Helvetica Neue", 8),
    "emoji":    ("Segoe UI Emoji", 11),
    "input":    ("Helvetica Neue", 11),
    "user":     ("Helvetica Neue", 10, "bold"),
    "side_u":   ("Helvetica Neue", 11, "bold"),
    "side_s":   ("Helvetica Neue", 9),
}


# ─── BUBBLE WIDGET ────────────────────────────────────────────────────────────
class MessageBubble(tk.Frame):
    def __init__(self, parent, username, text, timestamp, is_self=False,
                 msg_type="message", filename=None, **kwargs):
        super().__init__(parent, bg=COLORS["bg_dark"], **kwargs)

        align = tk.E if is_self else tk.W
        bubble_bg = COLORS["sent_bg"] if is_self else COLORS["recv_bg"]
        anchor = "e" if is_self else "w"
        padx_val = (80, 10) if is_self else (10, 80)

        outer = tk.Frame(self, bg=COLORS["bg_dark"])
        outer.pack(fill=tk.X, padx=padx_val, pady=2)

        bubble = tk.Frame(outer, bg=bubble_bg, padx=12, pady=8)
        bubble.pack(anchor=anchor)

        # Add rounded effect with border
        bubble.config(
            highlightbackground=COLORS["accent_dim"] if is_self else COLORS["border"],
            highlightthickness=1,
            relief="flat"
        )

        if not is_self:
            name_lbl = tk.Label(
                bubble,
                text=username,
                font=FONTS["user"],
                bg=bubble_bg,
                fg=COLORS["accent_light"]
            )
            name_lbl.pack(anchor="w")

        if msg_type == "message":
            # Support multi-line
            msg_lbl = tk.Label(
                bubble,
                text=text,
                font=FONTS["body"],
                bg=bubble_bg,
                fg=COLORS["text_main"],
                wraplength=340,
                justify="left",
                anchor="w"
            )
            msg_lbl.pack(anchor="w")

        elif msg_type == "image":
            icon_frame = tk.Frame(bubble, bg=bubble_bg)
            icon_frame.pack(anchor="w")
            tk.Label(icon_frame, text="🖼️", font=("Segoe UI Emoji", 20),
                     bg=bubble_bg).pack(side=tk.LEFT)
            tk.Label(icon_frame,
                     text=filename or "Image",
                     font=FONTS["body"],
                     bg=bubble_bg, fg=COLORS["accent_light"],
                     cursor="hand2").pack(side=tk.LEFT, padx=5)

        elif msg_type == "file":
            ext = os.path.splitext(filename or "")[1].upper() if filename else ""
            icon_map = {".PDF": "📄", ".ZIP": "🗜️", ".MP3": "🎵",
                        ".MP4": "🎬", ".PY": "🐍", ".TXT": "📝",
                        ".DOCX": "📘", ".XLSX": "📗"}
            icon = icon_map.get(ext, "📁")
            ff = tk.Frame(bubble, bg=bubble_bg)
            ff.pack(anchor="w")
            tk.Label(ff, text=icon, font=("Segoe UI Emoji", 20),
                     bg=bubble_bg).pack(side=tk.LEFT)
            inner = tk.Frame(ff, bg=bubble_bg)
            inner.pack(side=tk.LEFT, padx=5)
            tk.Label(inner, text=filename or "File",
                     font=FONTS["body_b"], bg=bubble_bg,
                     fg=COLORS["text_main"]).pack(anchor="w")
            tk.Label(inner, text="File attachment",
                     font=FONTS["small"], bg=bubble_bg,
                     fg=COLORS["text_sub"]).pack(anchor="w")

        # Timestamp + checkmarks
        status = "✓✓" if is_self else ""
        time_frame = tk.Frame(bubble, bg=bubble_bg)
        time_frame.pack(anchor="e")
        tk.Label(time_frame,
                 text=f"{timestamp} {status}",
                 font=FONTS["time"],
                 bg=bubble_bg,
                 fg=COLORS["accent_light"] if is_self else COLORS["text_time"]
                 ).pack(side=tk.RIGHT)


# ─── MAIN APP ─────────────────────────────────────────────────────────────────
class ChatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Echo-Chat")
        self.root.geometry("900x650")
        self.root.minsize(700, 500)
        self.root.configure(bg=COLORS["bg_dark"])

        self.username = None
        self.client = None
        self.online_users = []
        self.typing_timer = None
        self.is_typing = False

        self._build_login()

    # ── LOGIN SCREEN ──────────────────────────────────────────────────────────
    def _build_login(self):
        self.login_frame = tk.Frame(self.root, bg=COLORS["bg_dark"])
        self.login_frame.place(relx=0, rely=0, relwidth=1, relheight=1)

        center = tk.Frame(self.login_frame, bg=COLORS["bg_mid"],
                          padx=50, pady=40,
                          highlightbackground=COLORS["border"],
                          highlightthickness=1)
        center.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(center, text="💬", font=("Segoe UI Emoji", 40),
                 bg=COLORS["bg_mid"]).pack(pady=(0, 5))
        tk.Label(center, text="Echo-Chat",
                 font=("Helvetica Neue", 22, "bold"),
                 bg=COLORS["bg_mid"], fg=COLORS["accent_light"]).pack()
        tk.Label(center, text="Connect. Communicate. Collaborate.",
                 font=FONTS["subtitle"],
                 bg=COLORS["bg_mid"], fg=COLORS["text_sub"]).pack(pady=(0, 25))

        tk.Label(center, text="Your name",
                 font=FONTS["small"], bg=COLORS["bg_mid"],
                 fg=COLORS["text_sub"]).pack(anchor="w")

        self.name_var = tk.StringVar()
        name_entry = tk.Entry(center, textvariable=self.name_var,
                              font=FONTS["input"],
                              bg=COLORS["bg_input"], fg=COLORS["text_main"],
                              insertbackground=COLORS["accent_light"],
                              relief="flat", width=26,
                              highlightbackground=COLORS["border"],
                              highlightthickness=1)
        name_entry.pack(ipady=8, pady=(3, 15))
        name_entry.bind("<Return>", lambda e: self._connect())
        name_entry.focus()

        join_btn = tk.Button(center, text="Join Chat →",
                             font=FONTS["body_b"],
                             bg=COLORS["accent"], fg="white",
                             activebackground=COLORS["accent_light"],
                             activeforeground="white",
                             relief="flat", cursor="hand2",
                             command=self._connect)
        join_btn.pack(fill=tk.X, ipady=8)

        self.login_status = tk.Label(center, text="",
                                     font=FONTS["small"],
                                     bg=COLORS["bg_mid"], fg=COLORS["red"])
        self.login_status.pack(pady=(8, 0))

    def _connect(self):
        name = self.name_var.get().strip()
        if not name:
            self.login_status.config(text="Please enter your name.")
            return
        self.login_status.config(text="Connecting...", fg=COLORS["yellow"])
        self.root.update()
        try:
            self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client.settimeout(5)
            self.client.connect((HOST, PORT))
            self._send_json({"type": "join", "username": name})
            # Wait for welcome
            data = self._recv_packet()
            self.client.settimeout(None)  # Remove timeout after connect
            if data:
                msg = json.loads(data.decode())
                if msg.get("type") == "welcome":
                    self.username = msg["username"]
                    self.login_frame.destroy()
                    self._build_chat()
                    threading.Thread(target=self._receive_loop, daemon=True).start()
                    return
            self.login_status.config(text="Server error. Try again.", fg=COLORS["red"])
        except Exception as e:
            self.login_status.config(text=f"Cannot connect: {e}", fg=COLORS["red"])

    # ── CHAT UI ───────────────────────────────────────────────────────────────
    def _build_chat(self):
        self.root.title(f"Echo-Chat — {self.username}")

        # Main layout: sidebar + chat
        main = tk.Frame(self.root, bg=COLORS["bg_dark"])
        main.pack(fill=tk.BOTH, expand=True)

        # ── SIDEBAR ───────────────────────────────────────────────────────────
        self.sidebar = tk.Frame(main, bg=COLORS["bg_panel"], width=200,
                                highlightbackground=COLORS["border"],
                                highlightthickness=1)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)

        # Sidebar header
        sb_header = tk.Frame(self.sidebar, bg=COLORS["accent_dim"], padx=12, pady=12)
        sb_header.pack(fill=tk.X)
        tk.Label(sb_header, text="💬 Echo-Chat",
                 font=FONTS["title"], bg=COLORS["accent_dim"],
                 fg=COLORS["text_main"]).pack(anchor="w")
        tk.Label(sb_header, text=f"@{self.username}",
                 font=FONTS["small"], bg=COLORS["accent_dim"],
                 fg=COLORS["accent_light"]).pack(anchor="w")

        # Online label
        tk.Label(self.sidebar, text="ONLINE",
                 font=("Helvetica Neue", 8, "bold"),
                 bg=COLORS["bg_panel"], fg=COLORS["text_sub"],
                 padx=12).pack(anchor="w", pady=(12, 4))

        self.user_list_frame = tk.Frame(self.sidebar, bg=COLORS["bg_panel"])
        self.user_list_frame.pack(fill=tk.BOTH, expand=True, padx=6)

        # ── CHAT AREA ─────────────────────────────────────────────────────────
        chat_col = tk.Frame(main, bg=COLORS["bg_dark"])
        chat_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Chat header
        self.chat_header = tk.Frame(chat_col, bg=COLORS["bg_panel"],
                                    padx=16, pady=10,
                                    highlightbackground=COLORS["border"],
                                    highlightthickness=1)
        self.chat_header.pack(fill=tk.X)

        header_left = tk.Frame(self.chat_header, bg=COLORS["bg_panel"])
        header_left.pack(side=tk.LEFT)
        tk.Label(header_left, text="🌐  Group Chat",
                 font=FONTS["body_b"], bg=COLORS["bg_panel"],
                 fg=COLORS["text_main"]).pack(anchor="w")
        self.online_count_lbl = tk.Label(header_left, text="1 online",
                                          font=FONTS["small"],
                                          bg=COLORS["bg_panel"],
                                          fg=COLORS["green"])
        self.online_count_lbl.pack(anchor="w")

        # Scrollable messages
        canvas_frame = tk.Frame(chat_col, bg=COLORS["bg_dark"])
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(canvas_frame, bg=COLORS["bg_dark"],
                                highlightthickness=0)
        scrollbar = tk.Scrollbar(canvas_frame, orient="vertical",
                                  command=self.canvas.yview,
                                  troughcolor=COLORS["bg_dark"],
                                  bg=COLORS["scrollbar"])
        self.canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.msg_container = tk.Frame(self.canvas, bg=COLORS["bg_dark"])
        self.canvas_window = self.canvas.create_window(
            (0, 0), window=self.msg_container, anchor="nw"
        )

        self.msg_container.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        # Mousewheel
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)

        # Typing indicator
        self.typing_lbl = tk.Label(chat_col, text="",
                                    font=FONTS["small"],
                                    bg=COLORS["bg_dark"],
                                    fg=COLORS["text_sub"],
                                    anchor="w", padx=16)
        self.typing_lbl.pack(fill=tk.X, pady=(2, 0))

        # ── INPUT BAR ─────────────────────────────────────────────────────────
        input_bar = tk.Frame(chat_col, bg=COLORS["bg_panel"],
                              padx=12, pady=10,
                              highlightbackground=COLORS["border"],
                              highlightthickness=1)
        input_bar.pack(fill=tk.X)

        # Emoji button
        emoji_btn = tk.Button(input_bar, text="😊",
                               font=("Segoe UI Emoji", 14),
                               bg=COLORS["bg_panel"], fg=COLORS["text_sub"],
                               activebackground=COLORS["bg_panel"],
                               relief="flat", cursor="hand2",
                               command=self._show_emoji_picker)
        emoji_btn.pack(side=tk.LEFT, padx=(0, 4))

        # Text input
        self.msg_var = tk.StringVar()
        self.msg_entry = tk.Entry(input_bar,
                                   textvariable=self.msg_var,
                                   font=FONTS["input"],
                                   bg=COLORS["bg_input"],
                                   fg=COLORS["text_main"],
                                   insertbackground=COLORS["accent_light"],
                                   relief="flat",
                                   highlightbackground=COLORS["border"],
                                   highlightthickness=1)
        self.msg_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=9)
        self.msg_entry.bind("<Return>", lambda e: self._send_message())
        self.msg_entry.bind("<KeyRelease>", self._on_keyrelease)

        # Placeholder
        self._set_placeholder()

        btn_cfg = dict(font=("Segoe UI Emoji", 14),
                       bg=COLORS["bg_panel"],
                       activebackground=COLORS["hover"],
                       relief="flat", cursor="hand2", padx=6)

        tk.Button(input_bar, text="📷", fg=COLORS["green"],
                  command=self._send_image, **btn_cfg).pack(side=tk.LEFT)
        tk.Button(input_bar, text="📁", fg=COLORS["yellow"],
                  command=self._send_file, **btn_cfg).pack(side=tk.LEFT)

        send_btn = tk.Button(input_bar, text="  ➤  ",
                              font=FONTS["body_b"],
                              bg=COLORS["accent"], fg="white",
                              activebackground=COLORS["accent_light"],
                              activeforeground="white",
                              relief="flat", cursor="hand2",
                              command=self._send_message)
        send_btn.pack(side=tk.LEFT, padx=(6, 0), ipady=5)

        # Welcome system message
        self._add_system_msg(f"Welcome, {self.username}! You've joined Echo-Chat 🎉")

    # ── PLACEHOLDER ───────────────────────────────────────────────────────────
    def _set_placeholder(self):
        self.msg_entry.insert(0, "Type a message…")
        self.msg_entry.config(fg=COLORS["text_sub"])
        self.msg_entry.bind("<FocusIn>", self._clear_placeholder)
        self.msg_entry.bind("<FocusOut>", self._restore_placeholder)

    def _clear_placeholder(self, e):
        if self.msg_entry.get() == "Type a message…":
            self.msg_entry.delete(0, tk.END)
            self.msg_entry.config(fg=COLORS["text_main"])

    def _restore_placeholder(self, e):
        if not self.msg_entry.get():
            self.msg_entry.insert(0, "Type a message…")
            self.msg_entry.config(fg=COLORS["text_sub"])

    # ── EMOJI PICKER ──────────────────────────────────────────────────────────
    def _show_emoji_picker(self):
        picker = tk.Toplevel(self.root)
        picker.title("")
        picker.geometry("300x200")
        picker.configure(bg=COLORS["bg_mid"])
        picker.resizable(False, False)
        picker.grab_set()

        emojis = ["😊","😂","❤️","👍","🔥","✨","😎","🎉",
                   "🥳","😍","🙏","💯","😅","🤔","😢","😡",
                   "🤣","🫡","💪","🎮","🍕","🎵","🌙","⭐"]

        tk.Label(picker, text="Pick an emoji",
                 font=FONTS["small"], bg=COLORS["bg_mid"],
                 fg=COLORS["text_sub"]).pack(pady=(8, 4))

        grid_frame = tk.Frame(picker, bg=COLORS["bg_mid"])
        grid_frame.pack(padx=10, pady=4)

        for i, em in enumerate(emojis):
            btn = tk.Button(grid_frame, text=em,
                            font=("Segoe UI Emoji", 16),
                            bg=COLORS["bg_mid"],
                            activebackground=COLORS["hover"],
                            relief="flat", cursor="hand2",
                            command=lambda e=em, p=picker: self._insert_emoji(e, p))
            btn.grid(row=i//8, column=i%8, padx=2, pady=2)

    def _insert_emoji(self, emoji, picker):
        picker.destroy()
        current = self.msg_entry.get()
        if current == "Type a message…":
            current = ""
        self.msg_entry.delete(0, tk.END)
        self.msg_entry.insert(0, current + emoji)
        self.msg_entry.config(fg=COLORS["text_main"])

    # ── SCROLLING ─────────────────────────────────────────────────────────────
    def _on_frame_configure(self, e):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, e):
        self.canvas.itemconfig(self.canvas_window, width=e.width)

    def _on_mousewheel(self, e):
        if e.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif e.num == 5:
            self.canvas.yview_scroll(1, "units")
        else:
            self.canvas.yview_scroll(int(-1*(e.delta/120)), "units")

    def _scroll_bottom(self):
        self.root.after(50, lambda: self.canvas.yview_moveto(1.0))

    # ── MESSAGES ──────────────────────────────────────────────────────────────
    def _add_bubble(self, username, text, timestamp, is_self=False,
                    msg_type="message", filename=None):
        bubble = MessageBubble(
            self.msg_container,
            username=username, text=text,
            timestamp=timestamp, is_self=is_self,
            msg_type=msg_type, filename=filename
        )
        bubble.pack(fill=tk.X, pady=2)
        self._scroll_bottom()

    def _add_system_msg(self, text):
        frame = tk.Frame(self.msg_container, bg=COLORS["bg_dark"])
        frame.pack(fill=tk.X, pady=6)
        tk.Label(frame, text=text,
                 font=FONTS["small"],
                 bg=COLORS["bg_dark"], fg=COLORS["system_fg"],
                 justify="center").pack()
        self._scroll_bottom()

    # ── TYPING ────────────────────────────────────────────────────────────────
    def _on_keyrelease(self, e):
        txt = self.msg_entry.get()
        if txt and txt != "Type a message…":
            if not self.is_typing:
                self.is_typing = True
                self._send_json({"type": "typing", "is_typing": True})
        else:
            if self.is_typing:
                self.is_typing = False
                self._send_json({"type": "typing", "is_typing": False})
        # Auto-stop typing after 3s
        if self.typing_timer:
            self.root.after_cancel(self.typing_timer)
        self.typing_timer = self.root.after(3000, self._stop_typing)

    def _stop_typing(self):
        if self.is_typing:
            self.is_typing = False
            self._send_json({"type": "typing", "is_typing": False})

    # ── SEND ──────────────────────────────────────────────────────────────────
    def _send_message(self):
        text = self.msg_entry.get().strip()
        if not text or text == "Type a message…":
            return
        ts = time.strftime("%H:%M")
        self._send_json({
            "type": "message",
            "text": text,
            "timestamp": ts
        })
        self._add_bubble(self.username, text, ts, is_self=True)
        self.msg_entry.delete(0, tk.END)
        self._stop_typing()

    def _send_image(self):
        path = filedialog.askopenfilename(
            title="Select Image",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.gif *.bmp *.webp")]
        )
        if not path:
            return
        filename = os.path.basename(path)
        try:
            with open(path, "rb") as f:
                data = base64.b64encode(f.read()).decode()
            ts = time.strftime("%H:%M")
            self._send_json({
                "type": "image",
                "filename": filename,
                "data": data,
                "timestamp": ts
            })
            self._add_bubble(self.username, "", ts, is_self=True,
                             msg_type="image", filename=filename)
        except Exception as e:
            messagebox.showerror("Error", f"Could not send image:\n{e}")

    def _send_file(self):
        path = filedialog.askopenfilename(title="Select File")
        if not path:
            return
        size = os.path.getsize(path)
        if size > 10 * 1024 * 1024:
            messagebox.showwarning("Too Large", "Max file size is 10 MB.")
            return
        filename = os.path.basename(path)
        try:
            with open(path, "rb") as f:
                data = base64.b64encode(f.read()).decode()
            ts = time.strftime("%H:%M")
            self._send_json({
                "type": "file",
                "filename": filename,
                "data": data,
                "timestamp": ts
            })
            self._add_bubble(self.username, "", ts, is_self=True,
                             msg_type="file", filename=filename)
        except Exception as e:
            messagebox.showerror("Error", f"Could not send file:\n{e}")

    # ── RECEIVE ───────────────────────────────────────────────────────────────
    def _receive_loop(self):
        while True:
            try:
                data = self._recv_packet()
                if not data:
                    break
                msg = json.loads(data.decode("utf-8"))
                self.root.after(0, self._handle_incoming, msg)
            except Exception as e:
                break
        self.root.after(0, lambda: messagebox.showerror(
            "Disconnected", "Lost connection to server."))

    def _handle_incoming(self, msg):
        t = msg.get("type")

        if t == "message":
            self._add_bubble(msg["username"], msg["text"],
                             msg.get("timestamp", ""), is_self=False)

        elif t == "system":
            self._add_system_msg(msg["text"])

        elif t == "image":
            self._add_bubble(msg["username"], "", msg.get("timestamp", ""),
                             is_self=False, msg_type="image",
                             filename=msg.get("filename"))
            # Auto-save received image
            if "data" in msg:
                self._save_received_file(msg["filename"], msg["data"])

        elif t == "file":
            self._add_bubble(msg["username"], "", msg.get("timestamp", ""),
                             is_self=False, msg_type="file",
                             filename=msg.get("filename"))
            if "data" in msg:
                self._save_received_file(msg["filename"], msg["data"])

        elif t == "typing":
            uname = msg.get("username", "")
            if msg.get("is_typing"):
                self.typing_lbl.config(text=f"✍️  {uname} is typing…")
            else:
                self.typing_lbl.config(text="")

        elif t == "user_list":
            self.online_users = msg.get("users", [])
            self._update_user_list()

    def _save_received_file(self, filename, b64data):
        """Auto-save received files to Downloads folder"""
        try:
            downloads = os.path.join(os.path.expanduser("~"), "Downloads", "NovaChat")
            os.makedirs(downloads, exist_ok=True)
            filepath = os.path.join(downloads, filename)
            # Avoid overwrite
            base, ext = os.path.splitext(filename)
            count = 1
            while os.path.exists(filepath):
                filepath = os.path.join(downloads, f"{base}_{count}{ext}")
                count += 1
            with open(filepath, "wb") as f:
                f.write(base64.b64decode(b64data))
        except:
            pass

    # ── USER LIST ─────────────────────────────────────────────────────────────
    def _update_user_list(self):
        for w in self.user_list_frame.winfo_children():
            w.destroy()

        self.online_count_lbl.config(
            text=f"{len(self.online_users)} online"
        )

        for uname in self.online_users:
            row = tk.Frame(self.user_list_frame, bg=COLORS["bg_panel"],
                           padx=8, pady=5)
            row.pack(fill=tk.X, pady=1)

            # Online dot
            dot = tk.Canvas(row, width=8, height=8,
                            bg=COLORS["bg_panel"], highlightthickness=0)
            dot.create_oval(0, 0, 8, 8, fill=COLORS["online_dot"], outline="")
            dot.pack(side=tk.LEFT, padx=(0, 6))

            me_tag = " (you)" if uname == self.username else ""
            tk.Label(row, text=uname + me_tag,
                     font=FONTS["side_u"] if uname == self.username else FONTS["side_u"],
                     bg=COLORS["bg_panel"],
                     fg=COLORS["accent_light"] if uname == self.username else COLORS["text_main"]
                     ).pack(side=tk.LEFT, anchor="w")

    # ── NETWORKING ────────────────────────────────────────────────────────────
    def _send_json(self, obj):
        try:
            data = json.dumps(obj).encode("utf-8")
            length = len(data)
            self.client.sendall(length.to_bytes(4, "big") + data)
        except:
            pass

    def _recv_packet(self):
        raw_len = self._recv_exact(4)
        if not raw_len:
            return None
        length = int.from_bytes(raw_len, "big")
        return self._recv_exact(length)

    def _recv_exact(self, n):
        data = b""
        while len(data) < n:
            chunk = self.client.recv(n - len(data))
            if not chunk:
                return None
            data += chunk
        return data


# ─── ENTRY POINT ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    app = ChatApp(root)
    root.mainloop()
