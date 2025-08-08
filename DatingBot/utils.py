import random
import string
import hashlib
import re
from datetime import datetime, timezone
from config import Config

def generate_anonymous_id(length=None):
    """Generate a random anonymous ID for users"""
    if length is None:
        length = Config.ANONYMOUS_ID_LENGTH
    
    # Generate random string
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
    return f"{Config.ANONYMOUS_ID_PREFIX}{random_part}"

def validate_age(age):
    """Validate age input"""
    try:
        age_int = int(age)
        return Config.MIN_AGE <= age_int <= Config.MAX_AGE, age_int
    except (ValueError, TypeError):
        return False, None

def validate_bio(bio):
    """Validate bio input"""
    if not bio or bio.strip() == "":
        return True, ""  # Empty bio is allowed
    
    bio = bio.strip()
    if len(bio) > Config.MAX_BIO_LENGTH:
        return False, None
    
    # Check for inappropriate content (basic check)
    inappropriate_words = ["hate", "kill", "die", "suicide", "drug"]  # Extend as needed
    bio_lower = bio.lower()
    for word in inappropriate_words:
        if word in bio_lower:
            return False, None
    
    return True, bio

def validate_interests(interests):
    """Validate interests input"""
    if not interests or interests.strip() == "":
        return True, ""  # Empty interests are allowed
    
    interests = interests.strip()
    if len(interests) > Config.MAX_INTERESTS_LENGTH:
        return False, None
    
    # Basic format check (comma-separated)
    interest_list = [i.strip() for i in interests.split(',')]
    if len(interest_list) > 10:  # Max 10 interests
        return False, None
    
    # Check each interest
    for interest in interest_list:
        if len(interest) < 2 or len(interest) > 30:
            return False, None
        if not re.match(r'^[a-zA-Z0-9\s-]+$', interest):  # Only alphanumeric, spaces, hyphens
            return False, None
    
    return True, interests

def validate_city(city):
    """Validate city input"""
    if not city or city.strip() == "":
        return True, ""  # Empty city is allowed
    
    city = city.strip().title()  # Capitalize first letters
    if len(city) > 50:
        return False, None
    
    # Only letters, spaces, hyphens, apostrophes
    if not re.match(r"^[a-zA-Z\s\-']+$", city):
        return False, None
    
    return True, city

def validate_message(message):
    """Validate message content"""
    if not message or message.strip() == "":
        return False, None
    
    message = message.strip()
    if len(message) > Config.MAX_MESSAGE_LENGTH:
        return False, None
    
    # Basic inappropriate content check
    inappropriate_words = ["hate", "kill", "die", "suicide"]  # Extend as needed
    message_lower = message.lower()
    for word in inappropriate_words:
        if word in message_lower:
            return False, None
    
    return True, message

def hash_user_id(telegram_id):
    """Create a hash of telegram ID for privacy"""
    return hashlib.sha256(str(telegram_id).encode()).hexdigest()[:10]

def format_datetime(dt):
    """Format datetime for display"""
    if not dt:
        return "Never"
    
    now = datetime.now(timezone.utc)
    diff = now - dt
    
    if diff.days > 0:
        return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    else:
        return "Just now"

def clean_text(text):
    """Clean text input from user"""
    if not text:
        return ""
    
    # Remove extra whitespace
    text = ' '.join(text.split())
    
    # Remove potentially harmful characters
    text = re.sub(r'[<>"\']', '', text)
    
    return text.strip()

def generate_match_summary(user_profile, partner_profile):
    """Generate a summary of what makes two users compatible"""
    compatibility_points = []
    
    # Age compatibility
    age_diff = abs(user_profile.age - partner_profile.age)
    if age_diff <= 2:
        compatibility_points.append("Very close in age")
    elif age_diff <= 5:
        compatibility_points.append("Similar age range")
    
    # Same city
    if (user_profile.city and partner_profile.city and 
        user_profile.city.lower() == partner_profile.city.lower()):
        compatibility_points.append(f"Both from {user_profile.city}")
    
    # Common interests
    if user_profile.interests and partner_profile.interests:
        user_interests = set(i.strip().lower() for i in user_profile.interests.split(','))
        partner_interests = set(i.strip().lower() for i in partner_profile.interests.split(','))
        common = user_interests.intersection(partner_interests)
        
        if common:
            if len(common) == 1:
                compatibility_points.append(f"Shared interest: {list(common)[0]}")
            else:
                compatibility_points.append(f"Shared interests: {', '.join(list(common)[:2])}")
    
    if compatibility_points:
        return "You have: " + ", ".join(compatibility_points)
    else:
        return "You both meet each other's preferences!"

