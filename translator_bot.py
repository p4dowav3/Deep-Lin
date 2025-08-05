import discord
import os
import deepl
import flag
from dotenv import load_dotenv
from discord.ext import commands

# Load environment variables from .env file
load_dotenv()

# Get tokens and API keys from environment variables
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DEEPL_AUTH_KEY = os.getenv("DEEPL_AUTH_KEY")

# Initialize DeepL translator client
try:
    translator = deepl.Translator(DEEPL_AUTH_KEY)
except Exception as e:
    print(f"DeepL API key is invalid or not set: {e}")
    exit()

# Set intents so the bot can read message content
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Map flag emojis to DeepL language codes
# Check supported language codes at https://www.deepl.com/docs-api/translate-text/translate-text/
FLAG_TO_LANGUAGE = {
    "KR": "KO",
    "US": "EN-US",
    "GB": "EN-GB",
    "JP": "JA",
    "CN": "ZH",
    "DE": "DE",
    "FR": "FR",
    "ES": "ES",
    "IT": "IT",
    "RU": "RU",
    "PT": "PT-PT", # Portugal
    "BR": "PT-BR", # Brazil
}

@bot.event
async def on_ready():
    """Event called when the bot is ready"""
    print(f"Logged in as {bot.user}!")
    print("Bot has been successfully activated.")
    print("-" * 20)

@bot.slash_command(name="translate", description="Translate text to specified language.")
async def translate_command(
    ctx: discord.ApplicationContext,
    text: discord.Option(str, description="Enter text to translate."),
    target_language: discord.Option(str, description="Target language code (e.g., KO, EN-US, JA)")
):
    """Translate text using slash command."""
    try:
        # Translate text using DeepL API
        result = translator.translate_text(text, target_lang=target_language.upper())
        
        embed = discord.Embed(title="🌐 Translation Result", color=discord.Color.blue())
        embed.add_field(name="Original Text", value=f"```{text}```", inline=False)
        embed.add_field(name=f"Translated Text ({result.detected_source_lang} -> {target_language.upper()})", 
                        value=f"```{result.text}```", inline=False)
        
        await ctx.respond(embed=embed, delete_after=60)

    except deepl.DeepLException as e:
        await ctx.respond(f"Translation error occurred: {e}", ephemeral=True)
    except Exception as e:
        await ctx.respond(f"Unknown error occurred: {e}", ephemeral=True)

@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    """Event called when reaction is added to message (detects reactions even when bot was offline)"""
    # Ignore bot's own reactions
    if payload.user_id == bot.user.id:
        return

    try:
        # Get channel and message objects where reaction was added
        channel = await bot.fetch_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        
        # Ignore if original message content is empty
        if not message.content:
            return
            
        emoji_char = str(payload.emoji)
        
        # Check if emoji is a flag and extract country code
        country_code = flag.dflagize(emoji_char).strip(":").upper()

        # Check if there's a mapped language code
        target_lang = FLAG_TO_LANGUAGE.get(country_code)

        if target_lang:
            result = translator.translate_text(message.content, target_lang=target_lang)
            
            # Reply only if translation is different from original
            if result.text.strip() and result.text.lower() != message.content.lower():
                await message.reply(f"**🌐 {result.detected_source_lang} → {target_lang} Translation:**\n{result.text}")

    except deepl.DeepLException as e:
        print(f"DeepL API error: {e}")
    except KeyError:
        # Ignore if not a flag emoji or not mapped
        pass
    except Exception as e:
        print(f"Error processing reaction: {e}")

# Run bot
if DISCORD_TOKEN and DEEPL_AUTH_KEY:
    bot.run(DISCORD_TOKEN)
else:
    print("DISCORD_TOKEN or DEEPL_AUTH_KEY environment variable is not set.")
