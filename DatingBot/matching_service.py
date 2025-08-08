import logging
import random
from datetime import datetime, timezone, timedelta
from sqlalchemy import and_, or_, not_
from models import User, UserProfile, Match, BlockedUser, Gender, MatchStatus
from utils import generate_anonymous_id

logger = logging.getLogger(__name__)

class MatchingService:
    def __init__(self, db):
        self.db = db
    
    async def find_match(self, user_id):
        """Find a compatible match for the given user"""
        try:
            with self.db.session() as session:
                user = session.query(User).filter_by(id=user_id).first()
                if not user or not user.profile:
                    return None
                
                user_profile = user.profile
                
                # Get users that this user has blocked
                blocked_user_ids = session.query(BlockedUser.blocked_id).filter_by(blocker_id=user_id).subquery()
                
                # Get users that have blocked this user
                blocked_by_user_ids = session.query(BlockedUser.blocker_id).filter_by(blocked_id=user_id).subquery()
                
                # Get users that this user has already matched with recently (within last 7 days)
                recent_match_user_ids = session.query(
                    Match.user1_id, Match.user2_id
                ).filter(
                    and_(
                        or_(Match.user1_id == user_id, Match.user2_id == user_id),
                        Match.created_at >= datetime.now(timezone.utc) - timedelta(days=7)
                    )
                ).all()
                
                # Flatten the recent match user IDs
                recent_matched_ids = set()
                for match in recent_match_user_ids:
                    if match.user1_id != user_id:
                        recent_matched_ids.add(match.user1_id)
                    if match.user2_id != user_id:
                        recent_matched_ids.add(match.user2_id)
                
                # Find compatible users
                potential_matches = session.query(User).join(UserProfile).filter(
                    # Basic filters
                    User.id != user_id,
                    User.is_registered == True,
                    User.status.in_(['active']),
                    
                    # Age compatibility
                    UserProfile.age >= user_profile.min_age,
                    UserProfile.age <= user_profile.max_age,
                    UserProfile.min_age <= user_profile.age,
                    UserProfile.max_age >= user_profile.age,
                    
                    # Gender compatibility
                    UserProfile.gender == user_profile.looking_for,
                    UserProfile.looking_for == user_profile.gender,
                    
                    # Exclude blocked users
                    not_(User.id.in_(blocked_user_ids)),
                    not_(User.id.in_(blocked_by_user_ids)),
                    
                    # Exclude users already in active matches
                    not_(User.id.in_(
                        session.query(Match.user1_id).filter(Match.status == MatchStatus.ACTIVE).union(
                            session.query(Match.user2_id).filter(Match.status == MatchStatus.ACTIVE)
                        )
                    ))
                ).all()
                
                # Filter out recently matched users
                potential_matches = [u for u in potential_matches if u.id not in recent_matched_ids]
                
                if not potential_matches:
                    return None
                
                # Apply additional compatibility scoring (optional enhancement)
                scored_matches = []
                for match_user in potential_matches:
                    score = self.calculate_compatibility_score(user_profile, match_user.profile)
                    scored_matches.append((match_user, score))
                
                # Sort by compatibility score (highest first)
                scored_matches.sort(key=lambda x: x[1], reverse=True)
                
                # Take top 5 matches and randomly select one (adds some variety)
                top_matches = scored_matches[:5] if len(scored_matches) >= 5 else scored_matches
                selected_match_user = random.choice(top_matches)[0]
                
                # Create the match
                anonymous_id_1 = generate_anonymous_id()
                anonymous_id_2 = generate_anonymous_id()
                
                match = Match(
                    user1_id=user_id,
                    user2_id=selected_match_user.id,
                    status=MatchStatus.ACTIVE,
                    anonymous_id_1=anonymous_id_1,
                    anonymous_id_2=anonymous_id_2
                )
                
                session.add(match)
                session.commit()
                
                logger.info(f"Match created: User {user_id} matched with User {selected_match_user.id}")
                return match
        
        except Exception as e:
            logger.error(f"Error finding match for user {user_id}: {e}")
            return None
    
    def calculate_compatibility_score(self, profile1, profile2):
        """Calculate compatibility score between two profiles"""
        score = 0
        
        # Base score for meeting basic criteria
        score += 50
        
        # City bonus (same city gets extra points)
        if profile1.city and profile2.city and profile1.city.lower() == profile2.city.lower():
            score += 20
        
        # Age compatibility bonus (closer ages get more points)
        age_diff = abs(profile1.age - profile2.age)
        if age_diff <= 2:
            score += 15
        elif age_diff <= 5:
            score += 10
        elif age_diff <= 10:
            score += 5
        
        # Interest matching bonus
        if profile1.interests and profile2.interests:
            interests1 = set(interest.strip().lower() for interest in profile1.interests.split(','))
            interests2 = set(interest.strip().lower() for interest in profile2.interests.split(','))
            
            common_interests = interests1.intersection(interests2)
            score += len(common_interests) * 5  # 5 points per common interest
        
        # Bio length bonus (users with bios are more serious)
        if profile1.bio and profile2.bio:
            if len(profile1.bio) > 20 and len(profile2.bio) > 20:
                score += 10
        
        return min(score, 100)  # Cap at 100 points
    
    async def get_user_match_history(self, user_id, limit=10):
        """Get recent match history for a user"""
        try:
            with self.db.session() as session:
                matches = session.query(Match).filter(
                    or_(Match.user1_id == user_id, Match.user2_id == user_id)
                ).order_by(Match.created_at.desc()).limit(limit).all()
                
                return matches
        
        except Exception as e:
            logger.error(f"Error getting match history for user {user_id}: {e}")
            return []
    
    async def end_inactive_matches(self, max_inactive_hours=24):
        """End matches that have been inactive for too long"""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_inactive_hours)
            
            with self.db.session() as session:
                # Find active matches with no recent messages
                inactive_matches = session.query(Match).filter(
                    Match.status == MatchStatus.ACTIVE,
                    Match.created_at < cutoff_time,
                    ~Match.messages.any()  # No messages in this match
                ).all()
                
                count = 0
                for match in inactive_matches:
                    match.status = MatchStatus.ENDED
                    match.ended_at = datetime.now(timezone.utc)
                    count += 1
                
                if count > 0:
                    session.commit()
                    logger.info(f"Ended {count} inactive matches")
                
                return count
        
        except Exception as e:
            logger.error(f"Error ending inactive matches: {e}")
            return 0
