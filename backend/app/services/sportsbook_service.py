"""Service for interacting with sportsbook APIs."""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import httpx
from sqlalchemy.orm import Session

from backend.app.config import get_settings
from backend.app.core.models import Game, Odds, Team

logger = logging.getLogger(__name__)


class SportsbookService:
    """Service for interacting with sportsbook APIs."""

    def __init__(self):
        """Initialize the sportsbook service."""
        self.settings = get_settings()
        self.draftkings_api_key = self.settings.draftkings_api_key
        self.fanduel_api_key = self.settings.fanduel_api_key

    async def refresh_games(self, db: Session, days: int = 7) -> int:
        """
        Refresh NHL games data from external API.
        
        Args:
            db: Database session
            days: Number of days to fetch
            
        Returns:
            Number of games updated
        """
        logger.info(f"Refreshing NHL games data for the next {days} days")
        
        # In a real implementation, this would fetch data from an external API
        # For now, we'll simulate it with mock data
        
        # First, ensure all NHL teams exist in the database
        await self._ensure_teams_exist(db)
        
        # Fetch games from external API (simulated)
        games_data = await self._fetch_games(days)
        
        # Update database with games data
        games_updated = 0
        for game_data in games_data:
            # Check if game already exists
            game = db.query(Game).filter(Game.external_id == game_data["external_id"]).first()
            
            if game:
                # Update existing game
                game.status = game_data["status"]
                game.game_time = game_data["game_time"]
                game.home_score = game_data.get("home_score")
                game.away_score = game_data.get("away_score")
                db.add(game)
                games_updated += 1
            else:
                # Create new game
                home_team = db.query(Team).filter(Team.name == game_data["home_team"]).first()
                away_team = db.query(Team).filter(Team.name == game_data["away_team"]).first()
                
                if not home_team or not away_team:
                    logger.warning(f"Team not found: {game_data['home_team']} or {game_data['away_team']}")
                    continue
                
                game = Game(
                    external_id=game_data["external_id"],
                    home_team_id=home_team.id,
                    away_team_id=away_team.id,
                    game_time=game_data["game_time"],
                    status=game_data["status"],
                    home_score=game_data.get("home_score"),
                    away_score=game_data.get("away_score"),
                )
                db.add(game)
                games_updated += 1
        
        db.commit()
        logger.info(f"Updated {games_updated} NHL games")
        return games_updated

    async def refresh_odds(self, db: Session) -> int:
        """
        Refresh betting odds data from external APIs.
        
        Args:
            db: Database session
            
        Returns:
            Number of odds updated
        """
        logger.info("Refreshing betting odds data")
        
        # Get upcoming games
        now = datetime.utcnow()
        future = now + timedelta(days=7)
        games = db.query(Game).filter(
            Game.game_time >= now,
            Game.game_time <= future,
            Game.status == "scheduled",
        ).all()
        
        odds_updated = 0
        for game in games:
            # Refresh odds for each game
            game_odds_updated = await self.refresh_odds_for_game(db, game.id)
            odds_updated += game_odds_updated
        
        logger.info(f"Updated odds for {odds_updated} games")
        return odds_updated

    async def refresh_odds_for_game(self, db: Session, game_id: int) -> int:
        """
        Refresh betting odds data for a specific game.
        
        Args:
            db: Database session
            game_id: ID of the game to refresh odds for
            
        Returns:
            Number of odds updated
        """
        logger.info(f"Refreshing betting odds for game {game_id}")
        
        # Get game
        game = db.query(Game).filter(Game.id == game_id).first()
        if not game:
            logger.warning(f"Game not found: {game_id}")
            return 0
        
        # Fetch odds from external APIs (simulated)
        draftkings_odds = await self._fetch_draftkings_odds(game.external_id)
        fanduel_odds = await self._fetch_fanduel_odds(game.external_id)
        
        odds_updated = 0
        
        # Update DraftKings odds
        if draftkings_odds:
            # Check if odds already exist
            existing_odds = db.query(Odds).filter(
                Odds.game_id == game_id,
                Odds.sportsbook == "DraftKings",
            ).first()
            
            if existing_odds:
                # Update existing odds
                existing_odds.home_moneyline = draftkings_odds.get("home_moneyline")
                existing_odds.away_moneyline = draftkings_odds.get("away_moneyline")
                existing_odds.home_spread = draftkings_odds.get("home_spread")
                existing_odds.away_spread = draftkings_odds.get("away_spread")
                existing_odds.home_spread_odds = draftkings_odds.get("home_spread_odds")
                existing_odds.away_spread_odds = draftkings_odds.get("away_spread_odds")
                existing_odds.over_under = draftkings_odds.get("over_under")
                existing_odds.over_odds = draftkings_odds.get("over_odds")
                existing_odds.under_odds = draftkings_odds.get("under_odds")
                db.add(existing_odds)
            else:
                # Create new odds
                new_odds = Odds(
                    game_id=game_id,
                    sportsbook="DraftKings",
                    home_moneyline=draftkings_odds.get("home_moneyline"),
                    away_moneyline=draftkings_odds.get("away_moneyline"),
                    home_spread=draftkings_odds.get("home_spread"),
                    away_spread=draftkings_odds.get("away_spread"),
                    home_spread_odds=draftkings_odds.get("home_spread_odds"),
                    away_spread_odds=draftkings_odds.get("away_spread_odds"),
                    over_under=draftkings_odds.get("over_under"),
                    over_odds=draftkings_odds.get("over_odds"),
                    under_odds=draftkings_odds.get("under_odds"),
                )
                db.add(new_odds)
            
            odds_updated += 1
        
        # Update FanDuel odds
        if fanduel_odds:
            # Check if odds already exist
            existing_odds = db.query(Odds).filter(
                Odds.game_id == game_id,
                Odds.sportsbook == "FanDuel",
            ).first()
            
            if existing_odds:
                # Update existing odds
                existing_odds.home_moneyline = fanduel_odds.get("home_moneyline")
                existing_odds.away_moneyline = fanduel_odds.get("away_moneyline")
                existing_odds.home_spread = fanduel_odds.get("home_spread")
                existing_odds.away_spread = fanduel_odds.get("away_spread")
                existing_odds.home_spread_odds = fanduel_odds.get("home_spread_odds")
                existing_odds.away_spread_odds = fanduel_odds.get("away_spread_odds")
                existing_odds.over_under = fanduel_odds.get("over_under")
                existing_odds.over_odds = fanduel_odds.get("over_odds")
                existing_odds.under_odds = fanduel_odds.get("under_odds")
                db.add(existing_odds)
            else:
                # Create new odds
                new_odds = Odds(
                    game_id=game_id,
                    sportsbook="FanDuel",
                    home_moneyline=fanduel_odds.get("home_moneyline"),
                    away_moneyline=fanduel_odds.get("away_moneyline"),
                    home_spread=fanduel_odds.get("home_spread"),
                    away_spread=fanduel_odds.get("away_spread"),
                    home_spread_odds=fanduel_odds.get("home_spread_odds"),
                    away_spread_odds=fanduel_odds.get("away_spread_odds"),
                    over_under=fanduel_odds.get("over_under"),
                    over_odds=fanduel_odds.get("over_odds"),
                    under_odds=fanduel_odds.get("under_odds"),
                )
                db.add(new_odds)
            
            odds_updated += 1
        
        db.commit()
        logger.info(f"Updated {odds_updated} odds for game {game_id}")
        return odds_updated

    async def _ensure_teams_exist(self, db: Session) -> None:
        """
        Ensure all NHL teams exist in the database.
        
        Args:
            db: Database session
        """
        # NHL teams data
        nhl_teams = [
            {"name": "Boston Bruins", "abbreviation": "BOS", "division": "Atlantic", "conference": "Eastern"},
            {"name": "Buffalo Sabres", "abbreviation": "BUF", "division": "Atlantic", "conference": "Eastern"},
            {"name": "Detroit Red Wings", "abbreviation": "DET", "division": "Atlantic", "conference": "Eastern"},
            {"name": "Florida Panthers", "abbreviation": "FLA", "division": "Atlantic", "conference": "Eastern"},
            {"name": "Montreal Canadiens", "abbreviation": "MTL", "division": "Atlantic", "conference": "Eastern"},
            {"name": "Ottawa Senators", "abbreviation": "OTT", "division": "Atlantic", "conference": "Eastern"},
            {"name": "Tampa Bay Lightning", "abbreviation": "TBL", "division": "Atlantic", "conference": "Eastern"},
            {"name": "Toronto Maple Leafs", "abbreviation": "TOR", "division": "Atlantic", "conference": "Eastern"},
            {"name": "Carolina Hurricanes", "abbreviation": "CAR", "division": "Metropolitan", "conference": "Eastern"},
            {"name": "Columbus Blue Jackets", "abbreviation": "CBJ", "division": "Metropolitan", "conference": "Eastern"},
            {"name": "New Jersey Devils", "abbreviation": "NJD", "division": "Metropolitan", "conference": "Eastern"},
            {"name": "New York Islanders", "abbreviation": "NYI", "division": "Metropolitan", "conference": "Eastern"},
            {"name": "New York Rangers", "abbreviation": "NYR", "division": "Metropolitan", "conference": "Eastern"},
            {"name": "Philadelphia Flyers", "abbreviation": "PHI", "division": "Metropolitan", "conference": "Eastern"},
            {"name": "Pittsburgh Penguins", "abbreviation": "PIT", "division": "Metropolitan", "conference": "Eastern"},
            {"name": "Washington Capitals", "abbreviation": "WSH", "division": "Metropolitan", "conference": "Eastern"},
            {"name": "Chicago Blackhawks", "abbreviation": "CHI", "division": "Central", "conference": "Western"},
            {"name": "Colorado Avalanche", "abbreviation": "COL", "division": "Central", "conference": "Western"},
            {"name": "Dallas Stars", "abbreviation": "DAL", "division": "Central", "conference": "Western"},
            {"name": "Minnesota Wild", "abbreviation": "MIN", "division": "Central", "conference": "Western"},
            {"name": "Nashville Predators", "abbreviation": "NSH", "division": "Central", "conference": "Western"},
            {"name": "St. Louis Blues", "abbreviation": "STL", "division": "Central", "conference": "Western"},
            {"name": "Winnipeg Jets", "abbreviation": "WPG", "division": "Central", "conference": "Western"},
            {"name": "Anaheim Ducks", "abbreviation": "ANA", "division": "Pacific", "conference": "Western"},
            {"name": "Calgary Flames", "abbreviation": "CGY", "division": "Pacific", "conference": "Western"},
            {"name": "Edmonton Oilers", "abbreviation": "EDM", "division": "Pacific", "conference": "Western"},
            {"name": "Los Angeles Kings", "abbreviation": "LAK", "division": "Pacific", "conference": "Western"},
            {"name": "San Jose Sharks", "abbreviation": "SJS", "division": "Pacific", "conference": "Western"},
            {"name": "Seattle Kraken", "abbreviation": "SEA", "division": "Pacific", "conference": "Western"},
            {"name": "Vancouver Canucks", "abbreviation": "VAN", "division": "Pacific", "conference": "Western"},
            {"name": "Vegas Golden Knights", "abbreviation": "VGK", "division": "Pacific", "conference": "Western"},
            {"name": "Arizona Coyotes", "abbreviation": "ARI", "division": "Central", "conference": "Western"},
        ]
        
        # Check if teams exist
        for team_data in nhl_teams:
            team = db.query(Team).filter(Team.name == team_data["name"]).first()
            if not team:
                # Create team
                team = Team(
                    name=team_data["name"],
                    abbreviation=team_data["abbreviation"],
                    division=team_data["division"],
                    conference=team_data["conference"],
                )
                db.add(team)
        
        db.commit()
        logger.info("Ensured all NHL teams exist in the database")

    async def _fetch_games(self, days: int) -> List[Dict]:
        """
        Fetch NHL games data from external API (simulated).
        
        Args:
            days: Number of days to fetch
            
        Returns:
            List of games data
        """
        # In a real implementation, this would fetch data from an external API
        # For now, we'll simulate it with mock data
        
        # Generate some mock games
        now = datetime.utcnow()
        games = []
        
        # Sample teams for mock data
        teams = [
            "Boston Bruins",
            "Toronto Maple Leafs",
            "Tampa Bay Lightning",
            "Florida Panthers",
            "New York Rangers",
            "Carolina Hurricanes",
            "Colorado Avalanche",
            "Edmonton Oilers",
            "Vegas Golden Knights",
            "Dallas Stars",
        ]
        
        # Generate games for each day
        for day in range(days):
            game_date = now + timedelta(days=day)
            
            # Generate 3 games per day
            for i in range(3):
                home_idx = (day + i) % len(teams)
                away_idx = (day + i + 5) % len(teams)
                
                game_time = game_date.replace(hour=19, minute=0, second=0, microsecond=0)
                
                games.append({
                    "external_id": f"NHL{game_date.strftime('%Y%m%d')}{i+1}",
                    "home_team": teams[home_idx],
                    "away_team": teams[away_idx],
                    "game_time": game_time,
                    "status": "scheduled",
                })
        
        return games

    async def _fetch_draftkings_odds(self, game_external_id: str) -> Optional[Dict]:
        """
        Fetch odds from DraftKings API (simulated).
        
        Args:
            game_external_id: External ID of the game
            
        Returns:
            Odds data or None if not available
        """
        # In a real implementation, this would fetch data from the DraftKings API
        # For now, we'll simulate it with mock data
        
        # Simulate API call
        if not self.draftkings_api_key:
            logger.warning("DraftKings API key not configured")
            return None
        
        # Generate mock odds
        import random
        
        # 10% chance of no odds available
        if random.random() < 0.1:
            return None
        
        # Generate mock odds
        home_ml = random.choice([-120, -130, -140, -150, -160, 110, 120, 130, 140, 150])
        away_ml = -home_ml if home_ml > 0 else abs(home_ml) + 10
        
        spread = 1.5
        home_spread_odds = random.choice([-110, -115, -120, -125, -130])
        away_spread_odds = random.choice([-110, -115, -120, -125, -130])
        
        total = random.choice([5.5, 6.0, 6.5])
        over_odds = random.choice([-110, -115, -120, -125, -130])
        under_odds = random.choice([-110, -115, -120, -125, -130])
        
        return {
            "home_moneyline": home_ml,
            "away_moneyline": away_ml,
            "home_spread": -spread,
            "away_spread": spread,
            "home_spread_odds": home_spread_odds,
            "away_spread_odds": away_spread_odds,
            "over_under": total,
            "over_odds": over_odds,
            "under_odds": under_odds,
        }

    async def _fetch_fanduel_odds(self, game_external_id: str) -> Optional[Dict]:
        """
        Fetch odds from FanDuel API (simulated).
        
        Args:
            game_external_id: External ID of the game
            
        Returns:
            Odds data or None if not available
        """
        # In a real implementation, this would fetch data from the FanDuel API
        # For now, we'll simulate it with mock data
        
        # Simulate API call
        if not self.fanduel_api_key:
            logger.warning("FanDuel API key not configured")
            return None
        
        # Generate mock odds
        import random
        
        # 10% chance of no odds available
        if random.random() < 0.1:
            return None
        
        # Generate mock odds
        home_ml = random.choice([-125, -135, -145, -155, -165, 115, 125, 135, 145, 155])
        away_ml = -home_ml if home_ml > 0 else abs(home_ml) + 10
        
        spread = 1.5
        home_spread_odds = random.choice([-110, -115, -120, -125, -130])
        away_spread_odds = random.choice([-110, -115, -120, -125, -130])
        
        total = random.choice([5.5, 6.0, 6.5])
        over_odds = random.choice([-110, -115, -120, -125, -130])
        under_odds = random.choice([-110, -115, -120, -125, -130])
        
        return {
            "home_moneyline": home_ml,
            "away_moneyline": away_ml,
            "home_spread": -spread,
            "away_spread": spread,
            "home_spread_odds": home_spread_odds,
            "away_spread_odds": away_spread_odds,
            "over_under": total,
            "over_odds": over_odds,
            "under_odds": under_odds,
        }

    async def refresh_player_props(self, db: Session) -> int:
        """
        Refresh player props data from external APIs.
        
        Args:
            db: Database session
            
        Returns:
            Number of props updated
        """
        logger.info("Refreshing player props data")
        
        # Get upcoming games
        now = datetime.utcnow()
        future = now + timedelta(days=7)
        games = db.query(Game).filter(
            Game.game_time >= now,
            Game.game_time <= future,
            Game.status == "scheduled",
        ).all()
        
        props_updated = 0
        for game in games:
            # Refresh props for each game
            game_props_updated = await self.refresh_player_props_for_game(db, game.id)
            props_updated += game_props_updated
        
        logger.info(f"Updated props for {props_updated} games")
        return props_updated

    async def refresh_player_props_for_game(self, db: Session, game_id: int) -> int:
        """
        Refresh player props data for a specific game.
        
        Args:
            db: Database session
            game_id: ID of the game to refresh props for
            
        Returns:
            Number of props updated
        """
        logger.info(f"Refreshing player props for game {game_id}")
        
        # Get game
        game = db.query(Game).filter(Game.id == game_id).first()
        if not game:
            logger.warning(f"Game not found: {game_id}")
            return 0
        
        # Get players for both teams
        home_team_players = db.query(Player).filter(Player.team_id == game.home_team_id).all()
        away_team_players = db.query(Player).filter(Player.team_id == game.away_team_id).all()
        
        # Get odds for the game
        odds_list = db.query(Odds).filter(Odds.game_id == game_id).all()
        
        props_updated = 0
        for odds in odds_list:
            # Fetch player props for each sportsbook
            if odds.sportsbook == "DraftKings":
                home_props = await self._fetch_draftkings_player_props(game.external_id, home_team_players)
                away_props = await self._fetch_draftkings_player_props(game.external_id, away_team_players)
            elif odds.sportsbook == "FanDuel":
                home_props = await self._fetch_fanduel_player_props(game.external_id, home_team_players)
                away_props = await self._fetch_fanduel_player_props(game.external_id, away_team_players)
            else:
                continue
            
            # Combine props
            all_props = home_props + away_props
            
            # Update database with props data
            for prop_data in all_props:
                player_id = prop_data["player_id"]
                prop_type = prop_data["prop_type"]
                
                # Check if prop already exists
                existing_prop = db.query(PlayerProp).filter(
                    PlayerProp.odds_id == odds.id,
                    PlayerProp.player_id == player_id,
                    PlayerProp.prop_type == prop_type,
                ).first()
                
                if existing_prop:
                    # Update existing prop
                    existing_prop.line = prop_data["line"]
                    existing_prop.over_odds = prop_data["over_odds"]
                    existing_prop.under_odds = prop_data["under_odds"]
                    db.add(existing_prop)
                else:
                    # Create new prop
                    new_prop = PlayerProp(
                        odds_id=odds.id,
                        player_id=player_id,
                        prop_type=prop_type,
                        line=prop_data["line"],
                        over_odds=prop_data["over_odds"],
                        under_odds=prop_data["under_odds"],
                    )
                    db.add(new_prop)
                
                props_updated += 1
        
        db.commit()
        logger.info(f"Updated {props_updated} player props for game {game_id}")
        return props_updated

    async def refresh_player_props_for_player(self, db: Session, player_id: int) -> int:
        """
        Refresh player props data for a specific player.
        
        Args:
            db: Database session
            player_id: ID of the player to refresh props for
            
        Returns:
            Number of props updated
        """
        logger.info(f"Refreshing player props for player {player_id}")
        
        # Get player
        player = db.query(Player).filter(Player.id == player_id).first()
        if not player:
            logger.warning(f"Player not found: {player_id}")
            return 0
        
        # Get upcoming games for the player's team
        now = datetime.utcnow()
        future = now + timedelta(days=7)
        games = db.query(Game).filter(
            (Game.home_team_id == player.team_id) | (Game.away_team_id == player.team_id),
            Game.game_time >= now,
            Game.game_time <= future,
            Game.status == "scheduled",
        ).all()
        
        props_updated = 0
        for game in games:
            # Get odds for the game
            odds_list = db.query(Odds).filter(Odds.game_id == game.id).all()
            
            for odds in odds_list:
                # Fetch player props for the player
                if odds.sportsbook == "DraftKings":
                    props = await self._fetch_draftkings_player_props(game.external_id, [player])
                elif odds.sportsbook == "FanDuel":
                    props = await self._fetch_fanduel_player_props(game.external_id, [player])
                else:
                    continue
                
                # Update database with props data
                for prop_data in props:
                    prop_type = prop_data["prop_type"]
                    
                    # Check if prop already exists
                    existing_prop = db.query(PlayerProp).filter(
                        PlayerProp.odds_id == odds.id,
                        PlayerProp.player_id == player_id,
                        PlayerProp.prop_type == prop_type,
                    ).first()
                    
                    if existing_prop:
                        # Update existing prop
                        existing_prop.line = prop_data["line"]
                        existing_prop.over_odds = prop_data["over_odds"]
                        existing_prop.under_odds = prop_data["under_odds"]
                        db.add(existing_prop)
                    else:
                        # Create new prop
                        new_prop = PlayerProp(
                            odds_id=odds.id,
                            player_id=player_id,
                            prop_type=prop_type,
                            line=prop_data["line"],
                            over_odds=prop_data["over_odds"],
                            under_odds=prop_data["under_odds"],
                        )
                        db.add(new_prop)
                    
                    props_updated += 1
        
        db.commit()
        logger.info(f"Updated {props_updated} player props for player {player_id}")
        return props_updated

    async def _fetch_draftkings_player_props(self, game_external_id: str, players: List[Player]) -> List[Dict]:
        """
        Fetch player props from DraftKings API (simulated).
        
        Args:
            game_external_id: External ID of the game
            players: List of Player objects
            
        Returns:
            List of player props data
        """
        # In a real implementation, this would fetch data from the DraftKings API
        # For now, we'll simulate it with mock data
        
        # Simulate API call
        if not self.draftkings_api_key:
            logger.warning("DraftKings API key not configured")
            return []
        
        # Generate mock props
        import random
        
        props = []
        for player in players:
            # Skip 20% of players (not all players have props)
            if random.random() < 0.2:
                continue
            
            # Points prop (for forwards and defensemen)
            if player.position in ["C", "LW", "RW", "D"]:
                line = round(random.uniform(0.5, 2.5) * 2) / 2  # 0.5, 1.0, 1.5, 2.0, 2.5
                over_odds = random.choice([-110, -115, -120, -125, -130, -135, -140])
                under_odds = random.choice([-110, -115, -120, -125, -130, -135, -140])
                
                props.append({
                    "player_id": player.id,
                    "prop_type": "points",
                    "line": line,
                    "over_odds": over_odds,
                    "under_odds": under_odds,
                })
            
            # Goals prop (for forwards and defensemen)
            if player.position in ["C", "LW", "RW", "D"]:
                line = 0.5  # Most common line for goals
                over_odds = random.choice([120, 130, 140, 150, 160, 170, 180])
                under_odds = random.choice([-140, -150, -160, -170, -180, -190, -200])
                
                props.append({
                    "player_id": player.id,
                    "prop_type": "goals",
                    "line": line,
                    "over_odds": over_odds,
                    "under_odds": under_odds,
                })
            
            # Assists prop (for forwards and defensemen)
            if player.position in ["C", "LW", "RW", "D"]:
                line = 0.5  # Most common line for assists
                over_odds = random.choice([110, 120, 130, 140, 150, 160])
                under_odds = random.choice([-130, -140, -150, -160, -170, -180])
                
                props.append({
                    "player_id": player.id,
                    "prop_type": "assists",
                    "line": line,
                    "over_odds": over_odds,
                    "under_odds": under_odds,
                })
            
            # Shots on goal prop (for forwards and defensemen)
            if player.position in ["C", "LW", "RW", "D"]:
                line = round(random.uniform(1.5, 3.5) * 2) / 2  # 1.5, 2.0, 2.5, 3.0, 3.5
                over_odds = random.choice([-110, -115, -120, -125, -130])
                under_odds = random.choice([-110, -115, -120, -125, -130])
                
                props.append({
                    "player_id": player.id,
                    "prop_type": "shots_on_goal",
                    "line": line,
                    "over_odds": over_odds,
                    "under_odds": under_odds,
                })
        
        return props

    async def _fetch_fanduel_player_props(self, game_external_id: str, players: List[Player]) -> List[Dict]:
        """
        Fetch player props from FanDuel API (simulated).
        
        Args:
            game_external_id: External ID of the game
            players: List of Player objects
            
        Returns:
            List of player props data
        """
        # In a real implementation, this would fetch data from the FanDuel API
        # For now, we'll simulate it with mock data
        
        # Simulate API call
        if not self.fanduel_api_key:
            logger.warning("FanDuel API key not configured")
            return []
        
        # Generate mock props
        import random
        
        props = []
        for player in players:
            # Skip 20% of players (not all players have props)
            if random.random() < 0.2:
                continue
            
            # Points prop (for forwards and defensemen)
            if player.position in ["C", "LW", "RW", "D"]:
                line = round(random.uniform(0.5, 2.5) * 2) / 2  # 0.5, 1.0, 1.5, 2.0, 2.5
                over_odds = random.choice([-110, -115, -120, -125, -130, -135, -140])
                under_odds = random.choice([-110, -115, -120, -125, -130, -135, -140])
                
                props.append({
                    "player_id": player.id,
                    "prop_type": "points",
                    "line": line,
                    "over_odds": over_odds,
                    "under_odds": under_odds,
                })
            
            # Goals prop (for forwards and defensemen)
            if player.position in ["C", "LW", "RW", "D"]:
                line = 0.5  # Most common line for goals
                over_odds = random.choice([125, 135, 145, 155, 165, 175, 185])
                under_odds = random.choice([-145, -155, -165, -175, -185, -195, -205])
                
                props.append({
                    "player_id": player.id,
                    "prop_type": "goals",
                    "line": line,
                    "over_odds": over_odds,
                    "under_odds": under_odds,
                })
            
            # Assists prop (for forwards and defensemen)
            if player.position in ["C", "LW", "RW", "D"]:
                line = 0.5  # Most common line for assists
                over_odds = random.choice([115, 125, 135, 145, 155, 165])
                under_odds = random.choice([-135, -145, -155, -165, -175, -185])
                
                props.append({
                    "player_id": player.id,
                    "prop_type": "assists",
                    "line": line,
                    "over_odds": over_odds,
                    "under_odds": under_odds,
                })
            
            # Shots on goal prop (for forwards and defensemen)
            if player.position in ["C", "LW", "RW", "D"]:
                line = round(random.uniform(1.5, 3.5) * 2) / 2  # 1.5, 2.0, 2.5, 3.0, 3.5
                over_odds = random.choice([-110, -115, -120, -125, -130])
                under_odds = random.choice([-110, -115, -120, -125, -130])
                
                props.append({
                    "player_id": player.id,
                    "prop_type": "shots_on_goal",
                    "line": line,
                    "over_odds": over_odds,
                    "under_odds": under_odds,
                })
        
        return props
