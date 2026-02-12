# QGIS Notebook Plugin

A QGIS plugin for rendering and running Jupyter notebooks directly within QGIS. The plugin provides a dockable panel interface for interactive notebook execution.

[![QGIS Plugin](https://img.shields.io/badge/QGIS-Plugin-green.svg)](https://plugins.qgis.org/plugins/qgis_notebook)
![License](https://img.shields.io/badge/License-MIT-blue.svg)

## Features

- **📂 Open Notebooks**: Load and render Jupyter notebook (.ipynb) files
- **▶️ Execute Cells**: Run Python code cells with syntax highlighting
- **📝 Markdown Support**: Render markdown cells with headers, lists, links, and formatting
- **🎨 Syntax Highlighting**: Beautiful Python syntax highlighting for code cells
- **📊 Rich Output**: View text, errors, and execution results
- **🔄 QGIS Integration**: Access QGIS layers, projects, and Python environment
- **💾 Save Notebooks**: Save changes back to notebook files
- **📄 Create New**: Start fresh notebooks from within QGIS
- **⚙️ Customizable**: Configure appearance, fonts, and execution settings
- **🔄 Auto-Update**: Check for and install updates from GitHub

## Screenshots

The plugin provides a clean, dark-themed interface that integrates seamlessly with QGIS:

- **Notebook Panel**: Dockable panel for viewing and executing notebooks
- **Settings Panel**: Configure plugin behavior and appearance
- **Update Checker**: Keep the plugin up-to-date

### Notebook Panel

![](https://github.com/user-attachments/assets/104b8a54-d693-40e8-b4fd-fa8d69b0c655)

### Settings Panel

![](https://github.com/user-attachments/assets/a812876d-0f2a-4d84-8ac6-6764f38abf77)

### Update Checker

![](https://github.com/user-attachments/assets/9addca25-c9b0-49f6-b19a-4d4aaf92d5fa)


## Video Tutorial

👉 [Run Jupyter Notebooks Directly Inside QGIS! | QGIS Notebook Plugin Tutorial](https://youtu.be/Nr2QEZq2Q_Q)

[![QGIS Notebook Plugin](https://github.com/user-attachments/assets/ca52a874-f920-45cb-980d-f77006f3f2fd)](https://youtu.be/Nr2QEZq2Q_Q)

## Installation

### From QGIS Plugin Manager (Recommended)

1. Open QGIS
2. Go to **Plugins** → **Manage and Install Plugins...**
3. Go to the **Settings** tab
4. Click **Add...** under "Plugin Repositories"
5. Give a name for the repository, e.g., "OpenGeos"
6. Enter the URL of the repository: https://qgis.gishub.org/plugins.xml
7. Click **OK**
8. Go to the **All** tab
9. Search for "Notebook"
10. Select "Notebook" from the list and click **Install Plugin**

### Using Installation Scripts

#### Python Script (Cross-platform)

Clone the repository:

```bash
git clone https://github.com/opengeos/qgis-notebook-plugin.git
cd qgis-notebook-plugin
```

Install the plugin:

```bash
# Install the plugin
python install.py

# Remove the plugin
python install.py --remove
```

#### Shell Script (Linux/macOS)

```bash
# Install the plugin
./install.sh

# Remove the plugin
./install.sh --remove

# Show help
./install.sh --help
```

### Manual Installation

1. Download the latest release from <https://qgis.gishub.org>.
2. Extract the zip file
3. Copy the `qgis_notebook` folder to your QGIS plugins directory:
   - **Linux**: `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/`
   - **Windows**: `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\`
   - **macOS**: `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/`
4. Restart QGIS
5. Enable the plugin in **Plugins** → **Manage and Install Plugins...**

## Usage

### Opening a Notebook

1. Click the **📂 Open** button in the toolbar
2. Navigate to and select a `.ipynb` file
3. The notebook will be rendered in the panel

### Running Code Cells

1. Click the **▶ Run** button on any code cell to execute it
2. Use **▶▶ Run All** to execute all cells in order
3. Use **🔄 Restart Session** to reset the Python namespace and clear outputs
4. View output directly below each cell

### Creating a New Notebook

1. Click the **📄 New** button
2. Start adding code and markdown cells
3. Save with **💾 Save**

### Keyboard Shortcuts

The plugin supports JupyterLab-style keyboard shortcuts for efficient notebook editing.

#### Edit Mode (while editing a cell)

| Shortcut | Action |
|----------|--------|
| `Ctrl+Enter` | Execute current cell |
| `Shift+Enter` | Execute cell and move to next |
| `Alt+Enter` | Execute cell and insert new cell below |
| `Ctrl+Space` | Trigger autocomplete |

#### Command Mode (cell selected, not editing)

To enter command mode, click outside the text editor area of a cell (e.g., on the cell border or header).

| Shortcut | Action |
|----------|--------|
| `A` | Insert code cell above |
| `B` | Insert code cell below |
| `X` | Cut selected cell |
| `D, D` | Delete selected cell (press D twice) |
| `Y` | Change cell type to Code |
| `M` | Change cell type to Markdown |
| `Ctrl+Shift+Up` | Move cell up |
| `Ctrl+Shift+Down` | Move cell down |

## Configuration

Access settings via the **Settings** button in the toolbar:

### General Settings
- Auto-save notebooks
- Show line numbers
- Word wrap in cells

### Execution Settings
- Execution timeout
- Clear outputs before run
- Stop on error
- Pre-import modules (QGIS, os, sys, numpy, pandas)

### Appearance Settings
- Color scheme
- Code font family
- Font size
- Line height
- Cell spacing

## QGIS Integration

The plugin automatically imports QGIS modules, making it easy to work with your project:

```python
# Access the current project
from qgis.core import QgsProject
project = QgsProject.instance()

# List all layers
for layer in project.mapLayers().values():
    print(layer.name())

# Access the map canvas
from qgis.utils import iface
canvas = iface.mapCanvas()
```

## Requirements

- QGIS 3.28 or later
- Python 3.10 or later (included with QGIS)

## Update Checker

The plugin includes a built-in update checker that can:
- Check for new versions from GitHub
- Display changelog information
- Download and install updates automatically

Access it via **Notebook** → **Check for Updates...**

## About Dialog

The About dialog displays:
- Current plugin version
- Author information
- Feature list
- Links to GitHub repository and issue tracker

Access it via **Notebook** → **About QGIS Notebook**

## Development

### Packaging for Distribution

#### Python Script

```bash
# Create a zip file for distribution
python package_plugin.py

# Create without version in filename
python package_plugin.py --no-version

# Custom output path
python package_plugin.py --output /path/to/output.zip
```

#### Shell Script

```bash
# Create a zip file for distribution
./package_plugin.sh

# Create without version in filename
./package_plugin.sh --no-version

# Show help
./package_plugin.sh --help
```

The packaged zip file can be uploaded to the [QGIS Plugin Repository](https://plugins.qgis.org/).

### Project Structure

```
qgis-notebook-plugin/
├── install.py                # Cross-platform installation script
├── install.sh                # Shell installation script (Linux/macOS)
├── package_plugin.py         # Cross-platform packaging script
├── package_plugin.sh         # Shell packaging script (Linux/macOS)
├── README.md                 # This file
├── LICENSE                   # MIT License
└── qgis_notebook/            # Main plugin directory
    ├── __init__.py           # Plugin entry point
    ├── qgis_notebook.py      # Main plugin class
    ├── metadata.txt          # Plugin metadata
    ├── LICENSE               # Plugin license
    ├── dialogs/
    │   ├── __init__.py
    │   ├── notebook_dock.py  # Main notebook dock widget
    │   ├── settings_dock.py  # Settings panel
    │   └── update_checker.py # Update checker dialog
    └── icons/
        ├── icon.svg          # Main plugin icon
        ├── settings.svg      # Settings icon
        └── about.svg         # About icon
```

### Building

To package the plugin for distribution, use the provided scripts:

```bash
cd qgis-notebook-plugin

# Using Python (cross-platform)
python package_plugin.py

# Using shell script (Linux/macOS)
./package_plugin.sh

# Or manually
zip -r qgis_notebook.zip qgis_notebook/
```

The output will be a file like `qgis_notebook-0.1.0.zip` ready for distribution.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Changelog

### 0.3.0
- Fix line spacing issue on Linux

### 0.2.0
- Add support for light theme
- Add support for clearing output of a code cell
- Add support for inserting code snippets into a notebook

### 0.1.0 (Initial Release)
- Basic notebook rendering and execution
- Dockable panel interface
- Python syntax highlighting
- Markdown cell rendering
- Settings panel for configuration
- Update checker functionality
- QGIS module integration
