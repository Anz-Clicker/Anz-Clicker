from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QCoreApplication, QEvent, QItemSelectionModel, QMimeData, QModelIndex, QPoint, QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QDrag, QHelpEvent, QIcon, QKeyEvent, QMouseEvent, QPainter, QPainterPath, QPen, QRegion
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QDoubleSpinBox,
    QSpinBox,
    QStyle,
    QStyleOptionViewItem,
    QStyledItemDelegate,
    QTabBar,
    QTableView,
    QToolTip,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import QAbstractTableModel

from actions import Action, ActionType, PositionMode, ScreenArea
from .constants import CAPTURE_KEY_ACTIONS, SCRIPT_ACTIONS, SIMPLE_ACTION_KEYS
from .icons import app_icon


PICTURE_ACTIONS = {ActionType.WAIT_FOR_PICTURE.value, ActionType.AUTO_PICTURE_CLICKER.value}
ACTION_DRAG_MIME = "application/x-anz-clicker-action-row"


def encode_action_drag(group_name: str, rows: int | list[int]) -> QMimeData:
    mime = QMimeData()
    row_values = [rows] if isinstance(rows, int) else rows
    row_text = ",".join(str(row) for row in sorted(set(row_values)))
    mime.setData(ACTION_DRAG_MIME, f"{group_name}\n{row_text}".encode("utf-8"))
    return mime


def decode_action_drag(mime: QMimeData) -> tuple[str, list[int]] | None:
    if not mime.hasFormat(ACTION_DRAG_MIME):
        return None
    try:
        group_name, row_text = bytes(mime.data(ACTION_DRAG_MIME)).decode("utf-8").splitlines()
        rows = [int(value) for value in row_text.split(",") if value.strip()]
        return group_name, sorted(set(rows))
    except (TypeError, ValueError):
        return None


class PlaceholderSpinBox(QSpinBox):
    """Render zero as placeholder text while preserving a numeric zero value."""

    def textFromValue(self, value: int) -> str:
        return "" if value == 0 else super().textFromValue(value)

    def valueFromText(self, text: str) -> int:
        return 0 if not text.strip() else super().valueFromText(text)


class PlaceholderDoubleSpinBox(QDoubleSpinBox):
    """Floating-point counterpart to PlaceholderSpinBox."""

    def textFromValue(self, value: float) -> str:
        return "" if value == 0 else super().textFromValue(value)

    def valueFromText(self, text: str) -> float:
        return 0.0 if not text.strip() else super().valueFromText(text)


def make_help_button(parent: QWidget, title: str, message: str) -> QPushButton:
    button = QPushButton("?")
    button.setObjectName("HelpButton")
    button.setToolTip("What does this do?")
    button.setFixedSize(30, 30)
    button.clicked.connect(lambda: QMessageBox.information(parent, title, message))
    return button


def make_help_label(parent: QWidget, text: str, message: str) -> QWidget:
    row = QWidget()
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(6)
    layout.addWidget(QLabel(text))
    layout.addWidget(make_help_button(parent, text, message))
    layout.addStretch(1)
    return row


def plain_number_field(field: QSpinBox) -> None:
    field.setButtonSymbols(QSpinBox.NoButtons)
    field.setKeyboardTracking(False)
    field.setMinimumWidth(92)
    field.setMinimumHeight(34)
    if field.minimum() <= 0 <= field.maximum():
        field.lineEdit().setPlaceholderText("0")


def time_row(minutes: QSpinBox, seconds: QSpinBox, milliseconds: QSpinBox) -> QWidget:
    row = QWidget()
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 2, 0, 2)
    layout.setSpacing(8)
    for field, label in ((minutes, "min"), (seconds, "sec"), (milliseconds, "ms")):
        field.setMinimumWidth(92)
        layout.addWidget(field)
        layout.addWidget(QLabel(label))
    layout.addStretch(1)
    return row


