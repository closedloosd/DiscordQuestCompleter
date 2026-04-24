import asyncio
import json
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QScrollArea, QFrame,
    QMessageBox, QSizePolicy, QSpacerItem, QGraphicsOpacityEffect
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QRect, QTimer
from PyQt6.QtGui import QPixmap, QPainter, QBrush, QWheelEvent, QCursor
from qasync import asyncSlot

from core.discord_api import DiscordAPI
from core.quest_worker import QuestWorker
from ui.quest_card import QuestCard, _ImageLoader


class SmoothScrollArea(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._anim = QPropertyAnimation(self.verticalScrollBar(), b"value", self)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.setDuration(300)

    def wheelEvent(self, event: QWheelEvent):
        delta = -event.angleDelta().y()
        current = self.verticalScrollBar().value()
        target = max(self.verticalScrollBar().minimum(),
                     min(int(current + delta * 0.8), self.verticalScrollBar().maximum()))
        if self._anim.state() == QPropertyAnimation.State.Running:
            self._anim.stop()
        self._anim.setStartValue(self.verticalScrollBar().value())
        self._anim.setEndValue(target)
        self._anim.start()


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Discord Quest Completer")
        self.setMinimumSize(560, 650)
        self.resize(600, 750)
        self._load_styles()
        self._save_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "session.json")
        self._api: DiscordAPI | None = None
        self._worker: QuestWorker | None = None
        self._cards: dict[str, QuestCard] = {}
        self._build_login_page()
        self._animate_page(self)
        self._try_autologin()

    def _animate_page(self, widget: QWidget, duration: int = 350):
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity", widget)
        anim.setDuration(duration)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.finished.connect(lambda: widget.setGraphicsEffect(None))
        anim.start()
        widget._fade_anim = anim

    def _animate_card(self, card: QWidget, delay: int = 0):
        effect = QGraphicsOpacityEffect(card)
        card.setGraphicsEffect(effect)
        effect.setOpacity(0.0)
        def start():
            anim = QPropertyAnimation(effect, b"opacity", card)
            anim.setDuration(400)
            anim.setStartValue(0.0)
            anim.setEndValue(1.0)
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            anim.finished.connect(lambda: card.setGraphicsEffect(None))
            anim.start()
            card._fade_anim = anim
        QTimer.singleShot(delay, start)

    def _try_autologin(self):
        if not os.path.exists(self._save_path):
            return
        try:
            with open(self._save_path, "r") as f:
                data = json.load(f)
            token = data.get("token", "")
            if token:
                self._token_input.setText(token)
                self._login_btn.click()
        except Exception:
            pass

    def _save_session(self, token: str):
        with open(self._save_path, "w") as f:
            json.dump({"token": token}, f)

    def _clear_session(self):
        if os.path.exists(self._save_path):
            os.remove(self._save_path)

    def _load_styles(self):
        qss_path = os.path.join(os.path.dirname(__file__), "styles.qss")
        with open(qss_path, "r", encoding="utf-8") as f:
            self.setStyleSheet(f.read())

    def _build_login_page(self):
        self._clear_layout()
        self._animate_page(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(60, 80, 60, 60)
        layout.setSpacing(10)

        title = QLabel("Quest Completer")
        title.setObjectName("titleLabel")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        layout.addWidget(title)

        sub = QLabel("Автоматическое выполнение квестов Discord")
        sub.setObjectName("subtitleLabel")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        layout.addWidget(sub)

        layout.addSpacerItem(QSpacerItem(0, 24, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))

        token_label = QLabel("Токен аккаунта Discord")
        token_label.setObjectName("subtitleLabel")
        token_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        layout.addWidget(token_label)

        self._token_input = QLineEdit()
        self._token_input.setPlaceholderText("Вставьте ваш токен...")
        self._token_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._token_input.returnPressed.connect(self._on_login)
        layout.addWidget(self._token_input)

        help_btn = QPushButton("Как получить токен?")
        help_btn.setObjectName("helpBtn")
        help_btn.clicked.connect(self._show_token_help)
        layout.addWidget(help_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        layout.addSpacerItem(QSpacerItem(0, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))

        self._login_btn = QPushButton("Войти")
        self._login_btn.clicked.connect(self._on_login)
        layout.addWidget(self._login_btn)
        layout.addStretch()

    def _build_quests_page(self, profile: dict, quests: list, orbs: int, history: list):
        self._clear_layout()
        self._animate_page(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        header = QFrame()
        header.setObjectName("questCard")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(14, 10, 14, 10)
        h_layout.setSpacing(12)

        avatar_label = QLabel()
        avatar_label.setFixedSize(44, 44)
        avatar_label.setStyleSheet("border-radius: 22px; background-color: #313338;")
        avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar_hash = profile.get("avatar")
        user_id = profile.get("id")
        if avatar_hash and user_id:
            loader = _ImageLoader(avatar_label)
            def on_avatar(data: bytes, lbl=avatar_label):
                if not data:
                    return
                pix = QPixmap()
                pix.loadFromData(data)
                if pix.isNull():
                    return
                rounded = QPixmap(44, 44)
                rounded.fill(Qt.GlobalColor.transparent)
                painter = QPainter(rounded)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                painter.setBrush(QBrush(pix.scaled(44, 44, Qt.AspectRatioMode.KeepAspectRatio,
                                                    Qt.TransformationMode.SmoothTransformation)))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(QRect(0, 0, 44, 44))
                painter.end()
                lbl.setPixmap(rounded)
            loader.loaded.connect(on_avatar)
            loader.load(f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_hash}.png?size=64")
            header._avatar_loader = loader
        h_layout.addWidget(avatar_label)

        info_col = QVBoxLayout()
        info_col.setSpacing(2)
        username = profile.get("global_name") or profile.get("username", "Неизвестно")
        discriminator = profile.get("discriminator", "0")
        tag = f"#{discriminator}" if discriminator != "0" else ""
        name_lbl = QLabel(f"{username}{tag}")
        name_lbl.setObjectName("profileName")
        info_col.addWidget(name_lbl)
        status_lbl = QLabel("Подключено")
        status_lbl.setObjectName("subtitleLabel")
        status_lbl.setStyleSheet("color: #248046;")
        info_col.addWidget(status_lbl)
        h_layout.addLayout(info_col)
        h_layout.addStretch()

        logout_btn = QPushButton("Выйти")
        logout_btn.setObjectName("stopBtn")
        logout_btn.setFixedWidth(80)
        logout_btn.clicked.connect(self._on_logout)
        h_layout.addWidget(logout_btn)
        layout.addWidget(header)

        layout.addWidget(self._build_stats(quests, orbs))

        self._tab_quests_btn = QPushButton("Задания")
        self._tab_history_btn = QPushButton("История")
        self._tab_quests_btn.setObjectName("tabBtnActive")
        self._tab_history_btn.setObjectName("tabBtn")
        self._tab_quests_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._tab_history_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        tab_bar = QHBoxLayout()
        tab_bar.setSpacing(6)
        tab_bar.addWidget(self._tab_quests_btn)
        tab_bar.addWidget(self._tab_history_btn)
        tab_bar.addStretch()
        run_all_btn = QPushButton("Выполнить все")
        run_all_btn.setObjectName("runBtn")
        run_all_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        run_all_btn.clicked.connect(self._run_all)
        tab_bar.addWidget(run_all_btn)
        layout.addLayout(tab_bar)

        from ui.history_page import HistoryPage
        history_orbs = sum(
            next((r.get("orb_quantity") or r.get("amount", 0)
                  for r in ((q.get("config") or {}).get("rewards_config") or {}).get("rewards", [])), 0)
            for q in history
        )

        self._quests_widget = self._build_quests_tab(quests)
        self._history_widget = HistoryPage(history, history_orbs)
        self._history_widget.setVisible(False)

        layout.addWidget(self._quests_widget)
        layout.addWidget(self._history_widget)

        self._tab_quests_btn.clicked.connect(lambda: self._switch_tab(0))
        self._tab_history_btn.clicked.connect(lambda: self._switch_tab(1))
        self._current_tab = 0
        QTimer.singleShot(0, lambda: self._apply_cursors(self))

        self._orbs_timer = QTimer(self)
        self._orbs_timer.setInterval(5000)
        self._orbs_timer.timeout.connect(self._refresh_orbs)
        self._orbs_timer.start()

    def _build_stats(self, quests: list, orbs: int) -> QFrame:
        frame = QFrame()
        frame.setObjectName("questCard")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(0)

        pending_orbs = 0
        for q in quests:
            rewards = ((q.get("config") or {}).get("rewards_config") or {}).get("rewards", [])
            pending_orbs += next((r.get("orb_quantity") or r.get("amount", 0) for r in rewards), 0)

        def stat_col(title: str, value: str, color: str = "#dcddde") -> QVBoxLayout:
            col = QVBoxLayout()
            col.setSpacing(2)
            t = QLabel(title)
            t.setObjectName("subtitleLabel")
            t.setAlignment(Qt.AlignmentFlag.AlignCenter)
            v = QLabel(value)
            v.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {color};")
            v.setAlignment(Qt.AlignmentFlag.AlignCenter)
            col.addWidget(t)
            col.addWidget(v)
            return col

        layout.addLayout(stat_col("Заданий доступно", str(len(quests)), "#5865f2"))
        self._add_divider(layout)
        self._orbs_val_label = QLabel(str(orbs) if orbs >= 0 else "—")
        self._orbs_val_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #faa61a;")
        self._orbs_val_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        orbs_col = QVBoxLayout()
        orbs_col.setSpacing(2)
        orbs_title = QLabel("Орбов на счету")
        orbs_title.setObjectName("subtitleLabel")
        orbs_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        orbs_col.addWidget(orbs_title)
        orbs_col.addWidget(self._orbs_val_label)
        layout.addLayout(orbs_col)
        self._add_divider(layout)
        layout.addLayout(stat_col("Получите за задания", str(pending_orbs), "#248046"))
        self._add_divider(layout)
        total = (orbs if orbs >= 0 else 0) + pending_orbs
        layout.addLayout(stat_col("Итого орбов", str(total) if orbs >= 0 else f"+{pending_orbs}", "#faa61a"))
        return frame

    def _add_divider(self, layout: QHBoxLayout):
        div = QFrame()
        div.setFixedWidth(1)
        div.setStyleSheet("background-color: #3d3f45;")
        layout.addWidget(div)

    def _build_quests_tab(self, quests: list) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(0)

        if not quests:
            empty = QLabel("Нет доступных заданий")
            empty.setObjectName("subtitleLabel")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(empty)
            layout.addStretch()
            return widget

        scroll = SmoothScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        cards_layout = QVBoxLayout(container)
        cards_layout.setContentsMargins(0, 0, 8, 0)
        cards_layout.setSpacing(10)

        self._cards = {}
        self._quests_cache = {}
        for i, quest in enumerate(quests):
            card = QuestCard(quest, self._run_quest, self._stop_quest)
            self._cards[quest["id"]] = card
            self._quests_cache[quest["id"]] = quest
            cards_layout.addWidget(card)
            self._animate_card(card, delay=i * 80)

        cards_layout.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll)
        return widget

    @asyncSlot()
    async def _refresh_orbs(self):
        if not self._api:
            return
        orbs = await self._api.get_orbs()
        if hasattr(self, "_orbs_val_label") and self._orbs_val_label:
            self._orbs_val_label.setText(str(orbs) if orbs >= 0 else "—")

    @asyncSlot()
    async def _on_login(self):
        token = self._token_input.text().strip()
        if not token:
            QMessageBox.warning(self, "Ошибка", "Введите токен!")
            return

        self._login_btn.setEnabled(False)
        self._login_btn.setText("Подключение...")

        try:
            self._api = DiscordAPI(token)
            self._worker = QuestWorker(self._api)
            self._worker.progress_updated.connect(self._on_progress)
            self._worker.quest_completed.connect(self._on_quest_done)
            self._worker.log_message.connect(self._on_log)

            profile, quests, orbs, history = await asyncio.gather(
                self._api.get_profile(),
                self._api.get_quests(),
                self._api.get_orbs(),
                self._api.get_quest_history(),
            )
            self._save_session(token)
            self._build_quests_page(profile, quests, orbs, history)
        except ValueError as e:
            QMessageBox.critical(self, "Ошибка", str(e))
            self._login_btn.setEnabled(True)
            self._login_btn.setText("Войти")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось подключиться:\n{e}")
            self._login_btn.setEnabled(True)
            self._login_btn.setText("Войти")

    def _on_logout(self):
        if hasattr(self, "_orbs_timer"):
            self._orbs_timer.stop()
        self._clear_session()
        self._api = None
        self._worker = None
        self._cards = {}
        self._build_login_page()

    def _run_quest(self, quest_id: str):
        card = self._cards.get(quest_id)
        if card:
            card.set_running(True)
        quest = self._get_quest_by_id(quest_id)
        if quest and self._worker:
            asyncio.ensure_future(self._worker.run_quest(quest))

    def _stop_quest(self, quest_id: str):
        if self._worker:
            self._worker.stop_quest(quest_id)
        card = self._cards.get(quest_id)
        if card:
            card.set_running(False)
            card.set_log("Остановлено")

    def _run_all(self):
        for quest_id, card in self._cards.items():
            if card.run_btn.isVisible() and card.run_btn.isEnabled():
                self._run_quest(quest_id)

    def _on_progress(self, quest_id: str, done: int, total: int):
        card = self._cards.get(quest_id)
        if card:
            card.update_progress(done, total)

    def _on_quest_done(self, quest_id: str):
        card = self._cards.get(quest_id)
        if card:
            card.set_completed()

    def _on_log(self, quest_id: str, message: str, color: str = "#72767d"):
        card = self._cards.get(quest_id)
        if card:
            card.set_log(message, color)

    def _switch_tab(self, index: int):
        if self._current_tab == index:
            return
        self._current_tab = index
        hide = self._quests_widget if index == 1 else self._history_widget
        show = self._history_widget if index == 1 else self._quests_widget
        self._tab_quests_btn.setObjectName("tabBtn" if index == 1 else "tabBtnActive")
        self._tab_history_btn.setObjectName("tabBtnActive" if index == 1 else "tabBtn")
        self._tab_quests_btn.setStyle(self._tab_quests_btn.style())
        self._tab_history_btn.setStyle(self._tab_history_btn.style())

        effect_out = QGraphicsOpacityEffect(hide)
        hide.setGraphicsEffect(effect_out)
        anim_out = QPropertyAnimation(effect_out, b"opacity", hide)
        anim_out.setDuration(150)
        anim_out.setStartValue(1.0)
        anim_out.setEndValue(0.0)
        anim_out.setEasingCurve(QEasingCurve.Type.OutCubic)

        def do_switch():
            hide.setVisible(False)
            hide.setGraphicsEffect(None)
            show.setVisible(True)
            effect_in = QGraphicsOpacityEffect(show)
            show.setGraphicsEffect(effect_in)
            anim_in = QPropertyAnimation(effect_in, b"opacity", show)
            anim_in.setDuration(200)
            anim_in.setStartValue(0.0)
            anim_in.setEndValue(1.0)
            anim_in.setEasingCurve(QEasingCurve.Type.OutCubic)
            anim_in.finished.connect(lambda: show.setGraphicsEffect(None))
            anim_in.start()
            show._tab_anim = anim_in

        anim_out.finished.connect(do_switch)
        anim_out.start()
        hide._tab_anim_out = anim_out

    def _get_quest_by_id(self, quest_id: str) -> dict | None:
        return getattr(self, "_quests_cache", {}).get(quest_id)

    def _show_token_help(self):
        from PyQt6.QtWidgets import QDialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Как получить токен Discord")
        dialog.setMinimumWidth(460)
        dialog.setStyleSheet(self.styleSheet())
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)
        steps = QLabel(
            "<b>Инструкция:</b><br><br>"
            "1. Откройте приложение Discord и нажмите <b>Ctrl+Shift+I</b><br>"
            "2. Перейдите во вкладку <b>Network</b><br>"
            "3. В поле <b>Filter</b> введите <b>api</b> и перезагрузите страницу (<b>Ctrl+F5</b>)<br>"
            "4. Найдите <b>science</b> в списке и кликните на него<br>"
            "5. Откройте вкладку <b>Headers</b><br>"
            "6. Напротив заголовка <b>authorization</b> — ваш токен"
        )
        steps.setTextFormat(Qt.TextFormat.RichText)
        steps.setWordWrap(True)
        layout.addWidget(steps)
        img_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "image.png")
        if os.path.exists(img_path):
            img_label = QLabel()
            pix = QPixmap(img_path)
            pix = pix.scaledToWidth(412, Qt.TransformationMode.SmoothTransformation)
            img_label.setPixmap(pix)
            img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(img_label)
        warn = QLabel("Никому не передавайте токен!")
        warn.setStyleSheet("color: #da373c; font-size: 12px;")
        layout.addWidget(warn)
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        dialog.exec()

    def _clear_layout(self):
        if self.layout():
            while self.layout().count():
                item = self.layout().takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            QWidget().setLayout(self.layout())

    def _apply_cursors(self, widget: QWidget):
        from PyQt6.QtWidgets import QPushButton
        for child in widget.findChildren(QPushButton):
            child.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
