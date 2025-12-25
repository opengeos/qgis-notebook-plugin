"""
QGIS Notebook Plugin Dialogs

This module contains the dialog and dock widget classes for the notebook plugin.
"""

from .notebook_dock import NotebookDockWidget
from .settings_dock import SettingsDockWidget
from .update_checker import UpdateCheckerDialog

__all__ = [
    "NotebookDockWidget",
    "SettingsDockWidget",
    "UpdateCheckerDialog",
]
