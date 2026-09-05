import logging
import time
from collections import defaultdict

import discord
from discord import app_commands
from discord.ext import commands

from ai_service import AIService
from config import Settings, load_settings
from database import Database

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("husey-ai")

LANGUAGES = {
    "en": "English",
    "fr": "Français",
    "es": "Español",
    "it": "Italiano",
    "de": "Deutsch",
    "ru": "Русский",
}


class AskModal(discord.ui.Modal, title="Poser une question à Husey Ai"):
    question = discord.ui.TextInput(
        label="Votre question",
        placeholder="Explique-moi clairement...",
        style=discord.TextStyle.paragraph,
        max_length=4000,
        required=True,
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(thinking=True)
        await interaction.client.handle_question(interaction, str(self.question))


class ImageModal(discord.ui.Modal, title="Créer une image"):
    prompt = discord.ui.TextInput(
        label="Description de l'image",
        placeholder="Un château futuriste au coucher du soleil, style cinématographique",
        style=discord.TextStyle.paragraph,
        max_length=1000,
        required=True,
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(thinking=True)
        await interaction.client.handle_image(interaction, str(self.prompt))


class ControlPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Question", emoji="💬", style=discord.ButtonStyle.primary, custom_id="husey:ask")
    async def ask(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_modal(AskModal())

    @discord.ui.button(label="Image", emoji="🎨", style=discord.ButtonStyle.success, custom_id="husey:image")
    async def image(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_modal(ImageModal())

    @discord.ui.button(label="Effacer", emoji="🧹", style=discord.ButtonStyle.secondary, custom_id="husey:clear")
    async def clear(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.client.db.clear_context(interaction.user.id, interaction.channel_id)
        await interaction.response.send_message("Ta conversation a été effacée.", ephemeral=True)

    @discord.ui.button(label="Aide", emoji="❔", style=discord.ButtonStyle.secondary, custom_id="husey:help")
    async def help(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_message(embed=help_embed(), ephemeral=True)


class DMPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Générer une image", emoji="🎨", style=discord.ButtonStyle.success, custom_id="husey:dm-image")
    async def image(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_modal(ImageModal())

    @discord.ui.button(label="Effacer ma mémoire", emoji="🧹", style=discord.ButtonStyle.secondary, custom_id="husey:dm-clear")
    async def clear(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.client.db.clear_context(interaction.user.id, interaction.channel_id)
        await interaction.response.send_message("Ta mémoire de conversation privée a été effacée.", ephemeral=True)


class LanguageSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=label, value=code, emoji=emoji, description=f"Répondre en {label}")
            for code, label, emoji in [
                ("fr", "Français", "🇫🇷"), ("en", "English", "🇬🇧"), ("es", "Español", "🇪🇸"),
                ("it", "Italiano", "🇮🇹"), ("de", "Deutsch", "🇩🇪"), ("ru", "Русский", "🇷🇺"),
            ]
        ]
        super().__init__(placeholder="Choisir la langue de réponse", options=options, custom_id="husey:language")

    async def callback(self, interaction: discord.Interaction) -> None:
        language = self.values[0]
        await interaction.client.db.set_language(interaction.user.id, language)
        await interaction.response.send_message(f"Langue sélectionnée : **{LANGUAGES[language]}**.", ephemeral=True)


class LanguageView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(LanguageSelect())


def help_embed() -> discord.Embed:
    embed = discord.Embed(title="Husey Ai | Centre de commandes", color=discord.Color.blurple())
    embed.description = "Un assistant IA polyvalent directement dans Discord."
    embed.add_field(name="IA", value="`/ask` pose une question et garde le contexte.\n`/image` crée une image.", inline=False)
    embed.add_field(name="Conversation", value="`/clear` efface ton contexte.\n`/dm` ouvre une conversation privée.", inline=False)
    embed.add_field(name="Automatique", value="Mentionne Husey Ai dans un salon ou écris-lui en DM.", inline=False)
    embed.add_field(name="Langue", value="Choisis Français, English, Español, Italiano, Deutsch ou Русский dans le menu.", inline=False)
    embed.add_field(name="Utilitaires", value="`/ping` vérifie la latence.\n`/about` affiche l'état du bot.", inline=False)
    embed.set_footer(text="Husey Ai • Respecte les règles de ton serveur et les conditions du fournisseur IA")
    return embed


class HuseyBot(commands.Bot):
    def __init__(self, settings: Settings):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
        self.settings = settings
        self.db = Database(settings.database_path)
        self.ai = AIService(settings)
        self.cooldowns: dict[int, float] = defaultdict(float)

    async def setup_hook(self) -> None:
        await self.db.initialize()
        self.add_view(ControlPanel())
        self.add_view(DMPanel())
        self.add_view(LanguageView())
        if self.settings.dev_guild_id:
            guild = discord.Object(id=self.settings.dev_guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            log.info("Commandes synchronisées sur le serveur de développement %s", self.settings.dev_guild_id)
        else:
            await self.tree.sync()

    async def on_ready(self) -> None:
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="/panel | vos questions"))
        log.info("Connecté comme %s (%s)", self.user, self.user.id if self.user else "?")

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return
        if message.guild is None:
            await self.handle_message(message, message.content.strip() or "Bonjour")
        elif self.user and self.user in message.mentions:
            question = message.content.replace(f"<@{self.user.id}>", "").replace(f"<@!{self.user.id}>", "").strip()
            if not question:
                await message.channel.send(
                    f"Je suis là, {message.author.mention} ! En quoi puis-je t'aider ? "
                    "Pose-moi une question ou demande-moi de créer une image avec `/image`."
                )
            else:
                await message.channel.send(f"Je suis là, {message.author.mention} ! Je prépare une réponse...")
                await self.handle_message(message, question)
        await self.process_commands(message)

    def allowed_now(self, user_id: int) -> bool:
        now = time.monotonic()
        if now - self.cooldowns[user_id] < 8:
            return False
        self.cooldowns[user_id] = now
        return True

    async def handle_message(self, message: discord.Message, content: str) -> None:
        if not self.allowed_now(message.author.id):
            await message.channel.send("Patiente quelques secondes avant ta prochaine demande.")
            return
        async with message.channel.typing():
            context = await self.db.get_context(message.author.id, message.channel.id)
            try:
                language = await self.db.get_language(message.author.id)
                answer = await self.ai.answer(content, context, language)
                await self.db.add_message(message.author.id, message.channel.id, "user", content)
                await self.db.add_message(message.author.id, message.channel.id, "assistant", answer)
                await send_message_long(message.channel, answer)
            except Exception:
                log.exception("Erreur pendant une réponse automatique")
                await message.channel.send("Je rencontre un problème avec le service IA. Réessaie dans un instant.")

    async def handle_question(self, interaction: discord.Interaction, question: str) -> None:
        if not self.allowed_now(interaction.user.id):
            await interaction.followup.send("Patiente quelques secondes avant une nouvelle demande.", ephemeral=True)
            return
        context = await self.db.get_context(interaction.user.id, interaction.channel_id)
        language = await self.db.get_language(interaction.user.id)
        try:
            answer = await self.ai.answer(question, context, language)
            await self.db.add_message(interaction.user.id, interaction.channel_id, "user", question)
            await self.db.add_message(interaction.user.id, interaction.channel_id, "assistant", answer)
            await send_long(interaction, answer)
        except Exception:
            log.exception("Erreur pendant une réponse IA")
            await interaction.followup.send("Le service IA est momentanément indisponible. Vérifie la configuration de la clé API.", ephemeral=True)

    async def handle_image(self, interaction: discord.Interaction, prompt: str) -> None:
        if not self.allowed_now(interaction.user.id):
            await interaction.followup.send("Patiente quelques secondes avant une nouvelle demande.", ephemeral=True)
            return
        try:
            url = await self.ai.generate_image(prompt)
            embed = discord.Embed(title="Image générée par Husey Ai", description=f"**Prompt :** {prompt}", color=discord.Color.green())
            embed.set_image(url=url)
            await interaction.followup.send(embed=embed)
        except Exception:
            log.exception("Erreur pendant la génération d'image")
            await interaction.followup.send("La génération d'image a échoué. Vérifie que ton fournisseur prend en charge ce modèle.", ephemeral=True)


async def send_long(interaction: discord.Interaction, content: str) -> None:
    chunks = [content[index:index + 1900] for index in range(0, len(content), 1900)] or ["Réponse vide."]
    await interaction.followup.send(chunks[0])
    for chunk in chunks[1:]:
        await interaction.followup.send(chunk)


settings = load_settings()
bot = HuseyBot(settings)


@bot.tree.command(name="ask", description="Pose une question à Husey Ai")
@app_commands.describe(question="La question ou la tâche à traiter")
async def ask(interaction: discord.Interaction, question: str) -> None:
    await interaction.response.defer(thinking=True)
    await bot.handle_question(interaction, question)


@bot.tree.command(name="image", description="Génère une image à partir d'une description")
@app_commands.describe(prompt="La description de l'image")
async def image(interaction: discord.Interaction, prompt: str) -> None:
    await interaction.response.defer(thinking=True)
    await bot.handle_image(interaction, prompt)


@bot.tree.command(name="language", description="Choisis la langue des réponses de Husey Ai")
@app_commands.describe(language="Langue utilisée par Husey Ai")
@app_commands.choices(language=[app_commands.Choice(name=label, value=code) for code, label in LANGUAGES.items()])
async def language(interaction: discord.Interaction, language: app_commands.Choice[str]) -> None:
    await bot.db.set_language(interaction.user.id, language.value)
    await interaction.response.send_message(f"Husey Ai répondra désormais en **{language.name}**.", ephemeral=True)


@bot.tree.command(name="dm", description="Ouvre une conversation privée avec Husey Ai")
async def dm(interaction: discord.Interaction) -> None:
    try:
        private_channel = await interaction.user.create_dm()
        embed = discord.Embed(
            title="Husey Ai | Conversation privée",
            description=(
                "Bienvenue dans ton espace privé. Écris-moi directement ici pour poser tes questions, "
                "demander de l'aide ou lancer une création."
            ),
            color=discord.Color.blurple(),
        )
        embed.add_field(name="Texte", value="Envoie simplement un message dans ce DM.", inline=False)
        embed.add_field(name="Images", value="Utilise `/image` ici ou le bouton ci-dessous.", inline=False)
        await private_channel.send(embed=embed, view=DMPanel())
        await interaction.response.send_message("Je t'ai envoyé un message privé pour démarrer la conversation.", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("Je ne peux pas t'envoyer de DM. Active les messages privés pour ce serveur.", ephemeral=True)


@bot.tree.command(name="clear", description="Efface ton historique de conversation dans ce salon")
async def clear(interaction: discord.Interaction) -> None:
    await bot.db.clear_context(interaction.user.id, interaction.channel_id)
    await interaction.response.send_message("Historique effacé.", ephemeral=True)


@bot.tree.command(name="panel", description="Affiche le panneau interactif Husey Ai")
async def panel(interaction: discord.Interaction) -> None:
    embed = help_embed()
    embed.title = "Husey Ai | Assistant interactif"
    await interaction.response.send_message(embed=embed, view=ControlPanel())
    await interaction.followup.send("Choisis ta langue de réponse :", view=LanguageView(), ephemeral=True)


@bot.tree.command(name="help", description="Affiche toutes les commandes Husey Ai")
async def help_command(interaction: discord.Interaction) -> None:
    await interaction.response.send_message(embed=help_embed(), ephemeral=True)


@bot.tree.command(name="ping", description="Affiche la latence du bot")
async def ping(interaction: discord.Interaction) -> None:
    await interaction.response.send_message(f"Pong : {round(bot.latency * 1000)} ms", ephemeral=True)


@bot.tree.command(name="about", description="Affiche les informations de Husey Ai")
async def about(interaction: discord.Interaction) -> None:
    embed = discord.Embed(title="Husey Ai", description="Assistant IA Discord avec conversation contextuelle et génération d'images.", color=discord.Color.blurple())
    embed.add_field(name="Modèle texte", value=settings.ai_model)
    embed.add_field(name="Modèle image", value=settings.ai_image_model)
    embed.add_field(name="Serveurs", value=str(len(bot.guilds)))
    await interaction.response.send_message(embed=embed, ephemeral=True)


async def send_message_long(channel: discord.abc.Messageable, content: str) -> None:
    chunks = [content[index:index + 1900] for index in range(0, len(content), 1900)] or ["Réponse vide."]
    for chunk in chunks:
        await channel.send(chunk)


if __name__ == "__main__":
    bot.run(settings.discord_token)
