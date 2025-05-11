"""API routes for parlays."""

from typing import List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.models import Bet, Game, Parlay
from backend.app.services.parlay_service import ParlayService

router = APIRouter()


@router.get("/parlays", response_model=List[dict])
async def get_parlays(
    db: Session = Depends(get_db),
    status: Optional[str] = Query(None, description="Filter by status (e.g., pending, won, lost)"),
    limit: Optional[int] = Query(20, description="Maximum number of parlays to return"),
):
    """
    Get parlays with optional filtering.
    
    - If status is provided, returns parlays with that specific status
    - limit parameter controls the maximum number of parlays to return
    """
    query = db.query(Parlay)
    
    # Apply status filter
    if status:
        query = query.filter(Parlay.status == status)
    
    # Order by created date (newest first) and limit results
    query = query.order_by(Parlay.created_at.desc()).limit(limit)
    
    parlays = query.all()
    
    # Convert to dictionary with bet information
    result = []
    for parlay in parlays:
        legs = []
        for bet in parlay.bets:
            game = bet.game
            legs.append({
                "id": bet.id,
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
                    "home_score": game.home_score,
                    "away_score": game.away_score,
                },
                "bet_type": bet.bet_type,
                "selection": bet.selection,
                "odds": bet.odds,
                "status": bet.status,
            })
        
        result.append({
            "id": parlay.id,
            "name": parlay.name,
            "stake": parlay.stake,
            "total_odds": parlay.total_odds,
            "potential_payout": parlay.potential_payout,
            "confidence_score": parlay.confidence_score,
            "status": parlay.status,
            "created_at": parlay.created_at.isoformat(),
            "legs": legs,
        })
    
    return result


@router.get("/parlays/{parlay_id}", response_model=dict)
async def get_parlay(parlay_id: int, db: Session = Depends(get_db)):
    """Get a specific parlay by ID."""
    parlay = db.query(Parlay).filter(Parlay.id == parlay_id).first()
    if not parlay:
        raise HTTPException(status_code=404, detail="Parlay not found")
    
    # Convert to dictionary with bet information
    legs = []
    for bet in parlay.bets:
        game = bet.game
        legs.append({
            "id": bet.id,
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
                "home_score": game.home_score,
                "away_score": game.away_score,
            },
            "bet_type": bet.bet_type,
            "selection": bet.selection,
            "odds": bet.odds,
            "justification": bet.justification,
            "status": bet.status,
        })
    
    return {
        "id": parlay.id,
        "name": parlay.name,
        "stake": parlay.stake,
        "total_odds": parlay.total_odds,
        "potential_payout": parlay.potential_payout,
        "confidence_score": parlay.confidence_score,
        "status": parlay.status,
        "created_at": parlay.created_at.isoformat(),
        "updated_at": parlay.updated_at.isoformat(),
        "legs": legs,
    }


@router.post("/parlays", response_model=dict)
async def create_parlay(
    db: Session = Depends(get_db),
    name: Optional[str] = Body(None, description="Name for the parlay"),
    stake: float = Body(..., description="Amount to stake on the parlay"),
    bets: List[dict] = Body(..., description="List of bets to include in the parlay"),
):
    """
    Create a new parlay.
    
    This endpoint creates a new parlay with the specified bets.
    
    - name is an optional name for the parlay
    - stake is the amount to stake on the parlay
    - bets is a list of bets to include in the parlay, each with:
      - game_id: ID of the game
      - bet_type: Type of bet (moneyline, spread, over_under, etc.)
      - selection: Selection for the bet (home, away, over, under, etc.)
    """
    parlay_service = ParlayService()
    
    try:
        # Create parlay
        parlay = await parlay_service.create_parlay(db, name, stake, bets)
        
        # Convert to response format
        legs = []
        for bet in parlay.bets:
            game = bet.game
            legs.append({
                "id": bet.id,
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
                },
                "bet_type": bet.bet_type,
                "selection": bet.selection,
                "odds": bet.odds,
                "justification": bet.justification,
                "status": bet.status,
            })
        
        return {
            "id": parlay.id,
            "name": parlay.name,
            "stake": parlay.stake,
            "total_odds": parlay.total_odds,
            "potential_payout": parlay.potential_payout,
            "confidence_score": parlay.confidence_score,
            "status": parlay.status,
            "created_at": parlay.created_at.isoformat(),
            "legs": legs,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create parlay: {str(e)}")


@router.put("/parlays/{parlay_id}", response_model=dict)
async def update_parlay(
    parlay_id: int,
    db: Session = Depends(get_db),
    name: Optional[str] = Body(None, description="Name for the parlay"),
    stake: Optional[float] = Body(None, description="Amount to stake on the parlay"),
    status: Optional[str] = Body(None, description="Status of the parlay"),
):
    """
    Update an existing parlay.
    
    This endpoint updates an existing parlay with the specified parameters.
    
    - name is an optional name for the parlay
    - stake is the amount to stake on the parlay
    - status is the status of the parlay (pending, won, lost, etc.)
    """
    parlay = db.query(Parlay).filter(Parlay.id == parlay_id).first()
    if not parlay:
        raise HTTPException(status_code=404, detail="Parlay not found")
    
    # Update parlay
    if name is not None:
        parlay.name = name
    if stake is not None:
        parlay.stake = stake
        # Recalculate potential payout
        parlay.potential_payout = parlay.stake * parlay.total_odds
    if status is not None:
        parlay.status = status
    
    db.commit()
    db.refresh(parlay)
    
    # Convert to response format
    legs = []
    for bet in parlay.bets:
        game = bet.game
        legs.append({
            "id": bet.id,
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
            "bet_type": bet.bet_type,
            "selection": bet.selection,
            "odds": bet.odds,
            "justification": bet.justification,
            "status": bet.status,
        })
    
    return {
        "id": parlay.id,
        "name": parlay.name,
        "stake": parlay.stake,
        "total_odds": parlay.total_odds,
        "potential_payout": parlay.potential_payout,
        "confidence_score": parlay.confidence_score,
        "status": parlay.status,
        "created_at": parlay.created_at.isoformat(),
        "updated_at": parlay.updated_at.isoformat(),
        "legs": legs,
    }


@router.delete("/parlays/{parlay_id}", response_model=dict)
async def delete_parlay(parlay_id: int, db: Session = Depends(get_db)):
    """Delete a specific parlay by ID."""
    parlay = db.query(Parlay).filter(Parlay.id == parlay_id).first()
    if not parlay:
        raise HTTPException(status_code=404, detail="Parlay not found")
    
    # Delete associated bets
    db.query(Bet).filter(Bet.parlay_id == parlay_id).delete()
    
    # Delete parlay
    db.delete(parlay)
    db.commit()
    
    return {"message": f"Parlay {parlay_id} deleted successfully"}


@router.get("/parlays/update-status", response_model=dict)
async def update_parlay_statuses(db: Session = Depends(get_db)):
    """
    Update the status of all pending parlays.
    
    This endpoint checks the status of all games in pending parlays and updates
    the status of the parlays and their bets accordingly.
    """
    parlay_service = ParlayService()
    
    try:
        # Update parlay statuses
        updated_count = await parlay_service.update_parlay_statuses(db)
        return {"message": f"Successfully updated {updated_count} parlays"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update parlay statuses: {str(e)}")
