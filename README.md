# Prompt Chaos Randomizer v1.0.11

Offline-capable GUI tool for TXT wildcard prompt lists and Stable-Diffusion-style CSV source files.

## What it does

For each processed TXT line or selected CSV field:

1. Counts `.` period characters.
2. If the count is odd, appends `anything is matching well.` for TXT/prompt text.
3. If the count is zero, appends `.` plus the balancing phrase, producing at least two periods.
4. For CSV negative-prompt mode, the balancing phrase is `worse looking.` by default.
5. Splits each item at period boundaries into halves, quarters, or a mixed chunk pool.
6. Randomly recombines resulting chunks with chunks from other lines/rows.
7. Optionally creates an expanded 2x output set for larger wildcard lists.
8. Saves a new plain TXT wildcard file beside the source file as:

```text
originalname_changed_YYYY-MM-DD_HH-MM-SS.txt
```

The output is always `.txt`, including when the source file is `.csv`. CSV files are only used as input sources; the selected prompt column is extracted and written as normal Forge/A1111 wildcard lines.

The original file is never overwritten.

## Start on Windows

Run:

```bat
install_windows.bat
```

Then use:

```bat
run_windows.bat
```

The installer creates a local `.venv` folder next to the app. If the `wheelhouse` folder is empty, it first tries to download PyQt6 wheels automatically. If that is not possible because the machine is offline or pip cannot reach PyPI, the app still runs with the built-in Tkinter fallback GUI.

## PyQt6 / offline wheelhouse

The project includes a full PyQt6 GUI and an offline fallback GUI based on Tkinter.

For a fully offline PyQt6 install, you can either let `install_windows.bat` try this automatically, or run this once manually on a machine with internet access and the same Windows/Python architecture:

```bat
prepare_pyqt6_wheelhouse_online.bat
```

This fills the `wheelhouse` folder with PyQt6 wheels. After that, copy the whole project folder to the offline machine and run `install_windows.bat`. If the wheelhouse is empty, the app still runs offline using the built-in Tkinter fallback GUI.

## CSV layout

The CSV mode expects the common Stable Diffusion style layout as input:

```csv
name,prompt,negative prompt
Style A,"prompt text here","negative prompt here"
```

Selectable processing targets:

- TXT: each line -> TXT wildcard output
- CSV: second column / prompt -> TXT wildcard output
- CSV: third column / negative prompt -> TXT wildcard output

The CSV delimiter can be auto-detected or manually set to comma, semicolon or tab. The CSV name column, header row and unselected columns are not written into the output wildcard file.

## Useful options

- Maximum chaos: shuffle all chunks
- Readable: keep first halves and shuffle second halves
- Cross-insert shuffled halves
- Segment split: halves, quarters, or mixed halves + quarters
- Output amount: normal 1x or expanded up to 2x wildcard lines
- Random/prepend/append insertion
- Avoid pairing halves/chunks from the same original line
- Preserve blank lines
- Clean repeated spaces
- Fixed seed for reproducible results
- 1–5 chaos passes

## Files

```text
src/app.py                     starts PyQt6 GUI or fallback GUI
src/main_pyqt6.py              PyQt6 GUI
src/main_tkinter.py            offline fallback GUI
src/randomizer_engine.py       processing logic
samples/                       small test files
install_windows.bat            creates .venv, tries PyQt6 wheelhouse download, then installs local wheels if available
run_windows.bat                starts the app from .venv
prepare_pyqt6_wheelhouse_online.bat  PyQt6 wheel downloader, also called automatically by installer
```


## Recent fixes

### v1.0.11

- `install_windows.bat` is now the main smart entry point.
- If no PyQt6 wheels are present, the installer automatically tries to run `prepare_pyqt6_wheelhouse_online.bat`.
- If the download fails or the machine is offline, installation continues with the Tkinter fallback GUI.
- `prepare_pyqt6_wheelhouse_online.bat` now supports an automatic no-pause mode for installer use.

### v1.0.10

- Reworked fallback GUI checkbox rendering so hover contrast stays readable on Windows themes.

### v1.0.7

- Added optional segment split modes: classic halves, quarters, and mixed halves + quarters.
- Added optional expanded output mode for up to 2x wildcard line generation.
- Updated PyQt6 and Tkinter fallback GUIs with the new randomization controls.
- Stats now show segment split mode and output amount.

### v1.0.6

- Output is now always a plain `.txt` file, including CSV input.
- CSV mode now extracts the selected prompt/negative-prompt column and writes wildcard lines instead of saving a modified CSV.
- Updated the quick guide and README to describe the Forge/A1111 wildcard workflow.

### v1.0.5

- Replaced the initial fallback GUI message with a useful quick guide inside the main text area.
- Added option explanations and the update hint for github.com/zeittresor.
- Updated PyQt6 and Tkinter fallback title strings.

### v1.0.4

- Made balancing phrase fields look like editable text boxes.
- Added scrolling for the left option panel in the fallback GUI.

### v1.0.3

- Replaced fallback GUI dropdowns with custom Tk menu dropdowns for reliable Windows offline use.
- Improved spacing between labels and dropdown fields.

### v1.0.1

- Fixed the offline Tkinter fallback startup crash caused by a naming collision with Tkinter's internal `_options` method.

## Updates

Newer versions may be available in the repositories at github.com/zeittresor.