class GeneralActionSettings:
    """Shared editor fields that every action supports."""

    def __init__(self, action: Action) -> None:
        self.delay_minutes = PlaceholderSpinBox()
        self.delay_seconds = PlaceholderSpinBox()
        self.delay_milliseconds = PlaceholderSpinBox()
        self.random_delay_minutes = PlaceholderSpinBox()
        self.random_delay_seconds = PlaceholderSpinBox()
        self.random_delay_milliseconds = PlaceholderSpinBox()
        self.repeat = QSpinBox()
        self.random_repeat = PlaceholderSpinBox()
        self.comment = QLineEdit()
        self.repeat_label = QLabel("Repeat Count")
        self.repeat_row_widget = self._repeat_row()

        for field in (self.delay_minutes, self.random_delay_minutes):
            field.setRange(0, 999)
        for field in (self.delay_seconds, self.random_delay_seconds):
            field.setRange(0, 59)
        for field in (self.delay_milliseconds, self.random_delay_milliseconds):
            field.setRange(0, 999)
        self.repeat.setRange(1, 999999)
        self.random_repeat.setRange(0, 999999)
        for field in self.number_fields():
            plain_number_field(field)
        self.load_from_action(action)

    def number_fields(self) -> tuple[QSpinBox, ...]:
        return (
            self.delay_minutes,
            self.delay_seconds,
            self.delay_milliseconds,
            self.random_delay_minutes,
            self.random_delay_seconds,
            self.random_delay_milliseconds,
            self.repeat,
            self.random_repeat,
        )

    def add_to_form(self, form: QFormLayout) -> None:
        form.addRow("Delay", time_row(self.delay_minutes, self.delay_seconds, self.delay_milliseconds))
        form.addRow("+ Random Delay", time_row(self.random_delay_minutes, self.random_delay_seconds, self.random_delay_milliseconds))
        form.addRow(self.repeat_label, self.repeat_row_widget)
        form.addRow("Comment", self.comment)

    def set_repeat_visible(self, visible: bool) -> None:
        self.repeat_label.setVisible(visible)
        self.repeat_row_widget.setVisible(visible)
        if not visible:
            self.repeat.setValue(1)
            self.random_repeat.setValue(0)

    def load_from_action(self, action: Action) -> None:
        self.delay_minutes.setValue(action.delay_minutes)
        self.delay_seconds.setValue(action.delay_seconds)
        self.delay_milliseconds.setValue(action.delay_milliseconds)
        self.random_delay_minutes.setValue(action.random_delay_minutes)
        self.random_delay_seconds.setValue(action.random_delay_seconds)
        self.random_delay_milliseconds.setValue(action.random_delay_milliseconds)
        self.repeat.setValue(max(1, action.repeat))
        self.random_repeat.setValue(action.random_repeat)
        self.comment.setText(action.comment)

    def apply_to_action(self, action: Action) -> None:
        action.delay_minutes = self.delay_minutes.value()
        action.delay_seconds = self.delay_seconds.value()
        action.delay_milliseconds = self.delay_milliseconds.value()
        action.random_delay_minutes = self.random_delay_minutes.value()
        action.random_delay_seconds = self.random_delay_seconds.value()
        action.random_delay_milliseconds = self.random_delay_milliseconds.value()
        action.repeat = self.repeat.value()
        action.random_repeat = self.random_repeat.value()
        action.comment = self.comment.text().strip()

    def _repeat_row(self) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(8)
        layout.addWidget(self.repeat)
        layout.addWidget(QLabel("+ random"))
        layout.addWidget(self.random_repeat)
        layout.addStretch(1)
        return row


def delay_label(action: Action) -> str:
    base = compact_time_label(action.delay_minutes, action.delay_seconds, action.delay_milliseconds)
    if action.random_delay_minutes or action.random_delay_seconds or action.random_delay_milliseconds:
        random_part = compact_time_label(action.random_delay_minutes, action.random_delay_seconds, action.random_delay_milliseconds)
        return f"{base} (+{random_part})"
    return base


def compact_time_label(minutes: int, seconds: int, milliseconds: int) -> str:
    parts: list[str] = []
    if minutes:
        parts.append(f"{minutes}m")
    if seconds:
        parts.append(f"{seconds}s")
    if milliseconds or not parts:
        parts.append(f"{milliseconds}ms")
    return " ".join(parts)


def repeat_label(action: Action) -> str:
    if action.random_repeat:
        return f"{action.repeat} (+{action.random_repeat})"
    return str(action.repeat)


def target_label(action: Action) -> str:
    if action.action_type in CAPTURE_KEY_ACTIONS:
        return action.key or ""
    if action.action_type in SIMPLE_ACTION_KEYS:
        return SIMPLE_ACTION_KEYS[action.action_type]
    if action.position_mode == PositionMode.AREA.value and action.area and action.area.is_valid():
        return "Random Area"
    if action.action_type == ActionType.WAIT_FOR_PIXEL_COLOR.value:
        coords = f"{action.pixel_x}, {action.pixel_y}" if action.pixel_x is not None and action.pixel_y is not None else "Pixel"
        return f"{coords} -> ({action.pixel_r}, {action.pixel_g}, {action.pixel_b})"
    if action.action_type in PICTURE_ACTIONS:
        if isinstance(action.picture_area, ScreenArea) and action.picture_area.is_valid():
            return f"Area {action.picture_area.summary()}"
        return Path(action.picture_path).name if action.picture_path else ""
    if action.action_type == ActionType.WAIT_FOR_SCREEN_TEXT.value:
        if isinstance(action.screen_text_area, ScreenArea) and action.screen_text_area.is_valid():
            return f"Area {action.screen_text_area.summary()}"
        return action.screen_text_pattern
    if action.action_type in SCRIPT_ACTIONS:
        return Path(action.launch_path).name if action.launch_path else ""
    return action.position_summary() or action.key or action.launch_path or ""


def action_row_values(action: Action) -> tuple[bool, str, str, str, str, str]:
    return (
        action.enabled,
        action.preset_name or action.action_type,
        target_label(action),
        delay_label(action),
        repeat_label(action),
        action.comment,
    )


