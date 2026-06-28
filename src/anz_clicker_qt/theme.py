from __future__ import annotations

from .icons import resource_path


def build_stylesheet(dark: bool) -> str:
    checkbox_check_icon = resource_path("icons/dark/checkbox_check.svg").as_posix()
    if dark:
        bg = "#0b1220"
        rail = "#0c1a2f"
        panel = "#111827"
        panel_soft = "#162033"
        card = "#10192c"
        border = "#233149"
        fg = "#ecf3ff"
        muted = "#8ea0bf"
        accent = "#3b82f6"
        accent_soft = "#1d4ed8"
        hover = "#18263d"
        selected = "#14294a"
        nav_start = "#152844"
        nav_end = "#0f1f37"
        nav_border = "#2e4568"
        disabled = "#6e809c"
        disabled_bg = "rgba(16, 25, 44, 0.45)"
        disabled_border = "rgba(35, 49, 73, 0.55)"
        row_hover = "#13213a"
        row_selected = "#17345f"
        row_selected_hover = "#24538f"
        input_bg = "#0d1628"
        checkbox_bg = "#0d1628"
        checkbox_border = "#5b6f91"
        scrollbar_track = "#0b1220"
        scrollbar_handle = "#33435f"
        scrollbar_handle_hover = "#4b5f82"
        topbar = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #081326, stop:0.55 #0d1f38, stop:1 #102944)"
        header_button = "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1b2d49, stop:1 #111d32)"
        queue_card = "#0d1b31"
    else:
        bg = "#f5f7fb"
        rail = "#e7eef9"
        panel = "#ffffff"
        panel_soft = "#eef3fb"
        card = "#ffffff"
        border = "#d9e2f0"
        fg = "#18212f"
        muted = "#5f718b"
        accent = "#2f6fff"
        accent_soft = "#dce8ff"
        hover = "#f3f7ff"
        selected = "#eaf1ff"
        nav_start = "#ffffff"
        nav_end = "#e7f0ff"
        nav_border = "#b9c9e2"
        disabled = "#9aa8bc"
        disabled_bg = "rgba(255, 255, 255, 0.42)"
        disabled_border = "rgba(217, 226, 240, 0.62)"
        row_hover = "#f1f6ff"
        row_selected = "#dceaff"
        row_selected_hover = "#b9d3ff"
        input_bg = "#ffffff"
        checkbox_bg = "#ffffff"
        checkbox_border = "#64748b"
        scrollbar_track = "#edf2f8"
        scrollbar_handle = "#b8c5d8"
        scrollbar_handle_hover = "#8fa2bd"
        topbar = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #f8fbff, stop:0.55 #edf4ff, stop:1 #e4efff)"
        header_button = "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffffff, stop:1 #e9f1ff)"
        queue_card = "#ffffff"

    return f"""
    QWidget {{
        background: {bg};
        color: {fg};
        font-family: "Segoe UI";
        font-size: 13px;
    }}
    QMainWindow {{
        background: {bg};
    }}
    #TopBar {{
        background: {topbar};
        border-bottom: 1px solid {border};
    }}
    #Sidebar {{
        background: {rail};
        border-right: 1px solid {border};
    }}
    #CenterPanel, #RightPanel {{
        background: {panel};
    }}
    #CenterPanel {{
        border-right: none;
    }}
    #BottomStatusBar {{
        background: {topbar};
        border-top: 1px solid {border};
    }}
    #TopBar QWidget,
    #TopBar QLabel,
    #BottomStatusBar QWidget,
    #BottomStatusBar QLabel {{
        background: transparent;
    }}
    #StatusDivider, #HeaderDivider {{
        background: {border};
    }}
    QDialog#ActionEditor {{
        background: {bg};
    }}
    QDialog#SettingsDialog {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {bg}, stop:1 {card});
    }}
    QDialog#ActionOrderDialog {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {bg}, stop:1 {card});
    }}
    #ActionEditorSection {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {card}, stop:1 {queue_card});
        border: 1px solid {border};
        border-radius: 12px;
    }}
    #ActionEditorSection QLabel,
    #ActionEditorSection QWidget {{
        background: transparent;
    }}
    #ActionEditorSectionTitle {{
        color: {accent};
        font-size: 16px;
        font-weight: 800;
    }}
    QFrame#SettingsSection {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {card}, stop:1 {queue_card});
        border: 1px solid {border};
        border-radius: 12px;
    }}
    QFrame#SettingsSection QLabel,
    QFrame#SettingsSection QWidget {{
        background: transparent;
    }}
    QLabel#SettingsSectionIcon {{
        min-width: 24px;
        max-width: 24px;
        min-height: 24px;
        max-height: 24px;
        border: none;
        background: transparent;
    }}
    QLabel#SettingsSectionTitle {{
        color: {fg};
        font-size: 15px;
        font-weight: 800;
    }}
    QLabel#SettingsNote {{
        color: {muted};
        font-size: 12px;
    }}
    QListWidget#ActionOrderList {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {card}, stop:1 {queue_card});
        border: 1px solid {accent};
        border-radius: 12px;
        padding: 8px;
        outline: none;
        alternate-background-color: transparent;
    }}
    QListWidget#ActionOrderList::item {{
        background: transparent;
        border: 1px solid transparent;
        border-bottom: 1px solid {border};
        border-radius: 8px;
        padding: 9px 10px;
        color: {fg};
    }}
    QListWidget#ActionOrderList::item:hover {{
        background: {row_hover};
        border-color: {border};
    }}
    QListWidget#ActionOrderList::item:selected {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {row_selected}, stop:1 {selected});
        border: 1px solid {accent};
        color: {fg};
    }}
    QListWidget#ActionOrderList::item:selected:hover {{
        background: {row_selected_hover};
        border-color: {accent};
    }}
    QListWidget#ActionOrderList QScrollBar:vertical {{
        background: {scrollbar_track};
        border: none;
        width: 14px;
        margin: 8px 4px 8px 2px;
        border-radius: 7px;
    }}
    QListWidget#ActionOrderList QScrollBar::handle:vertical {{
        background: {scrollbar_handle};
        border: 3px solid {scrollbar_track};
        border-radius: 7px;
        min-height: 34px;
    }}
    QListWidget#ActionOrderList QScrollBar::handle:vertical:hover {{
        background: {scrollbar_handle_hover};
    }}
    QListWidget#ActionOrderList QScrollBar::add-line:vertical,
    QListWidget#ActionOrderList QScrollBar::sub-line:vertical {{
        height: 0;
        border: none;
        background: transparent;
    }}
    QListWidget#ActionOrderList QScrollBar::add-page:vertical,
    QListWidget#ActionOrderList QScrollBar::sub-page:vertical {{
        background: transparent;
    }}
    #DialogTitle {{
        font-size: 24px;
        font-weight: 800;
    }}
    #DialogSubtitle {{
        color: {muted};
        font-size: 13px;
    }}
    #InfoCard {{
        background: {card};
        border: 1px solid {border};
        border-radius: 10px;
    }}
    #InfoCard QWidget {{
        background: transparent;
    }}
    QLabel {{
        background: transparent;
    }}
    QPushButton QLabel,
    QFrame QLabel,
    QWidget QLabel {{
        background: transparent;
    }}
    #AppTitle {{
        font-size: 22px;
        font-weight: 700;
    }}
    #AppSlogan {{
        color: {muted};
        font-size: 13px;
        font-weight: 500;
    }}
    #SidebarTitle {{
        font-size: 15px;
        font-weight: 700;
    }}
    #SidebarSubtle {{
        color: {muted};
        font-size: 12px;
    }}
    #VersionLabel {{
        color: {muted};
        font-size: 12px;
        font-weight: 500;
    }}
    #SidebarSection {{
        color: {muted};
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 1px;
        padding-top: 6px;
    }}
    QLabel#SectionTitle, QLabel#CardTitle {{
        font-size: 14px;
        font-weight: 700;
    }}
    QLabel#MetricValue {{
        color: {muted};
        background: transparent;
    }}
    QPushButton {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {nav_start}, stop:1 {nav_end});
        border: 1px solid {nav_border};
        border-radius: 10px;
        padding: 10px 14px;
        color: {fg};
        font-weight: 600;
    }}
    QPushButton:hover {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {hover}, stop:1 {selected});
        border-color: {accent};
    }}
    QPushButton:checked {{
        background: {selected};
        border-color: {accent};
    }}
    QPushButton[navItem="true"] {{
        text-align: left;
        padding: 8px 11px;
        font-weight: 600;
        border-radius: 10px;
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {nav_start}, stop:1 {nav_end});
        border-color: {nav_border};
    }}
    QPushButton[navItem="true"]:hover {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {hover}, stop:1 {selected});
        border-color: {accent};
    }}
    QPushButton#HeaderButton {{
        background: {header_button};
        font-weight: 600;
    }}
    QPushButton#HeaderButton:hover {{
        background: {hover};
        border-color: {accent};
    }}
    QPushButton:disabled {{
        color: {disabled};
        background: {disabled_bg};
        border-color: {disabled_border};
    }}
    QPushButton#SaveButton {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2f8cff, stop:1 #0f63e6);
        border: 1px solid #58a6ff;
        color: white;
        font-weight: 800;
        min-width: 104px;
    }}
    QPushButton#SaveButton:hover {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #48a0ff, stop:1 #1d72f3);
        border-color: #8cc4ff;
    }}
    QPushButton#SaveButton:pressed {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0f63e6, stop:1 #0b4ec4);
    }}
    QPushButton#PrimaryAction {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #22c55e, stop:1 #16a34a);
        border: none;
        color: white;
        font-weight: 700;
    }}
    QPushButton#PrimaryAction:hover {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #16a34a, stop:1 #15803d);
        border: none;
    }}
    QPushButton#HelpButton {{
        min-width: 30px;
        max-width: 30px;
        min-height: 30px;
        max-height: 30px;
        padding: 0;
        border-radius: 15px;
        font-weight: 800;
        font-size: 13px;
        text-align: center;
    }}
    QLineEdit {{
        background: {input_bg};
        border: 1px solid {border};
        border-radius: 8px;
        padding: 6px 8px;
    }}
    QSpinBox, QDoubleSpinBox, QComboBox {{
        background: {input_bg};
        border: 1px solid {border};
        border-radius: 8px;
        padding: 7px 10px;
        min-height: 22px;
        color: {fg};
        combobox-popup: 0;
    }}
    QSpinBox:focus, QDoubleSpinBox:focus, QLineEdit:focus, QComboBox:focus {{
        border-color: {accent};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 28px;
    }}
    QComboBox::down-arrow {{
        width: 8px;
        height: 8px;
    }}
    QComboBox QAbstractItemView {{
        background: {queue_card};
        color: {fg};
        border: 1px solid {border};
        border-radius: 10px;
        padding: 6px;
        outline: none;
        selection-background-color: {selected};
        selection-color: {fg};
    }}
    QComboBox QAbstractItemView::item {{
        min-height: 28px;
        padding: 6px 10px;
        border-radius: 7px;
        background: transparent;
    }}
    QComboBox QAbstractItemView::item:hover {{
        background: {row_hover};
        color: {fg};
    }}
    QComboBox QAbstractItemView::item:selected {{
        background: {row_selected};
        color: {fg};
    }}
    QComboBox QScrollBar:vertical {{
        background: {scrollbar_track};
        border: none;
        width: 13px;
        margin: 5px 3px 5px 0;
        border-radius: 6px;
    }}
    QComboBox QScrollBar::handle:vertical {{
        background: {scrollbar_handle};
        border: 3px solid {scrollbar_track};
        border-radius: 6px;
        min-height: 32px;
    }}
    QComboBox QScrollBar::handle:vertical:hover {{
        background: {scrollbar_handle_hover};
    }}
    QComboBox QScrollBar::add-line:vertical,
    QComboBox QScrollBar::sub-line:vertical {{
        height: 0;
        border: none;
        background: transparent;
    }}
    QComboBox QScrollBar::add-page:vertical,
    QComboBox QScrollBar::sub-page:vertical {{
        background: transparent;
    }}
    QCheckBox {{
        background: transparent;
        spacing: 8px;
    }}
    QCheckBox::indicator {{
        width: 16px;
        height: 16px;
        border: 1px solid {checkbox_border};
        border-radius: 4px;
        background: {checkbox_bg};
    }}
    QCheckBox::indicator:hover {{
        border-color: {accent};
    }}
    QCheckBox::indicator:checked {{
        background: {accent};
        border-color: {accent};
        image: url("{checkbox_check_icon}");
    }}
    QCheckBox::indicator:checked:disabled {{
        background: {disabled};
        border-color: {disabled};
    }}
    QCheckBox::indicator:unchecked:disabled {{
        background: {disabled_bg};
        border-color: {disabled_border};
    }}
    QTabWidget#ActionTabs {{
        background: transparent;
    }}
    QTabWidget#ActionTabs QStackedWidget {{
        background: transparent;
        border: none;
    }}
    QTabWidget#ActionTabs::tab-bar {{
        left: 18px;
    }}
    QTabWidget::pane {{
        border: none;
        background: transparent;
        margin-top: 0;
    }}
    QTabWidget#ActionTabs QWidget#QueuePane {{
        background: transparent;
        border: none;
    }}
    QTabBar {{
        background: transparent;
        border: none;
        outline: none;
    }}
    QTabBar::tab {{
        background: {queue_card};
        color: {muted};
        padding: 11px 18px;
        margin-right: 0;
        margin-bottom: -1px;
        border: 1px solid {border};
        border-top-left-radius: 10px;
        border-top-right-radius: 10px;
        border-bottom-left-radius: 0;
        border-bottom-right-radius: 0;
        font-weight: 600;
        outline: none;
    }}
    QTabBar::tab:hover {{
        background: {hover};
        color: {fg};
        border-color: {accent};
    }}
    QTabBar::tab:selected {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {selected}, stop:1 {accent_soft});
        color: {fg};
        border: 1px solid {accent};
        border-bottom-color: {queue_card};
    }}
    QDialog#TutorialDialog {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {bg}, stop:1 {card});
    }}
    QDialog#TutorialDialog QLabel {{
        background: transparent;
    }}
    QLabel#TutorialHeroIcon {{
        min-width: 46px;
        max-width: 46px;
        min-height: 46px;
        max-height: 46px;
        border-radius: 23px;
        border: 1px solid {accent};
        background: {accent_soft};
        color: {accent};
        font-size: 23px;
        font-weight: 800;
    }}
    QFrame#TutorialSection {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {card}, stop:1 {queue_card});
        border: 1px solid {border};
        border-radius: 12px;
    }}
    QFrame#TutorialSection QLabel,
    QFrame#TutorialSection QWidget {{
        background: transparent;
    }}
    QLabel#TutorialSectionIcon {{
        min-width: 50px;
        max-width: 50px;
        min-height: 50px;
        max-height: 50px;
        border-radius: 10px;
        border: 1px solid {border};
        background: {hover};
        color: {accent};
        font-size: 18px;
        font-weight: 800;
    }}
    QLabel#TutorialSectionTitle {{
        color: {fg};
        font-size: 15px;
        font-weight: 800;
    }}
    QLabel#TutorialSectionBody {{
        color: {muted};
        font-size: 12px;
    }}
    QHeaderView::section {{
        background: {panel_soft};
        color: {muted};
        border: none;
        border-right: 1px solid {border};
        border-bottom: 1px solid {border};
        padding: 10px 8px;
        font-weight: 600;
    }}
    QTableView#ActionTableView {{
        background: transparent;
        border: none;
        border-radius: 0;
        gridline-color: {border};
        selection-background-color: {row_selected};
        selection-color: {fg};
        outline: none;
    }}
    QTableView#ActionTableView::viewport {{
        background: {card};
        border-radius: 0;
    }}
    QTableView::item {{
        padding: 8px;
        border: none;
    }}
    QTableView::item:selected {{
        background: {row_selected};
        color: {fg};
        border: none;
    }}
    QTableView#ActionTableView::item:hover {{
        background: {row_hover};
    }}
    QTableView#ActionTableView::item:selected:hover {{
        background: {row_selected_hover};
        color: {fg};
    }}
    QTableView#ActionTableView QScrollBar:vertical {{
        background: {scrollbar_track};
        border: none;
        border-left: 1px solid {border};
        width: 13px;
        margin: 0;
    }}
    QTableView#ActionTableView QScrollBar::handle:vertical {{
        background: {scrollbar_handle};
        border: 3px solid {scrollbar_track};
        border-radius: 6px;
        min-height: 34px;
    }}
    QTableView#ActionTableView QScrollBar::handle:vertical:hover {{
        background: {scrollbar_handle_hover};
    }}
    QTableView#ActionTableView QScrollBar::add-line:vertical,
    QTableView#ActionTableView QScrollBar::sub-line:vertical {{
        height: 0;
        border: none;
        background: transparent;
    }}
    QTableView#ActionTableView QScrollBar::add-page:vertical,
    QTableView#ActionTableView QScrollBar::sub-page:vertical {{
        background: transparent;
    }}
    QTableView#ActionTableView QScrollBar:horizontal {{
        background: {scrollbar_track};
        border: none;
        border-top: 1px solid {border};
        height: 13px;
        margin: 0;
    }}
    QTableView#ActionTableView QScrollBar::handle:horizontal {{
        background: {scrollbar_handle};
        border: 3px solid {scrollbar_track};
        border-radius: 6px;
        min-width: 34px;
    }}
    QTableView#ActionTableView QScrollBar::handle:horizontal:hover {{
        background: {scrollbar_handle_hover};
    }}
    QTableView#ActionTableView QScrollBar::add-line:horizontal,
    QTableView#ActionTableView QScrollBar::sub-line:horizontal {{
        width: 0;
        border: none;
        background: transparent;
    }}
    QTableView#ActionTableView QScrollBar::add-page:horizontal,
    QTableView#ActionTableView QScrollBar::sub-page:horizontal {{
        background: transparent;
    }}
    QAbstractScrollArea#ActionTableView::corner {{
        background: {scrollbar_track};
        border: none;
    }}
    QProgressBar#ProgressBar {{
        border-radius: 5px;
        background: {panel_soft};
        border: 1px solid {border};
    }}
    QProgressBar#ProgressBar::chunk {{
        border-radius: 4px;
        background: {accent};
    }}
    QMenu {{
        background: {panel};
        border: 1px solid {border};
        padding: 8px;
    }}
    QMenu::item {{
        padding: 8px 18px;
        border-radius: 8px;
    }}
    QMenu::item:selected {{
        background: {hover};
    }}
    #EmptyActionState {{
        background: rgba(0, 0, 0, 0);
    }}
    #EmptyStateIcon {{
        color: {muted};
        font-size: 42px;
        border: 1px solid {border};
        border-radius: 34px;
        min-width: 68px;
        max-width: 68px;
        min-height: 68px;
        max-height: 68px;
    }}
    #EmptyStateTitle {{
        color: {fg};
        font-size: 15px;
        font-weight: 600;
    }}
    #EmptyStateHint {{
        color: {muted};
        font-size: 13px;
    }}
    """

