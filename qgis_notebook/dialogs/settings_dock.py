"""
Settings Dock Widget for QGIS Notebook Plugin

This module provides a settings panel for configuring
the notebook plugin options.
"""

from qgis.PyQt.QtCore import Qt, QSettings
from qgis.PyQt.QtWidgets import (
    QDockWidget,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QGroupBox,
    QComboBox,
    QSpinBox,
    QCheckBox,
    QFormLayout,
    QMessageBox,
    QFileDialog,
    QTabWidget,
)
from qgis.PyQt.QtGui import QFont


class SettingsDockWidget(QDockWidget):
    """A settings panel for configuring notebook plugin options."""

    # Settings keys
    SETTINGS_PREFIX = "QGISNotebook/"

    def __init__(self, iface, parent=None):
        """Initialize the settings dock widget.

        Args:
            iface: QGIS interface instance.
            parent: Parent widget.
        """
        super().__init__("Notebook Settings", parent)
        self.iface = iface
        self.settings = QSettings()

        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)

        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        """Set up the settings UI."""
        main_widget = QWidget()
        self.setWidget(main_widget)

        main_layout = QVBoxLayout(main_widget)
        main_layout.setSpacing(10)

        # Header
        header_label = QLabel("Notebook Settings")
        header_font = QFont()
        header_font.setPointSize(12)
        header_font.setBold(True)
        header_label.setFont(header_font)
        header_label.setAlignment(Qt.AlignCenter)
        header_label.setStyleSheet("color: #E8BF6A; padding: 10px;")
        main_layout.addWidget(header_label)

        # Tab widget for organized settings
        tab_widget = QTabWidget()
        tab_widget.setStyleSheet(
            """
            QTabWidget::pane {
                border: 1px solid #3C3F41;
                border-radius: 4px;
            }
            QTabBar::tab {
                background-color: #2B2D30;
                color: #BCBEC4;
                padding: 8px 16px;
                border: 1px solid #3C3F41;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #3C3F41;
                color: #E8BF6A;
            }
            QTabBar::tab:hover {
                background-color: #4E5254;
            }
        """
        )
        main_layout.addWidget(tab_widget)

        # General settings tab
        general_tab = self._create_general_tab()
        tab_widget.addTab(general_tab, "General")

        # Execution settings tab
        execution_tab = self._create_execution_tab()
        tab_widget.addTab(execution_tab, "Execution")

        # Appearance settings tab
        appearance_tab = self._create_appearance_tab()
        tab_widget.addTab(appearance_tab, "Appearance")

        # Buttons
        button_layout = QHBoxLayout()

        self.save_btn = QPushButton("Save Settings")
        self.save_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #365880;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #4A6FA5; }
        """
        )
        self.save_btn.clicked.connect(self._save_settings)
        button_layout.addWidget(self.save_btn)

        self.reset_btn = QPushButton("Reset Defaults")
        self.reset_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #5F3C41;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #7A4A50; }
        """
        )
        self.reset_btn.clicked.connect(self._reset_defaults)
        button_layout.addWidget(self.reset_btn)

        main_layout.addLayout(button_layout)

        # Stretch at the end
        main_layout.addStretch()

        # Status label
        self.status_label = QLabel("Settings loaded")
        self.status_label.setStyleSheet(
            "color: #6E7274; font-size: 10px; padding: 4px;"
        )
        main_layout.addWidget(self.status_label)

    def _create_general_tab(self):
        """Create the general settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # General options group
        general_group = QGroupBox("General Options")
        general_group.setStyleSheet(
            """
            QGroupBox {
                font-weight: bold;
                border: 1px solid #3C3F41;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #6897BB;
            }
        """
        )
        general_layout = QFormLayout(general_group)

        # Auto-save option
        self.auto_save_check = QCheckBox()
        self.auto_save_check.setChecked(False)
        general_layout.addRow("Auto-save notebooks:", self.auto_save_check)

        # Auto-save interval
        self.auto_save_interval = QSpinBox()
        self.auto_save_interval.setRange(30, 600)
        self.auto_save_interval.setValue(60)
        self.auto_save_interval.setSuffix(" seconds")
        general_layout.addRow("Auto-save interval:", self.auto_save_interval)

        # Show line numbers
        self.line_numbers_check = QCheckBox()
        self.line_numbers_check.setChecked(True)
        general_layout.addRow("Show line numbers:", self.line_numbers_check)

        # Word wrap
        self.word_wrap_check = QCheckBox()
        self.word_wrap_check.setChecked(True)
        general_layout.addRow("Word wrap in cells:", self.word_wrap_check)

        layout.addWidget(general_group)

        # Default paths group
        paths_group = QGroupBox("Default Paths")
        paths_group.setStyleSheet(general_group.styleSheet())
        paths_layout = QFormLayout(paths_group)

        # Default notebook directory
        dir_layout = QHBoxLayout()
        self.default_dir_input = QLineEdit()
        self.default_dir_input.setPlaceholderText("Default notebook directory...")
        dir_layout.addWidget(self.default_dir_input)
        self.browse_dir_btn = QPushButton("...")
        self.browse_dir_btn.setMaximumWidth(30)
        self.browse_dir_btn.clicked.connect(self._browse_default_dir)
        dir_layout.addWidget(self.browse_dir_btn)
        paths_layout.addRow("Notebook directory:", dir_layout)

        layout.addWidget(paths_group)

        layout.addStretch()
        return widget

    def _create_execution_tab(self):
        """Create the execution settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Kernel options group
        kernel_group = QGroupBox("Execution Options")
        kernel_group.setStyleSheet(
            """
            QGroupBox {
                font-weight: bold;
                border: 1px solid #3C3F41;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #6897BB;
            }
        """
        )
        kernel_layout = QFormLayout(kernel_group)

        # Execution timeout
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(0, 3600)
        self.timeout_spin.setValue(0)
        self.timeout_spin.setSpecialValueText("No limit")
        self.timeout_spin.setSuffix(" seconds")
        kernel_layout.addRow("Execution timeout:", self.timeout_spin)

        # Clear outputs before run
        self.clear_before_run_check = QCheckBox()
        self.clear_before_run_check.setChecked(True)
        kernel_layout.addRow("Clear outputs before run:", self.clear_before_run_check)

        # Stop on error
        self.stop_on_error_check = QCheckBox()
        self.stop_on_error_check.setChecked(True)
        kernel_layout.addRow("Stop on error:", self.stop_on_error_check)

        # Show execution time
        self.show_exec_time_check = QCheckBox()
        self.show_exec_time_check.setChecked(True)
        kernel_layout.addRow("Show execution time:", self.show_exec_time_check)

        layout.addWidget(kernel_group)

        # Pre-import options
        import_group = QGroupBox("Pre-import Modules")
        import_group.setStyleSheet(kernel_group.styleSheet())
        import_layout = QFormLayout(import_group)

        # Import QGIS modules
        self.import_qgis_check = QCheckBox()
        self.import_qgis_check.setChecked(True)
        import_layout.addRow("Import QGIS modules:", self.import_qgis_check)

        # Import common modules
        self.import_common_check = QCheckBox()
        self.import_common_check.setChecked(True)
        import_layout.addRow("Import os, sys:", self.import_common_check)

        # Import numpy/pandas
        self.import_numpy_check = QCheckBox()
        self.import_numpy_check.setChecked(False)
        import_layout.addRow("Import numpy, pandas:", self.import_numpy_check)

        layout.addWidget(import_group)

        layout.addStretch()
        return widget

    def _create_appearance_tab(self):
        """Create the appearance settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Theme group
        theme_group = QGroupBox("Theme")
        theme_group.setStyleSheet(
            """
            QGroupBox {
                font-weight: bold;
                border: 1px solid #3C3F41;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #6897BB;
            }
        """
        )
        theme_layout = QFormLayout(theme_group)

        # Color scheme
        self.color_scheme_combo = QComboBox()
        self.color_scheme_combo.addItems(
            ["Dark (Darcula)", "Light", "Monokai", "Solarized Dark"]
        )
        theme_layout.addRow("Color scheme:", self.color_scheme_combo)

        layout.addWidget(theme_group)

        # Font group
        font_group = QGroupBox("Fonts")
        font_group.setStyleSheet(theme_group.styleSheet())
        font_layout = QFormLayout(font_group)

        # Code font
        self.code_font_combo = QComboBox()
        self.code_font_combo.addItems(
            [
                "JetBrains Mono",
                "Consolas",
                "Monaco",
                "Fira Code",
                "Source Code Pro",
                "Menlo",
                "Courier New",
            ]
        )
        font_layout.addRow("Code font:", self.code_font_combo)

        # Font size
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 24)
        self.font_size_spin.setValue(11)
        self.font_size_spin.setSuffix(" px")
        font_layout.addRow("Font size:", self.font_size_spin)

        # Line height
        self.line_height_spin = QSpinBox()
        self.line_height_spin.setRange(100, 200)
        self.line_height_spin.setValue(140)
        self.line_height_spin.setSuffix(" %")
        font_layout.addRow("Line height:", self.line_height_spin)

        layout.addWidget(font_group)

        # Cell appearance group
        cell_group = QGroupBox("Cell Appearance")
        cell_group.setStyleSheet(theme_group.styleSheet())
        cell_layout = QFormLayout(cell_group)

        # Cell spacing
        self.cell_spacing_spin = QSpinBox()
        self.cell_spacing_spin.setRange(0, 20)
        self.cell_spacing_spin.setValue(8)
        self.cell_spacing_spin.setSuffix(" px")
        cell_layout.addRow("Cell spacing:", self.cell_spacing_spin)

        # Cell border radius
        self.cell_radius_spin = QSpinBox()
        self.cell_radius_spin.setRange(0, 20)
        self.cell_radius_spin.setValue(6)
        self.cell_radius_spin.setSuffix(" px")
        cell_layout.addRow("Border radius:", self.cell_radius_spin)

        layout.addWidget(cell_group)

        layout.addStretch()
        return widget

    def _browse_default_dir(self):
        """Open directory browser dialog."""
        dir_path = QFileDialog.getExistingDirectory(
            self, "Select Default Directory", self.default_dir_input.text() or ""
        )
        if dir_path:
            self.default_dir_input.setText(dir_path)

    def _load_settings(self):
        """Load settings from QSettings."""
        # General
        self.auto_save_check.setChecked(
            self.settings.value(f"{self.SETTINGS_PREFIX}auto_save", False, type=bool)
        )
        self.auto_save_interval.setValue(
            self.settings.value(
                f"{self.SETTINGS_PREFIX}auto_save_interval", 60, type=int
            )
        )
        self.line_numbers_check.setChecked(
            self.settings.value(f"{self.SETTINGS_PREFIX}line_numbers", True, type=bool)
        )
        self.word_wrap_check.setChecked(
            self.settings.value(f"{self.SETTINGS_PREFIX}word_wrap", True, type=bool)
        )
        self.default_dir_input.setText(
            self.settings.value(
                f"{self.SETTINGS_PREFIX}default_directory", "", type=str
            )
        )

        # Execution
        self.timeout_spin.setValue(
            self.settings.value(f"{self.SETTINGS_PREFIX}timeout", 0, type=int)
        )
        self.clear_before_run_check.setChecked(
            self.settings.value(
                f"{self.SETTINGS_PREFIX}clear_before_run", True, type=bool
            )
        )
        self.stop_on_error_check.setChecked(
            self.settings.value(f"{self.SETTINGS_PREFIX}stop_on_error", True, type=bool)
        )
        self.show_exec_time_check.setChecked(
            self.settings.value(
                f"{self.SETTINGS_PREFIX}show_exec_time", True, type=bool
            )
        )
        self.import_qgis_check.setChecked(
            self.settings.value(f"{self.SETTINGS_PREFIX}import_qgis", True, type=bool)
        )
        self.import_common_check.setChecked(
            self.settings.value(f"{self.SETTINGS_PREFIX}import_common", True, type=bool)
        )
        self.import_numpy_check.setChecked(
            self.settings.value(f"{self.SETTINGS_PREFIX}import_numpy", False, type=bool)
        )

        # Appearance
        self.color_scheme_combo.setCurrentIndex(
            self.settings.value(f"{self.SETTINGS_PREFIX}color_scheme", 0, type=int)
        )
        self.code_font_combo.setCurrentIndex(
            self.settings.value(f"{self.SETTINGS_PREFIX}code_font", 0, type=int)
        )
        self.font_size_spin.setValue(
            self.settings.value(f"{self.SETTINGS_PREFIX}font_size", 11, type=int)
        )
        self.line_height_spin.setValue(
            self.settings.value(f"{self.SETTINGS_PREFIX}line_height", 140, type=int)
        )
        self.cell_spacing_spin.setValue(
            self.settings.value(f"{self.SETTINGS_PREFIX}cell_spacing", 8, type=int)
        )
        self.cell_radius_spin.setValue(
            self.settings.value(f"{self.SETTINGS_PREFIX}cell_radius", 6, type=int)
        )

        self.status_label.setText("Settings loaded")
        self.status_label.setStyleSheet("color: #6E7274; font-size: 10px;")

    def _save_settings(self):
        """Save settings to QSettings."""
        # General
        self.settings.setValue(
            f"{self.SETTINGS_PREFIX}auto_save", self.auto_save_check.isChecked()
        )
        self.settings.setValue(
            f"{self.SETTINGS_PREFIX}auto_save_interval", self.auto_save_interval.value()
        )
        self.settings.setValue(
            f"{self.SETTINGS_PREFIX}line_numbers", self.line_numbers_check.isChecked()
        )
        self.settings.setValue(
            f"{self.SETTINGS_PREFIX}word_wrap", self.word_wrap_check.isChecked()
        )
        self.settings.setValue(
            f"{self.SETTINGS_PREFIX}default_directory", self.default_dir_input.text()
        )

        # Execution
        self.settings.setValue(
            f"{self.SETTINGS_PREFIX}timeout", self.timeout_spin.value()
        )
        self.settings.setValue(
            f"{self.SETTINGS_PREFIX}clear_before_run",
            self.clear_before_run_check.isChecked(),
        )
        self.settings.setValue(
            f"{self.SETTINGS_PREFIX}stop_on_error", self.stop_on_error_check.isChecked()
        )
        self.settings.setValue(
            f"{self.SETTINGS_PREFIX}show_exec_time",
            self.show_exec_time_check.isChecked(),
        )
        self.settings.setValue(
            f"{self.SETTINGS_PREFIX}import_qgis", self.import_qgis_check.isChecked()
        )
        self.settings.setValue(
            f"{self.SETTINGS_PREFIX}import_common", self.import_common_check.isChecked()
        )
        self.settings.setValue(
            f"{self.SETTINGS_PREFIX}import_numpy", self.import_numpy_check.isChecked()
        )

        # Appearance
        self.settings.setValue(
            f"{self.SETTINGS_PREFIX}color_scheme",
            self.color_scheme_combo.currentIndex(),
        )
        self.settings.setValue(
            f"{self.SETTINGS_PREFIX}code_font", self.code_font_combo.currentIndex()
        )
        self.settings.setValue(
            f"{self.SETTINGS_PREFIX}font_size", self.font_size_spin.value()
        )
        self.settings.setValue(
            f"{self.SETTINGS_PREFIX}line_height", self.line_height_spin.value()
        )
        self.settings.setValue(
            f"{self.SETTINGS_PREFIX}cell_spacing", self.cell_spacing_spin.value()
        )
        self.settings.setValue(
            f"{self.SETTINGS_PREFIX}cell_radius", self.cell_radius_spin.value()
        )

        self.settings.sync()

        self.status_label.setText("Settings saved")
        self.status_label.setStyleSheet("color: #6AAB73; font-size: 10px;")

        self.iface.messageBar().pushSuccess(
            "QGIS Notebook", "Settings saved successfully!"
        )

    def _reset_defaults(self):
        """Reset all settings to defaults."""
        reply = QMessageBox.question(
            self,
            "Reset Settings",
            "Are you sure you want to reset all settings to defaults?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply != QMessageBox.Yes:
            return

        # General
        self.auto_save_check.setChecked(False)
        self.auto_save_interval.setValue(60)
        self.line_numbers_check.setChecked(True)
        self.word_wrap_check.setChecked(True)
        self.default_dir_input.clear()

        # Execution
        self.timeout_spin.setValue(0)
        self.clear_before_run_check.setChecked(True)
        self.stop_on_error_check.setChecked(True)
        self.show_exec_time_check.setChecked(True)
        self.import_qgis_check.setChecked(True)
        self.import_common_check.setChecked(True)
        self.import_numpy_check.setChecked(False)

        # Appearance
        self.color_scheme_combo.setCurrentIndex(0)
        self.code_font_combo.setCurrentIndex(0)
        self.font_size_spin.setValue(11)
        self.line_height_spin.setValue(140)
        self.cell_spacing_spin.setValue(8)
        self.cell_radius_spin.setValue(6)

        self.status_label.setText("Defaults restored (not saved)")
        self.status_label.setStyleSheet("color: #E8BF6A; font-size: 10px;")
