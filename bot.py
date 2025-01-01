import os
import discord
from dotenv import load_dotenv
from discord.ext import commands
import openai
from duckduckgo_search import DDGS
import asyncio
import time
from random import uniform

load_dotenv()

# Konfigurasi bot
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=os.getenv('COMMAND_PREFIX', '!'), intents=intents)

# Konfigurasi OpenAI
openai_client = openai.OpenAI(
    api_key=os.getenv('OPENAI_API_KEY'),
    base_url=os.getenv('OPENAI_BASE_URL')
)

# Lock untuk mencegah multiple responses
processing_lock = {}

async def search_with_retry(query, max_retries=3):
    """Melakukan pencarian dengan retry mechanism"""
    for attempt in range(max_retries):
        try:
            with DDGS() as ddgs:
                await asyncio.sleep(uniform(1, 3))
                results = list(ddgs.text(query, max_results=2))
                return results
        except Exception as e:
            if "Ratelimit" in str(e) and attempt < max_retries - 1:
                await asyncio.sleep(5 * (attempt + 1))
                continue
            raise e
    return []

async def search_web(query, num_results=2):
    """Melakukan pencarian web menggunakan DuckDuckGo"""
    try:
        if len(query.strip()) < 10:
            return ""

        results = await search_with_retry(query)
        if not results:
            return ""
        
        formatted_results = []
        for i, r in enumerate(results, 1):
            try:
                title = r.get('title', 'No Title')
                body = r.get('body', 'No Content')
                formatted_results.append("{0}. {1}\n   {2}\n".format(i, title, body))
            except Exception as e:
                print("Error memformat hasil {0}: {1}".format(i, e))
                continue
        
        return "\n".join(formatted_results) if formatted_results else ""
    except Exception as e:
        print("Error dalam pencarian web: {0}".format(e))
        return ""

@bot.event
async def on_ready():
    print("{0} telah berhasil login!".format(bot.user))
    print("Bot tersedia di {0} server".format(len(bot.guilds)))
    for guild in bot.guilds:
        print("- {0} (id: {1})".format(guild.name, guild.id))

@bot.event
async def on_guild_join(guild):
    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).send_messages:
            await channel.send(
                "Halo! Saya adalah {0}! 👋\n"
                "Saya siap membantu menjawab pertanyaan Anda. Mention saya dan ajukan pertanyaan Anda!\n"
                "Contoh: @{1} Apa itu Cryptocurrency?\n"
                "Ketik `{2}bantuan` untuk melihat panduan penggunaan.".format(
                    os.getenv('BOT_NAME', 'Astronode AI'), bot.user.name, os.getenv('COMMAND_PREFIX', '!')
                )
            )
            break

@bot.command(name='bantuan')
async def help_command(ctx):
    help_text = (
        "🤖 **Panduan Penggunaan {0}**\n\n"
        "1️⃣ **Cara Bertanya:**\n"
        "- Mention @{1} diikuti pertanyaan Anda\n"
        "- Contoh: @{1} Jelaskan tentang AI\n\n"
        "2️⃣ **Fitur Pencarian Web:**\n"
        "- Bot akan otomatis mencari informasi terbaru dari web\n"
        "- Hasil pencarian akan digunakan untuk memberikan jawaban yang akurat\n\n"
        "3️⃣ **Perintah Tersedia:**\n"
        "- `{2}bantuan` - Menampilkan panduan ini\n\n"
        "4️⃣ **Tips:**\n"
        "- Berikan pertanyaan yang jelas dan spesifik\n"
        "- Bot akan memberikan sumber informasi jika relevan"
    ).format(os.getenv('BOT_NAME', 'Astronode AI'), bot.user.name, os.getenv('COMMAND_PREFIX', '!'))
    await ctx.send(help_text)

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    await bot.process_commands(message)
    
    if bot.user.mentioned_in(message):
        # Cek apakah pesan sedang diproses
        message_id = "{0}_{1}".format(message.channel.id, message.id)
        if message_id in processing_lock:
            return
        
        # Set lock
        processing_lock[message_id] = True
        
        try:
            async with message.channel.typing():
                # Hapus mention dari pesan
                content = message.clean_content.replace("@{0}".format(bot.user.name), "").strip()
                
                if not content:
                    await message.reply("Halo! Ada yang bisa saya bantu? 😊")
                    return

                try:
                    # Lakukan pencarian web jika pesan cukup panjang
                    search_results = await search_web(content) if len(content) >= 10 else ""
                    
                    # Gabungkan hasil pencarian dengan prompt sistem
                    system_prompt = os.getenv('SYSTEM_PROMPT', 'Anda adalah asisten AI yang membantu.')
                    combined_prompt = (
                        "{0}\n\n"
                        "{1}"
                        "Pertanyaan user: {2}".format(
                            system_prompt,
                            "Informasi dari web:\n{0}\n".format(search_results) if search_results else "",
                            content
                        )
                    )
                    
                    # Dapatkan respons dari OpenAI
                    completion = openai_client.chat.completions.create(
                        model="deepseek-chat",
                        messages=[
                            {"role": "system", "content": combined_prompt},
                            {"role": "user", "content": content}
                        ],
                        temperature=0.7,
                        max_tokens=1000
                    )
                    
                    # Ambil respons
                    bot_response = completion.choices[0].message.content
                    
                    # Kirim respons dalam beberapa pesan jika terlalu panjang
                    if len(bot_response) > 2000:
                        chunks = [bot_response[i:i+1990] for i in range(0, len(bot_response), 1990)]
                        for chunk in chunks:
                            await message.reply(chunk)
                    else:
                        await message.reply(bot_response)
                        
                except Exception as e:
                    print("Error: {0}".format(str(e)))
                    if "rate limit" in str(e).lower():
                        await message.reply(
                            "Maaf, saya sedang sibuk melayani banyak permintaan. "
                            "Mohon tunggu sebentar sebelum mencoba lagi."
                        )
                    else:
                        await message.reply(
                            "Maaf, saya sedang mengalami gangguan teknis. "
                            "Mohon tunggu sebentar dan coba lagi."
                        )
        finally:
            # Hapus lock setelah selesai
            if message_id in processing_lock:
                del processing_lock[message_id]

bot.run(os.getenv('DISCORD_TOKEN'))
