"""Centralized stylesheet for the Learning Platform."""

MAIN_STYLE = """
QMainWindow, QWidget {
    background-color: #f0f2f5;
    font-family: 'Segoe UI', Arial, sans-serif;
}

/* ── Cards & Frames ─────────────────────────────────────────── */
QFrame#card {
    background-color: white;
    border-radius: 12px;
    border: 1px solid #e0e0e0;
}

/* ── Labels ─────────────────────────────────────────────────── */
QLabel {
    color: #333333;
}
QLabel#title {
    font-size: 24px;
    font-weight: bold;
    color: #1a73e8;
}
QLabel#subtitle {
    font-size: 14px;
    color: #666666;
}
QLabel#section_title {
    font-size: 18px;
    font-weight: bold;
    color: #202124;
}
QLabel#error {
    color: #d32f2f;
    font-size: 12px;
}
QLabel#success {
    color: #2e7d32;
    font-size: 12px;
}
QLabel#welcome {
    font-size: 28px;
    font-weight: bold;
    color: #1a73e8;
}

/* ── Inputs ─────────────────────────────────────────────────── */
QLineEdit {
    padding: 10px 14px;
    border: 2px solid #dadce0;
    border-radius: 8px;
    font-size: 14px;
    background-color: white;
    color: #202124;
}
QLineEdit:focus {
    border-color: #1a73e8;
}

QTextEdit {
    padding: 8px;
    border: 2px solid #dadce0;
    border-radius: 8px;
    font-size: 13px;
    background-color: white;
}

QComboBox {
    padding: 8px 12px;
    border: 2px solid #dadce0;
    border-radius: 8px;
    font-size: 13px;
    background-color: white;
}
QComboBox::drop-down {
    border: none;
    width: 30px;
}

/* ── Buttons ────────────────────────────────────────────────── */
QPushButton {
    padding: 10px 24px;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 600;
    border: none;
    cursor: pointer;
}
QPushButton#primary {
    background-color: #1a73e8;
    color: white;
}
QPushButton#primary:hover {
    background-color: #1557b0;
}
QPushButton#primary:pressed {
    background-color: #0d47a1;
}
QPushButton#secondary {
    background-color: #e8f0fe;
    color: #1a73e8;
    border: 1px solid #1a73e8;
}
QPushButton#secondary:hover {
    background-color: #d2e3fc;
}
QPushButton#danger {
    background-color: #d32f2f;
    color: white;
}
QPushButton#danger:hover {
    background-color: #b71c1c;
}
QPushButton#success_btn {
    background-color: #2e7d32;
    color: white;
}
QPushButton#success_btn:hover {
    background-color: #1b5e20;
}
QPushButton#topic_btn {
    background-color: white;
    color: #333;
    border: 2px solid #dadce0;
    padding: 20px;
    font-size: 15px;
    border-radius: 12px;
    min-height: 60px;
}
QPushButton#topic_btn:hover {
    border-color: #1a73e8;
    background-color: #e8f0fe;
    color: #1a73e8;
}

/* ── Radio buttons ──────────────────────────────────────────── */
QRadioButton {
    font-size: 14px;
    padding: 8px;
    spacing: 8px;
    color: #333;
}
QRadioButton::indicator {
    width: 18px;
    height: 18px;
}

/* ── Table ──────────────────────────────────────────────────── */
QTableWidget {
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    gridline-color: #f0f0f0;
    font-size: 13px;
    background-color: white;
}
QTableWidget::item {
    padding: 8px;
}
QHeaderView::section {
    background-color: #1a73e8;
    color: white;
    padding: 10px;
    font-weight: bold;
    border: none;
}

/* ── Tabs ───────────────────────────────────────────────────── */
QTabWidget::pane {
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    background-color: white;
}
QTabBar::tab {
    padding: 10px 20px;
    font-size: 13px;
    font-weight: 600;
    border-bottom: 3px solid transparent;
    color: #666;
}
QTabBar::tab:selected {
    color: #1a73e8;
    border-bottom: 3px solid #1a73e8;
}

/* ── Progress bar ───────────────────────────────────────────── */
QProgressBar {
    border: 1px solid #dadce0;
    border-radius: 8px;
    text-align: center;
    height: 24px;
    font-size: 12px;
    background-color: #f0f0f0;
}
QProgressBar::chunk {
    background-color: #1a73e8;
    border-radius: 7px;
}

/* ── Scroll area ────────────────────────────────────────────── */
QScrollArea {
    border: none;
    background-color: transparent;
}
QScrollBar:vertical {
    width: 8px;
    background: transparent;
}
QScrollBar::handle:vertical {
    background: #c0c0c0;
    border-radius: 4px;
    min-height: 30px;
}

/* ── Sidebar ────────────────────────────────────────────────── */
QFrame#sidebar {
    background-color: #1a237e;
    border-radius: 0px;
}
QFrame#sidebar QPushButton {
    background-color: transparent;
    color: #b0bec5;
    text-align: left;
    padding: 14px 20px;
    font-size: 14px;
    border-radius: 0px;
    border: none;
}
QFrame#sidebar QPushButton:hover {
    background-color: #283593;
    color: white;
}
QFrame#sidebar QPushButton#active_nav {
    background-color: #3949ab;
    color: white;
    border-left: 4px solid #42a5f5;
}
QFrame#sidebar QLabel {
    color: white;
}

/* ── App Header ─────────────────────────────────────────────── */
QFrame#app_header {
    background-color: #1a237e;
    border-bottom: 2px solid #3949ab;
}

/* ── Top Nav Buttons ────────────────────────────────────────── */
QPushButton#nav_btn {
    background-color: transparent;
    color: #b0bec5;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 600;
    border: none;
    border-radius: 4px;
}
QPushButton#nav_btn:hover {
    background-color: #3949ab;
    color: white;
}
QPushButton#nav_btn_active {
    background-color: #3949ab;
    color: white;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 600;
    border: none;
    border-radius: 4px;
    border-bottom: 2px solid #42a5f5;
}
QPushButton#nav_logout_btn {
    background-color: transparent;
    color: #ef9a9a;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 600;
    border: none;
    border-radius: 4px;
}
QPushButton#nav_logout_btn:hover {
    background-color: #b71c1c;
    color: white;
}

/* ── Udemy-style Cards ──────────────────────────────────────── */
QFrame#udemy_card {
    background-color: white;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
}
QFrame#udemy_card:hover {
    border-color: #1a73e8;
}

/* ── Hero Buttons ───────────────────────────────────────────── */
QPushButton#hero_btn_primary {
    background-color: white;
    color: #1a237e;
    padding: 12px 28px;
    font-size: 14px;
    font-weight: bold;
    border-radius: 4px;
    border: none;
}
QPushButton#hero_btn_primary:hover {
    background-color: #e8eaf6;
}
QPushButton#hero_btn_secondary {
    background-color: transparent;
    color: white;
    padding: 12px 28px;
    font-size: 14px;
    font-weight: bold;
    border-radius: 4px;
    border: 2px solid white;
}
QPushButton#hero_btn_secondary:hover {
    background-color: rgba(255, 255, 255, 0.1);
}
"""
