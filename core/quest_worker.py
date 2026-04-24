import asyncio
from datetime import datetime, timezone
from PyQt6.QtCore import QObject, pyqtSignal
from core.discord_api import DiscordAPI, SUPPORTED_TASKS

class QuestWorker(QObject):
    progress_updated = pyqtSignal(str, int, int)
    quest_completed = pyqtSignal(str)
    log_message = pyqtSignal(str, str, str)

    def __init__(self, api: DiscordAPI):
        super().__init__()
        self.api = api
        self._running: dict[str, bool] = {}

    def stop_quest(self, quest_id: str):
        self._running[quest_id] = False

    async def run_quest(self, quest: dict):
        quest_id = quest["id"]
        self._running[quest_id] = True

        user_status = quest.get("user_status") or {}
        if not user_status.get("enrolled_at"):
            self.log_message.emit(quest_id, "Записываемся на квест...", "#72767d")
            enrolled = await self.api.enroll(quest_id)
            if "user_status" in enrolled:
                quest["user_status"] = enrolled["user_status"]
        task_config = quest["config"].get("task_config") or quest["config"].get("task_config_v2", {})
        tasks = task_config.get("tasks", {})
        task_name = next((t for t in SUPPORTED_TASKS if t in tasks), None)
        if not task_name:
            self.log_message.emit(quest_id, "Задание не поддерживается", "#da373c")
            return

        seconds_needed = tasks[task_name]["target"]
        user_status = quest.get("user_status") or {}
        seconds_done = (user_status.get("progress") or {}).get(task_name, {}).get("value", 0)

        if task_name in ("WATCH_VIDEO", "WATCH_VIDEO_ON_MOBILE"):
            await self._do_video(quest, quest_id, task_name, seconds_needed, seconds_done)
        elif task_name == "PLAY_ACTIVITY":
            await self._do_activity(quest, quest_id, seconds_needed)
        elif task_name == "PLAY_ON_DESKTOP":
            await self._do_play_on_desktop(quest, quest_id, seconds_needed, seconds_done)
        elif task_name == "STREAM_ON_DESKTOP":
            await self._do_stream_on_desktop(quest, quest_id, seconds_needed, seconds_done)
        else:
            self.log_message.emit(quest_id, f"Задание {task_name} не поддерживается")

    async def _do_video(self, quest, quest_id, task_name, seconds_needed, seconds_done):
        user_status = quest.get("user_status") or {}
        enrolled_at_str = user_status.get("enrolled_at")
        if enrolled_at_str:
            enrolled_at = datetime.fromisoformat(enrolled_at_str.replace("Z", "+00:00")).timestamp() * 1000
        else:
            enrolled_at = datetime.now(timezone.utc).timestamp() * 1000
        max_future, speed, interval = 10, 7, 1
        completed = False

        self.log_message.emit(quest_id, "Начинаем просмотр видео...", "#248046")

        while self._running.get(quest_id):
            max_allowed = (datetime.now(timezone.utc).timestamp() * 1000 - enrolled_at) / 1000 + max_future
            diff = max_allowed - seconds_done
            timestamp = seconds_done + speed

            if diff >= speed:
                import random
                res = await self.api.video_progress(quest_id, min(seconds_needed, timestamp + random.random()))
                completed = res.get("completed_at") is not None
                seconds_done = min(seconds_needed, timestamp)
                self.progress_updated.emit(quest_id, int(seconds_done), int(seconds_needed))

            if timestamp >= seconds_needed:
                break

            await asyncio.sleep(interval)

        if not completed:
            await self.api.video_progress(quest_id, seconds_needed)

        self.progress_updated.emit(quest_id, int(seconds_needed), int(seconds_needed))
        self.quest_completed.emit(quest_id)
        self.log_message.emit(quest_id, "Задание выполнено!", "#248046")

    async def _do_play_on_desktop(self, quest, quest_id, seconds_needed, seconds_done):
        self.log_message.emit(quest_id, "Выполняется...", "#248046")
        app_id = quest["config"]["application"]["id"]
        import random
        pid = random.randint(1000, 30000)

        while self._running.get(quest_id):
            res = await self.api.send_game_heartbeat(quest_id, app_id, pid)
            progress = (res.get("progress") or {}).get("PLAY_ON_DESKTOP", {}).get("value", 0)
            self.progress_updated.emit(quest_id, int(progress), int(seconds_needed))
            if progress >= seconds_needed or res.get("completed_at"):
                break
            await asyncio.sleep(20)

        self.progress_updated.emit(quest_id, int(seconds_needed), int(seconds_needed))
        self.quest_completed.emit(quest_id)
        self.log_message.emit(quest_id, "Задание выполнено!", "#248046")

    async def _do_stream_on_desktop(self, quest, quest_id, seconds_needed, seconds_done):
        self.log_message.emit(quest_id, "Выполняется...", "#248046")
        app_id = quest["config"]["application"]["id"]
        import random
        pid = random.randint(1000, 30000)

        while self._running.get(quest_id):
            res = await self.api.send_game_heartbeat(quest_id, app_id, pid)
            progress = (res.get("progress") or {}).get("STREAM_ON_DESKTOP", {}).get("value", 0)
            self.progress_updated.emit(quest_id, int(progress), int(seconds_needed))
            if progress >= seconds_needed or res.get("completed_at"):
                break
            await asyncio.sleep(20)

        self.progress_updated.emit(quest_id, int(seconds_needed), int(seconds_needed))
        self.quest_completed.emit(quest_id)
        self.log_message.emit(quest_id, "Задание выполнено!", "#248046")

    async def _do_activity(self, quest, quest_id, seconds_needed):
        stream_key = "call:0:1"
        self.log_message.emit(quest_id, "Выполняется...", "#248046")

        while self._running.get(quest_id):
            res = await self.api.heartbeat(quest_id, stream_key, terminal=False)
            progress = res.get("progress", {}).get("PLAY_ACTIVITY", {}).get("value", 0)
            self.progress_updated.emit(quest_id, int(progress), int(seconds_needed))

            if progress >= seconds_needed:
                await self.api.heartbeat(quest_id, stream_key, terminal=True)
                break

            await asyncio.sleep(20)

        self.quest_completed.emit(quest_id)
        self.log_message.emit(quest_id, "Задание выполнено!", "#248046")
