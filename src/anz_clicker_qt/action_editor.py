from __future__ import annotations

from pathlib import Path
import re
import time

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from actions import Action, ActionType, PositionMode, ScreenArea
import input_controller
from preset_store import PresetStore
import screen_tools
from .constants import (
    BACKGROUND_GROUP,
    CAPTURE_KEY_ACTIONS,
    LAUNCH_MODES,
    PICTURE_ACTIONS,
    POSITION_ACTIONS,
    PRESET_PREFIX,
    SCRIPT_ACTIONS,
    SIMPLE_ACTION_KEYS,
)
from .icons import app_base_dir
from .paths import captures_dir
from .widgets import (
    GeneralActionSettings,
    KeyCaptureLineEdit,
    PlaceholderDoubleSpinBox,
    PlaceholderSpinBox,
    choose_screen_area,
    make_help_button,
    plain_number_field,
    time_row,
)


class ActionEditorDialog(QDialog):
    def __init__(self, action: Action, action_choices: list[str], preset_store: PresetStore, parent: QWidget | None = None, title: str = "Action Editor") -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setObjectName("ActionEditor")
        self.setAttribute(Qt.WA_DeleteOnClose, False)
        self._init_state(action, preset_store)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        self._build_action_header(form, action, action_choices)
        self._create_reusable_fields(action)
        self._configure_reusable_fields()
        self._load_reusable_field_values(action)

        self.general_settings = GeneralActionSettings(action)
        self.general_settings.add_to_form(form)
        self._bind_general_settings_fields()

        self.dynamic_panel = QFrame()
        self.dynamic_layout = QFormLayout(self.dynamic_panel)
        self.dynamic_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        layout.addLayout(form)
        layout.addWidget(self.dynamic_panel)
        self._add_footer(layout)
        self._refresh_dynamic_panel()
        self.resize(700, 640)

    def _init_state(self, action: Action, preset_store: PresetStore) -> None:
        self.preset_store = preset_store
        self.result: Action | None = None
        self.original_group = action.execution_group
        self.area = action.area.normalized() if action.area and action.area.is_valid() else None
        self.picture_area = action.picture_area.normalized() if action.picture_area and action.picture_area.is_valid() else None
        self.screen_text_area = action.screen_text_area.normalized() if action.screen_text_area and action.screen_text_area.is_valid() else None
        self._dynamic_rows: list[QWidget] = []
        self.shortcut_f6 = None
        self.action_choices: list[str] = []

    def _build_action_header(self, form: QFormLayout, action: Action, action_choices: list[str]) -> None:
        self.action_choices = list(action_choices)
        display_name = f"{PRESET_PREFIX}{action.preset_name}" if action.preset_name else action.action_type
        self.action_search = QLineEdit()
        self.action_search.setPlaceholderText("Search actions...")
        self.action_search.textChanged.connect(self._filter_action_choices)
        form.addRow("Search", self.action_search)

        self.action_type = QComboBox()
        self.action_type.addItems(action_choices)
        if display_name not in action_choices:
            self.action_type.insertItem(0, display_name)
            self.action_choices.insert(0, display_name)
        self.action_type.setCurrentText(display_name)
        self.action_type.currentTextChanged.connect(self._load_template)
        form.addRow("Action Type", self.action_type)

        self.enabled = QCheckBox("Enabled")
        self.enabled.setChecked(action.enabled)
        form.addRow("", self.enabled)
        self.start_as_background = QCheckBox("Start Action as Background Action")
        self.start_as_background.setChecked(action.start_as_background)

    def _filter_action_choices(self, text: str) -> None:
        if not hasattr(self, "action_type"):
            return
        current = self.action_type.currentText()
        query = text.strip().lower()
        choices = [choice for choice in self.action_choices if query in choice.lower()] or list(self.action_choices)
        self.action_type.blockSignals(True)
        self.action_type.clear()
        self.action_type.addItems(choices)
        self.action_type.setCurrentText(current if current in choices else choices[0])
        self.action_type.blockSignals(False)
        if self.action_type.currentText() != current:
            self._load_template(self.action_type.currentText())

    def _create_reusable_fields(self, action: Action) -> None:
        self.key = KeyCaptureLineEdit(action.key)
        self.x = QLineEdit("" if action.x is None else str(action.x))
        self.y = QLineEdit("" if action.y is None else str(action.y))

        self.launch_path = QLineEdit(action.launch_path)
        self.launch_args = QLineEdit(action.launch_args)
        self.launch_verb = QLineEdit(action.launch_verb)
        self.launch_mode = QComboBox()
        self.launch_mode.addItems(LAUNCH_MODES)
        self.launch_mode.setCurrentText(action.launch_mode if action.launch_mode in LAUNCH_MODES else "Show")

        self.movement_minutes = PlaceholderSpinBox()
        self.movement_seconds = PlaceholderSpinBox()
        self.movement_milliseconds = PlaceholderSpinBox()
        self.use_area = QCheckBox("Random Location for Mouse Action")
        self.use_area.setChecked(action.position_mode == PositionMode.AREA.value)
        self.use_area.toggled.connect(self._refresh_dynamic_panel)

        self.screen_min = PlaceholderDoubleSpinBox()
        self.screen_max = PlaceholderDoubleSpinBox()
        self.screen_minutes = PlaceholderSpinBox()
        self.screen_seconds = PlaceholderSpinBox()
        self.screen_milliseconds = PlaceholderSpinBox()
        self.pixel_x = QLineEdit("" if action.pixel_x is None else str(action.pixel_x))
        self.pixel_y = QLineEdit("" if action.pixel_y is None else str(action.pixel_y))
        self.pixel_r = PlaceholderSpinBox()
        self.pixel_g = PlaceholderSpinBox()
        self.pixel_b = PlaceholderSpinBox()
        self.pixel_tolerance = PlaceholderDoubleSpinBox()
        self.pixel_wait_minutes = PlaceholderSpinBox()
        self.pixel_wait_seconds = PlaceholderSpinBox()
        self.pixel_wait_milliseconds = PlaceholderSpinBox()
        self.picture_path = QLineEdit(action.picture_path)
        self.picture_tolerance = PlaceholderDoubleSpinBox()
        self.picture_wait_minutes = PlaceholderSpinBox()
        self.picture_wait_seconds = PlaceholderSpinBox()
        self.picture_wait_milliseconds = PlaceholderSpinBox()
        self.picture_found_animate = QCheckBox("Animate mouse to picture")
        self.picture_found_random_point = QCheckBox("Use random point within picture")
        self.screen_text_pattern = QLineEdit(action.screen_text_pattern)
        self.screen_text_regex = QCheckBox("Use regular expression")
        self.screen_text_regex.setChecked(action.screen_text_is_regex)

    def _configure_reusable_fields(self) -> None:
        self.movement_minutes.setRange(0, 99999)
        self.movement_seconds.setRange(0, 59)
        self.movement_milliseconds.setRange(0, 9999)
        for field in (self.screen_min, self.screen_max, self.pixel_tolerance, self.picture_tolerance):
            field.setRange(0, 100)
            field.setDecimals(2)
        for field in (self.screen_minutes, self.pixel_wait_minutes, self.picture_wait_minutes):
            field.setRange(0, 999)
        for field in (self.screen_seconds, self.pixel_wait_seconds, self.picture_wait_seconds):
            field.setRange(0, 59)
        for field in (self.screen_milliseconds, self.pixel_wait_milliseconds, self.picture_wait_milliseconds):
            field.setRange(0, 9999)
        for field in (self.pixel_r, self.pixel_g, self.pixel_b):
            field.setRange(0, 255)
        for field in (
            self.movement_minutes,
            self.movement_seconds,
            self.movement_milliseconds,
            self.screen_min,
            self.screen_max,
            self.screen_minutes,
            self.screen_seconds,
            self.screen_milliseconds,
            self.pixel_r,
            self.pixel_g,
            self.pixel_b,
            self.pixel_tolerance,
            self.pixel_wait_minutes,
            self.pixel_wait_seconds,
            self.pixel_wait_milliseconds,
            self.picture_tolerance,
            self.picture_wait_minutes,
            self.picture_wait_seconds,
            self.picture_wait_milliseconds,
        ):
            self._plain_number_field(field)

    def _load_reusable_field_values(self, action: Action) -> None:
        self.movement_minutes.setValue(action.movement_duration_minutes)
        self.movement_seconds.setValue(action.movement_duration_seconds)
        self.movement_milliseconds.setValue(action.movement_duration_milliseconds)
        self.screen_min.setValue(action.screen_change_min_percent)
        self.screen_max.setValue(action.screen_change_max_percent)
        self.screen_minutes.setValue(action.screen_change_check_minutes)
        self.screen_seconds.setValue(action.screen_change_check_seconds)
        self.screen_milliseconds.setValue(action.screen_change_check_milliseconds)
        self.pixel_r.setValue(action.pixel_r)
        self.pixel_g.setValue(action.pixel_g)
        self.pixel_b.setValue(action.pixel_b)
        self.pixel_tolerance.setValue(action.pixel_tolerance_percent)
        self.pixel_wait_minutes.setValue(action.pixel_wait_minutes)
        self.pixel_wait_seconds.setValue(action.pixel_wait_seconds)
        self.pixel_wait_milliseconds.setValue(action.pixel_wait_milliseconds)
        self.picture_tolerance.setValue(action.picture_tolerance_percent)
        self.picture_wait_minutes.setValue(action.picture_wait_minutes)
        self.picture_wait_seconds.setValue(action.picture_wait_seconds)
        self.picture_wait_milliseconds.setValue(action.picture_wait_milliseconds)
        self.picture_found_animate.setChecked(action.picture_found_animate)
        self.picture_found_random_point.setChecked(action.picture_found_random_point)

    def _add_footer(self, layout: QVBoxLayout) -> None:
        bottom_row = QHBoxLayout()
        bottom_row.addWidget(self.start_as_background)
        background_help = make_help_button(
            self,
            "Start Action as Background Action",
            "When checked, this action will execute as a background task rather than a sequential task. "
            "When this happens, it continues executing in the background, and the script continues to move "
            "through the sequential actions. If the action is already saved in Background Actions, this "
            "setting has no effect because the action already runs in the background.",
        )
        bottom_row.addWidget(background_help)
        bottom_row.addStretch(1)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        bottom_row.addWidget(buttons)
        layout.addLayout(bottom_row)

    def _bind_general_settings_fields(self) -> None:
        self.delay_minutes = self.general_settings.delay_minutes
        self.delay_seconds = self.general_settings.delay_seconds
        self.delay_milliseconds = self.general_settings.delay_milliseconds
        self.random_delay_minutes = self.general_settings.random_delay_minutes
        self.random_delay_seconds = self.general_settings.random_delay_seconds
        self.random_delay_milliseconds = self.general_settings.random_delay_milliseconds
        self.repeat = self.general_settings.repeat
        self.random_repeat = self.general_settings.random_repeat
        self.comment = self.general_settings.comment

    def _plain_number_field(self, field: QSpinBox | QDoubleSpinBox) -> None:
        if isinstance(field, QSpinBox):
            plain_number_field(field)
            return
        field.setButtonSymbols(QDoubleSpinBox.NoButtons)
        field.setKeyboardTracking(False)
        field.setMinimumWidth(92)
        field.setMinimumHeight(34)
        if field.minimum() <= 0 <= field.maximum():
            field.lineEdit().setPlaceholderText("0")

    def _time_row(self, minutes: QSpinBox, seconds: QSpinBox, milliseconds: QSpinBox) -> QWidget:
        return time_row(minutes, seconds, milliseconds)

    def _refresh_dynamic_panel(self) -> None:
        self._detach_reusable_dynamic_fields()
        self._dynamic_rows = []
        while self.dynamic_layout.count():
            item = self.dynamic_layout.takeAt(0)
            widget = item.widget()
            if widget:
                if self._is_reusable_dynamic_widget(widget):
                    widget.setParent(None)
                else:
                    widget.hide()
                    widget.setParent(None)
                    widget.deleteLater()
        action_type = self._actual_action_type()
        self.general_settings.set_repeat_visible(action_type != ActionType.STOP_ANZ_CLICKER.value)
        if action_type == ActionType.STOP_ANZ_CLICKER.value or self.original_group == BACKGROUND_GROUP:
            self.start_as_background.setChecked(False)
            self.start_as_background.setEnabled(False)
        else:
            self.start_as_background.setEnabled(True)
        if self.shortcut_f6 is not None:
            self.shortcut_f6.setEnabled(action_type in POSITION_ACTIONS)
        if action_type in POSITION_ACTIONS:
            self._build_mouse_panel(action_type)
        elif action_type in CAPTURE_KEY_ACTIONS:
            self.dynamic_layout.addRow("Captured Key", self.key)
            clear = QPushButton("Clear")
            clear.clicked.connect(self.key.clear)
            self.dynamic_layout.addRow("", clear)
        elif action_type == ActionType.LAUNCH_APP.value:
            self._build_launch_panel(is_script=False)
        elif action_type in SCRIPT_ACTIONS:
            self._build_launch_panel(is_script=True)
        elif action_type == ActionType.WAIT_FOR_SCREEN_CHANGE.value:
            self._build_screen_change_panel()
        elif action_type == ActionType.WAIT_FOR_PIXEL_COLOR.value:
            self._build_pixel_panel()
        elif action_type in PICTURE_ACTIONS:
            self._build_picture_panel(action_type == ActionType.AUTO_PICTURE_CLICKER.value)
        elif action_type == ActionType.WAIT_FOR_SCREEN_TEXT.value:
            self._build_screen_text_panel()
        elif action_type == ActionType.STOP_ANZ_CLICKER.value:
            self.dynamic_layout.addRow(QLabel("Stops all currently running Anz Clicker execution after the configured delay."))
        else:
            self.dynamic_layout.addRow(QLabel("This action uses the general timing settings above."))

    def _detach_reusable_dynamic_fields(self) -> None:
        for widget in (
            self.key,
            self.x,
            self.y,
            self.movement_minutes,
            self.movement_seconds,
            self.movement_milliseconds,
            self.use_area,
            self.launch_path,
            self.launch_args,
            self.launch_verb,
            self.launch_mode,
            self.screen_min,
            self.screen_max,
            self.screen_minutes,
            self.screen_seconds,
            self.screen_milliseconds,
            self.pixel_x,
            self.pixel_y,
            self.pixel_r,
            self.pixel_g,
            self.pixel_b,
            self.pixel_tolerance,
            self.pixel_wait_minutes,
            self.pixel_wait_seconds,
            self.pixel_wait_milliseconds,
            self.picture_path,
            self.picture_tolerance,
            self.picture_wait_minutes,
            self.picture_wait_seconds,
            self.picture_wait_milliseconds,
            self.picture_found_animate,
            self.picture_found_random_point,
            self.screen_text_pattern,
            self.screen_text_regex,
        ):
            widget.setParent(None)

    def _is_reusable_dynamic_widget(self, widget: QWidget) -> bool:
        return widget in {
            self.key,
            self.x,
            self.y,
            self.movement_minutes,
            self.movement_seconds,
            self.movement_milliseconds,
            self.use_area,
            self.launch_path,
            self.launch_args,
            self.launch_verb,
            self.launch_mode,
            self.screen_min,
            self.screen_max,
            self.screen_minutes,
            self.screen_seconds,
            self.screen_milliseconds,
            self.pixel_x,
            self.pixel_y,
            self.pixel_r,
            self.pixel_g,
            self.pixel_b,
            self.pixel_tolerance,
            self.pixel_wait_minutes,
            self.pixel_wait_seconds,
            self.pixel_wait_milliseconds,
            self.picture_path,
            self.picture_tolerance,
            self.picture_wait_minutes,
            self.picture_wait_seconds,
            self.picture_wait_milliseconds,
            self.picture_found_animate,
            self.picture_found_random_point,
            self.screen_text_pattern,
            self.screen_text_regex,
        }

    def _build_mouse_panel(self, action_type: str) -> None:
        self.dynamic_layout.addRow(QLabel("Leave X/Y blank to use the cursor position at execution time. 0/0 stays literal. Press F6 to capture coordinates."))
        if self.shortcut_f6 is None:
            self.shortcut_f6 = QShortcut(QKeySequence("F6"), self)
            self.shortcut_f6.activated.connect(self._capture_cursor_coordinates)
        self.shortcut_f6.setEnabled(True)
        xy_row = QWidget()
        self._dynamic_rows.append(xy_row)
        layout = QHBoxLayout(xy_row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel("X"))
        layout.addWidget(self.x)
        layout.addWidget(QLabel("Y"))
        layout.addWidget(self.y)
        layout.addStretch(1)
        self.dynamic_layout.addRow("Coordinates", xy_row)
        area_row = QWidget()
        self._dynamic_rows.append(area_row)
        area_layout = QHBoxLayout(area_row)
        area_layout.setContentsMargins(0, 0, 0, 0)
        pick = QPushButton("...")
        pick.clicked.connect(lambda: self._pick_area("area", auto_close=True))
        view = QPushButton("View Area")
        view.clicked.connect(lambda: self._pick_area("area", auto_close=False))
        area_layout.addWidget(self.use_area)
        area_layout.addWidget(pick)
        area_layout.addWidget(view)
        area_layout.addStretch(1)
        self.dynamic_layout.addRow("Area", area_row)
        self.dynamic_layout.addRow("", QLabel(self._area_summary(self.area)))

    def _capture_cursor_coordinates(self) -> None:
        if self._actual_action_type() not in POSITION_ACTIONS:
            return
        x, y = input_controller.current_position()
        self.use_area.setChecked(False)
        self.x.setText(str(x))
        self.y.setText(str(y))

    def _build_launch_panel(self, *, is_script: bool = False) -> None:
        browse = QPushButton("Browse")
        browse.clicked.connect(lambda: self._browse_launch_path(is_script=is_script))
        row = QWidget()
        self._dynamic_rows.append(row)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.launch_path)
        layout.addWidget(browse)
        self.dynamic_layout.addRow("Script File" if is_script else "File Path or Command", row)
        if not is_script:
            self.dynamic_layout.addRow("Verb", self.launch_verb)
            self.dynamic_layout.addRow("Arguments", self.launch_args)
            self.dynamic_layout.addRow("Mode", self.launch_mode)

    def _build_screen_change_panel(self) -> None:
        self.dynamic_layout.addRow("Capture Area", self._area_buttons("area"))
        self.dynamic_layout.addRow("", QLabel(self._area_summary(self.area)))
        self.dynamic_layout.addRow("Minimum Change %", self.screen_min)
        self.dynamic_layout.addRow("Maximum Change %", self.screen_max)
        self.dynamic_layout.addRow("Check Every", self._time_row(self.screen_minutes, self.screen_seconds, self.screen_milliseconds))

    def _build_pixel_panel(self) -> None:
        xy_row = QWidget()
        self._dynamic_rows.append(xy_row)
        layout = QHBoxLayout(xy_row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel("X"))
        layout.addWidget(self.pixel_x)
        layout.addWidget(QLabel("Y"))
        layout.addWidget(self.pixel_y)
        capture = QPushButton("Capture Current Pixel")
        capture.clicked.connect(self._capture_current_pixel)
        layout.addWidget(capture)
        self.dynamic_layout.addRow("Pixel", xy_row)
        color_row = QWidget()
        self._dynamic_rows.append(color_row)
        color_layout = QHBoxLayout(color_row)
        color_layout.setContentsMargins(0, 0, 0, 0)
        for label, field in (("R", self.pixel_r), ("G", self.pixel_g), ("B", self.pixel_b)):
            color_layout.addWidget(QLabel(label))
            color_layout.addWidget(field)
        self.dynamic_layout.addRow("Target Color", color_row)
        self.dynamic_layout.addRow("Deviation %", self.pixel_tolerance)
        self.dynamic_layout.addRow("Max Wait (0 = infinite)", self._time_row(self.pixel_wait_minutes, self.pixel_wait_seconds, self.pixel_wait_milliseconds))

    def _build_picture_panel(self, is_auto_clicker: bool) -> None:
        self.dynamic_layout.addRow("Search Area", self._area_buttons("picture_area"))
        self.dynamic_layout.addRow("", QLabel(self._area_summary(self.picture_area)))
        file_row = QWidget()
        self._dynamic_rows.append(file_row)
        layout = QHBoxLayout(file_row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.picture_path)
        select = QPushButton("Select File")
        select.clicked.connect(self._select_picture_file)
        capture = QPushButton("Capture Picture")
        capture.clicked.connect(self._capture_picture)
        preview = QPushButton("Preview")
        preview.clicked.connect(self._preview_picture)
        layout.addWidget(select)
        layout.addWidget(capture)
        layout.addWidget(preview)
        self.dynamic_layout.addRow("Picture", file_row)
        self.dynamic_layout.addRow("Deviation %", self._picture_deviation_row())
        self.dynamic_layout.addRow("Max Wait (0 = infinite)", self._time_row(self.picture_wait_minutes, self.picture_wait_seconds, self.picture_wait_milliseconds))
        if is_auto_clicker:
            self.dynamic_layout.addRow("", self.picture_found_animate)
            self.dynamic_layout.addRow("", self.picture_found_random_point)

    def _build_screen_text_panel(self) -> None:
        self.dynamic_layout.addRow("Screen Area", self._area_buttons("screen_text_area"))
        self.dynamic_layout.addRow("", QLabel(self._area_summary(self.screen_text_area)))
        self.dynamic_layout.addRow("Text / Regex to Match", self.screen_text_pattern)
        self.dynamic_layout.addRow("", self.screen_text_regex)
        show_text = QPushButton("Show Text in Area")
        show_text.clicked.connect(self._show_text_in_area)
        self.dynamic_layout.addRow("", show_text)

    def _show_text_in_area(self) -> None:
        if not self.screen_text_area or not self.screen_text_area.is_valid():
            QMessageBox.information(self, "No Area Selected", "Select a screen area first.")
            return
        try:
            screen_tools.configure_ocr(app_base_dir())
            text = screen_tools.read_text_in_area(self.screen_text_area)
        except Exception as exc:
            QMessageBox.warning(self, "OCR Failed", f"Could not read text from this area:\n{exc}")
            return
        QMessageBox.information(self, "Text in Selected Area", text or "No text detected.")

    def _picture_deviation_row(self) -> QWidget:
        row = QWidget()
        self._dynamic_rows.append(row)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(self.picture_tolerance)
        help_button = make_help_button(
            self,
            "Picture Deviation",
            "A percentage of how loose the script is when looking for the picture. "
            'A 10% deviation allows a 90% match to return as "found". '
            "A 100% deviation should in they always return as found, regardless if the picture is there or not.",
        )
        layout.addWidget(help_button)
        layout.addStretch(1)
        return row

    def _area_buttons(self, attr: str) -> QWidget:
        row = QWidget()
        self._dynamic_rows.append(row)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        pick = QPushButton("Select Area")
        pick.clicked.connect(lambda: self._pick_area(attr, auto_close=True))
        view = QPushButton("View Area")
        view.clicked.connect(lambda: self._pick_area(attr, auto_close=False))
        layout.addWidget(pick)
        layout.addWidget(view)
        layout.addStretch(1)
        return row

    def _pick_area(self, attr: str, auto_close: bool) -> None:
        if attr == "area" and not self.use_area.isChecked():
            self.use_area.blockSignals(True)
            self.use_area.setChecked(True)
            self.use_area.blockSignals(False)
        selected_area = choose_screen_area(self, getattr(self, attr), auto_close)
        if selected_area:
            setattr(self, attr, selected_area)
        self._refresh_dynamic_panel()

    def _browse_launch_path(self, *, is_script: bool = False) -> None:
        if is_script:
            path, _ = QFileDialog.getOpenFileName(self, "Choose Anz Clicker Script", "", "Anz Clicker Scripts (*.json);;All Files (*.*)")
        else:
            path, _ = QFileDialog.getOpenFileName(self, "Choose File or Application")
        if path:
            self.launch_path.setText(path)

    def _select_picture_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Choose Picture", "", "Image Files (*.png *.jpg *.jpeg *.bmp *.gif);;All Files (*.*)")
        if path:
            self.picture_path.setText(path)

    def _capture_picture(self) -> None:
        selected_area = choose_screen_area(self, None, True)
        if not selected_area:
            return
        image = screen_tools.capture_area(selected_area)
        capture_folder = captures_dir()
        capture_folder.mkdir(parents=True, exist_ok=True)
        path = capture_folder / f"capture_{int(time.time() * 1000)}.png"
        screen_tools.save_image(image, path)
        self.picture_path.setText(str(path))

    def _preview_picture(self) -> None:
        path = self.picture_path.text().strip()
        if not path:
            QMessageBox.information(self, "No Picture", "Choose or capture a picture first.")
            return
        if not Path(path).exists():
            QMessageBox.warning(self, "Missing Picture", "The selected picture file does not exist.")
            return
        preview = QDialog(self)
        preview.setWindowTitle("Picture Preview")
        layout = QVBoxLayout(preview)
        label = QLabel()
        pixmap = QPixmap(path)
        label.setPixmap(pixmap.scaled(520, 360, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        layout.addWidget(label)
        layout.addWidget(QLabel(path))
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(preview.reject)
        layout.addWidget(buttons)
        preview.exec()

    def _capture_current_pixel(self) -> None:
        x, y = input_controller.current_position()
        r, g, b = screen_tools.capture_screen_pixel(x, y)
        self.pixel_x.setText(str(x))
        self.pixel_y.setText(str(y))
        self.pixel_r.setValue(r)
        self.pixel_g.setValue(g)
        self.pixel_b.setValue(b)

    @staticmethod
    def _area_summary(area: ScreenArea | None) -> str:
        return f"Area: {area.summary()}" if area and area.is_valid() else "No area selected"

    def _actual_action_type(self) -> str:
        display = self.action_type.currentText()
        if display.startswith(PRESET_PREFIX):
            preset = self.preset_store.custom_action(display.removeprefix(PRESET_PREFIX))
            return preset.action_type if preset else ActionType.LEFT_CLICK.value
        return display

    def _load_template(self, display: str) -> None:
        template = self.preset_store.custom_action(display.removeprefix(PRESET_PREFIX)) if display.startswith(PRESET_PREFIX) else self.preset_store.default_for(display)
        if not template:
            self._refresh_dynamic_panel()
            return
        self.enabled.setChecked(template.enabled)
        self.key.setText(template.key)
        self.x.setText("" if template.x is None else str(template.x))
        self.y.setText("" if template.y is None else str(template.y))
        self.general_settings.load_from_action(template)
        self.launch_path.setText(template.launch_path)
        self.launch_args.setText(template.launch_args)
        self.launch_verb.setText(template.launch_verb)
        self.launch_mode.setCurrentText(template.launch_mode if template.launch_mode in LAUNCH_MODES else "Show")
        self.movement_minutes.setValue(template.movement_duration_minutes)
        self.movement_seconds.setValue(template.movement_duration_seconds)
        self.movement_milliseconds.setValue(template.movement_duration_milliseconds)
        self.area = template.area.normalized() if template.area and template.area.is_valid() else None
        self.picture_area = template.picture_area.normalized() if template.picture_area and template.picture_area.is_valid() else None
        self.screen_text_area = template.screen_text_area.normalized() if template.screen_text_area and template.screen_text_area.is_valid() else None
        self.use_area.setChecked(template.position_mode == PositionMode.AREA.value)
        self.screen_min.setValue(template.screen_change_min_percent)
        self.screen_max.setValue(template.screen_change_max_percent)
        self.screen_minutes.setValue(template.screen_change_check_minutes)
        self.screen_seconds.setValue(template.screen_change_check_seconds)
        self.screen_milliseconds.setValue(template.screen_change_check_milliseconds)
        self.pixel_x.setText("" if template.pixel_x is None else str(template.pixel_x))
        self.pixel_y.setText("" if template.pixel_y is None else str(template.pixel_y))
        self.pixel_r.setValue(template.pixel_r)
        self.pixel_g.setValue(template.pixel_g)
        self.pixel_b.setValue(template.pixel_b)
        self.pixel_tolerance.setValue(template.pixel_tolerance_percent)
        self.pixel_wait_minutes.setValue(template.pixel_wait_minutes)
        self.pixel_wait_seconds.setValue(template.pixel_wait_seconds)
        self.pixel_wait_milliseconds.setValue(template.pixel_wait_milliseconds)
        self.picture_path.setText(template.picture_path)
        self.picture_tolerance.setValue(template.picture_tolerance_percent)
        self.picture_wait_minutes.setValue(template.picture_wait_minutes)
        self.picture_wait_seconds.setValue(template.picture_wait_seconds)
        self.picture_wait_milliseconds.setValue(template.picture_wait_milliseconds)
        self.picture_found_animate.setChecked(template.picture_found_animate)
        self.picture_found_random_point.setChecked(template.picture_found_random_point)
        self.screen_text_pattern.setText(template.screen_text_pattern)
        self.screen_text_regex.setChecked(template.screen_text_is_regex)
        self._refresh_dynamic_panel()

    def _optional_int(self, value: str) -> int | None:
        value = value.strip()
        if not value:
            return None
        return int(value)

    def _save(self) -> None:
        try:
            x = self._optional_int(self.x.text())
            y = self._optional_int(self.y.text())
            pixel_x = self._optional_int(self.pixel_x.text())
            pixel_y = self._optional_int(self.pixel_y.text())
        except ValueError:
            QMessageBox.warning(self, "Invalid Coordinates", "Coordinate fields must be whole numbers, or left blank where supported.")
            return

        action = self._action_from_fields(pixel_x, pixel_y)
        self.general_settings.apply_to_action(action)
        if action.action_type == ActionType.STOP_ANZ_CLICKER.value:
            action.repeat = 1
            action.random_repeat = 0
        self._apply_location_fields(action, x, y)
        self._apply_simple_key_override(action)

        validation_error = self._validation_error(action)
        if validation_error:
            QMessageBox.warning(self, "Invalid Action", validation_error)
            return
        self._accept_action(action)

    def _action_from_fields(self, pixel_x: int | None, pixel_y: int | None) -> Action:
        display = self.action_type.currentText()
        return Action(
            action_type=self._actual_action_type(),
            enabled=self.enabled.isChecked(),
            preset_name=display.removeprefix(PRESET_PREFIX) if display.startswith(PRESET_PREFIX) else "",
            execution_group=self.original_group,
            start_as_background=self.start_as_background.isChecked() if self.original_group != BACKGROUND_GROUP else False,
            key=self.key.text().strip(),
            launch_path=self.launch_path.text().strip(),
            launch_args=self.launch_args.text().strip(),
            launch_verb=self.launch_verb.text().strip(),
            launch_mode=self.launch_mode.currentText(),
            movement_duration_minutes=self.movement_minutes.value(),
            movement_duration_seconds=self.movement_seconds.value(),
            movement_duration_milliseconds=self.movement_milliseconds.value(),
            screen_change_min_percent=self.screen_min.value(),
            screen_change_max_percent=self.screen_max.value(),
            screen_change_check_minutes=self.screen_minutes.value(),
            screen_change_check_seconds=self.screen_seconds.value(),
            screen_change_check_milliseconds=self.screen_milliseconds.value(),
            pixel_x=pixel_x,
            pixel_y=pixel_y,
            pixel_r=self.pixel_r.value(),
            pixel_g=self.pixel_g.value(),
            pixel_b=self.pixel_b.value(),
            pixel_tolerance_percent=self.pixel_tolerance.value(),
            pixel_wait_minutes=self.pixel_wait_minutes.value(),
            pixel_wait_seconds=self.pixel_wait_seconds.value(),
            pixel_wait_milliseconds=self.pixel_wait_milliseconds.value(),
            picture_path=self.picture_path.text().strip(),
            picture_tolerance_percent=self.picture_tolerance.value(),
            picture_wait_minutes=self.picture_wait_minutes.value(),
            picture_wait_seconds=self.picture_wait_seconds.value(),
            picture_wait_milliseconds=self.picture_wait_milliseconds.value(),
            picture_found_animate=self.picture_found_animate.isChecked(),
            picture_found_random_point=self.picture_found_random_point.isChecked(),
            screen_text_pattern=self.screen_text_pattern.text().strip(),
            screen_text_is_regex=self.screen_text_regex.isChecked(),
        )

    def _apply_location_fields(self, action: Action, x: int | None, y: int | None) -> None:
        if action.action_type in POSITION_ACTIONS:
            action.position_mode = PositionMode.AREA.value if self.use_area.isChecked() else (PositionMode.COORDINATES.value if x is not None and y is not None else PositionMode.CURRENT.value)
            action.x = x
            action.y = y
            action.random_x = 0
            action.random_y = 0
            action.area = self.area.normalized() if self.area else None
        elif action.action_type == ActionType.WAIT_FOR_SCREEN_CHANGE.value:
            action.area = self.area.normalized() if self.area else None
        elif action.action_type in PICTURE_ACTIONS:
            action.picture_area = self.picture_area.normalized() if self.picture_area else None
        elif action.action_type == ActionType.WAIT_FOR_SCREEN_TEXT.value:
            action.screen_text_area = self.screen_text_area.normalized() if self.screen_text_area else None

    @staticmethod
    def _apply_simple_key_override(action: Action) -> None:
        if action.action_type in SIMPLE_ACTION_KEYS:
            action.key = SIMPLE_ACTION_KEYS[action.action_type]

    def _accept_action(self, action: Action) -> None:
        self.result = action
        self.setWindowModality(Qt.NonModal)
        self.releaseKeyboard()
        self.releaseMouse()
        self.accept()

    @staticmethod
    def _validation_error(action: Action) -> str:
        if action.action_type in POSITION_ACTIONS and action.position_mode == PositionMode.AREA.value and (not action.area or not action.area.is_valid()):
            return "Select a valid area for area-based mouse actions."
        if action.action_type in CAPTURE_KEY_ACTIONS and not action.key:
            return "Choose a key or key combination."
        if action.action_type == ActionType.LAUNCH_APP.value and not action.launch_path:
            return "Launch App actions require a file path or command."
        if action.action_type in SCRIPT_ACTIONS:
            if not action.launch_path:
                return "Anz Clicker script actions require a script file."
            if not Path(action.launch_path).exists():
                return "The selected Anz Clicker script file does not exist."
        if action.action_type == ActionType.WAIT_FOR_SCREEN_CHANGE.value and (not action.area or not action.area.is_valid()):
            return "Wait for Screen Change requires a capture area."
        if action.action_type == ActionType.WAIT_FOR_PIXEL_COLOR.value and (action.pixel_x is None or action.pixel_y is None):
            return "Wait for Pixel Color requires X and Y coordinates."
        if action.action_type in PICTURE_ACTIONS:
            if not action.picture_area or not action.picture_area.is_valid():
                return "Picture actions require a valid search area."
            if not action.picture_path:
                return "Picture actions require a picture file."
            if not Path(action.picture_path).exists():
                return "The selected picture file does not exist."
        if action.action_type == ActionType.WAIT_FOR_SCREEN_TEXT.value:
            if not action.screen_text_area or not action.screen_text_area.is_valid():
                return "Wait for Screen Text requires a valid screen area."
            if not action.screen_text_pattern.strip():
                return "Wait for Screen Text requires text or a regular expression to match."
            if action.screen_text_is_regex:
                try:
                    re.compile(action.screen_text_pattern)
                except re.error as exc:
                    return f"Regular expression is invalid: {exc}"
        return ""

__all__ = ["ActionEditorDialog"]
