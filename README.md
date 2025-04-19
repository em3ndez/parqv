# parqv

[![Python Version](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![PyPI version](https://badge.fury.io/py/parqv.svg)](https://badge.fury.io/py/parqv) <!-- Link after PyPI release -->
[![Built with Textual](https://img.shields.io/badge/Built%20with-Textual-blueviolet.svg)](https://textual.textualize.io/)
<!-- Optional: Add BuyMeACoffee or other badges later if desired -->

**`parqv` is a Python-based interactive TUI (Text User Interface) tool designed to explore, analyze, and understand Parquet files directly within your terminal.** Forget juggling multiple commands; `parqv` provides a unified, visual experience.

## 💻 Demo

![parqv.gif](assets/parqv.gif)

## 🤔 Why `parqv`?
1.  **Unified Interface:** Launch `parqv <file.parquet>` to access **metadata, schema, data preview, column statistics, and row group details** all within a single, navigable terminal window. No more memorizing different commands.
2.  **Interactive Exploration:**
    *   **🖱️ Keyboard & Mouse Driven:** Navigate using familiar keys (arrows, `hjkl`, Tab) or even your mouse (thanks to `Textual`).
    *   **📜 Scrollable Views:** Easily scroll through large schemas, data tables, or row group lists.
    *   **🌲 Expandable Schema:** Visualize and navigate complex nested structures (Structs, Lists) effortlessly.
    *   **📊 Dynamic Stats:** Select a column and instantly see its detailed statistics and distribution.
3.  **Enhanced Analysis & Visualization:**
    *   **🎨 Rich Display:** Leverages `rich` and `Textual` for colorful, readable tables and syntax-highlighted schema.
    *   **📈 Quick Stats:** Go beyond min/max/nulls. See means, medians, quantiles, distinct counts, frequency distributions, and even text-based histograms.
    *   **🔬 Row Group Deep Dive:** Inspect individual row groups to understand compression, encoding, and potential data skew.

## ✨ Features (TUI Mode)
*   **Interactive TUI:** Run `parqv <file.parquet>` to launch the main interface.
*   **Metadata Panel:** Displays key file information (path, creator, total rows, row groups, compression, etc.).
*   **Schema Explorer:**
    *   Interactive, collapsible tree view for schemas.
    *   Clearly shows column names, data types (including nested types), and nullability.
    *   Syntax highlighting for better readability.
*   **Data Table Viewer:**
    *   Scrollable table preview of the file's data.
    *   Handles large files by loading data pages on demand.
    *   (Planned) Column selection/reordering.
*   **Row Group Inspector:**
    *   List all row groups with key stats (row count, compressed/uncompressed size).
    *   Select a row group to view per-column details (encoding, size, stats within the group).

## 🚀 Getting Started

**1. Prerequisites:**
*   **Python:** Version 3.10 or higher.
*   **pip:** The Python package installer.

**2. Install `parqv`:**
*   Open your terminal and run:
    ```bash
    pip install parqv
    ```
*   **Updating `parqv`:**
    ```bash
    pip install --upgrade parqv
    ```

**3. Run `parqv`:**
*   Point `parqv` to your Parquet file:
    ```bash
    parqv /path/to/your/data.parquet
    ```
*   The interactive TUI will launch. Use your keyboard (and mouse, if supported by your terminal) to navigate:
    *   **Arrow Keys / `h`,`j`,`k`,`l`:** Move focus within lists, tables, trees.
    *   **`Tab` / `Shift+Tab`:** Cycle focus between different panes/widgets.
    *   **`Enter`:** Select items, expand/collapse tree nodes.
    *   **View Switching Keys (Examples - check help):** `m` (Metadata), `s` (Schema), `d` (Data), `t` (Stats), `g` (Row Groups).
    *   **`PageUp` / `PageDown` / `Home` / `End`:** Scroll long lists or tables.
    *   **`?`:** Show help screen with keybindings.
    *   **`q` / `Ctrl+C`:** Quit `parqv`.

---

## 📄 License

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) for the full license text.