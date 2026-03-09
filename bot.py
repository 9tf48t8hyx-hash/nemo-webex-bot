#!/usr/bin/env python3
"""
Nemo Webex Bot -- Bot LLM + MCP pour Webex.
Recoit les messages via websocket, repond via OVH LLM (gpt-oss-120b)
avec acces aux outils MCP de Nemo v2.
"""
import asyncio
import threading
import sys
import os
from collections import defaultdict

from webex_bot.webex_bot import WebexBot
from webex_bot.models.command import Command

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from mcp_client import MCPManager
from llm_client import call_llm

# Boucle asyncio dediee (background thread) pour MCP + LLM
_loop = asyncio.new_event_loop()
_mcp_manager = MCPManager()

# Historique des conversations par utilisateur
conversations: dict[str, list[dict]] = defaultdict(list)


def _start_async_loop():
    asyncio.set_event_loop(_loop)
    _loop.run_forever()


def run_async(coro, timeout=120):
    """Execute une coroutine dans la boucle background et attend le resultat."""
    future = asyncio.run_coroutine_threadsafe(coro, _loop)
    return future.result(timeout=timeout)


class LLMCommand(Command):
    """Commande par defaut : route tous les messages vers le LLM."""

    def __init__(self):
        super().__init__(
            command_keyword="",
            help_message="Pose-moi n importe quelle question !",
            card=None,
        )

    def execute(self, message, attachment_actions, activity):
        user_email = activity.get("actor", {}).get("id", "unknown")
        user_message = message.strip()
        if not user_message:
            return "Je suis Nemo, ton assistant IA. Pose-moi une question !"

        print(f"[BOT] Message de {user_email}: {user_message[:80]}")

        # Historique
        history = conversations[user_email]
        history.append({"role": "user", "content": user_message})
        if len(history) > config.MAX_HISTORY:
            conversations[user_email] = history[-config.MAX_HISTORY:]
            history = conversations[user_email]

        # Appel LLM via la boucle async background
        try:
            response = run_async(call_llm(history, _mcp_manager))
        except Exception as e:
            print(f"[BOT] Erreur LLM: {e}")
            response = f"Erreur lors du traitement : {e}"

        print(f"[BOT] Reponse: {response[:80]}")
        history.append({"role": "assistant", "content": response})

        # Limite Webex (~7000 chars)
        if len(response) > 6500:
            response = response[:6500] + "\n\n[... reponse tronquee]"

        return response


async def init_mcp():
    """Connecte tous les serveurs MCP."""
    for name, url in config.MCP_SERVERS.items():
        try:
            await _mcp_manager.connect_server(name, url)
        except Exception as e:
            print(f"[MCP] Erreur connexion {name} ({url}): {e}")
    tools = _mcp_manager.get_all_tool_names()
    print(f"[MCP] {len(tools)} outils disponibles: {tools}")


def main():
    print("[BOT] Demarrage Nemo Webex Bot...")

    # Demarrer la boucle async en background
    thread = threading.Thread(target=_start_async_loop, daemon=True)
    thread.start()

    # Initialiser MCP dans la boucle background
    run_async(init_mcp(), timeout=30)

    # Creer le bot Webex — LLMCommand comme help_command (= fallback par defaut)
    asyncio.set_event_loop(asyncio.new_event_loop())

    bot = WebexBot(
        teams_bot_token=config.WEBEX_BOT_TOKEN,
        bot_name="Nemo",
        include_demo_commands=False,
        help_command=LLMCommand(),
    )

    print("[BOT] Bot pret, connexion websocket Webex...")
    bot.run()


if __name__ == "__main__":
    main()
