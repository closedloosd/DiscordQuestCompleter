import aiohttp
import base64
import json

DISCORD_API = "https://discord.com/api/v9"

SUPPORTED_TASKS = ["WATCH_VIDEO", "PLAY_ON_DESKTOP", "STREAM_ON_DESKTOP", "PLAY_ACTIVITY", "WATCH_VIDEO_ON_MOBILE"]

SUPER_PROPERTIES = base64.b64encode(json.dumps({
    "os": "Windows",
    "browser": "Discord Client",
    "release_channel": "stable",
    "client_version": "1.0.9234",
    "os_version": "10.0.26200",
    "os_arch": "x64",
    "app_arch": "x64",
    "system_locale": "ru",
    "has_client_mods": False,
    "browser_user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) discord/1.0.9234 Chrome/138.0.7204.251 Electron/37.6.0 Safari/537.36",
    "browser_version": "37.6.0",
    "client_build_number": 534681,
    "native_build_number": 80790,
    "client_event_source": None,
}).encode()).decode()

class DiscordAPI:
    def __init__(self, token: str):
        self.token = token
        self.headers = {
            "Authorization": token,
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) discord/1.0.9234 Chrome/138.0.7204.251 Electron/37.6.0 Safari/537.36",
            "x-discord-locale": "ru",
            "x-discord-timezone": "Europe/Moscow",
            "x-super-properties": SUPER_PROPERTIES,
            "Referer": "https://discord.com/quest-home",
        }

    async def get_profile(self) -> dict:
        async with aiohttp.ClientSession(headers=self.headers) as s:
            async with s.get(f"{DISCORD_API}/users/@me") as r:
                if r.status == 401:
                    raise ValueError("Неверный токен")
                return await r.json()

    async def get_quests(self) -> list:
        async with aiohttp.ClientSession(headers=self.headers) as s:
            async with s.get(f"{DISCORD_API}/quests/@me") as r:
                if r.status != 200:
                    return []
                raw = await r.json()
                data = raw if isinstance(raw, list) else raw.get("quests", [])
                result = []
                for q in data:
                    if not isinstance(q, dict):
                        continue
                    if (q.get("user_status") or {}).get("completed_at"):
                        continue
                    try:
                        from datetime import datetime, timezone
                        expires = datetime.fromisoformat(q["config"]["expires_at"].replace("Z", "+00:00"))
                        if expires < datetime.now(timezone.utc):
                            continue
                    except Exception:
                        pass
                    cfg = q.get("config") or {}
                    task_config = (
                        cfg.get("task_config")
                        or cfg.get("taskConfig")
                        or cfg.get("task_config_v2")
                        or cfg.get("taskConfigV2")
                        or {}
                    )
                    tasks = task_config.get("tasks") or {}
                    task_name = next((t for t in SUPPORTED_TASKS if t in tasks), None)
                    if task_name:
                        result.append(q)
                return result

    async def enroll(self, quest_id: str) -> dict:
        async with aiohttp.ClientSession(headers=self.headers) as s:
            async with s.post(f"{DISCORD_API}/quests/{quest_id}/enroll", json={"location": "quest-home"}) as r:
                return await r.json()

    async def send_game_heartbeat(self, quest_id: str, app_id: str, pid: int) -> dict:
        async with aiohttp.ClientSession(headers=self.headers) as s:
            async with s.post(f"{DISCORD_API}/quests/{quest_id}/heartbeat",
                              json={"app_id": app_id, "pid": pid}) as r:
                data = await r.json()
                return data

    async def video_progress(self, quest_id: str, timestamp: float) -> dict:
        async with aiohttp.ClientSession(headers=self.headers) as s:
            async with s.post(f"{DISCORD_API}/quests/{quest_id}/video-progress",
                              json={"timestamp": timestamp}) as r:
                return await r.json()

    async def heartbeat(self, quest_id: str, stream_key: str, terminal: bool = False) -> dict:
        async with aiohttp.ClientSession(headers=self.headers) as s:
            async with s.post(f"{DISCORD_API}/quests/{quest_id}/heartbeat",
                              json={"stream_key": stream_key, "terminal": terminal}) as r:
                return await r.json()

    async def get_orbs(self) -> int:
        async with aiohttp.ClientSession(headers=self.headers) as s:
            async with s.get(f"{DISCORD_API}/users/@me/virtual-currency/balance") as r:
                if r.status != 200:
                    return -1
                data = await r.json()
                return data.get("balance") or data.get("orb_balance") or 0

    async def get_quest_history(self) -> list:
        async with aiohttp.ClientSession(headers=self.headers) as s:
            async with s.get(f"{DISCORD_API}/quests/@me?include_completed=true") as r:
                if r.status != 200:
                    return []
                raw = await r.json()
                data = raw if isinstance(raw, list) else raw.get("quests", [])
                return [q for q in data if isinstance(q, dict) and (q.get("user_status") or {}).get("completed_at")]

    async def get_avatar_url(self, user_id: str, avatar_hash: str) -> str:
        return f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_hash}.png?size=64"
