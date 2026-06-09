from __future__ import annotations


def build_stylesheet(dark: bool) -> str:
    if dark:
        bg = "#0b1220"
        rail = "#0f1728"
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
        disabled = "#6e809c"
        disabled_bg = "rgba(16, 25, 44, 0.45)"
        disabled_border = "rgba(35, 49, 73, 0.55)"
        row_hover = "#13213a"
        row_selected = "#17345f"
        input_bg = "#0d1628"
        scrollbar_track = "#0b1220"
        scrollbar_handle = "#33435f"
        scrollbar_handle_hover = "#4b5f82"
    else:
        bg = "#f5f7fb"
        rail = "#eef2f8"
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
        disabled = "#9aa8bc"
        disabled_bg = "rgba(255, 255, 255, 0.42)"
        disabled_border = "rgba(217, 226, 240, 0.62)"
        row_hover = "#f1f6ff"
        row_selected = "#dceaff"
        input_bg = "#ffffff"
        scrollbar_track = "#edf2f8"
        scrollbar_handle = "#b8c5d8"
        scrollbar_handle_hover = "#8fa2bd"

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
        background: {panel};
        border-bottom: 1px solid {border};
    }}
    #Sidebar {{
        background: {panel};
        border-right: 1px solid {border};
    }}
    #Sidebar, #CenterPanel, #RightPanel {{
        background: {panel};
    }}
    #CenterPanel {{
        border-right: 1px solid {border};
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
    #AppTitle {{
        font-size: 19px;
        font-weight: 700;
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
    }}
    QPushButton {{
        background: {panel_soft};
        border: 1px solid {border};
        border-radius: 10px;
        padding: 10px 14px;
        color: {fg};
    }}
    QPushButton:hover {{
        background: {hover};
        border-color: {accent};
    }}
    QPushButton:checked {{
        background: {selected};
        border-color: {accent};
    }}
    QPushButton[navItem="true"] {{
        text-align: left;
        padding-left: 14px;
        font-weight: 600;
        border-radius: 12px;
    }}
    QPushButton:disabled {{
        color: {disabled};
        background: {disabled_bg};
        border-color: {disabled_border};
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
    }}
    QSpinBox:focus, QDoubleSpinBox:focus, QLineEdit:focus, QComboBox:focus {{
        border-color: {accent};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 28px;
    }}
    QComboBox QAbstractItemView {{
        background: {card};
        color: {fg};
        border: 1px solid {border};
        selection-background-color: {selected};
        selection-color: {fg};
    }}
    QTabWidget#ActionTabs {{
        background: transparent;
    }}
    QTabWidget#ActionTabs QStackedWidget {{
        background: transparent;
        border: none;
    }}
    QTabWidget::pane {{
        border: none;
        background: transparent;
        margin-top: 10px;
    }}
    QTabWidget#ActionTabs QWidget#QueuePane {{
        background: transparent;
        border: none;
    }}
    QTabBar {{
        background: transparent;
    }}
    QTabBar::tab {{
        background: {card};
        color: {muted};
        padding: 10px 14px;
        margin-right: 8px;
        border: 1px solid {border};
        border-radius: 10px;
        font-weight: 600;
    }}
    QTabBar::tab:hover {{
        background: {hover};
        color: {fg};
        border-color: {border};
    }}
    QTabBar::tab:selected {{
        background: {selected};
        color: {fg};
        border: 1px solid {accent};
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
    QTableView::item:hover {{
        background: {row_hover};
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
    """

