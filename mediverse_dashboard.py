#!/usr/bin/env python3
"""Local desktop dashboard for the Mediverse ESP32 workshop prototype.

Requires: pyserial, matplotlib
Run from the project folder: py mediverse_dashboard.py
Close Arduino Serial Monitor before connecting; one application can own a COM port at a time.
"""
from __future__ import annotations

import csv
import queue
import re
import threading
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
import tkinter as tk
import tkinter.font as tkfont
from tkinter import messagebox, ttk

import serial
from serial.tools import list_ports
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator

BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "mediverse_measurements.csv"
CSV_HEADER = ["scan_id", "measurement_type", "angle_deg", "adc_median", "adc_min", "adc_max", "n", "status"]
SENSOR_CSV_PATH = BASE_DIR / "mediverse_sensor_tests.csv"
SENSOR_CSV_HEADER = ["test_id", "timestamp", "adc_median", "adc_min", "adc_max", "n", "status"]
ADC_MAX = 4095
SENSOR_STATUS_RE = re.compile(r"[A-Z_]+")

SENSOR_RE = re.compile(r"SENSOR_TEST\s+median=(\d+)\s+min=(\d+)\s+max=(\d+)\s+n=(\d+)\s+status=([A-Z_]+)")

# --- Visual theme (cosmetic only) -------------------------------------------
BG = "#000000"            # true black, OLED friendly
PLOT_BG = "#04070b"
SURFACE = "#0a1017"
SURFACE_HI = "#111b26"
BORDER = "#16212c"
BORDER_HI = "#2a3b4d"
TEXT = "#dce6f0"
MUTED = "#718397"
FAINT = "#3a4757"
ACCENT = "#2fd8ec"
ACCENT_DIM = "#14606e"
OK = "#3ddc97"
WARN = "#ffb347"
ERR = "#ff6b6b"
REF_COLOR = "#5b8def"
SAMPLE_COLOR = "#ffb347"
LIVE_COLOR = ACCENT
FONTS = {"ui": "Helvetica", "mono": "Courier"}


def _lerp(c1: str, c2: str, t: float) -> str:
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(a, b))


class Panel(tk.Frame):
    """Outlined HUD panel: title strip, corner ticks, `.body` for content, `.tools` for header widgets."""

    def __init__(self, parent, title: str, pad=12) -> None:
        super().__init__(parent, bg=BORDER, padx=1, pady=1)
        head = tk.Frame(self, bg=SURFACE)
        head.pack(fill="x")
        tk.Frame(head, bg=ACCENT, width=3).pack(side="left", fill="y")
        tk.Label(head, text=title.upper(), bg=SURFACE, fg=MUTED,
                 font=(FONTS["mono"], 8, "bold")).pack(side="left", padx=(9, 0), pady=6)
        self.tools = tk.Frame(head, bg=SURFACE)
        self.tools.pack(side="right")
        self.body = ttk.Frame(self, padding=pad)
        self.body.pack(fill="both", expand=True)
        for anchor, relx, rely in (("nw", 0, 0), ("ne", 1, 0), ("sw", 0, 1), ("se", 1, 1)):
            tk.Frame(self, bg=ACCENT).place(relx=relx, rely=rely, anchor=anchor, width=12, height=2)
            tk.Frame(self, bg=ACCENT).place(relx=relx, rely=rely, anchor=anchor, width=2, height=12)


class HudButton(tk.Canvas):
    """Chamfered canvas button. Accepts configure(state=...) like a ttk.Button."""

    def __init__(self, parent, text: str, command=None, variant: str = "normal",
                 height: int = 36, size: int = 10, bg: str = BG) -> None:
        super().__init__(parent, height=height, bg=bg, highlightthickness=0, bd=0, takefocus=1)
        self._text, self._command, self._variant = text, command, variant
        self._state = "normal"
        self._hover = self._pressed = self._focus = False
        self._font = tkfont.Font(family=FONTS["ui"], size=size)
        pad = 16 if height > 26 else 10
        super().configure(width=self._font.measure(text) + 2 * pad, cursor="hand2")
        self.bind("<Configure>", lambda e: self._draw())
        self.bind("<Enter>", lambda e: self._set(_hover=True))
        self.bind("<Leave>", lambda e: self._set(_hover=False, _pressed=False))
        self.bind("<FocusIn>", lambda e: self._set(_focus=True))
        self.bind("<FocusOut>", lambda e: self._set(_focus=False))
        self.bind("<ButtonPress-1>", self._press)
        self.bind("<ButtonRelease-1>", self._release)
        self.bind("<space>", lambda e: self._invoke())
        self.bind("<Return>", lambda e: self._invoke())

    def configure(self, cnf=None, **kw):
        if cnf:
            kw.update(cnf)
        if "state" in kw:
            self._state = kw.pop("state")
            super().configure(cursor="" if self._state == "disabled" else "hand2")
            self._draw()
        if "variant" in kw:
            self._variant = kw.pop("variant")
            self._draw()
        if "text" in kw:
            self._text = kw.pop("text")
            self._draw()
        if kw:
            super().configure(**kw)

    config = configure

    def _set(self, **flags) -> None:
        for key, value in flags.items():
            setattr(self, key, value)
        self._draw()

    def _invoke(self) -> None:
        if self._state != "disabled" and self._command:
            self._command()

    def _press(self, _event) -> None:
        if self._state != "disabled":
            self.focus_set()
            self._set(_pressed=True)

    def _release(self, event) -> None:
        was_pressed = self._pressed
        self._set(_pressed=False)
        inside = 0 <= event.x <= self.winfo_width() and 0 <= event.y <= self.winfo_height()
        if was_pressed and inside:
            self._invoke()

    def _draw(self) -> None:
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w <= 1:
            w, h = int(self.cget("width")), int(self.cget("height"))
        disabled = self._state == "disabled"
        accent = self._variant == "accent"
        active = self._hover or self._focus or self._pressed
        if disabled:
            fill, edge, fg = BG, BORDER, FAINT
        else:
            selected = self._variant == "selected"
            fill = BORDER if self._pressed else (SURFACE_HI if (self._hover or selected) else SURFACE)
            edge = ACCENT if (active or selected) else (ACCENT_DIM if accent else BORDER_HI)
            fg = ACCENT if (accent or selected) else TEXT
        m, c = 2, (7 if h > 26 else 4)
        pts = [m + c, m, w - m, m, w - m, h - m - c, w - m - c, h - m, m, h - m, m, m + c]
        if active and not disabled:
            self.create_polygon(pts, fill="", outline=ACCENT_DIM, width=3)
        self.create_polygon(pts, fill=fill, outline=edge, width=1)
        self.create_text(w / 2, h / 2, text=self._text, fill=fg, font=self._font)


