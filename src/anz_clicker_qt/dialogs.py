from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QItemSelectionModel, QSize, Qt, Signal
from PySide6.QtGui import QColor, QCursor, QMouseEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
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
from .icons import app_icon
from .paths import scripts_dir, storage_root
from .widgets import (
    ActionDropIndicator,
    KeyCaptureLineEdit,
    PlaceholderSpinBox,
    make_help_label,
    scroll_view_by_wheel,
    scroll_view_for_drag,
    set_active_drag_scroll_view,
    style_dialog_buttons,
)


class ActionOrderListWidget(QListWidget):
    orderChanged = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._dragging = False
        self._pending_drag_pos = None
        self._pending_drag_row = -1
        self._pending_drag_rows: list[int] = []
        self._manual_drag_active = False
        self._manual_drag_rows: list[int] = []
        self._manual_insertion_row = -1
        self.setObjectName("ActionOrderList")
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setDragEnabled(False)
        self.setAcceptDrops(False)
        self.setDropIndicatorShown(False)
        self.setDragDropMode(QAbstractItemView.NoDragDrop)
        self.setDragDropOverwriteMode(False)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setAutoScroll(True)
        self.setAutoScrollMargin(56)
        self.drop_indicator = ActionDropIndicator(self.viewport())
        self.drop_indicator.setGeometry(self.viewport().rect())

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.drop_indicator.setGeometry(self.viewport().rect())

    def startDrag(self, supported_actions) -> None:
        return

    def mousePressEvent(self, event: QMouseEvent) -> None:
        super().mousePressEvent(event)
        if event.button() != Qt.LeftButton:
            self._clear_pending_drag()
            return
        row = self.indexAt(event.position().toPoint()).row()
        if row < 0:
            self._clear_pending_drag()
            return
        rows = self._selected_rows()
        self._pending_drag_pos = event.position().toPoint()
        self._pending_drag_row = row
        self._pending_drag_rows = rows if row in rows else [row]

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._manual_drag_active:
            self._update_manual_drag(event.position().toPoint())
            event.accept()
            return
        if (
            self._pending_drag_row >= 0
            and event.buttons() & Qt.LeftButton
            and self._pending_drag_pos is not None
            and (event.position().toPoint() - self._pending_drag_pos).manhattanLength() >= QApplication.startDragDistance()
        ):
            self._begin_manual_drag()
            self._update_manual_drag(event.position().toPoint())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton and self._manual_drag_active:
            self._finish_manual_drag()
            event.accept()
            return
        self._clear_pending_drag()
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event) -> None:
        if self._manual_drag_active and scroll_view_by_wheel(self, event):
            self._update_manual_drag(self.viewport().mapFromGlobal(QCursor.pos()))
            return
        super().wheelEvent(event)

    def _selected_rows(self) -> list[int]:
        return sorted(index.row() for index in self.selectedIndexes())

    def _clear_pending_drag(self) -> None:
        self._pending_drag_pos = None
        self._pending_drag_row = -1
        self._pending_drag_rows = []

    def _begin_manual_drag(self) -> None:
        if self._manual_drag_active or self._pending_drag_row < 0:
            return
        self._manual_drag_active = True
        self._dragging = True
        self._manual_drag_rows = list(self._pending_drag_rows)
        self._manual_insertion_row = self._pending_drag_row
        self._clear_pending_drag()
        self.viewport().grabMouse(Qt.ClosedHandCursor)
        self.viewport().setCursor(Qt.ClosedHandCursor)
        set_active_drag_scroll_view(self)

    def _update_manual_drag(self, position) -> None:
        scroll_view_for_drag(self, position)
        insertion_row, line_y = self._drop_location(position)
        self._manual_insertion_row = insertion_row
        self.drop_indicator.set_target(line_y)

    def _finish_manual_drag(self) -> None:
        rows = list(self._manual_drag_rows)
        insertion_row = self._manual_insertion_row
        self._manual_drag_active = False
        self._dragging = False
        self._manual_drag_rows = []
        self._manual_insertion_row = -1
        set_active_drag_scroll_view(None)
        self.drop_indicator.clear_target()
        self.viewport().releaseMouse()
        self.viewport().unsetCursor()
        if rows and insertion_row >= 0:
            self._move_rows_to(rows, insertion_row)

    def _drop_location(self, position) -> tuple[int, int]:
        if position.y() < 0:
            return 0, 4
        index = self.indexAt(position)
        if index.isValid():
            rect = self.visualItemRect(self.item(index.row()))
            after = position.y() > rect.center().y()
            return index.row() + (1 if after else 0), rect.bottom() + 1 if after else rect.top()
        count = self.count()
        if count:
            last_rect = self.visualItemRect(self.item(count - 1))
            if position.y() > self.viewport().height():
                return count, last_rect.bottom() + 1
            return count, last_rect.bottom() + 1
        return 0, 4

    def _move_rows_to(self, rows: list[int], insertion_row: int) -> None:
        rows = sorted(set(row for row in rows if 0 <= row < self.count()))
        if not rows:
            return
        adjusted_row = insertion_row - sum(1 for row in rows if row < insertion_row)
        adjusted_row = max(0, min(adjusted_row, self.count() - len(rows)))
        if adjusted_row == rows[0] and rows == list(range(rows[0], rows[0] + len(rows))):
            return
        items = [self.takeItem(row) for row in reversed(rows)]
        items.reverse()
        self.clearSelection()
        for offset, item in enumerate(items):
            self.insertItem(adjusted_row + offset, item)
            item.setSelected(True)
        self.setCurrentRow(adjusted_row, QItemSelectionModel.NoUpdate)
        self.orderChanged.emit()


