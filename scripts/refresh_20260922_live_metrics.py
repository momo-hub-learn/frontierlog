from pathlib import Path
import json


def replace(path: str, old: str, new: str, expected: int = 1) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    found = text.count(old)
    if found != expected:
        raise SystemExit(f"{path}: expected {expected} occurrence(s), found {found}: {old[:100]}")
    p.write_text(text.replace(old, new), encoding="utf-8")


# Artificial Analysis published fuller GPT-6 Sol/Luna task-cost and Coding Agent
# results after the first launch snapshot. Refresh only source-backed live fields.
replace(
    "data/models.json",
    "独立公开快照：Intelligence Index 48、约 104.4 tok/s、输入/输出每百万 Token $2/$10、90% cache discount、872k context；当前 Cost per Intelligence Index Task 仍显示 N/A。",
    "独立公开快照：Intelligence Index 48、约 104.4 tok/s、输入/输出每百万 Token $2/$10、90% cache discount、872k context；Cost per Intelligence Index Task $1.06。Coding Agent Index 57（Codex harness）。",
)
replace(
    "data/models.json",
    "独立公开快照：Intelligence Index 37、约 157.2 tok/s、输入/输出每百万 Token $0.10/$0.50、1M context；当前 Cost per Intelligence Index Task 仍显示 N/A。",
    "独立公开快照：Intelligence Index 37、约 157.2 tok/s、输入/输出每百万 Token $0.10/$0.50、1M context；Cost per Intelligence Index Task $0.07。Coding Agent Index 41（Codex harness）。",
)
replace("data/models.json", "输出速度约 124.5 tok/s", "输出速度约 110.8 tok/s")
replace("data/models.json", "输出速度约 65 tok/s", "输出速度约 89.4 tok/s")
replace(
    "data/models.json",
    '"aa-gpt6-sol-max","name":"GPT-6 Sol (max)","maker":"OpenAI","intelligence":48,"speed":104.4,"cost_task":null,"input_price":2,"output_price":10,"coding":null',
    '"aa-gpt6-sol-max","name":"GPT-6 Sol (max)","maker":"OpenAI","intelligence":48,"speed":104.4,"cost_task":1.06,"input_price":2,"output_price":10,"coding":57',
)
replace(
    "data/models.json",
    '"aa-mimo-v26-pro","name":"MiMo-V2.6-Pro","maker":"Xiaomi","intelligence":46,"speed":124.5',
    '"aa-mimo-v26-pro","name":"MiMo-V2.6-Pro","maker":"Xiaomi","intelligence":46,"speed":110.8',
)
replace(
    "data/models.json",
    '"aa-grok-47-xhigh","name":"Grok 4.7 (xhigh)","maker":"SpaceXAI","intelligence":46,"speed":39,',
    '"aa-grok-47-xhigh","name":"Grok 4.7 (xhigh)","maker":"SpaceXAI","intelligence":46,"speed":39.2,',
)
replace(
    "data/models.json",
    '"aa-glm-53-flash","name":"GLM 5.3 Flash","maker":"Z AI","intelligence":42,"speed":65,',
    '"aa-glm-53-flash","name":"GLM 5.3 Flash","maker":"Z AI","intelligence":42,"speed":89.4,',
)
replace(
    "data/models.json",
    '"aa-gpt6-luna-max","name":"GPT-6 Luna (max)","maker":"OpenAI","intelligence":37,"speed":157.2,"cost_task":null,"input_price":0.1,"output_price":0.5,"coding":null',
    '"aa-gpt6-luna-max","name":"GPT-6 Luna (max)","maker":"OpenAI","intelligence":37,"speed":157.2,"cost_task":0.07,"input_price":0.1,"output_price":0.5,"coding":41',
)

# Hot page: replace stale launch-time N/A language with the now-published AA snapshot.
replace(
    "data/hot.json",
    "OpenAI 9 月 22 日发布 GPT-6 Sol 与 GPT-6 Luna，API 价分别为每百万输入 / 输出 Token $2/$10 与 $0.10/$0.50。Artificial Analysis 随后加入独立同口径快照：Sol (max) Intelligence Index 48，Luna (max) 37。",
    "OpenAI 9 月 22 日发布 GPT-6 Sol 与 GPT-6 Luna，API 价分别为每百万输入 / 输出 Token $2/$10 与 $0.10/$0.50。Artificial Analysis 同日独立评测：Sol (max) Intelligence Index 48、$1.06/task、Coding Agent Index 57；Luna (max) 37、$0.07/task、Coding Agent Index 41。",
)
replace(
    "data/hot.json",
    "发布、价格与可用性来自 OpenAI；48/37 来自 Artificial Analysis Intelligence Index v4.3.2 当前公开榜。AA 模型页当前仍把两者的 Cost per Intelligence Index Task 显示为 N/A，因此本站暂不写第三方转述的单任务成本；榜单速度与价格快照后续也可能继续变化。",
    "发布、价格与可用性来自 OpenAI；48/37、$1.06/$0.07 单任务成本与 57/41 Coding Agent Index 来自 Artificial Analysis 9 月 22 日公开评测。Coding Agent Index 使用 Codex harness，与基础模型 Intelligence Index 是不同维度；榜单速度与成本快照后续仍可能变化。",
)
replace("data/hot.json", "约 124.5 output tok/s", "约 110.8 output tok/s")
replace("data/hot.json", "46、约 124.5 tok/s、$0.13/task", "46、约 110.8 tok/s、$0.13/task")
replace(
    "data/hot.json",
    "42、约 65 output tok/s、Cost per Intelligence Index Task $0.25",
    "42、约 89.4 output tok/s、Cost per Intelligence Index Task $0.25",
)

# Capability page: surface the newly evaluated GPT-6 Sol coding-agent result.
replace(
    "data/capabilities.json",
    "模型、Agent Harness 与执行设置共同决定结果。Grok Build 行已按 Artificial Analysis Coding Agent Index v1.5 的 Grok 4.7 结果更新。",
    "模型、Agent Harness 与执行设置共同决定结果。GPT-6 Sol (max) 已按 Artificial Analysis 9 月 22 日 Coding Agent Index v1.5 的 Codex harness 结果更新；Grok Build 保留 Grok 4.7 当前快照。",
)
replace(
    "data/capabilities.json",
    '''        {
          "name": "GPT-5.6 Sol (max)",
          "maker": "OpenAI",
          "detail": "Codex",
          "index": 55,
          "deep": 72,
          "terminal": 37,
          "atlas": 54,
          "cost": 6.35,
          "time": 20.6
        },''',
    '''        {
          "name": "GPT-6 Sol (max)",
          "maker": "OpenAI",
          "detail": "Codex",
          "index": 57,
          "deep": 69,
          "terminal": 43,
          "atlas": 58,
          "cost": 2.99,
          "time": null
        },''',
)

for path in ("data/models.json", "data/hot.json", "data/capabilities.json"):
    json.loads(Path(path).read_text(encoding="utf-8"))

print("Live metrics patched and JSON validated")
