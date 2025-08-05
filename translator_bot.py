import discord
import os
import deepl
import flag
from dotenv import load_dotenv

# .env 파일에서 환경 변수를 로드합니다.
load_dotenv()

# 환경 변수에서 토큰과 API 키를 가져옵니다.
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DEEPL_AUTH_KEY = os.getenv("DEEPL_AUTH_KEY")

# DeepL 번역기 클라이언트를 초기화합니다.
try:
    translator = deepl.Translator(DEEPL_AUTH_KEY)
except Exception as e:
    print(f"DeepL API 키가 유효하지 않거나 설정되지 않았습니다: {e}")
    exit()

# 봇이 메시지 내용을 읽을 수 있도록 인텐트를 설정합니다.
intents = discord.Intents.default()
intents.message_content = True

bot = discord.Bot(intents=intents)

# 국기 이모지와 DeepL 언어 코드를 매핑합니다.
# https://www.deepl.com/docs-api/translate-text/translate-text/ 에서 지원 언어 코드를 확인하세요.
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
    "PT": "PT-PT", # 포르투갈
    "BR": "PT-BR", # 브라질
}

@bot.event
async def on_ready():
    """봇이 준비되었을 때 호출되는 이벤트"""
    print(f"{bot.user} (으)로 로그인했습니다!")
    print("봇이 성공적으로 활성화되었습니다.")
    print("-" * 20)


@bot.slash_command(name="translate", description="원하는 텍스트를 지정한 언어로 번역합니다.")
async def translate_command(
    ctx: discord.ApplicationContext,
    text: discord.Option(str, description="번역할 텍스트를 입력하세요."),
    target_language: discord.Option(str, description="목표 언어 코드 (예: KO, EN-US, JA)")
):
    """슬래시 명령어를 사용하여 텍스트를 번역합니다."""
    try:
        # DeepL API를 사용하여 텍스트 번역
        result = translator.translate_text(text, target_lang=target_language.upper())
        
        embed = discord.Embed(title="🌐 번역 결과", color=discord.Color.blue())
        embed.add_field(name="원본 텍스트", value=f"```{text}```", inline=False)
        embed.add_field(name=f"번역된 텍스트 ({result.detected_source_lang} -> {target_language.upper()})", 
                        value=f"```{result.text}```", inline=False)
        
        await ctx.respond(embed=embed)

    except deepl.DeepLException as e:
        await ctx.respond(f"번역 중 오류가 발생했습니다: {e}", ephemeral=True)
    except Exception as e:
        await ctx.respond(f"알 수 없는 오류가 발생했습니다: {e}", ephemeral=True)


@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    """메시지에 반응이 추가될 때 호출되는 이벤트 (봇이 꺼져있을 때 달린 반응도 감지)"""
    # 봇 자신의 반응은 무시
    if payload.user_id == bot.user.id:
        return

    try:
        # 반응이 달린 채널과 메시지 객체를 가져옵니다.
        channel = await bot.fetch_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        
        # 원본 메시지 내용이 비어있으면 무시
        if not message.content:
            return
            
        emoji_char = str(payload.emoji)
        
        # 이모지가 국기인지 확인하고 국가 코드를 추출합니다.
        country_code = flag.dflagize(emoji_char).strip(":").upper()

        # 매핑된 언어 코드가 있는지 확인합니다.
        target_lang = FLAG_TO_LANGUAGE.get(country_code)

        if target_lang:
            # DeepL API를 사용하여 메시지 내용 번역
            result = translator.translate_text(message.content, target_lang=target_lang)
            
            # 번역 결과가 원문과 같지 않을 때만 답장
            if result.text.strip() and result.text.lower() != message.content.lower():
                await message.reply(f"**🌐 {result.detected_source_lang} -> {target_lang} 번역:**\n{result.text}")

    except deepl.DeepLException as e:
        print(f"DeepL API 오류: {e}")
    except KeyError:
        # 국기 이모지가 아니거나 매핑되지 않은 경우 조용히 무시
        pass
    except Exception as e:
        print(f"반응 처리 중 오류 발생: {e}")


# 봇 실행
if DISCORD_TOKEN and DEEPL_AUTH_KEY:
    bot.run(DISCORD_TOKEN)
else:
    print("DISCORD_TOKEN 또는 DEEPL_AUTH_KEY 환경 변수가 설정되지 않았습니다.")