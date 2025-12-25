"""
QGIS Notebook Plugin

A plugin for rendering and running Jupyter notebooks within QGIS.
This plugin provides a dockable panel for interactive notebook execution.
"""

from .qgis_notebook import QGISNotebook


def classFactory(iface):
    """Load QGISNotebook class from file qgis_notebook.

    Args:
        iface: A QGIS interface instance.

    Returns:
        QGISNotebook: The plugin instance.
    """
    return QGISNotebook(iface)
