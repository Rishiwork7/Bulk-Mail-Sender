import os
import sys
os.environ['TK_SILENCE_DEPRECATION'] = '1'

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import threading
import time
import re
import random
import string
import json
import datetime
import webbrowser
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from dispatch_engine import start_bulk_dispatch
from attachment_service import generate_attachment_buffer

def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def get_config_path():
    """ Get path to config.json, preferring the one next to the executable if bundled """
    if hasattr(sys, 'frozen'):
        # Running as a bundled executable
        base_dir = os.path.dirname(sys.executable)
    else:
        # Running from source
        base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, "config.json")

class RoxInvoiceAppBM2:
    def __init__(self, root):
        self.root = root
        self.root.title("BM2 Ultra - Welcome To rox5 Menu")
        self.root.geometry("1024x768")
        self.root.configure(bg="#2D2D2D") # Dark grey background
        
        # Multi-Task State
        self.tasks = []
        self.current_task_idx = 0
        self.task_buttons = []
        self.task_strips = []
        
        self.client_secrets_path = None # Store for later auth

        # Initialize Variables
        self._init_variables()
        
        # Initialize the first task state
        self.tasks.append(self.dump_default_state())
        
        self.show_login()

    def _init_variables(self):
        # State Variables (current active)
        self.target_data = None
        self.sender_data = []
        self.failed_emails = []
        
        # Checkbox Variables
        self.var_rotate = tk.BooleanVar(value=False)
        self.var_grayscale = tk.BooleanVar(value=False)
        self.var_crop = tk.BooleanVar(value=False)
        self.var_hq = tk.BooleanVar(value=False)
        self.var_hsize = tk.BooleanVar(value=False)
        self.var_limit_check = tk.BooleanVar(value=False)
        self.var_auto_body_style = tk.BooleanVar(value=False)
        self.var_auto_body = tk.BooleanVar(value=False)
        self.var_delay_each = tk.BooleanVar(value=False)
        self.var_delay_every50 = tk.BooleanVar(value=False)
        self.var_random_width = tk.BooleanVar(value=False)
        self.var_test_mail = tk.BooleanVar(value=True)
        self.var_tfn1_b64 = tk.BooleanVar(value=False)
        self.var_tfn2_b64 = tk.BooleanVar(value=False)
        self.var_soft_fmt = tk.BooleanVar(value=False)
        self.var_unsub = tk.BooleanVar(value=False)
        self.var_header = tk.BooleanVar(value=False)
        self.var_color = tk.BooleanVar(value=False)
        self.var_with_name = tk.BooleanVar(value=False)
        self.var_html_body = tk.BooleanVar(value=True)
        self.var_geo = tk.StringVar(value="USA")
        self.var_auth_method = tk.StringVar(value="Manual")
        self.var_out_type = tk.StringVar(value="Raw pdf")
        self.var_info = tk.StringVar(value="Hover over an option to view its description")
        self.custom_pdf_path = None

    def show_login(self):
        self.login_frame = tk.Frame(self.root, bg="#111111")
        self.login_frame.place(relx=0, rely=0, relwidth=1, relheight=1)
        
        inner_f = tk.Frame(self.login_frame, bg="#2D2D2D", bd=2, relief="groove")
        inner_f.place(relx=0.5, rely=0.5, anchor="center", width=300, height=250)
        
        tk.Label(inner_f, text="BM2 ULTRA LOGIN", fg="#00BCD4", bg="#2D2D2D", font=("Arial", 14, "bold")).pack(pady=20)
        
        tk.Label(inner_f, text="User ID:", fg="white", bg="#2D2D2D").pack()
        self.ent_login_user = ttk.Entry(inner_f, width=25)
        self.ent_login_user.pack(pady=5)
        
        tk.Label(inner_f, text="Password:", fg="white", bg="#2D2D2D").pack()
        self.ent_login_pass = ttk.Entry(inner_f, width=25, show="*")
        self.ent_login_pass.pack(pady=5)
        
        tk.Button(inner_f, text="LOGIN", bg="#4CAF50", fg="white", font=("Arial", 10, "bold"), width=15, command=self.check_login).pack(pady=10)
        tk.Button(inner_f, text="Change Credentials", bg="#555555", fg="#aaaaaa", font=("Arial", 8), width=18, command=self.change_credentials).pack(pady=2)

    def check_login(self):
        u = self.ent_login_user.get()
        p = self.ent_login_pass.get()
        # Load credentials from config.json
        config_path = get_config_path()
        try:
            with open(config_path, "r") as f:
                cfg = json.load(f)
            valid_u = cfg.get("user_id", "admin")
            valid_p = cfg.get("password", "admin")
        except:
            valid_u, valid_p = "admin", "admin"
        if u == valid_u and p == valid_p:
            self.login_frame.destroy()
            self.setup_ui()
            self.log_message(f"Login Successful. Welcome {u}.")
        else:
            messagebox.showerror("Login Failed", "Invalid User ID or Password")

    def change_credentials(self):
        win = tk.Toplevel(self.root)
        win.title("Change Credentials")
        win.geometry("320x350")
        win.configure(bg="#2D2D2D")
        win.grab_set()
        
        tk.Label(win, text="Change Login Credentials", fg="#00BCD4", bg="#2D2D2D", font=("Arial", 11, "bold")).pack(pady=10)
        
        tk.Label(win, text="Current User ID:", fg="white", bg="#2D2D2D").pack()
        ent_old_u = ttk.Entry(win, width=25)
        ent_old_u.pack(pady=2)
        tk.Label(win, text="Current Password:", fg="white", bg="#2D2D2D").pack()
        ent_old_p = ttk.Entry(win, width=25, show="*")
        ent_old_p.pack(pady=2)

        ttk.Separator(win, orient="horizontal").pack(fill="x", pady=8)

        tk.Label(win, text="New User ID:", fg="white", bg="#2D2D2D").pack()
        ent_u = ttk.Entry(win, width=25)
        ent_u.pack(pady=2)
        tk.Label(win, text="New Password:", fg="white", bg="#2D2D2D").pack()
        ent_p = ttk.Entry(win, width=25, show="*")
        ent_p.pack(pady=2)
        tk.Label(win, text="Confirm Password:", fg="white", bg="#2D2D2D").pack()
        ent_p2 = ttk.Entry(win, width=25, show="*")
        ent_p2.pack(pady=2)

        def save_creds():
            old_u = ent_old_u.get().strip()
            old_p = ent_old_p.get()
            new_u = ent_u.get().strip()
            new_p = ent_p.get()
            new_p2 = ent_p2.get()
            
            config_path = get_config_path()
            try:
                with open(config_path, "r") as f:
                    cfg = json.load(f)
                valid_u = cfg.get("user_id", "admin")
                valid_p = cfg.get("password", "admin")
            except:
                valid_u, valid_p = "admin", "admin"
                
            if old_u != valid_u or old_p != valid_p:
                messagebox.showerror("Verification Failed", "Current User ID or Password is incorrect.", parent=win)
                return

            if not new_u or not new_p:
                messagebox.showwarning("Invalid", "New User ID and Password cannot be empty.", parent=win)
                return
            if new_p != new_p2:
                messagebox.showwarning("Mismatch", "New passwords do not match.", parent=win)
                return

            with open(config_path, "w") as f:
                json.dump({"user_id": new_u, "password": new_p}, f, indent=2)
            messagebox.showinfo("Saved", f"Credentials updated! New User ID: {new_u}", parent=win)
            win.destroy()
            
        tk.Button(win, text="Save", bg="#4CAF50", fg="white", font=("Arial", 10, "bold"), command=save_creds).pack(pady=8)


    def setup_ui(self):
        # Top Bar
        top_frame = tk.Frame(self.root, bg="#111111", height=50)
        top_frame.pack(fill="x", side="top", padx=5, pady=5)
        
        # Task Bar Container
        self.task_bar = tk.Frame(top_frame, bg="#111111")
        self.task_bar.pack(side="left", fill="y")
        
        self.task_buttons = {} # idx -> btn
        self.task_strips = {}  # idx -> strip
        
        # Add Task Button
        self.btn_add = tk.Button(self.task_bar, text="+ Add Task", bg="white", font=("Arial", 10, "bold"), width=10, command=self.add_task)
        self.btn_add.pack(side="left", padx=2, pady=5)
        strip = tk.Frame(self.task_bar, bg="#E0E0E0", height=4, width=80)
        strip.place(in_=self.btn_add, relx=0, rely=1.0, anchor="sw", relwidth=1.0)

        # Initial Task 1
        self.create_task_button(0)
            
        # Date Setting & All Tag
        right_top = tk.Frame(top_frame, bg="#111111")
        right_top.pack(side="right", padx=10)
        
        date_frame = tk.Frame(right_top, bg="#2D2D2D")
        date_frame.pack(side="left", padx=5)
        tk.Label(date_frame, text="Date Setting", fg="white", bg="#2D2D2D", font=("Arial", 9)).pack()
        self.ent_date = ttk.Entry(date_frame, width=12)
        self.ent_date.insert(0, time.strftime("%d/%m/%Y"))
        self.ent_date.pack()
        
        tk.Button(right_top, text="ALL TAG", bg="#4CAF50", fg="white", font=("Arial", 10, "bold")).pack(side="left")

        # Main Body - Left Column
        left_frame = tk.Frame(self.root, bg="#2D2D2D", width=250)
        left_frame.pack(side="left", fill="y", padx=5, pady=5)
        
        paste_top = tk.Frame(left_frame, bg="#444444")
        paste_top.pack(fill="x")
        tk.Button(paste_top, text="Paste", fg="white", bg="#666666", width=8, command=self.paste_targets).pack(side="left", padx=5, pady=2)
        lbl_clear = tk.Label(paste_top, text="🗑️", fg="#2196F3", bg="#444444", font=("Arial", 14), cursor="hand2")
        lbl_clear.pack(side="right", padx=5)
        lbl_clear.bind("<Button-1>", lambda e: self.clear_targets())
        
        self.txt_targets = tk.Text(left_frame, width=25, bg="#111111", fg="white", font=("Consolas", 10))
        self.txt_targets.pack(fill="both", expand=True, pady=2)
        
        btn_frame = tk.Frame(left_frame, bg="#2D2D2D")
        btn_frame.pack(fill="x", pady=2)
        tk.Button(btn_frame, text="Import Data", bg="#2196F3", fg="white", command=self.import_data).pack(side="left", fill="x", expand=True, padx=1)
        tk.Button(btn_frame, text="Import JSON", bg="#4CAF50", fg="white", command=self.import_json).pack(side="left", fill="x", expand=True, padx=1)
        
        limit_frame = tk.Frame(left_frame, bg="#2D2D2D")
        limit_frame.pack(fill="x", pady=2)
        tk.Label(limit_frame, text="Specif:", fg="white", bg="#2D2D2D").pack(side="left")
        ttk.Entry(limit_frame, width=5).pack(side="left", padx=2)
        ttk.Spinbox(limit_frame, from_=0, to=999, width=5).pack(side="left", padx=2)
        tk.Button(limit_frame, text="Get").pack(side="left", padx=2)

        # Main Body - Center/Right Column
        main_frame = tk.Frame(self.root, bg="#E0E0E0", bd=2, relief="sunken")
        main_frame.pack(fill="both", expand=True, padx=(5, 10), pady=5)
        
        # Options Top Bar
        opt_frame = tk.Frame(main_frame, bg="#111111")
        opt_frame.pack(fill="x")
        
        geo_f = tk.Frame(opt_frame, bg="#111111")
        geo_f.pack(side="left", padx=15, pady=5)
        self.var_geo = tk.StringVar(value="USA")
        for g in ["USA", "AUS", "UK"]:
            tk.Radiobutton(geo_f, text=g, variable=self.var_geo, value=g, fg="white", bg="#111111", selectcolor="#444", activebackground="#111").pack(side="left", padx=5)
            
        check_f = tk.Frame(opt_frame, bg="#111111")
        check_f.pack(side="left", padx=20, pady=5)
        self.var_unsub = tk.BooleanVar(value=False)
        self.var_header = tk.BooleanVar(value=False)
        self.var_color = tk.BooleanVar(value=False)
        self.var_with_name = tk.BooleanVar(value=False)
        
        cb_u = tk.Checkbutton(check_f, text="Unsubscribe Link", variable=self.var_unsub, fg="#4FC3F7", bg="#111111", selectcolor="#444")
        cb_u.grid(row=0, column=0, sticky="w")
        cb_h = tk.Checkbutton(check_f, text="Advance Header", variable=self.var_header, fg="#B0BEC5", bg="#111111", selectcolor="#444")
        cb_h.grid(row=0, column=1, sticky="w", padx=10)
        cb_c = tk.Checkbutton(check_f, text="HTML Random Color", variable=self.var_color, fg="#B0BEC5", bg="#111111", selectcolor="#444")
        cb_c.grid(row=1, column=0, sticky="w")
        cb_w = tk.Checkbutton(check_f, text="With Name", variable=self.var_with_name, fg="white", bg="#111111", selectcolor="#444")
        cb_w.grid(row=1, column=1, sticky="w", padx=10)

        qual_f = tk.Frame(opt_frame, bg="#111111")
        qual_f.pack(side="right", padx=15, pady=5)
        tk.Checkbutton(qual_f, text="GrayScale", variable=self.var_grayscale, fg="white", bg="#111111", selectcolor="#444").grid(row=0, column=0, sticky="w")
        tk.Checkbutton(qual_f, text="Crop Image", variable=self.var_crop, fg="white", bg="#111111", selectcolor="#444").grid(row=0, column=1, sticky="w", padx=5)
        tk.Checkbutton(qual_f, text="High Quality", variable=self.var_hq, fg="white", bg="#111111", selectcolor="#444").grid(row=1, column=0, sticky="w")
        tk.Checkbutton(qual_f, text="High Size", variable=self.var_hsize, fg="#81C784", bg="#111111", selectcolor="#444").grid(row=1, column=1, sticky="w", padx=5)
        
        err_lbl = tk.Label(qual_f, text="⚠️ Error List", fg="#FF5252", bg="#111111", cursor="hand2", font=("Arial", 10, "bold"))
        err_lbl.grid(row=0, column=2, padx=10, sticky="e")
        err_lbl.bind("<Button-1>", lambda e: self.show_error_list())
        
        tk.Checkbutton(qual_f, text="ReachedLimit Check", variable=self.var_limit_check, fg="#FF5252", bg="#111111", selectcolor="#444").grid(row=2, column=0, columnspan=3, sticky="w")

        # Dynamic Tooltip / Info Label beneath the options frame
        self.var_info = tk.StringVar(value="Hover over an option to view its description")
        info_l = tk.Label(main_frame, textvariable=self.var_info, fg="#FFC107", bg="#2D2D2D", font=("Arial", 11), justify="left", wraplength=900)
        info_l.pack(fill="x", padx=10, pady=(0, 5))

        # Bind hover events for the English descriptions
        cb_u.bind("<Enter>", lambda e: self.var_info.set("Unsubscribe Link injects an unsubscribe footer into the email body."))
        cb_u.bind("<Leave>", lambda e: self.var_info.set("Hover over an option to view its description"))
        
        cb_h.bind("<Enter>", lambda e: self.var_info.set("Advance Header inserts high-priority email headers into the SMTP packet."))
        cb_h.bind("<Leave>", lambda e: self.var_info.set("Hover over an option to view its description"))

        cb_c.bind("<Enter>", lambda e: self.var_info.set("HTML Random Color wraps the HTML body in a randomly generated hex-color border layout."))
        cb_c.bind("<Leave>", lambda e: self.var_info.set("Hover over an option to view its description"))

        cb_w.bind("<Enter>", lambda e: self.var_info.set("With Name appends the recipient's name to the To: header and Subject line."))
        cb_w.bind("<Leave>", lambda e: self.var_info.set("Hover over an option to view its description"))

        # Sender Details Section
        send_f = tk.Frame(main_frame, bg="#E0E0E0", pady=5)
        send_f.pack(fill="x", padx=10)
        send_f.columnconfigure(2, weight=1) # Allow Subject/Name entries to expand
        send_f.columnconfigure(6, weight=1) # Allow TFN box column to breathe or stick
        
        tk.Button(send_f, text="Clear cache", font=("Arial", 8), command=self.clear_cache).grid(row=0, column=0, sticky="w", padx=5)
        tk.Checkbutton(send_f, text="Change After Sent", variable=self.var_rotate, bg="#E0E0E0").grid(row=0, column=1, sticky="w")
        self.spn_rotate = ttk.Spinbox(send_f, from_=1, to=999, width=5)
        self.spn_rotate.set(50)
        self.spn_rotate.grid(row=0, column=2, sticky="w")
        
        tk.Label(send_f, text="Name *", bg="#E0E0E0", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky="e", pady=5)
        self.ent_name = ttk.Entry(send_f)
        self.ent_name.grid(row=1, column=1, columnspan=2, sticky="ew", padx=5)
        tk.Button(send_f, text="Pick", font=("Arial", 10), command=self.pick_name).grid(row=1, column=3, sticky="w", padx=2)
        tk.Button(send_f, text="Import", font=("Arial", 10), command=self.import_names).grid(row=1, column=4, sticky="w", padx=2)
        
        tk.Label(send_f, text="Sender Mail", bg="#E0E0E0", font=("Arial", 10, "bold")).grid(row=2, column=0, sticky="e", pady=5)
        self.ent_sender = ttk.Entry(send_f)
        self.ent_sender.grid(row=2, column=1, columnspan=4, sticky="ew", padx=5)
        
        tk.Label(send_f, text="App Pass", bg="#E0E0E0", font=("Arial", 10, "bold")).grid(row=3, column=0, sticky="e", pady=5)
        self.ent_app_pass = ttk.Entry(send_f, show="*")
        self.ent_app_pass.grid(row=3, column=1, columnspan=2, sticky="ew", padx=5)
        
        # Explicit Auth Method Choice
        auth_f = tk.Frame(send_f, bg="#E0E0E0")
        auth_f.grid(row=3, column=3, columnspan=2, sticky="w")
        self.var_auth_method = tk.StringVar(value="Manual")
        tk.Radiobutton(auth_f, text="Use Manual", variable=self.var_auth_method, value="Manual", bg="#E0E0E0", font=("Arial", 9, "bold")).pack(side="left")
        tk.Radiobutton(auth_f, text="Use JSON", variable=self.var_auth_method, value="JSON", bg="#E0E0E0", font=("Arial", 9, "bold")).pack(side="left", padx=10)
        
        tk.Label(send_f, text="Subject", bg="#E0E0E0", font=("Arial", 10, "bold")).grid(row=4, column=0, sticky="e", pady=5)
        tk.Button(send_f, text="Pick", font=("Arial", 10), command=self.pick_subject).grid(row=4, column=1, sticky="w", padx=2)
        self.ent_subject = ttk.Entry(send_f)
        self.ent_subject.grid(row=4, column=2, columnspan=3, sticky="ew", padx=5)
        tk.Button(send_f, text="Import", font=("Arial", 10), command=self.import_subjects).grid(row=4, column=5, sticky="w", padx=2)
        
        # TFN Box - Now as a grid element that sticks right
        tfn_f = tk.LabelFrame(send_f, text="TFN CONFIG", bd=1, relief="solid", bg="#F5F5F5", font=("Arial", 9, "bold"))
        tfn_f.grid(row=0, column=6, rowspan=5, padx=(20, 5), pady=5, sticky="ne") # Stick to top-right
        
        tk.Label(tfn_f, text="TFN 1 (#TFN#)", bg="#F5F5F5", font=("Arial", 8)).grid(row=0, column=0, sticky="w", padx=5)
        tk.Checkbutton(tfn_f, text="B64", variable=self.var_tfn1_b64, bg="#F5F5F5", fg="green", font=("Arial", 7)).grid(row=0, column=1, sticky="e")
        self.ent_tfn1 = ttk.Entry(tfn_f, width=15)
        self.ent_tfn1.grid(row=1, column=0, columnspan=2, padx=5, pady=2, sticky="ew")
        
        tk.Label(tfn_f, text="TFN 2 (#TFNA#)", bg="#F5F5F5", font=("Arial", 8)).grid(row=2, column=0, sticky="w", padx=5, pady=(5,0))
        tk.Checkbutton(tfn_f, text="B64", variable=self.var_tfn2_b64, bg="#F5F5F5", fg="green", font=("Arial", 7)).grid(row=2, column=1, sticky="e", pady=(5,0))
        self.ent_tfn2 = ttk.Entry(tfn_f, width=15)
        self.ent_tfn2.grid(row=3, column=0, columnspan=2, padx=5, pady=2, sticky="ew")
        
        tk.Checkbutton(tfn_f, text="Software Format?", variable=self.var_soft_fmt, bg="#F5F5F5", font=("Arial", 8)).grid(row=4, column=0, columnspan=2, sticky="w", padx=5)
        tk.Button(tfn_f, text="Help", fg="blue", bg="#F5F5F5", font=("Arial", 8), 
                  command=lambda: messagebox.showinfo("Info", "#TFN# and #TFNA# will be replaced in body.")).grid(row=5, column=0, columnspan=2, pady=5)

        tk.Button(main_frame, text="Check Bounce", bg="red", fg="white", font=("Arial", 9, "bold"), command=self.check_bounce).pack(anchor="w", padx=15, pady=2)
        
        # Body Section
        body_f = tk.Frame(main_frame, bg="#E0E0E0")
        body_f.pack(fill="both", expand=True, padx=10)
        
        body_left = tk.Frame(body_f, bg="#E0E0E0", width=120)
        body_left.pack(side="left", fill="y")
        tk.Label(body_left, text="Body", font=("Arial", 11, "bold"), bg="#E0E0E0").pack(anchor="w")
        self.var_html_body = tk.BooleanVar(value=True)
        tk.Checkbutton(body_left, text="Html Body ?", variable=self.var_html_body, font=("Arial", 10, "bold"), bg="#E0E0E0").pack(anchor="w")
        tk.Checkbutton(body_left, text="Auto Body Style", variable=self.var_auto_body_style, bg="#E0E0E0").pack(anchor="w")
        tk.Button(body_left, text="Import", font=("Arial", 10, "bold"), command=self.import_body, bg="#E0E0E0").pack(anchor="w", pady=2)
        tk.Checkbutton(body_left, text="Auto Body", variable=self.var_auto_body, bg="#E0E0E0").pack(anchor="w")
        
        # Pick button row
        pick_f = tk.Frame(body_left, bg="#E0E0E0")
        pick_f.pack(anchor="w", pady=10)
        tk.Label(pick_f, text="Pick", font=("Arial", 10, "bold"), bg="#E0E0E0").pack(side="right")
        
        body_txt_f = tk.Frame(body_f, bg="white", bd=1, relief="sunken")
        body_txt_f.pack(side="left", fill="both", expand=True, padx=5)
        
        lbl_mod = tk.Label(body_txt_f, text="Modify By AI ↓", fg="blue", bg="white", font=("Arial", 8))
        lbl_mod.pack(anchor="ne")
        self.txt_body = tk.Text(body_txt_f, height=10, bg="white", borderwidth=0)
        self.txt_body.pack(fill="both", expand=True)
        self.txt_body.insert("1.0", "<h1>[First_Name], Your Invoice</h1>\n<p>Amount: $150.00</p>")

        # Delay Settings
        delay_f = tk.Frame(main_frame, bg="#E0E0E0")
        delay_f.pack(fill="x", pady=5)
        tk.Label(delay_f, text="Delay (M.Sec)", bg="#E0E0E0").pack(side="left", padx=5)
        self.spn_delay = ttk.Spinbox(delay_f, from_=0, to=9999, width=6)
        self.spn_delay.set(1000)
        self.spn_delay.pack(side="left")
        tk.Checkbutton(delay_f, text="Each", variable=self.var_delay_each, bg="#E0E0E0").pack(side="left")
        tk.Checkbutton(delay_f, text="Every 50", variable=self.var_delay_every50, bg="#E0E0E0").pack(side="left")

        # Content Generation Options
        gen_f = tk.Frame(main_frame, bg="#E0E0E0")
        gen_f.pack(fill="x", padx=10, pady=5)
        
        content_left = tk.Frame(gen_f, bg="#E0E0E0")
        content_left.pack(side="left", fill="y", padx=5)
        tk.Label(content_left, text="Content (html)", font=("Arial", 11, "bold"), bg="#E0E0E0").pack(anchor="w")
        self.var_out_type = tk.StringVar(value="Raw pdf")
        opts = ["Flat pdf", "To image", "Inline image", "Raw pdf", "Inline Html", "Docx", "PPTX"]
        for o in opts:
            tk.Radiobutton(content_left, text=o, variable=self.var_out_type, value=o, font=("Arial", 10, "bold") if o=="Raw pdf" else ("Arial", 10), bg="#E0E0E0").pack(anchor="w")

        content_right = tk.Frame(gen_f, bg="#E0E0E0")
        content_right.pack(side="left", fill="both", expand=True)
        
        drop_f = tk.Frame(content_right, bg="#E0E0E0")
        drop_f.pack(fill="x", pady=2)
        tk.Label(drop_f, text="ContentType", font=("Arial", 11, "bold"), bg="#E0E0E0").pack(side="left")
        self.cb_ctype = ttk.Combobox(drop_f, values=["Auto"], width=10)
        self.cb_ctype.set("Auto")
        self.cb_ctype.pack(side="left", padx=5)
        
        tk.Label(drop_f, text="Img Forma", font=("Arial", 11, "bold"), bg="#E0E0E0").pack(side="left")
        img_formats = ["png", "jpeg", "jpg", "heic", "tiff", "bmp", "gif", "webp"]
        self.cb_iformat = ttk.Combobox(drop_f, values=img_formats, width=10)
        self.cb_iformat.set("png")
        self.cb_iformat.pack(side="left", padx=5)
        
        tk.Label(drop_f, text="Page Format", font=("Arial", 11, "bold"), bg="#E0E0E0").pack(side="right")
        self.cb_pformat = ttk.Combobox(drop_f, values=["A4", "Letter"], width=5)
        self.cb_pformat.set("A4")
        self.cb_pformat.pack(side="right", padx=5)
        
        pdf_f = tk.Frame(content_right, bg="#E0E0E0")
        pdf_f.pack(fill="x", pady=2)
        tk.Button(pdf_f, text="Upload Custom PDF", bg="#2196F3", fg="white", font=("Arial", 9, "bold"), command=self.browse_custom_pdf).pack(side="left", padx=5)
        self.lbl_custom_pdf = tk.Label(pdf_f, text="No file selected", bg="#E0E0E0", font=("Arial", 9))
        self.lbl_custom_pdf.pack(side="left", padx=5)
        
        msg_frame2 = tk.Frame(content_right, bg="white", height=100, bd=1, relief="sunken")
        msg_frame2.pack(fill="both", expand=True, padx=5, pady=5)
        
        lbl_mod_right = tk.Label(msg_frame2, text="Modify By AI ↓", fg="blue", bg="white", font=("Arial", 8))
        lbl_mod_right.pack(anchor="ne")
        self.txt_content = tk.Text(msg_frame2, bg="white", borderwidth=0, height=5)
        self.txt_content.pack(fill="both", expand=True)
        
        bot_ctrl = tk.Frame(content_right, bg="#E0E0E0")
        bot_ctrl.pack(fill="x", pady=5)
        tk.Button(bot_ctrl, text="Preview Attachment", bg="#4CAF50", fg="black", font=("Arial", 10, "bold"), command=self.preview_html_conversion).pack(side="left", padx=5)
        tk.Label(bot_ctrl, text="Html. W", bg="#E0E0E0").pack(side="left")
        self.spn_w = ttk.Spinbox(bot_ctrl, from_=0, to=4000, width=5)
        self.spn_w.set(800)
        self.spn_w.pack(side="left")
        tk.Label(bot_ctrl, text="H :", bg="#E0E0E0").pack(side="left")
        self.spn_h = ttk.Spinbox(bot_ctrl, from_=0, to=4000, width=5)
        self.spn_h.set(0)
        self.spn_h.pack(side="left")
        tk.Checkbutton(bot_ctrl, text="Random Width", variable=self.var_random_width, bg="#E0E0E0", font=("Arial", 7)).pack(side="left", anchor="s")
        
        tk.Checkbutton(bot_ctrl, text="Test Mail ?", variable=self.var_test_mail, bg="#E0E0E0").pack(side="right", padx=5)
        tk.Button(bot_ctrl, text="Send", bg="#4CAF50", fg="white", font=("Arial", 14, "bold"), width=10, command=self.send_dispatch).pack(side="right", padx=20)
        
        # Logging UI
        log_frame = tk.Frame(main_frame, bg="#111111")
        log_frame.pack(fill="both", expand=True, padx=10, pady=5)
        tk.Label(log_frame, text="Execution Logs", fg="white", bg="#111111", font=("Arial", 10, "bold")).pack(anchor="w", padx=2, pady=2)
        self.txt_logs = tk.Text(log_frame, height=5, bg="#000000", fg="#00FF00", font=("Consolas", 10))
        self.txt_logs.pack(fill="both", expand=True, padx=2, pady=2)
        
        # Bottom Bar
        bot_bar = tk.Frame(self.root, bg="#333333", height=30)
        bot_bar.pack(fill="x", side="bottom")
        tk.Label(bot_bar, text="Last Used API : ", fg="red", bg="#333333").pack(side="left")
        tk.Label(bot_bar, text="120 items", fg="gray", bg="#333333").pack(side="left", padx=20)
        tk.Label(bot_bar, text="Total mail sent 0 of 0", fg="white", bg="#333333", font=("Arial", 12, "bold")).pack(side="right", padx=10)
        # Final UI Load
        self.switch_task(0)

    # --- TASK MANAGEMENT ---
    def dump_default_state(self):
        return {
            'target_data': None,
            'sender_data': [],
            'failed_emails': [],
            'logs': "Initialization...\n",
            'custom_pdf_path': None,
            'vals': {
                'var_rotate': False, 'var_grayscale': False, 'var_crop': False, 'var_hq': False,
                'var_hsize': False, 'var_limit_check': False, 'var_auto_body_style': False,
                'var_auto_body': False, 'var_delay_each': False, 'var_delay_every50': False,
                'var_random_width': False, 'var_test_mail': True, 'var_tfn1_b64': False,
                'var_tfn2_b64': False, 'var_soft_fmt': False, 'var_unsub': False,
                'var_header': False, 'var_color': False, 'var_with_name': False,
                'var_html_body': True, 'var_geo': "USA", 'var_auth_method': "Manual",
                'var_out_type': "Raw pdf",
                'ent_date': time.strftime("%d/%m/%Y"), 'ent_name': "", 'ent_sender': "",
                'ent_app_pass': "", 'ent_subject': "", 'ent_tfn1': "", 'ent_tfn2': "",
                'spn_rotate': "50", 'spn_delay': "1000", 'spn_w': "800", 'spn_h': "0",
                'cb_ctype': "Auto", 'cb_iformat': "png", 'cb_pformat': "A4",
                'txt_targets': "", 'txt_body': "<h1>[First_Name], Your Invoice</h1>\n<p>Amount: $150.00</p>",
                'txt_content': ""
            }
        }

    def capture_current_state(self):
        return {
            'target_data': self.target_data,
            'sender_data': self.sender_data,
            'failed_emails': list(self.failed_emails),
            'custom_pdf_path': self.custom_pdf_path,
            'logs': self.txt_logs.get("1.0", tk.END),
            'vals': {
                'var_rotate': self.var_rotate.get(), 'var_grayscale': self.var_grayscale.get(),
                'var_crop': self.var_crop.get(), 'var_hq': self.var_hq.get(),
                'var_hsize': self.var_hsize.get(), 'var_limit_check': self.var_limit_check.get(),
                'var_auto_body_style': self.var_auto_body_style.get(),
                'var_auto_body': self.var_auto_body.get(), 'var_delay_each': self.var_delay_each.get(),
                'var_delay_every50': self.var_delay_every50.get(),
                'var_random_width': self.var_random_width.get(), 'var_test_mail': self.var_test_mail.get(),
                'var_tfn1_b64': self.var_tfn1_b64.get(), 'var_tfn2_b64': self.var_tfn2_b64.get(),
                'var_soft_fmt': self.var_soft_fmt.get(), 'var_unsub': self.var_unsub.get(),
                'var_header': self.var_header.get(), 'var_color': self.var_color.get(),
                'var_with_name': self.var_with_name.get(), 'var_html_body': self.var_html_body.get(),
                'var_geo': self.var_geo.get(), 'var_auth_method': self.var_auth_method.get(),
                'var_out_type': self.var_out_type.get(),
                'ent_date': self.ent_date.get(), 'ent_name': self.ent_name.get(),
                'ent_sender': self.ent_sender.get(), 'ent_app_pass': self.ent_app_pass.get(),
                'ent_subject': self.ent_subject.get(), 'ent_tfn1': self.ent_tfn1.get(),
                'ent_tfn2': self.ent_tfn2.get(), 'spn_rotate': self.spn_rotate.get(),
                'spn_delay': self.spn_delay.get(), 'spn_w': self.spn_w.get(),
                'spn_h': self.spn_h.get(), 'cb_ctype': self.cb_ctype.get(),
                'cb_iformat': self.cb_iformat.get(), 'cb_pformat': self.cb_pformat.get(),
                'txt_targets': self.txt_targets.get("1.0", tk.END),
                'txt_body': self.txt_body.get("1.0", tk.END),
                'txt_content': self.txt_content.get("1.0", tk.END)
            }
        }

    def apply_state(self, state):
        self.target_data = state['target_data']
        self.sender_data = state['sender_data']
        self.failed_emails = state['failed_emails']
        self.custom_pdf_path = state.get('custom_pdf_path', None)
        if hasattr(self, 'lbl_custom_pdf'):
            self.lbl_custom_pdf.config(text=os.path.basename(self.custom_pdf_path) if self.custom_pdf_path else "No file selected")
        
        self.txt_logs.delete("1.0", tk.END)
        self.txt_logs.insert("1.0", state['logs'])
        self.txt_logs.see(tk.END)
        
        v = state['vals']
        self.var_rotate.set(v['var_rotate'])
        self.var_grayscale.set(v['var_grayscale'])
        self.var_crop.set(v['var_crop'])
        self.var_hq.set(v['var_hq'])
        self.var_hsize.set(v['var_hsize'])
        self.var_limit_check.set(v['var_limit_check'])
        self.var_auto_body_style.set(v['var_auto_body_style'])
        self.var_auto_body.set(v['var_auto_body'])
        self.var_delay_each.set(v['var_delay_each'])
        self.var_delay_every50.set(v['var_delay_every50'])
        self.var_random_width.set(v['var_random_width'])
        self.var_test_mail.set(v['var_test_mail'])
        self.var_tfn1_b64.set(v['var_tfn1_b64'])
        self.var_tfn2_b64.set(v['var_tfn2_b64'])
        self.var_soft_fmt.set(v['var_soft_fmt'])
        self.var_unsub.set(v['var_unsub'])
        self.var_header.set(v['var_header'])
        self.var_color.set(v['var_color'])
        self.var_with_name.set(v['var_with_name'])
        self.var_html_body.set(v['var_html_body'])
        self.var_geo.set(v['var_geo'])
        self.var_auth_method.set(v['var_auth_method'])
        self.var_out_type.set(v['var_out_type'])
        
        self.ent_date.delete(0, tk.END); self.ent_date.insert(0, v['ent_date'])
        self.ent_name.delete(0, tk.END); self.ent_name.insert(0, v['ent_name'])
        self.ent_sender.delete(0, tk.END); self.ent_sender.insert(0, v['ent_sender'])
        self.ent_app_pass.delete(0, tk.END); self.ent_app_pass.insert(0, v['ent_app_pass'])
        self.ent_subject.delete(0, tk.END); self.ent_subject.insert(0, v['ent_subject'])
        self.ent_tfn1.delete(0, tk.END); self.ent_tfn1.insert(0, v['ent_tfn1'])
        self.ent_tfn2.delete(0, tk.END); self.ent_tfn2.insert(0, v['ent_tfn2'])
        
        self.spn_rotate.set(v['spn_rotate'])
        self.spn_delay.set(v['spn_delay'])
        self.spn_w.set(v['spn_w'])
        self.spn_h.set(v['spn_h'])
        
        self.cb_ctype.set(v['cb_ctype'])
        self.cb_iformat.set(v['cb_iformat'])
        self.cb_pformat.set(v['cb_pformat'])
        
        self.txt_targets.delete("1.0", tk.END); self.txt_targets.insert("1.0", v['txt_targets'])
        self.txt_body.delete("1.0", tk.END); self.txt_body.insert("1.0", v['txt_body'])
        self.txt_content.delete("1.0", tk.END); self.txt_content.insert("1.0", v['txt_content'])

    def create_task_button(self, idx):
        label = f"→ Task {idx + 1}"
        btn = tk.Button(self.task_bar, text=label, bg="white", font=("Arial", 10, "bold"), width=10, 
                        command=lambda: self.switch_task(idx))
        btn.pack(side="left", padx=2, pady=5)
        
        strip = tk.Frame(self.task_bar, bg="#00BCD4" if idx == self.current_task_idx else "#FFC107", height=4, width=80)
        strip.place(in_=btn, relx=0, rely=1.0, anchor="sw", relwidth=1.0)
        
        self.task_buttons[idx] = btn
        self.task_strips[idx] = strip

    def switch_task(self, idx):
        if idx >= len(self.tasks): return
        
        # Save current
        self.tasks[self.current_task_idx] = self.capture_current_state()
        
        # Update UI indices
        self.current_task_idx = idx
        
        # Load new
        self.apply_state(self.tasks[idx])
        
        # Update button highlights (Cyan for active, Amber for others)
        for i, strip in self.task_strips.items():
             strip.configure(bg="#00BCD4" if i == idx else "#FFC107")

    def add_task(self):
        if len(self.tasks) >= 5:
            messagebox.showwarning("Limit Reached", "Maximum of 5 tasks allowed.")
            return
            
        new_idx = len(self.tasks)
        self.tasks.append(self.dump_default_state())
        self.create_task_button(new_idx)
        self.switch_task(new_idx)
        self.log_message(f"Task {new_idx + 1} added.")


    # --- ACTIONS ---
    def show_error_list(self):
        win = tk.Toplevel(self.root)
        win.title("Error List — Failed Emails")
        win.geometry("500x350")
        win.configure(bg="#1e1e1e")
        tk.Label(win, text=f"Failed Emails ({len(self.failed_emails)})", fg="red", bg="#1e1e1e",
                 font=("Arial", 12, "bold")).pack(pady=8)
        txt = tk.Text(win, bg="#111", fg="#ff6b6b", font=("Consolas", 10), relief="flat")
        txt.pack(fill="both", expand=True, padx=10, pady=5)
        if self.failed_emails:
            txt.insert("1.0", "\n".join(self.failed_emails))
        else:
            txt.insert("1.0", "No failures recorded yet.")
        txt.config(state="disabled")
        btn_f = tk.Frame(win, bg="#1e1e1e")
        btn_f.pack(fill="x", padx=10, pady=5)
        tk.Button(btn_f, text="Copy All", bg="#2196F3", fg="white",
                  command=lambda: (win.clipboard_clear(), win.clipboard_append("\n".join(self.failed_emails)),
                                   messagebox.showinfo("Copied", "Failed emails copied to clipboard.", parent=win))).pack(side="left", padx=5)
        tk.Button(btn_f, text="Clear List", bg="#f44336", fg="white",
                  command=lambda: (self.failed_emails.clear(), win.destroy(),
                                   self.log_message("Error list cleared."))).pack(side="left", padx=5)
        tk.Button(btn_f, text="Close", bg="#444", fg="white", command=win.destroy).pack(side="right", padx=5)

    def clear_cache(self):
        self.txt_logs.delete("1.0", tk.END)
        self.log_message("Cache/Logs cleared.")

    def check_bounce(self):
        messagebox.showinfo("Bounce Check", "Bounce checker initialized. Scanning IMAP for undelivered reports...")

    def log_message(self, msg, task_idx=None):
        def _log():
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            log_line = f"[{timestamp}] {msg}\n"
            
            target_idx = task_idx if task_idx is not None else self.current_task_idx
            
            # Save to task state string
            if target_idx < len(self.tasks):
                self.tasks[target_idx]['logs'] += log_line
            
            # Update UI if it's the active task
            if target_idx == self.current_task_idx:
                self.txt_logs.insert(tk.END, log_line)
                self.txt_logs.see(tk.END)
        self.root.after(0, _log)

    def paste_targets(self):
        try:
            clipboard_content = self.root.clipboard_get()
            if clipboard_content:
                # Append to existing
                self.txt_targets.insert(tk.END, clipboard_content + "\n")
                
                # Split and convert to dataframe internally so Send logic still works
                all_text = self.txt_targets.get("1.0", tk.END).strip()
                emails = [e.strip() for e in all_text.split('\n') if e.strip()]
                self.target_data = pd.DataFrame({"Email": emails, "Name": ["Customer"]*len(emails)})
                
                messagebox.showinfo("Pasted", f"Pasted and loaded {len(emails)} total recipients from text box.")
        except tk.TclError:
            messagebox.showwarning("Clipboard", "Clipboard is empty or does not contain text.")

    def clear_targets(self):
        if messagebox.askyesno("Clear List", "Are you sure you want to delete all recipients in the list?"):
            self.txt_targets.delete("1.0", tk.END)
            self.target_data = None
            self.log_message("Recipient list cleared.")

    def import_data(self):
        # Implement recipients load
        path = filedialog.askopenfilename(filetypes=[("CSV/Excel", "*.csv *.xlsx")])
        if path:
            try:
                if path.endswith('.csv'):
                    self.target_data = pd.read_csv(path)
                else:
                    self.target_data = pd.read_excel(path)
                    
                count = len(self.target_data)
                self.txt_targets.delete("1.0", tk.END)
                for index, row in self.target_data.iterrows():
                    email = row.get('Email', row.get('email', str(row.iloc[0])))
                    self.txt_targets.insert("end", f"{email}\n")
                messagebox.showinfo("Success", f"Loaded {count} recipients")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to parse data: {str(e)}")

    def import_json(self):
        """
        Imports sender JSON. Handles both account lists and Google Client Secrets.
        If Client Secret is detected, triggers OAuth flow.
        """
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if path:
            try:
                # Handle filename-based autofill (e.g., test@gmail.com.json)
                filename = os.path.basename(path)
                if filename.lower().endswith(".json"):
                    email_cand = filename[:-5] # remove .json
                    if "@" in email_cand:
                        self.ent_sender.delete(0, tk.END)
                        self.ent_sender.insert(0, email_cand)
                        
                        # Extract name (part before @)
                        name_cand = email_cand.split("@")[0].capitalize()
                        self.ent_name.delete(0, tk.END)
                        self.ent_name.insert(0, name_cand)
                        self.log_message(f"Autofilled Sender: {email_cand}, Name: {name_cand}")

                with open(path, 'r') as f:
                    data = json.load(f)
                    
                    # Check for Google Client Secret format
                    if "installed" in data or "web" in data:
                        self.client_secrets_path = path
                        self.log_message("Google Client Secret detected. Click 'Auth Google' near Send button to authorize.")
                        messagebox.showinfo("Ready", "Client Secret loaded. Please click 'Auth Google' near the Send button to authorize your account.")
                        return

                    if isinstance(data, dict):
                        data = [data] # Wrap in list if single object
                        
                    if isinstance(data, list) and len(data) > 0:
                        self.sender_data = data
                        messagebox.showinfo("Success", f"Loaded {len(data)} sender config(s).")
                        self.var_auth_method.set("JSON") # Switch UI automatically
                    elif isinstance(data, list):
                        messagebox.showwarning("Warning", "JSON list is empty.")
                    else:
                        messagebox.showwarning("Warning", "JSON must be a list or object.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to parse JSON: {str(e)}")

    def trigger_google_auth(self):
        # Deleted in favor of automatic trigger at send time
        pass

    def run_google_auth_flow(self, client_secrets_path):
        """ Runs the Google OAuth flow in a background thread. """
        SCOPES = ['https://www.googleapis.com/auth/gmail.send']
        try:
            flow = InstalledAppFlow.from_client_secrets_file(client_secrets_path, SCOPES)
            creds = flow.run_local_server(port=0)
            
            # Extract credential details
            auth_data = {
                "email": self.ent_sender.get().strip(),
                "token": creds.token,
                "refresh_token": creds.refresh_token,
                "token_uri": creds.token_uri,
                "client_id": creds.client_id,
                "client_secret": creds.client_secret,
                "scopes": creds.scopes
            }
            
            self.sender_data = [auth_data]
            self.root.after(0, lambda: self.log_message("Google OAuth Authorization Successful!"))
            self.root.after(0, lambda: self.var_auth_method.set("JSON"))
            self.root.after(0, lambda: messagebox.showinfo("Authorized", "Google account authorized successfully!"))
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("OAuth Error", f"Failed to authorize: {str(e)}"))
            self.root.after(0, lambda: self.log_message(f"OAuth Error: {e}"))

    def browse_custom_pdf(self):
        path = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if path:
            self.custom_pdf_path = path
            if hasattr(self, 'lbl_custom_pdf'):
                self.lbl_custom_pdf.config(text=os.path.basename(path))

    def import_subjects(self):
        # Open file dialog for txt or csv containing subjects
        path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt"), ("CSV Files", "*.csv")])
        if path:
            try:
                subjects = []
                with open(path, 'r', encoding='utf-8') as f:
                    for line in f:
                        clean_line = line.strip()
                        if clean_line:
                            subjects.append(clean_line)
                
                if subjects:
                    # Create spintax {sub1|sub2|sub3}
                    spintax_str = "{" + "|".join(subjects) + "}"
                    self.ent_subject.delete(0, tk.END)
                    self.ent_subject.insert(0, spintax_str)
                    messagebox.showinfo("Success", f"Loaded {len(subjects)} subjects into Spintax format.")
                else:
                    messagebox.showwarning("Warning", "The selected file is empty or has no valid lines.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load subjects: {str(e)}")

    def import_names(self):
        path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt"), ("CSV Files", "*.csv")])
        if path:
            try:
                names = []
                with open(path, 'r', encoding='utf-8') as f:
                    for line in f:
                        clean_line = line.strip()
                        if clean_line:
                            names.append(clean_line)
                
                if names:
                    spintax_str = "{" + "|".join(names) + "}"
                    self.ent_name.delete(0, tk.END)
                    self.ent_name.insert(0, spintax_str)
                    messagebox.showinfo("Success", f"Loaded {len(names)} names into Spintax format.")
                else:
                    messagebox.showwarning("Warning", "The selected file is empty or has no valid lines.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load names: {str(e)}")

    def import_body(self):
        path = filedialog.askopenfilename(filetypes=[("Text/HTML Files", "*.txt *.html *.htm")])
        if path:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                self.txt_body.delete("1.0", tk.END)
                self.txt_body.insert("1.0", content)
                messagebox.showinfo("Success", "Loaded HTML body successfully.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load HTML body: {str(e)}")

    def pick_name(self):
        val = self.ent_name.get()
        if "{" in val and "}" in val:
            # Extract spintax content
            match = re.search(r'\{([^}]+)\}', val)
            if match:
                options = match.group(1).split('|')
                choice = random.choice(options)
                self.ent_name.delete(0, tk.END)
                self.ent_name.insert(0, choice)
        elif val == "":
            messagebox.showwarning("Warning", "The Name field is empty. Please import a list first.")
        else:
             messagebox.showinfo("Info", "The Name field is not in Spintax format (e.g., {A|B|C}). Unchanged.")

    def pick_subject(self):
        val = self.ent_subject.get()
        if "{" in val and "}" in val:
            match = re.search(r'\{([^}]+)\}', val)
            if match:
                options = match.group(1).split('|')
                choice = random.choice(options)
                self.ent_subject.delete(0, tk.END)
                self.ent_subject.insert(0, choice)
        elif val == "":
             messagebox.showwarning("Warning", "The Subject field is empty. Please import a list first.")
        else:
             messagebox.showinfo("Info", "The Subject field is not in Spintax format (e.g., {A|B|C}). Unchanged.")


    def preview_html_conversion(self):
        try:
            html = self.txt_content.get("1.0", "end-1c")
            # Replace placeholder tags for the preview
            sample_inv = f"INV-{random.randint(1000000, 9999999)}"
            sample_txn = "".join(random.choices(string.ascii_uppercase + string.digits, k=10))
            sample_date = time.strftime("%B %d, %Y")
            html = html.replace("#INVOICE#", sample_inv).replace("[Invoice_Number]", sample_inv)
            html = html.replace("#RANDOM#", sample_txn).replace("[Transaction_ID]", sample_txn)
            html = html.replace("#DATE#", sample_date).replace("[Issue_Date]", sample_date)
            
            output_mode = self.var_out_type.get()
            
            # Prepare config for service
            config = {
                'width': int(self.spn_w.get()),
                'height': int(self.spn_h.get()),
                'random_width': self.var_random_width.get(),
                'grayscale': self.var_grayscale.get(),
                'crop': self.var_crop.get(),
                'hq': self.var_hq.get(),
                'hsize': self.var_hsize.get(),
                'page_format': self.cb_pformat.get(),
                'inv_no': sample_inv
            }
            
            data, filename, _ = generate_attachment_buffer(html, output_mode, self.cb_iformat.get(), config)
            
            if data:
                # Save preview to local file for opening
                preview_path = f"preview_{filename}"
                with open(preview_path, "wb") as f:
                    f.write(data)
                
                messagebox.showinfo("Preview Saved", f"Generated attachment as {preview_path}. Opening...")
                import platform
                if platform.system() == 'Darwin':
                    os.system(f"open {preview_path}")
                elif platform.system() == 'Windows':
                    os.system(f"start {preview_path}")
            else:
                messagebox.showerror("Error", "Failed to generate preview data")
        except Exception as e:
            messagebox.showerror("Error rendering", str(e))

    def send_dispatch(self):
        if self.target_data is None or len(self.target_data) == 0:
            messagebox.showwarning("Validation", "No recipients imported!")
            return
            
        auth_choice = self.var_auth_method.get()
        if auth_choice == "JSON" and not self.sender_data and not self.client_secrets_path:
            messagebox.showwarning("Validation", "No sender JSON imported!")
            return
        elif auth_choice == "Manual":
            if not self.ent_sender.get().strip() or not self.ent_app_pass.get().strip():
                messagebox.showwarning("Validation", "Please enter Sender Mail and App Pass for Manual mode.")
                return
        
        # Collect UI Config
        ui_config = self.generate_ui_config()
        t_idx = self.current_task_idx
        
        # Check if we need to authorize first
        if auth_choice == "JSON" and self.client_secrets_path and not self.sender_data:
            self.log_message("Authorization required. Opening browser for Google OAuth...")
            threading.Thread(target=self.run_google_auth_flow_and_send, args=(self.client_secrets_path, ui_config, t_idx), daemon=True).start()
        else:
            threading.Thread(
                target=start_bulk_dispatch, 
                args=(self.target_data, self.sender_data, ui_config, lambda m: self.log_message(m, t_idx)), 
                daemon=True
            ).start()

    def generate_ui_config(self):
        return {
            'subject': self.ent_subject.get(),
            'raw_body_html': self.txt_body.get("1.0", "end-1c"),
            'raw_attachment_html': self.txt_content.get("1.0", "end-1c"),
            'sender_name': self.ent_name.get(),
            'img_format': self.cb_iformat.get(),
            'output_mode': self.var_out_type.get(),
            'tfn1': self.ent_tfn1.get(),
            'tfn1_b64': self.var_tfn1_b64.get(),
            'tfn2': self.ent_tfn2.get(),
            'tfn2_b64': self.var_tfn2_b64.get(),
            'soft_fmt': self.var_soft_fmt.get(),
            'geo': self.var_geo.get(),
            'test_mail': self.var_test_mail.get(),
            'delay': int(self.spn_delay.get()),
            'delay_each': self.var_delay_each.get(),
            'delay_50': self.var_delay_every50.get(),
            'rotate_limit': int(self.spn_rotate.get()),
            'rotate_each': self.var_rotate.get(),
            'auth_method': self.var_auth_method.get(),
            'manual_sender': self.ent_sender.get(),
            'manual_pass': self.ent_app_pass.get(),
            'unsub': self.var_unsub.get(),
            'header': self.var_header.get(),
            'color': self.var_color.get(),
            'with_name': self.var_with_name.get(),
            'grayscale': self.var_grayscale.get(),
            'crop': self.var_crop.get(),
            'hq': self.var_hq.get(),
            'hsize': self.var_hsize.get(),
            'limit_check': self.var_limit_check.get(),
            'width': int(self.spn_w.get()),
            'height': int(self.spn_h.get()),
            'random_width': self.var_random_width.get(),
            'page_format': self.cb_pformat.get(),
            'custom_pdf_path': self.custom_pdf_path
        }

    def run_google_auth_flow_and_send(self, client_secrets_path, ui_config, t_idx):
        SCOPES = ['https://www.googleapis.com/auth/gmail.send']
        try:
            flow = InstalledAppFlow.from_client_secrets_file(client_secrets_path, SCOPES)
            creds = flow.run_local_server(port=0)
            
            auth_data = {
                "email": self.ent_sender.get().strip(),
                "token": creds.token,
                "refresh_token": creds.refresh_token,
                "token_uri": creds.token_uri,
                "client_id": creds.client_id,
                "client_secret": creds.client_secret,
                "scopes": creds.scopes
            }
            
            self.sender_data = [auth_data]
            self.root.after(0, lambda: self.log_message("Google OAuth Successful! Starting dispatch..."))
            
            # Now start the dispatch
            start_bulk_dispatch(self.target_data, self.sender_data, ui_config, lambda m: self.log_message(m, t_idx))
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("OAuth Error", f"Failed to authorize: {str(e)}"))
            self.root.after(0, lambda: self.log_message(f"OAuth Error: {e}"))
            

if __name__ == "__main__":
    root = tk.Tk()
    app = RoxInvoiceAppBM2(root)
    root.mainloop()
