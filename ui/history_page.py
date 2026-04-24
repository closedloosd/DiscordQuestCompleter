from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea
from PyQt6.QtCore import Qt, QRect, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QPixmap, QPainter, QBrush, QWheelEvent
from ui.quest_card import _ImageLoader


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


class HistoryCard(QFrame):
    def __init__(self, quest: dict, parent=None):
        super().__init__(parent)
        self.setObjectName("questCard")
        self._loaders = []
        self._build(quest)

    def _build(self, quest: dict):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        config = quest.get("config") or {}
        assets = config.get("assets") or {}
        quest_id_cfg = config.get("id", "")
        user_status = quest.get("user_status") or {}
        rewards_config = config.get("rewards_config") or {}
        rewards = rewards_config.get("rewards") or config.get("rewards") or []

        banner = QLabel()
        banner.setFixedHeight(80)
        banner.setStyleSheet("background-color: #313338; border-radius: 10px 10px 0 0;")
        banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(banner)

        hero_path = assets.get("quest_bar_hero") or assets.get("hero")
        if hero_path:
            self._load_image(f"https://cdn.discordapp.com/{hero_path}", banner, 520, 80, cover=True)

        content = QFrame()
        content.setStyleSheet("background: transparent;")
        cl = QVBoxLayout(content)
        cl.setContentsMargins(14, 10, 14, 12)
        cl.setSpacing(6)

        top = QHBoxLayout()
        top.setSpacing(10)

        icon_lbl = QLabel()
        icon_lbl.setFixedSize(36, 36)
        icon_lbl.setStyleSheet("border-radius: 6px; background-color: #1e1f22;")
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top.addWidget(icon_lbl)

        icon_path = assets.get("logotype_dark") or assets.get("logotype_light") or assets.get("logotype")
        if icon_path:
            icon_url = f"https://cdn.discordapp.com/{icon_path}" if icon_path.startswith("quests/") else f"https://cdn.discordapp.com/quests/{quest_id_cfg}/{icon_path}"
            self._load_image(icon_url, icon_lbl, 36, 36, radius=6)

        name_col = QVBoxLayout()
        name_col.setSpacing(1)
        quest_name = config.get("messages", {}).get("quest_name", "Квест")
        title = QLabel(quest_name)
        title.setObjectName("questTitle")
        completed_at = user_status.get("completed_at", "")[:10] if user_status.get("completed_at") else ""
        date_lbl = QLabel(f"Выполнено: {completed_at}")
        date_lbl.setObjectName("questStatus")
        name_col.addWidget(title)
        name_col.addWidget(date_lbl)
        top.addLayout(name_col)
        top.addStretch()

        reward_col = QVBoxLayout()
        reward_col.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        for r in rewards:
            orbs = r.get("orb_quantity") or r.get("amount", 0)
            if orbs:
                orb_lbl = QLabel(f"{orbs} орбов")
                orb_lbl.setObjectName("questReward")
                orb_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
                reward_col.addWidget(orb_lbl)
            reward_type = r.get("type")
            if reward_type in (1, 2, "AVATAR_DECORATION"):
                asset_hash = r.get("asset") or (r.get("messages") or {}).get("asset")
                frame_lbl = QLabel()
                frame_lbl.setFixedSize(40, 40)
                frame_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                frame_lbl.setStyleSheet("background: transparent;")
                if asset_hash:
                    self._load_image(f"https://cdn.discordapp.com/avatar-decoration-presets/{asset_hash}.png?size=64", frame_lbl, 40, 40)
                reward_col.addWidget(frame_lbl)
        top.addLayout(reward_col)
        cl.addLayout(top)
        layout.addWidget(content)

    def _load_image(self, url: str, label: QLabel, w: int, h: int, radius: int = 0, cover: bool = False):
        loader = _ImageLoader(self)
        def on_loaded(data: bytes):
            if not data:
                return
            pix = QPixmap()
            pix.loadFromData(data)
            if pix.isNull():
                return
            if cover:
                scaled = pix.scaledToWidth(label.width() or w, Qt.TransformationMode.SmoothTransformation)
                if scaled.height() > h:
                    y = (scaled.height() - h) // 2
                    scaled = scaled.copy(0, y, scaled.width(), h)
                label.setPixmap(scaled)
            elif radius:
                rounded = QPixmap(w, h)
                rounded.fill(Qt.GlobalColor.transparent)
                painter = QPainter(rounded)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                scaled = pix.scaled(w, h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                x = (w - scaled.width()) // 2
                y = (h - scaled.height()) // 2
                painter.drawPixmap(x, y, scaled)
                painter.end()
                label.setPixmap(rounded)
            else:
                label.setPixmap(pix.scaled(w, h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        loader.loaded.connect(on_loaded)
        loader.load(url)
        self._loaders.append(loader)


class HistoryPage(QWidget):
    def __init__(self, history: list, total_orbs: int, parent=None):
        super().__init__(parent)
        self._build(history, total_orbs)

    def _build(self, history: list, total_orbs: int):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        total_frame = QFrame()
        total_frame.setObjectName("questCard")
        tl = QHBoxLayout(total_frame)
        tl.setContentsMargins(14, 10, 14, 10)
        total_lbl = QLabel(f"Всего орбов получено за все задания: {total_orbs}")
        total_lbl.setObjectName("profileName")
        tl.addWidget(total_lbl)
        layout.addWidget(total_frame)

        if not history:
            empty = QLabel("История заданий пуста")
            empty.setObjectName("subtitleLabel")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(empty)
            layout.addStretch()
            return

        scroll = SmoothScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("border: none; background: transparent;")

        container = QWidget()
        cl = QVBoxLayout(container)
        cl.setContentsMargins(0, 4, 8, 4)
        cl.setSpacing(12)

        for quest in history:
            cl.addWidget(HistoryCard(quest))

        cl.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll)
