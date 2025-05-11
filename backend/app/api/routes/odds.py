"""API routes for betting odds."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.models import Game, Odds, PlayerProp, Player
from backend.app.services.sportsbook_service import SportsbookService

router = APIRouter()


@router.get("/odds", response_model=List[dict])
async def get_odds(
    db: Session = Depends(get_db),
    game_id: Optional[int] = Query(None, description="Filter by game ID"),
    sportsbook: Optional[str] = Query(None, description="Filter by sportsbook (e.g., DraftKings, FanDuel)"),
):
    """
    Get betting odds with optional filtering.
    
    - If game_id is provided, returns odds for that specific game
    - If sportsbook is provided, returns odds from that specific sportsbook
    """
    query = db.query(Odds).join(Game)
    
    # Apply game filter
    if game_id:
        query = query.filter(Odds.game_id == game_id)
    
    # Apply sportsbook filter
    if sportsbook:
        query = query.filter(Odds.sportsbook == sportsbook)
    
    odds_list = query.all()
    
    # Convert to dictionary with game information
    result = []
    for odds in odds_list:
        game = odds.game
        result.append({
            "id": odds.id,
            "game": {
                "id": game.id,
                "external_id": game.external_id,
                "home_team": {
                    "id": game.home_team.id,
                    "name": game.home_team.name,
                    "abbreviation": game.home_team.abbreviation,
                },
                "away_team": {
                    "id": game.away_team.id,
                    "name": game.away_team.name,
                    "abbreviation": game.away_team.abbreviation,
                },
                "game_time": game.game_time.isoformat(),
                "status": game.status,
            },
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
            "updated_at": odds.updated_at.isoformat(),
        })
    
    return result


@router.get("/odds/compare", response_model=List[dict])
async def compare_odds(
    db: Session = Depends(get_db),
    game_id: int = Query(..., description="Game ID to compare odds for"),
):
    """
    Compare odds from different sportsbooks for a specific game.
    
    Returns a list of odds from different sportsbooks for the specified game,
    allowing for easy comparison.
    """
    odds_list = db.query(Odds).filter(Odds.game_id == game_id).all()
    
    if not odds_list:
        raise HTTPException(status_code=404, detail="No odds found for the specified game")
    
    # Get the game information
    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    # Convert to dictionary with game information
    result = []
    for odds in odds_list:
        result.append({
            "id": odds.id,
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
            "updated_at": odds.updated_at.isoformat(),
        })
    
    return result


@router.get("/odds/best", response_model=dict)
async def get_best_odds(
    db: Session = Depends(get_db),
    game_id: int = Query(..., description="Game ID to get best odds for"),
):
    """
    Get the best available odds for a specific game across all sportsbooks.
    
    Returns the best available odds for each bet type (moneyline, spread, over/under)
    for the specified game, along with the sportsbook offering those odds.
    """
    odds_list = db.query(Odds).filter(Odds.game_id == game_id).all()
    
    if not odds_list:
        raise HTTPException(status_code=404, detail="No odds found for the specified game")
    
    # Get the game information
    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    # Find the best odds for each bet type
    best_home_moneyline = {"odds": None, "sportsbook": None}
    best_away_moneyline = {"odds": None, "sportsbook": None}
    best_home_spread = {"spread": None, "odds": None, "sportsbook": None}
    best_away_spread = {"spread": None, "odds": None, "sportsbook": None}
    best_over = {"total": None, "odds": None, "sportsbook": None}
    best_under = {"total": None, "odds": None, "sportsbook": None}
    
    for odds in odds_list:
        # Home moneyline
        if odds.home_moneyline is not None:
            if best_home_moneyline["odds"] is None or odds.home_moneyline > best_home_moneyline["odds"]:
                best_home_moneyline["odds"] = odds.home_moneyline
                best_home_moneyline["sportsbook"] = odds.sportsbook
        
        # Away moneyline
        if odds.away_moneyline is not None:
            if best_away_moneyline["odds"] is None or odds.away_moneyline > best_away_moneyline["odds"]:
                best_away_moneyline["odds"] = odds.away_moneyline
                best_away_moneyline["sportsbook"] = odds.sportsbook
        
        # Home spread
        if odds.home_spread is not None and odds.home_spread_odds is not None:
            if (best_home_spread["spread"] is None or 
                (odds.home_spread == best_home_spread["spread"] and odds.home_spread_odds > best_home_spread["odds"]) or
                (odds.home_spread > best_home_spread["spread"])):
                best_home_spread["spread"] = odds.home_spread
                best_home_spread["odds"] = odds.home_spread_odds
                best_home_spread["sportsbook"] = odds.sportsbook
        
        # Away spread
        if odds.away_spread is not None and odds.away_spread_odds is not None:
            if (best_away_spread["spread"] is None or 
                (odds.away_spread == best_away_spread["spread"] and odds.away_spread_odds > best_away_spread["odds"]) or
                (odds.away_spread > best_away_spread["spread"])):
                best_away_spread["spread"] = odds.away_spread
                best_away_spread["odds"] = odds.away_spread_odds
                best_away_spread["sportsbook"] = odds.sportsbook
        
        # Over
        if odds.over_under is not None and odds.over_odds is not None:
            if (best_over["total"] is None or 
                (odds.over_under == best_over["total"] and odds.over_odds > best_over["odds"]) or
                (odds.over_under < best_over["total"])):
                best_over["total"] = odds.over_under
                best_over["odds"] = odds.over_odds
                best_over["sportsbook"] = odds.sportsbook
        
        # Under
        if odds.over_under is not None and odds.under_odds is not None:
            if (best_under["total"] is None or 
                (odds.over_under == best_under["total"] and odds.under_odds > best_under["odds"]) or
                (odds.over_under > best_under["total"])):
                best_under["total"] = odds.over_under
                best_under["odds"] = odds.under_odds
                best_under["sportsbook"] = odds.sportsbook
    
    return {
        "game": {
            "id": game.id,
            "external_id": game.external_id,
            "home_team": {
                "id": game.home_team.id,
                "name": game.home_team.name,
                "abbreviation": game.home_team.abbreviation,
            },
            "away_team": {
                "id": game.away_team.id,
                "name": game.away_team.name,
                "abbreviation": game.away_team.abbreviation,
            },
            "game_time": game.game_time.isoformat(),
            "status": game.status,
        },
        "best_odds": {
            "home_moneyline": best_home_moneyline,
            "away_moneyline": best_away_moneyline,
            "home_spread": best_home_spread,
            "away_spread": best_away_spread,
            "over": best_over,
            "under": best_under,
        },
    }


@router.get("/odds/refresh", response_model=dict)
async def refresh_odds(
    db: Session = Depends(get_db),
    game_id: Optional[int] = Query(None, description="Refresh odds for a specific game"),
):
    """
    Refresh betting odds data from external APIs.
    
    This endpoint fetches the latest betting odds data from the external APIs
    (DraftKings, FanDuel) and updates the database.
    
    - If game_id is provided, refreshes odds for that specific game
    - Otherwise, refreshes odds for all upcoming games
    """
    sportsbook_service = SportsbookService()
    
    # Fetch odds from external APIs
    try:
        if game_id:
            odds_updated = await sportsbook_service.refresh_odds_for_game(db, game_id)
            return {"message": f"Successfully refreshed odds for game {game_id}. {odds_updated} odds updated."}
        else:
            odds_updated = await sportsbook_service.refresh_odds(db)
            return {"message": f"Successfully refreshed odds data. {odds_updated} odds updated."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to refresh odds: {str(e)}")


@router.get("/player-props", response_model=List[dict])
async def get_player_props(
    db: Session = Depends(get_db),
    player_id: Optional[int] = Query(None, description="Filter by player ID"),
    game_id: Optional[int] = Query(None, description="Filter by game ID"),
    prop_type: Optional[str] = Query(None, description="Filter by prop type (points, goals, assists, shots_on_goal)"),
    sportsbook: Optional[str] = Query(None, description="Filter by sportsbook"),
):
    """
    Get player props with optional filtering.
    
    - If player_id is provided, returns props for that specific player
    - If game_id is provided, returns props for players in that game
    - If prop_type is provided, returns props of that specific type
    - If sportsbook is provided, returns props from that specific sportsbook
    """
    query = db.query(PlayerProp).join(Odds).join(Player)
    
    # Apply player filter
    if player_id:
        query = query.filter(PlayerProp.player_id == player_id)
    
    # Apply game filter
    if game_id:
        query = query.filter(Odds.game_id == game_id)
    
    # Apply prop type filter
    if prop_type:
        query = query.filter(PlayerProp.prop_type == prop_type)
    
    # Apply sportsbook filter
    if sportsbook:
        query = query.filter(Odds.sportsbook == sportsbook)
    
    props = query.all()
    
    # Convert to dictionary with player and game information
    result = []
    for prop in props:
        player = prop.player
        odds = prop.odds
        game = odds.game
        
        result.append({
            "id": prop.id,
            "player": {
                "id": player.id,
                "name": player.name,
                "position": player.position,
                "team": {
                    "id": player.team.id,
                    "name": player.team.name,
                    "abbreviation": player.team.abbreviation,
                },
            },
            "game": {
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
            },
            "sportsbook": odds.sportsbook,
            "prop_type": prop.prop_type,
            "line": prop.line,
            "over_odds": prop.over_odds,
            "under_odds": prop.under_odds,
            "updated_at": prop.updated_at.isoformat(),
        })
    
    return result


@router.get("/player-props/{prop_id}", response_model=dict)
async def get_player_prop(
    prop_id: int,
    db: Session = Depends(get_db),
):
    """Get a specific player prop by ID."""
    prop = db.query(PlayerProp).filter(PlayerProp.id == prop_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Player prop not found")
    
    player = prop.player
    odds = prop.odds
    game = odds.game
    
    return {
        "id": prop.id,
        "player": {
            "id": player.id,
            "name": player.name,
            "position": player.position,
            "team": {
                "id": player.team.id,
                "name": player.team.name,
                "abbreviation": player.team.abbreviation,
            },
        },
        "game": {
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
        },
        "sportsbook": odds.sportsbook,
        "prop_type": prop.prop_type,
        "line": prop.line,
        "over_odds": prop.over_odds,
        "under_odds": prop.under_odds,
        "created_at": prop.created_at.isoformat(),
        "updated_at": prop.updated_at.isoformat(),
    }


@router.get("/player-props/refresh", response_model=dict)
async def refresh_player_props(
    db: Session = Depends(get_db),
    player_id: Optional[int] = Query(None, description="Refresh props for a specific player"),
    game_id: Optional[int] = Query(None, description="Refresh props for a specific game"),
):
    """
    Refresh player props data from external APIs.
    
    This endpoint fetches the latest player props data from the external APIs
    (DraftKings, FanDuel) and updates the database.
    
    - If player_id is provided, refreshes props for that specific player
    - If game_id is provided, refreshes props for players in that game
    - Otherwise, refreshes props for all upcoming games
    """
    sportsbook_service = SportsbookService()
    
    # Fetch props from external APIs
    try:
        if player_id:
            props_updated = await sportsbook_service.refresh_player_props_for_player(db, player_id)
            return {"message": f"Successfully refreshed props for player {player_id}. {props_updated} props updated."}
        elif game_id:
            props_updated = await sportsbook_service.refresh_player_props_for_game(db, game_id)
            return {"message": f"Successfully refreshed props for game {game_id}. {props_updated} props updated."}
        else:
            props_updated = await sportsbook_service.refresh_player_props(db)
            return {"message": f"Successfully refreshed player props data. {props_updated} props updated."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to refresh player props: {str(e)}")
