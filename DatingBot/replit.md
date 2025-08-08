# Anonymous Dating Telegram Bot

## Overview

This is an anonymous dating Telegram bot that allows users to find meaningful connections while maintaining complete anonymity. Users can create profiles with age, gender preferences, interests, and bios, then get matched with compatible users for private conversations. The bot includes safety features like blocking, reporting, and content validation to ensure a safe dating environment.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Backend Architecture
- **Framework**: Flask web application with SQLAlchemy ORM for database operations
- **Bot Framework**: Python Telegram Bot library for handling Telegram interactions
- **Session Management**: SQLAlchemy session-based database transactions with proper connection pooling
- **Modular Design**: Separated concerns with dedicated handlers, services, and utilities

### Database Schema
- **User Management**: Users table with Telegram integration and status tracking
- **Profile System**: UserProfile table with age, gender, bio, interests, and preferences
- **Matching System**: Match table tracking user connections with status management
- **Messaging**: Message table for anonymous conversations between matched users
- **Safety Features**: Report and BlockedUser tables for user protection
- **Data Types**: Enum-based status tracking (UserStatus, MatchStatus, Gender)

### Matching Algorithm
- **Compatibility Logic**: Age range and gender preference filtering
- **Anti-Spam Protection**: Recent match cooldown (7 days) and blocked user exclusion
- **Anonymous Identity**: Auto-generated anonymous IDs for privacy protection
- **Match Lifecycle**: Pending, active, ended, and blocked states

### Privacy & Security
- **Anonymous Communication**: Users communicate via anonymous IDs, not real identities
- **Content Validation**: Bio and message length limits with inappropriate content filtering
- **Rate Limiting**: Message frequency controls and daily report limits
- **Blocking System**: Mutual blocking prevention in future matches
- **Data Protection**: No storage of sensitive personal information beyond Telegram basics

### Premium Features (Updated: August 8, 2025)
- **Owner Privileges**: Bot owners (IDs: 5518634633, 1078099033) get unlimited access to all features and can see all user genders/details
- **Free Tier Limits**: Regular users get 5 free gender views, then must upgrade to premium
- **Premium Subscription**: $2.00/month for unlimited gender visibility, priority matching, and advanced filters
- **Gender Visibility Control**: Smart system tracks usage and enforces premium requirements
- **Subscription Management**: Automatic premium expiration handling and status tracking
- **Payment Processing**: Manual payment collection via PayPal, crypto, or bank transfer - contact owner directly

### Bot Interaction Flow
- **Profile Setup**: Multi-step onboarding with inline keyboard navigation
- **Match Discovery**: Automated compatible user finding with retry logic
- **Conversation Management**: Anonymous messaging between matched users
- **Safety Controls**: Easy reporting and blocking mechanisms

### Configuration Management
- **Environment-Based**: Separate development and production configurations
- **Flexible Limits**: Configurable message lengths, age ranges, and cooldown periods
- **Logging**: Structured logging with configurable levels

## External Dependencies

### Core Dependencies
- **python-telegram-bot**: Telegram Bot API integration for message handling and user interactions
- **Flask**: Web framework for webhook handling and application structure
- **SQLAlchemy**: ORM for database operations and model management
- **Flask-SQLAlchemy**: Flask integration for SQLAlchemy with connection pooling

### Database
- **SQLite**: Default database for development (configurable via DATABASE_URL)
- **PostgreSQL**: Production-ready option via environment configuration

### Telegram Integration
- **Telegram Bot API**: Core messaging and callback handling
- **Webhook Support**: Production deployment via WEBHOOK_URL configuration
- **Inline Keyboards**: Rich user interface for profile setup and match interactions

### Environment Configuration
- **TELEGRAM_BOT_TOKEN**: Required bot authentication token
- **DATABASE_URL**: Database connection string (defaults to SQLite)
- **FLASK_SECRET_KEY**: Session security key
- **WEBHOOK_URL**: Production webhook endpoint
- **DEBUG**: Development mode toggle