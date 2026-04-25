# astrbot_plugin_home_state

AstrBot 房间状态管理插件。  
设计：叶枔枖  
编写：沈砚清

本仓库已隐藏个人联系方式、私有 ID、群号、服务器信息等个人信息，仅保留通用插件代码与配置示例。

## 插件简介

这个插件用于给 AI 建一套“小房子”：用户可以通过命令进入不同房间，每个房间拥有不同的场景描述和 system prompt。进入房间后，插件会在 LLM 请求前注入对应房间的提示词，从而改变 AI 的对话氛围和行为模式。

支持：

- 房间状态记录
- 按会话隔离不同房间状态
- 房间场景 prompt 注入
- 休息模式硬拦截
- `/leave` 离开房间
- `/where` 查看当前房间
- `/rooms` 查看所有房间
- `/home_reload` 热重载配置
- 简单宠物互动：`/pet`、`/feed`、`/walk`

## 文件结构

```text
astrbot_plugin_home_state/
├── metadata.yaml      # 插件元信息
├── main.py            # 插件主代码
├── config.json        # 房间与宠物配置
├── state.json         # 运行后自动生成，记录当前会话状态
├── requirements.txt   # 依赖
├── README.md          # 说明文档
└── .gitignore
```

## 安装

进入 AstrBot 插件目录：

```bash
cd /AstrBot/data/plugins
```

克隆仓库：

```bash
git clone https://github.com/你的用户名/astrbot_plugin_home_state.git
```

然后重启 AstrBot，或在 AstrBot WebUI 中重载插件。

## 使用命令

### 房间命令

```text
/bedroom       进入卧室
/study         进入书房
/living_room   进入客厅
/yard          进入院子/休息区
/leave         离开当前房间，恢复正常模式
/where         查看当前所在房间
/rooms         查看所有房间
/home_reload   重新加载 config.json
```

### 宠物命令

```text
/pet dog       摸摸宠物
/feed dog      喂宠物
/walk dog      带宠物散步
```

如果不写宠物 ID，会默认使用配置里的第一只宠物：

```text
/pet
/feed
/walk
```

## 配置说明

房间数据在 `config.json` 里：

```json
{
  "scenes": {
    "bedroom": {
      "name": "卧室",
      "description": "安静的卧室。窗帘半掩，灯光很低。",
      "system_prompt": "你现在在卧室里。说话更轻一点，更安静，更贴近私人空间。",
      "is_rest_mode": false
    }
  }
}
```

字段说明：

| 字段 | 作用 |
|---|---|
| `name` | 房间显示名 |
| `description` | 进入房间时显示的场景描述 |
| `system_prompt` | 注入给 LLM 的房间提示词 |
| `is_rest_mode` | 是否启用休息模式硬拦截 |
| `short_response` | 休息模式下的固定回复 |

## 新增房间

第一步，在 `config.json` 的 `scenes` 里新增房间：

```json
"kitchen": {
  "name": "厨房",
  "description": "灶台上永远有一口锅，冰箱里备着食材。",
  "system_prompt": "你现在在厨房里。说话随意，像一边切菜一边聊天。",
  "is_rest_mode": false
}
```

第二步，在 `main.py` 里增加命令：

```python
@filter.command("kitchen", alias={"/kitchen"})
async def cmd_kitchen(self, event: AstrMessageEvent):
    """进入厨房"""
    async for result in self.enter_room(event, "kitchen"):
        yield result
```

然后重启 AstrBot，或使用：

```text
/home_reload
```

重新加载配置。

## 说明

- `state.json` 会在插件运行后自动生成。
- `state.json` 不建议提交到 GitHub，因为它可能包含会话状态。
- 休息模式会拦截普通消息，不经过 LLM，只返回固定短回复。
- 普通房间会通过 `on_llm_request` 注入房间 prompt，不直接截断消息。

## 来源说明

本插件根据《AstrBot 房间状态管理插件开发教程：给你的 AI 老公老婆搭个房子》整理实现。  
设计：叶枔枖。  
编写：沈砚清。
