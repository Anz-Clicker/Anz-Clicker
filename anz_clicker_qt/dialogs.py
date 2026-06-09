from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QColor, QMouseEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app_settings import AppSettings
from .constants import APP_VERSION
from .icons import app_base_dir
from .widgets import make_help_label


class ActionOrderDialog(QDialog):
    def __init__(self, ordered_names: list[str], hidden_names: list[str], default_order: list[str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Action Order")
        self.result: tuple[list[str], list[str]] | None = None
        self.deleted_custom_actions: list[str] = []
        self.default_order = default_order
        self.items = [{"name": name, "hidden": name in hidden_names} for name in ordered_names]
        layout = QVBoxLayout(self)
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.list_widget.currentRowChanged.connect(lambda *_: self._update_button_states())
        layout.addWidget(self.list_widget, 1)
        controls = QHBoxLayout()
        self.move_up_button = QPushButton("Move Up")
        self.move_up_button.clicked.connect(lambda: self._move(-1))
        controls.addWidget(self.move_up_button)
        self.move_down_button = QPushButton("Move Down")
        self.move_down_button.clicked.connect(lambda: self._move(1))
        controls.addWidget(self.move_down_button)
        self.toggle_button = QPushButton("Show/Hide")
        self.toggle_button.clicked.connect(self._toggle)
        controls.addWidget(self.toggle_button)
        self.delete_button = QPushButton("Delete Action")
        self.delete_button.clicked.connect(self._delete_custom_action)
        controls.addWidget(self.delete_button)
        self.reset_button = QPushButton("Reset to Default Order")
        self.reset_button.clicked.connect(self._reset)
        controls.addWidget(self.reset_button)
        layout.addLayout(controls)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._refresh()
        self.resize(520, 560)

    def _refresh(self, select_row: int = 0) -> None:
        self.list_widget.clear()
        for item in self.items:
            list_item = QListWidgetItem(("Hidden  " if item["hidden"] else "Visible  ") + item["name"])
            if item["hidden"]:
                list_item.setForeground(QColor("#8ea0bf"))
            self.list_widget.addItem(list_item)
        if self.items:
            self.list_widget.setCurrentRow(max(0, min(select_row, len(self.items) - 1)))
        self._update_button_states()

    def _move(self, offset: int) -> None:
        row = self.list_widget.currentRow()
        target = row + offset
        if row < 0 or target < 0 or target >= len(self.items):
            return
        self.items[row], self.items[target] = self.items[target], self.items[row]
        self._refresh(target)

    def _toggle(self) -> None:
        row = self.list_widget.currentRow()
        if row < 0:
            return
        self.items[row]["hidden"] = not self.items[row]["hidden"]
        self._refresh(row)

    def _reset(self) -> None:
        self.items = [{"name": name, "hidden": False} for name in self.default_order]
        self._refresh()

    def _delete_custom_action(self) -> None:
        row = self.list_widget.currentRow()
        if row < 0 or row >= len(self.items):
            return
        display_name = self.items[row]["name"]
        if not self._is_custom_action(display_name):
            return
        custom_name = display_name.removeprefix("Custom: ")
        choice = QMessageBox.question(
            self,
            "Delete Custom Action",
            f'Delete the custom action "{custom_name}"? This cannot be undone.',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if choice != QMessageBox.Yes:
            return
        self.deleted_custom_actions.append(custom_name)
        del self.items[row]
        self.default_order = [item for item in self.default_order if item != display_name]
        self._refresh(min(row, len(self.items) - 1))

    def _update_button_states(self) -> None:
        row = self.list_widget.currentRow()
        has_selection = 0 <= row < len(self.items)
        self.move_up_button.setEnabled(has_selection and row > 0)
        self.move_down_button.setEnabled(has_selection and row < len(self.items) - 1)
        self.toggle_button.setEnabled(has_selection)
        self.delete_button.setEnabled(has_selection and self._is_custom_action(self.items[row]["name"]))

    @staticmethod
    def _is_custom_action(display_name: str) -> bool:
        return display_name.startswith("Custom: ")

    def _save(self) -> None:
        ordered = [item["name"] for item in self.items]
        hidden = [item["name"] for item in self.items if item["hidden"]]
        self.result = (ordered, hidden)
        self.accept()


class SettingsDialog(QDialog):
    def __init__(self, settings: AppSettings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setObjectName("SettingsDialog")
        self.result = AppSettings.from_dict(as_settings_dict(settings))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 22, 22, 18)
        layout.setSpacing(16)

        title = QLabel("Settings")
        title.setObjectName("SectionTitle")
        layout.addWidget(title)

        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.animation_speed = self._spin(1, 10, self.result.mouse_animation_speed)
        form.addRow(
            make_help_label(
                self,
                "Mouse animation speed (1-10)",
                "A scale of 1-10 for setting animation speed - 1 being the slowest, 10 being the fastest. The standard speed is 5.",
            ),
            self.animation_speed,
        )
        self.enhanced_mouse = QCheckBox("Enhanced humanlike animated mouse movement")
        self.enhanced_mouse.setChecked(self.result.enhanced_humanlike_mouse)
        form.addRow(
            make_help_label(
                self,
                "Animated mouse movement style",
                "When enabled, actions that already animate the mouse use more varied curves, pauses, overshoots, and settling. Normal click and move actions are unchanged.",
            ),
            self.enhanced_mouse,
        )
        form.addRow(
            make_help_label(
                self,
                "Mouse click down/up delay",
                "Sets a random time delay between a mouse being clicked down and being released.",
            ),
            self._range_row("Random value between", "and", "milliseconds", self.result.mouse_click_delay_min_ms, self.result.mouse_click_delay_max_ms, "mouse"),
        )
        form.addRow(
            make_help_label(
                self,
                "Key press down/up delay",
                "Sets a random time delay between a key being pressed down and being released.",
            ),
            self._range_row("Random value between", "and", "milliseconds", self.result.key_press_delay_min_ms, self.result.key_press_delay_max_ms, "key"),
        )
        form.addRow("Default Script Location Folder", self._script_folder_row())
        self.remember_geometry = QCheckBox()
        self.remember_geometry.setChecked(self.result.remember_window_geometry)
        form.addRow("Remember Last Position && Size", self.remember_geometry)
        layout.addLayout(form)

        note = QLabel("These settings are saved for Anz Clicker and applied when scripts run.")
        note.setObjectName("SidebarSubtle")
        note.setWordWrap(True)
        layout.addWidget(note)

        bottom_row = QHBoxLayout()
        reset_button = QPushButton("Reset to Defaults")
        reset_button.clicked.connect(self._reset_to_defaults)
        bottom_row.addWidget(reset_button)
        version_label = QLabel(f"Version {APP_VERSION}")
        version_label.setObjectName("VersionLabel")
        bottom_row.addWidget(version_label)
        bottom_row.addStretch(1)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        bottom_row.addWidget(buttons)
        layout.addLayout(bottom_row)
        self.resize(620, 350)

    def _spin(self, minimum: int, maximum: int, value: int) -> QSpinBox:
        field = QSpinBox()
        field.setButtonSymbols(QSpinBox.NoButtons)
        field.setRange(minimum, maximum)
        field.setValue(value)
        field.setMinimumWidth(96)
        return field

    def _range_row(self, before: str, middle: str, after: str, low: int, high: int, prefix: str) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        low_field = self._spin(0, 99999, low)
        high_field = self._spin(0, 99999, high)
        setattr(self, f"{prefix}_delay_min", low_field)
        setattr(self, f"{prefix}_delay_max", high_field)
        layout.addWidget(QLabel(before))
        layout.addWidget(low_field)
        layout.addWidget(QLabel(middle))
        layout.addWidget(high_field)
        layout.addWidget(QLabel(after))
        layout.addStretch(1)
        return row

    def _script_folder_row(self) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self.script_folder = QLineEdit(self.result.default_script_folder)
        browse = QPushButton("Browse")
        browse.clicked.connect(self._browse_script_folder)
        layout.addWidget(self.script_folder, 1)
        layout.addWidget(browse)
        return row

    def _browse_script_folder(self) -> None:
        start_dir = self.script_folder.text().strip() or str(app_base_dir() / "scripts")
        start_path = Path(start_dir)
        if not start_path.is_absolute():
            start_dir = str(app_base_dir() / start_path)
        selected = QFileDialog.getExistingDirectory(self, "Choose Default Script Folder", start_dir)
        if selected:
            self.script_folder.setText(selected)

    def _save(self) -> None:
        self.result = AppSettings(
            mouse_animation_speed=self.animation_speed.value(),
            enhanced_humanlike_mouse=self.enhanced_mouse.isChecked(),
            mouse_click_delay_min_ms=self.mouse_delay_min.value(),
            mouse_click_delay_max_ms=self.mouse_delay_max.value(),
            key_press_delay_min_ms=self.key_delay_min.value(),
            key_press_delay_max_ms=self.key_delay_max.value(),
            default_script_folder=self.script_folder.text().strip(),
            remember_window_geometry=self.remember_geometry.isChecked(),
            window_geometry=self.result.window_geometry,
            start_keybind=self.result.start_keybind,
            pause_keybind=self.result.pause_keybind,
        )
        self.result.normalize()
        self.accept()

    def _reset_to_defaults(self) -> None:
        choice = QMessageBox.question(
            self,
            "Reset Settings",
            "Reset all settings to their original defaults?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if choice != QMessageBox.Yes:
            return
        self._load_settings(AppSettings())

    def _load_settings(self, settings: AppSettings) -> None:
        self.result = AppSettings.from_dict(as_settings_dict(settings))
        self.animation_speed.setValue(self.result.mouse_animation_speed)
        self.enhanced_mouse.setChecked(self.result.enhanced_humanlike_mouse)
        self.mouse_delay_min.setValue(self.result.mouse_click_delay_min_ms)
        self.mouse_delay_max.setValue(self.result.mouse_click_delay_max_ms)
        self.key_delay_min.setValue(self.result.key_press_delay_min_ms)
        self.key_delay_max.setValue(self.result.key_press_delay_max_ms)
        self.script_folder.setText(self.result.default_script_folder)
        self.remember_geometry.setChecked(self.result.remember_window_geometry)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        focused = QApplication.focusWidget()
        if focused and self.isAncestorOf(focused):
            focused.clearFocus()
        super().mousePressEvent(event)


def as_settings_dict(settings: AppSettings) -> dict[str, int | str | bool]:
    return {
        "mouse_animation_speed": settings.mouse_animation_speed,
        "enhanced_humanlike_mouse": settings.enhanced_humanlike_mouse,
        "mouse_click_delay_min_ms": settings.mouse_click_delay_min_ms,
        "mouse_click_delay_max_ms": settings.mouse_click_delay_max_ms,
        "key_press_delay_min_ms": settings.key_press_delay_min_ms,
        "key_press_delay_max_ms": settings.key_press_delay_max_ms,
        "default_script_folder": settings.default_script_folder,
        "remember_window_geometry": settings.remember_window_geometry,
        "window_geometry": settings.window_geometry,
        "start_keybind": settings.start_keybind,
        "pause_keybind": settings.pause_keybind,
    }


__all__ = ["ActionOrderDialog", "SettingsDialog", "as_settings_dict"]
