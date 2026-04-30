import os
import json
import random
import time
from datetime import datetime

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register, StarTools
from astrbot.api.provider import ProviderRequest

PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))

DEFAULT_CONFIG = {
    "scenes": {
        "bedroom": {
            "name": "卧室",
            "description": "安静的卧室。窗帘半掩，灯光很低。",
            "system_prompt": "你现在在卧室里。说话更轻一点，更安静，更贴近私人空间。",
            "is_rest_mode": False,
        },
        "study": {
            "name": "书房",
            "description": "整洁的书房。桌上有书、笔记本和一盏台灯。",
            "system_prompt": "你现在在书房里。保持专注、清晰、克制，适合学习、写作和整理思路。",
            "is_rest_mode": False,
        },
        "living_room": {
            "name": "客厅",
            "description": "温暖的客厅。阳光从窗户照进来。",
            "system_prompt": "你现在在客厅里。语气自然、放松，像在日常聊天。",
            "is_rest_mode": False,
        },
        "yard": {
            "name": "院子",
            "description": "院子里有风和树影，适合短暂休息。",
            "system_prompt": "你现在在院子里。这里是休息区，只保持极简回应。",
            "is_rest_mode": True,
            "short_response": "。",
        },
    },
    "pets": {},
}


def load_json(path: str, default):
    if not os.path.exists(path):
        save_json(path, default)
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(path: str, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


@register("home_state", "沈砚清", "房间状态管理插件", "1.0.0", "https://github.com/yussica1016/astrbot_plugin_home_state")
class HomeStatePlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        plugin_name = getattr(self, "name", None) or "home_state"
        self.data_dir = str(StarTools.get_data_dir(plugin_name))
        os.makedirs(self.data_dir, exist_ok=True)
        self.config_file = os.path.join(self.data_dir, "config.json")
        self.state_file = os.path.join(self.data_dir, "state.json")
        self.config = load_json(self.config_file, DEFAULT_CONFIG)
        self.state = load_json(self.state_file, {})
        self._state_dirty = False
        self._last_save_time = 0.0

    def get_session_key(self, event: AstrMessageEvent) -> str:
        return getattr(event, "unified_msg_origin", None) or str(event.get_sender_id())

    def get_room(self, session_key: str):
        return self.state.get(session_key, {}).get("current_room")

    def _save_state_if_needed(self, force: bool = False):
        """防止频繁全量覆写：至少间隔5秒才实际写入"""
        now = time.time()
        if force or (self._state_dirty and now - self._last_save_time > 5):
            save_json(self.state_file, self.state)
            self._state_dirty = False
            self._last_save_time = now

    def set_room(self, session_key: str, room_id: str):
        self.state[session_key] = {
            "current_room": room_id,
            "last_changed": datetime.now().isoformat(timespec="seconds"),
        }
        self._state_dirty = True
        self._save_state_if_needed()

    def clear_room(self, session_key: str):
        self.state.pop(session_key, None)
        self._state_dirty = True
        self._save_state_if_needed(force=True)

    def get_room_info(self, room_id: str):
        return self.config.get("scenes", {}).get(room_id)

    def get_pet_behavior(self, pet_data: dict, room_id: str) -> str:
        behaviors = pet_data.get("room_behaviors", {})
        return behaviors.get(room_id, "")

    def build_room_entry_text(self, room_id: str) -> str:
        room_info = self.get_room_info(room_id)
        if not room_info:
            return "这个房间还没有配置。"

        text = f"你进入了{room_info.get('name', room_id)}。{room_info.get('description', '')}"

        pets = self.config.get("pets", {})
        for _pet_id, pet_data in pets.items():
            behavior = self.get_pet_behavior(pet_data, room_id)
            if behavior and random.random() < 0.7:
                text += f"\n{pet_data.get('name', '宠物')}：{behavior}"

        return text.strip()

    async def enter_room(self, event: AstrMessageEvent, room_id: str):
        session_key = self.get_session_key(event)
        self.set_room(session_key, room_id)
        yield event.plain_result(self.build_room_entry_text(room_id))

    @filter.command("bedroom", alias={"/bedroom"})
    async def cmd_bedroom(self, event: AstrMessageEvent):
        """进入卧室"""
        async for result in self.enter_room(event, "bedroom"):
            yield result

    @filter.command("study", alias={"/study"})
    async def cmd_study(self, event: AstrMessageEvent):
        """进入书房"""
        async for result in self.enter_room(event, "study"):
            yield result

    @filter.command("living_room", alias={"/living_room"})
    async def cmd_living_room(self, event: AstrMessageEvent):
        """进入客厅"""
        async for result in self.enter_room(event, "living_room"):
            yield result

    @filter.command("yard", alias={"/yard"})
    async def cmd_yard(self, event: AstrMessageEvent):
        """进入院子/休息区"""
        async for result in self.enter_room(event, "yard"):
            yield result

    @filter.command("leave", alias={"/leave"})
    async def cmd_leave(self, event: AstrMessageEvent):
        """离开当前房间，恢复正常模式"""
        session_key = self.get_session_key(event)
        self.clear_room(session_key)
        yield event.plain_result("已恢复正常模式。")

    @filter.command("where", alias={"/where"})
    async def cmd_where(self, event: AstrMessageEvent):
        """查看当前所在房间"""
        session_key = self.get_session_key(event)
        room_id = self.get_room(session_key)
        if not room_id:
            yield event.plain_result("你现在不在任何房间里。")
            return
        room_info = self.get_room_info(room_id) or {}
        yield event.plain_result(f"当前房间：{room_info.get('name', room_id)}。")

    @filter.command("rooms", alias={"/rooms"})
    async def cmd_rooms(self, event: AstrMessageEvent):
        """查看所有房间"""
        scenes = self.config.get("scenes", {})
        if not scenes:
            yield event.plain_result("还没有配置房间。")
            return
        lines = ["可用房间："]
        for room_id, info in scenes.items():
            lines.append(f"/{room_id} - {info.get('name', room_id)}")
        lines.append("/leave - 离开房间")
        lines.append("/where - 查看当前位置")
        yield event.plain_result("\n".join(lines))

    @filter.command("home_reload", alias={"/home_reload"})
    async def cmd_home_reload(self, event: AstrMessageEvent):
        """重新加载 config.json"""
        self.config = load_json(self.config_file, DEFAULT_CONFIG)
        yield event.plain_result("房间配置已重新加载。")

    async def pet_action(self, event: AstrMessageEvent, action: str):
        pets = self.config.get("pets", {})
        if not pets:
            yield event.plain_result("还没有配置宠物。")
            return

        raw = (event.message_str or "").strip().split()
        pet_id = raw[1] if len(raw) >= 2 else next(iter(pets.keys()))
        pet_data = pets.get(pet_id)
        if not pet_data:
            yield event.plain_result("没有找到这只宠物。")
            return

        items = pet_data.get("interactions", {}).get(action, [])
        if not items:
            yield event.plain_result(f"{pet_data.get('name', pet_id)}暂时不知道该怎么回应。")
            return
        yield event.plain_result(random.choice(items))

    @filter.command("pet", alias={"/pet"})
    async def cmd_pet(self, event: AstrMessageEvent):
        """摸摸宠物，可写 /pet dog"""
        async for result in self.pet_action(event, "pet"):
            yield result

    @filter.command("feed", alias={"/feed"})
    async def cmd_feed(self, event: AstrMessageEvent):
        """喂宠物，可写 /feed dog"""
        async for result in self.pet_action(event, "feed"):
            yield result

    @filter.command("walk", alias={"/walk"})
    async def cmd_walk(self, event: AstrMessageEvent):
        """带宠物散步，可写 /walk dog"""
        async for result in self.pet_action(event, "walk"):
            yield result

    @filter.on_llm_request()
    async def on_llm_request(self, event: AstrMessageEvent, req: ProviderRequest):
        session_key = self.get_session_key(event)
        room_id = self.get_room(session_key)
        if not room_id:
            return

        room_info = self.get_room_info(room_id)
        if not room_info:
            return

        room_prompt = room_info.get("system_prompt", "")
        pet_lines = []
        for _pet_id, pet_data in self.config.get("pets", {}).items():
            behavior = self.get_pet_behavior(pet_data, room_id)
            if behavior:
                pet_lines.append(f"当前房间里的{pet_data.get('name', '宠物')}：{behavior}")

        injected = "\n".join([room_prompt] + pet_lines).strip()
        if not injected:
            return

        # 休息模式下追加极简回复指令，但不阻断事件传播
        if room_info.get("is_rest_mode", False):
            rest_hint = room_info.get("rest_prompt", "你现在在休息区。只用极短的回复，一两个字即可。不主动展开话题。")
            injected = f"{injected}\n{rest_hint}"

        current_system_prompt = getattr(req, "system_prompt", "") or ""
        req.system_prompt = f"{injected}\n\n{current_system_prompt}".strip()

    # 注意：不再使用 event.stop_event() 硬拦截消息。
    # 休息模式的简短回复通过 on_llm_request 注入 system_prompt 实现，
    # 这样其他插件的 handler 仍然能正常处理消息，不会破坏插件生态。

    async def terminate(self):
        """插件卸载时确保状态已保存"""
        self._save_state_if_needed(force=True)
