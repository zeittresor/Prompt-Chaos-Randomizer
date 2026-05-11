from __future__ import annotations

import os
import sys
from pathlib import Path

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices, QFont
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from randomizer_engine import RandomizerOptions, preview_items_from_file, process_file

APP_TITLE = "Prompt Chaos Randomizer – v1.0.12 – 2026-05-11"
QUICK_GUIDE_TEXT = 'Prompt Chaos Randomizer – Quick Guide\n\nPurpose\n- Creates plain TXT wildcard lists for Stable Diffusion Forge / AUTOMATIC1111.\n- The output is always a .txt file, even when the input is a .csv file.\n- The original file is never overwritten. New files are saved beside the source as: originalname_changed_[date-time].txt\n\nProcessing presets\n- Chaos randomizer: balances periods, splits lines at period boundaries into halves/quarters/mixed chunks, then recombines chunks into new wildcard lines.\n- Sentence splitter cleanup: turns every dot-ended sentence or sentence fragment into its own wildcard line, removes duplicate lines, merges very short fragments, and extends leftover short lines with the matching phrase.\n\nSource modes\n- TXT mode: reads each source line.\n- CSV prompt mode: extracts only column 2 / prompt and writes TXT wildcard lines.\n- CSV negative prompt mode: extracts only column 3 / negative prompt and writes TXT wildcard lines.\n- CSV names, headers and other columns are not written to the output.\n\nSentence splitter cleanup\n- Splits every line so each output line contains one sentence/sentence fragment ending with a dot.\n- If a source line has no dot, a dot is appended first.\n- Duplicate output lines are removed.\n- Short lines below the selected minimum length are combined with other short lines when possible.\n- If a short leftover cannot be paired cleanly, the matching positive/TXT or negative prompt phrase is appended.\n\nChaos mixer\n- Shuffle style controls how aggressively text chunks are mixed.\n- Segment split chooses classic halves, quarters, or mixed halves + quarters.\n- Output amount can create up to 2x as many wildcard lines.\n- Chaos passes repeats the mutation process.\n\nUpdates\nNewer versions may be available in the repositories at github.com/zeittresor.'


class PromptChaosWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.selected_path: Path | None = None
        self.last_output_path: Path | None = None
        self.setWindowTitle(APP_TITLE)
        self.resize(1180, 820)
        self._build_ui()
        self._apply_style()

    def _build_ui(self) -> None:
        root = QWidget()
        main = QVBoxLayout(root)
        main.setContentsMargins(22, 22, 22, 22)
        main.setSpacing(16)

        hero = QFrame()
        hero.setObjectName("Hero")
        hero_layout = QVBoxLayout(hero)
        title = QLabel("Prompt Chaos Randomizer")
        title.setObjectName("HeroTitle")
        hero_layout.addWidget(title)
        main.addWidget(hero)

        file_row = QHBoxLayout()
        self.file_label = QLabel("No file selected")
        self.file_label.setObjectName("PathLabel")
        self.file_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.select_button = QPushButton("Choose .txt / .csv")
        self.select_button.clicked.connect(self.choose_file)
        self.randomize_button = QPushButton("Randomize + Save")
        self.randomize_button.setObjectName("PrimaryButton")
        self.randomize_button.clicked.connect(self.randomize_save)
        self.preview_button = QPushButton("Preview")
        self.preview_button.clicked.connect(self.preview)
        self.open_folder_button = QPushButton("Open Output Folder")
        self.open_folder_button.setEnabled(False)
        self.open_folder_button.clicked.connect(self.open_output_folder)
        file_row.addWidget(self.select_button)
        file_row.addWidget(self.file_label, 1)
        file_row.addWidget(self.preview_button)
        file_row.addWidget(self.randomize_button)
        file_row.addWidget(self.open_folder_button)
        main.addLayout(file_row)

        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(16)

        source_box = QGroupBox("Source Mode")
        source_layout = QGridLayout(source_box)
        self.preset_combo = QComboBox()
        self.preset_combo.addItem("Chaos randomizer: mix chunks", "chaos")
        self.preset_combo.addItem("Sentence splitter: split + dedupe", "sentence_splitter")
        self.preset_combo.setToolTip("Choose the main processing workflow. Sentence splitter makes clean one-sentence-per-line wildcard TXT files.")
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("TXT: process each line", "txt")
        self.mode_combo.addItem("CSV: extract 2nd column / prompt -> TXT", "csv_prompt")
        self.mode_combo.addItem("CSV: extract 3rd column / negative prompt -> TXT", "csv_negative")
        self.mode_combo.setToolTip("For CSV files, only the selected prompt column is extracted. Output is always plain .txt wildcard lines.")
        self.header_combo = QComboBox()
        self.header_combo.addItem("Auto-detect header", "auto")
        self.header_combo.addItem("First CSV row is header", "yes")
        self.header_combo.addItem("No CSV header", "no")
        self.delimiter_combo = QComboBox()
        self.delimiter_combo.addItem("Auto delimiter", "auto")
        self.delimiter_combo.addItem("Comma ,", "comma")
        self.delimiter_combo.addItem("Semicolon ;", "semicolon")
        self.delimiter_combo.addItem("Tab", "tab")
        source_layout.addWidget(QLabel("Processing preset"), 0, 0)
        source_layout.addWidget(self.preset_combo, 0, 1)
        source_layout.addWidget(QLabel("Processing target"), 1, 0)
        source_layout.addWidget(self.mode_combo, 1, 1)
        source_layout.addWidget(QLabel("CSV header"), 2, 0)
        source_layout.addWidget(self.header_combo, 2, 1)
        source_layout.addWidget(QLabel("CSV delimiter"), 3, 0)
        source_layout.addWidget(self.delimiter_combo, 3, 1)
        grid.addWidget(source_box, 0, 0)

        chaos_box = QGroupBox("Chaos Mixer")
        chaos_layout = QGridLayout(chaos_box)
        self.shuffle_combo = QComboBox()
        self.shuffle_combo.addItem("Maximum chaos: shuffle all chunks", "all_halves")
        self.shuffle_combo.addItem("Readable: keep first halves, shuffle second halves", "keep_first_halves")
        self.shuffle_combo.addItem("Cross-insert: shuffled left + shuffled right", "line_insert")
        self.segment_combo = QComboBox()
        self.segment_combo.addItem("Halves: classic 50/50 split", "halves")
        self.segment_combo.addItem("Quarters: split into up to 4 chunks", "quarters")
        self.segment_combo.addItem("Mixed: halves + quarters chunk pool", "mixed")
        self.segment_combo.setToolTip("Controls how each line is split at period boundaries before chunks are recombined.")
        self.output_factor_combo = QComboBox()
        self.output_factor_combo.addItem("Normal: about 1x source line count", 1)
        self.output_factor_combo.addItem("Expanded: up to 2x wildcard lines", 2)
        self.output_factor_combo.setToolTip("Expanded 2x adds an extra randomized line set to the saved TXT wildcard file.")
        self.placement_combo = QComboBox()
        self.placement_combo.addItem("Random start/end", "random")
        self.placement_combo.addItem("Insert at beginning", "prepend")
        self.placement_combo.addItem("Insert at end", "append")
        self.min_sentence_spin = QSpinBox()
        self.min_sentence_spin.setRange(8, 160)
        self.min_sentence_spin.setValue(24)
        self.min_sentence_spin.setToolTip("Sentence splitter: short fragments below this length are combined or extended with the matching phrase.")
        self.passes_spin = QSpinBox()
        self.passes_spin.setRange(1, 5)
        self.passes_spin.setValue(1)
        self.passes_spin.setToolTip("More passes means the generated output is randomized again, making it more surreal.")
        self.avoid_same_box = QCheckBox("Avoid pairing halves from the same original line")
        self.avoid_same_box.setChecked(True)
        self.keep_blanks_box = QCheckBox("Preserve blank lines")
        self.keep_blanks_box.setChecked(True)
        self.normalize_spaces_box = QCheckBox("Clean repeated spaces")
        self.normalize_spaces_box.setChecked(True)
        chaos_layout.addWidget(QLabel("Shuffle style"), 0, 0)
        chaos_layout.addWidget(self.shuffle_combo, 0, 1)
        chaos_layout.addWidget(QLabel("Segment split"), 1, 0)
        chaos_layout.addWidget(self.segment_combo, 1, 1)
        chaos_layout.addWidget(QLabel("Output amount"), 2, 0)
        chaos_layout.addWidget(self.output_factor_combo, 2, 1)
        chaos_layout.addWidget(QLabel("Insertion"), 3, 0)
        chaos_layout.addWidget(self.placement_combo, 3, 1)
        chaos_layout.addWidget(QLabel("Min splitter length"), 4, 0)
        chaos_layout.addWidget(self.min_sentence_spin, 4, 1)
        chaos_layout.addWidget(QLabel("Chaos passes"), 5, 0)
        chaos_layout.addWidget(self.passes_spin, 5, 1)
        chaos_layout.addWidget(self.avoid_same_box, 6, 0, 1, 2)
        chaos_layout.addWidget(self.keep_blanks_box, 7, 0, 1, 2)
        chaos_layout.addWidget(self.normalize_spaces_box, 8, 0, 1, 2)
        grid.addWidget(chaos_box, 0, 1)

        suffix_box = QGroupBox("Balancing Phrases")
        suffix_layout = QGridLayout(suffix_box)
        self.positive_suffix_edit = QLineEdit("anything is matching well.")
        self.negative_suffix_edit = QLineEdit("worse looking.")
        self.positive_suffix_edit.setToolTip("Used for TXT lines and CSV prompt column when a line has zero or an odd number of periods.")
        self.negative_suffix_edit.setToolTip("Used for CSV negative prompt column, so the balancing phrase still fits a negative prompt.")
        suffix_layout.addWidget(QLabel("Positive/TXT phrase"), 0, 0)
        suffix_layout.addWidget(self.positive_suffix_edit, 0, 1)
        suffix_layout.addWidget(QLabel("Negative prompt phrase"), 1, 0)
        suffix_layout.addWidget(self.negative_suffix_edit, 1, 1)
        grid.addWidget(suffix_box, 1, 0)

        reproducibility_box = QGroupBox("Reproducibility")
        rep_layout = QGridLayout(reproducibility_box)
        self.use_seed_box = QCheckBox("Use fixed seed")
        self.seed_spin = QSpinBox()
        self.seed_spin.setRange(0, 999999999)
        self.seed_spin.setValue(12345)
        self.seed_spin.setEnabled(False)
        self.use_seed_box.toggled.connect(self.seed_spin.setEnabled)
        rep_layout.addWidget(self.use_seed_box, 0, 0)
        rep_layout.addWidget(self.seed_spin, 0, 1)
        tip = QLabel("Leave seed disabled for a different result every time the Randomize button is pressed.")
        tip.setWordWrap(True)
        tip.setObjectName("Muted")
        rep_layout.addWidget(tip, 1, 0, 1, 2)
        grid.addWidget(reproducibility_box, 1, 1)

        main.addLayout(grid)

        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setPlaceholderText("Preview and processing log will appear here.")
        self.preview_text.setObjectName("Preview")
        self.preview_text.setPlainText(QUICK_GUIDE_TEXT)
        main.addWidget(self.preview_text, 1)

        self.setCentralWidget(root)

    def _apply_style(self) -> None:
        font = QFont("Segoe UI", 10)
        self.setFont(font)
        self.setStyleSheet(
            """
            QWidget {
                background: #10131c;
                color: #e9eefc;
                font-family: Segoe UI, Arial, sans-serif;
            }
            QFrame#Hero {
                border: 1px solid rgba(132, 156, 255, 0.45);
                border-radius: 22px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #222b5f, stop:0.5 #171b31, stop:1 #142b2b);
                padding: 18px;
            }
            QLabel#HeroTitle {
                font-size: 31px;
                font-weight: 800;
                letter-spacing: 0.5px;
                color: #ffffff;
            }
            QLabel#HeroSubtitle {
                color: #cbd6ff;
                font-size: 13px;
            }
            QLabel#PathLabel {
                border: 1px solid #2a3150;
                border-radius: 12px;
                padding: 10px 12px;
                background: #151a28;
                color: #c9d3f2;
            }
            QLabel#Muted {
                color: #97a3c7;
            }
            QGroupBox {
                border: 1px solid #2d3556;
                border-radius: 18px;
                margin-top: 16px;
                padding: 16px;
                background: #141926;
                font-weight: 700;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 16px;
                padding: 2px 8px;
                color: #b8c6ff;
                background: #10131c;
                border-radius: 8px;
            }
            QPushButton {
                border: 1px solid #3a456e;
                border-radius: 13px;
                background: #1b2238;
                color: #f5f7ff;
                padding: 10px 15px;
                font-weight: 650;
            }
            QPushButton:hover {
                background: #1b2238;
                border-color: #5964ff;
                color: #f5f7ff;
            }
            QPushButton:pressed {
                background: #12182a;
            }
            QPushButton#PrimaryButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #5964ff, stop:1 #1cc7a6);
                border: 0px;
                color: #ffffff;
            }
            QPushButton#PrimaryButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #5964ff, stop:1 #1cc7a6);
                color: #ffffff;
            }
            QComboBox, QLineEdit, QSpinBox {
                background: #0f1422;
                border: 1px solid #2e375a;
                border-radius: 10px;
                padding: 8px;
                color: #eef3ff;
            }
            QComboBox:hover, QLineEdit:hover, QSpinBox:hover {
                border-color: #3f4a70;
            }
            QCheckBox {
                spacing: 8px;
                color: #dde5ff;
            }
            QTextEdit#Preview {
                background: #090d16;
                border: 1px solid #2c3658;
                border-radius: 18px;
                padding: 14px;
                color: #dfe7ff;
                selection-background-color: #5964ff;
                font-family: Consolas, Cascadia Mono, monospace;
                font-size: 10.5pt;
            }
            """
        )

    def choose_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose TXT or CSV file",
            str(Path.home()),
            "Text and CSV Files (*.txt *.csv);;Text Files (*.txt);;CSV Files (*.csv);;All Files (*.*)",
        )
        if not path:
            return
        self.selected_path = Path(path)
        self.file_label.setText(str(self.selected_path))
        suffix = self.selected_path.suffix.lower()
        if suffix == ".csv":
            self.mode_combo.setCurrentIndex(1)
        elif suffix == ".txt":
            self.mode_combo.setCurrentIndex(0)
        self.preview_text.setPlainText(f"Selected:\n{self.selected_path}\n\nPress Preview or Randomize + Save.")

    def _options(self) -> RandomizerOptions:
        seed = self.seed_spin.value() if self.use_seed_box.isChecked() else None
        return RandomizerOptions(
            mode=self.mode_combo.currentData(),
            processing_preset=self.preset_combo.currentData(),
            shuffle_mode=self.shuffle_combo.currentData(),
            segment_mode=self.segment_combo.currentData(),
            output_factor=int(self.output_factor_combo.currentData()),
            min_sentence_chars=self.min_sentence_spin.value(),
            placement_mode=self.placement_combo.currentData(),
            positive_suffix=self.positive_suffix_edit.text().strip() or "anything is matching well.",
            negative_suffix=self.negative_suffix_edit.text().strip() or "worse looking.",
            avoid_same_source_pair=self.avoid_same_box.isChecked(),
            preserve_blank_lines=self.keep_blanks_box.isChecked(),
            normalize_whitespace=self.normalize_spaces_box.isChecked(),
            passes=self.passes_spin.value(),
            seed=seed,
            csv_header_mode=self.header_combo.currentData(),
            csv_delimiter_mode=self.delimiter_combo.currentData(),
        )

    def preview(self) -> None:
        if not self.selected_path:
            QMessageBox.information(self, "No file selected", "Please choose a .txt or .csv file first.")
            return
        try:
            output, stats = preview_items_from_file(self.selected_path, self._options(), max_items=10)
            text = ["Preview only – no file was saved.", "", "First generated items:", ""]
            for i, line in enumerate(output, start=1):
                text.append(f"{i:02d}: {line}")
            text.extend(["", "Stats:", self._format_stats(stats)])
            self.preview_text.setPlainText("\n".join(text))
        except Exception as exc:
            QMessageBox.critical(self, "Preview failed", str(exc))

    def randomize_save(self) -> None:
        if not self.selected_path:
            QMessageBox.information(self, "No file selected", "Please choose a .txt or .csv file first.")
            return
        try:
            stats = process_file(self.selected_path, self._options())
            self.last_output_path = Path(stats.output_path)
            self.open_folder_button.setEnabled(True)
            self.preview_text.setPlainText("Saved randomized file.\n\n" + self._format_stats(stats))
            QMessageBox.information(self, "Done", f"Saved:\n{stats.output_path}")
        except Exception as exc:
            QMessageBox.critical(self, "Randomize failed", str(exc))

    def open_output_folder(self) -> None:
        if not self.last_output_path:
            return
        folder = self.last_output_path.parent
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

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
    app = QApplication(sys.argv)
    window = PromptChaosWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
