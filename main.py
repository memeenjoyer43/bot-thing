# get the fuck out retarded nigga
import discord
from discord.ext import commands
import requests
import io
import os
import logging
import time
from threading import Thread
from flask import Flask
from dotenv import load_dotenv

# Initialize Flask for Railway health checks
app = Flask(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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

# Flask endpoints for Railway
@app.route('/')
def home():
    return "Anti-NSFW Bot Online", 200

@app.route('/health')
def health():
    return "OK", 200

@bot.event
async def on_ready():
    logger.info(f'Bot logged in as {bot.user} (ID: {bot.user.id})')
    logger.info('------')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # NSFW detection logic
    for attachment in message.attachments:
        if any(attachment.filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif']):
            try:
                # Download the image
                image_data = await attachment.read()
                
                # Check with SightEngine
                files = {'media': io.BytesIO(image_data)}
                params = {
                    'models': 'nudity-2.0,wad,offensive,gore',
                    'api_user': SIGHTENGINE_USER,
                    'api_secret': SIGHTENGINE_SECRET
                }

                logger.info(f"Checking image: {attachment.url}")
                response = requests.post(
                    'https://api.sightengine.com/1.0/check.json',
                    files=files,
                    data=params,
                    timeout=15  # Increased timeout
                )
                response.raise_for_status()
                result = response.json()
                logger.info(f"API Result: {result}")

                # Enhanced NSFW detection
                nudity = result.get('nudity', {})
                if (nudity.get('sexual_activity', 0) > 0.2 or  # Lowered from 0.4
                    nudity.get('sexual_display', 0) > 0.15 or  # Lowered from 0.3
                    nudity.get('suggestive', 0) > 0.3 or       # New check
                    result.get('weapon', 0) > 0.3 or
                    result.get('drugs', 0) > 0.3):
                    
                    await message.delete()
                    try:
                        await message.author.kick(reason="NSFW content detected")
                        logger.info(f"Kicked user {message.author} for NSFW content")
                        await message.channel.send(
                            f"🚨 {message.author.mention} was kicked for NSFW content",
                            delete_after=10
                        )
                    except discord.Forbidden:
                        logger.warning(f"Missing permissions to kick {message.author}")
                    except Exception as e:
                        logger.error(f"Kick error: {e}")

            except requests.exceptions.RequestException as e:
                logger.error(f"SightEngine API request failed: {e}")
            except Exception as e:
                logger.error(f"Image processing error: {e}")

    await bot.process_commands(message)

def run_flask():
    """Start Flask server for Railway"""
    # Disable Flask's startup message
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

def run_bot():
    """Run bot with auto-restart"""
    while True:
        try:
            bot.run(DISCORD_TOKEN)
        except Exception as e:
            logger.error(f"Bot crashed: {e}")
            logger.info("Restarting in 10 seconds...")
            time.sleep(10)

if __name__ == '__main__':
    # Start Flask in a separate thread
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # Start the bot
    run_bot()
