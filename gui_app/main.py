import customtkinter as ctk
import threading
import time
from api_client import APIClient
from datetime import datetime

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Rozetka-Click Manager")
        self.geometry("900x700")

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.categories_data = []
        self._stop_at: float | None = None

        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")

        self.tab_dashboard = self.tabview.add("Dashboard")
        self.tab_shops = self.tabview.add("Shops")
        self.tab_proxies = self.tabview.add("Proxies")
        self.tab_categories = self.tabview.add("Categories")

        self.setup_dashboard()
        self.setup_shops()
        self.setup_proxies()
        self.setup_categories()

        # Initial checks
        self.refresh_status_event()
        self.refresh_lists_event()
        self._start_auto_refresh()
        self._tick_countdown()

    def run_async_task(self, func, callback):
        def wrapper():
            success, result = func()
            self.after(0, lambda: callback(success, result))
        threading.Thread(target=wrapper, daemon=True).start()

    def log_message(self, message: str, is_error: bool = False):
        if hasattr(self, 'textbox'):
            self.textbox.configure(state="normal")
            timestamp = datetime.now().strftime("%H:%M:%S")
            prefix = "[ERROR]" if is_error else "[INFO]"
            text = f"{timestamp} {prefix} {message}\n"
            self.textbox.insert("end", text)
            self.textbox.see("end")
            self.textbox.configure(state="disabled")
        
        if is_error:
            self.tabview.set("Dashboard")

    # ================= DASHBOARD =================
    def setup_dashboard(self):
        self.tab_dashboard.grid_columnconfigure((0, 1), weight=1)
        self.tab_dashboard.grid_rowconfigure(1, weight=1)

        control_frame = ctk.CTkFrame(self.tab_dashboard)
        control_frame.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        self.status_label = ctk.CTkLabel(control_frame, text="Status: Unknown", text_color="yellow", font=ctk.CTkFont(size=18, weight="bold"))
        self.status_label.pack(side="left", padx=20)

        self.countdown_label = ctk.CTkLabel(control_frame, text="", text_color="orange", font=ctk.CTkFont(size=13))
        self.countdown_label.pack(side="left", padx=(0, 10))

        self.start_btn = ctk.CTkButton(control_frame, text="Start Parser", command=self.open_start_parser_popup, fg_color="green", hover_color="darkgreen")
        self.start_btn.pack(side="left", padx=10, pady=10)

        self.stop_btn = ctk.CTkButton(control_frame, text="Stop Parser", command=self.open_stop_parser_popup, fg_color="red", hover_color="darkred")
        self.stop_btn.pack(side="left", padx=10, pady=10)

        self.refresh_btn = ctk.CTkButton(control_frame, text="Refresh", command=self.refresh_status_event)
        self.refresh_btn.pack(side="right", padx=20, pady=10)

        log_frame = ctk.CTkFrame(self.tab_dashboard)
        log_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")
        log_frame.grid_rowconfigure(1, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(log_frame, text="System Logs", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, pady=(5,0))
        self.textbox = ctk.CTkTextbox(log_frame)
        self.textbox.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self.textbox.configure(state="disabled")

    def update_status_label(self, success: bool, data):
        if success:
            running = data.get("running", False)
            stop_at = data.get("stop_at")
            self._stop_at = stop_at if (stop_at and stop_at > time.time()) else None
            self._running = running
            if running:
                self.status_label.configure(text="Status: Running", text_color="green")
                self.start_btn.configure(state="disabled")
            else:
                self._stop_at = None
                self.status_label.configure(text="Status: Stopped", text_color="grey")
                self.start_btn.configure(state="normal")
        else:
            self._stop_at = None
            self._running = False
            self.status_label.configure(text="Status: Error/Offline", text_color="red")
            self.start_btn.configure(state="normal")
            self.log_message(data.get("error", "Connection error"), is_error=True)
        # Sync stop button state with server data
        self._update_stop_btn_state()

    def _update_stop_btn_state(self):
        if self._stop_at is not None and self._stop_at > time.time():
            self.stop_btn.configure(state="disabled")
        else:
            self.stop_btn.configure(state="normal")

    def _start_auto_refresh(self):
        self._auto_refresh_id = self.after(5000, self._auto_refresh_tick)

    def _auto_refresh_tick(self):
        self.refresh_status_event()
        self._auto_refresh_id = self.after(5000, self._auto_refresh_tick)

    def _tick_countdown(self):
        if self._stop_at is not None:
            remaining = self._stop_at - time.time()
            if remaining > 0:
                hours = int(remaining // 3600)
                minutes = int((remaining % 3600) // 60)
                seconds = int(remaining % 60)
                if hours > 0:
                    countdown_str = f"{hours}:{minutes:02d}:{seconds:02d}"
                else:
                    countdown_str = f"{minutes}:{seconds:02d}"
                self.countdown_label.configure(text=f"⏱ Stops in {countdown_str}")
            else:
                self._stop_at = None
                self.countdown_label.configure(text="")
                self.stop_btn.configure(state="normal")
        else:
            self.countdown_label.configure(text="")
        self.after(1000, self._tick_countdown)


    def refresh_status_event(self):
        self.run_async_task(APIClient.get_status, self.update_status_label)

    def open_start_parser_popup(self):
        popup = ctk.CTkToplevel(self)
        popup.title("Parser Settings")
        popup.geometry("300x250")
        popup.resizable(False, False)
        
        # Ensure we have up-to-date position data for the main window
        self.update_idletasks()
        
        x = self.winfo_x() + (self.winfo_width() // 2) - 150
        y = self.winfo_y() + (self.winfo_height() // 2) - 125
        popup.geometry(f"300x250+{max(0, x)}+{max(0, y)}")
        
        popup.grab_set()
        
        # Close on Escape
        popup.bind("<Escape>", lambda e: popup.destroy())

        frame = ctk.CTkFrame(popup, fg_color="transparent")
        frame.pack(pady=15, padx=20, fill="both", expand=True)

        # Iterations
        row_iter = ctk.CTkFrame(frame, fg_color="transparent")
        row_iter.pack(fill="x", pady=5)
        ctk.CTkLabel(row_iter, text="Iterations:", width=80, anchor="w", font=ctk.CTkFont(weight="bold")).pack(side="left")
        iterations_entry = ctk.CTkEntry(row_iter, width=100)
        iterations_entry.insert(0, "1")
        iterations_entry.pack(side="right", fill="x", expand=True)

        # Delay Dropdown Menu
        row_delay = ctk.CTkFrame(frame, fg_color="transparent")
        row_delay.pack(fill="x", pady=5)
        ctk.CTkLabel(row_delay, text="Delay:", width=80, anchor="w", font=ctk.CTkFont(weight="bold")).pack(side="left")
        
        delay_var = ctk.StringVar(value="None")
        delay_menu = ctk.CTkOptionMenu(row_delay, values=["None", "In Minutes", "In Hours", "Exact Time"], variable=delay_var)
        delay_menu.pack(side="right", fill="x", expand=True)

        # Value input
        self.row_val = ctk.CTkFrame(frame, fg_color="transparent")
        self.row_val.pack(fill="x", pady=5)
        self.val_label = ctk.CTkLabel(self.row_val, text="Value:", width=80, anchor="w")
        self.val_label.pack(side="left")
        self.delay_value_entry = ctk.CTkEntry(self.row_val, width=100, placeholder_text="")
        self.delay_value_entry.pack(side="right", fill="x", expand=True)

        def toggle_entry_visibility(*args):
            choice = delay_var.get()
            if choice == "None":
                self.row_val.pack_forget()
            else:
                self.row_val.pack(fill="x", pady=5)
                if choice == "In Hours":
                    self.delay_value_entry.configure(placeholder_text="e.g. 2.5")
                elif choice == "In Minutes":
                    self.delay_value_entry.configure(placeholder_text="e.g. 15")
                else:
                    self.delay_value_entry.configure(placeholder_text="HH:MM (e.g. 14:30)")

        delay_var.trace_add("write", toggle_entry_visibility)
        
        btn_frame = ctk.CTkFrame(popup, fg_color="transparent")
        btn_frame.pack(pady=10)

        toggle_entry_visibility()

        def on_confirm():
            try:
                iterations = int(iterations_entry.get().strip() or "1")
            except ValueError:
                self.log_message("Iterations must be a valid integer", is_error=True)
                return
            
            d_type = delay_var.get()
            d_val = self.delay_value_entry.get().strip()

            if d_type in ("In Minutes", "In Hours", "Exact Time") and not d_val:
                d_type = "None"
            else:
                if d_type in ("In Hours", "In Minutes"):
                    try:
                        float(d_val)
                    except ValueError:
                        self.log_message(f"Delay {d_type.lower()} must be a number", is_error=True)
                        return
                elif d_type == "Exact Time":
                    if ":" not in d_val:
                        self.log_message("Exact time must be in HH:MM format", is_error=True)
                        return

            popup.destroy()
            self.execute_start_parser(iterations, d_type, d_val)

        ctk.CTkButton(btn_frame, text="Start", command=on_confirm, fg_color="green", hover_color="darkgreen").pack()

    def execute_start_parser(self, iterations: int, delay_type: str = "None", delay_value: str = ""):
        def _cb(success, msg):
            self.log_message(msg, is_error=not success)
            self.refresh_status_event()
        
        # map frontend display string to backend type
        type_map = {"None": "none", "In Minutes": "minutes", "In Hours": "hours", "Exact Time": "exact_time"}
        d_type = type_map.get(delay_type, "none")
        self.run_async_task(lambda: APIClient.start_parser(iterations, d_type, delay_value), _cb)

    def open_stop_parser_popup(self):
        popup = ctk.CTkToplevel(self)
        popup.title("Stop Parser Settings")
        popup.geometry("300x220")
        popup.resizable(False, False)

        self.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - 150
        y = self.winfo_y() + (self.winfo_height() // 2) - 110
        popup.geometry(f"300x220+{max(0, x)}+{max(0, y)}")

        popup.grab_set()
        popup.bind("<Escape>", lambda e: popup.destroy())

        frame = ctk.CTkFrame(popup, fg_color="transparent")
        frame.pack(pady=15, padx=20, fill="both", expand=True)

        # Delay Dropdown Menu
        row_delay = ctk.CTkFrame(frame, fg_color="transparent")
        row_delay.pack(fill="x", pady=5)
        ctk.CTkLabel(row_delay, text="Delay:", width=80, anchor="w", font=ctk.CTkFont(weight="bold")).pack(side="left")

        delay_var = ctk.StringVar(value="None")
        delay_menu = ctk.CTkOptionMenu(row_delay, values=["None", "In Minutes", "In Hours", "Exact Time"], variable=delay_var)
        delay_menu.pack(side="right", fill="x", expand=True)

        # Value input
        self.stop_row_val = ctk.CTkFrame(frame, fg_color="transparent")
        self.stop_row_val.pack(fill="x", pady=5)
        ctk.CTkLabel(self.stop_row_val, text="Value:", width=80, anchor="w").pack(side="left")
        self.stop_delay_value_entry = ctk.CTkEntry(self.stop_row_val, width=100, placeholder_text="")
        self.stop_delay_value_entry.pack(side="right", fill="x", expand=True)

        def toggle_stop_entry(*args):
            choice = delay_var.get()
            if choice == "None":
                self.stop_row_val.pack_forget()
            else:
                self.stop_row_val.pack(fill="x", pady=5)
                if choice == "In Hours":
                    self.stop_delay_value_entry.configure(placeholder_text="e.g. 2.5")
                elif choice == "In Minutes":
                    self.stop_delay_value_entry.configure(placeholder_text="e.g. 15")
                else:
                    self.stop_delay_value_entry.configure(placeholder_text="HH:MM (e.g. 14:30)")

        delay_var.trace_add("write", toggle_stop_entry)

        btn_frame = ctk.CTkFrame(popup, fg_color="transparent")
        btn_frame.pack(pady=10)

        toggle_stop_entry()

        def on_confirm():
            d_type = delay_var.get()
            d_val = self.stop_delay_value_entry.get().strip()

            if d_type in ("In Minutes", "In Hours", "Exact Time") and not d_val:
                d_type = "None"
            else:
                if d_type in ("In Hours", "In Minutes"):
                    try:
                        float(d_val)
                    except ValueError:
                        self.log_message(f"Delay {d_type.lower()} must be a number", is_error=True)
                        return
                elif d_type == "Exact Time":
                    if ":" not in d_val:
                        self.log_message("Exact time must be in HH:MM format", is_error=True)
                        return

            popup.destroy()
            self.execute_stop_parser(d_type, d_val)

        ctk.CTkButton(btn_frame, text="Stop", command=on_confirm, fg_color="red", hover_color="darkred").pack()

    def execute_stop_parser(self, delay_type: str = "None", delay_value: str = ""):
        def _cb(success, msg):
            self.log_message(msg, is_error=not success)
            self.refresh_status_event()

        type_map = {"None": "none", "In Minutes": "minutes", "In Hours": "hours", "Exact Time": "exact_time"}
        d_type = type_map.get(delay_type, "none")
        self.run_async_task(lambda: APIClient.stop_parser(d_type, delay_value), _cb)

    def stop_parser_event(self):
        def _cb(success, msg):
            self.log_message(msg, is_error=not success)
            self.refresh_status_event()
        self.run_async_task(APIClient.stop_parser, _cb)

    def refresh_lists_event(self):
        self.load_shops()
        self.load_proxies()
        self.load_categories()

    # ================= SHOPS =================
    def setup_shops(self):
        self.tab_shops.grid_columnconfigure(0, weight=1)
        self.tab_shops.grid_rowconfigure(1, weight=1)

        # Add Shop form
        form = ctk.CTkFrame(self.tab_shops)
        form.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        form.grid_columnconfigure(0, weight=1)

        self.shop_url_entry = ctk.CTkEntry(form, placeholder_text="Shop URL")
        self.shop_url_entry.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        ctk.CTkButton(form, text="Add Shop", command=self.add_shop_event).grid(row=0, column=1, padx=5, pady=5)

        # List
        self.shops_scroll = ctk.CTkScrollableFrame(self.tab_shops, label_text="All Shops")
        self.shops_scroll.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

    def load_shops(self):
        def _cb(success, result):
            for widget in self.shops_scroll.winfo_children():
                widget.destroy()
            if success:
                if not result:
                    ctk.CTkLabel(self.shops_scroll, text="No shops found.").pack(pady=10)
                for s in result:
                    row = ctk.CTkFrame(self.shops_scroll)
                    row.pack(fill="x", padx=5, pady=2)
                    row.grid_columnconfigure(0, weight=1)
                    text = f"ID: {s['id']} | URL: {s['url']}"
                    ctk.CTkLabel(row, text=text, anchor="w", justify="left").grid(row=0, column=0, sticky="w", padx=5)
                    shop_id = s['id']
                    ctk.CTkButton(
                        row, text="Delete", width=70, fg_color="#c0392b", hover_color="#922b21",
                        command=lambda sid=shop_id: self.delete_shop_event(sid)
                    ).grid(row=0, column=1, padx=5, pady=2)
            else:
                ctk.CTkLabel(self.shops_scroll, text="Failed to load shops", text_color="red").pack(pady=10)
        self.run_async_task(APIClient.get_shops, _cb)

    def add_shop_event(self):
        url = self.shop_url_entry.get().strip()
        if not url:
            self.log_message("URL cannot be empty", is_error=True)
            return

        def _cb(success, msg):
            self.log_message(msg, is_error=not success)
            if success:
                self.shop_url_entry.delete(0, 'end')
                self.load_shops()
        self.run_async_task(lambda: APIClient.add_shop(url), _cb)

    def delete_shop_event(self, shop_id: int):
        def _cb(success, msg):
            self.log_message(msg, is_error=not success)
            if success:
                self.load_shops()
        self.run_async_task(lambda: APIClient.delete_shop(shop_id), _cb)

    # ================= PROXIES =================
    def setup_proxies(self):
        self.tab_proxies.grid_columnconfigure(0, weight=1)
        self.tab_proxies.grid_rowconfigure(1, weight=1)

        # Add form
        form = ctk.CTkFrame(self.tab_proxies)
        form.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        form.grid_columnconfigure((0,1,2), weight=1)

        self.proxy_server_entry = ctk.CTkEntry(form, placeholder_text="http://ip:port")
        self.proxy_server_entry.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        self.proxy_user_entry = ctk.CTkEntry(form, placeholder_text="Username")
        self.proxy_user_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        self.proxy_pass_entry = ctk.CTkEntry(form, placeholder_text="Password", show="*")
        self.proxy_pass_entry.grid(row=0, column=2, padx=5, pady=5, sticky="ew")

        ctk.CTkButton(form, text="Add Proxy", command=self.add_proxy_event).grid(row=1, column=0, columnspan=3, pady=5)

        # List
        self.proxies_scroll = ctk.CTkScrollableFrame(self.tab_proxies, label_text="All Proxies")
        self.proxies_scroll.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

    def load_proxies(self):
        def _cb(success, result):
            for widget in self.proxies_scroll.winfo_children():
                widget.destroy()
            if success:
                if not result:
                    ctk.CTkLabel(self.proxies_scroll, text="No proxies found.").pack(pady=10)
                for index, p in enumerate(result):
                    row = ctk.CTkFrame(self.proxies_scroll)
                    row.pack(fill="x", padx=5, pady=2)
                    row.grid_columnconfigure(0, weight=1)
                    
                    role = "(Scanning)" if index == 0 else "(Main)"
                    text = f"ID: {p['id']} {role} | Server: {p['server']} | User: {p['username']}"
                    
                    ctk.CTkLabel(row, text=text, anchor="w", justify="left").grid(row=0, column=0, sticky="w", padx=5)
                    proxy_id = p['id']
                    ctk.CTkButton(
                        row, text="Delete", width=70, fg_color="#c0392b", hover_color="#922b21",
                        command=lambda pid=proxy_id: self.delete_proxy_event(pid)
                    ).grid(row=0, column=1, padx=5, pady=2)
            else:
                ctk.CTkLabel(self.proxies_scroll, text="Failed to load proxies", text_color="red").pack(pady=10)
        self.run_async_task(APIClient.get_proxies, _cb)

    def add_proxy_event(self):
        server = self.proxy_server_entry.get().strip()
        user = self.proxy_user_entry.get().strip()
        pwd = self.proxy_pass_entry.get().strip()
        if not all([server, user, pwd]):
            self.log_message("Proxy fields cannot be empty", is_error=True)
            return

        def _cb(success, msg):
            self.log_message(msg, is_error=not success)
            if success:
                self.proxy_server_entry.delete(0, 'end')
                self.proxy_user_entry.delete(0, 'end')
                self.proxy_pass_entry.delete(0, 'end')
                self.load_proxies()
        self.run_async_task(lambda: APIClient.add_proxy(server, user, pwd), _cb)

    def delete_proxy_event(self, proxy_id: int):
        def _cb(success, msg):
            self.log_message(msg, is_error=not success)
            if success:
                self.load_proxies()
        self.run_async_task(lambda: APIClient.delete_proxy(proxy_id), _cb)

    # ================= CATEGORIES =================
    def setup_categories(self):
        self.tab_categories.grid_columnconfigure(0, weight=1)
        self.tab_categories.grid_rowconfigure(1, weight=1)

        # Add form
        form = ctk.CTkFrame(self.tab_categories)
        form.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        form.grid_columnconfigure((0,1), weight=1)

        self.cat_prod_entry = ctk.CTkEntry(form, placeholder_text="Target Product")
        self.cat_prod_entry.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        self.cat_name_entry = ctk.CTkEntry(form, placeholder_text="Target Category")
        self.cat_name_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ctk.CTkButton(form, text="Add Category", command=self.add_category_event).grid(row=1, column=0, columnspan=2, pady=5)

        # List
        self.categories_scroll = ctk.CTkScrollableFrame(self.tab_categories, label_text="All Categories")
        self.categories_scroll.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

    def load_categories(self):
        def _cb(success, result):
            for widget in self.categories_scroll.winfo_children():
                widget.destroy()
            if success:
                self.categories_data = result
                if not result:
                    ctk.CTkLabel(self.categories_scroll, text="No categories found.").pack(pady=10)
                for c in result:
                    row = ctk.CTkFrame(self.categories_scroll)
                    row.pack(fill="x", padx=5, pady=2)
                    row.grid_columnconfigure(0, weight=1)
                    text = f"ID: {c['id']} | Prod: {c['target_product']} | Cat: {c['target_category']}"
                    ctk.CTkLabel(row, text=text, anchor="w", justify="left").grid(row=0, column=0, sticky="w", padx=5)
                    cat_id = c['id']
                    ctk.CTkButton(
                        row, text="Delete", width=70, fg_color="#c0392b", hover_color="#922b21",
                        command=lambda cid=cat_id: self.delete_category_event(cid)
                    ).grid(row=0, column=1, padx=5, pady=2)
            else:
                ctk.CTkLabel(self.categories_scroll, text="Failed to load categories", text_color="red").pack(pady=10)
        self.run_async_task(APIClient.get_categories, _cb)



    def add_category_event(self):
        prod = self.cat_prod_entry.get().strip()
        cat = self.cat_name_entry.get().strip()
        if not all([prod, cat]):
            self.log_message("Category fields cannot be empty", is_error=True)
            return

        def _cb(success, msg):
            self.log_message(msg, is_error=not success)
            if success:
                self.cat_prod_entry.delete(0, 'end')
                self.cat_name_entry.delete(0, 'end')
                self.load_categories()
        self.run_async_task(lambda: APIClient.add_category(prod, cat), _cb)

    def delete_category_event(self, category_id: int):
        def _cb(success, msg):
            self.log_message(msg, is_error=not success)
            if success:
                self.load_categories()
        self.run_async_task(lambda: APIClient.delete_category(category_id), _cb)


if __name__ == "__main__":
    app = App()
    app.mainloop()
