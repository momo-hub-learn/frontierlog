#!/usr/bin/env python3
"""Jev 三类接口的知识核验示例。默认离线；--live 才调用付费 API。

核对日期：2026-09-25。
接口文档：https://docs.typesafe.ai/api
模型文档：https://docs.typesafe.ai/models

离线数值是教学示意，不是模型推理结果。这里没有模型权重，不执行任何工具。
运行：python jev_knowledge_demo.py
实调：设置 TYPESAFE_API_KEY 后，python jev_knowledge_demo.py --live
"""
from __future__ import annotations
import argparse
import json
import math
import os
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REQUEST_BODY = {
    "model": "jev-1.13.0",
    "state": {
        "question": "B17 批次良率下降的原因是什么？",
        "evidence": "B17 良率由97%降至92%。同期 ETCH-03 出现温控报警。尚无根因分析报告。",
        "claim": "ETCH-03 的温控异常造成了 B17 良率下降。",
    },
    "questions": {
        "supported": {
            "type": "noul",
            "instructions": "仅依据 state.evidence，是否有充分证据支持 state.claim？同时出现不等于因果证明。",
        },
        "next_step": {
            "type": "choice",
            "instructions": "依据 state.question 和现有 state.evidence，选择下一步的信息处理路径。不要执行动作。",
            "criteria": {
                "retrieve_more": "现有证据不足，应继续检索根因报告或相关记录。",
                "answer_now": "现有证据已充分，可以回答原因。",
                "human_review": "问题需要专家裁决，不能仅通过继续检索解决。",
            },
        },
        "relevance": {
            "type": "score",
            "instructions": "评价 state.evidence 与 state.question 的相关性，而不是它是否足以证明因果。",
            "criteria": [
                "材料与所问批次或良率问题无关。",
                "材料涉及相关工艺或设备，但未提供所问批次的直接记录。",
                "材料直接涉及所问批次的良率变化或同期设备记录。",
            ],
        },
    },
}

# 故意只展示 answer 摘要；没有伪造 confidence、usage、延迟或真实调用标识。
ILLUSTRATIVE_ANSWERS = {
    "supported": {"type": "noul", "noul": 0.08},
    "next_step": {
        "type": "choice", "choice": "retrieve_more",
        "probabilities": {"retrieve_more": 0.90, "answer_now": 0.02, "human_review": 0.08},
    },
    "relevance": {
        "type": "score", "score": 1.8,
        "probabilities": {"0": 0.0, "1": 0.2, "2": 0.8},
    },
}


def probability(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("概率必须是数值，不能是布尔值。")
    value = float(value)
    if not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError("概率必须是 [0, 1] 内的有限数。")
    return value


def distribution(value: Any, expected_keys: set[str]) -> dict[str, float]:
    if not isinstance(value, dict) or set(value) != expected_keys:
        raise ValueError("概率分布的候选与请求不一致。")
    result = {key: probability(p) for key, p in value.items()}
    if not math.isclose(sum(result.values()), 1.0, abs_tol=1e-3):
        raise ValueError("概率总和不接近 1。")
    return result


def inspect_answers(answers: Any) -> dict[str, Any]:
    """仅做接口一致性检查及可解释摘要；不证明语义正确，不授权动作。"""
    if not isinstance(answers, dict):
        raise ValueError("缺少 answers 对象。")
    if not {"supported", "next_step", "relevance"} <= set(answers):
        raise ValueError("返回结果缺少问题。")
    n, c, s = (answers[k] for k in ("supported", "next_step", "relevance"))
    if (n.get("type"), c.get("type"), s.get("type")) != ("noul", "choice", "score"):
        raise ValueError("响应类型与问题不一致。")
    p_support = probability(n["noul"])
    cp = distribution(c["probabilities"], set(REQUEST_BODY["questions"]["next_step"]["criteria"]))
    chosen = c["choice"]
    if chosen not in cp or not math.isclose(cp[chosen], max(cp.values()), abs_tol=1e-3):
        raise ValueError("Choice 不是最高概率候选。")
    sp = distribution(s["probabilities"], {"0", "1", "2"})
    expected_score = sum(int(k) * p for k, p in sp.items())
    raw_score = s["score"]
    if isinstance(raw_score, bool) or not isinstance(raw_score, (int, float)):
        raise ValueError("Score 不是数值。")
    if not math.isfinite(raw_score) or not math.isclose(raw_score, expected_score, abs_tol=0.01):
        raise ValueError("Score 与分布的加权期望不一致。")
    return {
        "support_probability": p_support,
        "suggested_path": chosen,
        "path_probability": cp[chosen],
        "relevance_expected_level": expected_score,
        "decision_status": "review_required_no_execution",
        "note": "相关性不等于证据支持。未设置经验证的自动化阈值，本脚本不自动回答、不执行工具。",
    }


def call_live(body: dict[str, Any]) -> dict[str, Any]:
    key = os.environ.get("TYPESAFE_API_KEY", "").strip()
    if not key:
        raise RuntimeError("--live 需要环境变量 TYPESAFE_API_KEY；未发出请求。")
    request = Request(
        "https://api.typesafe.ai/v1/systemone",
        data=json.dumps(body, ensure_ascii=False, allow_nan=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    # 不自动重试，避免示例中发生用户未预期的重复计费；生产环境应实现有界退避。
    try:
        with urlopen(request, timeout=45) as response:
            result = json.load(response)
    except HTTPError as exc:
        raise RuntimeError(f"API 返回 HTTP {exc.code}；未自动重试。") from None
    except (URLError, TimeoutError) as exc:
        raise RuntimeError(f"网络请求失败（{type(exc).__name__}）；未自动重试。") from None
    if not isinstance(result, dict):
        raise ValueError("API 未返回 JSON 对象。")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="真实调用 API，会消耗账户额度。")
    parser.add_argument("--print-request", action="store_true", help="仅输出请求 JSON，不调用 API。")
    args = parser.parse_args()
    try:
        if args.print_request:
            output = REQUEST_BODY
        elif args.live:
            response = call_live(REQUEST_BODY)
            output = {"mode": "live_api_response", "response": response,
                      "inspection": inspect_answers(response["answers"])}
        else:
            output = {"mode": "offline_illustration_NOT_model_inference",
                      "answer_excerpt": ILLUSTRATIVE_ANSWERS,
                      "inspection": inspect_answers(ILLUSTRATIVE_ANSWERS)}
        print(json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False))
        return 0
    except (ValueError, KeyError, TypeError, AttributeError, RuntimeError) as exc:
        print(f"停止处理：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
