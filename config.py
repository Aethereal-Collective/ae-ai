import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Discord Configuration
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

# Deepseek Configuration
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
DEEPSEEK_BASE_URL = os.getenv('DEEPSEEK_BASE_URL')

# Bot Configuration
COMMAND_PREFIX = '!'
BOT_NAME = 'Aethereal AI'
ALLOWED_CHANNELS = []  # Kosong berarti semua channel diizinkan
MAX_HISTORY = 10  # Jumlah maksimum pesan yang disimpan dalam konteks 