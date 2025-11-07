from __future__ import annotations

import sqlite3
import sys
import tkinter as tk
from tkinter import messagebox, ttk

from .config import DatabaseConnection, UserRepository
from .ui_main import CCTVMonitoringSystem


class AuthWindow:
    """Pantalla de autenticación con login y registro."""

    PALETTE = {
        "bg": "#0b1120",
        "hero_bg": "#111b2c",
        "hero_text": "#f1f5f9",
        "hero_accent": "#38bdf8",
        "hero_muted": "#94a3b8",
        "card_bg": "#0f172a",
        "text": "#e2e8f0",
        "muted": "#94a3b8",
        "accent": "#2563eb",
        "accent_hover": "#1d4ed8",
        "outline": "#1f2937",
        "input_bg": "#172554",
        "input_border": "#1d4ed8",
        "success": "#22c55e",
        "error": "#f87171",
        "info": "#38bdf8",
    }

    def __init__(self, root):
        self.root = root
        self.db = DatabaseConnection.get_instance()
        self.users = UserRepository(self.db)

        self.status_var = tk.StringVar(value="")
        self.mode = tk.StringVar(value="login")

        self.login_email_var = tk.StringVar()
        self.login_pass_var = tk.StringVar()

        self.register_name_var = tk.StringVar()
        self.register_email_var = tk.StringVar()
        self.register_pass_var = tk.StringVar()
        self.register_confirm_var = tk.StringVar()
        self._pending_registration = None
        self.is_fullscreen = False

        self._configure_style()
        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.bind("<Return>", self._submit_current)
        self.root.bind("<F11>", self._toggle_fullscreen)
        self.root.bind("<Escape>", self._end_fullscreen)

    def _configure_style(self):
        c = self.PALETTE
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("Auth.TFrame", background=c["bg"])
        style.configure("AuthHero.TFrame", background=c["hero_bg"])
        style.configure("AuthCard.TFrame", background=c["card_bg"])

        style.configure(
            "HeroTitle.TLabel",
            background=c["hero_bg"],
            foreground=c["hero_text"],
            font=("Segoe UI", 24, "bold"),
        )
        style.configure(
            "HeroSubtitle.TLabel",
            background=c["hero_bg"],
            foreground=c["hero_muted"],
            font=("Segoe UI", 11),
        )
        style.configure("HeroBadge.TFrame", background="#1e293b")
        style.configure(
            "HeroBadgeTitle.TLabel",
            background="#1e293b",
            foreground=c["hero_text"],
            font=("Segoe UI Semibold", 12),
        )
        style.configure(
            "HeroBadgeText.TLabel",
            background="#1e293b",
            foreground=c["hero_muted"],
            font=("Segoe UI", 9),
        )
        style.configure(
            "HeroFeatureIcon.TLabel",
            background=c["hero_bg"],
            foreground=c["hero_accent"],
            font=("Segoe UI", 16),
        )
        style.configure(
            "HeroFeatureTitle.TLabel",
            background=c["hero_bg"],
            foreground=c["hero_text"],
            font=("Segoe UI Semibold", 12),
        )
        style.configure(
            "HeroFeatureText.TLabel",
            background=c["hero_bg"],
            foreground=c["hero_muted"],
            font=("Segoe UI", 10),
        )

        style.configure(
            "CardTitle.TLabel",
            background=c["card_bg"],
            foreground=c["text"],
            font=("Segoe UI", 21, "bold"),
        )
        style.configure(
            "CardSubtitle.TLabel",
            background=c["card_bg"],
            foreground=c["muted"],
            font=("Segoe UI", 10),
        )
        style.configure(
            "FieldLabel.TLabel",
            background=c["card_bg"],
            foreground=c["text"],
            font=("Segoe UI Semibold", 10),
        )
        style.configure(
            "FieldHint.TLabel",
            background=c["card_bg"],
            foreground=c["muted"],
            font=("Segoe UI", 9),
        )
        style.configure(
            "AuthStatus.TLabel",
            background=c["card_bg"],
            foreground=c["error"],
            font=("Segoe UI", 9),
        )

        style.configure(
            "Auth.TEntry",
            fieldbackground=c["input_bg"],
            foreground=c["text"],
            bordercolor=c["outline"],
            lightcolor=c["input_border"],
            darkcolor=c["outline"],
            insertcolor=c["text"],
            padding=6,
        )
        style.map(
            "Auth.TEntry",
            bordercolor=[("focus", c["input_border"])],
            lightcolor=[("focus", c["input_border"])],
            darkcolor=[("focus", c["input_border"])],
            fieldbackground=[("focus", "#1e1b4b")],
        )

        style.configure(
            "AuthAccent.TButton",
            background=c["accent"],
            foreground="#ffffff",
            font=("Segoe UI Semibold", 11),
            padding=(18, 10),
            borderwidth=0,
        )
        style.map(
            "AuthAccent.TButton",
            background=[("active", c["accent_hover"]), ("disabled", c["outline"])],
            foreground=[("disabled", c["muted"])],
        )

        style.configure(
            "AuthSecondary.TButton",
            background=c["card_bg"],
            foreground=c["muted"],
            font=("Segoe UI", 10),
            padding=(0, 8),
            borderwidth=0,
        )
        style.map("AuthSecondary.TButton", foreground=[("active", c["text"])])

        style.configure("AuthToggle.TFrame", background=c["card_bg"])
        style.configure(
            "AuthToggle.TButton",
            background=c["card_bg"],
            foreground=c["muted"],
            font=("Segoe UI Semibold", 11),
            padding=(14, 8),
            borderwidth=0,
        )
        style.map("AuthToggle.TButton", foreground=[("active", c["text"])])

        style.configure(
            "AuthToggleActive.TButton",
            background=c["accent"],
            foreground="#ffffff",
            font=("Segoe UI Semibold", 11),
            padding=(14, 8),
            borderwidth=0,
        )
        style.map(
            "AuthToggleActive.TButton", background=[("active", c["accent_hover"])]
        )

    def _build_ui(self):
        c = self.PALETTE
        self.root.title("Ninera Virtual - Acceso seguro")
        self.root.geometry("1120x720")
        self.root.minsize(960, 620)
        self.root.resizable(True, True)
        self.root.configure(background=c["bg"])
        if sys.platform.startswith("win"):
            try:
                self.root.state("zoomed")
            except tk.TclError:
                pass

        outer = ttk.Frame(self.root, style="Auth.TFrame")
        outer.pack(fill=tk.BOTH, expand=True)

        main = ttk.Frame(outer, style="Auth.TFrame")
        main.pack(fill=tk.BOTH, expand=True, padx=32, pady=28)
        main.columnconfigure(0, weight=7)
        main.columnconfigure(1, weight=6)
        main.rowconfigure(0, weight=1)

        hero = ttk.Frame(main, style="AuthHero.TFrame", padding=(36, 40))
        hero.grid(row=0, column=0, sticky="nsew", padx=(0, 28))

        ttk.Label(hero, text="👶 Niñera Virtual", style="HeroTitle.TLabel").pack(anchor="w")
        ttk.Label(
            hero,
            text="Monitoreo inteligente de entornos infantiles con visión artificial, detección de riesgos y alertas instantáneas.",
            style="HeroSubtitle.TLabel",
            wraplength=360,
        ).pack(anchor="w", pady=(12, 0))

        badge = ttk.Frame(hero, style="HeroBadge.TFrame", padding=(18, 16))
        badge.pack(anchor="w", pady=(20, 22), fill=tk.X)
        ttk.Label(
            badge,
            text="Versión 4.0 + Patrones + Seguridad",
            style="HeroBadgeTitle.TLabel",
        ).pack(anchor="w")
        ttk.Label(
            badge,
            text="Incluye detección de tijeras, administración avanzada de zonas y autenticación con hashing PBKDF2.",
            style="HeroBadgeText.TLabel",
            wraplength=280,
        ).pack(anchor="w", pady=(6, 0))

        feats = ttk.Frame(hero, style="AuthHero.TFrame")
        feats.pack(fill=tk.BOTH, expand=True)
        items = [
            (
                "🛡️",
                "Seguridad proactiva",
                "Analizamos cámaras en tiempo real y alertamos ante riesgos potenciales.",
            ),
            (
                "⚡",
                "Reacción inmediata",
                "Recibe notificaciones con evidencia visual y registro histórico.",
            ),
            (
                "📊",
                "Control total",
                "Panel intuitivo, métricas y zonas configurables por cámara.",
            ),
        ]
        for icon, title, text in items:
            row = ttk.Frame(feats, style="AuthHero.TFrame")
            row.pack(anchor="w", fill=tk.X, pady=10)
            ttk.Label(row, text=icon, style="HeroFeatureIcon.TLabel").pack(side=tk.LEFT, padx=(0, 14))
            txt = ttk.Frame(row, style="AuthHero.TFrame")
            txt.pack(side=tk.LEFT, fill=tk.X, expand=True)
            ttk.Label(txt, text=title, style="HeroFeatureTitle.TLabel").pack(anchor="w")
            ttk.Label(txt, text=text, style="HeroFeatureText.TLabel", wraplength=280).pack(anchor="w")

        ttk.Label(
            hero,
            text="Activa tu cuenta en minutos y comienza a monitorear al instante.",
            style="HeroSubtitle.TLabel",
        ).pack(anchor="w", pady=(24, 0))

        card = ttk.Frame(main, style="AuthCard.TFrame", padding=(34, 38))
        card.grid(row=0, column=1, sticky="nsew")
        card.columnconfigure(0, weight=1)
        card.rowconfigure(3, weight=1)

        ttk.Label(card, text="Bienvenido de vuelta", style="CardTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            card,
            text="Inicia sesión con tu email o crea una cuenta para proteger a los más pequeños.",
            style="CardSubtitle.TLabel",
            wraplength=360,
        ).grid(row=1, column=0, sticky="w", pady=(8, 0))

        toggle = ttk.Frame(card, style="AuthToggle.TFrame")
        toggle.grid(row=2, column=0, sticky="ew", pady=(26, 18))
        toggle.columnconfigure((0, 1), weight=1)

        self.login_toggle = ttk.Button(
            toggle,
            text="Iniciar sesión",
            style="AuthToggleActive.TButton",
            command=lambda: self._show_form("login", reset_status=True),
        )
        self.login_toggle.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self.register_toggle = ttk.Button(
            toggle,
            text="Crear cuenta",
            style="AuthToggle.TButton",
            command=lambda: self._show_form("register", reset_status=True),
        )
        self.register_toggle.grid(row=0, column=1, sticky="ew", padx=(8, 0))

        forms = ttk.Frame(card, style="AuthCard.TFrame")
        forms.grid(row=3, column=0, sticky="nsew")
        forms.columnconfigure(0, weight=1)

        self.forms = {
            "login": self._build_login_form(forms),
            "register": self._build_register_form(forms),
        }
        self.forms["register"].grid_remove()

        self.status_label = ttk.Label(card, textvariable=self.status_var, style="AuthStatus.TLabel", anchor="w")
        self.status_label.grid(row=4, column=0, sticky="ew", pady=(18, 0))

        self._set_status("")
        self._show_form("login", reset_status=True)

    def _build_login_form(self, parent):
        frame = ttk.Frame(parent, style="AuthCard.TFrame")
        frame.grid(row=0, column=0, sticky="nsew")
        frame.columnconfigure(0, weight=1)

        ttk.Label(frame, text="Email", style="FieldLabel.TLabel").grid(row=0, column=0, sticky="w")
        self.login_email_entry = ttk.Entry(
            frame,
            style="Auth.TEntry",
            font=("Segoe UI", 11),
            textvariable=self.login_email_var,
        )
        self.login_email_entry.grid(row=1, column=0, sticky="ew", pady=(4, 14))

        ttk.Label(frame, text="Contrasena", style="FieldLabel.TLabel").grid(row=2, column=0, sticky="w")
        self.login_pass_entry = ttk.Entry(
            frame,
            style="Auth.TEntry",
            show="•",
            font=("Segoe UI", 11),
            textvariable=self.login_pass_var,
        )
        self.login_pass_entry.grid(row=3, column=0, sticky="ew", pady=(4, 18))

        ttk.Button(frame, text="Ingresar", style="AuthAccent.TButton", command=self._handle_login).grid(
            row=4, column=0, sticky="ew"
        )

        ttk.Button(
            frame,
            text="¿Aún sin cuenta? Regístrate",
            style="AuthSecondary.TButton",
            command=lambda: self._show_form("register", reset_status=True),
        ).grid(row=5, column=0, sticky="w", pady=(18, 0))

        return frame

    def _build_register_form(self, parent):
        frame = ttk.Frame(parent, style="AuthCard.TFrame")
        frame.grid(row=0, column=0, sticky="nsew")
        frame.columnconfigure(0, weight=1)

        ttk.Label(frame, text="Nombre completo", style="FieldLabel.TLabel").grid(row=0, column=0, sticky="w")
        self.reg_name_entry = ttk.Entry(
            frame,
            style="Auth.TEntry",
            font=("Segoe UI", 11),
            textvariable=self.register_name_var,
        )
        self.reg_name_entry.grid(row=1, column=0, sticky="ew", pady=(4, 12))

        ttk.Label(frame, text="Email", style="FieldLabel.TLabel").grid(row=2, column=0, sticky="w")
        self.reg_email_entry = ttk.Entry(
            frame,
            style="Auth.TEntry",
            font=("Segoe UI", 11),
            textvariable=self.register_email_var,
        )
        self.reg_email_entry.grid(row=3, column=0, sticky="ew", pady=(4, 12))

        ttk.Label(frame, text="Contrasena", style="FieldLabel.TLabel").grid(row=4, column=0, sticky="w")
        self.reg_pass_entry = ttk.Entry(
            frame,
            style="Auth.TEntry",
            show="*",
            font=("Segoe UI", 11),
            textvariable=self.register_pass_var,
        )
        self.reg_pass_entry.grid(row=5, column=0, sticky="ew", pady=(4, 12))

        ttk.Label(frame, text="Confirmar contrasena", style="FieldLabel.TLabel").grid(row=6, column=0, sticky="w")
        self.reg_confirm_entry = ttk.Entry(
            frame,
            style="Auth.TEntry",
            show="*",
            font=("Segoe UI", 11),
            textvariable=self.register_confirm_var,
        )
        self.reg_confirm_entry.grid(row=7, column=0, sticky="ew", pady=(4, 8))

        self.register_feedback = ttk.Label(frame, text="", style="FieldHint.TLabel", wraplength=340, anchor="w")
        self.register_feedback.grid(row=8, column=0, sticky="w", pady=(0, 8))

        ttk.Label(
            frame,
            text="La contrasena debe tener minimo 6 caracteres. Usa una combinacion facil de recordar y segura.",
            style="FieldHint.TLabel",
            wraplength=340,
        ).grid(row=9, column=0, sticky="w", pady=(0, 14))

        self.register_validate_btn = ttk.Button(
            frame,
            text="Verificar datos",
            style="AuthAccent.TButton",
            command=self._prepare_register,
        )
        self.register_validate_btn.grid(row=10, column=0, sticky="ew")
        self.register_validate_btn.state(["disabled"])
        self.register_validate_btn.configure(state=tk.DISABLED)

        self.register_confirm_btn = ttk.Button(
            frame,
            text="Confirmar registro",
            style="AuthAccent.TButton",
            command=self._confirm_register,
        )
        self.register_confirm_btn.grid(row=11, column=0, sticky="ew", pady=(8, 0))
        self.register_confirm_btn.state(["disabled"])
        self.register_confirm_btn.configure(state=tk.DISABLED)

        ttk.Button(
            frame,
            text="¿Ya tienes cuenta? Inicia sesión",
            style="AuthSecondary.TButton",
            command=lambda: self._show_form("login", reset_status=True),
        ).grid(row=12, column=0, sticky="w", pady=(18, 0))

        for var in (
            self.register_name_var,
            self.register_email_var,
            self.register_pass_var,
            self.register_confirm_var,
        ):
            var.trace_add("write", lambda *args: self._validate_register_fields())

        self._validate_register_fields()

        return frame

    def _show_form(self, mode: str, reset_status: bool = False):
        if mode not in self.forms:
            return
        self.mode.set(mode)
        for key, frame in self.forms.items():
            if key == mode:
                frame.grid()
            else:
                frame.grid_remove()
        self._update_toggle_styles()
        if reset_status:
            self._set_status("")
        if mode == "login":
            if hasattr(self, "login_email_entry"):
                self.login_email_entry.focus_set()
        else:
            if hasattr(self, "reg_name_entry"):
                self.reg_name_entry.focus_set()
        self._validate_register_fields()

    def _update_toggle_styles(self):
        if self.mode.get() == "login":
            self.login_toggle.configure(style="AuthToggleActive.TButton")
            self.register_toggle.configure(style="AuthToggle.TButton")
        else:
            self.login_toggle.configure(style="AuthToggle.TButton")
            self.register_toggle.configure(style="AuthToggleActive.TButton")

    def _set_status(self, message: str, tone: str = "error"):
        palette = self.PALETTE
        colors = {
            "error": palette["error"],
            "success": palette["success"],
            "info": palette["info"],
        }
        self.status_label.configure(foreground=colors.get(tone, palette["error"]))
        self.status_var.set(message)

    def _set_register_feedback(self, message: str, tone: str = "info"):
        if not hasattr(self, "register_feedback"):
            return
        palette = self.PALETTE
        colors = {
            "error": palette["error"],
            "success": palette["success"],
            "info": palette["muted"],
        }
        self.register_feedback.configure(text=message, foreground=colors.get(tone, palette["muted"]))

    def _validate_register_fields(self):
        if not hasattr(self, "register_validate_btn"):
            return False

        name = (self.register_name_var.get() or "").strip()
        email = (self.register_email_var.get() or "").strip()
        password = self.register_pass_var.get() or ""
        confirm = self.register_confirm_var.get() or ""

        self._pending_registration = None
        self.register_confirm_btn.state(["disabled"])
        self.register_confirm_btn.configure(state=tk.DISABLED)

        valid = False
        message = "Completa todos los campos para crear tu cuenta."
        tone = "info"

        if not name or not email or not password or not confirm:
            pass
        elif len(name) < 2:
            message = "Ingresa tu nombre completo (minimo 2 caracteres)."
            tone = "error"
        elif "@" not in email or "." not in email:
            message = "Introduce un email valido."
            tone = "error"
        elif len(password) < 6:
            message = "La contrasena debe tener al menos 6 caracteres."
            tone = "error"
        elif password != confirm:
            message = "Las contrasenas deben coincidir exactamente."
            tone = "error"
        else:
            message = "Listo para verificar los datos."
            tone = "success"
            valid = True

        if valid:
            self.register_validate_btn.state(["!disabled"])
            self.register_validate_btn.configure(state=tk.NORMAL)
            self._set_register_feedback(message, "success")
        else:
            self.register_validate_btn.state(["disabled"])
            self.register_validate_btn.configure(state=tk.DISABLED)
            self._set_register_feedback(message, tone)

        return valid

    def _handle_login(self):
        email = (self.login_email_var.get() or "").strip().lower()
        password = self.login_pass_var.get() or ""
        if not email or not password:
            self._set_status("Completa email y contrasena para ingresar.", "info")
            return

        user = self.users.verify_credentials(email, password)
        if not user:
            self._set_status("Credenciales invalidas. Revisa los datos e intenta de nuevo.", "error")
            messagebox.showerror("Login", "Credenciales invalidas.")
            return

        self._set_status("")
        self.login_pass_var.set("")
        messagebox.showinfo("Bienvenido", f"Hola {user['name']}!")
        self._open_main(user)

    def _prepare_register(self):
        if not self._validate_register_fields():
            self._set_status("Verifica los campos resaltados antes de continuar.", "info")
            return

        data = {
            "name": self.register_name_var.get().strip(),
            "email": self.register_email_var.get().strip().lower(),
            "password": self.register_pass_var.get(),
        }

        self._pending_registration = data
        self.register_confirm_btn.state(["!disabled"])
        self.register_confirm_btn.configure(state=tk.NORMAL)
        self._set_register_feedback("Datos verificados. Presiona Confirmar registro para guardar la cuenta.", "success")
        self._set_status("Datos verificados. Presiona Confirmar registro para crear la cuenta.", "info")

    def _confirm_register(self):
        if not self._pending_registration:
            self._set_status("Primero verifica los datos con el boton Verificar datos.", "info")
            return

        data = self._pending_registration
        try:
            self.users.create_user(data["name"], data["email"], data["password"])
        except sqlite3.IntegrityError:
            msg = "Ese email ya esta registrado."
            self._set_register_feedback(msg, "error")
            self._set_status(msg, "error")
            self._pending_registration = None
            self._validate_register_fields()
            return
        except Exception as exc:
            msg = f"Error creando la cuenta: {exc}"
            self._set_register_feedback(msg, "error")
            self._set_status(msg, "error")
            self._pending_registration = None
            self._validate_register_fields()
            return

        self.login_email_var.set(data["email"])
        self.login_pass_var.set("")
        self.register_pass_var.set("")
        self.register_confirm_var.set("")
        self._pending_registration = None
        self.register_confirm_btn.state(["disabled"])
        self.register_confirm_btn.configure(state=tk.DISABLED)
        self._show_form("login", reset_status=True)
        self._set_register_feedback("", "info")
        self._validate_register_fields()
        self._set_status("Cuenta creada correctamente. Inicia sesion con tus datos.", "success")
        messagebox.showinfo("Registro", "Cuenta creada. Ya puedes iniciar sesion.")

    def _submit_current(self, _event):
        if self.mode.get() == "login":
            self._handle_login()
        else:
            self._prepare_register()

    def _toggle_fullscreen(self, _event=None):
        self.is_fullscreen = not self.is_fullscreen
        try:
            self.root.attributes("-fullscreen", self.is_fullscreen)
        except tk.TclError:
            self.is_fullscreen = False

    def _end_fullscreen(self, _event=None):
        if self.is_fullscreen:
            self.is_fullscreen = False
            try:
                self.root.attributes("-fullscreen", False)
            except tk.TclError:
                pass

    def _open_main(self, user_dict):
        self.root.withdraw()
        win = tk.Toplevel()
        CCTVMonitoringSystem(win, session_user=user_dict, on_logout=self._on_logout)

        def on_main_close():
            try:
                win.destroy()
            except Exception:
                pass
            try:
                self.root.destroy()
            except Exception:
                pass

        win.protocol("WM_DELETE_WINDOW", on_main_close)

    def _on_logout(self):
        self.root.deiconify()

    def _on_close(self):
        try:
            self.root.destroy()
        except Exception:
            pass
