"""Cell outputs must be written back to the .ipynb file on save."""

import json
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from qgis.PyQt.QtWidgets import QApplication  # noqa: E402


@pytest.fixture(scope="module")
def app():
    """Provide a QApplication for widget tests."""
    return QApplication.instance() or QApplication([])


def _load_notebook(dock, path, cells):
    """Write a notebook with the given cells and open it in the dock.

    Args:
        dock: The NotebookDockWidget instance.
        path: Destination path for the notebook file.
        cells: List of nbformat cell dicts.
    """
    nb = dock._create_empty_notebook()
    nb["cells"] = cells
    path.write_text(json.dumps(nb), encoding="utf-8")
    dock._load_notebook(str(path))


def _code_cell(source):
    """Build an empty nbformat code cell.

    Args:
        source: The cell source code.

    Returns:
        dict: An nbformat v4 code cell.
    """
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": source,
    }


def test_outputs_saved_and_reloaded(app, tmp_path):
    """Executed cell outputs are persisted in nbformat and shown on reload."""
    from qgis_notebook.dialogs.notebook_dock import NotebookDockWidget

    dock = NotebookDockWidget(iface=None)
    path = tmp_path / "nb.ipynb"
    _load_notebook(
        dock,
        path,
        [
            _code_cell("print('hello')\nprint('world')"),
            _code_cell("1 + 1"),
            _code_cell("1 / 0"),
        ],
    )
    for i in range(3):
        dock._execute_cell(i)
    assert dock._is_dirty
    dock._save_to_path(str(path))

    saved = json.loads(path.read_text(encoding="utf-8"))
    c0, c1, c2 = saved["cells"]
    assert [c["execution_count"] for c in (c0, c1, c2)] == [1, 2, 3]
    assert c0["outputs"] == [
        {"output_type": "stream", "name": "stdout", "text": ["hello\n", "world\n"]}
    ]
    assert c1["outputs"][0]["output_type"] == "execute_result"
    assert c1["outputs"][0]["data"]["text/plain"] == ["2"]
    assert c2["outputs"][0]["name"] == "stderr"
    assert "ZeroDivisionError" in "".join(c2["outputs"][0]["text"])

    # The saved file must be a valid notebook (nbformat is optional in CI)
    try:
        import nbformat
    except ImportError:
        pass
    else:
        nbformat.validate(nbformat.read(str(path), as_version=4))

    # Reloading shows the saved output
    dock._load_notebook(str(path))
    assert "hello" in dock.cell_widgets[0].output_area.toPlainText()
    assert "world" in dock.cell_widgets[0].output_area.toPlainText()

    # Clearing outputs removes them from the saved file too
    dock._clear_outputs()
    dock._save_to_path(str(path))
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert all(c["outputs"] == [] for c in saved["cells"])
    assert all(c["execution_count"] is None for c in saved["cells"])


def test_reloaded_output_matches_live_output(app, tmp_path):
    """Reloaded outputs keep live order and add no extra blank lines."""
    from qgis_notebook.dialogs.notebook_dock import NotebookDockWidget

    dock = NotebookDockWidget(iface=None)
    path = tmp_path / "nb.ipynb"
    code = "(print('hello'), print('oops', file=__import__('sys').stderr), 2)[2]"
    _load_notebook(dock, path, [_code_cell(code)])
    dock._execute_cell(0)
    live = dock.cell_widgets[0].output_area.toPlainText()
    dock._save_to_path(str(path))

    saved = json.loads(path.read_text(encoding="utf-8"))
    kinds = [o.get("name", o["output_type"]) for o in saved["cells"][0]["outputs"]]
    assert kinds == ["stdout", "execute_result", "stderr"]

    dock._load_notebook(str(path))
    reloaded = dock.cell_widgets[0].output_area.toPlainText()
    assert reloaded.strip() == live.strip() == "hello\n2\noops"


def test_clearing_outputs_marks_dirty(app, tmp_path):
    """Clearing saved outputs is an unsaved change."""
    from qgis_notebook.dialogs.notebook_dock import NotebookDockWidget

    dock = NotebookDockWidget(iface=None)
    path = tmp_path / "nb.ipynb"
    _load_notebook(dock, path, [_code_cell("1 + 1")])
    dock._execute_cell(0)
    dock._save_to_path(str(path))
    assert not dock._is_dirty

    dock._clear_outputs()
    assert dock._is_dirty