class HudSlider(tk.Canvas):
    """Tick-marked slider that drives an IntVar and calls command(value_str) like ttk.Scale."""

    PAD = 14

    def __init__(self, parent, from_: int, to: int, variable, command) -> None:
        super().__init__(parent, height=56, bg=BG, highlightthickness=0, bd=0, takefocus=1, cursor="hand2")
        self._lo, self._hi, self._var, self._command = from_, to, variable, command
        self._focus = False
        self._font = tkfont.Font(family=FONTS["mono"], size=7)
        self._var.trace_add("write", lambda *_: self._draw())
        self.bind("<Configure>", lambda e: self._draw())
        self.bind("<ButtonPress-1>", self._drag)
        self.bind("<B1-Motion>", self._drag)
        self.bind("<Left>", lambda e: self._nudge(-10))
        self.bind("<Right>", lambda e: self._nudge(10))
        self.bind("<FocusIn>", lambda e: self._set_focus(True))
        self.bind("<FocusOut>", lambda e: self._set_focus(False))

    def _set_focus(self, value: bool) -> None:
        self._focus = value
        self._draw()

    def _width(self) -> int:
        return max(self.winfo_width(), 80)

    def _x(self, value: float) -> float:
        span = self._width() - 2 * self.PAD
        return self.PAD + (value - self._lo) / (self._hi - self._lo) * span

    def _drag(self, event) -> None:
        self.focus_set()
        span = self._width() - 2 * self.PAD
        frac = min(1.0, max(0.0, (event.x - self.PAD) / span))
        value = self._lo + frac * (self._hi - self._lo)
        self._var.set(int(round(value)))
        self._command(str(value))

    def _nudge(self, delta: int) -> None:
        value = min(self._hi, max(self._lo, int(self._var.get()) + delta))
        self._var.set(value)
        self._command(str(value))

    def _draw(self) -> None:
        self.delete("all")
        w = self._width()
        try:
            value = float(self._var.get())
        except (tk.TclError, ValueError):
            value = self._lo
        x, y = self._x(value), 14
        self.create_line(self.PAD, y, w - self.PAD, y, fill=BORDER_HI, width=3)
        self.create_line(self.PAD, y, x, y, fill=ACCENT, width=3)
        for a in range(self._lo, self._hi + 1, 10):
            tx, major = self._x(a), a % 90 == 0
            color = MUTED if major else (ACCENT_DIM if a <= value else FAINT)
            self.create_line(tx, 27, tx, 36 if major else 32, fill=color)
            if major:
                self.create_text(tx, 46, text=str(a), fill=MUTED, font=self._font)
        self.create_polygon(x, y - 9, x + 9, y, x, y + 9, x - 9, y, fill="", outline=ACCENT_DIM, width=3)
        self.create_polygon(x, y - 6, x + 6, y, x, y + 6, x - 6, y,
                            fill=TEXT if self._focus else ACCENT, outline="")