class ActionTableModel(QAbstractTableModel):
    HEADERS = ["#", "Enabled", "Action", "Target", "Delay", "Repeat", "Notes"]

    def __init__(self, actions: list[Action] | None = None) -> None:
        super().__init__()
        self.actions = actions or []
        self.editing_locked = False

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.actions)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.HEADERS)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return self.HEADERS[section]
        return str(section + 1)

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        if not index.isValid():
            return Qt.ItemIsDropEnabled if not self.editing_locked else Qt.NoItemFlags
        flags = Qt.ItemIsSelectable | Qt.ItemIsEnabled
        if not self.editing_locked:
            flags |= Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled
        if index.column() == 1 and not self.editing_locked:
            flags |= Qt.ItemIsUserCheckable
        return flags

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid():
            return None
        enabled, action_name, target, delay, repeat, notes = action_row_values(self.actions[index.row()])
        col = index.column()

        if role == Qt.DisplayRole:
            values = {
                0: str(index.row() + 1),
                2: action_name,
                3: target,
                4: delay,
                5: repeat,
                6: notes,
            }
            return values.get(col, "")

        if role == Qt.CheckStateRole and col == 1:
            return Qt.Checked if enabled else Qt.Unchecked

        if role == Qt.ForegroundRole and not enabled:
            return QColor("#71839f")

        if role == Qt.TextAlignmentRole and col in {0, 1, 4, 5}:
            return int(Qt.AlignCenter)

        return None

    def setData(self, index: QModelIndex, value, role: int = Qt.EditRole) -> bool:
        if not index.isValid() or self.editing_locked:
            return False
        if index.column() == 1 and role == Qt.CheckStateRole:
            self.actions[index.row()].enabled = value == Qt.Checked
            self.dataChanged.emit(self.index(index.row(), 0), self.index(index.row(), self.columnCount() - 1), [Qt.CheckStateRole, Qt.ForegroundRole, Qt.DisplayRole])
            return True
        return False

    def add_action(self, action: Action) -> None:
        insert_at = len(self.actions)
        self.beginInsertRows(QModelIndex(), insert_at, insert_at)
        self.actions.append(action)
        self.endInsertRows()

    def remove_row(self, row_index: int) -> None:
        if row_index < 0 or row_index >= len(self.actions):
            return
        self.beginRemoveRows(QModelIndex(), row_index, row_index)
        self.actions.pop(row_index)
        self.endRemoveRows()

    def remove_rows(self, rows: list[int]) -> int:
        valid_rows = sorted({row for row in rows if 0 <= row < len(self.actions)}, reverse=True)
        if not valid_rows:
            return -1
        nearest = min(valid_rows)
        self.beginResetModel()
        for row in valid_rows:
            self.actions.pop(row)
        self.endResetModel()
        return min(nearest, len(self.actions) - 1)

    def move_row(self, source: int, offset: int) -> int:
        target = source + offset
        if source < 0 or source >= len(self.actions) or target < 0 or target >= len(self.actions):
            return source
        self.beginResetModel()
        self.actions[source], self.actions[target] = self.actions[target], self.actions[source]
        self.endResetModel()
        return target

    def move_rows(self, rows: list[int], offset: int) -> list[int]:
        selected = sorted({row for row in rows if 0 <= row < len(self.actions)})
        if not selected or offset == 0:
            return selected
        selected_set = set(selected)
        self.beginResetModel()
        if offset < 0:
            for row in selected:
                if row > 0 and row - 1 not in selected_set:
                    self.actions[row - 1], self.actions[row] = self.actions[row], self.actions[row - 1]
                    selected_set.remove(row)
                    selected_set.add(row - 1)
        else:
            for row in reversed(selected):
                if row < len(self.actions) - 1 and row + 1 not in selected_set:
                    self.actions[row + 1], self.actions[row] = self.actions[row], self.actions[row + 1]
                    selected_set.remove(row)
                    selected_set.add(row + 1)
        self.endResetModel()
        return sorted(selected_set)

    def move_row_to(self, source: int, insertion_row: int) -> int:
        if source < 0 or source >= len(self.actions):
            return source
        insertion_row = max(0, min(insertion_row, len(self.actions)))
        target = insertion_row - 1 if insertion_row > source else insertion_row
        if target == source:
            return source
        self.beginResetModel()
        action = self.actions.pop(source)
        self.actions.insert(target, action)
        self.endResetModel()
        return target

    def move_rows_to(self, rows: list[int], insertion_row: int) -> list[int]:
        selected = sorted({row for row in rows if 0 <= row < len(self.actions)})
        if not selected:
            return []
        insertion_row = max(0, min(insertion_row, len(self.actions)))
        selected_actions = [self.actions[row] for row in selected]
        selected_set = set(selected)
        remaining = [action for index, action in enumerate(self.actions) if index not in selected_set]
        adjusted_insertion = insertion_row - sum(1 for row in selected if row < insertion_row)
        adjusted_insertion = max(0, min(adjusted_insertion, len(remaining)))
        self.beginResetModel()
        self.actions = remaining[:adjusted_insertion] + selected_actions + remaining[adjusted_insertion:]
        self.endResetModel()
        return list(range(adjusted_insertion, adjusted_insertion + len(selected_actions)))

    def set_editing_locked(self, locked: bool) -> None:
        self.editing_locked = locked

    def duplicate_row(self, row_index: int) -> int:
        if row_index < 0 or row_index >= len(self.actions):
            return row_index
        insert_at = row_index + 1
        self.beginInsertRows(QModelIndex(), insert_at, insert_at)
        self.actions.insert(insert_at, Action.from_dict(self.actions[row_index].to_dict()))
        self.endInsertRows()
        return insert_at

    def duplicate_rows(self, rows: list[int]) -> list[int]:
        selected = sorted({row for row in rows if 0 <= row < len(self.actions)})
        if not selected:
            return []
        duplicates = [Action.from_dict(self.actions[row].to_dict()) for row in selected]
        insert_at = selected[-1] + 1
        self.beginResetModel()
        for offset, action in enumerate(duplicates):
            self.actions.insert(insert_at + offset, action)
        self.endResetModel()
        return list(range(insert_at, insert_at + len(duplicates)))

    def take_row(self, row_index: int) -> Action | None:
        if row_index < 0 or row_index >= len(self.actions):
            return None
        self.beginRemoveRows(QModelIndex(), row_index, row_index)
        row = self.actions.pop(row_index)
        self.endRemoveRows()
        return row

    def take_rows(self, rows: list[int]) -> list[Action]:
        selected = sorted({row for row in rows if 0 <= row < len(self.actions)})
        if not selected:
            return []
        selected_actions = [self.actions[row] for row in selected]
        selected_set = set(selected)
        self.beginResetModel()
        self.actions = [action for index, action in enumerate(self.actions) if index not in selected_set]
        self.endResetModel()
        return selected_actions

    def insert_existing_row(self, row_index: int, row: Action) -> None:
        row_index = max(0, min(row_index, len(self.actions)))
        self.beginInsertRows(QModelIndex(), row_index, row_index)
        self.actions.insert(row_index, row)
        self.endInsertRows()

    def insert_existing_rows(self, row_index: int, rows: list[Action]) -> list[int]:
        if not rows:
            return []
        row_index = max(0, min(row_index, len(self.actions)))
        self.beginResetModel()
        for offset, row in enumerate(rows):
            self.actions.insert(row_index + offset, row)
        self.endResetModel()
        return list(range(row_index, row_index + len(rows)))

    def replace_row(self, row_index: int, action: Action) -> None:
        if row_index < 0 or row_index >= len(self.actions):
            return
        self.actions[row_index] = action
        self.dataChanged.emit(self.index(row_index, 0), self.index(row_index, self.columnCount() - 1), [Qt.DisplayRole, Qt.CheckStateRole, Qt.ForegroundRole])

    def reset_actions(self, actions: list[Action]) -> None:
        self.beginResetModel()
        self.actions = actions
        self.endResetModel()


