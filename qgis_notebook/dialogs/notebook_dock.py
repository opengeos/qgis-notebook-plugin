"""
Notebook Dock Widget for QGIS Notebook Plugin

This module provides the main dockable panel for rendering and executing
Jupyter notebooks within QGIS.
"""

import json
import os
import sys
import traceback
from io import StringIO

from qgis.PyQt.QtCore import Qt, QSettings, pyqtSignal, QTimer, QSize, QStringListModel
from qgis.PyQt.QtWidgets import (
    QDockWidget,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QTextEdit,
    QScrollArea,
    QFrame,
    QMessageBox,
    QFileDialog,
    QPlainTextEdit,
    QMenu,
    QApplication,
    QSizePolicy,
    QCompleter,
    QListView,
)
from qgis.PyQt.QtGui import (
    QFont,
    QColor,
    QTextCharFormat,
    QSyntaxHighlighter,
    QTextCursor,
)


class PythonHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for Python code."""

    def __init__(self, parent=None, colors=None):
        super().__init__(parent)
        self._rules = []

        # Use default dark colors if none provided
        if colors is None:
            colors = {
                "syntax_keyword": "#CF8E6D",
                "syntax_builtin": "#56A8F5",
                "syntax_string": "#6AAB73",
                "syntax_comment": "#7A7E85",
                "syntax_number": "#2AACB8",
                "syntax_decorator": "#BBB529",
            }

        # Keywords
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor(colors["syntax_keyword"]))
        keyword_format.setFontWeight(QFont.Bold)
        keywords = [
            "and",
            "as",
            "assert",
            "async",
            "await",
            "break",
            "class",
            "continue",
            "def",
            "del",
            "elif",
            "else",
            "except",
            "False",
            "finally",
            "for",
            "from",
            "global",
            "if",
            "import",
            "in",
            "is",
            "lambda",
            "None",
            "nonlocal",
            "not",
            "or",
            "pass",
            "raise",
            "return",
            "True",
            "try",
            "while",
            "with",
            "yield",
        ]
        for word in keywords:
            self._rules.append((rf"\b{word}\b", keyword_format))

        # Built-in functions
        builtin_format = QTextCharFormat()
        builtin_format.setForeground(QColor(colors["syntax_builtin"]))
        builtins = [
            "abs",
            "all",
            "any",
            "bin",
            "bool",
            "bytes",
            "callable",
            "chr",
            "classmethod",
            "compile",
            "complex",
            "delattr",
            "dict",
            "dir",
            "divmod",
            "enumerate",
            "eval",
            "exec",
            "filter",
            "float",
            "format",
            "frozenset",
            "getattr",
            "globals",
            "hasattr",
            "hash",
            "help",
            "hex",
            "id",
            "input",
            "int",
            "isinstance",
            "issubclass",
            "iter",
            "len",
            "list",
            "locals",
            "map",
            "max",
            "memoryview",
            "min",
            "next",
            "object",
            "oct",
            "open",
            "ord",
            "pow",
            "print",
            "property",
            "range",
            "repr",
            "reversed",
            "round",
            "set",
            "setattr",
            "slice",
            "sorted",
            "staticmethod",
            "str",
            "sum",
            "super",
            "tuple",
            "type",
            "vars",
            "zip",
        ]
        for word in builtins:
            self._rules.append((rf"\b{word}\b", builtin_format))

        # Strings
        string_format = QTextCharFormat()
        string_format.setForeground(QColor(colors["syntax_string"]))
        self._rules.append((r'"[^"\\]*(\\.[^"\\]*)*"', string_format))
        self._rules.append((r"'[^'\\]*(\\.[^'\\]*)*'", string_format))

        # Comments
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor(colors["syntax_comment"]))
        comment_format.setFontItalic(True)
        self._rules.append((r"#[^\n]*", comment_format))

        # Numbers
        number_format = QTextCharFormat()
        number_format.setForeground(QColor(colors["syntax_number"]))
        self._rules.append((r"\b\d+\.?\d*\b", number_format))

        # Decorators
        decorator_format = QTextCharFormat()
        decorator_format.setForeground(QColor(colors["syntax_decorator"]))
        self._rules.append((r"@\w+", decorator_format))

    def highlightBlock(self, text):
        """Apply syntax highlighting to the given block of text."""
        import re

        for pattern, fmt in self._rules:
            for match in re.finditer(pattern, text):
                self.setFormat(match.start(), match.end() - match.start(), fmt)


class CodeEditor(QPlainTextEdit):
    """Custom code editor with keyboard shortcuts and autocomplete."""

    execute_requested = pyqtSignal()  # Ctrl+Enter
    execute_and_advance = pyqtSignal()  # Shift+Enter
    execute_and_insert = pyqtSignal()  # Alt+Enter
    focus_changed = pyqtSignal(bool)  # True when focused, False when unfocused
    height_changed = pyqtSignal()  # Emitted when content changes height

    def __init__(self, namespace=None, parent=None):
        super().__init__(parent)
        self.setFont(QFont("Monospace", 11))
        self.namespace = namespace or {}

        # Setup autocomplete
        self.completer = QCompleter(self)
        self.completer.setWidget(self)
        self.completer.setCompletionMode(QCompleter.PopupCompletion)
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.activated.connect(self._insert_completion)

        # Autocomplete popup styling will be set when colors are available
        self.popup_colors = None

        # Track content changes for dynamic height
        self.textChanged.connect(self._on_text_changed)
        self._min_height = 38
        self._max_height = 400
        self._line_height = 22

    def _on_text_changed(self):
        """Adjust height based on content."""
        line_count = max(1, self.document().blockCount())
        new_height = min(
            self._max_height, max(self._min_height, line_count * self._line_height + 16)
        )
        if self.minimumHeight() != new_height:
            self.setMinimumHeight(new_height)
            self.setMaximumHeight(new_height)
            self.height_changed.emit()

    def set_namespace(self, namespace):
        """Set the namespace for autocomplete."""
        self.namespace = namespace

    def set_popup_colors(self, colors):
        """Set the colors for the autocomplete popup."""
        popup = self.completer.popup()
        popup.setStyleSheet(
            f"""
            QListView {{
                background-color: {colors['bg_cell']};
                color: {colors['text_primary']};
                border: 1px solid {colors['border_focus']};
                border-radius: 4px;
                font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                font-size: 11px;
            }}
            QListView::item:selected {{
                background-color: {colors['bg_button_primary']};
                color: {colors['text_button']};
            }}
            QListView::item:hover {{
                background-color: {colors['bg_button']};
            }}
        """
        )

    def _get_completions(self, obj_name):
        """Get completions for an object."""
        try:
            # Try to evaluate the object name in the namespace
            if "." in obj_name:
                parts = obj_name.rsplit(".", 1)
                base = parts[0]
                obj = eval(base, self.namespace)
            else:
                obj = eval(obj_name, self.namespace)

            # Get attributes
            attrs = dir(obj)
            # Filter out private attributes unless user typed underscore
            return [a for a in attrs if not a.startswith("_")]
        except:
            return []

    def _get_word_before_cursor(self):
        """Get the word/expression before the cursor for completion."""
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.StartOfBlock, QTextCursor.KeepAnchor)
        line = cursor.selectedText()

        # Find the expression to complete (handles obj.method.attr patterns)
        word = ""
        for i in range(len(line) - 1, -1, -1):
            char = line[i]
            if char.isalnum() or char in "._":
                word = char + word
            else:
                break
        return word

    def _insert_completion(self, completion):
        """Insert the selected completion."""
        cursor = self.textCursor()

        # Get the partial text that user already typed
        prefix = self.completer.completionPrefix()

        # Move cursor back by the length of the prefix and select it
        for _ in range(len(prefix)):
            cursor.movePosition(QTextCursor.Left, QTextCursor.KeepAnchor)

        # Replace the prefix with the full completion
        cursor.insertText(completion)
        self.setTextCursor(cursor)

    def focusInEvent(self, event):
        """Handle focus in event."""
        super().focusInEvent(event)
        self.focus_changed.emit(True)

    def focusOutEvent(self, event):
        """Handle focus out event."""
        super().focusOutEvent(event)
        self.focus_changed.emit(False)

    def keyPressEvent(self, event):
        """Handle key press events."""
        # If completer popup is visible, handle its keys
        if self.completer.popup().isVisible():
            if event.key() in (Qt.Key_Enter, Qt.Key_Return, Qt.Key_Tab):
                # Accept the completion
                index = self.completer.popup().currentIndex()
                if index.isValid():
                    self.completer.activated.emit(
                        self.completer.completionModel().data(index)
                    )
                self.completer.popup().hide()
                return
            elif event.key() == Qt.Key_Escape:
                self.completer.popup().hide()
                return
            elif event.key() in (Qt.Key_Up, Qt.Key_Down):
                # Let completer handle navigation - pass event to popup
                self.completer.popup().keyPressEvent(event)
                return
            elif event.key() == Qt.Key_Backspace:
                # Handle backspace - let it through, then update completions
                super().keyPressEvent(event)
                self._update_completions()
                return

        # Ctrl+Enter: Execute cell
        if event.key() == Qt.Key_Return and event.modifiers() == Qt.ControlModifier:
            self.completer.popup().hide()
            self.execute_requested.emit()
            return
        # Shift+Enter: Execute and move to next cell
        if event.key() == Qt.Key_Return and event.modifiers() == Qt.ShiftModifier:
            self.completer.popup().hide()
            self.execute_and_advance.emit()
            return
        # Alt+Enter: Execute and insert new cell below
        if event.key() == Qt.Key_Return and event.modifiers() == Qt.AltModifier:
            self.completer.popup().hide()
            self.execute_and_insert.emit()
            return

        # Ctrl+Space: Trigger autocomplete manually
        if event.key() == Qt.Key_Space and event.modifiers() == Qt.ControlModifier:
            self._show_completions()
            return

        super().keyPressEvent(event)

        # Trigger autocomplete after typing a dot
        if event.text() == ".":
            self._show_completions()
        # Update completions as user types (filter the list)
        elif self.completer.popup().isVisible() and (
            event.text().isalnum() or event.text() == "_"
        ):
            self._update_completions()

    def _update_completions(self):
        """Update the completion prefix as user types more characters."""
        word = self._get_word_before_cursor()

        if "." in word:
            prefix = word.rsplit(".", 1)[1]
        else:
            prefix = word

        # Update the prefix to filter completions
        self.completer.setCompletionPrefix(prefix)

        # If no completions match, hide popup
        if self.completer.completionCount() == 0:
            self.completer.popup().hide()
        else:
            # Select the first matching item
            self.completer.popup().setCurrentIndex(
                self.completer.completionModel().index(0, 0)
            )

    def _show_completions(self):
        """Show the autocomplete popup."""
        word = self._get_word_before_cursor()

        if "." in word:
            # Get completions for the object before the dot
            base = word.rsplit(".", 1)[0]
            prefix = word.rsplit(".", 1)[1] if len(word.rsplit(".", 1)) > 1 else ""
            completions = self._get_completions(base)
        else:
            # Get completions from namespace
            completions = [k for k in self.namespace.keys() if not k.startswith("_")]
            prefix = word

        if not completions:
            self.completer.popup().hide()
            return

        # Set completions
        model = QStringListModel(sorted(completions))
        self.completer.setModel(model)
        self.completer.setCompletionPrefix(prefix)

        # Position the popup below the current line (not blocking the cursor)
        cursor_rect = self.cursorRect()
        # Move the rect down by the line height so popup appears below the text
        cursor_rect.setTop(cursor_rect.bottom() + 10)
        cursor_rect.setHeight(1)
        cursor_rect.setWidth(300)
        self.completer.complete(cursor_rect)


class MarkdownEditor(QPlainTextEdit):
    """Custom markdown editor with keyboard shortcuts and dynamic height."""

    finish_editing = pyqtSignal()  # Escape or Ctrl+Enter
    focus_changed = pyqtSignal(bool)  # True when focused, False when unfocused
    height_changed = pyqtSignal()  # Emitted when content changes height

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFont(QFont("Monospace", 11))

        # Track content changes for dynamic height
        self.textChanged.connect(self._on_text_changed)
        self._min_height = 38
        self._max_height = 300
        self._line_height = 22

    def _on_text_changed(self):
        """Adjust height based on content."""
        line_count = max(1, self.document().blockCount())
        new_height = min(
            self._max_height, max(self._min_height, line_count * self._line_height + 16)
        )
        if self.minimumHeight() != new_height:
            self.setMinimumHeight(new_height)
            self.setMaximumHeight(new_height)
            self.height_changed.emit()

    def focusInEvent(self, event):
        """Handle focus in event."""
        super().focusInEvent(event)
        self.focus_changed.emit(True)

    def focusOutEvent(self, event):
        """Handle focus out event."""
        super().focusOutEvent(event)
        self.focus_changed.emit(False)

    def keyPressEvent(self, event):
        """Handle key press events."""
        # Escape or Ctrl+Enter: Finish editing
        if event.key() == Qt.Key_Escape:
            self.finish_editing.emit()
            return
        if event.key() == Qt.Key_Return and event.modifiers() == Qt.ControlModifier:
            self.finish_editing.emit()
            return
        super().keyPressEvent(event)


class NotebookCellWidget(QFrame):
    """Widget representing a single notebook cell."""

    executed = pyqtSignal(int)  # cell index
    execute_and_advance = pyqtSignal(int)  # cell index
    execute_and_insert = pyqtSignal(
        int
    )  # cell index - execute and create new cell below
    delete_requested = pyqtSignal(int)  # cell index
    add_cell_above = pyqtSignal(int, str)  # cell index, cell type
    add_cell_below = pyqtSignal(int, str)  # cell index, cell type
    change_type_requested = pyqtSignal(int, str)  # cell index, new type
    cell_focused = pyqtSignal(int)  # emitted when cell gains focus
    content_changed = pyqtSignal()  # emitted when cell content is modified

    def __init__(self, cell_data, cell_index, colors, parent=None):
        super().__init__(parent)
        self.cell_data = cell_data
        self.cell_index = cell_index
        self.cell_type = cell_data.get("cell_type", "code")
        self.colors = colors
        self._editing_markdown = False
        self._is_focused = False

        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self._update_style()

        self._setup_ui()
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def _update_style(self):
        """Update the cell's border style based on focus state."""
        if self._is_focused:
            self.setStyleSheet(
                f"""
                NotebookCellWidget {{
                    background-color: {self.colors['bg_cell']};
                    border: 2px solid {self.colors['border_focus']};
                    border-radius: 6px;
                    margin: 4px;
                    padding: 8px;
                }}
            """
            )
        else:
            self.setStyleSheet(
                f"""
                NotebookCellWidget {{
                    background-color: {self.colors['bg_cell']};
                    border: 1px solid {self.colors['border_primary']};
                    border-radius: 6px;
                    margin: 4px;
                    padding: 8px;
                }}
            """
            )

    def set_focused(self, focused):
        """Set the focus state and update visual style."""
        if self._is_focused != focused:
            self._is_focused = focused
            self._update_style()
            if focused:
                self.cell_focused.emit(self.cell_index)

    def _clear_cell_output(self):
        """Clear the output of this cell."""
        if self.cell_type == "code" and hasattr(self, "output_area"):
            self.output_area.clear()
            self.output_area.setVisible(False)

    def _show_context_menu(self, pos):
        """Show context menu for cell operations."""
        menu = QMenu(self)

        # Add cell actions
        add_code_above = menu.addAction("Add Code Cell Above")
        add_code_above.triggered.connect(
            lambda: self.add_cell_above.emit(self.cell_index, "code")
        )

        add_md_above = menu.addAction("Add Markdown Cell Above")
        add_md_above.triggered.connect(
            lambda: self.add_cell_above.emit(self.cell_index, "markdown")
        )

        menu.addSeparator()

        add_code_below = menu.addAction("Add Code Cell Below")
        add_code_below.triggered.connect(
            lambda: self.add_cell_below.emit(self.cell_index, "code")
        )

        add_md_below = menu.addAction("Add Markdown Cell Below")
        add_md_below.triggered.connect(
            lambda: self.add_cell_below.emit(self.cell_index, "markdown")
        )

        menu.addSeparator()

        # Clear output action (only for code cells)
        if self.cell_type == "code":
            clear_output_action = menu.addAction("Clear Output")
            clear_output_action.triggered.connect(self._clear_cell_output)
            menu.addSeparator()

        # Change cell type
        if self.cell_type == "code":
            to_markdown = menu.addAction("Convert to Markdown")
            to_markdown.triggered.connect(
                lambda: self.change_type_requested.emit(self.cell_index, "markdown")
            )
        else:
            to_code = menu.addAction("Convert to Code")
            to_code.triggered.connect(
                lambda: self.change_type_requested.emit(self.cell_index, "code")
            )

        menu.addSeparator()

        # Delete action
        delete_action = menu.addAction("Delete Cell")
        delete_action.triggered.connect(
            lambda: self.delete_requested.emit(self.cell_index)
        )

        menu.exec_(self.mapToGlobal(pos))

    def _setup_ui(self):
        """Set up the cell UI."""
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(8, 8, 8, 8)
        self.layout.setSpacing(4)

        # Cell header
        header_layout = QHBoxLayout()

        # Cell type indicator
        self.index_label = QLabel(f"[{self.cell_index + 1}]")
        self.index_label.setStyleSheet(
            f"color: {self.colors['text_primary']}; font-weight: bold; font-size: 11px;"
        )
        header_layout.addWidget(self.index_label)

        self.cell_type_label = QLabel(self.cell_type.upper())
        cell_type_color = (
            self.colors["cell_type_code"]
            if self.cell_type == "code"
            else self.colors["cell_type_markdown"]
        )
        self.cell_type_label.setStyleSheet(
            f"color: {cell_type_color}; "
            f"font-size: 10px; padding: 2px 6px; background: {self.colors['bg_button']}; border-radius: 3px;"
        )
        header_layout.addWidget(self.cell_type_label)
        header_layout.addStretch()

        # Run button for code cells
        if self.cell_type == "code":
            self.run_btn = QPushButton("Run")
            self.run_btn.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: {self.colors['bg_button_primary']};
                    color: #FFFFFF;
                    border: none;
                    padding: 4px 10px;
                    border-radius: 3px;
                    font-size: 11px;
                }}
                QPushButton:hover {{
                    background-color: {self.colors['bg_button_primary_hover']};
                }}
                QPushButton:pressed {{
                    background-color: {self.colors['bg_button_primary']};
                }}
            """
            )
            self.run_btn.clicked.connect(lambda: self.executed.emit(self.cell_index))
            header_layout.addWidget(self.run_btn)

        self.layout.addLayout(header_layout)

        # Cell content
        source = self.cell_data.get("source", [])
        if isinstance(source, list):
            source = "".join(source)
        # Strip trailing newlines while preserving other trailing whitespace
        source = source.rstrip("\n")

        if self.cell_type == "code":
            self._setup_code_cell(source)
        else:  # markdown
            self._setup_markdown_cell(source)

    def _setup_code_cell(self, source):
        """Set up a code cell."""
        self.source_edit = CodeEditor()
        self.source_edit.setStyleSheet(
            f"""
            QPlainTextEdit {{
                background-color: {self.colors['bg_code']};
                color: {self.colors['text_code']};
                border: 1px solid {self.colors['border_primary']};
                border-radius: 4px;
                padding: 8px;
                font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            }}
        """
        )
        # Set up syntax highlighting
        self.highlighter = PythonHighlighter(self.source_edit.document(), self.colors)

        # Set autocomplete popup colors
        self.source_edit.set_popup_colors(self.colors)

        # Connect keyboard shortcuts
        self.source_edit.execute_requested.connect(
            lambda: self.executed.emit(self.cell_index)
        )
        self.source_edit.execute_and_advance.connect(
            lambda: self.execute_and_advance.emit(self.cell_index)
        )
        self.source_edit.execute_and_insert.connect(
            lambda: self.execute_and_insert.emit(self.cell_index)
        )

        # Connect focus tracking
        self.source_edit.focus_changed.connect(self.set_focused)

        # Connect content change tracking
        self.source_edit.textChanged.connect(self.content_changed.emit)

        # Set initial height based on content (dynamic height handled by CodeEditor)
        line_count = max(1, min(20, source.count("\n") + 1))
        # 22 is the approximate line height in pixels; 16 adds vertical padding/margins
        initial_height = line_count * 22 + 16
        self.source_edit.setMinimumHeight(initial_height)
        self.source_edit.setMaximumHeight(initial_height)

        # Set the text after height setup
        self.source_edit.setPlainText(source)
        self.layout.addWidget(self.source_edit)

        # Output area
        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        self.output_area.setFont(QFont("Consolas, Monaco, Courier New, monospace", 10))
        self.output_area.setStyleSheet(
            f"""
            QTextEdit {{
                background-color: {self.colors['bg_output']};
                color: {self.colors['text_output']};
                border: 1px solid {self.colors['border_primary']};
                border-radius: 4px;
                padding: 8px;
            }}
        """
        )
        # Start hidden, height will be adjusted dynamically when output is set
        self.output_area.setVisible(False)
        self.layout.addWidget(self.output_area)

        # Show existing outputs
        outputs = self.cell_data.get("outputs", [])
        if outputs:
            self._display_outputs(outputs)

    def set_namespace(self, namespace):
        """Set the namespace for autocomplete in code cells."""
        if self.cell_type == "code" and hasattr(self, "source_edit"):
            self.source_edit.set_namespace(namespace)

    def _setup_markdown_cell(self, source):
        """Set up a markdown cell."""
        self._source = source

        # Rendered markdown view (default)
        self.markdown_label = QLabel()
        self.markdown_label.setWordWrap(True)
        self.markdown_label.setTextFormat(Qt.RichText)
        self.markdown_label.setStyleSheet(
            f"""
            QLabel {{
                color: {self.colors['text_primary']};
                padding: 8px;
                line-height: 1.5;
                background-color: {self.colors['bg_code']};
                border: 1px solid {self.colors['border_primary']};
                border-radius: 4px;
            }}
        """
        )
        self.markdown_label.setMinimumHeight(40)
        # Convert markdown to rich text (simple conversion)
        html = self._markdown_to_html(source)
        self.markdown_label.setText(html)
        self.markdown_label.mouseDoubleClickEvent = self._start_markdown_edit
        self.layout.addWidget(self.markdown_label)

        # Markdown editor (hidden by default)
        self.markdown_edit = MarkdownEditor()
        self.markdown_edit.setStyleSheet(
            f"""
            QPlainTextEdit {{
                background-color: {self.colors['bg_code']};
                color: {self.colors['text_code']};
                border: 1px solid {self.colors['border_focus']};
                border-radius: 4px;
                padding: 8px;
                font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            }}
        """
        )
        self.markdown_edit.finish_editing.connect(self._finish_markdown_edit)
        self.markdown_edit.focus_changed.connect(self.set_focused)

        # Connect content change tracking
        self.markdown_edit.textChanged.connect(self.content_changed.emit)

        # Set initial height based on content (dynamic height handled by MarkdownEditor)
        line_count = max(1, min(15, source.count("\n") + 1))
        initial_height = line_count * 22 + 16
        self.markdown_edit.setMinimumHeight(initial_height)
        self.markdown_edit.setMaximumHeight(initial_height)

        # Set the text after height setup
        self.markdown_edit.setPlainText(source)
        self.markdown_edit.setVisible(False)
        self.layout.addWidget(self.markdown_edit)

    def _start_markdown_edit(self, event):
        """Start editing markdown cell."""
        if self.cell_type != "markdown":
            return
        self._editing_markdown = True
        self.markdown_label.setVisible(False)
        self.markdown_edit.setVisible(True)
        self.markdown_edit.setFocus()
        # Update height based on content
        content = self.markdown_edit.toPlainText()
        line_count = max(1, min(15, content.count("\n") + 1))
        self.markdown_edit.setFixedHeight(line_count * 22 + 16)

    def _finish_markdown_edit(self):
        """Finish editing markdown and render."""
        if self.cell_type != "markdown":
            return
        self._editing_markdown = False
        self._source = self.markdown_edit.toPlainText()
        html = self._markdown_to_html(self._source)
        self.markdown_label.setText(html)
        self.markdown_edit.setVisible(False)
        self.markdown_label.setVisible(True)

    def _markdown_to_html(self, text):
        """Convert markdown to simple HTML."""
        import re

        if not text.strip():
            return f"<i style='color:{self.colors['text_tertiary']};'>Double-click to edit markdown...</i>"

        # Headers - use margin:0 to avoid extra spacing
        text = re.sub(
            r"^######\s+(.+)$",
            r"<h6 style='margin:0.3em 0;'>\1</h6>",
            text,
            flags=re.MULTILINE,
        )
        text = re.sub(
            r"^#####\s+(.+)$",
            r"<h5 style='margin:0.3em 0;'>\1</h5>",
            text,
            flags=re.MULTILINE,
        )
        text = re.sub(
            r"^####\s+(.+)$",
            r"<h4 style='margin:0.3em 0;'>\1</h4>",
            text,
            flags=re.MULTILINE,
        )
        text = re.sub(
            r"^###\s+(.+)$",
            rf"<h3 style='color:{self.colors['header_accent']};margin:0.3em 0;'>\1</h3>",
            text,
            flags=re.MULTILINE,
        )
        text = re.sub(
            r"^##\s+(.+)$",
            rf"<h2 style='color:{self.colors['header_accent']};margin:0.3em 0;'>\1</h2>",
            text,
            flags=re.MULTILINE,
        )
        text = re.sub(
            r"^#\s+(.+)$",
            rf"<h1 style='color:{self.colors['header_accent']};margin:0.3em 0;'>\1</h1>",
            text,
            flags=re.MULTILINE,
        )

        # Bold and italic
        text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
        text = re.sub(r"\*(.+?)\*", r"<i>\1</i>", text)
        text = re.sub(r"__(.+?)__", r"<b>\1</b>", text)
        text = re.sub(r"_(.+?)_", r"<i>\1</i>", text)

        # Code
        text = re.sub(
            r"`(.+?)`",
            rf"<code style='background:{self.colors['bg_button']};padding:2px 4px;border-radius:3px;'>\1</code>",
            text,
        )

        # Links
        text = re.sub(
            r"\[(.+?)\]\((.+?)\)",
            rf"<a href='\2' style='color:{self.colors['text_primary']};'>\1</a>",
            text,
        )

        # Lists
        text = re.sub(r"^\s*[-*]\s+(.+)$", r"&bull; \1<br>", text, flags=re.MULTILINE)
        text = re.sub(r"^\s*\d+\.\s+(.+)$", r"&rarr; \1<br>", text, flags=re.MULTILINE)

        # Remove newlines after closing heading tags (they add extra space)
        text = re.sub(r"(</h[1-6]>)\n+", r"\1", text)

        # Convert remaining line breaks
        text = text.replace("\n\n", "<br><br>")
        text = text.replace("\n", "<br>")

        return text

    def _display_outputs(self, outputs):
        """Display cell outputs."""
        output_text = []
        for output in outputs:
            output_type = output.get("output_type", "")

            if output_type == "stream":
                text = output.get("text", [])
                if isinstance(text, list):
                    text = "".join(text)
                output_text.append(text)

            elif output_type in ("execute_result", "display_data"):
                data = output.get("data", {})
                if "text/plain" in data:
                    text = data["text/plain"]
                    if isinstance(text, list):
                        text = "".join(text)
                    output_text.append(text)

            elif output_type == "error":
                ename = output.get("ename", "Error")
                evalue = output.get("evalue", "")
                output_text.append(
                    f"<span style='color:{self.colors['text_error']};'>{ename}: {evalue}</span>"
                )

        if output_text:
            self.output_area.clear()
            self.output_area.setHtml("<br>".join(output_text))
            self.output_area.setVisible(True)
            # Adjust height based on content
            doc_height = self.output_area.document().size().height()
            self.output_area.setFixedHeight(min(200, max(40, int(doc_height) + 16)))

    def get_source(self):
        """Get the current source code from the cell."""
        if self.cell_type == "code":
            return self.source_edit.toPlainText()
        elif self.cell_type == "markdown":
            if self._editing_markdown:
                return self.markdown_edit.toPlainText()
            return self._source
        return ""

    def set_output(self, result, stdout, stderr):
        """Set the output of the cell after execution."""
        # Clear previous output first
        self.output_area.clear()

        output_parts = []

        if stdout:
            # Strip trailing newline to avoid extra blank line
            output_parts.append(stdout.rstrip("\n"))

        if result is not None:
            output_parts.append(
                f"<span style='color:{self.colors['text_output']};'>{repr(result)}</span>"
            )

        if stderr:
            output_parts.append(
                f"<span style='color:{self.colors['text_error']};'>{stderr}</span>"
            )

        if output_parts:
            self.output_area.setHtml("<pre>" + "<br>".join(output_parts) + "</pre>")
            self.output_area.setVisible(True)
            # Adjust height based on content
            doc_height = self.output_area.document().size().height()
            self.output_area.setFixedHeight(min(200, max(40, int(doc_height) + 16)))
        else:
            self.output_area.setVisible(False)

    def set_running(self, running):
        """Update UI to show running state."""
        if self.cell_type == "code":
            if running:
                self.run_btn.setText("Running...")
                self.run_btn.setEnabled(False)
            else:
                self.run_btn.setText("Run")
                self.run_btn.setEnabled(True)

    def update_index(self, new_index):
        """Update the cell index."""
        self.cell_index = new_index
        self.index_label.setText(f"[{new_index + 1}]")

    def focus_editor(self):
        """Set focus to the cell's editor."""
        if self.cell_type == "code":
            self.source_edit.setFocus()
        elif self.cell_type == "markdown":
            self._start_markdown_edit(None)