class ActionOrderDialog(QDialog):
    def __init__(self, ordered_names: list[str], hidden_names: list[str], default_order: list[str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Action Order")
        self.setObjectName("ActionOrderDialog")
        self.result: tuple[list[str], list[str]] | None = None
        self.deleted_custom_actions: list[str] = []
        self.default_order = default_order
        self.items = [{"name": name, "hidden": name in hidden_names} for name in ordered_names]
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 14)
        layout.setSpacing(10)

        title_row = QHBoxLayout()
        title_stack = QVBoxLayout()
        title_stack.setSpacing(2)
        title = QLabel("Edit Action Order")
        title.setObjectName("DialogTitle")
        subtitle = QLabel("Rearrange actions and control visibility.")
        subtitle.setObjectName("DialogSubtitle")
        title_stack.addWidget(title)
        title_stack.addWidget(subtitle)
        title_row.addLayout(title_stack, 1)
        layout.addLayout(title_row)

        self.list_widget = ActionOrderListWidget()
        self.list_widget.currentRowChanged.connect(lambda *_: self._update_button_states())
        self.list_widget.itemSelectionChanged.connect(self._update_button_states)
        self.list_widget.orderChanged.connect(self._sync_items_from_list)
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
        note = QLabel("Drag items or use the controls below to reorder actions.")
        note.setObjectName("SettingsNote")
        layout.addWidget(note)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        style_dialog_buttons(buttons)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._refresh()
        self.resize(760, 680)

    def _refresh(self, select_rows: int | list[int] | None = 0) -> None:
        self.list_widget.clear()
        for item in self.items:
            label = ("Hidden" if item["hidden"] else "Visible").ljust(8)
            list_item = QListWidgetItem(f"::::   {label}   {item['name']}")
            list_item.setData(Qt.UserRole, dict(item))
            list_item.setSizeHint(QSize(0, 42))
            if item["hidden"]:
                list_item.setForeground(QColor("#8ea0bf"))
            list_item.setFlags((list_item.flags() | Qt.ItemIsDragEnabled) & ~Qt.ItemIsDropEnabled)
            self.list_widget.addItem(list_item)
        if self.items:
            if select_rows is None:
                select_rows = []
            if isinstance(select_rows, int):
                select_rows = [select_rows]
            clamped_rows = [max(0, min(row, len(self.items) - 1)) for row in select_rows]
            self.list_widget.clearSelection()
            for row in clamped_rows:
                self.list_widget.item(row).setSelected(True)
            self.list_widget.setCurrentRow(clamped_rows[0] if clamped_rows else 0, QItemSelectionModel.NoUpdate)
        self._update_button_states()

    def _move(self, offset: int) -> None:
        rows = self._selected_rows()
        if not rows:
            return
        if offset < 0 and rows[0] <= 0:
            return
        if offset > 0 and rows[-1] >= len(self.items) - 1:
            return
        if offset < 0:
            for row in rows:
                self.items[row - 1], self.items[row] = self.items[row], self.items[row - 1]
        else:
            for row in reversed(rows):
                self.items[row + 1], self.items[row] = self.items[row], self.items[row + 1]
        self._refresh([row + offset for row in rows])

    def _toggle(self) -> None:
        rows = self._selected_rows()
        if not rows:
            return
        for row in rows:
            self.items[row]["hidden"] = not self.items[row]["hidden"]
        self._refresh(rows)

    def _reset(self) -> None:
        self.items = [{"name": name, "hidden": False} for name in self.default_order]
        self._refresh()

    def _delete_custom_action(self) -> None:
        rows = self._selected_rows()
        if not rows or any(not self._is_custom_action(self.items[row]["name"]) for row in rows):
            return
        custom_names = [self.items[row]["name"].removeprefix("Custom: ") for row in rows]
        action_word = "action" if len(custom_names) == 1 else "actions"
        names_preview = ", ".join(custom_names[:4]) + ("..." if len(custom_names) > 4 else "")
        choice = QMessageBox.question(
            self,
            "Delete Custom Action",
            f"Delete the selected custom {action_word}: {names_preview}? This cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if choice != QMessageBox.Yes:
            return
        for row in reversed(rows):
            display_name = self.items[row]["name"]
            self.deleted_custom_actions.append(display_name.removeprefix("Custom: "))
            del self.items[row]
            self.default_order = [item for item in self.default_order if item != display_name]
        self._refresh(min(rows[0], len(self.items) - 1) if self.items else None)

    def _update_button_states(self) -> None:
        rows = self._selected_rows()
        has_selection = bool(rows)
        self.move_up_button.setEnabled(has_selection and rows[0] > 0)
        self.move_down_button.setEnabled(has_selection and rows[-1] < len(self.items) - 1)
        self.toggle_button.setEnabled(has_selection)
        self.delete_button.setEnabled(has_selection and all(self._is_custom_action(self.items[row]["name"]) for row in rows))

    def _selected_rows(self) -> list[int]:
        return sorted(index.row() for index in self.list_widget.selectedIndexes())

    def _sync_items_from_list(self) -> None:
        synced: list[dict[str, str | bool]] = []
        for row in range(self.list_widget.count()):
            data = self.list_widget.item(row).data(Qt.UserRole)
            if isinstance(data, dict) and "name" in data:
                synced.append({"name": str(data["name"]), "hidden": bool(data.get("hidden", False))})
        if len(synced) == len(self.items):
            self.items = synced
        self._update_button_states()

    @staticmethod
    def _is_custom_action(display_name: str) -> bool:
        return display_name.startswith("Custom: ")

    def _save(self) -> None:
        ordered = [item["name"] for item in self.items]
        hidden = [item["name"] for item in self.items if item["hidden"]]
        self.result = (ordered, hidden)
        self.accept()


class SettingsDialog(QDialog):
    checkUpdatesRequested = Signal()

    def __init__(self, settings: AppSettings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setObjectName("SettingsDialog")
        self.result = AppSettings.from_dict(as_settings_dict(settings))
        self._original_dark_mode = self.result.dark_mode
        self._section_icons: list[tuple[QLabel, str, int]] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 14)
        layout.setSpacing(10)

        title_row = QHBoxLayout()
        title = QLabel("Settings")
        title.setObjectName("DialogTitle")
        title_row.addWidget(title)
        title_row.addStretch(1)
        version_label = QLabel(f"Version {APP_VERSION}")
        version_label.setObjectName("VersionLabel")
        title_row.addWidget(version_label)
        layout.addLayout(title_row)

        input_section, input_form = self._settings_section("Input / Timing", "clock")
        self.animation_speed = self._spin(1, 10, self.result.mouse_animation_speed)
        input_form.addRow(
            make_help_label(
                self,
                "Mouse animation speed (1-10)",
                "A scale of 1-10 for setting animation speed - 1 being the slowest, 10 being the fastest. The standard speed is 5.",
            ),
            self.animation_speed,
        )
        self.enhanced_mouse = QCheckBox("Enhanced humanlike animated mouse movement")
        self.enhanced_mouse.setChecked(self.result.enhanced_humanlike_mouse)
        input_form.addRow(
            make_help_label(
                self,
                "Animated mouse movement style",
                "When enabled, actions that already animate the mouse use more varied curves, pauses, overshoots, and settling. Normal click and move actions are unchanged.",
            ),
            self.enhanced_mouse,
        )
        input_form.addRow(
            make_help_label(
                self,
                "Mouse click down/up delay",
                "Sets a random time delay between a mouse being clicked down and being released.",
            ),
            self._range_row("Random value between", "and", "milliseconds", self.result.mouse_click_delay_min_ms, self.result.mouse_click_delay_max_ms, "mouse"),
        )
        input_form.addRow(
            make_help_label(
                self,
                "Key press down/up delay",
                "Sets a random time delay between a key being pressed down and being released.",
            ),
            self._range_row("Random value between", "and", "milliseconds", self.result.key_press_delay_min_ms, self.result.key_press_delay_max_ms, "key"),
        )
        layout.addWidget(input_section)

        storage_section, storage_form = self._settings_section("Storage & Appearance", "load")
        storage_form.addRow("Default Script Location Folder", self._script_folder_row())
        self.theme_button = QPushButton()
        self.theme_button.clicked.connect(self._toggle_theme_choice)
        self._sync_theme_button()
        storage_form.addRow("Theme", self.theme_button)
        layout.addWidget(storage_section)

        controls_section, controls_form = self._settings_section("Controls / Keybinds", "keybind")
        self.start_keybind = KeyCaptureLineEdit(self.result.start_keybind)
        self.start_keybind.setToolTip("Click here, then press the key or key combination to assign Start/Stop.")
        controls_form.addRow("Start / Stop Keybind", self.start_keybind)
        self.pause_keybind = KeyCaptureLineEdit(self.result.pause_keybind)
        self.pause_keybind.setToolTip("Click here, then press the key or key combination to assign Pause/Unpause.")
        controls_form.addRow("Pause / Unpause Keybind", self.pause_keybind)
        layout.addWidget(controls_section)

        behavior_section, behavior_form = self._settings_section("Behavior", "settings")
        self.remember_geometry = QCheckBox()
        self.remember_geometry.setChecked(self.result.remember_window_geometry)
        behavior_form.addRow("Remember Last Position && Size", self.remember_geometry)
        layout.addWidget(behavior_section)

        note = QLabel("These settings are saved for Anz Clicker and applied when scripts run.")
        note.setObjectName("SettingsNote")
        note.setWordWrap(True)
        layout.addWidget(note)

        bottom_row = QHBoxLayout()
        reset_button = QPushButton("Reset to Defaults")
        reset_button.clicked.connect(self._reset_to_defaults)
        bottom_row.addWidget(reset_button)
        disclaimer_button = QPushButton("Disclaimer")
        disclaimer_button.clicked.connect(self._show_disclaimer)
        bottom_row.addWidget(disclaimer_button)
        self.check_updates_button = QPushButton("Check for Updates")
        self.check_updates_button.clicked.connect(self.checkUpdatesRequested.emit)
        bottom_row.addWidget(self.check_updates_button)
        bottom_row.addStretch(1)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        style_dialog_buttons(buttons)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        bottom_row.addWidget(buttons)
        layout.addLayout(bottom_row)
        self.resize(840, 570)

    def _settings_section(self, title: str, icon_name: str) -> tuple[QFrame, QFormLayout]:
        section = QFrame()
        section.setObjectName("SettingsSection")
        outer = QVBoxLayout(section)
        outer.setContentsMargins(14, 11, 14, 12)
        outer.setSpacing(8)

        header = QHBoxLayout()
        header.setSpacing(10)
        icon = QLabel()
        icon.setObjectName("SettingsSectionIcon")
        icon.setAlignment(Qt.AlignCenter)
        self._section_icons.append((icon, icon_name, 20))
        self._apply_section_icon(icon, icon_name, 20)
        header.addWidget(icon)
        title_label = QLabel(title)
        title_label.setObjectName("SettingsSectionTitle")
        header.addWidget(title_label)
        header.addStretch(1)
        outer.addLayout(header)

        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        form.setLabelAlignment(Qt.AlignLeft)
        form.setFormAlignment(Qt.AlignTop)
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(8)
        outer.addLayout(form)
        return section, form

    def _apply_section_icon(self, label: QLabel, icon_name: str, size: int) -> None:
        label.setPixmap(app_icon(icon_name, size=size, dark=self.result.dark_mode).pixmap(size, size))

    def _refresh_section_icons(self) -> None:
        for label, icon_name, size in self._section_icons:
            self._apply_section_icon(label, icon_name, size)

    def set_update_checking(self, checking: bool) -> None:
        self.check_updates_button.setEnabled(not checking)
        self.check_updates_button.setText("Checking..." if checking else "Check for Updates")

    def save_for_update(self) -> None:
        self._save()

    def _show_disclaimer(self) -> None:
        QMessageBox.warning(
            self,
            "Anz Clicker Disclaimer",
            "Anz Clicker should not be assumed to be undetectable by anti-cheat or automation-detection "
            "systems used by games or other software.\n\n"
            "Using automation may violate the rules or terms of a game, service, or application and may "
            "result in warnings, suspensions, bans, or other action against an account. The creator is not "
            "responsible for consequences resulting from use of this tool.\n\n"
            "Anz Clicker is provided strictly as a use-at-your-own-risk tool. Review the applicable rules "
            "before using it.",
        )

    def _spin(self, minimum: int, maximum: int, value: int) -> QSpinBox:
        field = PlaceholderSpinBox()
        field.setButtonSymbols(QSpinBox.NoButtons)
        field.setRange(minimum, maximum)
        field.setValue(value)
        field.setMinimumWidth(96)
        if minimum <= 0 <= maximum:
            field.lineEdit().setPlaceholderText("0")
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
        start_dir = self.script_folder.text().strip() or str(scripts_dir())
        start_path = Path(start_dir)
        if not start_path.is_absolute():
            start_dir = str(storage_root() / start_path)
        selected = QFileDialog.getExistingDirectory(self, "Choose Default Script Folder", start_dir)
        if selected:
            self.script_folder.setText(selected)

    def _save(self) -> None:
        start_keybind = self.start_keybind.text().strip()
        pause_keybind = self.pause_keybind.text().strip()
        if start_keybind and pause_keybind and start_keybind.lower() == pause_keybind.lower():
            QMessageBox.warning(
                self,
                "Duplicate Keybind",
                "Start / Stop and Pause / Unpause cannot use the same keybind.",
            )
            return
        self.result = AppSettings(
            mouse_animation_speed=self.animation_speed.value(),
            enhanced_humanlike_mouse=self.enhanced_mouse.isChecked(),
            mouse_click_delay_min_ms=self.mouse_delay_min.value(),
            mouse_click_delay_max_ms=self.mouse_delay_max.value(),
            key_press_delay_min_ms=self.key_delay_min.value(),
            key_press_delay_max_ms=self.key_delay_max.value(),
            default_script_folder=self.script_folder.text().strip(),
            dark_mode=self.result.dark_mode,
            remember_window_geometry=self.remember_geometry.isChecked(),
            window_geometry=self.result.window_geometry,
            start_keybind=start_keybind,
            pause_keybind=pause_keybind,
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
        self.start_keybind.setText(self.result.start_keybind)
        self.pause_keybind.setText(self.result.pause_keybind)
        self._sync_theme_button()
        self._preview_theme_choice()
        self.remember_geometry.setChecked(self.result.remember_window_geometry)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        focused = QApplication.focusWidget()
        if focused and self.isAncestorOf(focused):
            focused.clearFocus()
        super().mousePressEvent(event)

    def _toggle_theme_choice(self) -> None:
        self.result.dark_mode = not self.result.dark_mode
        self._sync_theme_button()
        self._preview_theme_choice()

    def _sync_theme_button(self) -> None:
        if not hasattr(self, "theme_button"):
            return
        self.theme_button.setText("Dark Mode" if self.result.dark_mode else "Light Mode")
        self._refresh_section_icons()

    def _preview_theme_choice(self) -> None:
        parent = self.parent()
        if parent is not None and hasattr(parent, "apply_theme"):
            parent.apply_theme(self.result.dark_mode)

    def reject(self) -> None:
        parent = self.parent()
        if parent is not None and hasattr(parent, "apply_theme"):
            parent.apply_theme(self._original_dark_mode)
        super().reject()


def as_settings_dict(settings: AppSettings) -> dict[str, int | str | bool]:
    return {
        "mouse_animation_speed": settings.mouse_animation_speed,
        "enhanced_humanlike_mouse": settings.enhanced_humanlike_mouse,
        "mouse_click_delay_min_ms": settings.mouse_click_delay_min_ms,
        "mouse_click_delay_max_ms": settings.mouse_click_delay_max_ms,
        "key_press_delay_min_ms": settings.key_press_delay_min_ms,
        "key_press_delay_max_ms": settings.key_press_delay_max_ms,
        "default_script_folder": settings.default_script_folder,
        "dark_mode": settings.dark_mode,
        "remember_window_geometry": settings.remember_window_geometry,
        "window_geometry": settings.window_geometry,
        "start_keybind": settings.start_keybind,
        "pause_keybind": settings.pause_keybind,
    }


__all__ = ["ActionOrderDialog", "SettingsDialog", "as_settings_dict"]