def is_appropriate_content(text):
    """Check if content is appropriate"""
    if not text:
        return True
    
    text_lower = text.lower()
    
    # List of inappropriate words/phrases (extend as needed)
    inappropriate_patterns = [
        r'\b(hate|kill|die|suicide)\b',
        r'\b(fuck|shit|damn)\b',  # Profanity
        r'\b(drug|weed|cocaine)\b',  # Drug references
        r'\b(sex|nude|naked)\b',  # Sexual content
        r'(instagram|telegram|whatsapp|phone|number)',  # Contact sharing attempts
        r'(\d{10,})',  # Phone numbers
        r'(@\w+)',  # Social media handles
    ]
    
    for pattern in inappropriate_patterns:
        if re.search(pattern, text_lower):
            return False
    
    return True

def get_safety_tips():
    """Get random safety tip for users"""
    tips = [
        "🔒 Never share personal information like your real name, phone number, or address",
        "📱 Keep conversations within the bot until you feel completely comfortable",
        "🚫 Report anyone who makes you feel uncomfortable using /report",
        "⚠️ Trust your instincts - if something feels wrong, end the chat with /stop_chat",
        "💪 You're in control - you can block users anytime with /block",
        "🎭 Remember, everyone deserves respect in anonymous conversations",
        "🚨 If someone asks for personal details, it's okay to refuse and report them",
        "💕 Take your time getting to know someone before revealing more about yourself"
    ]
    
    return random.choice(tips)

def log_user_action(user_id, action, details=None):
    """Log user actions for monitoring (in a real app, this would go to proper logging)"""
    timestamp = datetime.now(timezone.utc).isoformat()
    log_entry = f"[{timestamp}] User {user_id} - {action}"
    if details:
        log_entry += f" - {details}"
    
    # In production, send to proper logging service
    print(log_entry)  # For now, just print

def can_see_gender(user, db_session=None):
    """Check if user can see gender information based on their subscription and usage"""
    from models import SubscriptionType
    
    # Owner can always see gender
    if user.subscription_type == SubscriptionType.OWNER:
        return True, "Owner privileges"
    
    # Premium users can always see gender
    if user.subscription_type == SubscriptionType.PREMIUM:
        # Check if premium is still valid
        if user.premium_expires_at and user.premium_expires_at > datetime.now(timezone.utc):
            return True, "Premium active"
        else:
            # Premium expired, revert to free
            if db_session:
                user.subscription_type = SubscriptionType.FREE
                db_session.commit()
            return False, "Premium expired"
    
    # Free users get limited gender views
    if user.gender_views_used < Config.FREE_GENDER_VIEWS:
        return True, f"Free tier ({user.gender_views_used + 1}/{Config.FREE_GENDER_VIEWS})"
    
    return False, "Premium required"

def increment_gender_view(user, db_session):
    """Increment the user's gender view count"""
    from models import SubscriptionType
    
    # Only increment for free users
    if user.subscription_type == SubscriptionType.FREE:
        user.gender_views_used += 1
        db_session.commit()

def is_owner(user):
    """Check if user is the bot owner"""
    return int(user.telegram_id) in Config.OWNER_IDS

def format_gender_display(partner_profile, viewer_user, db_session):
    """Format gender display based on user's privileges"""
    can_see, reason = can_see_gender(viewer_user, db_session)
    
    if can_see:
        # Increment view count for eligible users
        increment_gender_view(viewer_user, db_session)
        return f"Gender: {partner_profile.gender.value.title()}", True
    else:
        return "Gender: Hidden (Premium required)", False

def get_premium_info_text():
    """Get premium subscription information text"""
    return (
        f"💎 PREMIUM SUBSCRIPTION 💎\n\n"
        f"Upgrade to Premium for just ${Config.PREMIUM_PRICE_USD}/month and get:\n\n"
        f"✨ Unlimited gender visibility\n"
        f"🔥 Priority matching\n"
        f"🎯 Advanced filters\n"
        f"📊 Match statistics\n"
        f"🚀 Early access to new features\n\n"
        f"💳 Payment Methods:\n"
        f"• PayPal: Contact owner for details\n"
        f"• Crypto: Contact owner for wallet\n"
        f"• Bank Transfer: Contact owner for info\n\n"
        f"📞 Contact the bot owner to upgrade!\n"
        f"Your subscription helps maintain this service."
    )
