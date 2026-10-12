#!/usr/bin/env python3
"""
MCP 安全扫描脚本
=================

功能：
    读取白名单中的 MCP 配置文件路径，提取可用的 MCP 服务信息。
    输出结构化 JSON，供 Agent 或用户查看。

安全原则：
    - 只扫描白名单中的固定路径，不遍历全盘
    - 不联网，不上传任何数据
    - 不执行配置文件中的任何命令
    - 不输出敏感字段（env / token / key / password 等）
    - 不保存任何状态（仅打印到 stdout）

用法：
    python3 scan_config.py                     # 使用默认白名单
    python3 scan_config.py path/to/whitelist.json

依赖：
    Python 3.8+，仅使用标准库。
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path


# 敏感字段关键词，匹配到则 redact
SENSITIVE_KEYS = {
    "env", "environment", "headers", "token", "key", "apikey",
    "api_key", "password", "secret", "authorization", "auth",
}

# 只显示 args 列表的第一个元素（通常是包名 / 脚本名）
# 后续元素可能包含路径或密钥，不予输出
ARGS_PREVIEW_COUNT = 1


def expand_path(raw: str) -> Path:
    """展开 ~ 和 %VAR% / $VAR 环境变量。"""
    expanded = os.path.expandvars(os.path.expanduser(raw))
    return Path(expanded)


def clean_url(url: str) -> str:
    """移除 URL 中的 query string，避免泄露 token 等参数。"""
    if "?" in url:
        return url.split("?", 1)[0]
    return url


def extract_services(config: dict) -> list:
    """
    从 MCP 配置文件中提取服务列表。
    支持常见的几种格式：mcpServers / mcp_servers / servers。
    仅提取服务名、传输方式、启动命令、URL（去 query），不提取敏感字段。
    """
    services = []

    container = None
    for key in ("mcpServers", "mcp_servers", "servers"):
        if key in config and isinstance(config[key], dict):
            container = config[key]
            break

    if container is None:
        return services

    for name, cfg in container.items():
        if not isinstance(cfg, dict):
            continue

        service = {"name": name}

        # stdio 类型：有 command
        if "command" in cfg:
            service["transport"] = "stdio"
            service["command"] = str(cfg.get("command", ""))
            args = cfg.get("args", [])
            if isinstance(args, list) and args:
                service["args_preview"] = [str(a) for a in args[:ARGS_PREVIEW_COUNT]]

        # http / sse 类型：有 url
        elif "url" in cfg:
            service["transport"] = "http/sse"
            service["url"] = clean_url(str(cfg.get("url", "")))

        else:
            service["transport"] = "unknown"

        services.append(service)

    return services


def scan(whitelist_path: Path) -> dict:
    """执行扫描，返回结构化结果。"""
    with open(whitelist_path, "r", encoding="utf-8") as f:
        whitelist = json.load(f)

    results = []

    for entry in whitelist.get("paths", []):
        tool = entry.get("tool", "unknown")
        raw_path = entry.get("path", "")
        path = expand_path(raw_path)

        item = {
            "tool": tool,
            "path": str(path),
            "exists": path.exists(),
            "services": [],
            "error": None,
        }

        if not path.exists():
            results.append(item)
            continue

        try:
            with open(path, "r", encoding="utf-8") as f:
                config = json.load(f)
            item["services"] = extract_services(config)

        except json.JSONDecodeError as e:
            item["error"] = f"JSON 解析失败: {e}"
        except PermissionError:
            item["error"] = "权限不足，无法读取"
        except UnicodeDecodeError:
            item["error"] = "文件编码不是 UTF-8，跳过"
        except Exception as e:
            item["error"] = f"未知错误: {type(e).__name__}: {e}"

        results.append(item)

    return {
        "scanned_at": datetime.now().isoformat(timespec="seconds"),
        "whitelist_source": str(whitelist_path),
        "results": results,
    }


def main() -> int:
    # 默认白名单路径：脚本所在目录的上一级 / examples / whitelist.json
    script_dir = Path(__file__).resolve().parent
    default_whitelist = script_dir.parent / "examples" / "whitelist.json"

    whitelist_path = Path(sys.argv[1]) if len(sys.argv) > 1 else default_whitelist

    if not whitelist_path.exists():
        print(f"错误：找不到白名单文件 {whitelist_path}", file=sys.stderr)
        return 1

    try:
        output = scan(whitelist_path)
    except Exception as e:
        print(f"扫描失败: {type(e).__name__}: {e}", file=sys.stderr)
        return 2

    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())