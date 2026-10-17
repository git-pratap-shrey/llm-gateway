#!/usr/bin/env python3
"""
check_keys.py — Pre-flight health and status check for all provider API keys.

Verifies connectivity, authentication, and completion capability across
all configured API keys in .env (Ollama Cloud, Gemini, OpenRouter).

Usage:
    ./check_keys.py                                   # Full completion test for all provider keys
    ./check_keys.py --fast                            # Fast auth/models check only (<2s)
    ./check_keys.py --provider ollama                 # Test only Ollama keys
    ./check_keys.py --provider gemini                 # Test only Gemini key
    ./check_keys.py --provider openrouter             # Test only OpenRouter key
    ./check_keys.py --provider ollama --fast          # Quick auth check for Ollama keys only
    ./check_keys.py --timeout 30                      # Set custom timeout per request in seconds
    ./check_keys.py --env-file /path/to/.env          # Specify custom .env file path

Alternative with uv:
    uv run python check_keys.py
    uv run python check_keys.py --fast
    uv run python check_keys.py --provider ollama

Exit Codes:
    0 — All tested keys are operational
    1 — One or more keys failed or timed out
"""

import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Optional

try:
    from dotenv import dotenv_values
except ImportError:
    def dotenv_values(env_path: str = ".env") -> dict[str, str]:
        env_dict = {}
        if not os.path.exists(env_path):
            return env_dict
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip("'\"")
                env_dict[k] = v
        return env_dict

# ANSI Colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


@dataclass
class KeyCheckResult:
    provider: str
    key_idx: int
    masked_key: str
    status_code: str
    latency_sec: float
    message: str
    is_ok: bool


def mask_key(key: str) -> str:
    key = key.strip()
    if len(key) <= 10:
        return "***"
    return f"{key[:6]}...{key[-4:]}"


def test_ollama_key(key: str, idx: int, fast: bool, timeout: int) -> KeyCheckResult:
    masked = mask_key(key)
    t0 = time.time()

    if fast:
        # Quick auth/models check
        cmd = [
            "curl", "-s", "-w", "\n%{http_code}",
            "-m", str(timeout),
            "https://ollama.com/v1/models",
            "-H", f"Authorization: Bearer {key}",
        ]
    else:
        # Full completion check
        payload = json.dumps({
            "model": "gemma4:cloud",
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 5,
        })
        cmd = [
            "curl", "-s", "-w", "\n%{http_code}",
            "-m", str(timeout),
            "https://ollama.com/v1/chat/completions",
            "-H", f"Authorization: Bearer {key}",
            "-H", "Content-Type: application/json",
            "-d", payload,
        ]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5)
        elapsed = time.time() - t0
        lines = res.stdout.strip().rsplit("\n", 1)
        body = lines[0] if len(lines) > 1 else ""
        code = lines[-1].strip() if lines else "unknown"

        if code == "200":
            if fast:
                msg = "Auth OK (/v1/models)"
            else:
                try:
                    data = json.loads(body)
                    msg = data["choices"][0]["message"]["content"].strip().replace("\n", " ")
                except Exception:
                    msg = "Completed (200 OK)"
            return KeyCheckResult("ollama_cloud", idx, masked, code, elapsed, msg, True)
        else:
            try:
                data = json.loads(body)
                err = data.get("error", {})
                err_msg = err.get("message") if isinstance(err, dict) else str(err)
            except Exception:
                err_msg = body[:60]
            return KeyCheckResult("ollama_cloud", idx, masked, code, elapsed, err_msg or "Failed", False)

    except subprocess.TimeoutExpired:
        return KeyCheckResult("ollama_cloud", idx, masked, "TIMEOUT", timeout, f"Timed out after {timeout}s", False)
    except Exception as e:
        return KeyCheckResult("ollama_cloud", idx, masked, "ERROR", time.time() - t0, str(e), False)


def test_gemini_key(key: str, idx: int, fast: bool, timeout: int) -> KeyCheckResult:
    masked = mask_key(key)
    t0 = time.time()

    if fast:
        cmd = [
            "curl", "-s", "-w", "\n%{http_code}",
            "-m", str(timeout),
            "https://generativelanguage.googleapis.com/v1beta/openai/models",
            "-H", f"Authorization: Bearer {key}",
        ]
    else:
        payload = json.dumps({
            "model": "gemma-4-31b-it",
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 5,
        })
        cmd = [
            "curl", "-s", "-w", "\n%{http_code}",
            "-m", str(timeout),
            "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
            "-H", f"Authorization: Bearer {key}",
            "-H", "Content-Type: application/json",
            "-d", payload,
        ]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5)
        elapsed = time.time() - t0
        lines = res.stdout.strip().rsplit("\n", 1)
        body = lines[0] if len(lines) > 1 else ""
        code = lines[-1].strip() if lines else "unknown"

        if code == "200":
            if fast:
                msg = "Auth OK (/v1beta/openai/models)"
            else:
                try:
                    data = json.loads(body)
                    msg = data["choices"][0]["message"]["content"].strip().replace("\n", " ")
                except Exception:
                    msg = "Completed (200 OK)"
            return KeyCheckResult("gemini", idx, masked, code, elapsed, msg, True)
        else:
            return KeyCheckResult("gemini", idx, masked, code, elapsed, body[:60] or "Failed", False)

    except subprocess.TimeoutExpired:
        return KeyCheckResult("gemini", idx, masked, "TIMEOUT", timeout, f"Timed out after {timeout}s", False)
    except Exception as e:
        return KeyCheckResult("gemini", idx, masked, "ERROR", time.time() - t0, str(e), False)