class RowHoverDelegate(QStyledItemDelegate):
    def _row_option(self, option, index: QModelIndex) -> QStyleOptionViewItem:
        row_option = QStyleOptionViewItem(option)
        table = self.parent()
        if isinstance(table, ActionTableView) and index.row() == table.hovered_row:
            row_option.state |= QStyle.State_MouseOver
        return row_option

    def paint(self, painter: QPainter, option, index: QModelIndex) -> None:
        table = self.parent()
        painter.save()
        if isinstance(table, ActionTableView) and index.row() == table.dragging_row:
            painter.setOpacity(0.32)
        super().paint(painter, self._row_option(option, index), index)
        painter.restore()


class EnabledCheckboxDelegate(RowHoverDelegate):
    def paint(self, painter: QPainter, option, index: QModelIndex) -> None:
        if index.column() != 1:
            super().paint(painter, option, index)
            return
        option = self._row_option(option, index)
        table = self.parent()
        painter.save()
        if isinstance(table, ActionTableView) and index.row() == table.dragging_row:
            painter.setOpacity(0.32)
        style = option.widget.style() if option.widget else QApplication.style()
        style.drawPrimitive(QStyle.PE_PanelItemViewItem, option, painter, option.widget)
        checked = index.data(Qt.CheckStateRole) == Qt.Checked
        painter.setRenderHint(QPainter.Antialiasing)
        dark = option.palette.window().color().lightness() < 128
        rect = option.rect.adjusted(12, 8, -12, -8)
        rect.setWidth(16)
        rect.setHeight(16)
        rect.moveCenter(option.rect.center())
        painter.setPen(QPen(QColor("#3b82f6"), 1.4))
        painter.setBrush(QColor("#2563eb") if checked else QColor("#0f172a" if dark else "#ffffff"))
        painter.drawRoundedRect(rect, 4, 4)
        if checked:
            painter.setPen(QPen(QColor("#ffffff"), 2))
            painter.drawLine(rect.left() + 3, rect.center().y(), rect.left() + 7, rect.bottom() - 4)
            painter.drawLine(rect.left() + 7, rect.bottom() - 4, rect.right() - 3, rect.top() + 4)
        painter.restore()

    def editorEvent(self, event, model, option, index: QModelIndex) -> bool:
        if index.column() != 1 or getattr(model, "editing_locked", False):
            return super().editorEvent(event, model, option, index)
        if event.type() == event.Type.MouseButtonRelease:
            current = index.data(Qt.CheckStateRole)
            model.setData(index, Qt.Unchecked if current == Qt.Checked else Qt.Checked, Qt.CheckStateRole)
            return True
        return super().editorEvent(event, model, option, index)


class ActionDropIndicator(QWidget):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.line_y = -1
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.hide()

    def set_target(self, line_y: int) -> None:
        self.line_y = max(3, min(line_y, self.height() - 4))
        self.show()
        self.raise_()
        self.update()

    def clear_target(self) -> None:
        self.line_y = -1
        self.hide()

    def paintEvent(self, event) -> None:
        if self.line_y < 0:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        accent = self.palette().highlight().color()
        painter.setPen(QPen(accent, 3))
        painter.drawLine(8, self.line_y, self.width() - 8, self.line_y)
        painter.setPen(Qt.NoPen)
        painter.setBrush(accent)
        painter.drawEllipse(QPoint(8, self.line_y), 4, 4)
        painter.drawEllipse(QPoint(self.width() - 8, self.line_y), 4, 4)


