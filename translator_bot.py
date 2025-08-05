import discord
import os
import deepl
import flag
import json
from dotenv import load_dotenv

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

bot = discord.Bot(intents=intents)

# Dictionary file path
DICTIONARY_FILE = "translation_dictionary.json"

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

def load_dictionary():
    """Load dictionary from JSON file"""
    try:
        with open(DICTIONARY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except Exception as e:
        print(f"Error loading dictionary: {e}")
        return {}

def save_dictionary(dictionary):
    """Save dictionary to JSON file"""
    try:
        with open(DICTIONARY_FILE, 'w', encoding='utf-8') as f:
            json.dump(dictionary, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Error saving dictionary: {e}")
        return False

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
        
        await ctx.respond(embed=embed)

    except deepl.DeepLException as e:
        await ctx.respond(f"Translation error occurred: {e}", ephemeral=True)
    except Exception as e:
        await ctx.respond(f"Unknown error occurred: {e}", ephemeral=True)

@bot.slash_command(name="dict_add", description="Add a word/phrase to the translation dictionary.")
async def dict_add_command(
    ctx: discord.ApplicationContext,
    original: discord.Option(str, description="Original word/phrase"),
    translation: discord.Option(str, description="Translation"),
    language: discord.Option(str, description="Language code (e.g., KO, EN-US, JA)")
):
    """Add entry to translation dictionary"""
    try:
        dictionary = load_dictionary()
        
        # Create entry key
        key = f"{original.lower()}_{language.upper()}"
        
        # Add to dictionary
        dictionary[key] = {
            "original": original,
            "translation": translation,
            "language": language.upper(),
            "added_by": str(ctx.author),
            "server_id": str(ctx.guild.id) if ctx.guild else "DM"
        }
        
        # Save dictionary
        if save_dictionary(dictionary):
            embed = discord.Embed(
                title="📚 Dictionary Entry Added", 
                color=discord.Color.green()
            )
            embed.add_field(name="Original", value=original, inline=True)
            embed.add_field(name="Translation", value=translation, inline=True)
            embed.add_field(name="Language", value=language.upper(), inline=True)
            embed.add_field(name="Added by", value=ctx.author.mention, inline=False)
            
            await ctx.respond(embed=embed)
        else:
            await ctx.respond("Failed to save dictionary entry.", ephemeral=True)
            
    except Exception as e:
        await ctx.respond(f"Error adding dictionary entry: {e}", ephemeral=True)

@bot.slash_command(name="dict_search", description="Search for a word/phrase in the translation dictionary.")
async def dict_search_command(
    ctx: discord.ApplicationContext,
    word: discord.Option(str, description="Word/phrase to search for"),
    language: discord.Option(str, description="Language code (optional)", required=False)
):
    """Search dictionary for entries"""
    try:
        dictionary = load_dictionary()
        
        if not dictionary:
            await ctx.respond("Dictionary is empty.", ephemeral=True)
            return
        
        # Search for entries
        found_entries = []
        search_word = word.lower()
        
        for key, entry in dictionary.items():
            # Filter by server
            if ctx.guild and entry.get("server_id") != str(ctx.guild.id):
                continue
                
            # Search in original text
            if search_word in entry["original"].lower():
                if not language or entry["language"] == language.upper():
                    found_entries.append(entry)
        
        if not found_entries:
            await ctx.respond(f"No entries found for '{word}'.", ephemeral=True)
            return
        
        # Create embed with results
        embed = discord.Embed(
            title=f"📖 Dictionary Search Results for '{word}'", 
            color=discord.Color.blue()
        )
        
        for i, entry in enumerate(found_entries[:10]):  # Limit to 10 results
            embed.add_field(
                name=f"{entry['original']} ({entry['language']})",
                value=f"**Translation:** {entry['translation']}\n*Added by: {entry['added_by']}*",
                inline=False
            )
        
        if len(found_entries) > 10:
            embed.set_footer(text=f"Showing first 10 of {len(found_entries)} results")
        
        await ctx.respond(embed=embed)
        
    except Exception as e:
        await ctx.respond(f"Error searching dictionary: {e}", ephemeral=True)

@bot.slash_command(name="dict_list", description="List all dictionary entries for this server.")
async def dict_list_command(ctx: discord.ApplicationContext):
    """List all dictionary entries"""
    try:
        dictionary = load_dictionary()
        
        if not dictionary:
            await ctx.respond("Dictionary is empty.", ephemeral=True)
            return
        
        # Filter entries by server
        server_entries = []
        for entry in dictionary.values():
            if ctx.guild and entry.get("server_id") == str(ctx.guild.id):
                server_entries.append(entry)
            elif not ctx.guild and entry.get("server_id") == "DM":
                server_entries.append(entry)
        
        if not server_entries:
            await ctx.respond("No dictionary entries found for this server.", ephemeral=True)
            return
        
        # Create embed
        embed = discord.Embed(
            title="📚 Translation Dictionary", 
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Total entries: {len(server_entries)}")
        
        # Show first 20 entries
        for i, entry in enumerate(server_entries[:20]):
            embed.add_field(
                name=f"{entry['original']} ({entry['language']})",
                value=f"**→** {entry['translation']}",
                inline=True
            )
        
        if len(server_entries) > 20:
            embed.description = f"Showing first 20 of {len(server_entries)} entries"
        
        await ctx.respond(embed=embed)
        
    except Exception as e:
        await ctx.respond(f"Error listing dictionary: {e}", ephemeral=True)

@bot.slash_command(name="dict_remove", description="Remove an entry from the translation dictionary.")
async def dict_remove_command(
    ctx: discord.ApplicationContext,
    original: discord.Option(str, description="Original word/phrase to remove"),
    language: discord.Option(str, description="Language code (e.g., KO, EN-US, JA)")
):
    """Remove entry from dictionary"""
    try:
        dictionary = load_dictionary()
        key = f"{original.lower()}_{language.upper()}"
        
        if key not in dictionary:
            await ctx.respond(f"Entry '{original}' ({language.upper()}) not found in dictionary.", ephemeral=True)
            return
        
        # Check if user can remove (added by them or has manage messages permission)
        entry = dictionary[key]
        can_remove = (
            str(ctx.author) == entry.get("added_by") or
            ctx.author.guild_permissions.manage_messages
        )
        
        if not can_remove:
            await ctx.respond("You can only remove entries you added, or you need 'Manage Messages' permission.", ephemeral=True)
            return
        
        # Remove entry
        removed_entry = dictionary.pop(key)
        
        if save_dictionary(dictionary):
            embed = discord.Embed(
                title="🗑️ Dictionary Entry Removed", 
                color=discord.Color.red()
            )
            embed.add_field(name="Removed", value=f"{removed_entry['original']} → {removed_entry['translation']}", inline=False)
            embed.add_field(name="Language", value=removed_entry['language'], inline=True)
            
            await ctx.respond(embed=embed)
        else:
            await ctx.respond("Failed to remove dictionary entry.", ephemeral=True)
            
    except Exception as e:
        await ctx.respond(f"Error removing dictionary entry: {e}", ephemeral=True)

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
            # Check dictionary first
            dictionary = load_dictionary()
            search_text = message.content.lower()
            dict_key = f"{search_text}_{target_lang}"
            
            # Look for exact match in dictionary
            if dict_key in dictionary:
                entry = dictionary[dict_key]
                await message.reply(f"**📚 Dictionary → {entry['language']}:**\n{entry['translation']}")
                return
            
            # If not in dictionary, use DeepL API
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