class NotebookDockWidget(QDockWidget):
    """A dockable panel for rendering and executing Jupyter notebooks."""

    def __init__(self, iface, parent=None):
        """Initialize the notebook dock widget.

        Args:
            iface: QGIS interface instance.
            parent: Parent widget.
        """
        super().__init__("Jupyter Notebook", parent)
        self.iface = iface
        self.settings = QSettings()

        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.setMinimumWidth(450)

        # Notebook state
        self.notebook_path = None
        self.notebook_data = None
        self.cell_widgets = []
        self._focused_cell_index = -1  # Track currently focused cell
        self._is_dirty = False  # Track unsaved changes

        # Execution queue for Run All
        self._execution_queue = []
        self._is_running_all = False

        # Python namespace for execution
        self.namespace = {
            "__name__": "__main__",
            "__doc__": None,
        }
        # Pre-import common modules
        self._setup_namespace()

        # Load theme colors
        self._load_theme()

        self._setup_ui()

    def _setup_namespace(self):
        """Set up the Python namespace with common modules."""
        # Import QGIS modules and iface
        try:
            import qgis.core
            import qgis.gui
            from qgis.utils import iface

            self.namespace["qgis"] = __import__("qgis")
            self.namespace["QgsProject"] = qgis.core.QgsProject
            self.namespace["iface"] = iface

            # Also add commonly used QGIS classes
            self.namespace["QgsVectorLayer"] = qgis.core.QgsVectorLayer
            self.namespace["QgsRasterLayer"] = qgis.core.QgsRasterLayer
            self.namespace["QgsGeometry"] = qgis.core.QgsGeometry
            self.namespace["QgsFeature"] = qgis.core.QgsFeature
            self.namespace["QgsPointXY"] = qgis.core.QgsPointXY
            self.namespace["QgsCoordinateReferenceSystem"] = (
                qgis.core.QgsCoordinateReferenceSystem
            )
            self.namespace["QgsField"] = qgis.core.QgsField
            self.namespace["QgsFields"] = qgis.core.QgsFields
            self.namespace["QgsWkbTypes"] = qgis.core.QgsWkbTypes
            self.namespace["QgsMapLayerType"] = qgis.core.QgsMapLayerType
            self.namespace["QgsProcessing"] = qgis.core.QgsProcessing
            self.namespace["QgsApplication"] = qgis.core.QgsApplication
        except ImportError:
            pass

        # Import processing module
        try:
            import processing

            self.namespace["processing"] = processing
        except ImportError:
            pass

        # Import common modules
        try:
            import os
            import sys
            import json
            import math

            self.namespace["os"] = os
            self.namespace["sys"] = sys
            self.namespace["json"] = json
            self.namespace["math"] = math
        except ImportError:
            pass

        # Try importing common data science libraries
        try:
            import numpy as np

            self.namespace["np"] = np
            self.namespace["numpy"] = np
        except ImportError:
            pass

        try:
            import pandas as pd

            self.namespace["pd"] = pd
            self.namespace["pandas"] = pd
        except ImportError:
            pass

    def _load_theme(self):
        """Load theme colors from settings."""
        # Get color scheme index from settings (0=Dark, 1=Light, 2=Monokai, 3=Solarized Dark)
        color_scheme = self.settings.value("QGISNotebook/color_scheme", 0, type=int)

        # Define color palettes for each theme
        if color_scheme == 1:  # Light
            self.colors = {
                # Backgrounds
                "bg_primary": "#FFFFFF",  # Main background
                "bg_secondary": "#F5F5F5",  # Secondary background
                "bg_tertiary": "#E8E8E8",  # Tertiary background
                "bg_cell": "#FAFAFA",  # Cell background
                "bg_code": "#F8F8F8",  # Code editor background
                "bg_output": "#F5F5F5",  # Output background
                "bg_button": "#D0D0D0",  # Button background (darker for better contrast)
                "bg_button_hover": "#B0B0B0",  # Button hover
                "bg_button_primary": "#0078D4",  # Primary button
                "bg_button_primary_hover": "#106EBE",  # Primary button hover
                "bg_button_success": "#107C10",  # Success button
                "bg_button_success_hover": "#0E6B0E",  # Success button hover
                "bg_button_danger": "#D13438",  # Danger button
                "bg_button_danger_hover": "#A72E2E",  # Danger button hover
                # Borders
                "border_primary": "#CCCCCC",  # Primary border
                "border_secondary": "#E0E0E0",  # Secondary border
                "border_focus": "#0078D4",  # Focus border
                # Text
                "text_primary": "#000000",  # Primary text
                "text_secondary": "#666666",  # Secondary text
                "text_tertiary": "#999999",  # Tertiary text
                "text_code": "#000000",  # Code text
                "text_output": "#333333",  # Output text
                "text_error": "#E81123",  # Error text
                "text_success": "#107C10",  # Success text
                "text_warning": "#FF8C00",  # Warning text
                "text_button": "#000000",  # Button text (dark for light theme)
                # Syntax highlighting (light theme)
                "syntax_keyword": "#0000FF",  # Keywords
                "syntax_builtin": "#267F99",  # Built-ins
                "syntax_string": "#A31515",  # Strings
                "syntax_comment": "#008000",  # Comments
                "syntax_number": "#098658",  # Numbers
                "syntax_decorator": "#795E26",  # Decorators
                # UI elements
                "header_accent": "#0078D4",  # Header accent color
                "cell_type_code": "#0078D4",  # Code cell label
                "cell_type_markdown": "#107C10",  # Markdown cell label
                "scrollbar_bg": "#F5F5F5",  # Scrollbar background
                "scrollbar_handle": "#CCCCCC",  # Scrollbar handle
                "scrollbar_handle_hover": "#999999",  # Scrollbar handle hover
            }
        elif color_scheme == 2:  # Monokai
            self.colors = {
                # Backgrounds
                "bg_primary": "#272822",
                "bg_secondary": "#2D2E27",
                "bg_tertiary": "#3E3D32",
                "bg_cell": "#2D2E27",
                "bg_code": "#272822",
                "bg_output": "#2D2E27",
                "bg_button": "#49483E",  # Darker for better contrast
                "bg_button_hover": "#5A594E",  # Lighter hover
                "bg_button_primary": "#66D9EF",
                "bg_button_primary_hover": "#7EE0F5",
                "bg_button_success": "#A6E22E",
                "bg_button_success_hover": "#B8E844",
                "bg_button_danger": "#F92672",
                "bg_button_danger_hover": "#FF3D86",
                # Borders
                "border_primary": "#49483E",
                "border_secondary": "#3E3D32",
                "border_focus": "#66D9EF",
                # Text
                "text_primary": "#F8F8F2",
                "text_secondary": "#BCBCBC",
                "text_tertiary": "#75715E",
                "text_code": "#F8F8F2",
                "text_output": "#F8F8F2",
                "text_error": "#F92672",
                "text_success": "#A6E22E",
                "text_warning": "#E6DB74",
                "text_button": "#272822",
                # Syntax highlighting
                "syntax_keyword": "#F92672",
                "syntax_builtin": "#66D9EF",
                "syntax_string": "#E6DB74",
                "syntax_comment": "#75715E",
                "syntax_number": "#AE81FF",
                "syntax_decorator": "#A6E22E",
                # UI elements
                "header_accent": "#E6DB74",
                "cell_type_code": "#F92672",
                "cell_type_markdown": "#A6E22E",
                "scrollbar_bg": "#2D2E27",
                "scrollbar_handle": "#49483E",
                "scrollbar_handle_hover": "#75715E",
            }
        elif color_scheme == 3:  # Solarized Dark
            self.colors = {
                # Backgrounds
                "bg_primary": "#002B36",
                "bg_secondary": "#073642",
                "bg_tertiary": "#0E4C5A",
                "bg_cell": "#073642",
                "bg_code": "#002B36",
                "bg_output": "#073642",
                "bg_button": "#0E4C5A",
                "bg_button_hover": "#14596B",
                "bg_button_primary": "#268BD2",
                "bg_button_primary_hover": "#3C9FE6",
                "bg_button_success": "#859900",
                "bg_button_success_hover": "#9BAD14",
                "bg_button_danger": "#DC322F",
                "bg_button_danger_hover": "#F04643",
                # Borders
                "border_primary": "#0E4C5A",
                "border_secondary": "#073642",
                "border_focus": "#268BD2",
                # Text
                "text_primary": "#93A1A1",
                "text_secondary": "#839496",
                "text_tertiary": "#586E75",
                "text_code": "#93A1A1",
                "text_output": "#93A1A1",
                "text_error": "#DC322F",
                "text_success": "#859900",
                "text_warning": "#B58900",
                "text_button": "#FDF6E3",
                # Syntax highlighting
                "syntax_keyword": "#CB4B16",
                "syntax_builtin": "#268BD2",
                "syntax_string": "#2AA198",
                "syntax_comment": "#586E75",
                "syntax_number": "#6C71C4",
                "syntax_decorator": "#B58900",
                # UI elements
                "header_accent": "#B58900",
                "cell_type_code": "#CB4B16",
                "cell_type_markdown": "#859900",
                "scrollbar_bg": "#073642",
                "scrollbar_handle": "#0E4C5A",
                "scrollbar_handle_hover": "#586E75",
            }
        else:  # Default: Dark (Darcula) - index 0
            self.colors = {
                # Backgrounds
                "bg_primary": "#1E1F22",
                "bg_secondary": "#2B2D30",
                "bg_tertiary": "#252629",
                "bg_cell": "#2B2D30",
                "bg_code": "#1E1F22",
                "bg_output": "#1E1F22",
                "bg_button": "#3C3F41",
                "bg_button_hover": "#4E5254",
                "bg_button_primary": "#365880",
                "bg_button_primary_hover": "#4A6FA5",
                "bg_button_success": "#3C5F41",
                "bg_button_success_hover": "#4A7A50",
                "bg_button_danger": "#5F3C41",
                "bg_button_danger_hover": "#7A4A50",
                # Borders
                "border_primary": "#3C3F41",
                "border_secondary": "#3C3F41",
                "border_focus": "#4E94CE",
                # Text
                "text_primary": "#BCBEC4",
                "text_secondary": "#6E7274",
                "text_tertiary": "#4E5254",
                "text_code": "#BCBEC4",
                "text_output": "#A9B7C6",
                "text_error": "#FF6B68",
                "text_success": "#6AAB73",
                "text_warning": "#E8BF6A",
                "text_button": "#FFFFFF",
                # Syntax highlighting
                "syntax_keyword": "#CF8E6D",
                "syntax_builtin": "#56A8F5",
                "syntax_string": "#6AAB73",
                "syntax_comment": "#7A7E85",
                "syntax_number": "#2AACB8",
                "syntax_decorator": "#BBB529",
                # UI elements
                "header_accent": "#E8BF6A",
                "cell_type_code": "#CF8E6D",
                "cell_type_markdown": "#6AAB73",
                "scrollbar_bg": "#2B2D30",
                "scrollbar_handle": "#4E5254",
                "scrollbar_handle_hover": "#6E7274",
            }

    def _update_cell_namespaces(self):
        """Update the namespace in all cell widgets for autocomplete."""
        for cell_widget in self.cell_widgets:
            if isinstance(cell_widget, NotebookCellWidget):
                cell_widget.set_namespace(self.namespace)

    def _mark_dirty(self):
        """Mark the notebook as having unsaved changes."""
        self._is_dirty = True

    def _check_unsaved_changes(self):
        """Check for unsaved changes and prompt user to save.

        Returns:
            True if it's safe to proceed (saved, discarded, or no changes)
            False if user cancelled the operation
        """
        if not self._is_dirty:
            return True

        # Show confirmation dialog
        reply = QMessageBox.question(
            self,
            "Unsaved Changes",
            "The current notebook has unsaved changes.\n\nDo you want to save before continuing?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
            QMessageBox.Save,
        )

        if reply == QMessageBox.Save:
            saved = self._save_notebook()
            return bool(saved)
        elif reply == QMessageBox.Discard:
            return True
        else:  # Cancel
            return False

    def _create_toolbar_button(self, text, button_type="normal"):
        """Create a styled toolbar button.

        Args:
            text: Button text
            button_type: Type of button (normal, primary, success, danger)
        """
        btn = QPushButton(text)
        btn.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        btn.setMinimumHeight(28)

        # Determine colors based on button type
        if button_type == "primary":
            bg_color = self.colors["bg_button_primary"]
            hover_color = self.colors["bg_button_primary_hover"]
            text_color = "#FFFFFF"  # Always white for colored buttons
        elif button_type == "success":
            bg_color = self.colors["bg_button_success"]
            hover_color = self.colors["bg_button_success_hover"]
            text_color = "#FFFFFF"  # Always white for colored buttons
        elif button_type == "danger":
            bg_color = self.colors["bg_button_danger"]
            hover_color = self.colors["bg_button_danger_hover"]
            text_color = "#FFFFFF"  # Always white for colored buttons
        else:  # normal
            bg_color = self.colors["bg_button"]
            hover_color = self.colors["bg_button_hover"]
            text_color = self.colors["text_button"]  # Use theme-specific color

        btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {bg_color};
                color: {text_color};
                border: none;
                padding: 5px 15px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
            QPushButton:pressed {{
                background-color: {bg_color};
            }}
            QPushButton:disabled {{
                background-color: {self.colors["bg_button"]};
                color: {self.colors["text_tertiary"]};
            }}
        """
        )
        return btn

    def _setup_ui(self):
        """Set up the dock widget UI."""
        main_widget = QWidget()
        self.setWidget(main_widget)

        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Main toolbar
        toolbar_widget = QWidget()
        toolbar_widget.setStyleSheet(
            f"background-color: {self.colors['bg_secondary']};"
        )
        toolbar_widget.setMinimumHeight(44)
        toolbar_layout = QHBoxLayout(toolbar_widget)
        toolbar_layout.setContentsMargins(8, 8, 8, 8)
        toolbar_layout.setSpacing(8)

        # Open button
        self.open_btn = self._create_toolbar_button("Open", "primary")
        self.open_btn.clicked.connect(self._open_notebook)
        toolbar_layout.addWidget(self.open_btn)

        # Run all button
        self.run_all_btn = self._create_toolbar_button("Run All", "success")
        self.run_all_btn.clicked.connect(self._run_all_cells)
        toolbar_layout.addWidget(self.run_all_btn)

        # Clear outputs button
        self.clear_btn = self._create_toolbar_button("Clear Outputs", "danger")
        self.clear_btn.clicked.connect(self._clear_outputs)
        toolbar_layout.addWidget(self.clear_btn)

        # Save button
        self.save_btn = self._create_toolbar_button("Save", "normal")
        self.save_btn.clicked.connect(self._save_notebook)
        toolbar_layout.addWidget(self.save_btn)

        # New notebook button
        self.new_btn = self._create_toolbar_button("New", "normal")
        self.new_btn.clicked.connect(self._new_notebook)
        toolbar_layout.addWidget(self.new_btn)

        toolbar_layout.addStretch()
        main_layout.addWidget(toolbar_widget)

        # Second toolbar for cell operations
        cell_toolbar_widget = QWidget()
        cell_toolbar_widget.setStyleSheet(
            f"background-color: {self.colors['bg_tertiary']};"
        )
        cell_toolbar_widget.setMinimumHeight(36)
        cell_toolbar_layout = QHBoxLayout(cell_toolbar_widget)
        cell_toolbar_layout.setContentsMargins(8, 4, 8, 4)
        cell_toolbar_layout.setSpacing(8)

        # Add code cell button
        self.add_code_btn = QPushButton("+ Code")
        self.add_code_btn.setMinimumHeight(24)
        self.add_code_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: transparent;
                color: {self.colors['cell_type_code']};
                border: 1px solid {self.colors['cell_type_code']};
                padding: 3px 12px;
                border-radius: 3px;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {self.colors['bg_button']}; }}
        """
        )
        self.add_code_btn.clicked.connect(lambda: self._add_cell_below_focused("code"))
        cell_toolbar_layout.addWidget(self.add_code_btn)

        # Add markdown cell button
        self.add_md_btn = QPushButton("+ Markdown")
        self.add_md_btn.setMinimumHeight(24)
        self.add_md_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: transparent;
                color: {self.colors['cell_type_markdown']};
                border: 1px solid {self.colors['cell_type_markdown']};
                padding: 3px 12px;
                border-radius: 3px;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {self.colors['bg_button']}; }}
        """
        )
        self.add_md_btn.clicked.connect(
            lambda: self._add_cell_below_focused("markdown")
        )
        cell_toolbar_layout.addWidget(self.add_md_btn)

        # Shortcut help
        shortcut_label = QLabel(
            "Ctrl+Enter: Run | Shift+Enter: Run & Next | Alt+Enter: Run & New | Ctrl+Space: Autocomplete"
        )
        shortcut_label.setStyleSheet(
            f"color: {self.colors['text_secondary']}; font-size: 10px;"
        )
        cell_toolbar_layout.addWidget(shortcut_label)

        cell_toolbar_layout.addStretch()
        main_layout.addWidget(cell_toolbar_widget)

        # File path display
        path_widget = QWidget()
        path_widget.setStyleSheet(f"background-color: {self.colors['bg_code']};")
        path_widget.setMinimumHeight(28)
        path_layout = QHBoxLayout(path_widget)
        path_layout.setContentsMargins(8, 4, 8, 4)

        path_icon = QLabel("NB")
        path_icon.setStyleSheet(
            f"color: {self.colors['header_accent']}; font-weight: bold; font-size: 11px;"
        )
        path_layout.addWidget(path_icon)

        self.path_edit = QLineEdit()
        self.path_edit.setReadOnly(True)
        self.path_edit.setPlaceholderText("No notebook loaded...")
        self.path_edit.setStyleSheet(
            f"""
            QLineEdit {{
                background-color: transparent;
                color: {self.colors['text_primary']};
                border: none;
                font-size: 11px;
            }}
        """
        )
        path_layout.addWidget(self.path_edit)

        main_layout.addWidget(path_widget)

        # Scroll area for cells
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            f"""
            QScrollArea {{
                background-color: {self.colors['bg_primary']};
                border: none;
            }}
            QScrollBar:vertical {{
                background-color: {self.colors['scrollbar_bg']};
                width: 12px;
                border-radius: 6px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {self.colors['scrollbar_handle']};
                border-radius: 6px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {self.colors['scrollbar_handle_hover']};
            }}
        """
        )

        self.cells_container = QWidget()
        self.cells_container.setStyleSheet(
            f"background-color: {self.colors['bg_primary']};"
        )
        self.cells_layout = QVBoxLayout(self.cells_container)
        self.cells_layout.setContentsMargins(8, 8, 8, 8)
        self.cells_layout.setSpacing(8)
        self.cells_layout.addStretch()

        scroll.setWidget(self.cells_container)
        main_layout.addWidget(scroll)

        # Status bar
        self.status_bar = QLabel("Ready")
        self.status_bar.setMinimumHeight(28)
        self.status_bar.setStyleSheet(
            f"""
            QLabel {{
                background-color: {self.colors['bg_secondary']};
                color: {self.colors['text_secondary']};
                padding: 6px 10px;
                font-size: 11px;
                border-top: 1px solid {self.colors['border_primary']};
            }}
        """
        )
        main_layout.addWidget(self.status_bar)

        # Show welcome message
        self._show_welcome()

    def _show_welcome(self):
        """Show welcome message when no notebook is loaded."""
        # Clear existing cells
        self._clear_cells()

        welcome = QLabel(
            f"""
            <div style='text-align: center; padding: 40px;'>
                <h2 style='color: {self.colors['header_accent']};'>QGIS Notebook</h2>
                <p style='color: {self.colors['text_secondary']}; font-size: 13px;'>
                    Open a Jupyter notebook (.ipynb) to get started<br>
                    or create a new notebook.
                </p>
                <p style='color: {self.colors['text_tertiary']}; font-size: 11px; margin-top: 20px;'>
                    Click <b>Open</b> to load an existing notebook<br>
                    or <b>New</b> to create a new one.
                </p>
                <p style='color: {self.colors['text_tertiary']}; font-size: 11px; margin-top: 10px;'>
                    <b>Pre-imported:</b><br>
                    iface, QgsProject, QgsVectorLayer, QgsRasterLayer, QgsGeometry,<br>
                    QgsFeature, QgsPointXY, processing, os, sys, json, math,<br>
                    numpy (np), pandas (pd) if available
                </p>
                <p style='color: {self.colors['text_tertiary']}; font-size: 11px; margin-top: 10px;'>
                    <b>Shortcuts:</b><br>
                    Ctrl+Enter: Run cell<br>
                    Shift+Enter: Run and move to next<br>
                    Alt+Enter: Run and create new cell<br>
                    Ctrl+Space: Autocomplete<br>
                    Type "." after object: Show methods/attributes<br>
                    Esc: Finish markdown edit<br>
                    Right-click: Cell menu
                </p>
            </div>
        """
        )
        welcome.setAlignment(Qt.AlignCenter)
        welcome.setStyleSheet("background-color: transparent;")

        # Insert before the stretch
        self.cells_layout.insertWidget(0, welcome)
        self.cell_widgets.append(welcome)

    def _clear_cells(self):
        """Clear all cell widgets."""
        for widget in self.cell_widgets:
            self.cells_layout.removeWidget(widget)
            widget.deleteLater()
        self.cell_widgets = []

    def _open_notebook(self):
        """Open a notebook file."""
        # Check for unsaved changes first
        if not self._check_unsaved_changes():
            return

        last_dir = self.settings.value("QGISNotebook/last_directory", "")

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Jupyter Notebook",
            last_dir,
            "Jupyter Notebooks (*.ipynb);;All Files (*)",
        )

        if file_path:
            self.settings.setValue(
                "QGISNotebook/last_directory", os.path.dirname(file_path)
            )
            self._load_notebook(file_path)

    def _load_notebook(self, file_path):
        """Load a notebook from file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                self.notebook_data = json.load(f)

            self.notebook_path = file_path
            self.path_edit.setText(file_path)

            self._render_notebook()
            self._is_dirty = False  # Freshly loaded notebook is not dirty
            self.status_bar.setText(f"Loaded: {os.path.basename(file_path)}")

        except json.JSONDecodeError as e:
            QMessageBox.critical(self, "Error", f"Invalid notebook format:\n{str(e)}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load notebook:\n{str(e)}")

    def _render_notebook(self):
        """Render the loaded notebook."""
        self._clear_cells()

        if not self.notebook_data:
            return

        cells = self.notebook_data.get("cells", [])

        for i, cell_data in enumerate(cells):
            self._create_cell_widget(cell_data, i)

        self.status_bar.setText(f"Loaded {len(cells)} cells")

    def _create_cell_widget(self, cell_data, index):
        """Create a cell widget and add it to the layout."""
        cell_widget = NotebookCellWidget(cell_data, index, self.colors)
        cell_widget.executed.connect(self._execute_cell)
        cell_widget.execute_and_advance.connect(self._execute_and_advance)
        cell_widget.execute_and_insert.connect(self._execute_and_insert)
        cell_widget.delete_requested.connect(self._delete_cell)
        cell_widget.add_cell_above.connect(self._add_cell_above)
        cell_widget.add_cell_below.connect(self._add_cell_below)
        cell_widget.change_type_requested.connect(self._change_cell_type)
        cell_widget.cell_focused.connect(self._on_cell_focused)
        cell_widget.content_changed.connect(self._mark_dirty)

        # Pass namespace for autocomplete
        cell_widget.set_namespace(self.namespace)

        self.cells_layout.insertWidget(index, cell_widget)
        self.cell_widgets.insert(index, cell_widget)
        return cell_widget

    def _on_cell_focused(self, cell_index):
        """Handle when a cell gains focus."""
        self._focused_cell_index = cell_index

    def _update_cell_indices(self):
        """Update all cell indices after adding/removing cells."""
        for i, widget in enumerate(self.cell_widgets):
            if isinstance(widget, NotebookCellWidget):
                widget.update_index(i)

    def _add_cell_at_end(self, cell_type):
        """Add a new cell at the end of the notebook."""
        if not self.notebook_data:
            self.notebook_data = self._create_empty_notebook()
            self.notebook_data["cells"] = []
            self._clear_cells()

        cell_data = self._create_empty_cell(cell_type)
        self.notebook_data["cells"].append(cell_data)

        index = len(self.cell_widgets)
        new_widget = self._create_cell_widget(cell_data, index)
        self._update_cell_indices()
        self._mark_dirty()
        self.status_bar.setText(f"Added {cell_type} cell")

        # Focus the new cell
        QTimer.singleShot(50, new_widget.focus_editor)

    def _add_cell_below_focused(self, cell_type):
        """Add a new cell below the currently focused cell, or at the end if none focused."""
        if not self.notebook_data:
            self.notebook_data = self._create_empty_notebook()
            self.notebook_data["cells"] = []
            self._clear_cells()
            self._focused_cell_index = -1

        # If a cell is focused, add below it; otherwise add at end
        if self._focused_cell_index >= 0 and self._focused_cell_index < len(
            self.cell_widgets
        ):
            self._add_cell_below(self._focused_cell_index, cell_type)
        else:
            self._add_cell_at_end(cell_type)

    def _add_cell_above(self, index, cell_type):
        """Add a new cell above the specified index."""
        if not self.notebook_data:
            return

        cell_data = self._create_empty_cell(cell_type)
        self.notebook_data["cells"].insert(index, cell_data)

        new_widget = self._create_cell_widget(cell_data, index)
        self._update_cell_indices()
        self._mark_dirty()
        self.status_bar.setText(f"Added {cell_type} cell above [{index + 1}]")

        # Focus the new cell
        QTimer.singleShot(50, new_widget.focus_editor)

    def _add_cell_below(self, index, cell_type):
        """Add a new cell below the specified index."""
        if not self.notebook_data:
            return

        new_index = index + 1
        cell_data = self._create_empty_cell(cell_type)
        self.notebook_data["cells"].insert(new_index, cell_data)

        new_widget = self._create_cell_widget(cell_data, new_index)
        self._update_cell_indices()
        self._mark_dirty()
        self.status_bar.setText(f"Added {cell_type} cell below [{index + 1}]")

        # Focus the new cell
        QTimer.singleShot(50, new_widget.focus_editor)

        return new_widget

    def _delete_cell(self, index):
        """Delete a cell at the specified index."""
        if not self.notebook_data or len(self.cell_widgets) <= 1:
            QMessageBox.warning(self, "Warning", "Cannot delete the last cell.")
            return

        reply = QMessageBox.question(
            self,
            "Delete Cell",
            f"Are you sure you want to delete cell [{index + 1}]?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply != QMessageBox.Yes:
            return

        # Remove from notebook data
        if index < len(self.notebook_data["cells"]):
            self.notebook_data["cells"].pop(index)

        # Remove widget
        widget = self.cell_widgets.pop(index)
        self.cells_layout.removeWidget(widget)
        widget.deleteLater()

        self._update_cell_indices()
        self._mark_dirty()
        self.status_bar.setText(f"Deleted cell [{index + 1}]")

    def _change_cell_type(self, index, new_type):
        """Change the type of a cell."""
        if not self.notebook_data or index >= len(self.cell_widgets):
            return

        # Get current source
        widget = self.cell_widgets[index]
        source = widget.get_source()

        # Update notebook data
        self.notebook_data["cells"][index]["cell_type"] = new_type
        self.notebook_data["cells"][index]["source"] = source.split("\n")
        if new_type == "code":
            self.notebook_data["cells"][index]["outputs"] = []
            self.notebook_data["cells"][index]["execution_count"] = None

        # Remove old widget and create new one
        old_widget = self.cell_widgets.pop(index)
        self.cells_layout.removeWidget(old_widget)
        old_widget.deleteLater()

        cell_data = self.notebook_data["cells"][index]
        cell_data["source"] = source  # Keep as string for widget
        self._create_cell_widget(cell_data, index)
        self._update_cell_indices()
        self._mark_dirty()

        self.status_bar.setText(f"Changed cell [{index + 1}] to {new_type}")

    def _create_empty_cell(self, cell_type):
        """Create an empty cell data structure."""
        if cell_type == "code":
            return {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": "",
            }
        else:
            return {"cell_type": "markdown", "metadata": {}, "source": ""}

    def _execute_code_sync(self, code):
        """Execute code synchronously and return result, stdout, stderr."""
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = StringIO()
        sys.stderr = StringIO()

        result = None
        try:
            # Try to evaluate as expression first (to get return value)
            try:
                result = eval(code, self.namespace)
            except SyntaxError:
                # If not an expression, execute as statements
                exec(code, self.namespace)

            stdout = sys.stdout.getvalue()
            stderr = sys.stderr.getvalue()
            return result, stdout, stderr

        except Exception as e:
            stderr = traceback.format_exc()
            return None, "", stderr

        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

    def _execute_cell(self, cell_index):
        """Execute a specific cell synchronously."""
        if cell_index >= len(self.cell_widgets):
            return

        cell_widget = self.cell_widgets[cell_index]
        if not isinstance(cell_widget, NotebookCellWidget):
            return

        if cell_widget.cell_type != "code":
            return

        code = cell_widget.get_source()
        if not code.strip():
            return

        cell_widget.set_running(True)
        self.status_bar.setText(f"Executing cell [{cell_index + 1}]...")

        # Process events to update UI
        QApplication.processEvents()

        # Execute synchronously
        result, stdout, stderr = self._execute_code_sync(code)

        # Update cell output
        cell_widget.set_running(False)
        cell_widget.set_output(result, stdout, stderr)

        # Update namespace for all cells (for autocomplete with newly defined variables)
        self._update_cell_namespaces()

        if stderr:
            self.status_bar.setText(f"Cell [{cell_index + 1}] completed with errors")
            self.status_bar.setStyleSheet(
                f"""
                QLabel {{
                    background-color: {self.colors['bg_secondary']};
                    color: {self.colors['text_error']};
                    padding: 6px 10px;
                    font-size: 11px;
                    border-top: 1px solid {self.colors['border_primary']};
                }}
            """
            )
        else:
            self.status_bar.setText(f"Cell [{cell_index + 1}] executed successfully")
            self.status_bar.setStyleSheet(
                f"""
                QLabel {{
                    background-color: {self.colors['bg_secondary']};
                    color: {self.colors['text_success']};
                    padding: 6px 10px;
                    font-size: 11px;
                    border-top: 1px solid {self.colors['border_primary']};
                }}
            """
            )

    def _execute_and_advance(self, cell_index):
        """Execute a cell and move focus to the next cell."""
        self._execute_cell(cell_index)

        # Focus next cell if it exists
        next_index = cell_index + 1
        if next_index < len(self.cell_widgets):
            next_widget = self.cell_widgets[next_index]
            if isinstance(next_widget, NotebookCellWidget):
                # Use QTimer to ensure focus happens after execution completes
                QTimer.singleShot(50, next_widget.focus_editor)
        else:
            # No next cell - create a new code cell
            self._add_cell_at_end("code")

    def _execute_and_insert(self, cell_index):
        """Execute a cell and insert a new code cell below, moving focus to it."""
        self._execute_cell(cell_index)

        # Create a new code cell below
        if not self.notebook_data:
            return

        new_index = cell_index + 1
        cell_data = self._create_empty_cell("code")
        self.notebook_data["cells"].insert(new_index, cell_data)

        new_widget = self._create_cell_widget(cell_data, new_index)
        self._update_cell_indices()
        self.status_bar.setText(f"Created new cell [{new_index + 1}]")

        # Focus the new cell
        QTimer.singleShot(50, new_widget.focus_editor)

    def _run_all_cells(self):
        """Run all code cells in order using a queue."""
        if self._is_running_all:
            return

        # Build list of code cell indices
        self._execution_queue = []
        for i, widget in enumerate(self.cell_widgets):
            if isinstance(widget, NotebookCellWidget) and widget.cell_type == "code":
                self._execution_queue.append(i)

        if not self._execution_queue:
            self.status_bar.setText("No code cells to execute")
            return

        self._is_running_all = True
        self.run_all_btn.setEnabled(False)
        self.status_bar.setText(f"Running {len(self._execution_queue)} cells...")

        # Start executing the queue
        self._execute_next_in_queue()

    def _execute_next_in_queue(self):
        """Execute the next cell in the queue."""
        if not self._execution_queue:
            # Done with all cells
            self._is_running_all = False
            self.run_all_btn.setEnabled(True)
            self.status_bar.setText("Finished running all cells")
            self.status_bar.setStyleSheet(
                f"""
                QLabel {{
                    background-color: {self.colors['bg_secondary']};
                    color: {self.colors['text_success']};
                    padding: 6px 10px;
                    font-size: 11px;
                    border-top: 1px solid {self.colors['border_primary']};
                }}
            """
            )
            return

        cell_index = self._execution_queue.pop(0)
        self._execute_cell(cell_index)

        # Process events and schedule next cell
        QApplication.processEvents()

        # Use QTimer to schedule next execution to avoid stack overflow
        QTimer.singleShot(10, self._execute_next_in_queue)

    def _clear_outputs(self):
        """Clear all cell outputs."""
        for widget in self.cell_widgets:
            if isinstance(widget, NotebookCellWidget) and widget.cell_type == "code":
                widget.output_area.clear()
                widget.output_area.setVisible(False)

        self.status_bar.setText("Outputs cleared")
        self.status_bar.setStyleSheet(
            f"""
            QLabel {{
                background-color: {self.colors['bg_secondary']};
                color: {self.colors['text_secondary']};
                padding: 6px 10px;
                font-size: 11px;
                border-top: 1px solid {self.colors['border_primary']};
            }}
        """
        )

    def _save_notebook(self):
        """Save the current notebook."""
        if not self.notebook_path:
            self._save_notebook_as()
            return

        self._save_to_path(self.notebook_path)

    def _save_notebook_as(self):
        """Save the notebook to a new file."""
        last_dir = self.settings.value("QGISNotebook/last_directory", "")

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Jupyter Notebook",
            last_dir,
            "Jupyter Notebooks (*.ipynb);;All Files (*)",
        )

        if file_path:
            if not file_path.endswith(".ipynb"):
                file_path += ".ipynb"
            self._save_to_path(file_path)

    def _save_to_path(self, file_path):
        """Save notebook to specific path."""
        if not self.notebook_data:
            self.notebook_data = self._create_empty_notebook()

        # Update cell sources from widgets
        for i, widget in enumerate(self.cell_widgets):
            if isinstance(widget, NotebookCellWidget):
                source = widget.get_source()
                if i < len(self.notebook_data.get("cells", [])):
                    # Split into lines for JSON format
                    lines = source.split("\n")
                    self.notebook_data["cells"][i]["source"] = (
                        [line + "\n" for line in lines[:-1]] + [lines[-1]]
                        if lines
                        else []
                    )

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(self.notebook_data, f, indent=2)

            self.notebook_path = file_path
            self.path_edit.setText(file_path)
            self._is_dirty = False  # Reset dirty flag after successful save
            self.status_bar.setText(f"Saved: {os.path.basename(file_path)}")
            self.status_bar.setStyleSheet(
                f"""
                QLabel {{
                    background-color: {self.colors['bg_secondary']};
                    color: {self.colors['text_success']};
                    padding: 6px 10px;
                    font-size: 11px;
                    border-top: 1px solid {self.colors['border_primary']};
                }}
            """
            )

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save notebook:\n{str(e)}")

    def _new_notebook(self):
        """Create a new empty notebook."""
        # Check for unsaved changes first
        if not self._check_unsaved_changes():
            return

        self.notebook_data = self._create_empty_notebook()
        self.notebook_path = None
        self.path_edit.setText("Untitled.ipynb")

        # Reset namespace
        self.namespace = {"__name__": "__main__", "__doc__": None}
        self._setup_namespace()

        self._render_notebook()
        self._is_dirty = False  # New notebook starts clean
        self.status_bar.setText("New notebook created")

    def _create_empty_notebook(self):
        """Create an empty notebook structure."""
        return {
            "cells": [
                {
                    "cell_type": "markdown",
                    "metadata": {},
                    "source": "# New Notebook\n\nWelcome to your new Jupyter notebook!",
                },
                {
                    "cell_type": "code",
                    "execution_count": None,
                    "metadata": {},
                    "outputs": [],
                    "source": "# Enter your Python code here\nprint('Hello, QGIS!')",
                },
            ],
            "metadata": {
                "kernelspec": {
                    "display_name": "Python 3",
                    "language": "python",
                    "name": "python3",
                },
                "language_info": {"name": "python", "version": "3.9"},
            },
            "nbformat": 4,
            "nbformat_minor": 5,
        }

    def closeEvent(self, event):
        """Handle dock widget close event."""
        # Cancel any running execution
        self._execution_queue = []
        self._is_running_all = False
        event.accept()
