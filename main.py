# Tf are you looking at nigga
import discord
from discord.ext import commands
import requests
import io
import os
from dotenv import load_dotenv
from flask import Flask
from threading import Thread
import logging

# Initialize Flask for Railway health checks
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot Online", 200

@app.route('/health')
def health():
    return "OK", 200

# Load environment variables
load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
SIGHTENGINE_USER = os.getenv('SIGHTENGINE_USER')
SIGHTENGINE_SECRET = os.getenv('SIGHTENGINE_SECRET')

# Configure Discord bot
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Bot logged in as {bot.user} (ID: {bot.user.id})')
    print('------')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # NSFW detection logic
    for attachment in message.attachments:
        if any(attachment.filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif']):
            try:
                image_data = await attachment.read()
                files = {'media': io.BytesIO(image_data)}
                params = {
                    'models': 'nudity-2.0,wad,offensive,gore',
                    'api_user': SIGHTENGINE_USER,
                    'api_secret': SIGHTENGINE_SECRET
                }

                response = requests.post(
                    'https://api.sightengine.com/1.0/check.json',
                    files=files,
                    data=params,
                    timeout=10
                )
                result = response.json()

                # NSFW detection thresholds
                if (result.get('nudity', {}).get('sexual_activity', 0) > 0.5 or
                    result.get('nudity', {}).get('sexual_display', 0) > 0.4 or
                    result.get('weapon', 0) > 0.5 or
                    result.get('drugs', 0) > 0.5):
                    
                    await message.delete()
                    try:
                        await message.author.kick(reason="NSFW content detected")
                        await message.channel.send(
                            f"🚨 {message.author.mention} was kicked for NSFW content",
                            delete_after=10
                        )
                    except discord.Forbidden:
                        pass

            except Exception as e:
                logging.error(f"Detection error: {e}")

    await bot.process_commands(message)

def run_flask():
    """Start Flask server for Railway health checks"""
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

def start_bot():
    """Start the Discord bot with auto-restart"""
    while True:
        try:
            bot.run(DISCORD_TOKEN)
        except Exception as e:
            logging.error(f"Bot crashed: {e}. Restarting in 10 seconds...")
            time.sleep(10)

if __name__ == '__main__':
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Start Flask in a separate thread
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Start bot with auto-restart
    start_bot()
