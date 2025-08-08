import logging
import json
import random
import string
from datetime import datetime, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from sqlalchemy.orm import sessionmaker
from sqlalchemy import and_, or_
from models import User, UserProfile, Match, Message, Report, BlockedUser, Gender, UserStatus, MatchStatus, SubscriptionType
from matching_service import MatchingService
from utils import generate_anonymous_id, format_gender_display, can_see_gender, get_premium_info_text, is_owner

logger = logging.getLogger(__name__)

class BotHandlers:
    def __init__(self, db):
        self.db = db
        self.matching_service = MatchingService(db)
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        try:
            telegram_id = str(update.effective_user.id)
            
            with self.db.session() as session:
                # Check if user exists
                user = session.query(User).filter_by(telegram_id=telegram_id).first()
                
                if not user:
                    # Create new user
                    user = User(
                        telegram_id=telegram_id,
                        username=update.effective_user.username,
                        first_name=update.effective_user.first_name
                    )
                    
                    # Check if user should be set as owner
                    from config import Config
                    if int(telegram_id) in Config.OWNER_IDS:
                        user.subscription_type = SubscriptionType.OWNER
                    
                    session.add(user)
                    session.commit()
                    
                    welcome_text = (
                        "🎭 Welcome to Anonymous Dating Bot! 🎭\n\n"
                        "Find meaningful connections while staying completely anonymous.\n\n"
                        "To get started, let's set up your profile:\n"
                        "• Age and gender preferences\n"
                        "• Interests and bio\n"
                        "• What you're looking for\n\n"
                        "Ready to begin? Click the button below!"
                    )
                    
                    keyboard = [[InlineKeyboardButton("Setup Profile 📝", callback_data="setup_profile")]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await update.message.reply_text(welcome_text, reply_markup=reply_markup)
                else:
                    if user.is_registered:
                        welcome_back_text = (
                            f"🎭 Welcome back, {user.first_name or 'Anonymous'}!\n\n"
                            "What would you like to do today?"
                        )
                        
                        keyboard = [
                            [InlineKeyboardButton("Find Match 💕", callback_data="find_match")],
                            [InlineKeyboardButton("My Profile 👤", callback_data="view_profile")],
                            [InlineKeyboardButton("Help ❓", callback_data="show_help")]
                        ]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        
                        await update.message.reply_text(welcome_back_text, reply_markup=reply_markup)
                    else:
                        incomplete_text = (
                            "🎭 Welcome back!\n\n"
                            "It looks like you haven't completed your profile setup yet.\n"
                            "Let's finish setting up your profile to start matching!"
                        )
                        
                        keyboard = [[InlineKeyboardButton("Complete Profile 📝", callback_data="setup_profile")]]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        
                        await update.message.reply_text(incomplete_text, reply_markup=reply_markup)
        
        except Exception as e:
            logger.error(f"Error in start_command: {e}")
            await update.message.reply_text("Sorry, something went wrong. Please try again later.")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = (
            "🎭 Anonymous Dating Bot Help 🎭\n\n"
            "📋 Available Commands:\n"
            "/start - Start or restart the bot\n"
            "/help - Show this help message\n"
            "/profile - View or edit your profile\n"
            "/match - Find a new match\n"
            "/stop_chat - End current anonymous chat\n"
            "/report - Report inappropriate behavior\n"
            "/block - Block a user\n\n"
            "🔒 Privacy & Safety:\n"
            "• Your identity remains completely anonymous\n"
            "• All conversations are private and secure\n"
            "• You can report or block users at any time\n"
            "• End chats whenever you feel uncomfortable\n\n"
            "💕 How Matching Works:\n"
            "1. Complete your profile with preferences\n"
            "2. Use /match to find compatible users\n"
            "3. Start anonymous conversations\n"
            "4. Reveal your identity only if you choose to\n\n"
            "Need more help? Contact @support"
        )
        
        await update.message.reply_text(help_text)
    
    async def profile_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /profile command"""
        try:
            telegram_id = str(update.effective_user.id)
            
            with self.db.session() as session:
                user = session.query(User).filter_by(telegram_id=telegram_id).first()
                
                if not user:
                    await update.message.reply_text("Please use /start first to register.")
                    return
                
                if not user.is_registered or not user.profile:
                    keyboard = [[InlineKeyboardButton("Setup Profile 📝", callback_data="setup_profile")]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await update.message.reply_text("You haven't set up your profile yet!", reply_markup=reply_markup)
                    return
                
                profile = user.profile
                profile_text = (
                    f"👤 Your Profile:\n\n"
                    f"Age: {profile.age}\n"
                    f"Gender: {profile.gender.value.title()}\n"
                    f"Looking for: {profile.looking_for.value.title()}\n"
                    f"Age range: {profile.min_age}-{profile.max_age}\n"
                    f"City: {profile.city or 'Not specified'}\n"
                    f"Bio: {profile.bio or 'No bio yet'}\n"
                    f"Interests: {profile.interests or 'None specified'}"
                )
                
                keyboard = [
                    [InlineKeyboardButton("Edit Profile ✏️", callback_data="edit_profile")],
                    [InlineKeyboardButton("Find Match 💕", callback_data="find_match")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(profile_text, reply_markup=reply_markup)
        
        except Exception as e:
            logger.error(f"Error in profile_command: {e}")
            await update.message.reply_text("Sorry, couldn't load your profile. Please try again later.")
    
    async def find_match_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /match command"""
        try:
            telegram_id = str(update.effective_user.id)
            
            with self.db.session() as session:
                user = session.query(User).filter_by(telegram_id=telegram_id).first()
                
                if not user or not user.is_registered:
                    await update.message.reply_text("Please complete your profile setup first using /start")
                    return
                
                # Check if user is already in an active match
                active_match = session.query(Match).filter(
                    and_(
                        or_(Match.user1_id == user.id, Match.user2_id == user.id),
                        Match.status == MatchStatus.ACTIVE
                    )
                ).first()
                
                if active_match:
                    await update.message.reply_text(
                        "You're already in an active conversation! Use /stop_chat to end it before finding a new match."
                    )
                    return
                
                # Find a match
                match = await self.matching_service.find_match(user.id)
                
                if match:
                    # Notify both users
                    partner_id = match.user2_id if match.user1_id == user.id else match.user1_id
                    user_anonymous_id = match.anonymous_id_1 if match.user1_id == user.id else match.anonymous_id_2
                    partner_anonymous_id = match.anonymous_id_2 if match.user1_id == user.id else match.anonymous_id_1
                    
                    # Get partner info with gender visibility based on subscription
                    partner = session.query(User).filter_by(id=partner_id).first()
                    partner_profile = partner.profile if partner else None
                    
                    # Format gender display based on user's subscription
                    gender_display, can_see_gender_bool = format_gender_display(partner_profile, user, session) if partner_profile else ("Gender: Unknown", False)
                    
                    # Show additional info for owner
                    owner_info = ""
                    if is_owner(user) and partner_profile:
                        owner_info = f"\n\n👑 OWNER INFO:\n• Real Gender: {partner_profile.gender.value.title()}\n• Age: {partner_profile.age}\n• City: {partner_profile.city or 'Not specified'}"
                    
                    match_text = (
                        f"🎭 Match found! You're now connected with {partner_anonymous_id}\n\n"
                        f"Your anonymous ID: {user_anonymous_id}\n\n"
                        f"Partner Info:\n{gender_display}\n"
                        f"Age range: {partner_profile.min_age}-{partner_profile.max_age} (looking for {user.profile.min_age}-{user.profile.max_age})\n"
                        f"{owner_info}\n"
                        "Start chatting by sending a message! Remember:\n"
                        "• Stay respectful and kind\n"
                        "• You can end the chat anytime with /stop_chat\n"
                        "• Report inappropriate behavior with /report\n\n"
                        "Have fun getting to know each other! 💕"
                    )
                    
                    # Add premium upgrade button if user can't see gender
                    keyboard = []
                    if not can_see_gender_bool and not is_owner(user):
                        keyboard.append([InlineKeyboardButton("🔓 Upgrade to Premium", callback_data="upgrade_premium")])
                    
                    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
                    
                    await update.message.reply_text(match_text, reply_markup=reply_markup)
                    
                    # Notify the partner with their gender visibility
                    if partner:
                        # Format gender display for partner
                        partner_gender_display, partner_can_see = format_gender_display(user.profile, partner, session)
                        
                        # Show additional info for owner
                        partner_owner_info = ""
                        if is_owner(partner):
                            partner_owner_info = f"\n\n👑 OWNER INFO:\n• Real Gender: {user.profile.gender.value.title()}\n• Age: {user.profile.age}\n• City: {user.profile.city or 'Not specified'}"
                        
                        partner_text = (
                            f"🎭 You've been matched with {user_anonymous_id}!\n\n"
                            f"Your anonymous ID: {partner_anonymous_id}\n\n"
                            f"Partner Info:\n{partner_gender_display}\n"
                            f"Age range: {user.profile.min_age}-{user.profile.max_age} (looking for {partner_profile.min_age}-{partner_profile.max_age})\n"
                            f"{partner_owner_info}\n"
                            "Start chatting by sending a message! Remember:\n"
                            "• Stay respectful and kind\n"
                            "• You can end the chat anytime with /stop_chat\n"
                            "• Report inappropriate behavior with /report\n\n"
                            "Have fun getting to know each other! 💕"
                        )
                        
                        # Add premium upgrade button for partner if needed
                        partner_keyboard = []
                        if not partner_can_see and not is_owner(partner):
                            partner_keyboard.append([InlineKeyboardButton("🔓 Upgrade to Premium", callback_data="upgrade_premium")])
                        
                        partner_reply_markup = InlineKeyboardMarkup(partner_keyboard) if partner_keyboard else None
                        
                        await context.bot.send_message(chat_id=partner.telegram_id, text=partner_text, reply_markup=partner_reply_markup)
                else:
                    await update.message.reply_text(
                        "🔍 No matches found right now. We'll keep looking!\n\n"
                        "Try again in a few minutes, or update your preferences in your profile."
                    )
        
        except Exception as e:
            logger.error(f"Error in find_match_command: {e}")
            await update.message.reply_text("Sorry, couldn't find a match right now. Please try again later.")
    
    async def stop_chat_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stop_chat command"""
        try:
            telegram_id = str(update.effective_user.id)
            
            with self.db.session() as session:
                user = session.query(User).filter_by(telegram_id=telegram_id).first()
                
                if not user:
                    await update.message.reply_text("Please use /start first to register.")
                    return
                
                # Find active match
                active_match = session.query(Match).filter(
                    and_(
                        or_(Match.user1_id == user.id, Match.user2_id == user.id),
                        Match.status == MatchStatus.ACTIVE
                    )
                ).first()
                
                if not active_match:
                    await update.message.reply_text("You're not currently in any chat.")
                    return
                
                # End the match
                active_match.status = MatchStatus.ENDED
                active_match.ended_at = datetime.now(timezone.utc)
                session.commit()
                
                # Notify both users
                partner_id = active_match.user2_id if active_match.user1_id == user.id else active_match.user1_id
                partner = session.query(User).filter_by(id=partner_id).first()
                
                await update.message.reply_text(
                    "✋ Chat ended. Thanks for using Anonymous Dating Bot!\n\n"
                    "Use /match to find a new connection whenever you're ready. 💕"
                )
                
                if partner:
                    await context.bot.send_message(
                        chat_id=partner.telegram_id,
                        text="✋ Your chat partner has ended the conversation.\n\nUse /match to find a new connection! 💕"
                    )
        
        except Exception as e:
            logger.error(f"Error in stop_chat_command: {e}")
            await update.message.reply_text("Sorry, couldn't end the chat. Please try again.")
    
    async def report_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /report command"""
        await update.message.reply_text(
            "🚨 To report inappropriate behavior:\n\n"
            "1. Use this format: /report <reason>\n"
            "   Example: /report harassment\n\n"
            "2. Common reasons: harassment, spam, inappropriate content, fake profile\n\n"
            "Your report will be reviewed and appropriate action will be taken."
        )
    
    async def block_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /block command"""
        try:
            telegram_id = str(update.effective_user.id)
            
            with self.db.session() as session:
                user = session.query(User).filter_by(telegram_id=telegram_id).first()
                
                if not user:
                    await update.message.reply_text("Please use /start first to register.")
                    return
                
                # Find active match
                active_match = session.query(Match).filter(
                    and_(
                        or_(Match.user1_id == user.id, Match.user2_id == user.id),
                        Match.status == MatchStatus.ACTIVE
                    )
                ).first()
                
                if not active_match:
                    await update.message.reply_text("You're not currently in any chat to block.")
                    return
                
                # Block the user
                partner_id = active_match.user2_id if active_match.user1_id == user.id else active_match.user1_id
                
                existing_block = session.query(BlockedUser).filter_by(
                    blocker_id=user.id,
                    blocked_id=partner_id
                ).first()
                
                if not existing_block:
                    blocked_user = BlockedUser(blocker_id=user.id, blocked_id=partner_id)
                    session.add(blocked_user)
                
                # End the match
                active_match.status = MatchStatus.BLOCKED
                active_match.ended_at = datetime.now(timezone.utc)
                session.commit()
                
                await update.message.reply_text(
                    "🚫 User has been blocked and chat ended.\n\n"
                    "You won't be matched with this user again.\n"
                    "Use /match to find a new connection."
                )
        
        except Exception as e:
            logger.error(f"Error in block_command: {e}")
            await update.message.reply_text("Sorry, couldn't block the user. Please try again.")
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline keyboard button callbacks"""
        query = update.callback_query
        await query.answer()
        
        if query.data == "setup_profile":
            await self.start_profile_setup(query, context)
        elif query.data == "find_match":
            await self.find_match_callback(query, context)
        elif query.data == "view_profile":
            await self.view_profile_callback(query, context)
        elif query.data == "edit_profile":
            await self.edit_profile_callback(query, context)
        elif query.data == "show_help":
            await self.help_callback(query, context)
        elif query.data == "upgrade_premium":
            await self.show_premium_info(query, context)
        elif query.data.startswith("gender_"):
            await self.handle_gender_selection(query, context)
        elif query.data.startswith("looking_"):
            await self.handle_looking_for_selection(query, context)
    
    async def start_profile_setup(self, query, context):
        """Start the profile setup process"""
        text = (
            "📝 Let's set up your profile!\n\n"
            "First, what's your gender?"
        )
        
        keyboard = [
            [InlineKeyboardButton("Male", callback_data="gender_male")],
            [InlineKeyboardButton("Female", callback_data="gender_female")],
            [InlineKeyboardButton("Other", callback_data="gender_other")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup)
    
    async def handle_gender_selection(self, query, context):
        """Handle gender selection during profile setup"""
        gender = query.data.split("_")[1]
        context.user_data["gender"] = gender
        
        text = (
            f"👍 Got it! You selected: {gender.title()}\n\n"
            "What are you looking for?"
        )
        
        keyboard = [
            [InlineKeyboardButton("Men", callback_data="looking_male")],
            [InlineKeyboardButton("Women", callback_data="looking_female")],
            [InlineKeyboardButton("Anyone", callback_data="looking_other")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup)
    
    async def handle_looking_for_selection(self, query, context):
        """Handle 'looking for' selection during profile setup"""
        looking_for = query.data.split("_")[1]
        context.user_data["looking_for"] = looking_for
        
        text = (
            f"✨ Perfect! Looking for: {looking_for.title()}\n\n"
            "Now please send me your age (just the number, like: 25)"
        )
        
        context.user_data["setup_step"] = "age"
        await query.edit_message_text(text)
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages"""
        try:
            telegram_id = str(update.effective_user.id)
            
            # Check if user is in profile setup
            if "setup_step" in context.user_data:
                await self.handle_profile_setup_message(update, context)
                return
            
            with self.db.session() as session:
                user = session.query(User).filter_by(telegram_id=telegram_id).first()
                
                if not user:
                    await update.message.reply_text("Please use /start first to register.")
                    return
                
                # Check if user is in an active match
                active_match = session.query(Match).filter(
                    and_(
                        or_(Match.user1_id == user.id, Match.user2_id == user.id),
                        Match.status == MatchStatus.ACTIVE
                    )
                ).first()
                
                if active_match:
                    # Forward message to partner
                    partner_id = active_match.user2_id if active_match.user1_id == user.id else active_match.user1_id
                    partner = session.query(User).filter_by(id=partner_id).first()
                    
                    if partner:
                        # Save message to database
                        message = Message(
                            match_id=active_match.id,
                            sender_id=user.id,
                            receiver_id=partner_id,
                            content=update.message.text
                        )
                        session.add(message)
                        session.commit()
                        
                        # Get anonymous IDs
                        sender_anonymous_id = active_match.anonymous_id_1 if active_match.user1_id == user.id else active_match.anonymous_id_2
                        
                        # Forward to partner
                        forward_text = f"💬 {sender_anonymous_id}: {update.message.text}"
                        await context.bot.send_message(chat_id=partner.telegram_id, text=forward_text)
                else:
                    # No active match
                    keyboard = [[InlineKeyboardButton("Find Match 💕", callback_data="find_match")]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await update.message.reply_text(
                        "You're not currently matched with anyone.\nWould you like to find a match?",
                        reply_markup=reply_markup
                    )
        
        except Exception as e:
            logger.error(f"Error in handle_message: {e}")
            await update.message.reply_text("Sorry, something went wrong. Please try again.")
    
    async def handle_profile_setup_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle messages during profile setup"""
        try:
            step = context.user_data.get("setup_step")
            
            if step == "age":
                try:
                    age = int(update.message.text)
                    if age < 18 or age > 99:
                        await update.message.reply_text("Please enter an age between 18 and 99.")
                        return
                    
                    context.user_data["age"] = age
                    context.user_data["setup_step"] = "bio"
                    
                    await update.message.reply_text(
                        f"Great! Age: {age}\n\n"
                        "Now tell me a bit about yourself (bio). Keep it interesting but brief! "
                        "Or send 'skip' to skip this step."
                    )
                except ValueError:
                    await update.message.reply_text("Please enter a valid age number (like: 25)")
                    return
            
            elif step == "bio":
                bio = update.message.text.strip()
                if bio.lower() != "skip":
                    context.user_data["bio"] = bio
                
                context.user_data["setup_step"] = "interests"
                await update.message.reply_text(
                    "Perfect! Now tell me your interests (separated by commas).\n"
                    "Example: music, movies, hiking, cooking\n"
                    "Or send 'skip' to skip this step."
                )
            
            elif step == "interests":
                interests = update.message.text.strip()
                if interests.lower() != "skip":
                    context.user_data["interests"] = interests
                
                context.user_data["setup_step"] = "city"
                await update.message.reply_text(
                    "Awesome! What city are you in?\n"
                    "This helps us find matches near you.\n"
                    "Or send 'skip' to skip this step."
                )
            
            elif step == "city":
                city = update.message.text.strip()
                if city.lower() != "skip":
                    context.user_data["city"] = city
                
                # Complete profile setup
                await self.complete_profile_setup(update, context)
        
        except Exception as e:
            logger.error(f"Error in profile setup: {e}")
            await update.message.reply_text("Sorry, something went wrong. Please try /start again.")
    
    async def complete_profile_setup(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Complete the profile setup process"""
        try:
            telegram_id = str(update.effective_user.id)
            
            with self.db.session() as session:
                user = session.query(User).filter_by(telegram_id=telegram_id).first()
                
                if not user:
                    await update.message.reply_text("Please use /start first to register.")
                    return
                
                # Create or update profile
                if user.profile:
                    profile = user.profile
                else:
                    profile = UserProfile(user_id=user.id)
                
                profile.gender = Gender(context.user_data["gender"])
                profile.looking_for = Gender(context.user_data["looking_for"])
                profile.age = context.user_data["age"]
                profile.bio = context.user_data.get("bio", "")
                profile.interests = context.user_data.get("interests", "")
                profile.city = context.user_data.get("city", "")
                
                if not user.profile:
                    session.add(profile)
                
                user.is_registered = True
                session.commit()
                
                # Clear setup data
                context.user_data.clear()
                
                success_text = (
                    "🎉 Profile setup complete!\n\n"
                    f"Age: {profile.age}\n"
                    f"Gender: {profile.gender.value.title()}\n"
                    f"Looking for: {profile.looking_for.value.title()}\n"
                    f"City: {profile.city or 'Not specified'}\n\n"
                    "You're all set to start meeting people! 💕"
                )
                
                keyboard = [[InlineKeyboardButton("Find My First Match! 💕", callback_data="find_match")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(success_text, reply_markup=reply_markup)
        
        except Exception as e:
            logger.error(f"Error completing profile setup: {e}")
            await update.message.reply_text("Sorry, couldn't complete your profile. Please try again.")
    
    async def find_match_callback(self, query, context):
        """Handle find match button callback"""
        await query.edit_message_text("🔍 Looking for your perfect match... Please wait!")
        
        # Simulate the /match command
        fake_update = type('obj', (object,), {
            'effective_user': query.from_user,
            'message': type('obj', (object,), {
                'reply_text': lambda text: context.bot.send_message(chat_id=query.from_user.id, text=text)
            })()
        })()
        
        await self.find_match_command(fake_update, context)
    
    async def view_profile_callback(self, query, context):
        """Handle view profile button callback"""
        fake_update = type('obj', (object,), {
            'effective_user': query.from_user,
            'message': type('obj', (object,), {
                'reply_text': lambda text, reply_markup=None: context.bot.send_message(
                    chat_id=query.from_user.id, text=text, reply_markup=reply_markup
                )
            })()
        })()
        
        await self.profile_command(fake_update, context)
    
    async def edit_profile_callback(self, query, context):
        """Handle edit profile button callback"""
        await query.edit_message_text(
            "✏️ Profile editing is coming soon!\n\n"
            "For now, you can contact support to update your profile.\n"
            "Use /start to create a new profile if needed."
        )
    
    async def help_callback(self, query, context):
        """Handle help button callback"""
        help_text = (
            "🎭 Anonymous Dating Bot Help 🎭\n\n"
            "📋 Available Commands:\n"
            "/start - Start or restart the bot\n"
            "/help - Show help message\n"
            "/profile - View your profile\n"
            "/match - Find a new match\n"
            "/stop_chat - End current chat\n"
            "/report - Report inappropriate behavior\n"
            "/block - Block a user\n\n"
            "💕 Happy dating! 💕"
        )
        
        await query.edit_message_text(help_text)
    
    async def show_premium_info(self, query, context):
        """Show premium subscription information"""
        premium_text = get_premium_info_text()
        
        keyboard = [
            [InlineKeyboardButton("💎 Contact Owner", url="https://t.me/your_username")],
            [InlineKeyboardButton("🔙 Back", callback_data="find_match")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(premium_text, reply_markup=reply_markup)
    
    async def premium_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /premium command"""
        telegram_id = str(update.effective_user.id)
        
        with self.db.session() as session:
            user = session.query(User).filter_by(telegram_id=telegram_id).first()
            
            if not user:
                await update.message.reply_text("Please use /start first to register.")
                return
            
            can_see, reason = can_see_gender(user, session)
            
            if user.subscription_type == SubscriptionType.OWNER:
                status_text = "👑 OWNER STATUS\n\nYou have full access to all features including:\n• Unlimited gender visibility\n• All user data access\n• Premium features\n• Administrative controls"
            elif user.subscription_type == SubscriptionType.PREMIUM:
                if user.premium_expires_at:
                    expires = user.premium_expires_at.strftime("%Y-%m-%d")
                    status_text = f"💎 PREMIUM ACTIVE\n\nYour premium subscription expires on: {expires}\n\nPremium benefits:\n• Unlimited gender visibility\n• Priority matching\n• Advanced filters\n• No ads"
                else:
                    status_text = "💎 PREMIUM ACTIVE\n\nYou have premium access with unlimited features!"
            else:
                views_left = max(0, Config.FREE_GENDER_VIEWS - user.gender_views_used)
                status_text = f"🆓 FREE ACCOUNT\n\nGender views remaining: {views_left}/{Config.FREE_GENDER_VIEWS}\n\n{get_premium_info_text()}"
            
            keyboard = []
            if user.subscription_type == SubscriptionType.FREE:
                keyboard.append([InlineKeyboardButton("💎 Upgrade to Premium", callback_data="upgrade_premium")])
            
            reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
            await update.message.reply_text(status_text, reply_markup=reply_markup)
