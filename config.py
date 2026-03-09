import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "bot.env"))

# Webex
WEBEX_BOT_TOKEN = os.getenv("WEBEX_BOT_TOKEN", "")

# OVH LLM
OVH_API_URL = "https://oai.endpoints.kepler.ai.cloud.ovh.net/v1/chat/completions"
OVH_MODEL = "gpt-oss-120b"
OVH_TOKEN = os.getenv("OVH_TOKEN", "")

# MCP Servers (Nemo v2 — 10.1.0.61)
MCP_SERVERS = {
    "horloge":      "http://10.1.0.61:7001/sse",
    "photovoltaic": "http://10.1.0.61:7002/sse",
    "legifrance":   "http://10.1.0.61:7003/sse",
    "weather":      "http://10.1.0.61:7004/sse",
    "websearch":    "http://10.1.0.61:7005/sse",
}

# LLM System Prompt
SYSTEM_PROMPT = """Tu es Nemo, un assistant intelligent accessible via Webex. Tu disposes des outils suivants :

- web_search : pour faire des recherches sur Internet (actualites, evenements recents, faits)
- get_current_date : pour obtenir la date du jour
- get_current_time : pour obtenir l heure actuelle
- get_weather_forecast : pour obtenir les previsions meteo d une ville
- get_weather_today : pour obtenir la meteo du jour d une ville
- get_solar_production : pour obtenir la production photovoltaique d une date (format YYYY-MM-DD)
- get_solar_sites : pour lister les sites photovoltaiques disponibles
- get_solar_hourly : pour obtenir la production horaire detaillee
- get_solar_week_summary : pour obtenir un resume de production sur 7 jours

Utilise ces outils quand c est pertinent pour repondre aux questions de l utilisateur.
Reponds de maniere concise et utile. Formate en texte simple (pas de HTML)."""

# Conversation
MAX_HISTORY = 20