def test_openrouter_key(key: str, idx: int, fast: bool, timeout: int) -> KeyCheckResult:
    masked = mask_key(key)
    t0 = time.time()

    if fast:
        cmd = [
            "curl", "-s", "-w", "\n%{http_code}",
            "-m", str(timeout),
            "https://openrouter.ai/api/v1/models",
            "-H", f"Authorization: Bearer {key}",
        ]
    else:
        payload = json.dumps({
            "model": "google/gemma-4-31b-it:free",
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 5,
        })
        cmd = [
            "curl", "-s", "-w", "\n%{http_code}",
            "-m", str(timeout),
            "https://openrouter.ai/api/v1/chat/completions",
            "-H", f"Authorization: Bearer {key}",
            "-H", "Content-Type: application/json",
            "-d", payload,
        ]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5)
        elapsed = time.time() - t0
        lines = res.stdout.strip().rsplit("\n", 1)
        body = lines[0] if len(lines) > 1 else ""
        code = lines[-1].strip() if lines else "unknown"

        if code == "200":
            if fast:
                msg = "Auth OK (/api/v1/models)"
            else:
                try:
                    data = json.loads(body)
                    msg = data["choices"][0]["message"]["content"].strip().replace("\n", " ")
                except Exception:
                    msg = "Completed (200 OK)"
            return KeyCheckResult("openrouter", idx, masked, code, elapsed, msg, True)
        else:
            return KeyCheckResult("openrouter", idx, masked, code, elapsed, body[:60] or "Failed", False)

    except subprocess.TimeoutExpired:
        return KeyCheckResult("openrouter", idx, masked, "TIMEOUT", timeout, f"Timed out after {timeout}s", False)
    except Exception as e:
        return KeyCheckResult("openrouter", idx, masked, "ERROR", time.time() - t0, str(e), False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check status and health of LLM Gateway provider API keys.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--provider",
        choices=["all", "ollama", "gemini", "openrouter"],
        default="all",
        help="Provider to check (default: all).",
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Quick check (/models endpoint only, ~1-2s). If omitted, tests full completion.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Timeout in seconds per key check (default: 60s for completion, 15s for --fast).",
    )
    parser.add_argument(
        "--env-file",
        default=".env",
        help="Path to .env file (default: .env).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    timeout = 15 if args.fast and args.timeout == 60 else args.timeout

    env = dotenv_values(args.env_file)
    if not env:
        print(f"{RED}Error: Could not load '{args.env_file}' or file is empty.{RESET}")
        sys.exit(1)

    ollama_keys = [k.strip() for k in env.get("OLLAMA_API_KEY", "").split(",") if k.strip()]
    gemini_keys = [k.strip() for k in env.get("GEMINI_API_KEY", "").split(",") if k.strip()]
    openrouter_keys = [k.strip() for k in env.get("OPENROUTER_API_KEY", "").split(",") if k.strip()]

    tasks = []

    if args.provider in ("all", "ollama"):
        for i, k in enumerate(ollama_keys, 1):
            tasks.append(("ollama", k, i))

    if args.provider in ("all", "gemini"):
        for i, k in enumerate(gemini_keys, 1):
            tasks.append(("gemini", k, i))

    if args.provider in ("all", "openrouter"):
        for i, k in enumerate(openrouter_keys, 1):
            tasks.append(("openrouter", k, i))

    if not tasks:
        print(f"{YELLOW}No keys found for provider '{args.provider}' in {args.env_file}.{RESET}")
        sys.exit(0)

    mode_label = "Quick Auth Check (/models)" if args.fast else "Full Completion Test"
    print(f"\n{BOLD}{CYAN}=== LLM Gateway API Key Health Check ==={RESET}")
    print(f"Mode:     {BOLD}{mode_label}{RESET}")
    print(f"Env file: {args.env_file}")
    print(f"Testing:  {len(tasks)} key(s) in parallel...\n")

    def run_task(task):
        provider, key, idx = task
        if provider == "ollama":
            return test_ollama_key(key, idx, args.fast, timeout)
        elif provider == "gemini":
            return test_gemini_key(key, idx, args.fast, timeout)
        elif provider == "openrouter":
            return test_openrouter_key(key, idx, args.fast, timeout)

    with ThreadPoolExecutor(max_workers=max(1, len(tasks))) as executor:
        results = list(executor.map(run_task, tasks))

    # Print Table
    header = f"{'PROVIDER':<14} {'KEY #':<7} {'MASKED KEY':<18} {'STATUS':<10} {'TIME':<8} {'DETAILS / RESPONSE'}"
    print(BOLD + header + RESET)
    print("-" * 88)

    ok_count = 0
    for r in results:
        status_color = GREEN if r.is_ok else RED
        status_str = f"{status_color}{r.status_code:<10}{RESET}"
        time_str = f"{r.latency_sec:.2f}s"
        msg_preview = r.message[:38]
        print(f"{r.provider:<14} #{r.key_idx:<6} {r.masked_key:<18} {status_str} {time_str:<8} {msg_preview}")
        if r.is_ok:
            ok_count += 1

    print("-" * 88)
    summary_color = GREEN if ok_count == len(results) else (YELLOW if ok_count > 0 else RED)
    print(f"\n{summary_color}{BOLD}Summary: {ok_count}/{len(results)} keys operational.{RESET}\n")

    sys.exit(0 if ok_count == len(results) else 1)


if __name__ == "__main__":
    main()
