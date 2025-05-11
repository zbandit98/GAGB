"""Service for parlay management."""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from sqlalchemy.orm import Session

from backend.app.core.models import Bet, Game, Odds, Parlay

logger = logging.getLogger(__name__)


class ParlayService:
    """Service for parlay management."""

    async def create_parlay(
        self,
        db: Session,
        name: Optional[str],
        stake: float,
        bets_data: List[Dict[str, Any]],
    ) -> Parlay:
        """
        Create a new parlay.
        
        Args:
            db: Database session
            name: Name for the parlay
            stake: Amount to stake on the parlay
            bets_data: List of bets to include in the parlay
            
        Returns:
            Parlay object
        """
        logger.info(f"Creating parlay with {len(bets_data)} bets")
        
        # Calculate total odds
        total_odds = 1.0
        for bet_data in bets_data:
            # Get odds from database if not provided
            if "odds" not in bet_data:
                game_id = bet_data["game_id"]
                bet_type = bet_data["bet_type"]
                selection = bet_data["selection"]
                
                # Get odds from database
                player_id = bet_data.get("player_id")
                prop_type = bet_data.get("prop_type")
                odds_obj = self._get_odds_for_bet(db, game_id, bet_type, selection, player_id, prop_type)
                if odds_obj:
                    bet_data["odds"] = odds_obj
                else:
                    raise ValueError(f"Could not find odds for bet: {bet_data}")
            
            total_odds *= bet_data["odds"]
        
        # Create parlay
        parlay = Parlay(
            name=name or "Custom Parlay",
            stake=stake,
            total_odds=total_odds,
            potential_payout=stake * total_odds,
            confidence_score=0.5,  # Default confidence score
            status="pending",
        )
        db.add(parlay)
        db.flush()  # Flush to get the parlay ID
        
        # Create bets
        for bet_data in bets_data:
            # Create bet with common fields
            bet = Bet(
                parlay_id=parlay.id,
                game_id=bet_data["game_id"],
                bet_type=bet_data["bet_type"],
                selection=bet_data["selection"],
                odds=bet_data["odds"],
                justification=bet_data.get("justification", "User selection"),
                status="pending",
            )
            
            # Add player prop fields if applicable
            if bet_data["bet_type"] == "player_prop":
                bet.player_id = bet_data.get("player_id")
                bet.prop_type = bet_data.get("prop_type")
            
            db.add(bet)
        
        db.commit()
        db.refresh(parlay)
        
        logger.info(f"Created parlay {parlay.id} with {len(parlay.bets)} bets")
        return parlay

    async def update_parlay_statuses(self, db: Session) -> int:
        """
        Update the status of all pending parlays.
        
        Args:
            db: Database session
            
        Returns:
            Number of parlays updated
        """
        logger.info("Updating parlay statuses")
        
        # Get all pending parlays
        pending_parlays = db.query(Parlay).filter(Parlay.status == "pending").all()
        
        updated_count = 0
        for parlay in pending_parlays:
            # Get all bets for the parlay
            bets = db.query(Bet).filter(Bet.parlay_id == parlay.id).all()
            
            # Check if all games are finished
            all_games_finished = True
            for bet in bets:
                game = db.query(Game).filter(Game.id == bet.game_id).first()
                if not game or game.status != "finished":
                    all_games_finished = False
                    break
            
            if all_games_finished:
                # Update bet statuses
                for bet in bets:
                    bet.status = self._determine_bet_status(db, bet)
                    db.add(bet)
                
                # Update parlay status
                parlay.status = self._determine_parlay_status(bets)
                db.add(parlay)
                
                updated_count += 1
        
        db.commit()
        logger.info(f"Updated {updated_count} parlays")
        return updated_count

    def _get_odds_for_bet(
        self,
        db: Session,
        game_id: int,
        bet_type: str,
        selection: str,
        player_id: Optional[int] = None,
        prop_type: Optional[str] = None,
    ) -> Optional[float]:
        """
        Get odds for a specific bet.
        
        Args:
            db: Database session
            game_id: ID of the game
            bet_type: Type of bet (moneyline, spread, over_under, player_prop)
            selection: Selection for the bet (home, away, over, under)
            player_id: ID of the player (for player props)
            prop_type: Type of prop (points, goals, assists, shots_on_goal)
            
        Returns:
            Odds value or None if not found
        """
        # Get all odds for the game
        odds_list = db.query(Odds).filter(Odds.game_id == game_id).all()
        
        if not odds_list:
            return None
        
        # Find the best odds for the bet
        best_odds = None
        for odds in odds_list:
            if bet_type == "moneyline":
                if selection == "home" and odds.home_moneyline is not None:
                    if best_odds is None or odds.home_moneyline > best_odds:
                        best_odds = odds.home_moneyline
                elif selection == "away" and odds.away_moneyline is not None:
                    if best_odds is None or odds.away_moneyline > best_odds:
                        best_odds = odds.away_moneyline
            elif bet_type == "spread":
                if selection == "home" and odds.home_spread_odds is not None:
                    if best_odds is None or odds.home_spread_odds > best_odds:
                        best_odds = odds.home_spread_odds
                elif selection == "away" and odds.away_spread_odds is not None:
                    if best_odds is None or odds.away_spread_odds > best_odds:
                        best_odds = odds.away_spread_odds
            elif bet_type == "over_under":
                if selection == "over" and odds.over_odds is not None:
                    if best_odds is None or odds.over_odds > best_odds:
                        best_odds = odds.over_odds
                elif selection == "under" and odds.under_odds is not None:
                    if best_odds is None or odds.under_odds > best_odds:
                        best_odds = odds.under_odds
            elif bet_type == "player_prop" and player_id is not None and prop_type is not None:
                # Get player props for this odds
                from backend.app.core.models import PlayerProp
                
                player_prop = db.query(PlayerProp).filter(
                    PlayerProp.odds_id == odds.id,
                    PlayerProp.player_id == player_id,
                    PlayerProp.prop_type == prop_type,
                ).first()
                
                if player_prop:
                    if selection == "over" and player_prop.over_odds is not None:
                        if best_odds is None or player_prop.over_odds > best_odds:
                            best_odds = player_prop.over_odds
                    elif selection == "under" and player_prop.under_odds is not None:
                        if best_odds is None or player_prop.under_odds > best_odds:
                            best_odds = player_prop.under_odds
        
        return best_odds

    def _determine_bet_status(self, db: Session, bet: Bet) -> str:
        """
        Determine the status of a bet based on the game result.
        
        Args:
            db: Database session
            bet: Bet object
            
        Returns:
            Status string (won, lost, push, etc.)
        """
        # Get the game
        game = db.query(Game).filter(Game.id == bet.game_id).first()
        if not game or game.status != "finished":
            return "pending"
        
        # Check if the game has a result
        if game.home_score is None or game.away_score is None:
            return "pending"
        
        # Determine the result based on the bet type and selection
        if bet.bet_type == "moneyline":
            if bet.selection == "home":
                return "won" if game.home_score > game.away_score else "lost"
            elif bet.selection == "away":
                return "won" if game.away_score > game.home_score else "lost"
        elif bet.bet_type == "spread":
            # Get the spread value
            odds = db.query(Odds).filter(
                Odds.game_id == game.id,
                Odds.sportsbook == "DraftKings",  # Use DraftKings as default
            ).first()
            
            if not odds:
                return "pending"
            
            if bet.selection == "home":
                spread = odds.home_spread
                if spread is None:
                    return "pending"
                
                adjusted_score = game.home_score + spread
                if adjusted_score > game.away_score:
                    return "won"
                elif adjusted_score < game.away_score:
                    return "lost"
                else:
                    return "push"
            elif bet.selection == "away":
                spread = odds.away_spread
                if spread is None:
                    return "pending"
                
                adjusted_score = game.away_score + spread
                if adjusted_score > game.home_score:
                    return "won"
                elif adjusted_score < game.home_score:
                    return "lost"
                else:
                    return "push"
        elif bet.bet_type == "over_under":
            # Get the over/under value
            odds = db.query(Odds).filter(
                Odds.game_id == game.id,
                Odds.sportsbook == "DraftKings",  # Use DraftKings as default
            ).first()
            
            if not odds or odds.over_under is None:
                return "pending"
            
            total = game.home_score + game.away_score
            if bet.selection == "over":
                if total > odds.over_under:
                    return "won"
                elif total < odds.over_under:
                    return "lost"
                else:
                    return "push"
            elif bet.selection == "under":
                if total < odds.over_under:
                    return "won"
                elif total > odds.over_under:
                    return "lost"
                else:
                    return "push"
        elif bet.bet_type == "player_prop":
            # For player props, we need additional data from the bet
            # In a real implementation, this would check the player's stats for the game
            # For now, we'll simulate it with a random result
            
            # Get the player prop details
            from backend.app.core.models import PlayerProp
            
            # In a real implementation, we would get the player's stats for the game
            # and compare them to the prop line
            # For now, we'll just return a random result
            import random
            
            # 50% chance of winning
            if random.random() < 0.5:
                return "won"
            else:
                return "lost"
        
        return "pending"

    def _determine_parlay_status(self, bets: List[Bet]) -> str:
        """
        Determine the status of a parlay based on the status of its bets.
        
        Args:
            bets: List of Bet objects
            
        Returns:
            Status string (won, lost, partially_won, etc.)
        """
        if not bets:
            return "pending"
        
        # Check if any bets are still pending
        if any(bet.status == "pending" for bet in bets):
            return "pending"
        
        # Check if any bets are pushes
        has_push = any(bet.status == "push" for bet in bets)
        
        # Check if all remaining bets are won
        all_won = all(bet.status == "won" or bet.status == "push" for bet in bets)
        
        if all_won:
            return "partially_won" if has_push else "won"
        else:
            return "lost"
