"""Database models for the GAGB application."""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
)
from sqlalchemy.orm import relationship

from backend.app.core.database import Base


# Association table for many-to-many relationship between articles and teams
article_team_association = Table(
    "article_team_association",
    Base.metadata,
    Column("article_id", Integer, ForeignKey("news_articles.id")),
    Column("team_id", Integer, ForeignKey("teams.id")),
)

# Association table for many-to-many relationship between articles and players
article_player_association = Table(
    "article_player_association",
    Base.metadata,
    Column("article_id", Integer, ForeignKey("news_articles.id")),
    Column("player_id", Integer, ForeignKey("players.id")),
)


class Team(Base):
    """NHL team model."""

    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    abbreviation = Column(String, unique=True)
    division = Column(String)
    conference = Column(String)
    logo_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    players = relationship("Player", back_populates="team")
    home_games = relationship("Game", foreign_keys="Game.home_team_id", back_populates="home_team")
    away_games = relationship("Game", foreign_keys="Game.away_team_id", back_populates="away_team")
    articles = relationship("NewsArticle", secondary=article_team_association, back_populates="teams")


class Player(Base):
    """NHL player model."""

    __tablename__ = "players"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    position = Column(String)
    jersey_number = Column(Integer, nullable=True)
    team_id = Column(Integer, ForeignKey("teams.id"))
    is_injured = Column(Boolean, default=False)
    injury_details = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    team = relationship("Team", back_populates="players")
    articles = relationship("NewsArticle", secondary=article_player_association, back_populates="players")
    props = relationship("PlayerProp", back_populates="player")


class Game(Base):
    """NHL game model."""

    __tablename__ = "games"

    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String, unique=True, index=True)
    home_team_id = Column(Integer, ForeignKey("teams.id"))
    away_team_id = Column(Integer, ForeignKey("teams.id"))
    game_time = Column(DateTime)
    status = Column(String)  # scheduled, in_progress, finished, postponed, etc.
    home_score = Column(Integer, nullable=True)
    away_score = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    home_team = relationship("Team", foreign_keys=[home_team_id], back_populates="home_games")
    away_team = relationship("Team", foreign_keys=[away_team_id], back_populates="away_games")
    odds = relationship("Odds", back_populates="game")
    bets = relationship("Bet", back_populates="game")


class Odds(Base):
    """Betting odds model."""

    __tablename__ = "odds"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id"))
    sportsbook = Column(String)  # DraftKings, FanDuel, etc.
    home_moneyline = Column(Float, nullable=True)
    away_moneyline = Column(Float, nullable=True)
    home_spread = Column(Float, nullable=True)
    away_spread = Column(Float, nullable=True)
    home_spread_odds = Column(Float, nullable=True)
    away_spread_odds = Column(Float, nullable=True)
    over_under = Column(Float, nullable=True)
    over_odds = Column(Float, nullable=True)
    under_odds = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    game = relationship("Game", back_populates="odds")
    player_props = relationship("PlayerProp", back_populates="odds")


class PlayerProp(Base):
    """Player prop betting model."""

    __tablename__ = "player_props"

    id = Column(Integer, primary_key=True, index=True)
    odds_id = Column(Integer, ForeignKey("odds.id"))
    player_id = Column(Integer, ForeignKey("players.id"))
    prop_type = Column(String)  # points, goals, assists, shots_on_goal
    line = Column(Float)
    over_odds = Column(Float)
    under_odds = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    odds = relationship("Odds", back_populates="player_props")
    player = relationship("Player", back_populates="props")


class NewsArticle(Base):
    """Sports news article model."""

    __tablename__ = "news_articles"

    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String, unique=True, index=True, nullable=True)
    source = Column(String)  # ESPN, The Athletic, etc.
    title = Column(String)
    url = Column(String, unique=True)
    content = Column(String)
    summary = Column(String, nullable=True)
    published_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    teams = relationship("Team", secondary=article_team_association, back_populates="articles")
    players = relationship("Player", secondary=article_player_association, back_populates="players")


class Parlay(Base):
    """Parlay model."""

    __tablename__ = "parlays"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=True)
    stake = Column(Float)
    total_odds = Column(Float)
    potential_payout = Column(Float)
    confidence_score = Column(Float)
    status = Column(String)  # pending, won, lost, partially_won, etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    bets = relationship("Bet", back_populates="parlay")


class Bet(Base):
    """Individual bet within a parlay."""

    __tablename__ = "bets"

    id = Column(Integer, primary_key=True, index=True)
    parlay_id = Column(Integer, ForeignKey("parlays.id"))
    game_id = Column(Integer, ForeignKey("games.id"))
    bet_type = Column(String)  # moneyline, spread, over_under, player_prop, etc.
    selection = Column(String)  # home, away, over, under, etc.
    player_id = Column(Integer, ForeignKey("players.id"), nullable=True)  # For player props
    prop_type = Column(String, nullable=True)  # points, goals, assists, shots_on_goal
    odds = Column(Float)
    stake = Column(Float, nullable=True)  # Only used for single bets
    justification = Column(String)
    status = Column(String)  # pending, won, lost, etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    parlay = relationship("Parlay", back_populates="bets")
    game = relationship("Game", back_populates="bets")
    player = relationship("Player", backref="bets")


class AIAnalysis(Base):
    """AI analysis model for storing generated analyses."""

    __tablename__ = "ai_analyses"

    id = Column(Integer, primary_key=True, index=True)
    analysis_type = Column(String)  # game_prediction, parlay_optimization, etc.
    content = Column(String)
    confidence_score = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
