#!/usr/bin/env python3
"""
Fast static regression checks for the SaaS guardrails.

This script intentionally uses only the Python standard library so it can run in
minimal deploy/debug environments before full dependencies are installed.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    contests = read("web/api/contests.py")
    publish = read("web/api/publish.py")
    billing = read("web/api/billing.py")
    admin = read("web/api/admin.py")
    bot_contest = read("bot/handlers/contest.py")

    for function_name in (
        "check_subscription",
        "auto_check",
        "register_participant",
        "get_results_info",
    ):
        marker = f"async def {function_name}("
        start = contests.find(marker)
        require(start != -1, f"Missing contests endpoint: {function_name}")
        next_function = contests.find("\nasync def ", start + len(marker))
        block = contests[start: next_function if next_function != -1 else len(contests)]
        require("verify_telegram_user" in block, f"{function_name} must validate Telegram initData")

    require("def require_owned_contest" in publish, "Publish API must keep contest ownership guard")
    require("require_owned_contest(contest, user_id)" in publish, "Publish endpoints must enforce contest ownership")
    require("PAYKASSA_WEBHOOK_SECRET" in billing, "PayKassa webhook must keep optional signature guard")
    require("expected_amount=expected_amount" in billing, "PayKassa webhook must validate payment amount")
    require("expected_currency=expected_currency" in billing, "PayKassa webhook must validate payment currency")
    require("async def delete_contest" in admin, "Admin API must expose contest deletion")
    require("require_owned(contest, admin_id" in admin, "Admin contest actions must enforce ownership")
    require("build_public_media_url" in bot_contest, "Bot publication must support public media URL fallback")

    print("security regression checks passed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"security regression check failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
