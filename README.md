# Nemo Webex Bot

Bot Cisco Webex connecte a un LLM (OVH gpt-oss-120b) avec acces a des outils MCP (Model Context Protocol).
Les utilisateurs discutent en langage naturel avec Nemo directement depuis Webex — pas de commandes, pas de slash commands.

## Architecture

```
Webex Cloud  <--websocket-->  Bot Python (10.1.0.55)
                                   |
                                   |-- OVH LLM (gpt-oss-120b) via HTTPS
                                   |      endpoint OpenAI-compatible
                                   |
                                   +-- MCP SSE --> Nemo v2 (10.1.0.61)
                                          |-- horloge    :7001  (date, heure)
                                          |-- photovoltaic :7002 (production solaire)
                                          |-- legifrance :7003  (droit francais)
                                          |-- weather    :7004  (meteo WeatherKit)
                                          +-- websearch  :7005  (recherche Tavily)
```

### Flux d un message

1. L utilisateur envoie un message dans Webex (DM ou mention du bot)
2. Le bot recoit le message via websocket (pas de webhook, pas d IP publique)
3. Le message + historique sont envoyes au LLM OVH (gpt-oss-120b)
4. Si le LLM decide d utiliser un outil, le bot appelle le serveur MCP concerne via SSE
5. Le resultat de l outil est renvoye au LLM pour synthetiser la reponse
6. La reponse finale est postee dans Webex

### Composants

| Fichier | Role |
|---------|------|
| `bot.py` | Point d entree, initialise le bot Webex et la boucle async MCP |
| `config.py` | Configuration (tokens, URLs MCP, system prompt) |
| `mcp_client.py` | Client MCP SSE (connexion persistante aux 5 serveurs) |
| `llm_client.py` | Client LLM OVH avec boucle de tool calling (max 5 iterations) |
| `bot.env` | Variables d environnement (tokens secrets, non versionne) |

### Dependances techniques

- **webex-bot** : Connexion websocket a Webex (auto-reconnect, device registration)
- **mcp** (SDK Python) : Client MCP SSE pour appeler les outils
- **httpx** : Appels HTTP async vers l API LLM OVH
- **python-dotenv** : Chargement du fichier bot.env

## Installation

### Prerequis

- Python 3.10+
- Acces reseau aux serveurs MCP (10.1.0.61:7001-7005)
- Acces HTTPS sortant vers Webex Cloud et OVH AI Endpoints
- Un bot Webex enregistre sur https://developer.webex.com

### 1. Cloner le projet

```bash
git clone https://github.com/9tf48t8hyx-hash/nemo-webex-bot.git
cd nemo-webex-bot
```

### 2. Installer les dependances

```bash
pip3 install --break-system-packages webex-bot httpx mcp python-dotenv
```

### 3. Configurer les secrets

Creer un fichier `bot.env` (non versionne) :

```
WEBEX_BOT_TOKEN=<token du bot Webex>
OVH_TOKEN=<token API OVH AI Endpoints>
```

### 4. Adapter la configuration

Editer `config.py` si necessaire :
- `MCP_SERVERS` : URLs des serveurs MCP
- `OVH_API_URL` / `OVH_MODEL` : endpoint et modele LLM
- `SYSTEM_PROMPT` : personnalite et instructions du bot
- `MAX_HISTORY` : nombre de messages gardes en memoire par utilisateur

### 5. Lancer manuellement (test)

```bash
PYTHONUNBUFFERED=1 python3 bot.py
```

### 6. Deployer en service systemd

```bash
sudo cp nemo-webex-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now nemo-webex-bot
```

Fichier `nemo-webex-bot.service` fourni dans le repo.

## Outils MCP disponibles

| Outil | Serveur | Description |
|-------|---------|-------------|
| `get_current_time` | horloge | Heure actuelle (fuseau configurable) |
| `get_current_date` | horloge | Date du jour en francais |
| `get_weather_forecast` | weather | Previsions meteo (Apple WeatherKit) |
| `get_weather_today` | weather | Meteo du jour |
| `get_solar_production` | photovoltaic | Production PV d une date |
| `get_solar_sites` | photovoltaic | Liste des sites PV |
| `get_solar_hourly` | photovoltaic | Production horaire detaillee |
| `get_solar_week_summary` | photovoltaic | Resume 7 jours |
| `search_legifrance` | legifrance | Recherche droit francais |
| `list_codes` | legifrance | Liste des codes juridiques |
| `get_article` | legifrance | Texte d un article de loi |
| `web_search` | websearch | Recherche Internet (Tavily) |

## Maintenance

### Logs

```bash
# Suivre les logs en temps reel
journalctl -u nemo-webex-bot -f

# Logs des 100 dernieres lignes
journalctl -u nemo-webex-bot -n 100 --no-pager
```

### Redemarrage

```bash
sudo systemctl restart nemo-webex-bot
```

### Statut

```bash
systemctl status nemo-webex-bot
```

### Problemes courants

**Le bot ne repond pas**
1. Verifier que le service tourne : `systemctl is-active nemo-webex-bot`
2. Verifier les logs pour des erreurs MCP ou LLM
3. Verifier la connectivite vers les serveurs MCP : `curl -s http://10.1.0.61:7001/sse`
4. Verifier la connectivite vers OVH : `curl -s https://oai.endpoints.kepler.ai.cloud.ovh.net/`

**Erreur 421 sur les serveurs MCP**
Les serveurs MCP FastMCP ont une protection DNS rebinding. Si de nouveaux serveurs sont ajoutes,
desactiver la protection dans le bloc `if __name__` :
```python
from mcp.server.transport_security import TransportSecuritySettings
mcp.settings.transport_security = TransportSecuritySettings(enable_dns_rebinding_protection=False)
```

**Le bot se deconnecte de Webex**
Normal — webex-bot gere la reconnexion automatique avec backoff. Verifier les logs.

**Reponses lentes**
Le LLM OVH peut prendre 2-5s par iteration. Si des outils sont appeles, compter 1-2s supplementaires
par outil. Le timeout global est de 120s.

### Ajouter un serveur MCP

1. Deployer le nouveau serveur MCP SSE sur Nemo v2 (10.1.0.61)
2. Ajouter l entree dans `config.py` > `MCP_SERVERS`
3. Mettre a jour le `SYSTEM_PROMPT` pour decrire les nouveaux outils
4. Redemarrer : `sudo systemctl restart nemo-webex-bot`
