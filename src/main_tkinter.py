from __future__ import annotations

import os
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from randomizer_engine import RandomizerOptions, preview_items_from_file, process_file

APP_TITLE = "Prompt Chaos Randomizer – fallback GUI – v1.0.12 – 2026-05-11"
QUICK_GUIDE_TEXT = 'Prompt Chaos Randomizer – Quick Guide\n\nPurpose\n- Creates plain TXT wildcard lists for Stable Diffusion Forge / AUTOMATIC1111.\n- The output is always a .txt file, even when the input is a .csv file.\n- The original file is never overwritten. New files are saved beside the source as: originalname_changed_[date-time].txt\n\nProcessing presets\n- Chaos randomizer: balances periods, splits lines at period boundaries into halves/quarters/mixed chunks, then recombines chunks into new wildcard lines.\n- Sentence splitter cleanup: turns every dot-ended sentence or sentence fragment into its own wildcard line, removes duplicate lines, merges very short fragments, and extends leftover short lines with the matching phrase.\n\nSource modes\n- TXT mode: reads each source line.\n- CSV prompt mode: extracts only column 2 / prompt and writes TXT wildcard lines.\n- CSV negative prompt mode: extracts only column 3 / negative prompt and writes TXT wildcard lines.\n- CSV names, headers and other columns are not written to the output.\n\nSentence splitter cleanup\n- Splits every line so each output line contains one sentence/sentence fragment ending with a dot.\n- If a source line has no dot, a dot is appended first.\n- Duplicate output lines are removed.\n- Short lines below the selected minimum length are combined with other short lines when possible.\n- If a short leftover cannot be paired cleanly, the matching positive/TXT or negative prompt phrase is appended.\n\nChaos mixer\n- Shuffle style controls how aggressively text chunks are mixed.\n- Segment split chooses classic halves, quarters, or mixed halves + quarters.\n- Output amount can create up to 2x as many wildcard lines.\n- Chaos passes repeats the mutation process.\n\nUpdates\nNewer versions may be available in the repositories at github.com/zeittresor.'


