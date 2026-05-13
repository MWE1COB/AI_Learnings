import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QFrame, QStackedWidget, QMessageBox,
    QGridLayout, QRadioButton, QButtonGroup, QScrollArea, QTableWidget,
    QTableWidgetItem, QHeaderView, QComboBox, QProgressBar, QSpacerItem,
    QSizePolicy, QTabWidget, QDialog, QFormLayout, QTextEdit,
)
from PyQt5.QtCore import Qt, QSize, QTimer, QRectF
from PyQt5.QtGui import QFont, QIcon, QPixmap, QPainter, QColor, QPen

import database as db
from quiz_engine import generate_quiz_with_ai, configure_gemini, GENAI_AVAILABLE, get_quiz_timer, PASS_PERCENTAGE
from styles import MAIN_STYLE


# ═══════════════════════════════════════════════════════════════════
#  LOGIN / REGISTER SCREEN
# ═══════════════════════════════════════════════════════════════════
class LoginScreen(QWidget):
    def __init__(self, on_login):
        super().__init__()
        self.on_login = on_login
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        # Card container
        card = QFrame()
        card.setObjectName("card")
        card.setFixedSize(420, 520)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(40, 40, 40, 40)
        card_layout.setSpacing(16)

        # Logo / Title
        title = QLabel("🎓 Learning Platform")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignCenter)

        subtitle = QLabel("Sign in to continue learning")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignCenter)

        # Inputs
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        self.username_input.setMinimumHeight(44)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setMinimumHeight(44)
        self.password_input.returnPressed.connect(self._handle_login)

        # Error label
        self.error_label = QLabel("")
        self.error_label.setObjectName("error")
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.hide()

        # Login button
        login_btn = QPushButton("Sign In")
        login_btn.setObjectName("primary")
        login_btn.setMinimumHeight(44)
        login_btn.clicked.connect(self._handle_login)

        # Register link
        register_btn = QPushButton("Don't have an account? Register")
        register_btn.setObjectName("secondary")
        register_btn.clicked.connect(self._show_register)

        card_layout.addWidget(title)
        card_layout.addWidget(subtitle)
        card_layout.addSpacing(10)
        card_layout.addWidget(self.username_input)
        card_layout.addWidget(self.password_input)
        card_layout.addWidget(self.error_label)
        card_layout.addWidget(login_btn)
        card_layout.addStretch()
        card_layout.addWidget(register_btn)

        layout.addWidget(card)

    def _handle_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        if not username or not password:
            self._show_error("Please enter both username and password.")
            return
        user = db.authenticate(username, password)
        if user:
            self.error_label.hide()
            self.username_input.clear()
            self.password_input.clear()
            self.on_login(user)
        else:
            self._show_error("Invalid username or password.")

    def _show_error(self, msg):
        self.error_label.setText(msg)
        self.error_label.show()

    def _show_register(self):
        dlg = RegisterDialog(self)
        dlg.exec_()


class RegisterDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Register")
        self.setFixedSize(380, 360)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(12)

        title = QLabel("Create Account")
        title.setObjectName("section_title")
        title.setAlignment(Qt.AlignCenter)

        self.fullname_input = QLineEdit()
        self.fullname_input.setPlaceholderText("Full Name")
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Email (optional)")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.Password)

        self.msg_label = QLabel("")
        self.msg_label.setAlignment(Qt.AlignCenter)
        self.msg_label.hide()

        register_btn = QPushButton("Register")
        register_btn.setObjectName("primary")
        register_btn.setMinimumHeight(40)
        register_btn.clicked.connect(self._handle_register)

        layout.addWidget(title)
        layout.addWidget(self.fullname_input)
        layout.addWidget(self.username_input)
        layout.addWidget(self.email_input)
        layout.addWidget(self.password_input)
        layout.addWidget(self.msg_label)
        layout.addWidget(register_btn)

    def _handle_register(self):
        fullname = self.fullname_input.text().strip()
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        email = self.email_input.text().strip()

        if not fullname or not username or not password:
            self.msg_label.setObjectName("error")
            self.msg_label.setStyleSheet("color: #d32f2f;")
            self.msg_label.setText("Please fill in all required fields.")
            self.msg_label.show()
            return

        if len(password) < 4:
            self.msg_label.setObjectName("error")
            self.msg_label.setStyleSheet("color: #d32f2f;")
            self.msg_label.setText("Password must be at least 4 characters.")
            self.msg_label.show()
            return

        ok, msg = db.register_user(username, password, fullname, email)
        if ok:
            self.msg_label.setStyleSheet("color: #2e7d32;")
            self.msg_label.setText("✓ " + msg)
            self.msg_label.show()
            QTimer.singleShot(1500, self.accept)
        else:
            self.msg_label.setStyleSheet("color: #d32f2f;")
            self.msg_label.setText(msg)
            self.msg_label.show()


