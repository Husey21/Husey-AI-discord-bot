# Husey Ai

Bot Discord IA complet avec commandes slash, boutons interactifs, conversations persistantes par utilisateur et salon, réponses longues découpées automatiquement, et génération d'images.

## Installation

1. Crée une application sur le [Discord Developer Portal](https://discord.com/developers/applications), ajoute un bot, invite-le avec les scopes `bot` et `applications.commands`, puis active **Message Content Intent** dans l'onglet Bot.
2. Copie `.env.example` vers `.env`, puis renseigne `DISCORD_TOKEN` et `OPENAI_API_KEY`.
3. Installe les dépendances :

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

4. Lance le bot :

```powershell
python bot.py
```

`DEV_GUILD_ID` permet de synchroniser les commandes instantanément sur un serveur de test. Sans cette variable, la synchronisation globale Discord peut prendre quelques minutes.

## Commandes

- `/ask` : question avec mémoire de conversation.
- `/image` : génération d'une image via le modèle configuré.
- `/language` : choisit Français, English, Español, Italiano, Deutsch ou Русский.
- `/dm` : envoie un espace de conversation privé au membre.
- `/panel` : panneau avec boutons Question, Image, Effacer et Aide.
- `/clear` : efface la conversation du membre dans le salon courant.
- `/help`, `/ping`, `/about` : aide et diagnostic.

Le bot accepte un endpoint compatible OpenAI via `OPENAI_BASE_URL`, ce qui permet d'utiliser OpenAI, OpenRouter ou un autre fournisseur compatible. Ne partage jamais le fichier `.env`.

Dans un salon, mentionne `@Husey Ai` pour obtenir une réponse automatique. En DM, chaque message est traité comme une question et conserve son propre contexte. Les réponses automatiques sont limitées à une demande toutes les 8 secondes par membre.

La langue choisie est conservée par membre dans SQLite et s'applique aux commandes, aux mentions et aux conversations privées. Le menu de langue est également disponible après `/panel`.