class MediverseDashboard:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Mediverse | FIBROS Workshop Dashboard")
        self.root.geometry("1240x860")
        self.root.minsize(980, 680)

        self.ser: serial.Serial | None = None
        self.reader_stop = threading.Event()
        self.reader_thread: threading.Thread | None = None
        self.incoming: queue.Queue[str] = queue.Queue()
        self.measurements: dict[str, list[dict[str, object]]] = {"reference": [], "sample": []}
        self.sensor_var = tk.StringVar(value="No sensor test yet")
        self.connection_var = tk.StringVar(value="Disconnected")
        self.csv_var = tk.StringVar(value=f"Measurements save to: {CSV_PATH.name}")
        self.port_var = tk.StringVar()
        self.baud_var = tk.StringVar(value="115200")
        self.angle_var = tk.IntVar(value=90)
        self.scans_unlocked_var = tk.BooleanVar(value=False)
        # Live LDR sensor-test history (separate from reference/sample scan data).
        self.sensor_tests: list[dict[str, object]] = []
        self.next_test_id = 1
        self.live_view_start = 0  # index of the first test shown; 'Clear live view' only moves this
        self.graph_view_var = tk.StringVar(value="live")

        self._configure_style()
        self._build_ui()
        self.refresh_ports()
        self._load_existing_csv()
        self._load_sensor_csv()
        self._update_plot()
        self.root.after(100, self._poll_incoming)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def _configure_style(self) -> None:
        families = set(tkfont.families(self.root))

        def pick(names: tuple[str, ...], fallback: str) -> str:
            return next((n for n in names if n in families), fallback)

        self.ui_font = pick(("Segoe UI Variable Text", "Segoe UI", "Inter", "Cantarell", "Ubuntu", "Helvetica Neue"), "Helvetica")
        self.mono_font = pick(("JetBrains Mono", "Cascadia Mono", "Consolas", "DejaVu Sans Mono", "Menlo"), "Courier")
        FONTS["ui"], FONTS["mono"] = self.ui_font, self.mono_font
        ui, mono = self.ui_font, self.mono_font

        self.root.configure(bg=BG)
        self.root.option_add("*TCombobox*Listbox.background", SURFACE)
        self.root.option_add("*TCombobox*Listbox.foreground", TEXT)
        self.root.option_add("*TCombobox*Listbox.selectBackground", ACCENT_DIM)
        self.root.option_add("*TCombobox*Listbox.selectForeground", TEXT)
        self.root.option_add("*TCombobox*Listbox.font", (ui, 10))
        self.root.option_add("*TCombobox*Listbox.borderWidth", 0)

        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure(".", background=BG, foreground=TEXT, font=(ui, 10))
        style.configure("TFrame", background=BG)
        style.configure("TPanedwindow", background=BG)
        style.configure("Sash", sashthickness=4, gripcount=0, background=BG)
        for sep in ("TSeparator", "Horizontal.TSeparator"):
            style.configure(sep, background=BORDER_HI)

        style.configure("TLabel", background=BG, foreground=TEXT)
        style.configure("Title.TLabel", font=(ui, 21, "bold"), foreground=TEXT)
        style.configure("Sub.TLabel", font=(ui, 9), foreground=MUTED)
        style.configure("Metric.TLabel", font=(mono, 11, "bold"), foreground=ACCENT)
        style.configure("Section.TLabel", font=(ui, 10, "bold"), foreground=TEXT)
        style.configure("Value.TLabel", font=(mono, 17, "bold"), foreground=ACCENT)

        style.configure("TCombobox", fieldbackground=SURFACE, background=SURFACE, foreground=TEXT,
                        arrowcolor=MUTED, bordercolor=BORDER_HI, lightcolor=SURFACE, darkcolor=SURFACE,
                        selectbackground=SURFACE, selectforeground=TEXT, padding=4)
        style.map("TCombobox",
                  fieldbackground=[("readonly", SURFACE)],
                  selectbackground=[("readonly", SURFACE)],
                  selectforeground=[("readonly", TEXT)],
                  bordercolor=[("focus", ACCENT), ("active", ACCENT_DIM)],
                  arrowcolor=[("active", ACCENT)])

        style.configure("TCheckbutton", background=BG, foreground=TEXT,
                        indicatorbackground=SURFACE, indicatorforeground=BG,
                        upperbordercolor=BORDER_HI, lowerbordercolor=BORDER_HI, focuscolor=BG)
        style.map("TCheckbutton",
                  background=[("active", BG)],
                  indicatorbackground=[("selected", ACCENT), ("active", SURFACE_HI)],
                  upperbordercolor=[("selected", ACCENT)], lowerbordercolor=[("selected", ACCENT)])

        # Slim, arrow-less scrollbar.
        style.layout("Vertical.TScrollbar", [("Vertical.Scrollbar.trough", {
            "sticky": "ns", "children": [("Vertical.Scrollbar.thumb", {"expand": "1", "sticky": "nswe"})]})])
        style.configure("Vertical.TScrollbar", background=BORDER_HI, troughcolor=PLOT_BG, bordercolor=PLOT_BG,
                        lightcolor=BORDER_HI, darkcolor=BORDER_HI, arrowsize=9, gripcount=0)
        style.map("Vertical.TScrollbar", background=[("active", ACCENT_DIM)],
                  lightcolor=[("active", ACCENT_DIM)], darkcolor=[("active", ACCENT_DIM)])

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root, padding=(18, 10, 18, 8))
        outer.pack(fill="both", expand=True)

        # Header: emblem + title stack on the left, live status chip on the right.
        header = ttk.Frame(outer)
        header.pack(fill="x", pady=(0, 6))
        logo = tk.Canvas(header, width=42, height=42, bg=BG, highlightthickness=0)
        logo.pack(side="left", padx=(0, 12))
        logo.create_polygon(21, 2, 40, 21, 21, 40, 2, 21, outline=ACCENT, fill="", width=2)
        logo.create_polygon(21, 12, 30, 21, 21, 30, 12, 21, fill=ACCENT, outline="")
        titles = ttk.Frame(header)
        titles.pack(side="left")
        ttk.Label(titles, text="MEDIVERSE", style="Title.TLabel").pack(anchor="w")
        ttk.Label(titles, text="FIBROS optical measurement prototype · Local workstation", style="Sub.TLabel").pack(anchor="w")

        chip = tk.Frame(header, bg=BORDER_HI, padx=1, pady=1)
        chip.pack(side="right", padx=4)
        chip_inner = tk.Frame(chip, bg=SURFACE)
        chip_inner.pack()
        self.led = tk.Canvas(chip_inner, width=12, height=12, bg=SURFACE, highlightthickness=0)
        self.led.pack(side="left", padx=(14, 7), pady=9)
        self.led_dot = self.led.create_oval(2, 2, 10, 10, fill=FAINT, outline="")
        self.status_label = tk.Label(chip_inner, textvariable=self.connection_var, bg=SURFACE, fg=MUTED,
                                     font=(self.ui_font, 10, "bold"))
        self.status_label.pack(side="left", padx=(0, 16))
        self._led_bright = True
        self.connection_var.trace_add("write", self._on_connection_change)
        self._on_connection_change()
        self.root.after(700, self._pulse_led)

        rule = tk.Canvas(outer, height=2, bg=BG, highlightthickness=0)
        rule.pack(fill="x", pady=(0, 10))
        rule.bind("<Configure>", lambda e: self._draw_rule(rule, e.width))

        # Connection strip: everything on one line.
        connect_panel = Panel(outer, "ESP32 serial connection", pad=(12, 10))
        connect_panel.pack(fill="x", pady=(0, 10))
        connect = connect_panel.body
        ttk.Label(connect, text="Port").grid(row=0, column=0, padx=(0, 6), sticky="w")
        self.port_combo = ttk.Combobox(connect, textvariable=self.port_var, width=16, state="readonly")
        self.port_combo.grid(row=0, column=1, padx=(0, 8), sticky="w")
        HudButton(connect, "Refresh ports", self.refresh_ports, height=30).grid(row=0, column=2, padx=(0, 16))
        ttk.Label(connect, text="Baud").grid(row=0, column=3, padx=(0, 6), sticky="w")
        ttk.Combobox(connect, textvariable=self.baud_var, values=["115200"], width=10, state="readonly").grid(row=0, column=4, padx=(0, 16), sticky="w")
        self.connect_button = HudButton(connect, "Connect", self.connect, variant="accent", height=30)
        self.connect_button.grid(row=0, column=5, padx=(0, 6))
        self.disconnect_button = HudButton(connect, "Disconnect", self.disconnect, height=30)
        self.disconnect_button.configure(state="disabled")
        self.disconnect_button.grid(row=0, column=6)
        ttk.Label(connect, text="Close Arduino Serial Monitor before connecting here.", style="Sub.TLabel").grid(row=0, column=7, sticky="e", padx=(16, 0))
        connect.columnconfigure(7, weight=1)

        # Bottom bar (packed first so it always keeps its space): saved-data info + disclaimer.
        footer = ttk.Frame(outer)
        footer.pack(side="bottom", fill="x", pady=(8, 0))
        ttk.Separator(footer).pack(fill="x", pady=(0, 8))
        ttk.Label(footer, text="Saved data", style="Section.TLabel").pack(side="left")
        ttk.Label(footer, textvariable=self.csv_var, style="Sub.TLabel").pack(side="left", padx=(10, 10))
        HudButton(footer, "Open data folder", self.open_data_folder, height=24, size=9).pack(side="left")
        ttk.Label(footer, text="Research/teaching demonstration only — optical response is not a diagnosis of fibrosis.", style="Sub.TLabel").pack(side="right")

        body = ttk.Panedwindow(outer, orient="horizontal")
        body.pack(fill="both", expand=True)
        left = ttk.Frame(body, padding=(0, 0, 12, 0))
        right = ttk.Frame(body)
        body.add(left, weight=0)
        body.add(right, weight=1)

        commands_panel = Panel(left, "Hardware controls")
        commands_panel.pack(fill="x", pady=(0, 10))
        commands = commands_panel.body
        ttk.Label(commands, text="Sensor & LED", style="Section.TLabel").pack(anchor="w", pady=(0, 8))
        row = ttk.Frame(commands)
        row.pack(fill="x")
        self._button(row, "Test sensor (T)", lambda: self.send_command("T")).pack(side="left", fill="x", expand=True, padx=(0, 4))
        self._button(row, "LED on (L)", lambda: self.send_command("L")).pack(side="left", fill="x", expand=True, padx=4)
        self._button(row, "LED off (X)", lambda: self.send_command("X")).pack(side="left", fill="x", expand=True, padx=(4, 0))
        ttk.Label(commands, text="Latest LDR test", style="Sub.TLabel").pack(anchor="w", pady=(10, 4))
        readout = tk.Frame(commands, bg=BORDER_HI, padx=1, pady=1)
        readout.pack(fill="x")
        readout_inner = tk.Frame(readout, bg=PLOT_BG)
        readout_inner.pack(fill="x")
        tk.Frame(readout_inner, bg=ACCENT, width=3).pack(side="left", fill="y")
        sensor_label = ttk.Label(readout_inner, textvariable=self.sensor_var, wraplength=330, style="Metric.TLabel", padding=(12, 10))
        sensor_label.configure(background=PLOT_BG)
        sensor_label.pack(side="left", anchor="w")

        ttk.Separator(commands).pack(fill="x", pady=10)
        servo_head = ttk.Frame(commands)
        servo_head.pack(fill="x")
        ttk.Label(servo_head, text="Servo positioning", style="Section.TLabel").pack(side="left")
        self.angle_label = ttk.Label(servo_head, text="90°", width=5, anchor="e", style="Value.TLabel")
        self.angle_label.pack(side="right")
        HudSlider(commands, 0, 180, self.angle_var, self._on_angle_scale).pack(fill="x", pady=(2, 4))
        self._button(commands, "Send position J…", self.send_angle).pack(fill="x", pady=(2, 0))
        ttk.Label(commands, text="Position is a command, not measured angle feedback.", wraplength=330, style="Sub.TLabel").pack(anchor="w", pady=(6, 0))

        scans_panel = Panel(left, "Measurement scans")
        scans_panel.pack(fill="x")
        scans = scans_panel.body
        ttk.Label(scans, text="Scans remain locked until the physical servo travel and optical zero are verified and the firmware flags are updated.", wraplength=330).pack(anchor="w", pady=(0, 10))
        ttk.Checkbutton(scans, text="I have verified both and updated firmware flags", variable=self.scans_unlocked_var, command=self._update_scan_buttons).pack(anchor="w", pady=(0, 10))
        scan_row = ttk.Frame(scans)
        scan_row.pack(fill="x")
        self.reference_button = self._button(scan_row, "Reference scan (R)", lambda: self._request_scan("R"))
        self.reference_button.configure(state="disabled")
        self.reference_button.pack(side="left", fill="x", expand=True, padx=(0, 4))
        self.sample_button = self._button(scan_row, "Sample scan (S)", lambda: self._request_scan("S"))
        self.sample_button.configure(state="disabled")
        self.sample_button.pack(side="left", fill="x", expand=True, padx=(4, 0))

        plot_panel = Panel(right, "Measurement curves", pad=8)
        plot_panel.pack(fill="both", expand=True, pady=(0, 10))
        self.view_live_button = HudButton(plot_panel.tools, "Live LDR", lambda: self._set_graph_view("live"),
                                          height=22, size=8, bg=SURFACE)
        self.view_live_button.pack(side="left", padx=(0, 4), pady=3)
        self.view_scan_button = HudButton(plot_panel.tools, "Scan curves", lambda: self._set_graph_view("scan"),
                                          height=22, size=8, bg=SURFACE)
        self.view_scan_button.pack(side="left", padx=(0, 4), pady=3)
        self.clear_view_button = HudButton(plot_panel.tools, "Clear live view", self.clear_live_view,
                                           height=22, size=8, bg=SURFACE)
        self.clear_view_button.pack(side="left", padx=(12, 6), pady=3)
        self._refresh_view_buttons()
        plot_frame = plot_panel.body
        self.figure = Figure(figsize=(7.2, 3.8), dpi=100, constrained_layout=True, facecolor=BG)
        self.ax = self.figure.add_subplot(111)
        self._draw_empty_plot()
        self.canvas = FigureCanvasTkAgg(self.figure, master=plot_frame)
        self.canvas.get_tk_widget().configure(bg=BG, highlightthickness=0)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        console_panel = Panel(right, "Serial console", pad=8)
        console_panel.pack(fill="both", expand=True)
        HudButton(console_panel.tools, "Clear console", self.clear_console, height=22, size=8, bg=SURFACE).pack(padx=6, pady=3)
        console_frame = console_panel.body
        self.console = tk.Text(console_frame, height=12, wrap="word", font=(self.mono_font, 9), state="disabled",
                               bg=PLOT_BG, fg=TEXT, insertbackground=ACCENT, selectbackground=ACCENT_DIM,
                               selectforeground=TEXT, relief="flat", borderwidth=0, highlightthickness=0,
                               padx=10, pady=8, spacing1=1, spacing3=1)
        for tag, color in (("rx", TEXT), ("tx", ACCENT), ("sys", MUTED), ("warn", WARN), ("err", ERR)):
            self.console.tag_configure(tag, foreground=color)
        scrollbar = ttk.Scrollbar(console_frame, orient="vertical", command=self.console.yview)
        self.console.configure(yscrollcommand=scrollbar.set)
        self.console.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y", padx=(4, 0))

    @staticmethod
    def _button(parent: ttk.Frame, label: str, command) -> HudButton:
        return HudButton(parent, label, command)

    def _draw_empty_plot(self) -> None:
        self.ax.clear()
        self.ax.set_title("LDR response versus commanded polarizer angle")
        self.ax.set_xlabel("Commanded angle (degrees)")
        self.ax.set_ylabel("Raw ADC counts (0–4095)")
        self.ax.set_xticks(list(range(0, 181, 10)))
        self.ax.set_xlim(0, 180)
        self.ax.set_ylim(0, 4095)
        self.ax.grid(True, alpha=0.25)
        self._style_axes()
        self.canvas.draw_idle() if hasattr(self, "canvas") else None

    def _paint_led(self) -> None:
        if self.connection_var.get().startswith("Connected"):
            color = OK if self._led_bright else _lerp(OK, SURFACE, 0.65)
        else:
            color = FAINT
        self.led.itemconfigure(self.led_dot, fill=color)

    def _on_connection_change(self, *_args) -> None:
        connected = self.connection_var.get().startswith("Connected")
        self.status_label.configure(fg=OK if connected else MUTED)
        self._paint_led()

    def _pulse_led(self) -> None:
        self._led_bright = not self._led_bright
        self._paint_led()
        self.root.after(700, self._pulse_led)

    @staticmethod
    def _draw_rule(canvas: tk.Canvas, width: int) -> None:
        canvas.delete("all")
        steps = 56
        for i in range(steps):
            color = _lerp(ACCENT, BG, (i / steps) ** 0.55)
            canvas.create_rectangle(width * i / steps, 0, width * (i + 1) / steps + 1, 2, fill=color, outline="")

    def _style_axes(self) -> None:
        ax = self.ax
        title = ax.get_title()
        ax.set_title("")
        ax.set_title(title, loc="left", color=TEXT, fontsize=11, fontweight="bold", pad=12)
        ax.set_facecolor(PLOT_BG)
        ax.xaxis.label.set_color(MUTED)
        ax.yaxis.label.set_color(MUTED)
        ax.xaxis.label.set_fontsize(9)
        ax.yaxis.label.set_fontsize(9)
        ax.tick_params(colors=MUTED, labelsize=8, length=3, color=BORDER_HI)
        try:
            ax.tick_params(labelfontfamily="DejaVu Sans Mono")
        except (TypeError, ValueError):
            for tick_label in ax.get_xticklabels() + ax.get_yticklabels():
                tick_label.set_fontfamily("DejaVu Sans Mono")
        for name, spine in ax.spines.items():
            spine.set_color(BORDER_HI)
            if name in ("top", "right"):
                spine.set_visible(False)
        ax.grid(True, color=BORDER_HI, alpha=0.55, linewidth=0.7, linestyle=(0, (1, 3)))
        ax.set_axisbelow(True)

    def refresh_ports(self) -> None:
        ports = list(list_ports.comports())
        values = [p.device for p in ports]
        self.port_combo["values"] = values
        if self.port_var.get() not in values:
            self.port_var.set(values[0] if values else "")
        if not values:
            self._append_console("[dashboard] No serial ports detected. Plug in the ESP32 and refresh.")

    def connect(self) -> None:
        if self.ser is not None:
            return
        port = self.port_var.get().strip()
        if not port:
            messagebox.showwarning("No port selected", "Select the ESP32 COM port first.")
            return
        try:
            ser = serial.Serial(port, int(self.baud_var.get()), timeout=0.2, write_timeout=0.5)
        except (serial.SerialException, ValueError) as exc:
            messagebox.showerror("Connection failed", f"Could not open {port}.\n\n{exc}\n\nClose Arduino Serial Monitor if it is open.")
            return
        self.ser = ser
        self.reader_stop.clear()
        self.reader_thread = threading.Thread(target=self._serial_reader, args=(ser,), daemon=True)
        self.reader_thread.start()
        self.connection_var.set(f"Connected · {port}")
        self.connect_button.configure(state="disabled")
        self.disconnect_button.configure(state="normal")
        self._append_console(f"[dashboard] Connected to {port} at {self.baud_var.get()} baud.")
        self._append_console("[dashboard] ESP32 may reset when the port opens; wait for its boot/help text.")

    def _serial_reader(self, ser: serial.Serial) -> None:
        # Opening many ESP32 serial ports resets the board; allow output to arrive naturally.
        while not self.reader_stop.is_set():
            try:
                raw = ser.readline()
            except (serial.SerialException, OSError) as exc:
                self.incoming.put(f"__ERROR__{exc}")
                break
            if raw:
                self.incoming.put(raw.decode("utf-8", errors="replace").strip())

    def disconnect(self) -> None:
        self.reader_stop.set()
        ser, self.ser = self.ser, None
        if ser is not None:
            try:
                ser.close()
            except (serial.SerialException, OSError):
                pass
        self.connection_var.set("Disconnected")
        self.connect_button.configure(state="normal")
        self.disconnect_button.configure(state="disabled")
        self._append_console("[dashboard] Disconnected.")

    def send_command(self, command: str) -> None:
        if self.ser is None or not self.ser.is_open:
            messagebox.showinfo("Not connected", "Connect to the ESP32 first.")
            return
        try:
            self.ser.write((command.strip() + "\n").encode("ascii"))
            self._append_console(f"> {command}")
        except (serial.SerialException, OSError) as exc:
            messagebox.showerror("Send failed", str(exc))

    def _on_angle_scale(self, value: str) -> None:
        angle = int(round(float(value) / 10) * 10)
        angle = max(0, min(180, angle))
        self.angle_var.set(angle)
        self.angle_label.configure(text=f"{angle}°")

    def send_angle(self) -> None:
        self.send_command(f"J{self.angle_var.get()}")

    def _update_scan_buttons(self) -> None:
        # The firmware independently blocks scans unless its calibration constants are true.
        state = "normal" if self.scans_unlocked_var.get() and self.ser is not None else "disabled"
        self.reference_button.configure(state=state)
        self.sample_button.configure(state=state)

    def _request_scan(self, command: str) -> None:
        if not self.scans_unlocked_var.get():
            return
        warning = ("Only proceed after an organiser/supervisor has verified safe servo travel and optical zero, "
                   "and the firmware constants SERVO_RANGE_VERIFIED and OPTICAL_ZERO_VERIFIED are both true.\n\n"
                   "Proceed to send the scan command?")
        if messagebox.askyesno("Confirm physical calibration", warning):
            self.send_command(command)

    def _poll_incoming(self) -> None:
        processed = False
        while True:
            try:
                line = self.incoming.get_nowait()
            except queue.Empty:
                break
            processed = True
            if line.startswith("__ERROR__"):
                self._append_console("[serial error] " + line[len("__ERROR__"):])
                self.disconnect()
                continue
            if line:
                self._append_console(line)
                self._parse_line(line)
        if processed:
            self._update_scan_buttons()
        self.root.after(100, self._poll_incoming)

    def _parse_line(self, line: str) -> None:
        match = SENSOR_RE.search(line)
        if match:
            median, minimum, maximum, n = map(int, match.groups()[:4])
            status = match.group(5)
            if not self._valid_sensor_values(median, minimum, maximum, n, status):
                self._append_console("[dashboard] Ignored SENSOR_TEST line with out-of-range values; not plotted or saved.")
                return
            self.sensor_var.set(f"Median {median} · min {minimum} · max {maximum}\nn={n} · {status}")
            self._record_sensor_test(median, minimum, maximum, n, status)
            return
        if line.startswith("# SCAN BLOCKED"):
            self._append_console("[safety] Firmware has kept scans locked. Do not bypass the firmware check.")
            return
        try:
            row = next(csv.reader([line]))
        except csv.Error:
            return
        if len(row) != 8:
            return
        try:
            scan_id = int(row[0]); kind = row[1].strip().lower(); angle = int(row[2])
            median = int(row[3]); minimum = int(row[4]); maximum = int(row[5]); n = int(row[6])
        except (ValueError, TypeError):
            return
        status = row[7].strip().upper()
        if kind not in {"reference", "sample"} or angle not in range(0, 181, 10) or n <= 0:
            return
        measurement = {"scan_id": scan_id, "measurement_type": kind, "angle_deg": angle,
                       "adc_median": median, "adc_min": minimum, "adc_max": maximum, "n": n, "status": status}
        self.measurements[kind].append(measurement)
        try:
            needs_header = not CSV_PATH.exists() or CSV_PATH.stat().st_size == 0
            with CSV_PATH.open("a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=CSV_HEADER)
                if needs_header:
                    writer.writeheader()
                writer.writerow(measurement)
        except OSError as exc:
            self._append_console(f"[save error] Could not write CSV: {exc}")
        self.csv_var.set(f"Saved measurement rows to: {CSV_PATH.name}")
        self._update_plot()

    def _load_existing_csv(self) -> None:
        if not CSV_PATH.exists():
            return
        try:
            with CSV_PATH.open("r", newline="", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        kind = row["measurement_type"].strip().lower()
                        if kind not in self.measurements:
                            continue
                        measurement = {"scan_id": int(row["scan_id"]), "measurement_type": kind,
                                       "angle_deg": int(row["angle_deg"]), "adc_median": int(row["adc_median"]),
                                       "adc_min": int(row["adc_min"]), "adc_max": int(row["adc_max"]),
                                       "n": int(row["n"]), "status": row["status"].strip().upper()}
                        self.measurements[kind].append(measurement)
                    except (ValueError, TypeError, KeyError, AttributeError):
                        continue
            self._update_plot()
            self.csv_var.set(f"Loaded/saving: {CSV_PATH.name}")
        except OSError as exc:
            self._append_console(f"[load error] Could not load existing CSV: {exc}")

    @staticmethod
    def _valid_sensor_values(median: int, minimum: int, maximum: int, n: int, status: str) -> bool:
        return (0 <= minimum <= median <= maximum <= ADC_MAX
                and 0 < n <= 100_000
                and SENSOR_STATUS_RE.fullmatch(status) is not None)

    def _record_sensor_test(self, median: int, minimum: int, maximum: int, n: int, status: str) -> None:
        reading = {"test_id": self.next_test_id, "timestamp": datetime.now().isoformat(timespec="seconds"),
                   "adc_median": median, "adc_min": minimum, "adc_max": maximum, "n": n, "status": status}
        self.next_test_id += 1
        self.sensor_tests.append(reading)
        try:
            needs_header = not SENSOR_CSV_PATH.exists() or SENSOR_CSV_PATH.stat().st_size == 0
            with SENSOR_CSV_PATH.open("a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=SENSOR_CSV_HEADER)
                if needs_header:
                    writer.writeheader()
                writer.writerow(reading)
            self.csv_var.set(f"Saved sensor test {reading['test_id']} to: {SENSOR_CSV_PATH.name}")
        except OSError as exc:
            self._append_console(f"[save error] Could not write sensor-test CSV: {exc}")
        if self.graph_view_var.get() == "live":
            self._update_plot()

    def _load_sensor_csv(self) -> None:
        if not SENSOR_CSV_PATH.exists():
            return
        skipped = 0
        try:
            with SENSOR_CSV_PATH.open("r", newline="", encoding="utf-8-sig") as f:
                for row in csv.DictReader(f):
                    try:
                        test_id = int(row["test_id"])
                        median, minimum, maximum = int(row["adc_median"]), int(row["adc_min"]), int(row["adc_max"])
                        n = int(row["n"])
                        status = row["status"].strip().upper()
                        timestamp = (row.get("timestamp") or "").strip()
                    except (ValueError, TypeError, KeyError, AttributeError):
                        skipped += 1
                        continue
                    if test_id < 1 or not self._valid_sensor_values(median, minimum, maximum, n, status):
                        skipped += 1
                        continue
                    self.sensor_tests.append({"test_id": test_id, "timestamp": timestamp, "adc_median": median,
                                              "adc_min": minimum, "adc_max": maximum, "n": n, "status": status})
        except (OSError, csv.Error, UnicodeDecodeError) as exc:
            self._append_console(f"[load error] Could not fully load sensor-test CSV: {exc}")
        self.sensor_tests.sort(key=lambda r: int(r["test_id"]))
        if self.sensor_tests:
            self.next_test_id = int(self.sensor_tests[-1]["test_id"]) + 1
        if skipped:
            self._append_console(f"[dashboard] Skipped {skipped} invalid row(s) in {SENSOR_CSV_PATH.name}.")

    def _set_graph_view(self, view: str) -> None:
        self.graph_view_var.set(view)
        self._refresh_view_buttons()
        self._update_plot()

    def _refresh_view_buttons(self) -> None:
        live = self.graph_view_var.get() == "live"
        self.view_live_button.configure(variant="selected" if live else "normal")
        self.view_scan_button.configure(variant="normal" if live else "selected")
        self.clear_view_button.configure(state="normal" if live else "disabled")

    def clear_live_view(self) -> None:
        """Hide earlier tests from the live graph only; nothing is deleted from disk."""
        self.live_view_start = len(self.sensor_tests)
        self._append_console(f"[dashboard] Live graph view cleared. Saved records in {SENSOR_CSV_PATH.name} were kept; "
                             "restarting the dashboard reloads the full history.")
        self._update_plot()

    def _update_plot(self) -> None:
        if self.graph_view_var.get() == "live":
            self._plot_live_ldr()
        else:
            self._plot_scan_curves()

    def _plot_live_ldr(self) -> None:
        ax = self.ax
        ax.clear()
        rows = self.sensor_tests[self.live_view_start:]
        ax.set_title("Live LDR response: median ADC per sensor test")
        ax.set_xlabel("Sensor test number")
        ax.set_ylabel("Raw ADC counts (0–4095)")
        ax.set_ylim(0, ADC_MAX)
        ax.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=12))
        if rows:
            ids = [int(r["test_id"]) for r in rows]
            meds = [int(r["adc_median"]) for r in rows]
            mins = [int(r["adc_min"]) for r in rows]
            maxs = [int(r["adc_max"]) for r in rows]
            ax.set_xlim(ids[0] - 0.5, max(ids[-1] + 0.5, ids[0] + 4.5))
            ax.vlines(ids, mins, maxs, color=LIVE_COLOR, alpha=0.55, linewidth=2.5, label="Min–max range")
            if len(ids) > 1:
                ax.fill_between(ids, mins, maxs, color=LIVE_COLOR, alpha=0.08, linewidth=0)
            for glow_width, glow_alpha in ((9, 0.05), (5, 0.12)):
                ax.plot(ids, meds, linewidth=glow_width, color=LIVE_COLOR, alpha=glow_alpha, solid_capstyle="round")
            ax.plot(ids, meds, marker="o", markersize=5, markerfacecolor=PLOT_BG, markeredgewidth=1.6,
                    linewidth=2.0, color=LIVE_COLOR, label="Median ADC")
            for status in sorted({str(r["status"]) for r in rows} - {"OK"}):
                flagged = [r for r in rows if r["status"] == status]
                ax.scatter([int(r["test_id"]) for r in flagged], [int(r["adc_median"]) for r in flagged],
                           marker="D", s=58, color=ERR if status == "SAT_HIGH" else WARN,
                           edgecolors=TEXT, linewidths=0.8, zorder=5, clip_on=False, label=f"Status {status}")
            self._style_axes()
            ax.legend(facecolor=SURFACE, edgecolor=BORDER_HI, labelcolor=TEXT, framealpha=0.95)
        else:
            ax.set_xlim(0.5, 5.5)
            self._style_axes()
            ax.text(0.5, 0.5, "No sensor-test readings yet. Connect the ESP32 and run Test sensor (T).",
                    transform=ax.transAxes, ha="center", va="center", color=MUTED)
        self.canvas.draw_idle()

    def _plot_scan_curves(self) -> None:
        self.ax.clear()
        colors = {"reference": REF_COLOR, "sample": SAMPLE_COLOR}
        labels = {"reference": "Reference (no sample)", "sample": "Sample inserted"}
        plotted = False
        for kind in ("reference", "sample"):
            valid = [r for r in self.measurements[kind] if r["status"] == "OK"]
            by_angle: dict[int, list[int]] = defaultdict(list)
            for row in valid:
                by_angle[int(row["angle_deg"])].append(int(row["adc_median"]))
            if by_angle:
                xs = sorted(by_angle)
                ys = [sum(by_angle[x]) / len(by_angle[x]) for x in xs]
                for glow_width, glow_alpha in ((9, 0.05), (5, 0.12)):
                    self.ax.plot(xs, ys, linewidth=glow_width, color=colors[kind], alpha=glow_alpha, solid_capstyle="round")
                self.ax.fill_between(xs, ys, 0, color=colors[kind], alpha=0.05, linewidth=0)
                self.ax.plot(xs, ys, marker="o", markersize=5, markerfacecolor=PLOT_BG, markeredgewidth=1.6,
                             linewidth=2.0, color=colors[kind], label=labels[kind])
                plotted = True
        self.ax.set_title("LDR response versus commanded polarizer angle")
        self.ax.set_xlabel("Commanded angle (degrees)")
        self.ax.set_ylabel("Raw ADC counts (0–4095)")
        self.ax.set_xticks(list(range(0, 181, 10)))
        self.ax.set_xlim(0, 180)
        self.ax.set_ylim(0, 4095)
        self.ax.grid(True, alpha=0.25)
        self._style_axes()
        if plotted:
            self.ax.legend(facecolor=SURFACE, edgecolor=BORDER_HI, labelcolor=TEXT, framealpha=0.95)
        else:
            self.ax.text(0.5, 0.5, "No valid reference/sample scan data yet", transform=self.ax.transAxes,
                         ha="center", va="center", color=MUTED)
        self.canvas.draw_idle()

    def _append_console(self, text: str) -> None:
        if not hasattr(self, "console"):
            return
        self.console.configure(state="normal")
        self.console.insert("end", text + "\n", self._console_tag(text))
        # Keep the console bounded during long sessions.
        lines = int(self.console.index("end-1c").split(".")[0])
        if lines > 700:
            self.console.delete("1.0", "150.0")
        self.console.see("end")
        self.console.configure(state="disabled")

    @staticmethod
    def _console_tag(text: str) -> str:
        if text.startswith(("[serial error]", "[save error]", "[load error]")):
            return "err"
        if text.startswith("[safety]") or text.startswith("# SCAN BLOCKED"):
            return "warn"
        if text.startswith("> "):
            return "tx"
        if "SENSOR_TEST" in text:
            return "rx"
        if text.startswith(("[dashboard]", "#")):
            return "sys"
        return "rx"

    def clear_console(self) -> None:
        self.console.configure(state="normal")
        self.console.delete("1.0", "end")
        self.console.configure(state="disabled")

    def open_data_folder(self) -> None:
        try:
            import os
            os.startfile(str(BASE_DIR))
        except (AttributeError, OSError) as exc:
            messagebox.showerror("Open folder failed", str(exc))

    def close(self) -> None:
        self.disconnect()
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    MediverseDashboard(root)
    root.mainloop()


if __name__ == "__main__":
    main()