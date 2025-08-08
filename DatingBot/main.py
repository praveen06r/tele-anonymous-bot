import os
import logging
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
import asyncio
import threading
from config import Config
from models import db
from bot_handlers import BotHandlers

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "anonymous_dating_bot_secret")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize database
db.init_app(app)

# Initialize Telegram bot
bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
if not bot_token:
    logger.error("TELEGRAM_BOT_TOKEN environment variable not set")
    exit(1)

# Global bot application
bot_app = None

def create_bot_application():
    """Create and configure the bot application"""
    global bot_app
    
    # Create application
    bot_app = Application.builder().token(bot_token).build()
    
    # Initialize bot handlers
    handlers = BotHandlers(db)
    
    # Add command handlers
    bot_app.add_handler(CommandHandler("start", handlers.start_command))
    bot_app.add_handler(CommandHandler("help", handlers.help_command))
    bot_app.add_handler(CommandHandler("profile", handlers.profile_command))
    bot_app.add_handler(CommandHandler("match", handlers.find_match_command))
    bot_app.add_handler(CommandHandler("stop_chat", handlers.stop_chat_command))
    bot_app.add_handler(CommandHandler("report", handlers.report_command))
    bot_app.add_handler(CommandHandler("block", handlers.block_command))
    bot_app.add_handler(CommandHandler("premium", handlers.premium_command))
    
    # Add callback query handler for inline keyboards
    bot_app.add_handler(CallbackQueryHandler(handlers.button_callback))
    
    # Add message handler for text messages
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_message))
    
    return bot_app

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming webhook requests from Telegram"""
    try:
        json_data = request.get_json()
        if json_data:
            update = Update.de_json(json_data, bot_app.bot)
            
            # Process update in a separate thread to avoid blocking
            def process_update():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(bot_app.process_update(update))
                loop.close()
            
            thread = threading.Thread(target=process_update)
            thread.start()
            
        return jsonify({"status": "ok"})
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "anonymous_dating_bot"})

@app.route('/', methods=['GET'])
def root():
    """Root endpoint"""
    return jsonify({
        "message": "Anonymous Dating Telegram Bot",
        "status": "running",
        "endpoints": {
            "webhook": "/webhook",
            "health": "/health"
        }
    })

def setup_webhook():
    """Set up webhook with Telegram"""
    try:
        # Get the webhook URL from environment or construct it
        webhook_url = os.environ.get("WEBHOOK_URL", "")
        if webhook_url:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def set_webhook():
                await bot_app.bot.set_webhook(url=f"{webhook_url}/webhook")
                logger.info(f"Webhook set to: {webhook_url}/webhook")
            
            loop.run_until_complete(set_webhook())
            loop.close()
        else:
            logger.warning("WEBHOOK_URL not set, webhook not configured")
    except Exception as e:
        logger.error(f"Error setting webhook: {e}")

if __name__ == '__main__':
    with app.app_context():
        # Import models to ensure tables are created
        import models
        from models import SubscriptionType
        
        # Create database tables
        db.create_all()
        logger.info("Database tables created")
        
        # Set owner privileges for configured owner IDs (after users register)
        logger.info("Database setup complete. Owner privileges will be set when users first use the bot.")
        
        # Create bot application
        create_bot_application()
        logger.info("Bot application created")
        
        # Setup webhook
        setup_webhook()
        
        # Start Flask app
        port = int(os.environ.get('PORT', 5000))
        app.run(host='0.0.0.0', port=port, debug=False)
