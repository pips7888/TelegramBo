import os
import logging
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CallbackQueryHandler, filters
import yt_dlp

# ==========================================
# PASTE YOUR TOKEN HERE
# ==========================================
TOKEN = "8386882032:AAFNHZrePyjr8jaRii3rTafwW5UR0z10Wsc" 

# ==========================================
# 1. DUMMY WEB SERVER (KEEPS BOT ALIVE)
# ==========================================
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is Running 24/7!")

def start_web_server():
    # Render gives us a PORT env variable. Default to 8080 if not found.
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), SimpleHandler)
    print(f"🌍 Web Server running on port {port}")
    server.serve_forever()

# ==========================================
# 2. BOT LOGIC
# ==========================================
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)

async def post_init(application):
    print("\n" * 3)
    print("==================================================")
    print(f"🚀 CLOUD BOT STARTED")
    print(f"✅ Web Server: ONLINE")
    print(f"✅ Mode: TikTok/Insta Optimized")
    print("==================================================")
    print("\n")

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if not url or "http" not in url: return
    context.user_data['current_link'] = url
    print(f"🔗 Link: {url}")

    keyboard = [
        [InlineKeyboardButton("💎 Best Quality", callback_data='quality_best'), InlineKeyboardButton("🎵 Audio (MP3)", callback_data='quality_audio')],
        [InlineKeyboardButton("📺 1080p", callback_data='quality_1080'), InlineKeyboardButton("📱 720p (HD)", callback_data='quality_720')],
        [InlineKeyboardButton("⚡ 480p", callback_data='quality_480'), InlineKeyboardButton("💾 360p", callback_data='quality_360')]
    ]
    await update.message.reply_text("🎬 <b>Select Resolution:</b>", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    choice = query.data
    url = context.user_data.get('current_link')
    if not url: return

    await query.edit_message_text(text="⏳ <b>Processing...</b>", parse_mode=ParseMode.HTML)
    await download_media(url, choice, query.message, context)

async def download_media(url, choice, message, context):
    # Cloud Config: Use generic Linux disguise or iPhone
    ydl_opts = {
        'outtmpl': '%(id)s.%(ext)s', 
        'quiet': True, 
        'no_warnings': True,
        'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
    }

    # CLOUD SAFETY: On free servers, we cannot merge video+audio easily because ffmpeg is missing.
    # We force "Best Single File" mode to prevent crashes.
    
    if choice == 'quality_audio':
        ydl_opts['format'] = 'bestaudio/best'
        # Note: We can't convert to mp3 without ffmpeg, so we download m4a (plays on all phones)
        ydl_opts['outtmpl'] = '%(id)s.m4a' 

    elif choice == 'quality_best':
        ydl_opts['format'] = 'best[ext=mp4]/best'
    
    elif choice == 'quality_1080':
        ydl_opts['format'] = 'best[height<=1080][ext=mp4]/best'

    elif choice == 'quality_720':
        ydl_opts['format'] = 'best[height<=720][ext=mp4]/best'

    elif choice == 'quality_480':
        ydl_opts['format'] = 'best[height<=480][ext=mp4]/best'

    elif choice == 'quality_360':
        ydl_opts['format'] = 'best[height<=360][ext=mp4]/best'

    filename = None
    try:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, lambda: run_yt_dlp(ydl_opts, url))

        files = [f for f in os.listdir('.') if os.path.isfile(f)]
        if not files: raise Exception("Download failed")
        filename = max(files, key=os.path.getctime)
        
        file_size_mb = os.path.getsize(filename) / (1024 * 1024)
        
        if file_size_mb > 50:
            await context.bot.edit_message_text(chat_id=message.chat.id, message_id=message.message_id, text=f"⚠️ File > 50MB.", parse_mode=ParseMode.HTML)
            os.remove(filename)
            return

        await context.bot.edit_message_text(chat_id=message.chat.id, message_id=message.message_id, text="🚀 <b>Uploading...</b>", parse_mode=ParseMode.HTML)
        
        with open(filename, 'rb') as f:
            if filename.endswith('.m4a') or filename.endswith('.mp3'):
                await context.bot.send_audio(chat_id=message.chat.id, audio=f, caption="✨ Audio", read_timeout=60, write_timeout=60)
            else:
                await context.bot.send_video(chat_id=message.chat.id, video=f, caption=f"✨ Downloaded", read_timeout=60, write_timeout=60)

        await context.bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)

    except Exception as e:
        print(f"Error: {e}")
        try: await context.bot.edit_message_text(chat_id=message.chat.id, message_id=message.message_id, text="❌ Error. Video might be private.", parse_mode=ParseMode.HTML)
        except: pass

    finally:
        if filename and os.path.exists(filename):
            try: os.remove(filename)
            except: pass

def run_yt_dlp(opts, url):
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.extract_info(url, download=True)

if __name__ == '__main__':
    # Start Dummy Web Server in Background
    threading.Thread(target=start_web_server, daemon=True).start()
    
    application = (
        ApplicationBuilder()
        .token(TOKEN)
        .post_init(post_init)
        .build()
    )
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_link))
    application.add_handler(CallbackQueryHandler(button_click))
    print("✅ System Ready...")
    application.run_polling()