import os
import discord
from dotenv import load_dotenv
from discord.ext import commands
from google import genai
from duckduckgo_search import DDGS
import asyncio
import time
from random import uniform

# Memuat variabel lingkungan dari file .env
load_dotenv()

# Konfigurasi bot Discord
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=os.getenv('COMMAND_PREFIX', '!'), intents=intents)

# --- KONFIGURASI GEMINI API ---
# Mengatur API key dari variabel lingkungan (pastikan nama variabelnya GOOGLE_API_KEY)
client = genai.Client()

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
    print(f"{bot.user} telah berhasil login!")
    print(f"Bot tersedia di {len(bot.guilds)} server")
    for guild in bot.guilds:
        print(f"- {guild.name} (id: {guild.id})")

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
        message_id = f"{message.channel.id}_{message.id}"
        if message_id in processing_lock:
            return
        
        # Set lock
        processing_lock[message_id] = True
        
        try:
            async with message.channel.typing():
                # Hapus mention dari pesan
                content = message.clean_content.replace(f"@{bot.user.name}", "").strip()
                
                if not content:
                    await message.reply("Halo! Ada yang bisa saya bantu? 😊")
                    return

                try:
                    # Lakukan pencarian web jika pesan cukup panjang
                    search_results = await search_web(content) if len(content) >= 10 else ""
                    
                    # Gabungkan hasil pencarian dengan prompt sistem
                    system_prompt = os.getenv('SYSTEM_PROMPT', 'Anda adalah asisten AI yang membantu.')
                    combined_prompt = (
                        f"{system_prompt}\n\n"
                        f"{'Informasi dari web:\n' + search_results + '\n' if search_results else ''}"
                        f"Pertanyaan user: {content}"
                    )
                    
                    # Dapatkan respons dari Gemini API
                    response = client.models.generate_content(model="gemini-2.5-flash", contents=combined_prompt)
                    
                    # Ambil respons
                    bot_response = response.text
                    
                    # Kirim respons dalam beberapa pesan jika terlalu panjang
                    if len(bot_response) > 2000:
                        chunks = [bot_response[i:i+1990] for i in range(0, len(bot_response), 1990)]
                        for chunk in chunks:
                            await message.reply(chunk)
                    else:
                        await message.reply(bot_response)
                        
                except Exception as e:
                    print(f"Error: {str(e)}")
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