# ═══════════════════════════════════════════════════════════════════
#  DASHBOARD SCREEN (Udemy-style)
# ═══════════════════════════════════════════════════════════════════
class DashboardScreen(QWidget):
    def __init__(self, user, navigate_to):
        super().__init__()
        self.user = user
        self.navigate_to = navigate_to
        self._build_ui()

    def _build_ui(self):
        # Scrollable content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Hero Banner ─────────────────────────────────────────
        hero = QFrame()
        hero.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1a237e, stop:0.5 #283593, stop:1 #3949ab);
                border-radius: 0px;
                padding: 40px;
            }
        """)
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(60, 40, 60, 40)
        hero_layout.setSpacing(12)

        welcome = QLabel(f"Welcome back, {self.user['full_name']}!")
        welcome.setStyleSheet("color: white; font-size: 28px; font-weight: bold; background: transparent;")

        subtitle = QLabel("Continue your learning journey. Pick up where you left off or explore new topics.")
        subtitle.setStyleSheet("color: #b3c7ff; font-size: 15px; background: transparent;")
        subtitle.setWordWrap(True)

        hero_btn_layout = QHBoxLayout()
        hero_btn_layout.setSpacing(12)

        explore_btn = QPushButton("Explore Topics")
        explore_btn.setObjectName("hero_btn_primary")
        explore_btn.setCursor(Qt.PointingHandCursor)
        explore_btn.clicked.connect(lambda: self.navigate_to("topics"))

        profile_btn = QPushButton("My Progress")
        profile_btn.setObjectName("hero_btn_secondary")
        profile_btn.setCursor(Qt.PointingHandCursor)
        profile_btn.clicked.connect(lambda: self.navigate_to("profile"))

        hero_btn_layout.addWidget(explore_btn)
        hero_btn_layout.addWidget(profile_btn)
        hero_btn_layout.addStretch()

        hero_layout.addWidget(welcome)
        hero_layout.addWidget(subtitle)
        hero_layout.addSpacing(16)
        hero_layout.addLayout(hero_btn_layout)

        layout.addWidget(hero)

        # ── Quick Actions Section ───────────────────────────────
        section_widget = QWidget()
        section_widget.setStyleSheet("background-color: white;")
        section_layout = QVBoxLayout(section_widget)
        section_layout.setContentsMargins(60, 30, 60, 30)
        section_layout.setSpacing(20)

        section_title = QLabel("Quick Actions")
        section_title.setStyleSheet("font-size: 22px; font-weight: bold; color: #1c1d1f;")
        section_layout.addWidget(section_title)

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(20)

        actions = [
            ("📚", "Browse Topics", "Explore learning topics and take quizzes", "topics"),
            ("👤", "My Profile", "View your skills and track progress", "profile"),
        ]
        if self.user["is_admin"]:
            actions.append(("⚙️", "Admin Panel", "Manage users and platform settings", "admin"))

        for icon, title, desc, target in actions:
            card = self._make_udemy_card(icon, title, desc, target)
            cards_layout.addWidget(card)

        # Add a spacer if few cards
        if len(actions) < 3:
            cards_layout.addStretch()

        section_layout.addLayout(cards_layout)
        layout.addWidget(section_widget)

        # ── Skills Progress Section ─────────────────────────────
        skills_widget = QWidget()
        skills_widget.setStyleSheet("background-color: #f7f9fa;")
        skills_layout_outer = QVBoxLayout(skills_widget)
        skills_layout_outer.setContentsMargins(60, 30, 60, 30)
        skills_layout_outer.setSpacing(16)

        skills_header = QHBoxLayout()
        skills_title = QLabel("📊 Your Learning Progress")
        skills_title.setStyleSheet("font-size: 22px; font-weight: bold; color: #1c1d1f;")
        skills_header.addWidget(skills_title)
        skills_header.addStretch()
        skills_layout_outer.addLayout(skills_header)

        self.skills_layout = QVBoxLayout()
        skills_layout_outer.addLayout(self.skills_layout)
        skills_layout_outer.addStretch()

        layout.addWidget(skills_widget)
        layout.addStretch()

        scroll.setWidget(content)

        # Main layout wrapping the scroll area
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

        self._refresh_skills()

    def _make_udemy_card(self, icon, title, desc, target):
        card = QFrame()
        card.setObjectName("udemy_card")
        card.setMinimumHeight(160)
        card.setMinimumWidth(250)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(8)

        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 32px; background: transparent;")

        t = QLabel(title)
        t.setStyleSheet("font-size: 16px; font-weight: bold; color: #1c1d1f;")

        d = QLabel(desc)
        d.setStyleSheet("font-size: 13px; color: #6a6f73;")
        d.setWordWrap(True)

        btn = QPushButton("Start →")
        btn.setObjectName("primary")
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(lambda checked, t=target: self.navigate_to(t))

        card_layout.addWidget(icon_label)
        card_layout.addWidget(t)
        card_layout.addWidget(d)
        card_layout.addStretch()
        card_layout.addWidget(btn)
        return card

    def _refresh_skills(self):
        # Clear existing
        while self.skills_layout.count():
            child = self.skills_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        skills = db.get_user_skills(self.user["id"])
        if not skills:
            no_skills = QLabel("No skills added yet. Browse topics to start learning!")
            no_skills.setObjectName("subtitle")
            self.skills_layout.addWidget(no_skills)
            return

        for skill in skills:
            row = QFrame()
            row.setObjectName("card")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(16, 12, 16, 12)

            topic_label = QLabel(f"  {skill['topic']}")
            topic_label.setFont(QFont("Segoe UI", 13, QFont.Bold))

            level_name = db.SKILL_LEVELS.get(skill["self_rated_level"], "Unknown")
            validated = skill["validated_level"]
            validated_name = db.SKILL_LEVELS.get(validated, "None")

            progress = QProgressBar()
            progress.setMaximum(4)
            progress.setValue(validated)
            progress.setFormat(f"Validated: {validated_name}")
            progress.setMinimumWidth(200)

            status_label = QLabel()
            if validated >= skill["self_rated_level"]:
                status_label.setText("  ✅ Validated")
                status_label.setStyleSheet("color: #2e7d32; font-weight: bold;")
            else:
                next_level = validated + 1
                next_name = db.SKILL_LEVELS.get(next_level, "")
                status_label.setText(f"  ⏳ Next: {next_name}")
                status_label.setStyleSheet("color: #e65100; font-weight: bold;")

            row_layout.addWidget(topic_label)
            row_layout.addStretch()
            row_layout.addWidget(progress)
            row_layout.addWidget(status_label)
            self.skills_layout.addWidget(row)

    def refresh(self):
        self._refresh_skills()


# ═══════════════════════════════════════════════════════════════════
#  TOPIC SELECTION SCREEN
# ═══════════════════════════════════════════════════════════════════
class TopicSelectionScreen(QWidget):
    def __init__(self, user, on_topic_selected):
        super().__init__()
        self.user = user
        self.on_topic_selected = on_topic_selected
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(16)

        title = QLabel("📚 Choose a Topic")
        title.setObjectName("title")
        layout.addWidget(title)

        subtitle = QLabel("Select a topic to rate yourself and take the quiz")
        subtitle.setObjectName("subtitle")
        layout.addWidget(subtitle)
        layout.addSpacing(10)

        grid = QGridLayout()
        grid.setSpacing(16)

        icons = ["💻", "🐍", "☕", "🌐", "🗄️", "🔢", "⚡", "🎨"]
        for i, topic in enumerate(db.TOPICS):
            btn = QPushButton(f"{icons[i % len(icons)]}  {topic}")
            btn.setObjectName("topic_btn")
            btn.setMinimumHeight(80)
            btn.clicked.connect(lambda checked, t=topic: self.on_topic_selected(t))
            grid.addWidget(btn, i // 3, i % 3)

        layout.addLayout(grid)
        layout.addStretch()


# ═══════════════════════════════════════════════════════════════════
#  SKILL RATING DIALOG
# ═══════════════════════════════════════════════════════════════════
class SkillRatingDialog(QDialog):
    def __init__(self, user, topic, on_start_quiz, parent=None):
        super().__init__(parent)
        self.user = user
        self.topic = topic
        self.on_start_quiz = on_start_quiz
        self.setWindowTitle(f"Rate Yourself - {topic}")
        self.setFixedSize(450, 400)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(16)

        title = QLabel(f"📝 {self.topic}")
        title.setObjectName("section_title")
        title.setAlignment(Qt.AlignCenter)

        instruction = QLabel("Rate your current skill level:")
        instruction.setObjectName("subtitle")
        instruction.setAlignment(Qt.AlignCenter)

        layout.addWidget(title)
        layout.addWidget(instruction)
        layout.addSpacing(10)

        self.level_group = QButtonGroup(self)
        level_descriptions = {
            1: "Beginner – New to this topic",
            2: "Moderate – Know the basics",
            3: "Intermediate – Can build projects",
            4: "Expert – Deep understanding",
        }

        current_validated = db.get_validated_level(self.user["id"], self.topic)

        for level, desc in level_descriptions.items():
            radio = QRadioButton(f"  {level}. {desc}")
            radio.setFont(QFont("Segoe UI", 12))
            if level == 1:
                radio.setChecked(True)
            self.level_group.addButton(radio, level)
            layout.addWidget(radio)

        layout.addSpacing(10)

        # Show current validated level
        if current_validated > 0:
            validated_name = db.SKILL_LEVELS.get(current_validated, "")
            info = QLabel(f"✅ You have validated up to: {validated_name} (Level {current_validated})")
            info.setStyleSheet("color: #2e7d32; font-size: 12px; font-weight: bold;")
            info.setAlignment(Qt.AlignCenter)
            layout.addWidget(info)

        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("secondary")
        cancel_btn.clicked.connect(self.reject)

        start_btn = QPushButton("Start Quiz →")
        start_btn.setObjectName("primary")
        start_btn.setMinimumHeight(40)
        start_btn.clicked.connect(self._start)

        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(start_btn)
        layout.addLayout(btn_layout)

    def _start(self):
        selected_level = self.level_group.checkedId()
        db.set_self_rated_level(self.user["id"], self.topic, selected_level)

        # Determine quiz level: next level to validate
        current_validated = db.get_validated_level(self.user["id"], self.topic)
        quiz_level = current_validated + 1
        if quiz_level > 4:
            QMessageBox.information(self, "Fully Validated",
                                    f"You have already validated all levels for {self.topic}! 🎉")
            self.accept()
            return

        self.accept()
        self.on_start_quiz(self.topic, quiz_level)


# ═══════════════════════════════════════════════════════════════════
#  QUIZ SCREEN
# ═══════════════════════════════════════════════════════════════════
class QuizScreen(QWidget):
    def __init__(self, user, topic, level, on_quiz_complete):
        super().__init__()
        self.user = user
        self.topic = topic
        self.level = level
        self.on_quiz_complete = on_quiz_complete
        self.questions = []
        self.current_q = 0
        self.score = 0
        self.user_answers = {}
        self.remaining_time = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self._build_ui()
        self._load_quiz()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header bar
        header_frame = QFrame()
        header_frame.setStyleSheet("background-color: white; border-bottom: 1px solid #e0e0e0;")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(20, 12, 20, 12)

        self.topic_label = QLabel(f"📝 {self.topic} – {db.SKILL_LEVELS.get(self.level, '')} Quiz")
        self.topic_label.setObjectName("section_title")
        self.timer_label = QLabel("⏱ --:--")
        self.timer_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.timer_label.setStyleSheet("color: #2e7d32; font-weight: bold;")
        self.progress_label = QLabel("Question 1/10")
        self.progress_label.setObjectName("subtitle")

        header_layout.addWidget(self.topic_label)
        header_layout.addStretch()
        header_layout.addWidget(self.timer_label)
        header_layout.addWidget(self.progress_label)
        layout.addWidget(header_frame)

        # Main content: sidebar + question area
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # ── Left sidebar: question navigator ──
        self.nav_panel = QFrame()
        self.nav_panel.setFixedWidth(180)
        self.nav_panel.setStyleSheet("background-color: #fafafa; border-right: 1px solid #e0e0e0;")
        nav_layout = QVBoxLayout(self.nav_panel)
        nav_layout.setContentsMargins(10, 16, 10, 10)
        nav_layout.setSpacing(6)

        nav_title = QLabel("Questions")
        nav_title.setFont(QFont("Segoe UI", 13, QFont.Bold))
        nav_title.setStyleSheet("color: #333;")
        nav_layout.addWidget(nav_title)

        self.nav_grid = QGridLayout()
        self.nav_grid.setSpacing(6)
        self.nav_buttons = []
        nav_layout.addLayout(self.nav_grid)

        # Legend
        nav_layout.addSpacing(10)
        legend_frame = QFrame()
        legend_layout = QVBoxLayout(legend_frame)
        legend_layout.setContentsMargins(0, 0, 0, 0)
        legend_layout.setSpacing(4)
        for color, text in [("#2e7d32", "Answered"), ("#d32f2f", "Not Answered"), ("#1a73e8", "Current")]:
            row = QHBoxLayout()
            dot = QLabel("●")
            dot.setStyleSheet(f"color: {color}; font-size: 14px;")
            dot.setFixedWidth(18)
            lbl = QLabel(text)
            lbl.setStyleSheet("color: #666; font-size: 11px;")
            row.addWidget(dot)
            row.addWidget(lbl)
            row.addStretch()
            legend_layout.addLayout(row)
        nav_layout.addWidget(legend_frame)
        nav_layout.addStretch()

        self.nav_panel.hide()
        content_layout.addWidget(self.nav_panel)

        # ── Right side: question content ──
        right_side = QVBoxLayout()
        right_side.setContentsMargins(20, 16, 20, 10)
        right_side.setSpacing(12)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(10)
        self.progress_bar.setValue(0)
        right_side.addWidget(self.progress_bar)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_inner = QVBoxLayout(scroll_widget)

        self.question_card = QFrame()
        self.question_card.setObjectName("card")
        self.question_card.setStyleSheet("QFrame#card { border: none; }")
        self.card_layout = QVBoxLayout(self.question_card)
        self.card_layout.setContentsMargins(30, 30, 30, 30)
        self.card_layout.setSpacing(16)

        self.loading_label = QLabel("⏳ Generating quiz questions...")
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setFont(QFont("Segoe UI", 14))
        self.loading_label.setStyleSheet("color: #1a73e8;")
        self.card_layout.addWidget(self.loading_label)

        self.type_badge = QLabel("")
        self.type_badge.setAlignment(Qt.AlignLeft)
        self.type_badge.hide()
        self.card_layout.addWidget(self.type_badge)

        self.question_label = QLabel("")
        self.question_label.setFont(QFont("Segoe UI", 15))
        self.question_label.setWordWrap(True)
        self.question_label.hide()
        self.card_layout.addWidget(self.question_label)

        # MCQ radio buttons
        self.mcq_frame = QFrame()
        mcq_layout = QVBoxLayout(self.mcq_frame)
        mcq_layout.setContentsMargins(0, 0, 0, 0)
        self.option_group = QButtonGroup(self)
        self.option_buttons = []
        for i in range(4):
            rb = QRadioButton("")
            rb.setFont(QFont("Segoe UI", 13))
            self.option_group.addButton(rb, i)
            self.option_buttons.append(rb)
            mcq_layout.addWidget(rb)
        self.mcq_frame.hide()
        self.card_layout.addWidget(self.mcq_frame)

        # Fill-in-blank text input
        self.fill_frame = QFrame()
        fill_layout = QVBoxLayout(self.fill_frame)
        fill_layout.setContentsMargins(0, 0, 0, 0)
        fill_layout.setSpacing(8)
        fill_hint = QLabel("Type your answer below:")
        fill_hint.setStyleSheet("color: #666; font-size: 12px;")
        fill_layout.addWidget(fill_hint)
        self.fill_input = QLineEdit()
        self.fill_input.setPlaceholderText("Enter your answer here...")
        self.fill_input.setMinimumHeight(44)
        self.fill_input.setFont(QFont("Segoe UI", 14))
        fill_layout.addWidget(self.fill_input)
        self.fill_frame.hide()
        self.card_layout.addWidget(self.fill_frame)

        scroll_inner.addWidget(self.question_card)
        scroll_inner.addStretch()
        scroll.setWidget(scroll_widget)
        right_side.addWidget(scroll)

        # Navigation buttons
        btn_layout = QHBoxLayout()
        self.quit_btn = QPushButton("Quit Quiz")
        self.quit_btn.setObjectName("danger")
        self.quit_btn.clicked.connect(self._quit_quiz)

        self.prev_btn = QPushButton("← Previous")
        self.prev_btn.setObjectName("secondary")
        self.prev_btn.setMinimumHeight(44)
        self.prev_btn.clicked.connect(self._prev_question)
        self.prev_btn.hide()

        self.next_btn = QPushButton("Next →")
        self.next_btn.setObjectName("primary")
        self.next_btn.setMinimumHeight(44)
        self.next_btn.clicked.connect(self._next_question)
        self.next_btn.hide()

        btn_layout.addWidget(self.quit_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.prev_btn)
        btn_layout.addWidget(self.next_btn)
        right_side.addLayout(btn_layout)

        content_layout.addLayout(right_side)
        layout.addLayout(content_layout)

    def _build_nav_buttons(self):
        while self.nav_grid.count():
            child = self.nav_grid.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.nav_buttons = []

        for i in range(len(self.questions)):
            btn = QPushButton(str(i + 1))
            btn.setFixedSize(38, 38)
            btn.setFont(QFont("Segoe UI", 11, QFont.Bold))
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, idx=i: self._jump_to_question(idx))
            self.nav_buttons.append(btn)
            self.nav_grid.addWidget(btn, i // 4, i % 4)

        self._update_nav_colors()

    def _update_nav_colors(self):
        for i, btn in enumerate(self.nav_buttons):
            if i == self.current_q:
                btn.setStyleSheet(
                    "QPushButton { background-color: #1a73e8; color: white; border: 2px solid #1557b0; border-radius: 6px; }"
                )
            elif i in self.user_answers:
                btn.setStyleSheet(
                    "QPushButton { background-color: #2e7d32; color: white; border: 2px solid #1b5e20; border-radius: 6px; }"
                )
            else:
                btn.setStyleSheet(
                    "QPushButton { background-color: #ffcdd2; color: #c62828; border: 2px solid #ef9a9a; border-radius: 6px; }"
                )

    def _jump_to_question(self, idx):
        self._save_current_answer()
        self._show_question(idx)

    def _load_quiz(self):
        QTimer.singleShot(100, self._generate_questions)

    def _generate_questions(self):
        self.questions = generate_quiz_with_ai(self.topic, self.level, 10)
        self.progress_bar.setMaximum(len(self.questions))
        self.remaining_time = get_quiz_timer(self.level, self.questions)
        self.timer.start(1000)
        self.loading_label.hide()
        self.question_label.show()
        self.type_badge.show()
        self.next_btn.show()
        self._build_nav_buttons()
        self.nav_panel.show()
        self._show_question(0)

    def _tick(self):
        self.remaining_time -= 1
        mins = self.remaining_time // 60
        secs = self.remaining_time % 60
        self.timer_label.setText(f"⏱ {mins:02d}:{secs:02d}")
        if self.remaining_time <= 30:
            self.timer_label.setStyleSheet("color: #d32f2f; font-weight: bold;")
        elif self.remaining_time <= 60:
            self.timer_label.setStyleSheet("color: #e65100; font-weight: bold;")
        else:
            self.timer_label.setStyleSheet("color: #2e7d32; font-weight: bold;")
        if self.remaining_time <= 0:
            self.timer.stop()
            self._finish_quiz()

    def _show_question(self, idx):
        if idx >= len(self.questions):
            self._try_submit()
            return
        self.current_q = idx
        q = self.questions[idx]
        qtype = q.get("type", "mcq")

        type_labels = {
            "mcq": ("📋 Choose the Best Answer", "#1a73e8", "#e8f0fe"),
            "fill": ("✏️ Fill in the Blank", "#e65100", "#fff3e0"),
        }
        label_text, color, bg = type_labels.get(qtype, type_labels["mcq"])
        self.type_badge.setText(f"  {label_text}  ")
        self.type_badge.setStyleSheet(
            f"color: {color}; background-color: {bg}; padding: 6px 14px; "
            f"border-radius: 12px; font-size: 12px; font-weight: bold;"
        )
        self.question_label.setText(f"Q{idx + 1}. {q['question']}")
        self.progress_label.setText(f"Question {idx + 1}/{len(self.questions)}")
        self.progress_bar.setValue(idx)

        self.mcq_frame.hide()
        self.fill_frame.hide()

        if qtype == "mcq":
            self._setup_mcq(q, idx)
        elif qtype == "fill":
            self._setup_fill(q, idx)

        self.prev_btn.setVisible(idx > 0)
        self.next_btn.setText("Next →" if idx < len(self.questions) - 1 else "Submit ✓")
        self._update_nav_colors()

    def _setup_mcq(self, q, idx):
        self.option_group.setExclusive(False)
        for btn in self.option_buttons:
            btn.setChecked(False)
        self.option_group.setExclusive(True)
        for i, btn in enumerate(self.option_buttons):
            btn.setText(f"  {q['options'][i]}")
        prev = self.user_answers.get(idx)
        if prev and prev.get("type") == "mcq":
            sel_text = prev["selected"]
            for i, opt in enumerate(q["options"]):
                if opt == sel_text:
                    self.option_buttons[i].setChecked(True)
                    break
        self.mcq_frame.show()

    def _setup_fill(self, q, idx):
        prev = self.user_answers.get(idx)
        self.fill_input.setText(prev["selected"] if prev and prev.get("type") == "fill" else "")
        self.fill_frame.show()

    def _save_current_answer(self):
        q = self.questions[self.current_q]
        qtype = q.get("type", "mcq")
        idx = self.current_q

        if qtype == "mcq":
            selected = self.option_group.checkedId()
            if selected != -1:
                self.user_answers[idx] = {
                    "type": "mcq",
                    "selected": q["options"][selected],
                    "correct": q["options"][q["answer"]],
                }
            else:
                self.user_answers.pop(idx, None)
        elif qtype == "fill":
            text = self.fill_input.text().strip()
            if text:
                self.user_answers[idx] = {
                    "type": "fill",
                    "selected": text,
                    "correct": q.get("correct_text", ""),
                }
            else:
                self.user_answers.pop(idx, None)

    def _prev_question(self):
        self._save_current_answer()
        if self.current_q > 0:
            self._show_question(self.current_q - 1)

    def _next_question(self):
        self._save_current_answer()
        if self.current_q < len(self.questions) - 1:
            self._show_question(self.current_q + 1)
        else:
            self._try_submit()

    def _try_submit(self):
        self._save_current_answer()
        unanswered = [i for i in range(len(self.questions)) if i not in self.user_answers]
        if unanswered and self.remaining_time > 0:
            q_nums = ", ".join(str(i + 1) for i in unanswered)
            QMessageBox.warning(
                self, "Unanswered Questions",
                f"You have not answered question(s): {q_nums}.\n\n"
                "Please go back and answer all questions before submitting.",
                QMessageBox.Ok,
            )
            self._show_question(unanswered[0])
            return
        self._finish_quiz()

    def _finish_quiz(self):
        self.timer.stop()
        self.score = 0
        for idx in range(len(self.questions)):
            ans = self.user_answers.get(idx)
            if not ans:
                continue
            if ans["type"] == "mcq":
                if ans["selected"] == ans["correct"]:
                    self.score += 1
            elif ans["type"] == "fill":
                if ans["selected"].lower() == ans["correct"].lower():
                    self.score += 1

        total = len(self.questions)
        passed = self.score >= (total * PASS_PERCENTAGE / 100)
        db.save_quiz_attempt(self.user["id"], self.topic, self.level, self.score, total, int(passed))
        if passed:
            db.validate_skill_level(self.user["id"], self.topic, self.level)
        self.on_quiz_complete(self.topic, self.level, self.score, total, passed)

    def _quit_quiz(self):
        self.timer.stop()
        reply = QMessageBox.question(self, "Quit Quiz",
                                     "Are you sure you want to quit? Progress will be lost.",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.on_quiz_complete(self.topic, self.level, 0, 0, False)
        else:
            self.timer.start(1000)


# ═══════════════════════════════════════════════════════════════════
#  SCORE GAUGE WIDGET
# ═══════════════════════════════════════════════════════════════════
class ScoreGauge(QWidget):
    """A circular gauge that visually displays the quiz score percentage."""
    def __init__(self, score, total, passed, parent=None):
        super().__init__(parent)
        self.score = score
        self.total = total
        self.passed = passed
        self.percentage = int(score / total * 100) if total > 0 else 0
        self.setFixedSize(200, 200)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        size = min(self.width(), self.height())
        margin = 16
        rect = QRectF(margin, margin, size - 2 * margin, size - 2 * margin)

        # Background circle (track)
        track_pen = QPen(QColor("#e0e0e0"), 14)
        track_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(track_pen)
        painter.drawArc(rect, 0, 360 * 16)

        # Foreground arc (score)
        if self.passed:
            arc_color = QColor("#2e7d32")
        elif self.percentage >= 50:
            arc_color = QColor("#e65100")
        else:
            arc_color = QColor("#d32f2f")

        arc_pen = QPen(arc_color, 14)
        arc_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(arc_pen)
        span = int(self.percentage / 100 * 360 * 16)
        painter.drawArc(rect, 90 * 16, -span)

        # Center text — percentage
        painter.setPen(QPen(arc_color))
        painter.setFont(QFont("Segoe UI", 28, QFont.Bold))
        painter.drawText(rect, Qt.AlignCenter, f"{self.percentage}%")

        painter.end()


# ═══════════════════════════════════════════════════════════════════
#  QUIZ RESULT SCREEN
# ═══════════════════════════════════════════════════════════════════
class QuizResultScreen(QWidget):
    def __init__(self, user, topic, level, score, total, passed, navigate_to, start_quiz_fn=None):
        super().__init__()
        self.user = user
        self.topic = topic
        self.level = level
        self.navigate_to = navigate_to
        self.start_quiz_fn = start_quiz_fn
        self._build_ui(topic, level, score, total, passed)

    def _build_ui(self, topic, level, score, total, passed):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(16)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(30, 30, 30, 30)
        card_layout.setSpacing(12)

        if total == 0:
            result_text = "Quiz Abandoned"
            result_icon = "🚫"
            color = "#666"
        elif passed:
            result_text = "Congratulations! You Passed! 🎉"
            result_icon = "✅"
            color = "#2e7d32"
        else:
            result_text = "Not quite there yet. Keep practicing!"
            result_icon = "❌"
            color = "#d32f2f"

        result_label = QLabel(f"{result_icon} {result_text}")
        result_label.setFont(QFont("Segoe UI", 20, QFont.Bold))
        result_label.setAlignment(Qt.AlignCenter)
        result_label.setStyleSheet(f"color: {color};")

        level_name = db.SKILL_LEVELS.get(level, "")
        info = QLabel(f"{topic} – {level_name} Level")
        info.setObjectName("subtitle")
        info.setAlignment(Qt.AlignCenter)

        card_layout.addWidget(result_label)
        card_layout.addWidget(info)
        card_layout.addSpacing(10)

        # Graphical score display
        if total > 0:
            gauge_row = QHBoxLayout()
            gauge_row.setAlignment(Qt.AlignCenter)
            gauge_row.setSpacing(40)

            # Circular score gauge
            gauge = ScoreGauge(score, total, passed)
            gauge_row.addWidget(gauge)

            # Stats column beside the gauge
            stats_col = QVBoxLayout()
            stats_col.setSpacing(10)

            correct_label = QLabel(f"✅ Correct:  {score}")
            correct_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
            correct_label.setStyleSheet("color: #2e7d32;")

            wrong_label = QLabel(f"❌ Wrong:  {total - score}")
            wrong_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
            wrong_label.setStyleSheet("color: #d32f2f;")

            total_label = QLabel(f"📋 Total:  {total}")
            total_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
            total_label.setStyleSheet("color: #333;")

            threshold_label = QLabel(f"🎯 Pass threshold:  {PASS_PERCENTAGE}%")
            threshold_label.setFont(QFont("Segoe UI", 12))
            threshold_label.setStyleSheet("color: #666;")

            stats_col.addStretch()
            stats_col.addWidget(correct_label)
            stats_col.addWidget(wrong_label)
            stats_col.addWidget(total_label)
            stats_col.addSpacing(6)
            stats_col.addWidget(threshold_label)
            stats_col.addStretch()

            gauge_row.addLayout(stats_col)
            card_layout.addLayout(gauge_row)
            card_layout.addSpacing(10)

            # Horizontal bar showing correct vs wrong
            bar_frame = QFrame()
            bar_frame.setFixedHeight(28)
            bar_frame.setStyleSheet("background-color: #e0e0e0; border-radius: 14px;")
            bar_layout = QHBoxLayout(bar_frame)
            bar_layout.setContentsMargins(0, 0, 0, 0)
            bar_layout.setSpacing(0)

            if score > 0:
                correct_bar = QFrame()
                correct_bar.setStyleSheet("background-color: #2e7d32; border-radius: 14px;")
                bar_layout.addWidget(correct_bar, score)
            if total - score > 0:
                wrong_bar = QFrame()
                wrong_bar.setStyleSheet("background-color: #d32f2f; border-radius: 14px;")
                bar_layout.addWidget(wrong_bar, total - score)

            card_layout.addWidget(bar_frame)
        else:
            no_score = QLabel("No score recorded")
            no_score.setFont(QFont("Segoe UI", 16))
            no_score.setAlignment(Qt.AlignCenter)
            card_layout.addWidget(no_score)

        if passed:
            next_level = level + 1
            if next_level <= 4:
                next_name = db.SKILL_LEVELS.get(next_level, "")
                unlock_label = QLabel(f"🔓 {next_name} level is now unlocked!")
                unlock_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
                unlock_label.setStyleSheet("color: #1a73e8;")
                unlock_label.setAlignment(Qt.AlignCenter)
                card_layout.addWidget(unlock_label)
            else:
                mastery = QLabel("🏆 You have mastered this topic!")
                mastery.setFont(QFont("Segoe UI", 14, QFont.Bold))
                mastery.setStyleSheet("color: #f9a825;")
                mastery.setAlignment(Qt.AlignCenter)
                card_layout.addWidget(mastery)

            profile_note = QLabel("✅ Your profile has been updated with the validated level.")
            profile_note.setStyleSheet("color: #2e7d32; font-size: 12px;")
            profile_note.setAlignment(Qt.AlignCenter)
            card_layout.addWidget(profile_note)

        layout.addWidget(card)
        layout.addStretch()

        # Buttons
        btn_layout = QHBoxLayout()
        dashboard_btn = QPushButton("🏠 Dashboard")
        dashboard_btn.setObjectName("secondary")
        dashboard_btn.clicked.connect(lambda: self.navigate_to("dashboard"))

        topics_btn = QPushButton("📚 Browse Topics")
        topics_btn.setObjectName("primary")
        topics_btn.clicked.connect(lambda: self.navigate_to("topics"))

        btn_layout.addWidget(dashboard_btn)

        if not passed and total > 0 and self.start_quiz_fn:
            reattempt_btn = QPushButton("🔄 Re-attempt Quiz")
            reattempt_btn.setObjectName("success_btn")
            reattempt_btn.setMinimumHeight(44)
            reattempt_btn.clicked.connect(lambda: self.start_quiz_fn(self.topic, self.level))
            btn_layout.addWidget(reattempt_btn)

        btn_layout.addWidget(topics_btn)
        layout.addLayout(btn_layout)


# ═══════════════════════════════════════════════════════════════════
#  PROFILE SCREEN
# ═══════════════════════════════════════════════════════════════════
class ProfileScreen(QWidget):
    def __init__(self, user, navigate_to):
        super().__init__()
        self.user = user
        self.navigate_to = navigate_to
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(16)

        title = QLabel(f"👤 {self.user['full_name']}'s Profile")
        title.setObjectName("title")
        layout.addWidget(title)

        # Tabs: Profile Info | Skills | Quiz History
        tabs = QTabWidget()

        # ── Tab 1: Profile info ──
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(20, 20, 20, 20)
        info_layout.setSpacing(12)

        form = QFormLayout()
        self.name_input = QLineEdit(self.user["full_name"])
        self.email_input = QLineEdit(self.user.get("email", ""))
        self.nt_id_input = QLineEdit(self.user.get("nt_id", ""))
        self.department_input = QLineEdit(self.user.get("department", ""))
        self.team_input = QLineEdit(self.user.get("team", ""))
        self.experience_input = QLineEdit(str(self.user.get("years_of_experience", 0)))
        self.pw_input = QLineEdit()
        self.pw_input.setPlaceholderText("Leave blank to keep current")
        self.pw_input.setEchoMode(QLineEdit.Password)

        form.addRow("Full Name:", self.name_input)
        form.addRow("Email:", self.email_input)
        form.addRow("NT ID:", self.nt_id_input)
        form.addRow("Department:", self.department_input)
        form.addRow("Team:", self.team_input)
        form.addRow("Years of Experience:", self.experience_input)
        form.addRow("New Password:", self.pw_input)
        info_layout.addLayout(form)

        save_btn = QPushButton("Save Changes")
        save_btn.setObjectName("primary")
        save_btn.clicked.connect(self._save_profile)
        info_layout.addWidget(save_btn)

        self.profile_msg = QLabel("")
        self.profile_msg.setAlignment(Qt.AlignCenter)
        self.profile_msg.hide()
        info_layout.addWidget(self.profile_msg)
        info_layout.addStretch()

        tabs.addTab(info_widget, "📋 Profile Info")

        # ── Tab 2: Skills ──
        skills_widget = QWidget()
        self.skills_layout = QVBoxLayout(skills_widget)
        self.skills_layout.setContentsMargins(20, 20, 20, 20)
        self.skills_layout.setSpacing(10)
        tabs.addTab(skills_widget, "🎯 Skills")

        # ── Tab 3: Quiz History ──
        history_widget = QWidget()
        self.history_layout = QVBoxLayout(history_widget)
        self.history_layout.setContentsMargins(20, 20, 20, 20)
        tabs.addTab(history_widget, "📊 Quiz History")

        layout.addWidget(tabs)
        self._refresh_skills()
        self._refresh_history()

    def _save_profile(self):
        name = self.name_input.text().strip()
        email = self.email_input.text().strip()
        nt_id = self.nt_id_input.text().strip()
        department = self.department_input.text().strip()
        team = self.team_input.text().strip()
        pw = self.pw_input.text().strip()

        try:
            years_exp = int(self.experience_input.text().strip())
        except ValueError:
            years_exp = 0

        if not name:
            self.profile_msg.setStyleSheet("color: #d32f2f;")
            self.profile_msg.setText("Name cannot be empty.")
            self.profile_msg.show()
            return

        db.update_user_profile(self.user["id"], name, email, nt_id, department, team, years_exp)
        self.user["full_name"] = name
        self.user["email"] = email
        self.user["nt_id"] = nt_id
        self.user["department"] = department
        self.user["team"] = team
        self.user["years_of_experience"] = years_exp

        if pw:
            if len(pw) < 4:
                self.profile_msg.setStyleSheet("color: #d32f2f;")
                self.profile_msg.setText("Password must be at least 4 characters.")
                self.profile_msg.show()
                return
            db.change_password(self.user["id"], pw)

        self.profile_msg.setStyleSheet("color: #2e7d32;")
        self.profile_msg.setText("✓ Profile updated successfully!")
        self.profile_msg.show()
        self.pw_input.clear()

    def _refresh_skills(self):
        while self.skills_layout.count():
            child = self.skills_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        skills = db.get_user_skills(self.user["id"])
        if not skills:
            no = QLabel("No skills added yet. Go to Topics and rate yourself!")
            no.setObjectName("subtitle")
            self.skills_layout.addWidget(no)
            return

        for skill in skills:
            card = QFrame()
            card.setObjectName("card")
            card_layout = QHBoxLayout(card)
            card_layout.setContentsMargins(16, 14, 16, 14)

            topic_label = QLabel(f"  {skill['topic']}")
            topic_label.setFont(QFont("Segoe UI", 14, QFont.Bold))

            self_level = skill["self_rated_level"]
            validated = skill["validated_level"]
            self_name = db.SKILL_LEVELS.get(self_level, "N/A")
            val_name = db.SKILL_LEVELS.get(validated, "None")

            rating_label = QLabel(f"Self-rated: {self_name}")
            rating_label.setStyleSheet("color: #555; font-size: 13px;")

            # Level badges
            badges = QHBoxLayout()
            for lv in range(1, 5):
                lv_name = db.SKILL_LEVELS[lv]
                badge = QLabel(f" {lv_name} ")
                if lv <= validated:
                    badge.setStyleSheet(
                        "background-color: #2e7d32; color: white; padding: 4px 10px; "
                        "border-radius: 10px; font-size: 11px; font-weight: bold;"
                    )
                    badge.setText(f"✅ {lv_name}")
                elif lv == validated + 1:
                    badge.setStyleSheet(
                        "background-color: #e8f0fe; color: #1a73e8; padding: 4px 10px; "
                        "border-radius: 10px; font-size: 11px; border: 1px solid #1a73e8;"
                    )
                    badge.setText(f"🔓 {lv_name}")
                else:
                    badge.setStyleSheet(
                        "background-color: #f0f0f0; color: #999; padding: 4px 10px; "
                        "border-radius: 10px; font-size: 11px;"
                    )
                    badge.setText(f"🔒 {lv_name}")
                badges.addWidget(badge)

            card_layout.addWidget(topic_label)
            card_layout.addWidget(rating_label)
            card_layout.addStretch()
            card_layout.addLayout(badges)
            self.skills_layout.addWidget(card)

        self.skills_layout.addStretch()

    def _refresh_history(self):
        while self.history_layout.count():
            child = self.history_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        history = db.get_quiz_history(self.user["id"])
        if not history:
            no = QLabel("No quiz attempts yet.")
            no.setObjectName("subtitle")
            self.history_layout.addWidget(no)
            return

        table = QTableWidget()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels(["Date", "Topic", "Level", "Score", "Result", "Pass %"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setRowCount(len(history))
        table.setEditTriggers(QTableWidget.NoEditTriggers)

        for i, h in enumerate(history):
            table.setItem(i, 0, QTableWidgetItem(h["attempted_at"]))
            table.setItem(i, 1, QTableWidgetItem(h["topic"]))
            table.setItem(i, 2, QTableWidgetItem(db.SKILL_LEVELS.get(h["level"], str(h["level"]))))
            table.setItem(i, 3, QTableWidgetItem(f"{h['score']}/{h['total_questions']}"))

            result = "✅ Pass" if h["passed"] else "❌ Fail"
            result_item = QTableWidgetItem(result)
            result_item.setForeground(QColor("#2e7d32" if h["passed"] else "#d32f2f"))
            table.setItem(i, 4, result_item)

            pct = int(h["score"] / h["total_questions"] * 100) if h["total_questions"] > 0 else 0
            table.setItem(i, 5, QTableWidgetItem(f"{pct}%"))

        self.history_layout.addWidget(table)

    def refresh(self):
        self._refresh_skills()
        self._refresh_history()


# ═══════════════════════════════════════════════════════════════════
#  ADMIN PANEL
# ═══════════════════════════════════════════════════════════════════
class AdminPanel(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(16)

        title = QLabel("⚙️ Admin Panel")
        title.setObjectName("title")
        layout.addWidget(title)

        tabs = QTabWidget()

        # ── Tab 1: User Management ──
        user_widget = QWidget()
        user_layout = QVBoxLayout(user_widget)
        user_layout.setContentsMargins(20, 20, 20, 20)

        btn_bar = QHBoxLayout()
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setObjectName("secondary")
        refresh_btn.clicked.connect(self._refresh_users)
        btn_bar.addWidget(refresh_btn)
        btn_bar.addStretch()
        user_layout.addLayout(btn_bar)

        self.user_table = QTableWidget()
        self.user_table.setColumnCount(6)
        self.user_table.setHorizontalHeaderLabels(["ID", "Username", "Full Name", "Email", "Admin", "Actions"])
        self.user_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.user_table.setEditTriggers(QTableWidget.NoEditTriggers)
        user_layout.addWidget(self.user_table)

        tabs.addTab(user_widget, "👥 Users")

        # ── Tab 2: AI Settings ──
        ai_widget = QWidget()
        ai_layout = QVBoxLayout(ai_widget)
        ai_layout.setContentsMargins(20, 20, 20, 20)
        ai_layout.setSpacing(12)

        ai_title = QLabel("🤖 AI Quiz Generation Settings")
        ai_title.setObjectName("section_title")
        ai_layout.addWidget(ai_title)

        status = "✅ Available" if GENAI_AVAILABLE else "❌ Not installed (pip install google-generativeai)"
        status_label = QLabel(f"Google Gemini SDK: {status}")
        status_label.setStyleSheet("font-size: 13px;")
        ai_layout.addWidget(status_label)

        ai_layout.addSpacing(10)
        key_label = QLabel("API Key:")
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("Enter your Google Gemini API key")
        self.api_key_input.setEchoMode(QLineEdit.Password)

        save_key_btn = QPushButton("Save & Configure")
        save_key_btn.setObjectName("primary")
        save_key_btn.clicked.connect(self._save_api_key)

        self.ai_msg = QLabel("")
        self.ai_msg.setAlignment(Qt.AlignCenter)
        self.ai_msg.hide()

        ai_layout.addWidget(key_label)
        ai_layout.addWidget(self.api_key_input)
        ai_layout.addWidget(save_key_btn)
        ai_layout.addWidget(self.ai_msg)

        info = QLabel(
            "ℹ️ Without a Gemini API key, the platform uses a built-in question bank.\n"
            "With an API key, quiz questions are generated dynamically by AI for each attempt."
        )
        info.setObjectName("subtitle")
        info.setWordWrap(True)
        ai_layout.addWidget(info)
        ai_layout.addStretch()

        tabs.addTab(ai_widget, "🤖 AI Settings")

        # ── Tab 3: Platform Stats ──
        stats_widget = QWidget()
        self.stats_layout = QVBoxLayout(stats_widget)
        self.stats_layout.setContentsMargins(20, 20, 20, 20)
        tabs.addTab(stats_widget, "📊 Statistics")

        layout.addWidget(tabs)
        self._refresh_users()
        self._refresh_stats()

    def _refresh_users(self):
        users = db.get_all_users()
        self.user_table.setRowCount(len(users))

        for i, u in enumerate(users):
            self.user_table.setItem(i, 0, QTableWidgetItem(str(u["id"])))
            self.user_table.setItem(i, 1, QTableWidgetItem(u["username"]))
            self.user_table.setItem(i, 2, QTableWidgetItem(u["full_name"]))
            self.user_table.setItem(i, 3, QTableWidgetItem(u.get("email", "")))

            admin_text = "✅ Admin" if u["is_admin"] else "User"
            admin_item = QTableWidgetItem(admin_text)
            self.user_table.setItem(i, 4, admin_item)

            # Action buttons
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(4, 4, 4, 4)
            actions_layout.setSpacing(4)

            if u["id"] != self.user["id"]:  # Can't modify yourself
                toggle_btn = QPushButton("Toggle Admin")
                toggle_btn.setObjectName("secondary")
                toggle_btn.setFixedHeight(30)
                toggle_btn.clicked.connect(lambda checked, uid=u["id"], is_admin=u["is_admin"]:
                                           self._toggle_admin(uid, is_admin))

                del_btn = QPushButton("Delete")
                del_btn.setObjectName("danger")
                del_btn.setFixedHeight(30)
                del_btn.clicked.connect(lambda checked, uid=u["id"], uname=u["username"]:
                                        self._delete_user(uid, uname))

                actions_layout.addWidget(toggle_btn)
                actions_layout.addWidget(del_btn)

            self.user_table.setCellWidget(i, 5, actions_widget)

    def _toggle_admin(self, user_id, current_is_admin):
        db.toggle_admin(user_id, 0 if current_is_admin else 1)
        self._refresh_users()

    def _delete_user(self, user_id, username):
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete user '{username}'?\nThis will remove all their data.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            db.delete_user(user_id)
            self._refresh_users()

    def _save_api_key(self):
        key = self.api_key_input.text().strip()
        if not key:
            self.ai_msg.setStyleSheet("color: #d32f2f;")
            self.ai_msg.setText("Please enter an API key.")
            self.ai_msg.show()
            return

        if configure_gemini(key):
            self.ai_msg.setStyleSheet("color: #2e7d32;")
            self.ai_msg.setText("✓ API key configured successfully!")
        else:
            self.ai_msg.setStyleSheet("color: #d32f2f;")
            self.ai_msg.setText("Failed. Install: pip install google-generativeai")
        self.ai_msg.show()

    def _refresh_stats(self):
        while self.stats_layout.count():
            child = self.stats_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        users = db.get_all_users()
        total_users = len(users)
        admin_count = sum(1 for u in users if u["is_admin"])

        stats_grid = QGridLayout()
        stats_data = [
            ("👥 Total Users", str(total_users)),
            ("🛡️ Admins", str(admin_count)),
            ("📚 Topics Available", str(len(db.TOPICS))),
        ]

        for i, (label, value) in enumerate(stats_data):
            card = QFrame()
            card.setObjectName("card")
            card.setMinimumHeight(100)
            cl = QVBoxLayout(card)
            cl.setAlignment(Qt.AlignCenter)

            v = QLabel(value)
            v.setFont(QFont("Segoe UI", 28, QFont.Bold))
            v.setStyleSheet("color: #1a73e8;")
            v.setAlignment(Qt.AlignCenter)

            l = QLabel(label)
            l.setAlignment(Qt.AlignCenter)
            l.setStyleSheet("font-size: 13px; color: #666;")

            cl.addWidget(v)
            cl.addWidget(l)
            stats_grid.addWidget(card, 0, i)

        self.stats_layout.addLayout(stats_grid)
        self.stats_layout.addStretch()

    def refresh(self):
        self._refresh_users()
        self._refresh_stats()


# ═══════════════════════════════════════════════════════════════════
#  MAIN WINDOW – Navigation Shell
# ═══════════════════════════════════════════════════════════════════
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🎓 AI Learning Platform")
        self.setMinimumSize(1100, 750)
        self.user = None
        self.current_page = None

        # Central widget
        self.central = QWidget()
        self.setCentralWidget(self.central)
        self.outer_layout = QVBoxLayout(self.central)
        self.outer_layout.setContentsMargins(0, 0, 0, 0)
        self.outer_layout.setSpacing(0)

        # Header bar
        self.header_frame = QFrame()
        self.header_frame.setObjectName("app_header")
        self.header_frame.setFixedHeight(60)
        self.header_layout = QHBoxLayout(self.header_frame)
        self.header_layout.setContentsMargins(20, 8, 20, 8)

        header_title = QLabel("🎓 AI Learning Platform")
        header_title.setStyleSheet("color: white; font-size: 18px; font-weight: bold; background: transparent;")
        header_title.setCursor(Qt.PointingHandCursor)
        header_title.mousePressEvent = lambda e: self._navigate_to("dashboard") if self.user else None
        self.header_layout.addWidget(header_title)

        # Navigation buttons (hidden until login)
        self.nav_widget = QWidget()
        self.nav_widget.setStyleSheet("background: transparent;")
        self.nav_hlayout = QHBoxLayout(self.nav_widget)
        self.nav_hlayout.setContentsMargins(0, 0, 0, 0)
        self.nav_hlayout.setSpacing(4)
        self.nav_widget.hide()
        self.header_layout.addWidget(self.nav_widget)

        self.header_layout.addStretch()

        # Bosch logo on the right
        logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "image", "bosch_logo.png")
        logo_label = QLabel()
        logo_label.setStyleSheet("background: transparent;")
        logo_label.setAttribute(Qt.WA_TranslucentBackground)
        logo_pixmap = QPixmap(logo_path)
        if not logo_pixmap.isNull():
            logo_label.setPixmap(logo_pixmap.scaled(120, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.header_layout.addWidget(logo_label)

        self.outer_layout.addWidget(self.header_frame)

        # Content area (full width, no sidebar)
        self.stack = QStackedWidget()
        self.outer_layout.addWidget(self.stack)

        # Login screen
        self.login_screen = LoginScreen(self._on_login)
        self.stack.addWidget(self.login_screen)
        self.stack.setCurrentWidget(self.login_screen)

    def _on_login(self, user):
        self.user = user
        self._build_nav_bar()
        self.nav_widget.show()
        self._navigate_to("dashboard")

    def _build_nav_bar(self):
        # Clear existing nav buttons
        while self.nav_hlayout.count():
            child = self.nav_hlayout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        self.nav_buttons = {}
        nav_items = [
            ("dashboard", "🏠 Home"),
            ("topics", "📚 Topics"),
            ("profile", "👤 Profile"),
        ]
        if self.user["is_admin"]:
            nav_items.append(("admin", "⚙️ Admin"))

        for key, text in nav_items:
            btn = QPushButton(text)
            btn.setObjectName("nav_btn")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, k=key: self._navigate_to(k))
            self.nav_buttons[key] = btn
            self.nav_hlayout.addWidget(btn)

        # Logout button
        logout_btn = QPushButton("🚪 Logout")
        logout_btn.setObjectName("nav_logout_btn")
        logout_btn.setCursor(Qt.PointingHandCursor)
        logout_btn.clicked.connect(self._logout)
        self.nav_hlayout.addWidget(logout_btn)

    def _navigate_to(self, page_name):
        self.current_page = page_name

        # Update nav button styles
        for key, btn in self.nav_buttons.items():
            if key == page_name:
                btn.setObjectName("nav_btn_active")
            else:
                btn.setObjectName("nav_btn")
            btn.setStyle(btn.style())

        # Remove current content pages (keep login at index 0)
        while self.stack.count() > 1:
            w = self.stack.widget(1)
            self.stack.removeWidget(w)
            w.deleteLater()

        if page_name == "dashboard":
            screen = DashboardScreen(self.user, self._navigate_to)
        elif page_name == "topics":
            screen = TopicSelectionScreen(self.user, self._on_topic_selected)
        elif page_name == "profile":
            screen = ProfileScreen(self.user, self._navigate_to)
        elif page_name == "admin":
            if not self.user["is_admin"]:
                QMessageBox.warning(self, "Access Denied", "Admin access only.")
                return
            screen = AdminPanel(self.user)
        else:
            return

        self.stack.addWidget(screen)
        self.stack.setCurrentWidget(screen)

    def _on_topic_selected(self, topic):
        dlg = SkillRatingDialog(self.user, topic, self._start_quiz, self)
        dlg.exec_()

    def _start_quiz(self, topic, level):
        while self.stack.count() > 1:
            w = self.stack.widget(1)
            self.stack.removeWidget(w)
            w.deleteLater()

        screen = QuizScreen(self.user, topic, level, self._on_quiz_complete)
        self.stack.addWidget(screen)
        self.stack.setCurrentWidget(screen)

    def _on_quiz_complete(self, topic, level, score, total, passed):
        while self.stack.count() > 1:
            w = self.stack.widget(1)
            self.stack.removeWidget(w)
            w.deleteLater()

        screen = QuizResultScreen(self.user, topic, level, score, total, passed, self._navigate_to, self._start_quiz)
        self.stack.addWidget(screen)
        self.stack.setCurrentWidget(screen)

    def _logout(self):
        self.user = None
        self.nav_widget.hide()
        while self.stack.count() > 1:
            w = self.stack.widget(1)
            self.stack.removeWidget(w)
            w.deleteLater()
        self.stack.setCurrentWidget(self.login_screen)


# ═══════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════════
def main():
    db.init_db()
    app = QApplication(sys.argv)
    app.setStyleSheet(MAIN_STYLE)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
