"""API client for interacting with the FastAPI backend."""

import logging
from typing import Dict, List, Optional, Any

import httpx

logger = logging.getLogger(__name__)


class APIClient:
    """Client for interacting with the FastAPI backend."""

    def __init__(self, base_url: str):
        """
        Initialize the API client.
        
        Args:
            base_url: Base URL of the FastAPI backend
        """
        self.base_url = base_url
        self.client = httpx.Client(timeout=30.0)
    
    def get_games(
        self,
        date: Optional[str] = None,
        team_id: Optional[int] = None,
        status: Optional[str] = None,
        days: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get games from the API.
        
        Args:
            date: Date in YYYY-MM-DD format
            team_id: Filter by team ID
            status: Filter by game status
            days: Number of days to fetch
            
        Returns:
            List of games
        """
        params = {}
        if date:
            params["date"] = date
        if team_id:
            params["team_id"] = team_id
        if status:
            params["status"] = status
        if days:
            params["days"] = days
        
        response = self.client.get(f"{self.base_url}/api/games", params=params)
        response.raise_for_status()
        return response.json()
    
    def get_game(self, game_id: int) -> Dict[str, Any]:
        """
        Get a specific game from the API.
        
        Args:
            game_id: ID of the game
            
        Returns:
            Game data
        """
        response = self.client.get(f"{self.base_url}/api/games/{game_id}")
        response.raise_for_status()
        return response.json()
    
    def refresh_games(self, days: int = 7) -> Dict[str, Any]:
        """
        Refresh games data from external API.
        
        Args:
            days: Number of days to fetch
            
        Returns:
            Response data
        """
        response = self.client.get(f"{self.base_url}/api/games/refresh", params={"days": days})
        response.raise_for_status()
        return response.json()
    
    def get_teams(self) -> List[Dict[str, Any]]:
        """
        Get teams from the API.
        
        Returns:
            List of teams
        """
        response = self.client.get(f"{self.base_url}/api/teams")
        response.raise_for_status()
        return response.json()
    
    def get_team(self, team_id: int) -> Dict[str, Any]:
        """
        Get a specific team from the API.
        
        Args:
            team_id: ID of the team
            
        Returns:
            Team data
        """
        response = self.client.get(f"{self.base_url}/api/teams/{team_id}")
        response.raise_for_status()
        return response.json()
    
    def get_odds(
        self,
        game_id: Optional[int] = None,
        sportsbook: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get odds from the API.
        
        Args:
            game_id: Filter by game ID
            sportsbook: Filter by sportsbook
            
        Returns:
            List of odds
        """
        params = {}
        if game_id:
            params["game_id"] = game_id
        if sportsbook:
            params["sportsbook"] = sportsbook
        
        response = self.client.get(f"{self.base_url}/api/odds", params=params)
        response.raise_for_status()
        return response.json()
    
    def compare_odds(self, game_id: int) -> List[Dict[str, Any]]:
        """
        Compare odds for a specific game.
        
        Args:
            game_id: ID of the game
            
        Returns:
            List of odds for comparison
        """
        response = self.client.get(f"{self.base_url}/api/odds/compare", params={"game_id": game_id})
        response.raise_for_status()
        return response.json()
    
    def get_best_odds(self, game_id: int) -> Dict[str, Any]:
        """
        Get the best odds for a specific game.
        
        Args:
            game_id: ID of the game
            
        Returns:
            Best odds data
        """
        response = self.client.get(f"{self.base_url}/api/odds/best", params={"game_id": game_id})
        response.raise_for_status()
        return response.json()
    
    def refresh_odds(self, game_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Refresh odds data from external APIs.
        
        Args:
            game_id: ID of the game to refresh odds for
            
        Returns:
            Response data
        """
        params = {}
        if game_id:
            params["game_id"] = game_id
        
        response = self.client.get(f"{self.base_url}/api/odds/refresh", params=params)
        response.raise_for_status()
        return response.json()
    
    def get_player_props(
        self,
        player_id: Optional[int] = None,
        game_id: Optional[int] = None,
        prop_type: Optional[str] = None,
        sportsbook: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get player props from the API.
        
        Args:
            player_id: Filter by player ID
            game_id: Filter by game ID
            prop_type: Filter by prop type (points, goals, assists, shots_on_goal)
            sportsbook: Filter by sportsbook
            
        Returns:
            List of player props
        """
        params = {}
        if player_id:
            params["player_id"] = player_id
        if game_id:
            params["game_id"] = game_id
        if prop_type:
            params["prop_type"] = prop_type
        if sportsbook:
            params["sportsbook"] = sportsbook
        
        response = self.client.get(f"{self.base_url}/api/player-props", params=params)
        response.raise_for_status()
        return response.json()
    
    def get_player_prop(self, prop_id: int) -> Dict[str, Any]:
        """
        Get a specific player prop from the API.
        
        Args:
            prop_id: ID of the player prop
            
        Returns:
            Player prop data
        """
        response = self.client.get(f"{self.base_url}/api/player-props/{prop_id}")
        response.raise_for_status()
        return response.json()
    
    def refresh_player_props(
        self,
        player_id: Optional[int] = None,
        game_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Refresh player props data from external APIs.
        
        Args:
            player_id: ID of the player to refresh props for
            game_id: ID of the game to refresh props for
            
        Returns:
            Response data
        """
        params = {}
        if player_id:
            params["player_id"] = player_id
        if game_id:
            params["game_id"] = game_id
        
        response = self.client.get(f"{self.base_url}/api/player-props/refresh", params=params)
        response.raise_for_status()
        return response.json()
    
    def get_news(
        self,
        team_id: Optional[int] = None,
        player_id: Optional[int] = None,
        source: Optional[str] = None,
        days: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get news articles from the API.
        
        Args:
            team_id: Filter by team ID
            player_id: Filter by player ID
            source: Filter by source
            days: Number of days to look back
            limit: Maximum number of articles to return
            
        Returns:
            List of news articles
        """
        params = {}
        if team_id:
            params["team_id"] = team_id
        if player_id:
            params["player_id"] = player_id
        if source:
            params["source"] = source
        if days:
            params["days"] = days
        if limit:
            params["limit"] = limit
        
        response = self.client.get(f"{self.base_url}/api/news", params=params)
        response.raise_for_status()
        return response.json()
    
    def get_article(self, article_id: int) -> Dict[str, Any]:
        """
        Get a specific news article from the API.
        
        Args:
            article_id: ID of the article
            
        Returns:
            Article data
        """
        response = self.client.get(f"{self.base_url}/api/news/{article_id}")
        response.raise_for_status()
        return response.json()
    
    def refresh_news(
        self,
        source: Optional[str] = None,
        days: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Refresh news data from external sources.
        
        Args:
            source: Refresh news from a specific source
            days: Number of days to fetch
            
        Returns:
            Response data
        """
        params = {}
        if source:
            params["source"] = source
        if days:
            params["days"] = days
        
        response = self.client.get(f"{self.base_url}/api/news/refresh", params=params)
        response.raise_for_status()
        return response.json()
    
    def analyze_game(self, game_id: int, refresh: bool = False) -> Dict[str, Any]:
        """
        Get AI analysis for a specific game.
        
        Args:
            game_id: ID of the game
            refresh: Force refresh of analysis
            
        Returns:
            Analysis data
        """
        response = self.client.get(
            f"{self.base_url}/api/analysis/game/{game_id}",
            params={"refresh": str(refresh).lower()},
        )
        response.raise_for_status()
        return response.json()
    
    def analyze_team(self, team_id: int, refresh: bool = False) -> Dict[str, Any]:
        """
        Get AI analysis for a specific team.
        
        Args:
            team_id: ID of the team
            refresh: Force refresh of analysis
            
        Returns:
            Analysis data
        """
        response = self.client.get(
            f"{self.base_url}/api/analysis/team/{team_id}",
            params={"refresh": str(refresh).lower()},
        )
        response.raise_for_status()
        return response.json()
    
    def optimize_parlay(
        self,
        stake: float,
        game_ids: Optional[List[int]] = None,
        min_odds: Optional[float] = None,
        max_legs: Optional[int] = None,
        min_confidence: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Generate an optimized parlay.
        
        Args:
            stake: Amount to stake on the parlay
            game_ids: List of game IDs to consider
            min_odds: Minimum total odds
            max_legs: Maximum number of legs
            min_confidence: Minimum confidence score
            
        Returns:
            Parlay data
        """
        params = {"stake": stake}
        if game_ids:
            params["game_ids"] = game_ids
        if min_odds:
            params["min_odds"] = min_odds
        if max_legs:
            params["max_legs"] = max_legs
        if min_confidence:
            params["min_confidence"] = min_confidence
        
        response = self.client.post(f"{self.base_url}/api/analysis/parlay/optimize", params=params)
        response.raise_for_status()
        return response.json()
    
    def evaluate_parlay(self, parlay_id: int) -> Dict[str, Any]:
        """
        Evaluate an existing parlay.
        
        Args:
            parlay_id: ID of the parlay
            
        Returns:
            Evaluation data
        """
        response = self.client.post(
            f"{self.base_url}/api/analysis/parlay/evaluate",
            params={"parlay_id": parlay_id},
        )
        response.raise_for_status()
        return response.json()
    
    def get_parlays(
        self,
        status: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get parlays from the API.
        
        Args:
            status: Filter by status
            limit: Maximum number of parlays to return
            
        Returns:
            List of parlays
        """
        params = {}
        if status:
            params["status"] = status
        if limit:
            params["limit"] = limit
        
        response = self.client.get(f"{self.base_url}/api/parlays", params=params)
        response.raise_for_status()
        return response.json()
    
    def get_parlay(self, parlay_id: int) -> Dict[str, Any]:
        """
        Get a specific parlay from the API.
        
        Args:
            parlay_id: ID of the parlay
            
        Returns:
            Parlay data
        """
        response = self.client.get(f"{self.base_url}/api/parlays/{parlay_id}")
        response.raise_for_status()
        return response.json()
    
    def create_parlay(
        self,
        name: Optional[str],
        stake: float,
        bets: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Create a new parlay.
        
        Args:
            name: Name for the parlay
            stake: Amount to stake on the parlay
            bets: List of bets to include in the parlay
            
        Returns:
            Parlay data
        """
        data = {
            "stake": stake,
            "bets": bets,
        }
        if name:
            data["name"] = name
        
        response = self.client.post(f"{self.base_url}/api/parlays", json=data)
        response.raise_for_status()
        return response.json()
    
    def update_parlay_statuses(self) -> Dict[str, Any]:
        """
        Update the status of all pending parlays.
        
        Returns:
            Response data
        """
        response = self.client.get(f"{self.base_url}/api/parlays/update-status")
        response.raise_for_status()
        return response.json()