class ActionTableView(QTableView):
    contextRequested = Signal(QPoint)
    editRequested = Signal()
    deleteRequested = Signal()
    actionDropped = Signal(str, object, str, int)

    def __init__(self, model: ActionTableModel, group_name: str) -> None:
        super().__init__()
        self.group_name = group_name
        self.editing_locked = False
        self.hovered_row = -1
        self.dragging_row = -1
        self.setObjectName("ActionTableView")
        self.setModel(model)
        self.setSelectionBehavior(QTableView.SelectRows)
        self.setSelectionMode(QTableView.ExtendedSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setShowGrid(True)
        self.setAlternatingRowColors(False)
        self.verticalHeader().hide()
        self.setMinimumHeight(252)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setToolTip("")
        self.viewport().setToolTip("")
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(False)
        self.setDragDropMode(QAbstractItemView.DragDrop)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setWordWrap(False)
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setHighlightSections(False)
        self.horizontalHeader().setSectionsMovable(False)
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)
        self.horizontalHeader().setSectionResizeMode(2, QHeaderView.Interactive)
        self.horizontalHeader().setSectionResizeMode(3, QHeaderView.Interactive)
        self.horizontalHeader().setSectionResizeMode(4, QHeaderView.Interactive)
        self.horizontalHeader().setSectionResizeMode(5, QHeaderView.Interactive)
        self.horizontalHeader().setSectionResizeMode(6, QHeaderView.Stretch)
        self.setColumnWidth(0, 34)
        self.setColumnWidth(1, 76)
        self.setColumnWidth(2, 148)
        self.setColumnWidth(3, 150)
        self.setColumnWidth(4, 120)
        self.setColumnWidth(5, 68)
        self.setItemDelegate(RowHoverDelegate(self))
        self.setItemDelegateForColumn(1, EnabledCheckboxDelegate(self))
        self.doubleClicked.connect(lambda _index: self.editRequested.emit())
        self.drop_indicator = ActionDropIndicator(self.viewport())
        self.drop_indicator.setGeometry(self.viewport().rect())
        self._apply_rounded_mask()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.drop_indicator.setGeometry(self.viewport().rect())
        self._apply_rounded_mask()

    def _apply_rounded_mask(self) -> None:
        if self.width() <= 0 or self.height() <= 0:
            return
        path = QPainterPath()
        path.addRoundedRect(self.rect(), 8, 8)
        self.setMask(QRegion(path.toFillPolygon().toPolygon()))

    def contextMenuEvent(self, event) -> None:
        if self.editing_locked:
            return
        self.contextRequested.emit(event.globalPos())

    def viewportEvent(self, event) -> bool:
        if event.type() == QEvent.ToolTip and isinstance(event, QHelpEvent):
            index = self.indexAt(event.pos())
            if index.isValid() and not self.editing_locked:
                QToolTip.showText(
                    event.globalPos(),
                    "Drag selected action rows to reorder them, or drag them onto a Sequential/Background tab to move them.",
                    self.viewport(),
                    self.visualRect(index),
                )
            else:
                QToolTip.hideText()
            return True
        return super().viewportEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        row = self.indexAt(event.position().toPoint()).row()
        if row != self.hovered_row:
            self.hovered_row = row
            self.viewport().update()
        self.viewport().setCursor(Qt.OpenHandCursor if row >= 0 and not self.editing_locked else Qt.ArrowCursor)
        super().mouseMoveEvent(event)

    def leaveEvent(self, event) -> None:
        if self.hovered_row != -1:
            self.hovered_row = -1
            self.viewport().update()
        self.viewport().unsetCursor()
        super().leaveEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if not self.editing_locked and event.key() in {Qt.Key_Delete, Qt.Key_Backspace}:
            self.deleteRequested.emit()
            event.accept()
            return
        if event.matches(QKeySequence.SelectAll):
            self.selectAll()
            event.accept()
            return
        super().keyPressEvent(event)

    def set_editing_locked(self, locked: bool) -> None:
        self.editing_locked = locked
        self.setDragEnabled(not locked)
        self.setAcceptDrops(not locked)

    def startDrag(self, supported_actions) -> None:
        if self.editing_locked:
            return
        row = self.currentIndex().row()
        if row < 0:
            return
        rows = self.selected_rows()
        if row not in rows:
            rows = [row]
        drag = QDrag(self)
        drag.setMimeData(encode_action_drag(self.group_name, rows))
        row_rect = self.visualRect(self.model().index(row, 0))
        row_rect.setRight(self.viewport().width())
        source_pixmap = self.viewport().grab(row_rect)
        pixmap = source_pixmap.copy()
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setOpacity(0.88)
        painter.drawPixmap(0, 0, source_pixmap)
        painter.setOpacity(1.0)
        painter.setPen(QPen(self.palette().highlight().color(), 2))
        painter.drawRoundedRect(pixmap.rect().adjusted(1, 1, -2, -2), 7, 7)
        painter.end()
        drag.setPixmap(pixmap)
        drag.setHotSpot(QPoint(min(30, pixmap.width() // 2), pixmap.height() // 2))
        self.dragging_row = row
        self.viewport().update()
        self.viewport().setCursor(Qt.ClosedHandCursor)
        drag.exec(Qt.MoveAction)
        self.dragging_row = -1
        self.drop_indicator.clear_target()
        self.viewport().update()
        self.viewport().unsetCursor()

    def dragEnterEvent(self, event) -> None:
        if not self.editing_locked and decode_action_drag(event.mimeData()):
            event.acceptProposedAction()
            return
        event.ignore()

    def dragMoveEvent(self, event) -> None:
        if not self.editing_locked and decode_action_drag(event.mimeData()):
            _insertion_row, line_y = self._drop_location(event.position().toPoint())
            self.drop_indicator.set_target(line_y)
            event.acceptProposedAction()
            return
        self.drop_indicator.clear_target()
        event.ignore()

    def dragLeaveEvent(self, event) -> None:
        self.drop_indicator.clear_target()
        super().dragLeaveEvent(event)

    def dropEvent(self, event) -> None:
        payload = decode_action_drag(event.mimeData())
        if self.editing_locked or payload is None:
            self.drop_indicator.clear_target()
            event.ignore()
            return
        source_group, source_rows = payload
        insertion_row, _line_y = self._drop_location(event.position().toPoint())
        self.drop_indicator.clear_target()
        self.actionDropped.emit(source_group, source_rows, self.group_name, insertion_row)
        event.acceptProposedAction()

    def _drop_location(self, position: QPoint) -> tuple[int, int]:
        index = self.indexAt(position)
        if index.isValid():
            rect = self.visualRect(index)
            after = position.y() > rect.center().y()
            return index.row() + (1 if after else 0), rect.bottom() + 1 if after else rect.top()
        row_count = self.model().rowCount()
        if row_count:
            last_rect = self.visualRect(self.model().index(row_count - 1, 0))
            return row_count, last_rect.bottom() + 1
        return 0, 4

    def selected_rows(self) -> list[int]:
        selection = self.selectionModel()
        if selection is None:
            return []
        return sorted({index.row() for index in selection.selectedRows() if index.isValid()})

    def select_rows(self, rows: list[int]) -> None:
        self.clearSelection()
        model = self.model()
        selection = self.selectionModel()
        if model is None or selection is None:
            return
        first = next((row for row in rows if 0 <= row < model.rowCount()), -1)
        if first >= 0:
            self.setCurrentIndex(model.index(first, 0))
        for row in rows:
            if 0 <= row < model.rowCount():
                selection.select(
                    model.index(row, 0),
                    QItemSelectionModel.Select | QItemSelectionModel.Rows,
                )


class ActionTabBar(QTabBar):
    actionDropped = Signal(str, object, str)

    def __init__(self) -> None:
        super().__init__()
        self.editing_locked = False
        self.drop_target_index = -1
        self.setAcceptDrops(True)
        self.setToolTip("Drop an action onto a tab to move it to that action queue.")

    def set_editing_locked(self, locked: bool) -> None:
        self.editing_locked = locked
        self.setAcceptDrops(not locked)

    def dragEnterEvent(self, event) -> None:
        if not self.editing_locked and decode_action_drag(event.mimeData()):
            event.acceptProposedAction()
            return
        event.ignore()

    def dragMoveEvent(self, event) -> None:
        tab_index = self.tabAt(event.position().toPoint())
        if not self.editing_locked and tab_index >= 0 and decode_action_drag(event.mimeData()):
            if tab_index != self.drop_target_index:
                self.drop_target_index = tab_index
                self.update()
            event.acceptProposedAction()
            return
        self._clear_drop_target()
        event.ignore()

    def dragLeaveEvent(self, event) -> None:
        self._clear_drop_target()
        super().dragLeaveEvent(event)

    def dropEvent(self, event) -> None:
        payload = decode_action_drag(event.mimeData())
        tab_index = self.tabAt(event.position().toPoint())
        if self.editing_locked or payload is None or tab_index < 0:
            self._clear_drop_target()
            event.ignore()
            return
        source_group, source_rows = payload
        target_group = "Sequential" if tab_index == 0 else "Background"
        self._clear_drop_target()
        self.actionDropped.emit(source_group, source_rows, target_group)
        event.acceptProposedAction()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if self.drop_target_index < 0:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        color = self.palette().highlight().color()
        fill = QColor(color)
        fill.setAlpha(42)
        painter.setBrush(fill)
        painter.setPen(QPen(color, 2))
        painter.drawRoundedRect(self.tabRect(self.drop_target_index).adjusted(2, 2, -2, -2), 8, 8)

    def _clear_drop_target(self) -> None:
        if self.drop_target_index != -1:
            self.drop_target_index = -1
            self.update()


class RoundedTableFrame(QWidget):
    def __init__(self, table: ActionTableView) -> None:
        super().__init__()
        self.setObjectName("RoundedTableFrame")
        self.setAttribute(Qt.WA_StyledBackground, False)
        self.setAutoFillBackground(False)
        self.card_color = QColor("#10192c")
        self.border_color = QColor("#233149")
        self.inner_border_color = QColor("#233149")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(0)
        layout.addWidget(table)
        self.inner_border = TableBorderOverlay(self)

    def set_theme(self, dark: bool) -> None:
        self.card_color = QColor("#10192c" if dark else "#ffffff")
        self.border_color = QColor("#233149" if dark else "#d9e2f0")
        self.inner_border_color = QColor("#233149" if dark else "#d9e2f0")
        self.inner_border.set_color(self.inner_border_color)
        self.update()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.inner_border.setGeometry(self.rect().adjusted(8, 8, -8, -8))
        self.inner_border.raise_()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        rect = self.rect().adjusted(0, 0, -1, -1)
        path = QPainterPath()
        path.addRoundedRect(rect, 12, 12)
        painter.fillPath(path, self.card_color)
        super().paintEvent(event)


class TableBorderOverlay(QWidget):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.border_color = QColor("#233149")
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

    def set_color(self, color: QColor) -> None:
        self.border_color = QColor(color)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setPen(QPen(self.border_color, 1))
        rect = self.rect().adjusted(0, 0, -1, -1)
        path = QPainterPath()
        path.addRoundedRect(rect, 8, 8)
        painter.drawPath(path)
        super().paintEvent(event)


class SidebarItem(QPushButton):
    def __init__(self, full_text: str, icon: QIcon, description: str = "") -> None:
        super().__init__(full_text)
        self.full_text = full_text
        self.description = description
        self.setIcon(icon)
        self.setIconSize(QSize(17, 17))
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(38)
        self.setCheckable(False)
        self.setProperty("navItem", True)
        self.setToolTip(self.description or self.full_text)


class QueuePane(QWidget):
    menuRequested = Signal(str, QPoint)
    overflowRequested = Signal(str, QPoint)
    addRequested = Signal(str)
    moveRequested = Signal(int)

    def __init__(self, group_name: str, model: ActionTableModel, show_repeat: bool = False) -> None:
        super().__init__()
        self.setObjectName("QueuePane")
        self.setAttribute(Qt.WA_StyledBackground, False)
        self.setAutoFillBackground(False)
        self.group_name = group_name
        self.model = model
        self.card_color = QColor("#10192c")
        self.border_color = QColor("#233149")
        self.repeat_input = QLineEdit("1")
        self.random_repeat_input = QLineEdit()
        self.random_repeat_input.setPlaceholderText("0")
        self.table = ActionTableView(model, group_name)
        self.table_frame = RoundedTableFrame(self.table)
        self.setMinimumHeight(360)
        self.icon_buttons: list[tuple[QPushButton, str, int]] = []
        self.table.contextRequested.connect(lambda point: self.menuRequested.emit(self.group_name, point))

        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)
        outer.setSpacing(12)

        toolbar = QHBoxLayout()
        title = QLabel(f"{group_name} Actions")
        title.setObjectName("SectionTitle")
        toolbar.addWidget(title)
        toolbar.addStretch(1)

        self.add_button = QPushButton("Add Action")
        self._set_icon(self.add_button, "add")
        self.add_button.clicked.connect(lambda: self.addRequested.emit(self.group_name))
        toolbar.addWidget(self.add_button)

        self.up_button = QPushButton()
        self._set_icon(self.up_button, "up")
        self.up_button.setToolTip("Move selected action up")
        self.up_button.setFixedWidth(38)
        self.up_button.clicked.connect(lambda: self.moveRequested.emit(-1))
        toolbar.addWidget(self.up_button)

        self.down_button = QPushButton()
        self._set_icon(self.down_button, "down")
        self.down_button.setToolTip("Move selected action down")
        self.down_button.setFixedWidth(38)
        self.down_button.clicked.connect(lambda: self.moveRequested.emit(1))
        toolbar.addWidget(self.down_button)

        self.more_button = QPushButton()
        self._set_icon(self.more_button, "more")
        self.more_button.setToolTip("More action options")
        self.more_button.setFixedWidth(42)
        self.more_button.clicked.connect(lambda: self.overflowRequested.emit(self.group_name, self.more_button.mapToGlobal(self.more_button.rect().bottomLeft())))
        toolbar.addWidget(self.more_button)
        outer.addLayout(toolbar)

        if show_repeat:
            repeat_row = QHBoxLayout()
            repeat_row.addWidget(QLabel("Repeat entire sequence"))
            self.repeat_input.setFixedWidth(52)
            repeat_row.addWidget(self.repeat_input)
            repeat_row.addWidget(QLabel(" + random"))
            self.random_repeat_input.setFixedWidth(52)
            repeat_row.addWidget(self.random_repeat_input)
            repeat_row.addWidget(QLabel("time(s)"))
            repeat_row.addStretch(1)
            outer.addLayout(repeat_row)

        outer.addWidget(self.table_frame, 1)
        self.update_button_states(-1)

    def set_theme(self, dark: bool) -> None:
        self.card_color = QColor("#10192c" if dark else "#ffffff")
        self.border_color = QColor("#233149" if dark else "#d9e2f0")
        self.table_frame.set_theme(dark)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        rect = self.rect().adjusted(0, 0, -1, -1)
        path = QPainterPath()
        path.addRoundedRect(rect, 16, 16)
        painter.fillPath(path, self.card_color)
        painter.setPen(QPen(self.border_color, 1))
        painter.drawPath(path)
        super().paintEvent(event)

    def _set_icon(self, button: QPushButton, name: str, size: int = 22) -> None:
        button.setIcon(app_icon(name, size=size))
        self.icon_buttons.append((button, name, size))

    def apply_icons(self, dark: bool) -> None:
        for button, name, size in self.icon_buttons:
            button.setIcon(app_icon(name, size=size, dark=dark))

    def update_button_states(self, selected_row: int | list[int]) -> None:
        row_count = self.model.rowCount()
        rows = [selected_row] if isinstance(selected_row, int) else selected_row
        valid_rows = sorted({row for row in rows if 0 <= row < row_count})
        self.up_button.setEnabled(bool(valid_rows) and min(valid_rows) > 0)
        self.down_button.setEnabled(bool(valid_rows) and max(valid_rows) < row_count - 1)

    def set_editing_locked(self, locked: bool) -> None:
        self.model.set_editing_locked(locked)
        self.table.set_editing_locked(locked)
        self.table.viewport().update()
        self.add_button.setEnabled(not locked)
        self.more_button.setEnabled(not locked)
        self.repeat_input.setEnabled(not locked)
        self.random_repeat_input.setEnabled(not locked)
        if locked:
            self.up_button.setEnabled(False)
            self.down_button.setEnabled(False)


class KeyCaptureLineEdit(QLineEdit):
    captureFocusChanged = Signal(bool)

    def focusInEvent(self, event) -> None:
        super().focusInEvent(event)
        self.selectAll()
        self.captureFocusChanged.emit(True)

    def focusOutEvent(self, event) -> None:
        super().focusOutEvent(event)
        self.captureFocusChanged.emit(False)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        parts: list[str] = []
        modifiers = event.modifiers()
        if modifiers & Qt.ControlModifier:
            parts.append("ctrl")
        if modifiers & Qt.AltModifier:
            parts.append("alt")
        if modifiers & Qt.ShiftModifier:
            parts.append("shift")
        named_keys = {
            Qt.Key_Space: "space",
            Qt.Key_Return: "enter",
            Qt.Key_Enter: "enter",
            Qt.Key_Tab: "tab",
            Qt.Key_Backspace: "backspace",
            Qt.Key_Escape: "escape",
            Qt.Key_Delete: "delete",
        }
        key_text = named_keys.get(event.key(), event.text().lower())
        if not key_text:
            key_text = QKeySequence(event.key()).toString().lower()
        if key_text in {"control", "shift", "alt", "meta"}:
            return
        if key_text:
            parts.append(key_text)
        self.setText("+".join(dict.fromkeys(parts)))
        event.accept()


class AreaOverlay(QDialog):
    def __init__(self, initial_area: ScreenArea | None = None, auto_close_on_drag: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.result = initial_area.normalized() if initial_area and initial_area.is_valid() else None
        self.saved = False
        self.auto_close_on_drag = auto_close_on_drag
        self.drag_mode = "draw"
        self.is_dragging = False
        self.start = QPoint()
        self.move_origin = QPoint()
        self.original_area: ScreenArea | None = self.result
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setCursor(Qt.CrossCursor)
        geometry = QApplication.primaryScreen().virtualGeometry()
        self.setGeometry(geometry)
        self.done_button = QPushButton("Done" if auto_close_on_drag else "Save", self)
        self.done_button.clicked.connect(self._save)
        self.done_button.resize(96, 32)
        self._position_done_button()

    def _global_to_local(self, point: QPoint) -> QPoint:
        return QPoint(point.x() - self.x(), point.y() - self.y())

    def _local_to_area(self, rect: QRect) -> ScreenArea:
        normalized = rect.normalized()
        return ScreenArea(
            self.x() + normalized.left(),
            self.y() + normalized.top(),
            normalized.width(),
            normalized.height(),
        )

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(20, 28, 44, 105))
        if self.result and self.result.is_valid():
            left, top, right, bottom = self.result.as_tuple()
            rect = QRect(left - self.x(), top - self.y(), right - left, bottom - top)
            painter.setPen(QPen(QColor("#44b8ff"), 2))
            painter.setBrush(QColor(68, 184, 255, 65))
            painter.drawRect(rect)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.LeftButton:
            return
        global_pos = event.globalPosition().toPoint()
        local_pos = self._global_to_local(global_pos)
        self.is_dragging = True
        if self.result and self._point_in_area(global_pos, self.result):
            self.drag_mode = "move"
            self.move_origin = global_pos
            self.original_area = self.result.normalized()
            return
        self.drag_mode = "draw"
        self.start = local_pos
        self.result = None
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if not self.is_dragging:
            return
        global_pos = event.globalPosition().toPoint()
        local_pos = self._global_to_local(global_pos)
        if self.drag_mode == "move" and self.original_area:
            delta = global_pos - self.move_origin
            self.result = ScreenArea(self.original_area.left + delta.x(), self.original_area.top + delta.y(), self.original_area.width, self.original_area.height)
        else:
            self.result = self._local_to_area(QRect(self.start, local_pos))
        self._position_done_button()
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.LeftButton:
            return
        if not self.is_dragging:
            return
        self.is_dragging = False
        if self.result and self.result.is_valid() and self.auto_close_on_drag:
            self.saved = True
            self.accept()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key_Escape:
            self.saved = False
            self.reject()
            return
        super().keyPressEvent(event)

    def _position_done_button(self) -> None:
        if not self.result or not self.result.is_valid():
            self.done_button.move(24, 24)
            return
        left, top, _right, _bottom = self.result.as_tuple()
        self.done_button.move(max(16, left - self.x() + 8), max(16, top - self.y() - 40))

    def _save(self) -> None:
        self.saved = bool(self.result and self.result.is_valid())
        self.accept()

    @staticmethod
    def _point_in_area(point: QPoint, area: ScreenArea) -> bool:
        left, top, right, bottom = area.as_tuple()
        return left <= point.x() <= right and top <= point.y() <= bottom


def choose_screen_area(owner: QWidget, initial_area: ScreenArea | None = None, auto_close_on_drag: bool = False) -> ScreenArea | None:
    parent = owner.parentWidget()
    overlay = AreaOverlay(initial_area, auto_close_on_drag, owner)
    selected_area: ScreenArea | None = None
    try:
        if parent:
            parent.showMinimized()
        owner.hide()
        overlay.setFocus()
        overlay.activateWindow()
        overlay.exec()
        if overlay.saved and overlay.result and overlay.result.is_valid():
            selected_area = overlay.result.normalized()
    finally:
        overlay.setWindowModality(Qt.NonModal)
        overlay.hide()
        overlay.setParent(None)
        overlay.deleteLater()
        QApplication.processEvents()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        owner.show()
        owner.raise_()
        owner.activateWindow()
        if parent:
            parent.showNormal()
            parent.raise_()
            parent.activateWindow()
    return selected_area


__all__ = [
    "ActionTabBar",
    "ActionTableModel",
    "ActionTableView",
    "AreaOverlay",
    "EnabledCheckboxDelegate",
    "GeneralActionSettings",
    "KeyCaptureLineEdit",
    "make_help_button",
    "make_help_label",
    "QueuePane",
    "PlaceholderSpinBox",
    "PlaceholderDoubleSpinBox",
    "SidebarItem",
    "choose_screen_area",
    "compact_time_label",
    "delay_label",
    "repeat_label",
    "target_label",
    "time_row",
    "plain_number_field",
]