class PromptChaosTk(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1120x780")
        self.minsize(980, 680)
        self.selected_path: Path | None = None
        self.last_output_path: Path | None = None
        self._setup_state()
        self._style()
        self._build()

    def _setup_state(self) -> None:
        self.mode_var = tk.StringVar(value="txt")
        self.preset_var = tk.StringVar(value="chaos")
        self.shuffle_var = tk.StringVar(value="all_halves")
        self.segment_var = tk.StringVar(value="halves")
        self.output_factor_var = tk.StringVar(value="1")
        self.min_sentence_chars_var = tk.IntVar(value=24)
        self.placement_var = tk.StringVar(value="random")
        self.header_var = tk.StringVar(value="auto")
        self.delimiter_var = tk.StringVar(value="auto")
        self.positive_suffix_var = tk.StringVar(value="anything is matching well.")
        self.negative_suffix_var = tk.StringVar(value="worse looking.")
        self.avoid_same_var = tk.BooleanVar(value=True)
        self.keep_blanks_var = tk.BooleanVar(value=True)
        self.normalize_spaces_var = tk.BooleanVar(value=True)
        self.use_seed_var = tk.BooleanVar(value=False)
        self.seed_var = tk.IntVar(value=12345)
        self.passes_var = tk.IntVar(value=1)
        self.path_var = tk.StringVar(value="No file selected")

    def _style(self) -> None:
        self.configure(bg="#10131c")
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        self.option_add("*TCombobox*Listbox.background", "#0f1422")
        self.option_add("*TCombobox*Listbox.foreground", "#eef3ff")
        self.option_add("*TCombobox*Listbox.selectBackground", "#5964ff")
        self.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")
        self.option_add("*TCombobox*Listbox.font", "Segoe UI 10")

        style.configure("TFrame", background="#10131c")
        style.configure("Card.TFrame", background="#141926", relief="flat")
        style.configure("TLabel", background="#10131c", foreground="#e9eefc", font=("Segoe UI", 10))
        style.configure("Muted.TLabel", background="#10131c", foreground="#aab7de", font=("Segoe UI", 9))
        style.configure("Hero.TLabel", background="#10131c", foreground="#ffffff", font=("Segoe UI", 25, "bold"))
        style.configure("Sub.TLabel", background="#10131c", foreground="#cbd6ff", font=("Segoe UI", 10))
        style.configure("TButton", background="#1b2238", foreground="#f5f7ff", bordercolor="#3a456e", focusthickness=0, padding=8, font=("Segoe UI", 10, "bold"))
        style.map("TButton", background=[("active", "#273257")])
        style.configure("Accent.TButton", background="#5964ff", foreground="#ffffff", padding=10, font=("Segoe UI", 10, "bold"))
        style.map("Accent.TButton", background=[("active", "#2de3bd")])

        style.configure(
            "Readable.TCombobox",
            fieldbackground="#0f1422",
            background="#0f1422",
            foreground="#eef3ff",
            arrowcolor="#e9eefc",
            bordercolor="#3a456e",
            lightcolor="#0f1422",
            darkcolor="#0f1422",
            padding=4,
            arrowsize=16,
        )
        style.map(
            "Readable.TCombobox",
            fieldbackground=[("readonly", "#0f1422"), ("disabled", "#1a2031")],
            background=[("readonly", "#0f1422"), ("active", "#151d30")],
            foreground=[("readonly", "#eef3ff"), ("disabled", "#8f9cc0")],
            selectbackground=[("readonly", "#5964ff")],
            selectforeground=[("readonly", "#ffffff")],
            arrowcolor=[("readonly", "#eef3ff"), ("active", "#ffffff")],
            bordercolor=[("focus", "#5964ff")],
            lightcolor=[("readonly", "#0f1422")],
            darkcolor=[("readonly", "#0f1422")],
        )

        style.configure("TCheckbutton", background="#141926", foreground="#dde5ff", font=("Segoe UI", 10))
        style.configure("TSpinbox", fieldbackground="#0f1422", background="#0f1422", foreground="#eef3ff")
        style.configure("TLabelframe", background="#141926", foreground="#b8c6ff", bordercolor="#2d3556")
        style.configure("TLabelframe.Label", background="#141926", foreground="#b8c6ff", font=("Segoe UI", 10, "bold"))

    def _build(self) -> None:
        root = ttk.Frame(self, padding=20)
        root.pack(fill="both", expand=True)

        ttk.Label(root, text="Prompt Chaos Randomizer", style="Hero.TLabel").pack(anchor="w", pady=(0, 14))

        file_frame = ttk.Frame(root)
        file_frame.pack(fill="x", pady=(0, 12))
        ttk.Button(file_frame, text="Choose .txt / .csv", command=self.choose_file).pack(side="left")
        self.path_label = tk.Label(file_frame, textvariable=self.path_var, bg="#151a28", fg="#c9d3f2", anchor="w", padx=12, pady=9)
        self.path_label.pack(side="left", fill="x", expand=True, padx=10)
        ttk.Button(file_frame, text="Preview", command=self.preview).pack(side="left", padx=(0, 8))
        ttk.Button(file_frame, text="Randomize + Save", style="Accent.TButton", command=self.randomize_save).pack(side="left", padx=(0, 8))
        self.open_button = ttk.Button(file_frame, text="Open Output Folder", command=self.open_output_folder, state="disabled")
        self.open_button.pack(side="left")

        content = ttk.Frame(root)
        content.pack(fill="both", expand=True)

        left_shell = ttk.Frame(content)
        left_shell.pack(side="left", fill="y", padx=(0, 14))
        self.left_canvas = tk.Canvas(left_shell, bg="#10131c", highlightthickness=0, bd=0, width=430)
        left_scrollbar = ttk.Scrollbar(left_shell, orient="vertical", command=self.left_canvas.yview)
        self.left_canvas.configure(yscrollcommand=left_scrollbar.set)
        self.left_canvas.pack(side="left", fill="y", expand=False)
        left_scrollbar.pack(side="left", fill="y")

        self.left_panel = ttk.Frame(self.left_canvas)
        self.left_canvas_window = self.left_canvas.create_window((0, 0), window=self.left_panel, anchor="nw")
        self.left_panel.bind("<Configure>", self._update_left_scrollregion)
        self.left_canvas.bind("<Configure>", self._resize_left_panel)
        self.left_canvas.bind("<Enter>", self._enable_left_mousewheel)
        self.left_canvas.bind("<Leave>", self._disable_left_mousewheel)
        self.left_panel.bind("<Enter>", self._enable_left_mousewheel)
        self.left_panel.bind("<Leave>", self._disable_left_mousewheel)

        right = ttk.Frame(content)
        right.pack(side="left", fill="both", expand=True)

        self._source_box(self.left_panel)
        self._chaos_box(self.left_panel)
        self._suffix_box(self.left_panel)
        self._seed_box(self.left_panel)

        self.preview_text = tk.Text(right, bg="#090d16", fg="#dfe7ff", insertbackground="#dfe7ff", relief="flat", padx=14, pady=14, wrap="word", font=("Consolas", 10))
        self.preview_text.pack(fill="both", expand=True)
        self.preview_text.insert("1.0", QUICK_GUIDE_TEXT)

    def _update_left_scrollregion(self, _event=None) -> None:
        self.left_canvas.configure(scrollregion=self.left_canvas.bbox("all"))

    def _resize_left_panel(self, event) -> None:
        self.left_canvas.itemconfigure(self.left_canvas_window, width=event.width)

    def _enable_left_mousewheel(self, _event=None) -> None:
        self.bind_all("<MouseWheel>", self._on_left_mousewheel, add="+")
        self.bind_all("<Button-4>", self._on_left_mousewheel_linux, add="+")
        self.bind_all("<Button-5>", self._on_left_mousewheel_linux, add="+")

    def _disable_left_mousewheel(self, _event=None) -> None:
        self.unbind_all("<MouseWheel>")
        self.unbind_all("<Button-4>")
        self.unbind_all("<Button-5>")

    def _on_left_mousewheel(self, event) -> str:
        delta = -1 * int(event.delta / 120) if event.delta else 0
        if delta == 0:
            delta = 1
        self.left_canvas.yview_scroll(delta, "units")
        return "break"

    def _on_left_mousewheel_linux(self, event) -> str:
        delta = -1 if getattr(event, "num", None) == 4 else 1
        self.left_canvas.yview_scroll(delta, "units")
        return "break"

    def _make_checkbutton(self, parent, text: str, variable: tk.BooleanVar) -> tk.Frame:
        normal_bg = "#141926"
        hover_bg = "#25304f"
        normal_fg = "#dde5ff"
        hover_fg = "#ffffff"

        row = tk.Frame(parent, bg=normal_bg, cursor="hand2", padx=0, pady=2)
        mark = tk.Label(
            row,
            width=3,
            bg=normal_bg,
            fg=normal_fg,
            anchor="w",
            font=("Segoe UI", 10, "bold"),
        )
        label = tk.Label(
            row,
            text=text,
            bg=normal_bg,
            fg=normal_fg,
            anchor="w",
            justify="left",
            font=("Segoe UI", 10),
        )
        mark.pack(side="left", padx=(0, 2))
        label.pack(side="left", fill="x", expand=True)

        def refresh(*_args) -> None:
            mark.configure(text="[x]" if variable.get() else "[ ]")

        def apply_colors(bg: str, fg: str) -> None:
            row.configure(bg=bg)
            mark.configure(bg=bg, fg=fg)
            label.configure(bg=bg, fg=fg)

        def toggle(_event=None) -> str:
            variable.set(not variable.get())
            refresh()
            return "break"

        def enter(_event=None) -> None:
            apply_colors(hover_bg, hover_fg)

        def leave(_event=None) -> None:
            apply_colors(normal_bg, normal_fg)

        for widget in (row, mark, label):
            widget.bind("<Button-1>", toggle)
            widget.bind("<Enter>", enter)
            widget.bind("<Leave>", leave)

        variable.trace_add("write", refresh)
        refresh()
        return row

    def _make_text_entry(self, parent, variable: tk.StringVar) -> tk.Entry:
        entry = tk.Entry(
            parent,
            textvariable=variable,
            bg="#0f1422",
            fg="#eef3ff",
            insertbackground="#ffffff",
            relief="sunken",
            bd=1,
            highlightthickness=1,
            highlightbackground="#3a456e",
            highlightcolor="#5964ff",
            font=("Segoe UI", 10),
        )
        return entry

    def _source_box(self, parent: ttk.Frame) -> None:
        box = ttk.LabelFrame(parent, text="Source Mode", padding=12)
        box.pack(fill="x", pady=(0, 12))
        self._combo(box, "Processing preset", self.preset_var, [
            ("Chaos randomizer: mix chunks", "chaos"),
            ("Sentence splitter: split + dedupe", "sentence_splitter"),
        ])
        self._combo(box, "Processing target", self.mode_var, [
            ("TXT: process each line", "txt"),
            ("CSV: extract 2nd column / prompt -> TXT", "csv_prompt"),
            ("CSV: extract 3rd column / negative prompt -> TXT", "csv_negative"),
        ])
        self._combo(box, "CSV header", self.header_var, [("Auto-detect header", "auto"), ("First row is header", "yes"), ("No header", "no")])
        self._combo(box, "CSV delimiter", self.delimiter_var, [("Auto delimiter", "auto"), ("Comma ,", "comma"), ("Semicolon ;", "semicolon"), ("Tab", "tab")])

    def _chaos_box(self, parent: ttk.Frame) -> None:
        box = ttk.LabelFrame(parent, text="Chaos Mixer", padding=12)
        box.pack(fill="x", pady=(0, 12))
        self._combo(box, "Shuffle style", self.shuffle_var, [
            ("Maximum chaos: shuffle all chunks", "all_halves"),
            ("Readable: keep first halves", "keep_first_halves"),
            ("Cross-insert shuffled halves", "line_insert"),
        ])
        self._combo(box, "Segment split", self.segment_var, [
            ("Halves: classic 50/50 split", "halves"),
            ("Quarters: split into up to 4 chunks", "quarters"),
            ("Mixed: halves + quarters chunk pool", "mixed"),
        ])
        self._combo(box, "Output amount", self.output_factor_var, [
            ("Normal: about 1x source line count", "1"),
            ("Expanded: up to 2x wildcard lines", "2"),
        ])
        self._combo(box, "Insertion", self.placement_var, [("Random start/end", "random"), ("Insert at beginning", "prepend"), ("Insert at end", "append")])
        minrow = ttk.Frame(box)
        minrow.pack(fill="x", pady=4)
        ttk.Label(minrow, text="Min splitter length", background="#141926").pack(side="left")
        tk.Spinbox(minrow, from_=8, to=160, textvariable=self.min_sentence_chars_var, width=8, bg="#0f1422", fg="#eef3ff", insertbackground="#eef3ff").pack(side="right")
        spinrow = ttk.Frame(box)
        spinrow.pack(fill="x", pady=4)
        ttk.Label(spinrow, text="Chaos passes", background="#141926").pack(side="left")
        tk.Spinbox(spinrow, from_=1, to=5, textvariable=self.passes_var, width=8, bg="#0f1422", fg="#eef3ff", insertbackground="#eef3ff").pack(side="right")
        self._make_checkbutton(box, "Avoid pairing halves from the same original line", self.avoid_same_var).pack(anchor="w", fill="x", pady=3)
        self._make_checkbutton(box, "Preserve blank lines", self.keep_blanks_var).pack(anchor="w", fill="x", pady=3)
        self._make_checkbutton(box, "Clean repeated spaces", self.normalize_spaces_var).pack(anchor="w", fill="x", pady=3)

    def _suffix_box(self, parent: ttk.Frame) -> None:
        box = ttk.LabelFrame(parent, text="Balancing Phrases", padding=12)
        box.pack(fill="x", pady=(0, 12))
        ttk.Label(box, text="Positive/TXT phrase", background="#141926").pack(anchor="w", pady=(0, 4))
        positive_entry = self._make_text_entry(box, self.positive_suffix_var)
        positive_entry.pack(fill="x", pady=(0, 12), ipady=7)
        ttk.Label(box, text="Negative prompt phrase", background="#141926").pack(anchor="w", pady=(0, 4))
        negative_entry = self._make_text_entry(box, self.negative_suffix_var)
        negative_entry.pack(fill="x", pady=(0, 2), ipady=7)

    def _seed_box(self, parent: ttk.Frame) -> None:
        box = ttk.LabelFrame(parent, text="Reproducibility", padding=12)
        box.pack(fill="x")
        self._make_checkbutton(box, "Use fixed seed", self.use_seed_var).pack(anchor="w", fill="x")
        tk.Spinbox(box, from_=0, to=999999999, textvariable=self.seed_var, width=14, bg="#0f1422", fg="#eef3ff", insertbackground="#eef3ff").pack(anchor="w", pady=5)
        ttk.Label(box, text="Disabled seed = new output every button press.", style="Muted.TLabel", wraplength=330).pack(anchor="w")

    def _combo(self, parent: ttk.Frame, label: str, var: tk.StringVar, items: list[tuple[str, str]]) -> None:
        row = tk.Frame(parent, bg="#141926")
        row.pack(fill="x", pady=7)
        row.grid_columnconfigure(1, weight=1)

        label_widget = tk.Label(
            row,
            text=label,
            bg="#141926",
            fg="#e9eefc",
            font=("Segoe UI", 10),
            anchor="w",
            width=18,
        )
        label_widget.grid(row=0, column=0, sticky="w", padx=(0, 14))

        labels_by_value = {value: item_label for item_label, value in items}
        display_var = tk.StringVar()

        button = tk.Menubutton(
            row,
            textvariable=display_var,
            bg="#0f1422",
            fg="#eef3ff",
            activebackground="#0f1422",
            activeforeground="#eef3ff",
            disabledforeground="#8f9cc0",
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground="#3a456e",
            highlightcolor="#5964ff",
            anchor="w",
            justify="left",
            padx=9,
            pady=6,
            width=36,
            font=("Segoe UI", 10),
            cursor="hand2",
            direction="below",
        )
        button.grid(row=0, column=1, sticky="ew")

        menu = tk.Menu(
            button,
            tearoff=False,
            bg="#0f1422",
            fg="#eef3ff",
            activebackground="#5964ff",
            activeforeground="#ffffff",
            bd=0,
            relief="flat",
            font=("Segoe UI", 10),
        )
        button.configure(menu=menu)

        def sync_display(*_args) -> None:
            current_label = labels_by_value.get(var.get(), items[0][0])
            display_var.set(f"{current_label}   ▼")

        def set_value(value: str) -> None:
            var.set(value)
            sync_display()

        for item_label, item_value in items:
            menu.add_command(label=item_label, command=lambda value=item_value: set_value(value))

        var.trace_add("write", sync_display)
        sync_display()

    def choose_file(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("Text and CSV Files", "*.txt *.csv"), ("Text Files", "*.txt"), ("CSV Files", "*.csv"), ("All Files", "*.*")])
        if not path:
            return
        self.selected_path = Path(path)
        self.path_var.set(str(self.selected_path))
        if self.selected_path.suffix.lower() == ".csv":
            self.mode_var.set("csv_prompt")
        elif self.selected_path.suffix.lower() == ".txt":
            self.mode_var.set("txt")
        self._set_text(f"Selected:\n{self.selected_path}\n\nPress Preview or Randomize + Save.")

    def _collect_options(self) -> RandomizerOptions:
        return RandomizerOptions(
            mode=self.mode_var.get(),
            processing_preset=self.preset_var.get(),
            shuffle_mode=self.shuffle_var.get(),
            segment_mode=self.segment_var.get(),
            output_factor=int(self.output_factor_var.get()),
            min_sentence_chars=int(self.min_sentence_chars_var.get()),
            placement_mode=self.placement_var.get(),
            positive_suffix=self.positive_suffix_var.get().strip() or "anything is matching well.",
            negative_suffix=self.negative_suffix_var.get().strip() or "worse looking.",
            avoid_same_source_pair=self.avoid_same_var.get(),
            preserve_blank_lines=self.keep_blanks_var.get(),
            normalize_whitespace=self.normalize_spaces_var.get(),
            passes=int(self.passes_var.get()),
            seed=int(self.seed_var.get()) if self.use_seed_var.get() else None,
            csv_header_mode=self.header_var.get(),
            csv_delimiter_mode=self.delimiter_var.get(),
        )

    def preview(self) -> None:
        if not self.selected_path:
            messagebox.showinfo("No file selected", "Please choose a .txt or .csv file first.")
            return
        try:
            output, stats = preview_items_from_file(self.selected_path, self._collect_options(), max_items=10)
            lines = ["Preview only – no file was saved.", "", "First generated items:", ""]
            for i, line in enumerate(output, start=1):
                lines.append(f"{i:02d}: {line}")
            lines.extend(["", "Stats:", self._format_stats(stats)])
            self._set_text("\n".join(lines))
        except Exception as exc:
            messagebox.showerror("Preview failed", str(exc))

    def randomize_save(self) -> None:
        if not self.selected_path:
            messagebox.showinfo("No file selected", "Please choose a .txt or .csv file first.")
            return
        try:
            stats = process_file(self.selected_path, self._collect_options())
            self.last_output_path = Path(stats.output_path)
            self.open_button.configure(state="normal")
            self._set_text("Saved randomized file.\n\n" + self._format_stats(stats))
            messagebox.showinfo("Done", f"Saved:\n{stats.output_path}")
        except Exception as exc:
            messagebox.showerror("Randomize failed", str(exc))

    def open_output_folder(self) -> None:
        if not self.last_output_path:
            return
        folder = self.last_output_path.parent
        if sys.platform.startswith("win"):
            os.startfile(folder)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            os.system(f'open "{folder}"')
        else:
            os.system(f'xdg-open "{folder}"')

    def _set_text(self, text: str) -> None:
        self.preview_text.delete("1.0", "end")
        self.preview_text.insert("1.0", text)

    def _format_stats(self, stats) -> str:
        warnings = stats.warnings or []
        lines = [
            f"Input:  {stats.input_path}" if stats.input_path else "Input:  preview sample",
            f"Output: {stats.output_path}" if stats.output_path else "Output: not saved",
            f"Mode: {stats.mode}",
            f"Processing preset: {stats.processing_preset}",
            f"Processed items: {stats.processed_items}",
            f"Untouched items: {stats.untouched_items}",
            f"Zero-dot fixes: {stats.zero_dot_fixed}",
            f"Odd-dot fixes: {stats.odd_dot_fixed}",
            f"Even-dot unchanged: {stats.even_dot_unchanged}",
            f"Chunks created: {stats.chunks_created}",
            f"Segment split: {stats.segment_mode}",
            f"Output amount: {stats.output_factor}x",
            f"Min splitter length: {stats.min_sentence_chars}",
            f"Duplicate lines removed: {stats.deduplicated_items}",
            f"Short fragments merged: {stats.short_items_merged}",
            f"Short leftovers extended: {stats.suffix_extended_items}",
            f"Passes: {stats.passes}",
            f"Seed: {stats.seed if stats.seed is not None else 'random every run'}",
        ]
        if warnings:
            lines.append("Warnings:")
            lines.extend(f"- {w}" for w in warnings)
        return "\n".join(lines)


def main() -> None:
    app = PromptChaosTk()
    app.mainloop()


if __name__ == "__main__":
    main()
