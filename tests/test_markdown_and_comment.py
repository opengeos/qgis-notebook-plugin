"""Markdown thematic breaks, the Ctrl+/ shortcut and the Restart button."""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from qgis.PyQt.QtCore import QEvent, Qt  # noqa: E402
from qgis.PyQt.QtGui import QKeyEvent, QTextCursor  # noqa: E402
from qgis.PyQt.QtWidgets import QApplication  # noqa: E402


@pytest.fixture(scope="module")
def app():
    """Provide a QApplication for widget tests."""
    return QApplication.instance() or QApplication([])


@pytest.fixture
def editor(app):
    """Provide a code editor for shortcut tests."""
    from qgis_notebook.dialogs.notebook_dock import CodeEditor

    return CodeEditor()


def _press_toggle(editor, event_type=QEvent.Type.KeyPress):
    """Send Ctrl+/ to an editor.

    Args:
        editor: The editor receiving the key event.
        event_type: The event type to send.

    Returns:
        QKeyEvent: The delivered event.
    """
    event = QKeyEvent(
        event_type, Qt.Key.Key_Slash, Qt.KeyboardModifier.ControlModifier, "/"
    )
    QApplication.sendEvent(editor, event)
    return event


def _select(editor, start, end):
    """Select a character range in an editor.

    Args:
        editor: The editor to change.
        start: The selection start position.
        end: The selection end position.
    """
    cursor = editor.textCursor()
    cursor.setPosition(start)
    cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
    editor.setTextCursor(cursor)


@pytest.mark.parametrize(
    "source, expected",
    [
        ("---", "<hr>"),
        ("-----------", "<hr>"),
        ("***", "<hr>"),
        ("___", "<hr>"),
        ("- - -", "<hr>"),
        ("<br>\n---", "<br><hr>"),
        ("<br>\n---\nAfter", "<br><hr>After"),
        ("Before\n\n---\n\nAfter", "Before<hr>After"),
    ],
)
def test_thematic_breaks(app, source, expected):
    """Thematic break lines become <hr> without extra line breaks."""
    widget = _markdown_cell(source)
    assert widget._markdown_to_html(source) == expected


def test_dashes_under_text_make_a_heading(app):
    """Dashes directly below a paragraph line make it a heading."""
    widget = _markdown_cell("Title\n---")
    html = widget._markdown_to_html("Title\n---")
    assert "<h2" in html and "Title" in html and "<hr>" not in html


def test_dashes_after_a_list_item_are_a_rule(app):
    """Dashes directly below a list item are a rule, not a heading."""
    widget = _markdown_cell("- item\n---")
    html = widget._markdown_to_html("- item\n---")
    assert "<hr>" in html and "<h2" not in html


def _markdown_cell(source):
    """Build a markdown cell widget.

    Args:
        source: The markdown source.

    Returns:
        NotebookCellWidget: The cell widget.
    """
    from qgis_notebook.dialogs.notebook_dock import NotebookDockWidget

    dock = NotebookDockWidget(iface=None)
    return dock._create_cell_widget(
        {"cell_type": "markdown", "metadata": {}, "source": source}, 0
    )


def test_toggle_current_line(editor):
    """Ctrl+/ comments the cursor line, and pressing it again restores it."""
    editor.setPlainText("a = 1\n    b = 2")
    _press_toggle(editor)
    assert editor.toPlainText() == "# a = 1\n    b = 2"
    _press_toggle(editor)
    assert editor.toPlainText() == "a = 1\n    b = 2"


def test_toggle_selection_uses_smallest_indent(editor):
    """Selected lines are commented at their shared indent, skipping blanks."""
    source = "if x:\n    a = 1\n\n        b = 2\nc = 3"
    editor.setPlainText(source)
    _select(editor, source.index("    a"), source.index("c = 3"))
    _press_toggle(editor)
    assert editor.toPlainText() == ("if x:\n    # a = 1\n\n    #     b = 2\nc = 3")
    _press_toggle(editor)
    assert editor.toPlainText() == source


def test_toggle_mixed_selection_comments_all(editor):
    """A selection with any uncommented line is commented, not uncommented."""
    source = "# a\nb"
    editor.setPlainText(source)
    editor.selectAll()
    _press_toggle(editor)
    assert editor.toPlainText() == "# # a\n# b"


def test_uncomment_without_space(editor):
    """A comment with no space after the hash is uncommented cleanly."""
    editor.setPlainText("#a = 1")
    _press_toggle(editor)
    assert editor.toPlainText() == "a = 1"


def test_toggle_is_one_undo_step(editor):
    """Undo reverts a multi-line toggle in one step."""
    editor.setPlainText("a\nb\nc")
    editor.selectAll()
    _press_toggle(editor)
    assert editor.toPlainText() == "# a\n# b\n# c"
    editor.undo()
    assert editor.toPlainText() == "a\nb\nc"


def test_shortcut_override_is_claimed(editor):
    """The editor claims Ctrl+/ so a window-level shortcut cannot take it."""
    event = QKeyEvent(
        QEvent.Type.ShortcutOverride,
        Qt.Key.Key_Slash,
        Qt.KeyboardModifier.ControlModifier,
        "/",
    )
    event.ignore()
    QApplication.sendEvent(editor, event)
    assert event.isAccepted()


def test_restart_button_uses_neutral_color(app):
    """The Restart button matches the neutral Save and New buttons."""
    from qgis_notebook.dialogs.notebook_dock import NotebookDockWidget

    dock = NotebookDockWidget(iface=None)
    assert dock.restart_btn.styleSheet() == dock.save_btn.styleSheet()
