"""
Client LLM OVH (gpt-oss-120b) avec gestion des appels outils MCP.
Pattern repris de Nemo v2 app_v2.py call_llm().
"""
import json
from datetime import datetime

import httpx

import config
from mcp_client import MCPManager


async def call_llm(history: list[dict], mcp_manager: MCPManager) -> str:
    """
    Appelle le LLM OVH avec l historique de conversation et les outils MCP.
    Retourne la reponse textuelle finale.
    """
    today = datetime.now().strftime("%A %d %B %Y")
    messages = [
        {"role": "system", "content": config.SYSTEM_PROMPT + "\n\nDate du jour : " + today}
    ]
    messages.extend(history)

    openai_tools = mcp_manager.get_openai_tools()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config.OVH_TOKEN}",
    }
    payload = {
        "model": config.OVH_MODEL,
        "messages": messages,
        "max_tokens": 2048,
        "temperature": 0.1,
    }
    if openai_tools:
        payload["tools"] = openai_tools
        payload["tool_choice"] = "auto"

    async with httpx.AsyncClient(timeout=120) as client:
        for iteration in range(5):
            print(f"[LLM] Iteration {iteration + 1}...")
            try:
                resp = await client.post(config.OVH_API_URL, json=payload, headers=headers)
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                return f"Erreur de connexion a l API : {e}"

            if resp.status_code != 200:
                print(f"[LLM] Erreur: {resp.text[:200]}")
                return f"Erreur API: {resp.status_code}"

            data = resp.json()
            choice = data["choices"][0]
            msg = choice["message"]

            if msg.get("tool_calls"):
                # Le LLM veut appeler des outils
                messages.append(msg)
                for tc in msg["tool_calls"]:
                    tool_name = tc["function"]["name"]
                    print(f"[TOOL] Appel: {tool_name}")
                    try:
                        tool_args = json.loads(tc["function"]["arguments"])
                    except json.JSONDecodeError:
                        tool_args = {}
                    result = await mcp_manager.call_tool(tool_name, tool_args)
                    print(f"[TOOL] Resultat: {len(result)} caracteres")
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": result,
                    })
                # Continuer la boucle pour que le LLM synthetise
                payload["messages"] = messages
                continue

            # Reponse directe (pas d appel d outils)
            content = msg.get("content", "")
            return content if content else "Pas de reponse du modele."

    return "Limite d iterations atteinte."
