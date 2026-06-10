from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
import random
import sys
import time

from PySide6.QtCore import QByteArray, QCoreApplication, QEvent, QModelIndex, QPoint, Qt, Signal, QTimer
from PySide6.QtGui import QColor, QIcon, QPalette
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QInputDialog,
    QProgressBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from actions import Action, ActionType, PositionMode, ScreenArea
from app_settings import AppSettings
import input_controller
from preset_store import PresetStore
from runner import ActionRunner, RuntimePlanError
import screen_tools
from .constants import (
    APP_TITLE,
    APP_VERSION,
    BACKGROUND_GROUP,
    BUILT_IN_ACTION_TYPES,
    PRESET_PREFIX,
    SEQUENTIAL_GROUP,
)
from .action_editor import ActionEditorDialog
from .dialogs import ActionOrderDialog, SettingsDialog
from .icons import app_base_dir, app_icon, resource_path
from .paths import (
    captures_dir,
    ensure_user_directories,
    migrate_legacy_user_data,
    presets_path,
    settings_path,
)
from .theme import build_stylesheet


from .widgets import (
    ActionTableModel,
    ActionTableView,
    KeyCaptureLineEdit,
    QueuePane,
    SidebarItem,
)
class MainWindow(QMainWindow):
    runnerStatus = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.dark_theme = True
        self.icon_buttons: list[tuple[QPushButton, str, int]] = []
        self.setWindowTitle(APP_TITLE)
        self.setMinimumSize(1040, 680)
        logo = resource_path("zabian_logo.png")
        if logo.exists():
            self.setWindowIcon(QIcon(str(logo)))

        migrate_legacy_user_data()
        ensure_user_directories()
        self.settings_path = settings_path()
        self.app_settings = AppSettings.load(self.settings_path)
        screen_tools.configure_ocr(app_base_dir())
        screen_tools.configure_captures_dir(captures_dir())
        input_controller.configure_input_timing(
            mouse_animation_speed=self.app_settings.mouse_animation_speed,
            enhanced_humanlike_mouse=self.app_settings.enhanced_humanlike_mouse,
            mouse_click_delay_min_ms=self.app_settings.mouse_click_delay_min_ms,
            mouse_click_delay_max_ms=self.app_settings.mouse_click_delay_max_ms,
            key_press_delay_min_ms=self.app_settings.key_press_delay_min_ms,
            key_press_delay_max_ms=self.app_settings.key_press_delay_max_ms,
        )
        self._loading_keybinds = True
        if hasattr(self, "start_key_input"):
            self.start_key_input.setText(self.app_settings.start_keybind)
        if hasattr(self, "pause_key_input"):
            self.pause_key_input.setText(self.app_settings.pause_keybind)
        self._loading_keybinds = False
        self._apply_keybinds()
        self.preset_store = PresetStore(presets_path())
        self.runner = ActionRunner(lambda text: self.runnerStatus.emit(text), settings=self.app_settings)
        self.runnerStatus.connect(self._set_status)
        self.run_controls_active = False
        self.run_started_at: float | None = None
        self.run_last_tick_at: float | None = None
        self.run_elapsed_active_seconds = 0.0
        self.run_progress_current = 0
        self.run_progress_total = 0
        self.run_progress_completed = False
        self.run_timer = QTimer(self)
        self.run_timer.timeout.connect(self._update_run_time)
        self._open_overflow_group: str | None = None
        self._open_overflow_menu: QMenu | None = None
        self._open_editors: list[ActionEditorDialog] = []
        self._capturing_keybind = False
        self._loading_keybinds = True
        self.current_script_path: Path | None = None
        self.current_script_metadata = self._new_script_metadata()
        self.is_dirty = False
        self._suppress_dirty = True
        self.sequential_model = ActionTableModel([])
        self.background_model = ActionTableModel([])

        central = QWidget()
        self.setCentralWidget(central)
        root = QGridLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setHorizontalSpacing(0)
        root.setVerticalSpacing(0)
        root.setColumnStretch(1, 1)
        root.setRowStretch(1, 1)

        root.addWidget(self._build_topbar(), 0, 0, 1, 3)
        self.sidebar = self._build_sidebar()
        root.addWidget(self.sidebar, 1, 0)
        root.addWidget(self._build_center_panel(), 1, 1)
        root.addWidget(self._build_right_panel(), 1, 2)

        self.apply_theme(dark=True)
        self._connect_dirty_tracking()
        self._suppress_dirty = False
        self._update_window_title()
        self.update_action_button_states()
        self._restore_window_geometry()
        self.start_shortcut = QShortcut(self)
        self.start_shortcut.activated.connect(self.toggle_run)
        self.pause_shortcut = QShortcut(self)
        self.pause_shortcut.activated.connect(self.toggle_pause)
        self.new_script_shortcut = QShortcut(QKeySequence("Ctrl+N"), self)
        self.new_script_shortcut.activated.connect(self.new_script)
        self.save_script_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        self.save_script_shortcut.activated.connect(self.save_script)
        self.save_as_script_shortcut = QShortcut(QKeySequence("Ctrl+Shift+S"), self)
        self.save_as_script_shortcut.activated.connect(self.save_as_script)
        self._loading_keybinds = False
        self._apply_keybinds()

    def _sample_sequential_actions(self) -> list[Action]:
        return [
            Action(action_type=ActionType.LEFT_CLICK.value, position_mode=PositionMode.COORDINATES.value, x=1250, y=680, delay_milliseconds=100, comment="Primary click", execution_group=SEQUENTIAL_GROUP),
            Action(action_type=ActionType.TYPE_KEY.value, key="Hello World", delay_milliseconds=200, comment="Type sample text", execution_group=SEQUENTIAL_GROUP),
            Action(action_type=ActionType.WAIT.value, delay_seconds=1, comment="Let the UI settle", execution_group=SEQUENTIAL_GROUP),
            Action(action_type=ActionType.RIGHT_CLICK.value, enabled=False, position_mode=PositionMode.COORDINATES.value, x=980, y=540, delay_milliseconds=100, comment="Disabled example", execution_group=SEQUENTIAL_GROUP),
        ]

    def _sample_background_actions(self) -> list[Action]:
        return [
            Action(action_type=ActionType.PRESS_SPACEBAR.value, key="space", delay_seconds=30, repeat=12, comment="Background keepalive", execution_group=BACKGROUND_GROUP),
            Action(action_type=ActionType.WAIT_FOR_PICTURE.value, picture_area=ScreenArea(0, 0, 640, 360), picture_wait_milliseconds=250, comment="Watch for reference image", execution_group=BACKGROUND_GROUP),
        ]

    def _nav_item(self, label: str, icon_name: str, description: str = "", checked: bool = False) -> SidebarItem:
        item = SidebarItem(label, self._make_icon(icon_name), description)
        self.icon_buttons.append((item, icon_name, 17))
        return item

    def _make_icon(self, name: str, size: int = 22) -> QIcon:
        return app_icon(name, size=size, dark=self.dark_theme)

    def _set_icon(self, button: QPushButton, name: str, size: int = 22) -> None:
        button.setIcon(self._make_icon(name, size))
        self.icon_buttons.append((button, name, size))

    def _build_topbar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("TopBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(10)

        logo = QLabel()
        logo_path = resource_path("zabian_logo.png")
        if logo_path.exists():
            logo.setPixmap(QIcon(str(logo_path)).pixmap(30, 30))
        layout.addWidget(logo)

        self.app_title_label = QLabel(APP_TITLE)
        self.app_title_label.setObjectName("AppTitle")
        layout.addWidget(self.app_title_label)
        layout.addStretch(1)

        for label, icon_name in (
            ("New Script", "add"),
            ("Save Script", "save"),
            ("Save As", "save"),
            ("Load Script", "load"),
        ):
            button = QPushButton(label)
            self._set_icon(button, icon_name)
            button.setMinimumWidth(112)
            if label == "New Script":
                button.clicked.connect(self.new_script)
            elif label == "Save Script":
                button.clicked.connect(self.save_script)
            elif label == "Save As":
                button.clicked.connect(self.save_as_script)
            else:
                button.clicked.connect(self.load_script)
            layout.addWidget(button)

        self.theme_button = QPushButton("Dark Mode")
        self._set_icon(self.theme_button, "theme")
        self.theme_button.clicked.connect(self.toggle_theme)
        self.theme_button.setMinimumWidth(110)
        layout.addWidget(self.theme_button)
        return bar

    def _sidebar_section_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("SidebarSection")
        return label

    def _build_sidebar(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("Sidebar")
        panel.setFixedWidth(264)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 18, 14, 14)
        layout.setSpacing(10)

        self.sidebar_toggle = QPushButton("Collapse Sidebar")
        self._set_icon(self.sidebar_toggle, "collapse")
        self.sidebar_toggle.clicked.connect(self.toggle_sidebar)
        layout.addWidget(self.sidebar_toggle)

        self.sidebar_section_labels: list[QLabel] = []
        current_script_label = self._sidebar_section_label("Current Script")
        self.sidebar_section_labels.append(current_script_label)
        layout.addWidget(current_script_label)
        self.primary_sidebar_items = [
            self._nav_item("Add Action", "add", "Create a new action in the current lane.", checked=True),
            self._nav_item("Edit Action", "edit", "Edit the selected action."),
            self._nav_item("Duplicate Action", "duplicate", "Copy the selected action directly below itself."),
            self._nav_item("Delete Action", "delete", "Delete the selected action."),
        ]
        self.primary_sidebar_items[0].clicked.connect(lambda: self.handle_add_request(self.current_group()))
        self.primary_sidebar_items[1].clicked.connect(self.edit_current_row)
        self.primary_sidebar_items[2].clicked.connect(self.duplicate_current_row)
        self.primary_sidebar_items[3].clicked.connect(self.delete_current_row)
        for item in self.primary_sidebar_items:
            layout.addWidget(item)

        layout.addSpacing(6)
        action_library_label = self._sidebar_section_label("Action Library Settings")
        self.sidebar_section_labels.append(action_library_label)
        layout.addWidget(action_library_label)
        self.library_sidebar_items = [
            self._nav_item("Save as Custom Action", "custom", "Save the selected action as a reusable custom preset."),
            self._nav_item("Edit Default Actions", "defaults", "Change default values for action types."),
            self._nav_item("Edit Action Order", "order", "Reorder and hide actions in the library."),
        ]
        self.library_sidebar_items[0].clicked.connect(self.save_selected_as_custom)
        self.library_sidebar_items[1].clicked.connect(self.edit_defaults)
        self.library_sidebar_items[2].clicked.connect(self.edit_action_order)
        for item in self.library_sidebar_items:
            layout.addWidget(item)

        layout.addStretch(1)
        utility_label = self._sidebar_section_label("App Tools")
        self.sidebar_section_labels.append(utility_label)
        layout.addWidget(utility_label)
        self.utility_sidebar_items = [
            self._nav_item("Settings", "settings", "Open app-level settings."),
            self._nav_item("Tutorial", "help", "Open the tutorial and usage guide."),
        ]
        self.utility_sidebar_items[0].clicked.connect(self.open_settings)
        self.utility_sidebar_items[1].clicked.connect(self.open_tutorial)
        for item in self.utility_sidebar_items:
            layout.addWidget(item)

        self.sidebar_items = self.primary_sidebar_items + self.library_sidebar_items + self.utility_sidebar_items
        self.row_selection_buttons = [
            self.primary_sidebar_items[1],
            self.primary_sidebar_items[2],
            self.primary_sidebar_items[3],
            self.library_sidebar_items[0],
        ]
        return panel

    def _build_center_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("CenterPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(0)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("ActionTabs")
        self.sequential_pane = QueuePane("Sequential", self.sequential_model, show_repeat=True)
        self.background_pane = QueuePane("Background", self.background_model, show_repeat=False)
        self.sequential_pane.addRequested.connect(self.handle_add_request)
        self.background_pane.addRequested.connect(self.handle_add_request)
        self.sequential_pane.moveRequested.connect(self.move_current_row)
        self.background_pane.moveRequested.connect(self.move_current_row)
        self.sequential_pane.menuRequested.connect(self.show_queue_menu)
        self.background_pane.menuRequested.connect(self.show_queue_menu)
        self.sequential_pane.overflowRequested.connect(self.show_overflow_menu)
        self.background_pane.overflowRequested.connect(self.show_overflow_menu)
        self.sequential_pane.repeat_input.textChanged.connect(lambda *_: self._mark_dirty())
        self.sequential_pane.random_repeat_input.textChanged.connect(lambda *_: self._mark_dirty())
        self.sequential_pane.table.selectionModel().selectionChanged.connect(lambda *_: self.update_action_button_states())
        self.background_pane.table.selectionModel().selectionChanged.connect(lambda *_: self.update_action_button_states())
        self.sequential_pane.table.editRequested.connect(self.edit_current_row)
        self.background_pane.table.editRequested.connect(self.edit_current_row)
        self.sequential_pane.table.deleteRequested.connect(self.delete_current_row)
        self.background_pane.table.deleteRequested.connect(self.delete_current_row)
        self.tabs.currentChanged.connect(lambda *_: self.update_action_button_states())
        self.tabs.addTab(self.sequential_pane, "Sequential Actions (0)")
        self.tabs.addTab(self.background_pane, "Background Actions (0)")
        self._update_action_tab_labels()
        layout.addWidget(self.tabs)
        return panel

    def _build_right_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("RightPanel")
        panel.setFixedWidth(340)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 18, 18, 18)
        layout.setSpacing(14)

        title = QLabel("Run Controls")
        title.setObjectName("SectionTitle")
        layout.addWidget(title)

        self.start_button = QPushButton("Start")
        self.start_button.setObjectName("PrimaryAction")
        self._set_icon(self.start_button, "start")
        self.start_button.setMinimumHeight(42)
        self.start_button.clicked.connect(self.toggle_run)
        layout.addWidget(self.start_button)

        self.pause_button = QPushButton("Pause")
        self._set_icon(self.pause_button, "pause")
        self.pause_button.setMinimumHeight(40)
        self.pause_button.setEnabled(False)
        self.pause_button.clicked.connect(self.toggle_pause)
        layout.addWidget(self.pause_button)

        keybind_card = self._info_card("Keybinds")
        keybind_layout = keybind_card.layout()
        keybind_layout.addWidget(self._keybind_row("Start", self.app_settings.start_keybind, "start_key_input"))
        keybind_layout.addWidget(self._keybind_row("Pause", self.app_settings.pause_keybind, "pause_key_input"))
        layout.addWidget(keybind_card)

        status_card = self._info_card("Status")
        status_layout = status_card.layout()
        self.status_text = QLabel("Ready")
        self.status_text.setWordWrap(True)
        status_layout.addWidget(self._status_row(self.status_text, "•"))
        self.run_time_value = QLabel("00:00:00")
        self.run_time_value.setObjectName("MetricValue")
        status_layout.addWidget(self._metric_row("Run Time", self.run_time_value))
        self.progress_value = QLabel("0s / 0s (0%)")
        self.progress_value.setObjectName("MetricValue")
        status_layout.addWidget(self._metric_row("Progress", self.progress_value))
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("ProgressBar")
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(10)
        status_layout.addWidget(self.progress_bar)
        layout.addWidget(status_card)
        layout.addStretch(1)
        return panel

    def _info_card(self, title: str) -> QFrame:
        card = QFrame()
        card.setObjectName("InfoCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)
        label = QLabel(title)
        label.setObjectName("CardTitle")
        layout.addWidget(label)
        return card

    def _keybind_row(self, label: str, value: str, attribute_name: str) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.addWidget(QLabel(label))
        field = KeyCaptureLineEdit(value)
        field.setToolTip("Click here, then press the key or key combination to assign.")
        field.setFixedWidth(180)
        field.textChanged.connect(self._apply_keybinds)
        field.captureFocusChanged.connect(self._set_keybind_capture_active)
        setattr(self, attribute_name, field)
        layout.addWidget(field)
        layout.addStretch(1)
        return row

    def _apply_keybinds(self) -> None:
        if hasattr(self, "start_shortcut") and hasattr(self, "start_key_input"):
            self._set_shortcut_sequence(self.start_shortcut, self.start_key_input.text())
        if hasattr(self, "pause_shortcut") and hasattr(self, "pause_key_input"):
            self._set_shortcut_sequence(self.pause_shortcut, self.pause_key_input.text())
        if not self._loading_keybinds and hasattr(self, "start_key_input") and hasattr(self, "pause_key_input"):
            self.app_settings.start_keybind = self.start_key_input.text().strip()
            self.app_settings.pause_keybind = self.pause_key_input.text().strip()
            self._save_app_settings_silent()
        if hasattr(self, "start_button"):
            self._refresh_run_button_labels()

    def _set_shortcut_sequence(self, shortcut: QShortcut, key_text: str) -> None:
        sequence = QKeySequence(key_text.strip())
        shortcut.setKey(sequence)
        shortcut.setEnabled(not self._capturing_keybind and not sequence.isEmpty())

    def _set_keybind_capture_active(self, active: bool) -> None:
        self._capturing_keybind = active
        if hasattr(self, "start_shortcut"):
            self.start_shortcut.setEnabled(not active and not self.start_shortcut.key().isEmpty())
        if hasattr(self, "pause_shortcut"):
            self.pause_shortcut.setEnabled(not active and not self.pause_shortcut.key().isEmpty())
        if not active:
            self._apply_keybinds()

    def _keybind_suffix(self, field_name: str) -> str:
        if not hasattr(self, field_name):
            return ""
        key_text = getattr(self, field_name).text().strip()
        return f" ({key_text})" if key_text else ""

    def _refresh_run_button_labels(self) -> None:
        if hasattr(self, "start_button"):
            start_label = "Stop" if self.run_controls_active else "Start"
            self.start_button.setText(f"{start_label}{self._keybind_suffix('start_key_input')}")
        if hasattr(self, "pause_button"):
            pause_label = "Unpause" if self.runner.is_paused else "Pause"
            self.pause_button.setText(f"{pause_label}{self._keybind_suffix('pause_key_input')}")

    def _status_row(self, label: str | QLabel, icon_text: str) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        dot = QLabel(icon_text)
        dot.setStyleSheet("color: #22c55e; font-size: 18px;")
        layout.addWidget(dot)
        layout.addWidget(label if isinstance(label, QLabel) else QLabel(label))
        layout.addStretch(1)
        return row

    def _metric_row(self, label: str, value: str | QLabel) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel(label))
        layout.addStretch(1)
        value_label = value if isinstance(value, QLabel) else QLabel(value)
        value_label.setObjectName("MetricValue")
        layout.addWidget(value_label)
        return row

    def toggle_sidebar(self) -> None:
        compact = self.sidebar.width() > 130
        self.sidebar.setFixedWidth(112 if compact else 264)
        self.sidebar_toggle.setText("Expand" if compact else "Collapse Sidebar")
        self.sidebar_toggle.setIcon(self._make_icon("expand" if compact else "collapse"))
        self._replace_icon_registration(self.sidebar_toggle, "expand" if compact else "collapse", 22)
        for label in self.sidebar_section_labels:
            label.setVisible(not compact)
        for item in self.sidebar_items:
            item.set_compact(compact)

    def _replace_icon_registration(self, button: QPushButton, name: str, size: int) -> None:
        self.icon_buttons = [(existing, icon_name, icon_size) for existing, icon_name, icon_size in self.icon_buttons if existing is not button]
        self.icon_buttons.append((button, name, size))

    def _connect_dirty_tracking(self) -> None:
        for model in (self.sequential_model, self.background_model):
            model.dataChanged.connect(lambda *_: self._mark_dirty())
            model.rowsInserted.connect(lambda *_: self._mark_dirty())
            model.rowsInserted.connect(lambda *_: self._update_action_tab_labels())
            model.rowsRemoved.connect(lambda *_: self._mark_dirty())
            model.rowsRemoved.connect(lambda *_: self._update_action_tab_labels())
            model.modelReset.connect(lambda *_: self._mark_dirty())
            model.modelReset.connect(lambda *_: self._update_action_tab_labels())

    def _update_action_tab_labels(self) -> None:
        if not hasattr(self, "tabs"):
            return
        self.tabs.setTabText(0, f"Sequential Actions ({self.sequential_model.rowCount()})")
        self.tabs.setTabText(1, f"Background Actions ({self.background_model.rowCount()})")

    def _mark_dirty(self) -> None:
        if self._suppress_dirty:
            return
        self.is_dirty = True
        self._update_window_title()

    def _set_clean(self) -> None:
        self.is_dirty = False
        self._update_window_title()

    def _script_display_name(self) -> str:
        return self.current_script_path.stem if self.current_script_path else ""

    def _update_window_title(self) -> None:
        script_name = self._script_display_name()
        title = f"{APP_TITLE} - {script_name}" if script_name else APP_TITLE
        if self.is_dirty:
            title += " *"
        self.setWindowTitle(title)
        if hasattr(self, "app_title_label"):
            self.app_title_label.setText(title)

    def current_group(self) -> str:
        return "Sequential" if self.tabs.currentIndex() == 0 else "Background"

    def current_pane(self) -> QueuePane:
        return self.sequential_pane if self.current_group() == "Sequential" else self.background_pane

    def current_model(self) -> ActionTableModel:
        return self.current_pane().model

    def current_table(self) -> ActionTableView:
        return self.current_pane().table

    def current_row(self) -> int:
        index = self.current_table().currentIndex()
        return index.row() if index.isValid() else -1

    def _retire_dialog(self, dialog: QDialog) -> None:
        dialog.setWindowModality(Qt.NonModal)
        dialog.hide()
        dialog.setParent(None)
        dialog.deleteLater()
        QApplication.processEvents()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        QApplication.processEvents()

    def _show_action_editor(self, editor: ActionEditorDialog, on_accept) -> None:
        editor.setWindowModality(Qt.NonModal)
        editor.setModal(False)
        self._open_editors.append(editor)

        def finish(result_code: int) -> None:
            try:
                result = Action.from_dict(editor.result.to_dict()) if result_code == QDialog.Accepted and editor.result else None
                if result:
                    on_accept(result)
            finally:
                if editor in self._open_editors:
                    self._open_editors.remove(editor)
                self._retire_dialog(editor)

        editor.finished.connect(finish)
        editor.show()
        editor.raise_()
        editor.activateWindow()

    def action_choices(self) -> list[str]:
        return self.preset_store.visible_action_names(BUILT_IN_ACTION_TYPES)

    def _top_visible_action_template(self) -> Action:
        visible = self.action_choices()
        if not visible:
            return Action(action_type=ActionType.LEFT_CLICK.value)
        first = visible[0]
        if first.startswith(PRESET_PREFIX):
            preset = self.preset_store.custom_action(first.removeprefix(PRESET_PREFIX))
            return Action.from_dict(preset.to_dict()) if preset else Action(action_type=ActionType.LEFT_CLICK.value)
        default = self.preset_store.default_for(first)
        return Action.from_dict(default.to_dict()) if default else Action(action_type=first)

    def handle_add_request(self, group_name: str) -> None:
        model = self.sequential_model if group_name == "Sequential" else self.background_model
        action = self._top_visible_action_template()
        action.execution_group = SEQUENTIAL_GROUP if group_name == "Sequential" else BACKGROUND_GROUP
        editor = ActionEditorDialog(action, self.action_choices(), self.preset_store, self, "Add Action")

        def accept(result: Action) -> None:
            result.execution_group = action.execution_group
            model.add_action(result)
            table = self.sequential_pane.table if group_name == "Sequential" else self.background_pane.table
            table.selectRow(model.rowCount() - 1)
            self.update_action_button_states()

        self._show_action_editor(editor, accept)

    def edit_current_row(self) -> None:
        row = self.current_row()
        if row < 0:
            return
        action = Action.from_dict(self.current_model().actions[row].to_dict())
        editor = ActionEditorDialog(action, self.action_choices(), self.preset_store, self, "Edit Action")

        def accept(result: Action) -> None:
            result.execution_group = action.execution_group
            self.current_model().replace_row(row, result)
            self.current_table().selectRow(row)
            self.update_action_button_states()

        self._show_action_editor(editor, accept)

    def move_current_row(self, offset: int) -> None:
        row = self.current_row()
        if row < 0:
            return
        new_row = self.current_model().move_row(row, offset)
        self.current_table().selectRow(new_row)
        self.update_action_button_states()

    def show_queue_menu(self, group_name: str, global_pos: QPoint) -> None:
        table = self.sequential_pane.table if group_name == "Sequential" else self.background_pane.table
        local = table.viewport().mapFromGlobal(global_pos)
        if table.viewport().rect().contains(local):
            index = table.indexAt(local)
            if index.isValid():
                table.selectRow(index.row())
        row = self.current_row()
        menu = QMenu(self)
        self._menu_action(menu, "Add Action", "add", lambda: self.handle_add_request(group_name))
        self._menu_action(menu, "Edit Action", "edit", self.edit_current_row)
        self._menu_action(menu, "Delete Action", "delete", self.delete_current_row)
        self._menu_action(menu, "Duplicate Action", "duplicate", self.duplicate_current_row)
        menu.addSeparator()
        self._menu_action(menu, "Move Up", "up", lambda: self.move_current_row(-1))
        self._menu_action(menu, "Move Down", "down", lambda: self.move_current_row(1))
        self._menu_action(menu, "Toggle Enabled", "defaults", self.toggle_current_enabled)
        menu.addSeparator()
        if group_name == "Sequential":
            self._menu_action(menu, "Send to Background Actions", "order", self.send_current_to_background)
        else:
            self._menu_action(menu, "Send to Sequential", "order", self.send_current_to_sequential)
        for action in menu.actions():
            if action.text() in {"Edit Action", "Delete Action", "Duplicate Action", "Move Up", "Move Down", "Toggle Enabled"} and row < 0:
                action.setEnabled(False)
        menu.exec(global_pos)

    def show_overflow_menu(self, group_name: str, global_pos: QPoint) -> None:
        if self._open_overflow_menu and self._open_overflow_menu.isVisible() and self._open_overflow_group == group_name:
            self._open_overflow_menu.close()
            self._open_overflow_menu = None
            self._open_overflow_group = None
            return
        menu = QMenu(self)
        self._open_overflow_menu = menu
        self._open_overflow_group = group_name
        self._menu_action(menu, "Add Action", "add", lambda: self.handle_add_request(group_name))
        menu.addSeparator()
        self._menu_action(menu, "Move Up", "up", lambda: self.move_current_row(-1))
        self._menu_action(menu, "Move Down", "down", lambda: self.move_current_row(1))
        if group_name == "Sequential":
            self._menu_action(menu, "Send to Background Actions", "order", self.send_current_to_background)
        else:
            self._menu_action(menu, "Send to Sequential", "order", self.send_current_to_sequential)
        menu.addSeparator()
        self._menu_action(menu, "Load Sample Actions", "load", self.load_sample_actions)
        row = self.current_row()
        for action in menu.actions():
            if action.text() in {"Move Up", "Move Down", "Send to Background Actions", "Send to Sequential"} and row < 0:
                action.setEnabled(False)
        menu.aboutToHide.connect(lambda: self._clear_overflow_menu(menu))
        menu.popup(global_pos)

    def _clear_overflow_menu(self, menu: QMenu) -> None:
        if self._open_overflow_menu is menu:
            self._open_overflow_menu = None
            self._open_overflow_group = None

    def _menu_action(self, menu: QMenu, label: str, icon_name: str, callback=None):
        action = menu.addAction(self._make_icon(icon_name, 18), label)
        if callback:
            action.triggered.connect(callback)
        return action

    def delete_current_row(self) -> None:
        row = self.current_row()
        if row >= 0:
            model = self.current_model()
            model.remove_row(row)
            if model.rowCount():
                self.current_table().selectRow(min(row, model.rowCount() - 1))
            self.update_action_button_states()

    def duplicate_current_row(self) -> None:
        row = self.current_row()
        if row >= 0:
            new_row = self.current_model().duplicate_row(row)
            self.current_table().selectRow(new_row)
            self.update_action_button_states()

    def toggle_current_enabled(self) -> None:
        row = self.current_row()
        if row < 0:
            return
        index = self.current_model().index(row, 1)
        current = self.current_model().data(index, Qt.CheckStateRole)
        self.current_model().setData(index, Qt.Unchecked if current == Qt.Checked else Qt.Checked, Qt.CheckStateRole)
        self.update_action_button_states()

    def send_current_to_background(self) -> None:
        if self.tabs.currentIndex() == 1:
            return
        row = self.current_row()
        if row < 0:
            return
        action = self.sequential_model.take_row(row)
        if action:
            action.execution_group = BACKGROUND_GROUP
            self.background_model.insert_existing_row(self.background_model.rowCount(), action)
            self._select_nearest_row(self.sequential_pane.table, self.sequential_model, row)
            self.update_action_button_states()

    def send_current_to_sequential(self) -> None:
        if self.tabs.currentIndex() == 0:
            return
        row = self.current_row()
        if row < 0:
            return
        action = self.background_model.take_row(row)
        if action:
            action.execution_group = SEQUENTIAL_GROUP
            self.sequential_model.insert_existing_row(self.sequential_model.rowCount(), action)
            self._select_nearest_row(self.background_pane.table, self.background_model, row)
            self.update_action_button_states()

    def _select_nearest_row(self, table: ActionTableView, model: ActionTableModel, row: int) -> None:
        if model.rowCount():
            table.selectRow(min(row, model.rowCount() - 1))
        else:
            table.clearSelection()
            table.setCurrentIndex(QModelIndex())

    def save_selected_as_custom(self) -> None:
        row = self.current_row()
        if row < 0:
            return
        name, ok = QInputDialog.getText(self, "Save Custom Action", "Custom action name:")
        if not ok or not name.strip():
            return
        custom_name = name.strip()
        if not self._confirm_overwrite_custom_action(custom_name):
            return
        action = Action.from_dict(self.current_model().actions[row].to_dict())
        action.preset_name = custom_name
        self.preset_store.save_custom_action(action.preset_name, action)
        self.current_model().replace_row(row, action)

    def edit_defaults(self) -> None:
        row = self.current_row()
        template = Action.from_dict(self.current_model().actions[row].to_dict()) if row >= 0 else self._top_visible_action_template()
        editor = ActionEditorDialog(template, self.action_choices(), self.preset_store, self, "Edit Default Actions")

        def accept(result: Action) -> None:
            if result.preset_name:
                self.preset_store.save_custom_action(result.preset_name, result)
            else:
                result.preset_name = ""
                self.preset_store.set_default(result)

        self._show_action_editor(editor, accept)

    def edit_action_order(self) -> None:
        default_order = BUILT_IN_ACTION_TYPES + [f"{PRESET_PREFIX}{name}" for name in self.preset_store.custom_names()]
        editor = ActionOrderDialog(self.preset_store.ordered_action_names(BUILT_IN_ACTION_TYPES), self.preset_store.hidden_actions, default_order, self)
        accepted = editor.exec() == QDialog.Accepted
        result = editor.result
        deleted_custom_actions = list(editor.deleted_custom_actions)
        self._retire_dialog(editor)
        if accepted and result:
            for custom_name in deleted_custom_actions:
                self.preset_store.delete_custom_action(custom_name)
            ordered, hidden = result
            self.preset_store.set_action_catalog(ordered, hidden)

    def _confirm_overwrite_custom_action(self, name: str) -> bool:
        if name not in self.preset_store.custom_actions:
            return True
        choice = QMessageBox.question(
            self,
            "Overwrite Custom Action",
            f'A custom action named "{name}" already exists. Overwrite it?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        return choice == QMessageBox.Yes

    def new_script(self) -> None:
        if not self._confirm_continue_with_unsaved_changes():
            return
        self._suppress_dirty = True
        self.sequential_model.reset_actions([])
        self.background_model.reset_actions([])
        self.sequential_pane.repeat_input.setText("1")
        self.sequential_pane.random_repeat_input.setText("0")
        self._suppress_dirty = False
        self.current_script_path = None
        self.current_script_metadata = self._new_script_metadata()
        self.run_progress_current = 0
        self.run_progress_total = 0
        self.run_progress_completed = False
        self._update_progress_label()
        if hasattr(self, "status_text"):
            self.status_text.setText("Ready")
        self._set_clean()
        self.update_action_button_states()

    def save_script(self) -> bool:
        if self.current_script_path:
            path = self.current_script_path
        else:
            path = self._choose_script_save_path("Save Action Sequence")
            if path is None:
                return False
        if not self._write_script(path):
            return False
        self.current_script_path = path
        self._set_clean()
        return True

    def save_as_script(self) -> bool:
        path = self._choose_script_save_path("Save Action Sequence As")
        if path is None:
            return False
        if not self._write_script(path):
            return False
        self.current_script_path = path
        self._set_clean()
        return True

    def _choose_script_save_path(self, title: str) -> Path | None:
        default_folder = self._default_script_folder()
        default_folder.mkdir(parents=True, exist_ok=True)
        suggested_path = default_folder
        if self.current_script_path:
            suggested_path = default_folder / self.current_script_path.name
        selected, _ = QFileDialog.getSaveFileName(
            self,
            title,
            str(suggested_path),
            "JSON Files (*.json);;All Files (*.*)",
        )
        if not selected:
            return None
        path = Path(selected)
        return path if path.suffix.lower() == ".json" else Path(f"{path}.json")

    def _write_script(self, path: Path) -> bool:
        try:
            sequential_repeat = max(1, int(self.sequential_pane.repeat_input.text() or "1"))
            sequential_random_repeat = max(0, int(self.sequential_pane.random_repeat_input.text() or "0"))
        except ValueError:
            QMessageBox.warning(self, "Invalid Repeat Count", "Sequential repeat counts must be whole numbers.")
            return False
        payload = {
            "metadata": self._metadata_for_save(path),
            "sequential_actions": [action.to_dict() for action in self.sequential_model.actions],
            "parallel_actions": [action.to_dict() for action in self.background_model.actions],
            "sequential_repeat_count": sequential_repeat,
            "sequential_random_repeat_count": sequential_random_repeat,
        }
        try:
            path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except OSError as exc:
            QMessageBox.warning(self, "Save Failed", f"Could not save this script:\n{exc}")
            return False
        return True

    def _confirm_continue_with_unsaved_changes(self) -> bool:
        if not self.is_dirty:
            return True
        choice = QMessageBox.question(
            self,
            "Unsaved Changes",
            "Save changes to the current script before continuing?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
            QMessageBox.Save,
        )
        if choice == QMessageBox.Cancel:
            return False
        if choice == QMessageBox.Save:
            self.save_script()
            return not self.is_dirty
        return True

    def load_script(self) -> None:
        if not self._confirm_continue_with_unsaved_changes():
            return
        default_folder = self._default_script_folder()
        default_folder.mkdir(parents=True, exist_ok=True)
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Action Sequence",
            str(default_folder),
            "JSON Files (*.json);;All Files (*.*)",
        )
        if not path:
            return
        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
            sequential, background, sequential_repeat, random_repeat, metadata = self._parse_script_payload(payload, Path(path))
        except Exception as exc:
            QMessageBox.warning(self, "Load Failed", f"Could not load this script:\n{exc}")
            return
        for action in sequential:
            action.execution_group = SEQUENTIAL_GROUP
        for action in background:
            action.execution_group = BACKGROUND_GROUP
        self._suppress_dirty = True
        self.sequential_model.reset_actions(sequential)
        self.background_model.reset_actions(background)
        self.sequential_pane.repeat_input.setText(str(sequential_repeat))
        self.sequential_pane.random_repeat_input.setText(str(random_repeat))
        self._suppress_dirty = False
        self.current_script_path = Path(path)
        self.current_script_metadata = metadata
        self._select_tab_for_loaded_script()
        self._set_clean()
        self.update_action_button_states()

    def _parse_script_payload(self, payload, path: Path) -> tuple[list[Action], list[Action], int, int, dict[str, str]]:
        if isinstance(payload, list):
            actions = self._parse_action_lane(payload, "legacy action list")
            sequential = [action for action in actions if action.execution_group != BACKGROUND_GROUP]
            background = [action for action in actions if action.execution_group == BACKGROUND_GROUP]
            return sequential, background, 1, 0, self._legacy_script_metadata(path)

        if not isinstance(payload, dict):
            raise ValueError("The selected file is JSON, but it is not an Anz Clicker script.")
        if "sequential_actions" not in payload and "parallel_actions" not in payload:
            raise ValueError("The selected JSON file does not contain Anz Clicker action lists.")

        sequential = self._parse_action_lane(payload.get("sequential_actions", []), "sequential_actions")
        background = self._parse_action_lane(payload.get("parallel_actions", []), "parallel_actions")
        try:
            sequential_repeat = max(1, int(payload.get("sequential_repeat_count", 1) or 1))
            random_repeat = max(0, int(payload.get("sequential_random_repeat_count", 0) or 0))
        except (TypeError, ValueError) as exc:
            raise ValueError("The script contains invalid sequence repeat settings.") from exc
        metadata = self._metadata_from_payload(payload, path)
        return sequential, background, sequential_repeat, random_repeat, metadata

    @staticmethod
    def _parse_action_lane(items, lane_name: str) -> list[Action]:
        if not isinstance(items, list):
            raise ValueError(f'The script field "{lane_name}" must be a list of actions.')
        valid_action_types = {action_type.value for action_type in ActionType}
        actions: list[Action] = []
        for index, item in enumerate(items, start=1):
            if not isinstance(item, dict):
                raise ValueError(f'Action {index} in "{lane_name}" is not a valid action object.')
            action_type = item.get("action_type")
            if action_type not in valid_action_types:
                raise ValueError(f'Action {index} in "{lane_name}" has an unsupported action type: {action_type!r}.')
            try:
                actions.append(Action.from_dict(item))
            except (TypeError, ValueError) as exc:
                raise ValueError(f'Action {index} in "{lane_name}" is not compatible with this version of Anz Clicker.') from exc
        return actions

    @staticmethod
    def _current_metadata_timestamp() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    def _new_script_metadata(self) -> dict[str, str]:
        timestamp = self._current_metadata_timestamp()
        return {
            "created_at": timestamp,
            "modified_at": timestamp,
            "app_version": APP_VERSION,
        }

    def _legacy_script_metadata(self, _path: Path) -> dict[str, str]:
        return self._new_script_metadata()

    def _metadata_from_payload(self, payload: dict, path: Path) -> dict[str, str]:
        raw_metadata = payload.get("metadata")
        if not isinstance(raw_metadata, dict):
            return self._legacy_script_metadata(path)
        metadata = {str(key): str(value) for key, value in raw_metadata.items() if value is not None}
        timestamp = self._current_metadata_timestamp()
        metadata.setdefault("created_at", timestamp)
        metadata.setdefault("modified_at", metadata["created_at"])
        metadata.setdefault("app_version", APP_VERSION)
        return metadata

    def _metadata_for_save(self, path: Path) -> dict[str, str]:
        metadata = dict(self.current_script_metadata or self._new_script_metadata())
        timestamp = self._current_metadata_timestamp()
        metadata.setdefault("created_at", timestamp)
        metadata["modified_at"] = timestamp
        metadata["app_version"] = APP_VERSION
        metadata["name"] = path.stem
        self.current_script_metadata = metadata
        return metadata

    def _select_tab_for_loaded_script(self) -> None:
        if self.sequential_model.rowCount() == 0 and self.background_model.rowCount() > 0:
            self.tabs.setCurrentIndex(1)
        else:
            self.tabs.setCurrentIndex(0)

    def _default_script_folder(self) -> Path:
        raw_folder = (self.app_settings.default_script_folder or "scripts").strip()
        folder = Path(raw_folder)
        if not folder.is_absolute():
            folder = app_base_dir() / folder
        return folder

    def load_sample_actions(self) -> None:
        self.sequential_model.reset_actions(self._sample_sequential_actions())
        self.background_model.reset_actions(self._sample_background_actions())
        self.sequential_pane.repeat_input.setText("1")
        self.sequential_pane.random_repeat_input.setText("0")
        self.current_script_metadata = self._new_script_metadata()
        self._mark_dirty()
        self.update_action_button_states()

    def toggle_run(self) -> None:
        if self.run_controls_active or self.runner.is_running:
            self.runner.stop()
            return
        self.start_run()

    def toggle_pause(self) -> None:
        if not self.runner.is_running:
            return
        if self.runner.is_paused:
            self.runner.resume()
            self.run_last_tick_at = time.monotonic()
            self._replace_icon_registration(self.pause_button, "pause", 22)
            self.pause_button.setIcon(self._make_icon("pause"))
        else:
            self._update_run_time()
            self.runner.pause()
            self.run_last_tick_at = time.monotonic()
            self._replace_icon_registration(self.pause_button, "start", 22)
            self.pause_button.setIcon(self._make_icon("start"))
        self._refresh_run_button_labels()

    def start_run(self) -> None:
        actions = self.sequential_model.actions + self.background_model.actions
        if not actions:
            QMessageBox.information(self, "No Actions", "Add at least one action before starting.")
            return
        try:
            base_cycles = max(1, int(self.sequential_pane.repeat_input.text() or "1"))
            random_cycles = max(0, int(self.sequential_pane.random_repeat_input.text() or "0"))
        except ValueError:
            QMessageBox.warning(self, "Invalid Repeat Count", "Sequential repeat counts must be whole numbers.")
            return
        sequential_cycles = base_cycles + (random.randint(1, random_cycles) if random_cycles else 0)
        try:
            self.runner.start(actions, sequential_cycles=sequential_cycles)
        except RuntimePlanError as exc:
            QMessageBox.warning(self, "Script Cannot Run", str(exc))
            return
        except Exception as exc:
            QMessageBox.warning(self, "Script Cannot Run", f"Could not prepare this script:\n{exc}")
            return
        self.run_progress_current = 0
        self.run_progress_total = 0
        self.run_progress_completed = False
        self._update_progress_label()
        self.run_started_at = time.time()
        self.run_last_tick_at = time.monotonic()
        self.run_elapsed_active_seconds = 0.0
        if hasattr(self, "run_time_value"):
            self.run_time_value.setText("00:00:00")
        self.run_timer.start(250)
        self.run_controls_active = True
        self._replace_icon_registration(self.start_button, "stop", 22)
        self.start_button.setIcon(self._make_icon("stop"))
        self.pause_button.setEnabled(True)
        self._refresh_run_button_labels()
        self._set_status("Running")

    def _set_status(self, text: str) -> None:
        if text.startswith(ActionRunner.PROGRESS_PREFIX):
            self._handle_progress_status(text.removeprefix(ActionRunner.PROGRESS_PREFIX))
            return
        if hasattr(self, "status_text"):
            self.status_text.setText(text)
        if text in {"Stopped", "Completed"} or text.startswith("Error:"):
            if text == "Completed":
                self.run_progress_completed = True
                self.run_progress_current = self.run_progress_total
                self._update_progress_label()
            self.run_timer.stop()
            self._update_run_time()
            self.run_last_tick_at = None
            self.run_controls_active = False
            self._replace_icon_registration(self.start_button, "start", 22)
            self.start_button.setIcon(self._make_icon("start"))
            self.pause_button.setEnabled(False)
            self._replace_icon_registration(self.pause_button, "pause", 22)
            self.pause_button.setIcon(self._make_icon("pause"))
            self._refresh_run_button_labels()
        elif text == "Paused":
            self._refresh_run_button_labels()
        elif text == "Running" and self.runner.is_running:
            self.run_controls_active = True
            self.pause_button.setEnabled(True)
            self._refresh_run_button_labels()

    def _handle_progress_status(self, value: str) -> None:
        try:
            current_text, total_text = value.split("/", 1)
            self.run_progress_current = max(0, int(current_text))
            self.run_progress_total = max(0, int(total_text))
            self.run_progress_completed = self.run_progress_total > 0 and self.run_progress_current >= self.run_progress_total
        except ValueError:
            return
        self._update_progress_label()

    def _update_progress_label(self) -> None:
        if not hasattr(self, "progress_value"):
            return
        if self.run_progress_total:
            percent = int((min(self.run_progress_current, self.run_progress_total) / self.run_progress_total) * 100)
        else:
            percent = 100 if self.run_progress_completed else 0
        current = self._format_progress_duration_ms(self.run_progress_current)
        total = self._format_progress_duration_ms(self.run_progress_total)
        self.progress_value.setText(f"{current} / {total} ({percent}%)")
        if hasattr(self, "progress_bar"):
            if self.run_progress_total:
                self.progress_bar.setRange(0, self.run_progress_total)
                self.progress_bar.setValue(min(self.run_progress_current, self.run_progress_total))
            else:
                self.progress_bar.setRange(0, 1)
                self.progress_bar.setValue(1 if self.run_progress_completed else 0)

    @staticmethod
    def _format_progress_duration_ms(milliseconds: int) -> str:
        total_seconds = max(0, int(milliseconds) // 1000)
        if total_seconds == 0:
            return "0s"
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours:
            return f"{hours:d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"

    def _update_run_time(self) -> None:
        if not self.run_started_at or not hasattr(self, "run_time_value"):
            return
        now = time.monotonic()
        if self.run_last_tick_at is None:
            self.run_last_tick_at = now
        if self.runner.is_paused:
            self.run_last_tick_at = now
        else:
            self.run_elapsed_active_seconds += max(0.0, now - self.run_last_tick_at)
            self.run_last_tick_at = now
        elapsed = int(self.run_elapsed_active_seconds)
        hours, remainder = divmod(elapsed, 3600)
        minutes, seconds = divmod(remainder, 60)
        self.run_time_value.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")

    def open_settings(self) -> None:
        dialog = SettingsDialog(self.app_settings, self)
        if dialog.exec() != QDialog.Accepted:
            return
        existing_geometry = self.app_settings.window_geometry
        self.app_settings = dialog.result
        self.app_settings.normalize()
        if self.app_settings.remember_window_geometry:
            self.app_settings.window_geometry = existing_geometry or self._current_geometry_payload()
        else:
            self.app_settings.window_geometry = ""
        try:
            self.app_settings.save(self.settings_path)
        except OSError as exc:
            QMessageBox.warning(self, "Settings Not Saved", f"Could not save settings:\n{exc}")
            return
        self.runner.settings = self.app_settings
        input_controller.configure_input_timing(
            mouse_animation_speed=self.app_settings.mouse_animation_speed,
            enhanced_humanlike_mouse=self.app_settings.enhanced_humanlike_mouse,
            mouse_click_delay_min_ms=self.app_settings.mouse_click_delay_min_ms,
            mouse_click_delay_max_ms=self.app_settings.mouse_click_delay_max_ms,
            key_press_delay_min_ms=self.app_settings.key_press_delay_min_ms,
            key_press_delay_max_ms=self.app_settings.key_press_delay_max_ms,
        )

    def _save_app_settings_silent(self) -> bool:
        try:
            self.app_settings.save(self.settings_path)
        except OSError:
            return False
        return True

    def _restore_window_geometry(self) -> None:
        if not self.app_settings.remember_window_geometry or not self.app_settings.window_geometry:
            return
        try:
            geometry = QByteArray.fromBase64(self.app_settings.window_geometry.encode("ascii"))
        except Exception:
            return
        self.restoreGeometry(geometry)

    def _current_geometry_payload(self) -> str:
        return bytes(self.saveGeometry().toBase64()).decode("ascii")

    def _save_window_geometry_setting(self) -> None:
        if not self.app_settings.remember_window_geometry:
            return
        self.app_settings.window_geometry = self._current_geometry_payload()
        self._save_app_settings_silent()

    def open_tutorial(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Anz Clicker Tutorial")
        layout = QVBoxLayout(dialog)
        title = QLabel("How Anz Clicker Works")
        title.setObjectName("SectionTitle")
        layout.addWidget(title)
        sections = [
            ("Adding Actions", "Use Add Action to add an action to the queue. When added, it will automatically get added to the list of Sequential Actions. It can be moved to the Background Actions tab manually to be ran in the background."),
            ("Sequential Actions", "These run one at a time from top to bottom. Each action uses its corresponding delay, occurs, then moves on to the next in the list. The repeat fields above this pane repeat the entire sequence, including all delays."),
            ("Background Actions", "These start alongside the sequential actions immediately on script start. Each background action follows its own delay and repeat settings while the sequential actions iterate."),
            ("Mouse Areas", "For mouse actions, enable Random Location for Mouse Action, click the area button, then drag the region you want. View Area lets you move and resave that box."),
            ("Custom Actions and Defaults", "Save as Custom Action button saves a configured action for reuse, and adds it to the list of available actions. Edit Default Actions changes what future actions load with. Edit Action Order allows you to change the default order of actions in the list, as well as allows you to hide unused actions from the list."),
            ("Saving Scripts", "Save Script writes both action panes and sequence repeat settings to a JSON file. Load Script loads all saved settings from a file."),
        ]
        for heading, body in sections:
            heading_label = QLabel(heading)
            heading_label.setObjectName("CardTitle")
            body_label = QLabel(body)
            body_label.setWordWrap(True)
            layout.addWidget(heading_label)
            layout.addWidget(body_label)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.resize(620, 520)
        dialog.exec()

    def closeEvent(self, event) -> None:
        if self._confirm_continue_with_unsaved_changes():
            self._save_window_geometry_setting()
            if self.runner.is_running:
                self.runner.stop()
            event.accept()
        else:
            event.ignore()

    def apply_theme(self, dark: bool) -> None:
        self.dark_theme = dark
        self.setStyleSheet(build_stylesheet(dark))
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor("#0b1220" if dark else "#f6f8fc"))
        palette.setColor(QPalette.WindowText, QColor("#edf2ff" if dark else "#18212f"))
        self.setPalette(palette)
        for button, name, size in self.icon_buttons:
            button.setIcon(app_icon(name, size=size, dark=dark))
        self.sequential_pane.set_theme(dark)
        self.background_pane.set_theme(dark)
        self.sequential_pane.apply_icons(dark)
        self.background_pane.apply_icons(dark)
        self.theme_button.setText("Dark Mode" if dark else "Light Mode")
        self.theme_button.setIcon(app_icon("theme", size=22, dark=dark))

    def toggle_theme(self) -> None:
        self.apply_theme(not self.dark_theme)

    def update_action_button_states(self) -> None:
        row = self.current_row()
        has_selection = row >= 0
        for button in getattr(self, "row_selection_buttons", []):
            button.setEnabled(has_selection)
        self.current_pane().update_button_states(row)
        other_pane = self.background_pane if self.current_pane() is self.sequential_pane else self.sequential_pane
        other_index = other_pane.table.currentIndex()
        other_pane.update_button_states(other_index.row() if other_index.isValid() else -1)


def run() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_TITLE)
    window = MainWindow()
    window.show()
    return app.exec()
