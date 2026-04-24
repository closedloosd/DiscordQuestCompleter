import urllib.request
import threading
import ssl
import certifi
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QProgressBar
from PyQt6.QtCore import Qt, QObject, pyqtSignal, QRect
from PyQt6.QtGui import QPixmap, QPainter, QBrush, QCursor

TASK_LABELS = {
    "WATCH_VIDEO": "Смотреть видео",
    "WATCH_VIDEO_ON_MOBILE": "Смотреть видео (мобайл)",
    "PLAY_ON_DESKTOP": "Играть на ПК",
    "STREAM_ON_DESKTOP": "Стримить на ПК",
    "PLAY_ACTIVITY": "Играть в активность",
}

class _ImageLoader(QObject):
    loaded = pyqtSignal(bytes)

    def load(self, url: str):
        def run():
            try:
                ctx = ssl.create_default_context(cafile=certifi.where())
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                data = urllib.request.urlopen(req, timeout=10, context=ctx).read()
                self.loaded.emit(data)
            except Exception:
                self.loaded.emit(b"")
        threading.Thread(target=run, daemon=True).start()


class QuestCard(QFrame):
    def __init__(self, quest: dict, on_run, on_stop, parent=None):
        super().__init__(parent)
        self.setObjectName("questCard")
        self.quest_id = quest["id"]
        self.on_run = on_run
        self.on_stop = on_stop
        self._loaders = []
        self._build(quest)

    def _build(self, quest: dict):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        config = quest["config"]
        task_config = config.get("task_config") or config.get("task_config_v2", {})
        tasks = task_config.get("tasks", {})

        from core.discord_api import SUPPORTED_TASKS
        task_name = next((t for t in SUPPORTED_TASKS if t in tasks), None)
        seconds_needed = tasks[task_name]["target"] if task_name else 0
        user_status = quest.get("user_status") or {}
        seconds_done = (user_status.get("progress") or {}).get(task_name or "", {}).get("value", 0)

        rewards_config = config.get("rewards_config") or {}
        rewards = rewards_config.get("rewards") or config.get("rewards") or []
        orbs = next((r.get("orb_quantity") or r.get("amount", 0) for r in rewards if r.get("orb_quantity") or r.get("amount")), 0)
        reward_name = None
        reward_asset = None
        if not orbs and rewards:
            r = rewards[0]
            msgs = r.get("messages") or {}
            reward_name = msgs.get("name") or msgs.get("name_with_article")
            if r.get("type") in (1, 2) or "decoration" in str(reward_name or "").lower():
                sku_id = r.get("sku_id", "")
                reward_asset = f"https://cdn.discordapp.com/avatar-decoration-presets/{sku_id}.png?size=80"

        assets = config.get("assets") or {}
        quest_id_cfg = config.get("id", "")
        app_id = (config.get("application") or {}).get("id")

        self._banner_label = QLabel()
        self._banner_label.setFixedHeight(120)
        self._banner_label.setStyleSheet("background-color: #313338; border-radius: 10px 10px 0 0;")
        self._banner_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._banner_label)

        hero_path = assets.get("quest_bar_hero") or assets.get("hero")
        if hero_path:
            hero_url = f"https://cdn.discordapp.com/{hero_path}" if not hero_path.startswith("http") else hero_path
            self._load_image(hero_url, self._banner_label, 520, 120, radius=0, cover=True)

        content = QFrame()
        content.setStyleSheet("QFrame { background: transparent; }")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(14, 10, 14, 12)
        content_layout.setSpacing(8)

        top = QHBoxLayout()
        top.setSpacing(10)

        self._icon_label = QLabel()
        self._icon_label.setFixedSize(36, 36)
        self._icon_label.setStyleSheet("border-radius: 6px; background-color: #1e1f22;")
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top.addWidget(self._icon_label)

        icon_path = assets.get("logotype_dark") or assets.get("logotype_light") or assets.get("logotype")
        if icon_path:
            icon_url = f"https://cdn.discordapp.com/{icon_path}" if icon_path.startswith("quests/") else f"https://cdn.discordapp.com/quests/{quest_id_cfg}/{icon_path}"
            self._load_image(icon_url, self._icon_label, 36, 36, radius=6)
        elif app_id:
            self._load_image(f"https://cdn.discordapp.com/app-icons/{app_id}/icon.png?size=64", self._icon_label, 36, 36, radius=6)

        name_col = QVBoxLayout()
        name_col.setSpacing(1)
        quest_name = config.get("messages", {}).get("quest_name", "Квест")
        title = QLabel(quest_name)
        title.setObjectName("questTitle")
        task_label = QLabel(TASK_LABELS.get(task_name, task_name or "Неизвестно"))
        task_label.setObjectName("questStatus")
        name_col.addWidget(title)
        name_col.addWidget(task_label)
        top.addLayout(name_col)
        top.addStretch()

        if orbs:
            orb_val = QLabel(f"{orbs} орбов")
            orb_val.setObjectName("questReward")
            orb_val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            top.addWidget(orb_val)
        elif reward_name:
            reward_col = QVBoxLayout()
            reward_col.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            reward_col.setSpacing(2)
            if reward_asset:
                self._reward_img = QLabel()
                self._reward_img.setFixedSize(40, 40)
                self._reward_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self._reward_img.setStyleSheet("background: transparent;")
                self._load_image(reward_asset, self._reward_img, 40, 40)
                reward_col.addWidget(self._reward_img)
            rname = QLabel(reward_name)
            rname.setObjectName("questReward")
            rname.setAlignment(Qt.AlignmentFlag.AlignRight)
            rname.setWordWrap(True)
            rname.setMaximumWidth(120)
            reward_col.addWidget(rname)
            top.addLayout(reward_col)

        content_layout.addLayout(top)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(int(seconds_needed) if seconds_needed else 1)
        self.progress_bar.setValue(int(seconds_done))
        self.progress_bar.setFixedHeight(6)
        content_layout.addWidget(self.progress_bar)

        bottom = QHBoxLayout()
        mins_left = max(0, int((seconds_needed - seconds_done) / 60))
        self.status_label = QLabel(f"Осталось: ~{mins_left} мин")
        self.status_label.setObjectName("questStatus")
        bottom.addWidget(self.status_label)
        bottom.addStretch()

        self.log_label = QLabel("")
        self.log_label.setObjectName("logLabel")
        bottom.addWidget(self.log_label)

        self.run_btn = QPushButton("Выполнить")
        self.run_btn.setObjectName("runBtn")
        self.run_btn.setFixedWidth(100)
        self.run_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.run_btn.clicked.connect(lambda: self.on_run(self.quest_id))

        self.stop_btn = QPushButton("Стоп")
        self.stop_btn.setObjectName("stopBtn")
        self.stop_btn.setFixedWidth(70)
        self.stop_btn.setVisible(False)
        self.stop_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.stop_btn.clicked.connect(lambda: self.on_stop(self.quest_id))

        bottom.addWidget(self.run_btn)
        bottom.addWidget(self.stop_btn)
        content_layout.addLayout(bottom)

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
                scaled = pix.scaled(w, h, Qt.AspectRatioMode.KeepAspectRatio,
                                    Qt.TransformationMode.SmoothTransformation)
                x = (w - scaled.width()) // 2
                y = (h - scaled.height()) // 2
                painter.drawPixmap(x, y, scaled)
                painter.end()
                label.setPixmap(rounded)
            else:
                label.setPixmap(pix.scaled(w, h, Qt.AspectRatioMode.KeepAspectRatio,
                                           Qt.TransformationMode.SmoothTransformation))
        loader.loaded.connect(on_loaded)
        loader.load(url)
        self._loaders.append(loader)

    def set_running(self, running: bool):
        self.run_btn.setVisible(not running)
        self.stop_btn.setVisible(running)

    def update_progress(self, done: int, total: int):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(done)
        mins_left = max(0, int((total - done) / 60))
        self.status_label.setText(f"Осталось: ~{mins_left} мин")

    def set_completed(self):
        self.progress_bar.setValue(self.progress_bar.maximum())
        self.status_label.setText("Выполнено!")
        self.status_label.setStyleSheet("color: #248046; font-weight: bold;")
        self.run_btn.setEnabled(False)
        self.run_btn.setVisible(True)
        self.stop_btn.setVisible(False)
        self.run_btn.setText("Готово")

    def set_log(self, text: str, color: str = "#72767d"):
        self.log_label.setText(text)
        self.log_label.setStyleSheet(f"font-size: 11px; font-style: italic; color: {color};")
