"""Service for AI analysis using Claude/Anthropic."""

import logging
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any

import anthropic
from sqlalchemy.orm import Session

from backend.app.config import get_settings
from backend.app.core.models import AIAnalysis, Bet, Game, NewsArticle, Odds, Parlay, Player, Team

logger = logging.getLogger(__name__)


class AIService:
    """Service for AI analysis using Claude/Anthropic."""

    def __init__(self):
        """Initialize the AI service."""
        self.settings = get_settings()
        self.anthropic_api_key = self.settings.anthropic_api_key
        
        # Initialize Anthropic client if API key is available
        if self.anthropic_api_key:
            self.client = anthropic.Anthropic(api_key=self.anthropic_api_key)
        else:
            logger.warning("Anthropic API key not configured")
            self.client = None

    async def analyze_game(self, db: Session, game_id: int, refresh: bool = False) -> AIAnalysis:
        """
        Get AI analysis for a specific game.
        
        Args:
            db: Database session
            game_id: ID of the game to analyze
            refresh: Whether to force a refresh of the analysis
            
        Returns:
            AIAnalysis object
        """
        logger.info(f"Getting AI analysis for game {game_id}")
        
        # Check if recent analysis exists
        if not refresh:
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            existing_analysis = db.query(AIAnalysis).filter(
                AIAnalysis.analysis_type == f"game_{game_id}",
                AIAnalysis.created_at >= cutoff_time,
            ).order_by(AIAnalysis.created_at.desc()).first()
            
            if existing_analysis:
                logger.info(f"Using existing analysis for game {game_id}")
                return existing_analysis
        
        # Get game data
        game = db.query(Game).filter(Game.id == game_id).first()
        if not game:
            raise ValueError(f"Game not found: {game_id}")
        
        # Get odds data
        odds_list = db.query(Odds).filter(Odds.game_id == game_id).all()
        
        # Get news articles mentioning the teams
        home_team_articles = db.query(NewsArticle).filter(
            NewsArticle.teams.any(id=game.home_team_id),
            NewsArticle.published_date >= datetime.utcnow() - timedelta(days=7),
        ).order_by(NewsArticle.published_date.desc()).limit(5).all()
        
        away_team_articles = db.query(NewsArticle).filter(
            NewsArticle.teams.any(id=game.away_team_id),
            NewsArticle.published_date >= datetime.utcnow() - timedelta(days=7),
        ).order_by(NewsArticle.published_date.desc()).limit(5).all()
        
        # Get player data
        home_team_players = db.query(Player).filter(Player.team_id == game.home_team_id).all()
        away_team_players = db.query(Player).filter(Player.team_id == game.away_team_id).all()
        
        # Generate prompt for Claude
        prompt = self._generate_game_analysis_prompt(
            game,
            odds_list,
            home_team_articles,
            away_team_articles,
            home_team_players,
            away_team_players,
        )
        
        # Get analysis from Claude
        analysis_content, confidence_score = await self._get_claude_analysis(prompt)
        
        # Create new analysis
        new_analysis = AIAnalysis(
            analysis_type=f"game_{game_id}",
            content=analysis_content,
            confidence_score=confidence_score,
        )
        db.add(new_analysis)
        db.commit()
        db.refresh(new_analysis)
        
        logger.info(f"Created new analysis for game {game_id}")
        return new_analysis

    async def analyze_team(self, db: Session, team_id: int, refresh: bool = False) -> AIAnalysis:
        """
        Get AI analysis for a specific team.
        
        Args:
            db: Database session
            team_id: ID of the team to analyze
            refresh: Whether to force a refresh of the analysis
            
        Returns:
            AIAnalysis object
        """
        logger.info(f"Getting AI analysis for team {team_id}")
        
        # Check if recent analysis exists
        if not refresh:
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            existing_analysis = db.query(AIAnalysis).filter(
                AIAnalysis.analysis_type == f"team_{team_id}",
                AIAnalysis.created_at >= cutoff_time,
            ).order_by(AIAnalysis.created_at.desc()).first()
            
            if existing_analysis:
                logger.info(f"Using existing analysis for team {team_id}")
                return existing_analysis
        
        # Get team data
        team = db.query(Team).filter(Team.id == team_id).first()
        if not team:
            raise ValueError(f"Team not found: {team_id}")
        
        # Get recent games
        recent_home_games = db.query(Game).filter(
            Game.home_team_id == team_id,
            Game.game_time <= datetime.utcnow(),
        ).order_by(Game.game_time.desc()).limit(10).all()
        
        recent_away_games = db.query(Game).filter(
            Game.away_team_id == team_id,
            Game.game_time <= datetime.utcnow(),
        ).order_by(Game.game_time.desc()).limit(10).all()
        
        # Get upcoming games
        upcoming_games = db.query(Game).filter(
            (Game.home_team_id == team_id) | (Game.away_team_id == team_id),
            Game.game_time > datetime.utcnow(),
        ).order_by(Game.game_time).limit(5).all()
        
        # Get news articles
        news_articles = db.query(NewsArticle).filter(
            NewsArticle.teams.any(id=team_id),
            NewsArticle.published_date >= datetime.utcnow() - timedelta(days=7),
        ).order_by(NewsArticle.published_date.desc()).limit(10).all()
        
        # Get player data
        players = db.query(Player).filter(Player.team_id == team_id).all()
        
        # Generate prompt for Claude
        prompt = self._generate_team_analysis_prompt(
            team,
            recent_home_games,
            recent_away_games,
            upcoming_games,
            news_articles,
            players,
        )
        
        # Get analysis from Claude
        analysis_content, confidence_score = await self._get_claude_analysis(prompt)
        
        # Create new analysis
        new_analysis = AIAnalysis(
            analysis_type=f"team_{team_id}",
            content=analysis_content,
            confidence_score=confidence_score,
        )
        db.add(new_analysis)
        db.commit()
        db.refresh(new_analysis)
        
        logger.info(f"Created new analysis for team {team_id}")
        return new_analysis

    async def optimize_parlay(
        self,
        db: Session,
        stake: float,
        game_ids: Optional[List[int]] = None,
        min_odds: Optional[float] = None,
        max_legs: Optional[int] = None,
        min_confidence: Optional[float] = None,
    ) -> Parlay:
        """
        Generate an optimized parlay based on AI analysis.
        
        Args:
            db: Database session
            stake: Amount to stake on the parlay
            game_ids: List of game IDs to consider for the parlay
            min_odds: Minimum total odds for the parlay
            max_legs: Maximum number of legs in the parlay
            min_confidence: Minimum confidence score for each leg
            
        Returns:
            Parlay object
        """
        logger.info("Generating optimized parlay")
        
        # Get upcoming games
        query = db.query(Game).filter(
            Game.game_time > datetime.utcnow(),
            Game.status == "scheduled",
        )
        
        # Apply game filter if provided
        if game_ids:
            query = query.filter(Game.id.in_(game_ids))
        
        # Order by game time
        query = query.order_by(Game.game_time)
        
        # Limit to next 7 days
        cutoff_time = datetime.utcnow() + timedelta(days=7)
        query = query.filter(Game.game_time <= cutoff_time)
        
        # Apply max legs filter if provided
        if max_legs:
            query = query.limit(max_legs * 2)  # Get more games than needed to allow for filtering
        
        games = query.all()
        
        if not games:
            raise ValueError("No upcoming games found")
        
        # Get odds for each game
        game_odds = {}
        for game in games:
            odds_list = db.query(Odds).filter(Odds.game_id == game.id).all()
            if odds_list:
                game_odds[game.id] = odds_list
        
        # Generate prompt for Claude
        prompt = self._generate_parlay_optimization_prompt(
            games,
            game_odds,
            stake,
            min_odds,
            max_legs,
            min_confidence,
            db,
        )
        
        # Get analysis from Claude
        parlay_data, confidence_score = await self._get_claude_parlay(prompt)
        
        # Create parlay
        parlay = Parlay(
            name=parlay_data.get("name", "AI-Generated Parlay"),
            stake=stake,
            total_odds=parlay_data["total_odds"],
            potential_payout=stake * parlay_data["total_odds"],
            confidence_score=confidence_score,
            status="pending",
        )
        db.add(parlay)
        db.flush()  # Flush to get the parlay ID
        
        # Create bets
        for bet_data in parlay_data["bets"]:
            bet = Bet(
                parlay_id=parlay.id,
                game_id=bet_data["game_id"],
                bet_type=bet_data["bet_type"],
                selection=bet_data["selection"],
                odds=bet_data["odds"],
                justification=bet_data["justification"],
                status="pending",
            )
            
            # Add player prop fields if applicable
            if bet_data["bet_type"] == "player_prop":
                bet.player_id = bet_data.get("player_id")
                bet.prop_type = bet_data.get("prop_type")
            
            db.add(bet)
        
        db.commit()
        db.refresh(parlay)
        
        logger.info(f"Created optimized parlay with {len(parlay.bets)} legs")
        return parlay

    async def evaluate_parlay(self, db: Session, parlay_id: int) -> AIAnalysis:
        """
        Evaluate an existing parlay using AI analysis.
        
        Args:
            db: Database session
            parlay_id: ID of the parlay to evaluate
            
        Returns:
            AIAnalysis object
        """
        logger.info(f"Evaluating parlay {parlay_id}")
        
        # Get parlay data
        parlay = db.query(Parlay).filter(Parlay.id == parlay_id).first()
        if not parlay:
            raise ValueError(f"Parlay not found: {parlay_id}")
        
        # Get bets data
        bets = db.query(Bet).filter(Bet.parlay_id == parlay_id).all()
        if not bets:
            raise ValueError(f"No bets found for parlay: {parlay_id}")
        
        # Get game data for each bet
        games = {}
        for bet in bets:
            game = db.query(Game).filter(Game.id == bet.game_id).first()
            if game:
                games[bet.game_id] = game
        
        # Get odds data for each game
        odds = {}
        for game_id in games:
            odds_list = db.query(Odds).filter(Odds.game_id == game_id).all()
            if odds_list:
                odds[game_id] = odds_list
        
        # Generate prompt for Claude
        prompt = self._generate_parlay_evaluation_prompt(
            parlay,
            bets,
            games,
            odds,
        )
        
        # Get analysis from Claude
        analysis_content, confidence_score = await self._get_claude_analysis(prompt)
        
        # Create new analysis
        new_analysis = AIAnalysis(
            analysis_type=f"parlay_{parlay_id}",
            content=analysis_content,
            confidence_score=confidence_score,
        )
        db.add(new_analysis)
        db.commit()
        db.refresh(new_analysis)
        
        logger.info(f"Created evaluation for parlay {parlay_id}")
        return new_analysis

    def _generate_game_analysis_prompt(
        self,
        game: Game,
        odds_list: List[Odds],
        home_team_articles: List[NewsArticle],
        away_team_articles: List[NewsArticle],
        home_team_players: List[Player],
        away_team_players: List[Player],
    ) -> str:
        """
        Generate a prompt for Claude to analyze a game.
        
        Args:
            game: Game object
            odds_list: List of Odds objects
            home_team_articles: List of NewsArticle objects for the home team
            away_team_articles: List of NewsArticle objects for the away team
            home_team_players: List of Player objects for the home team
            away_team_players: List of Player objects for the away team
            
        Returns:
            Prompt string
        """
        # Format game data
        game_data = {
            "id": game.id,
            "home_team": {
                "name": game.home_team.name,
                "abbreviation": game.home_team.abbreviation,
            },
            "away_team": {
                "name": game.away_team.name,
                "abbreviation": game.away_team.abbreviation,
            },
            "game_time": game.game_time.isoformat(),
            "status": game.status,
        }
        
        # Format odds data
        odds_data = []
        player_props_data = []
        
        for odds in odds_list:
            odds_obj = {
                "sportsbook": odds.sportsbook,
                "home_moneyline": odds.home_moneyline,
                "away_moneyline": odds.away_moneyline,
                "home_spread": odds.home_spread,
                "away_spread": odds.away_spread,
                "home_spread_odds": odds.home_spread_odds,
                "away_spread_odds": odds.away_spread_odds,
                "over_under": odds.over_under,
                "over_odds": odds.over_odds,
                "under_odds": odds.under_odds,
            }
            odds_data.append(odds_obj)
            
            # Get player props for this odds
            for prop in odds.player_props:
                player = None
                for p in home_team_players + away_team_players:
                    if p.id == prop.player_id:
                        player = p
                        break
                
                if player:
                    team = "home" if player.team_id == game.home_team_id else "away"
                    player_props_data.append({
                        "sportsbook": odds.sportsbook,
                        "player_name": player.name,
                        "team": team,
                        "position": player.position,
                        "prop_type": prop.prop_type,
                        "line": prop.line,
                        "over_odds": prop.over_odds,
                        "under_odds": prop.under_odds,
                    })
        
        # Format news articles
        home_articles_data = []
        for article in home_team_articles:
            home_articles_data.append({
                "title": article.title,
                "source": article.source,
                "published_date": article.published_date.isoformat(),
                "summary": article.summary,
                "content": article.content[:500] + "..." if len(article.content) > 500 else article.content,
            })
        
        away_articles_data = []
        for article in away_team_articles:
            away_articles_data.append({
                "title": article.title,
                "source": article.source,
                "published_date": article.published_date.isoformat(),
                "summary": article.summary,
                "content": article.content[:500] + "..." if len(article.content) > 500 else article.content,
            })
        
        # Format player data
        home_players_data = []
        for player in home_team_players:
            home_players_data.append({
                "name": player.name,
                "position": player.position,
                "is_injured": player.is_injured,
                "injury_details": player.injury_details,
            })
        
        away_players_data = []
        for player in away_team_players:
            away_players_data.append({
                "name": player.name,
                "position": player.position,
                "is_injured": player.is_injured,
                "injury_details": player.injury_details,
            })
        
        # Build prompt
        prompt = f"""
        You are an expert NHL analyst and sports betting advisor. Please analyze the following NHL game and provide insights for betting purposes.

        GAME INFORMATION:
        {json.dumps(game_data, indent=2)}

        BETTING ODDS:
        {json.dumps(odds_data, indent=2)}

        PLAYER PROPS:
        {json.dumps(player_props_data, indent=2)}

        HOME TEAM PLAYERS:
        {json.dumps(home_players_data, indent=2)}

        AWAY TEAM PLAYERS:
        {json.dumps(away_players_data, indent=2)}

        RECENT NEWS ABOUT HOME TEAM:
        {json.dumps(home_articles_data, indent=2)}

        RECENT NEWS ABOUT AWAY TEAM:
        {json.dumps(away_articles_data, indent=2)}

        Please provide a comprehensive analysis of this game, including:
        1. Team comparison and recent performance
        2. Key player matchups and injury impacts
        3. Betting recommendations (moneyline, spread, over/under)
        4. Player prop betting recommendations
        5. Confidence level for each recommendation (on a scale of 0.0 to 1.0)
        6. Justification for each recommendation

        Format your response as a detailed analysis that would be helpful for someone making betting decisions. Include a confidence score between 0.0 and 1.0 for your overall analysis.
        """
        
        return prompt

    def _generate_team_analysis_prompt(
        self,
        team: Team,
        recent_home_games: List[Game],
        recent_away_games: List[Game],
        upcoming_games: List[Game],
        news_articles: List[NewsArticle],
        players: List[Player],
    ) -> str:
        """
        Generate a prompt for Claude to analyze a team.
        
        Args:
            team: Team object
            recent_home_games: List of recent home Game objects
            recent_away_games: List of recent away Game objects
            upcoming_games: List of upcoming Game objects
            news_articles: List of NewsArticle objects
            players: List of Player objects
            
        Returns:
            Prompt string
        """
        # Format team data
        team_data = {
            "id": team.id,
            "name": team.name,
            "abbreviation": team.abbreviation,
            "division": team.division,
            "conference": team.conference,
        }
        
        # Format recent home games
        home_games_data = []
        for game in recent_home_games:
            home_games_data.append({
                "id": game.id,
                "opponent": game.away_team.name,
                "game_time": game.game_time.isoformat(),
                "status": game.status,
                "home_score": game.home_score,
                "away_score": game.away_score,
            })
        
        # Format recent away games
        away_games_data = []
        for game in recent_away_games:
            away_games_data.append({
                "id": game.id,
                "opponent": game.home_team.name,
                "game_time": game.game_time.isoformat(),
                "status": game.status,
                "home_score": game.home_score,
                "away_score": game.away_score,
            })
        
        # Format upcoming games
        upcoming_games_data = []
        for game in upcoming_games:
            if game.home_team_id == team.id:
                opponent = game.away_team.name
                is_home = True
            else:
                opponent = game.home_team.name
                is_home = False
            
            upcoming_games_data.append({
                "id": game.id,
                "opponent": opponent,
                "is_home": is_home,
                "game_time": game.game_time.isoformat(),
            })
        
        # Format news articles
        articles_data = []
        for article in news_articles:
            articles_data.append({
                "title": article.title,
                "source": article.source,
                "published_date": article.published_date.isoformat(),
                "summary": article.summary,
                "content": article.content[:500] + "..." if len(article.content) > 500 else article.content,
            })
        
        # Format player data
        players_data = []
        for player in players:
            players_data.append({
                "name": player.name,
                "position": player.position,
                "is_injured": player.is_injured,
                "injury_details": player.injury_details,
            })
        
        # Build prompt
        prompt = f"""
        You are an expert NHL analyst and sports betting advisor. Please analyze the following NHL team and provide insights for betting purposes.

        TEAM INFORMATION:
        {json.dumps(team_data, indent=2)}

        PLAYERS:
        {json.dumps(players_data, indent=2)}

        RECENT HOME GAMES:
        {json.dumps(home_games_data, indent=2)}

        RECENT AWAY GAMES:
        {json.dumps(away_games_data, indent=2)}

        UPCOMING GAMES:
        {json.dumps(upcoming_games_data, indent=2)}

        RECENT NEWS:
        {json.dumps(articles_data, indent=2)}

        Please provide a comprehensive analysis of this team, including:
        1. Recent performance and trends
        2. Key players and their impact
        3. Injury situation and implications
        4. Outlook for upcoming games
        5. Betting recommendations for upcoming games
        6. Confidence level for each recommendation (on a scale of 0.0 to 1.0)

        Format your response as a detailed analysis that would be helpful for someone making betting decisions. Include a confidence score between 0.0 and 1.0 for your overall analysis.
        """
        
        return prompt

    def _generate_parlay_optimization_prompt(
        self,
        games: List[Game],
        game_odds: Dict[int, List[Odds]],
        stake: float,
        min_odds: Optional[float] = None,
        max_legs: Optional[int] = None,
        min_confidence: Optional[float] = None,
        db: Optional[Session] = None,
    ) -> str:
        """
        Generate a prompt for Claude to optimize a parlay.
        
        Args:
            games: List of Game objects
            game_odds: Dictionary mapping game IDs to lists of Odds objects
            stake: Amount to stake on the parlay
            min_odds: Minimum total odds for the parlay
            max_legs: Maximum number of legs in the parlay
            min_confidence: Minimum confidence score for each leg
            
        Returns:
            Prompt string
        """
        # Format games data
        games_data = []
        for game in games:
            game_data = {
                "id": game.id,
                "home_team": {
                    "name": game.home_team.name,
                    "abbreviation": game.home_team.abbreviation,
                },
                "away_team": {
                    "name": game.away_team.name,
                    "abbreviation": game.away_team.abbreviation,
                },
                "game_time": game.game_time.isoformat(),
                "odds": [],
                "player_props": [],
            }
            
            # Add odds data
            if game.id in game_odds:
                for odds in game_odds[game.id]:
                    odds_obj = {
                        "sportsbook": odds.sportsbook,
                        "home_moneyline": odds.home_moneyline,
                        "away_moneyline": odds.away_moneyline,
                        "home_spread": odds.home_spread,
                        "away_spread": odds.away_spread,
                        "home_spread_odds": odds.home_spread_odds,
                        "away_spread_odds": odds.away_spread_odds,
                        "over_under": odds.over_under,
                        "over_odds": odds.over_odds,
                        "under_odds": odds.under_odds,
                    }
                    game_data["odds"].append(odds_obj)
                    
                    # Add player props
                    for prop in odds.player_props:
                        # Get player
                        player = None
                        from backend.app.core.models import Player
                        player = db.query(Player).filter(Player.id == prop.player_id).first()
                        
                        if player:
                            team = "home" if player.team_id == game.home_team_id else "away"
                            game_data["player_props"].append({
                                "sportsbook": odds.sportsbook,
                                "player_id": player.id,
                                "player_name": player.name,
                                "team": team,
                                "position": player.position,
                                "prop_type": prop.prop_type,
                                "line": prop.line,
                                "over_odds": prop.over_odds,
                                "under_odds": prop.under_odds,
                            })
            
            games_data.append(game_data)
        
        # Build prompt
        prompt = f"""
        You are an expert NHL analyst and sports betting advisor. Please create an optimized parlay based on the following NHL games.

        GAMES:
        {json.dumps(games_data, indent=2)}

        PARAMETERS:
        - Stake: ${stake}
        - Minimum Total Odds: {min_odds if min_odds is not None else 'Not specified'}
        - Maximum Legs: {max_legs if max_legs is not None else 'Not specified'}
        - Minimum Confidence: {min_confidence if min_confidence is not None else 'Not specified'}

        Please create an optimized parlay that maximizes potential return while considering confidence scores. For each leg of the parlay, select the best bet type (moneyline, spread, over/under) and the best odds available from the different sportsbooks.

        Your response should be in JSON format with the following structure:
        {{
          "name": "Name of the parlay",
          "total_odds": 0.0,
          "bets": [
            {{
              "game_id": 0,
              "bet_type": "moneyline|spread|over_under|player_prop",
              "selection": "home|away|over|under",
              "player_id": 0,  // Only for player_prop bets
              "prop_type": "points|goals|assists|shots_on_goal",  // Only for player_prop bets
              "odds": 0.0,
              "justification": "Justification for this bet"
            }}
          ]
        }}

        Also include a confidence score between 0.0 and 1.0 for the overall parlay.
        """
        
        return prompt

    def _generate_parlay_evaluation_prompt(
        self,
        parlay: Parlay,
        bets: List[Bet],
        games: Dict[int, Game],
        odds: Dict[int, List[Odds]],
    ) -> str:
        """
        Generate a prompt for Claude to evaluate a parlay.
        
        Args:
            parlay: Parlay object
            bets: List of Bet objects
            games: Dictionary mapping game IDs to Game objects
            odds: Dictionary mapping game IDs to lists of Odds objects
            
        Returns:
            Prompt string
        """
        # Format parlay data
        parlay_data = {
            "id": parlay.id,
            "name": parlay.name,
            "stake": parlay.stake,
            "total_odds": parlay.total_odds,
            "potential_payout": parlay.potential_payout,
            "status": parlay.status,
        }
        
        # Format bets data
        bets_data = []
        for bet in bets:
            bet_data = {
                "id": bet.id,
                "bet_type": bet.bet_type,
                "selection": bet.selection,
                "odds": bet.odds,
                "justification": bet.justification,
                "status": bet.status,
            }
            
            # Add game data
            if bet.game_id in games:
                game = games[bet.game_id]
                bet_data["game"] = {
                    "id": game.id,
                    "home_team": {
                        "name": game.home_team.name,
                        "abbreviation": game.home_team.abbreviation,
                    },
                    "away_team": {
                        "name": game.away_team.name,
                        "abbreviation": game.away_team.abbreviation,
                    },
                    "game_time": game.game_time.isoformat(),
                    "status": game.status,
                }
                
                # Add odds data
                if bet.game_id in odds:
                    bet_data["game"]["odds"] = []
                    for odds_obj in odds[bet.game_id]:
                        bet_data["game"]["odds"].append({
                            "sportsbook": odds_obj.sportsbook,
                            "home_moneyline": odds_obj.home_moneyline,
                            "away_moneyline": odds_obj.away_moneyline,
                            "home_spread": odds_obj.home_spread,
                            "away_spread": odds_obj.away_spread,
                            "home_spread_odds": odds_obj.home_spread_odds,
                            "away_spread_odds": odds_obj.away_spread_odds,
                            "over_under": odds_obj.over_under,
                            "over_odds": odds_obj.over_odds,
                            "under_odds": odds_obj.under_odds,
                        })
            
            bets_data.append(bet_data)
        
        # Build prompt
        prompt = f"""
        You are an expert NHL analyst and sports betting advisor. Please evaluate the following NHL parlay and provide insights.

        PARLAY:
        {json.dumps(parlay_data, indent=2)}

        BETS:
        {json.dumps(bets_data, indent=2)}

        Please provide a comprehensive evaluation of this parlay, including:
        1. Analysis of each leg of the parlay
        2. Strengths and weaknesses of the parlay
        3. Suggestions for improvement
        4. Overall assessment of the parlay's value
        5. Confidence level for the parlay (on a scale of 0.0 to 1.0)

        Format your response as a detailed analysis that would be helpful for someone making betting decisions. Include a confidence score between 0.0 and 1.0 for your overall evaluation.
        """
        
        return prompt

    async def _get_claude_analysis(self, prompt: str) -> Tuple[str, float]:
        """
        Get analysis from Claude.
        
        Args:
            prompt: Prompt string
            
        Returns:
            Tuple of (analysis_content, confidence_score)
        """
        if not self.client:
            # If no API key, return mock data
            return self._get_mock_analysis(prompt)
        
        try:
            # Call Claude API
            response = self.client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=4000,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
            )
            
            # Extract content
            content = response.content[0].text
            
            # Extract confidence score
            confidence_score = 0.7  # Default
            confidence_match = re.search(r"confidence score[:\s]+([0-9.]+)", content, re.IGNORECASE)
            if confidence_match:
                try:
                    confidence_score = float(confidence_match.group(1))
                    # Ensure it's in the range [0, 1]
                    confidence_score = max(0.0, min(1.0, confidence_score))
                except ValueError:
                    pass
            
            return content, confidence_score
        
        except Exception as e:
            logger.error(f"Error calling Claude API: {str(e)}")
            # Fall back to mock data
            return self._get_mock_analysis(prompt)

    async def _get_claude_parlay(self, prompt: str) -> Tuple[Dict[str, Any], float]:
        """
        Get parlay data from Claude.
        
        Args:
            prompt: Prompt string
            
        Returns:
            Tuple of (parlay_data, confidence_score)
        """
        if not self.client:
            # If no API key, return mock data
            return self._get_mock_parlay(prompt)
        
        try:
            # Call Claude API
            response = self.client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=4000,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
            )
            
            # Extract content
            content = response.content[0].text
            
            # Extract JSON data
            import re
            json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
            if not json_match:
                # Try without the code block
                json_match = re.search(r'({.*})', content, re.DOTALL)
            
            if json_match:
                json_str = json_match.group(1)
                parlay_data = json.loads(json_str)
            else:
                # Fallback to mock data if JSON parsing fails
                logger.warning("Failed to parse JSON from Claude response")
                return self._get_mock_parlay(prompt)
            
            # Extract confidence score
            confidence_score = 0.7  # Default
            confidence_match = re.search(r"confidence score[:\s]+([0-9.]+)", content, re.IGNORECASE)
            if confidence_match:
                try:
                    confidence_score = float(confidence_match.group(1))
                    # Ensure it's in the range [0, 1]
                    confidence_score = max(0.0, min(1.0, confidence_score))
                except ValueError:
                    pass
            
            return parlay_data, confidence_score
        
        except Exception as e:
            logger.error(f"Error calling Claude API: {str(e)}")
            # Fall back to mock data
            return self._get_mock_parlay(prompt)

    def _get_mock_analysis(self, prompt: str) -> Tuple[str, float]:
        """
        Get mock analysis when Claude API is not available.
        
        Args:
            prompt: Prompt string
            
        Returns:
            Tuple of (analysis_content, confidence_score)
        """
        logger.warning("Using mock analysis data")
        
        # Extract game or team info from prompt
        import re
        
        # Check if it's a game analysis
        game_match = re.search(r'"home_team":\s*{\s*"name":\s*"([^"]+)"', prompt)
        away_match = re.search(r'"away_team":\s*{\s*"name":\s*"([^"]+)"', prompt)
        
        if game_match and away_match:
            home_team = game_match.group(1)
            away_team = away_match.group(1)
            
            analysis = f"""
            # {home_team} vs. {away_team} - Game Analysis
            
            ## Team Comparison and Recent Performance
            
            The {home_team} have been showing strong form in their recent games, with solid defensive play and consistent offensive production. Their home record has been particularly impressive, giving them an advantage in this matchup.
            
            The {away_team} have been more inconsistent, with flashes of brilliance mixed with concerning defensive lapses. Their road performance has been below average, which could be a factor in this game.
            
            ## Key Player Matchups and Injury Impacts
            
            The {home_team}'s top line has been producing at an elite level, and they should have favorable matchups against the {away_team}'s defensive pairings. The {home_team}'s goaltending has also been steady.
            
            For the {away_team}, their success will depend heavily on their top players' performance. They'll need their stars to step up to overcome the home-ice disadvantage.
            
            ## Betting Recommendations
            
            ### Moneyline: {home_team} (-130)
            - Confidence: 0.75
            - Justification: The {home_team}'s home record and current form give them a clear edge in this matchup.
            
            ### Spread: {home_team} -1.5 (+180)
            - Confidence: 0.60
            - Justification: While the {home_team} should win, the value on the puck line is worth considering given the plus odds.
            
            ### Total: Under 6.5 (-110)
            - Confidence: 0.65
            - Justification: Both teams have been playing relatively tight defensive games recently, and this trend should continue.
            
            ## Overall Confidence Score: 0.70
            
            The {home_team} should win this game, but expect it to be competitive. The moneyline bet on the {home_team} offers the best combination of value and probability.
            """
        else:
            # Team analysis
            team_match = re.search(r'"name":\s*"([^"]+)"', prompt)
            team_name = team_match.group(1) if team_match else "Team"
            
            analysis = f"""
            # {team_name} - Team Analysis
            
            ## Recent Performance and Trends
            
            The {team_name} have shown mixed results over their last 10 games, with a record of 6-3-1. Their offensive production has been consistent, averaging 3.2 goals per game, but their defensive play has been somewhat inconsistent, particularly on the penalty kill.
            
            ## Key Players and Their Impact
            
            The top line continues to drive the team's offensive production, with particularly strong performances from the first-line center and right wing. The defensive corps has been solid, though not spectacular, with the top pair logging heavy minutes.
            
            The goaltending has been a strength, with a .918 save percentage over the last 10 games, keeping the team in games even when they've been outplayed.
            
            ## Injury Situation and Implications
            
            The team is relatively healthy, with only one significant injury to a bottom-six forward. This has allowed for consistent line combinations and defensive pairings, contributing to their recent success.
            
            ## Outlook for Upcoming Games
            
            The schedule over the next week includes three home games and one road game. The home games are against teams with varying strengths, but the {team_name} should be competitive in all of them.
            
            ## Betting Recommendations
            
            For the upcoming home game against a weaker opponent:
            - Moneyline: {team_name} (-150) - Confidence: 0.80
            - Puck Line: {team_name} -1.5 (+170) - Confidence: 0.65
            - Total: Over 6.0 (-110) - Confidence: 0.70
            
            For the road game against a stronger opponent:
            - Moneyline: {team_name} (+130) - Confidence: 0.55
            - Puck Line: {team_name} +1.5 (-160) - Confidence: 0.75
            - Total: Under 6.5 (-105) - Confidence: 0.60
            
            ## Overall Confidence Score: 0.70
            
            The {team_name} are in good form and should perform well in their upcoming games, particularly at home. Their consistent offensive production makes them a good bet on the moneyline in favorable matchups.
            """
        
        return analysis, 0.70

    def _get_mock_parlay(self, prompt: str) -> Tuple[Dict[str, Any], float]:
        """
        Get mock parlay data when Claude API is not available.
        
        Args:
            prompt: Prompt string
            
        Returns:
            Tuple of (parlay_data, confidence_score)
        """
        logger.warning("Using mock parlay data")
        
        # Extract stake from prompt
        import re
        stake_match = re.search(r'Stake:\s*\$([0-9.]+)', prompt)
        stake = float(stake_match.group(1)) if stake_match else 100.0
        
        # Create mock parlay data
        parlay_data = {
            "name": "NHL 3-Leg Value Parlay",
            "total_odds": 6.25,
            "bets": [
                {
                    "game_id": 1,
                    "bet_type": "moneyline",
                    "selection": "home",
                    "odds": 1.75,
                    "justification": "The home team has a strong home record and matchup advantages against the visiting team."
                },
                {
                    "game_id": 2,
                    "bet_type": "over_under",
                    "selection": "under",
                    "odds": 1.91,
                    "justification": "Both teams have strong goaltending and have been playing low-scoring games recently."
                },
                {
                    "game_id": 3,
                    "bet_type": "spread",
                    "selection": "away",
                    "odds": 1.87,
                    "justification": "The away team has been performing well on the road and should keep this game close."
                }
            ]
        }
        
        return parlay_data, 0.75
