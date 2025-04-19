# parqv

[![Python Version](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![PyPI version](https://badge.fury.io/py/parqv.svg)](https://badge.fury.io/py/parqv) <!-- Link after PyPI release -->
[![Built with Textual](https://img.shields.io/badge/Built%20with-Textual-blueviolet.svg)](https://textual.textualize.io/)
<!-- Optional: Add BuyMeACoffee or other badges later if desired -->

**`parqv` is a Python-based interactive TUI (Text User Interface) tool designed to explore, analyze, and understand Parquet files directly within your terminal.** Forget juggling multiple commands; `parqv` provides a unified, visual experience.

## 💻 Demo (Placeholder)

*(A GIF demonstrating the interactive TUI features will go here.)*

Imagine launching `parqv <your_file.parquet>` and instantly getting an interactive view like this, allowing you to navigate through metadata, schema, data, and statistics seamlessly.

## 🤔 Why `parqv`?

Parquet is fantastic, but inspecting files can feel clunky:

*   **Fragmented Workflow:** You need separate commands (`parquet-tools meta`, `parquet-tools schema`, `head`, custom scripts) just to get a basic overview. Context switching kills productivity.
*   **Static Output:** Standard CLI tools dump information to the console. Scrolling large outputs, exploring nested structures, or dynamically viewing stats for specific columns is difficult or impossible.
*   **Limited Insight:** Getting beyond basic metadata (like column distributions, detailed row group info, or comparing schemas easily) often requires loading the data into a full analysis environment (Pandas, Spark).
*   **"What's in this file again?":** Quickly understanding the structure, content, and basic statistics of an unfamiliar Parquet file shouldn't be a chore.

**`parqv` revolutionizes Parquet exploration with an interactive TUI:**

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

**`parqv` makes understanding your Parquet files faster, more intuitive, and more insightful, directly from your terminal.**

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
*   **Column Statistics Panel:**
    *   Select a column in the Schema or Data view to see detailed statistics:
        *   Basic: Count, Null Count, Min, Max.
        *   Advanced: Mean, Median, Std Dev, Quantiles, Distinct Count, Top N Frequent Values.
        *   Visual: Text-based histogram for numerical types, length distribution for strings.
*   **Row Group Inspector:**
    *   List all row groups with key stats (row count, compressed/uncompressed size).
    *   Select a row group to view per-column details (encoding, size, stats within the group).
*   **Modern TUI Experience:** Built with [`Textual`](https://textual.textualize.io/) for a smooth, responsive feel.
*   **Efficient Loading:** Uses `pyarrow` to read only necessary metadata or data chunks, keeping memory usage low.

## 🏗️ Architecture (TUI Mode)

`parqv` operates as a local Python application leveraging the `Textual` TUI framework.

1.  Running `parqv <file.parquet>` starts the `Textual` application.
2.  `pyarrow` is used to efficiently read the Parquet file's footer to extract metadata and schema information without loading the entire dataset.
3.  The TUI layout is rendered, typically including:
    *   A header/footer for status and keybindings.
    *   Navigable panes/tabs for Metadata, Schema, Data, Statistics, and Row Groups.
    *   A main content area displaying the active view's information.
4.  User interactions (key presses, mouse clicks) trigger events.
5.  Based on the event (e.g., selecting a column, scrolling the data table, switching views), `parqv` uses `pyarrow` to:
    *   Read specific data pages for the Data Table view.
    *   Calculate statistics for a selected column (potentially chunk-wise for large files).
    *   Retrieve detailed row group information.
6.  The relevant `Textual` widgets are updated with the new information, refreshing the display.
7.  The application loop continues until the user quits (`q` or `Ctrl+C`).

This architecture prioritizes responsiveness by loading data lazily and using efficient backend libraries.

## 🗺️ Roadmap

We have exciting plans for `parqv`:

*   **✨ Schema Diff View:** `parqv diff <file1> <file2>` command launching a TUI to visually compare schemas.
*   **🔍 Data Search & Filtering:** Allow searching for values or applying filters within the Data Table view.
*   **💾 Data Export:** Option to export the currently viewed/filtered data subset to CSV/JSON directly from the TUI.
*   **📊 More Visualizations:** Explore adding more advanced text-based plots (e.g., scatter plots if feasible).
*   **🔧 Configuration:** Allow user customization (keybindings, themes, default view) via a config file.
*   **🚀 Performance Tuning:** Continuously optimize for very large files and complex schemas.
*   **💡 UX Enhancements:** Improve help screens, add more intuitive navigation cues, refine layouts.
*   **(Maybe) Basic Editing:** Potentially add functionality to modify metadata (with strong warnings!).

---

## 🚀 Getting Started

**1. Prerequisites:**
*   **Python:** Version 3.8 or higher.
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

## 🙌 Contributing

Contributions are welcome! Please see `CONTRIBUTING.md` (TODO: Create this file) for guidelines on reporting issues, suggesting features, and submitting pull requests, especially for features on the Roadmap. You'll need Python, pip, and Git set up locally to contribute code.

---

## 📄 License

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) for the full license text.