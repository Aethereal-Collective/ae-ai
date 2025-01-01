import discord
from discord.ext import commands
from openai import OpenAI
import asyncio
import logging

import config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Konfigurasi
DISCORD_TOKEN = config.DISCORD_TOKEN
DEEPSEEK_API_KEY = config.DEEPSEEK_API_KEY
DEEPSEEK_BASE_URL = config.DEEPSEEK_BASE_URL

# Inisialisasi bot dengan semua intents
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# Inisialisasi Deepseek client
deepseek_client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL
)

@bot.event
async def on_ready():
    """Event yang dipanggil ketika bot siap"""
    logger.info(f'{bot.user} telah berhasil login!')
    logger.info(f'Bot tersedia di {len(bot.guilds)} server')
    
    # Menampilkan daftar server
    for guild in bot.guilds:
        logger.info(f'- {guild.name} (id: {guild.id})')
        logger.info(f'  - Member count: {guild.member_count}')
        logger.info(f'  - Owner: {guild.owner}')
    
    await bot.change_presence(activity=discord.Game(name="!bantuan"))

@bot.event
async def on_guild_join(guild):
    """Event yang dipanggil ketika bot bergabung ke server baru"""
    logger.info(f'Bot bergabung ke server baru: {guild.name} (id: {guild.id})')
    logger.info(f'- Member count: {guild.member_count}')
    logger.info(f'- Owner: {guild.owner}')
    
    # Mencoba mengirim pesan perkenalan ke channel umum
    try:
        # Mencari channel yang sesuai untuk mengirim pesan
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                welcome_text = f"""
Halo semuanya! 👋
Saya adalah Aethereal AI, asisten AI yang siap membantu Anda.

Untuk menggunakan saya:
1. Mention @{bot.user.name} diikuti dengan pertanyaan Anda
   Contoh: @{bot.user.name} Apa itu Python?

2. Ketik `!bantuan` untuk melihat panduan lengkap

Saya akan merespons dalam Bahasa Indonesia 🇮🇩
"""
                await channel.send(welcome_text)
                break
    except Exception as e:
        logger.error(f"Error saat mengirim pesan perkenalan: {str(e)}")

@bot.event
async def on_message(message):
    """Event yang dipanggil ketika ada pesan baru"""
    # Mengabaikan pesan dari bot
    if message.author == bot.user:
        return

    # Memeriksa apakah pesan dimulai dengan prefix
    if message.content.startswith(bot.command_prefix):
        await bot.process_commands(message)
        return

    # Memeriksa apakah bot di-mention
    if bot.user.mentioned_in(message):
        async with message.channel.typing():
            try:
                # Menghapus mention dari pesan
                prompt = message.content.replace(f'<@{bot.user.id}>', '').strip()
                
                logger.info(f"Menerima prompt dari {message.author} di {message.guild.name}: {prompt}")
                
                # Mendapatkan respons dari Deepseek
                response = deepseek_client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant. Please respond in Indonesian language."},
                        {"role": "user", "content": prompt}
                    ]
                )
                
                response_text = response.choices[0].message.content
                
                # Memecah respons yang panjang
                while response_text:
                    if len(response_text) <= 2000:
                        await message.reply(response_text)
                        break
                    else:
                        # Mencari titik terdekat untuk memecah pesan
                        split_point = response_text[:2000].rfind('.')
                        if split_point == -1:
                            split_point = 1999
                        
                        await message.channel.send(response_text[:split_point + 1])
                        response_text = response_text[split_point + 1:].strip()
                        await asyncio.sleep(1)  # Delay untuk menghindari rate limiting
                        
            except Exception as e:
                logger.error(f"Error saat memproses pesan: {str(e)}", exc_info=True)
                await message.reply("Maaf, terjadi kesalahan saat memproses permintaan Anda.")

@bot.command(name='bantuan')
async def bantuan_command(ctx):
    """Menampilkan bantuan penggunaan bot"""
    help_text = f"""
**🤖 Aethereal AI - Bantuan**

Untuk menggunakan bot ini, Anda bisa:
1. Mention @{bot.user.name} diikuti dengan pertanyaan Anda
   Contoh: @{bot.user.name} Apa itu Cryptocurrency?

2. Gunakan perintah berikut:
   • `!bantuan` - Menampilkan bantuan ini

Bot akan merespons dalam Bahasa Indonesia 🇮🇩
"""
    await ctx.send(help_text)

# Menjalankan bot
if __name__ == "__main__":
    logger.info("Memulai bot...")
    bot.run(DISCORD_TOKEN) 