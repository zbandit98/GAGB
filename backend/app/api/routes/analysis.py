"""API routes for AI analysis."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.models import AIAnalysis, Game, Team
from backend.app.services.ai_service import AIService

router = APIRouter()


@router.get("/analysis/game/{game_id}", response_model=dict)
async def analyze_game(
    game_id: int,
    db: Session = Depends(get_db),
    refresh: bool = Query(False, description="Force refresh of analysis"),
):
    """
    Get AI analysis for a specific game.
    
    This endpoint provides AI-generated analysis for the specified game,
    including predictions, key factors, and insights based on news and historical data.
    
    - If refresh is True, forces a new analysis to be generated
    - Otherwise, returns cached analysis if available (within the last 24 hours)
    """
    # Check if game exists
    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    ai_service = AIService()
    
    try:
        # Get or generate analysis
        analysis = await ai_service.analyze_game(db, game_id, refresh)
        
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
            "analysis": {
                "id": analysis.id,
                "content": analysis.content,
                "confidence_score": analysis.confidence_score,
                "created_at": analysis.created_at.isoformat(),
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze game: {str(e)}")


@router.get("/analysis/team/{team_id}", response_model=dict)
async def analyze_team(
    team_id: int,
    db: Session = Depends(get_db),
    refresh: bool = Query(False, description="Force refresh of analysis"),
):
    """
    Get AI analysis for a specific team.
    
    This endpoint provides AI-generated analysis for the specified team,
    including recent performance, injury impacts, and insights based on news and historical data.
    
    - If refresh is True, forces a new analysis to be generated
    - Otherwise, returns cached analysis if available (within the last 24 hours)
    """
    # Check if team exists
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    ai_service = AIService()
    
    try:
        # Get or generate analysis
        analysis = await ai_service.analyze_team(db, team_id, refresh)
        
        return {
            "team": {
                "id": team.id,
                "name": team.name,
                "abbreviation": team.abbreviation,
                "division": team.division,
                "conference": team.conference,
            },
            "analysis": {
                "id": analysis.id,
                "content": analysis.content,
                "confidence_score": analysis.confidence_score,
                "created_at": analysis.created_at.isoformat(),
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze team: {str(e)}")


@router.post("/analysis/parlay/optimize", response_model=dict)
async def optimize_parlay(
    db: Session = Depends(get_db),
    stake: float = Query(..., description="Amount to stake on the parlay"),
    game_ids: List[int] = Query(None, description="List of game IDs to consider for the parlay"),
    min_odds: Optional[float] = Query(None, description="Minimum total odds for the parlay"),
    max_legs: Optional[int] = Query(None, description="Maximum number of legs in the parlay"),
    min_confidence: Optional[float] = Query(None, description="Minimum confidence score for each leg"),
):
    """
    Generate an optimized parlay based on AI analysis.
    
    This endpoint uses AI to analyze available games and betting odds to generate
    an optimized parlay that maximizes potential return while considering confidence scores.
    
    - stake is the amount to stake on the parlay
    - game_ids can be provided to limit the games considered for the parlay
    - min_odds can be provided to set a minimum total odds for the parlay
    - max_legs can be provided to limit the number of legs in the parlay
    - min_confidence can be provided to set a minimum confidence score for each leg
    """
    ai_service = AIService()
    
    try:
        # Generate optimized parlay
        parlay = await ai_service.optimize_parlay(
            db,
            stake=stake,
            game_ids=game_ids,
            min_odds=min_odds,
            max_legs=max_legs,
            min_confidence=min_confidence,
        )
        
        # Convert to response format
        legs = []
        for bet in parlay.bets:
            game = bet.game
            legs.append({
                "game": {
                    "id": game.id,
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
                },
                "bet_type": bet.bet_type,
                "selection": bet.selection,
                "odds": bet.odds,
                "justification": bet.justification,
            })
        
        return {
            "parlay": {
                "id": parlay.id,
                "name": parlay.name,
                "stake": parlay.stake,
                "total_odds": parlay.total_odds,
                "potential_payout": parlay.potential_payout,
                "confidence_score": parlay.confidence_score,
                "legs": legs,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to optimize parlay: {str(e)}")


@router.post("/analysis/parlay/evaluate", response_model=dict)
async def evaluate_parlay(
    db: Session = Depends(get_db),
    parlay_id: int = Query(..., description="ID of the parlay to evaluate"),
):
    """
    Evaluate an existing parlay using AI analysis.
    
    This endpoint uses AI to analyze an existing parlay and provide insights,
    confidence scores, and recommendations for improvement.
    """
    ai_service = AIService()
    
    try:
        # Evaluate parlay
        analysis = await ai_service.evaluate_parlay(db, parlay_id)
        
        return {
            "parlay_id": parlay_id,
            "analysis": {
                "id": analysis.id,
                "content": analysis.content,
                "confidence_score": analysis.confidence_score,
                "created_at": analysis.created_at.isoformat(),
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to evaluate parlay: {str(e)}")
