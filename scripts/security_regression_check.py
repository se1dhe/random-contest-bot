#!/usr/bin/env python3
"""
Fast static regression checks for self-hosted bot guardrails.

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
    admin = read("web/api/admin.py")
    deps = read("web/api/deps.py")
    bot_main = read("bot/main.py")
    web_main = read("web/main.py")
    bot_contest = read("bot/handlers/contest.py")
    bot_forum_topics = read("bot/handlers/forum_topics.py")

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
    require("config.is_admin(auth_user_id)" in deps, "Admin access must be limited to configured ADMIN_ID(S)")
    require("has_active_subscription" not in deps, "Admin access must not depend on paid subscriptions")
    require("billing.router" not in bot_main, "Bot must not expose subscription payment commands")
    require("billing.router" not in web_main, "Web app must not expose billing API routes")
    require("async def delete_contest" in admin, "Admin API must expose contest deletion")
    require("require_owned(contest, admin_id" in admin, "Admin contest actions must enforce ownership")
    require("get_subscription_status" not in admin, "Admin API must not enforce paid subscription plans")
    require("build_public_media_url" in bot_contest, "Bot publication must support public media URL fallback")
    require("ForumTopicRecorderMiddleware" in bot_forum_topics, "Forum topics must be recorded silently before handlers")
    require('Command("topic")' not in bot_forum_topics, "Forum topic recording must not expose a public /topic command")
    require("message_thread_id" in bot_forum_topics, "Forum topic registration must keep Telegram thread ID")

    print("security regression checks passed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"security regression check failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
