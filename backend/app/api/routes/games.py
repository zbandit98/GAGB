"""API routes for NHL games."""

from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.models import Game, Team
from backend.app.services.sportsbook_service import SportsbookService

router = APIRouter()


@router.get("/games", response_model=List[dict])
async def get_games(
    db: Session = Depends(get_db),
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format"),
    team_id: Optional[int] = Query(None, description="Filter by team ID"),
    status: Optional[str] = Query(None, description="Filter by game status"),
    days: Optional[int] = Query(7, description="Number of days to fetch (if no date provided)"),
):
    """
    Get NHL games with optional filtering.
    
    - If date is provided, returns games for that specific date
    - If team_id is provided, returns games for that specific team
    - If status is provided, returns games with that specific status
    - If no date is provided, returns games for the next 'days' days
    """
    query = db.query(Game)
    
    # Apply date filter
    if date:
        try:
            game_date = datetime.strptime(date, "%Y-%m-%d")
            next_day = game_date + timedelta(days=1)
            query = query.filter(Game.game_time >= game_date, Game.game_time < next_day)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    else:
        # Default to upcoming games
        now = datetime.utcnow()
        future = now + timedelta(days=days)
        query = query.filter(Game.game_time >= now, Game.game_time <= future)
    
    # Apply team filter
    if team_id:
        query = query.filter((Game.home_team_id == team_id) | (Game.away_team_id == team_id))
    
    # Apply status filter
    if status:
        query = query.filter(Game.status == status)
    
    # Order by game time
    query = query.order_by(Game.game_time)
    
    games = query.all()
    
    # Convert to dictionary with team information
    result = []
    for game in games:
        result.append({
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
            "home_score": game.home_score,
            "away_score": game.away_score,
        })
    
    return result


@router.get("/games/{game_id}", response_model=dict)
async def get_game(game_id: int, db: Session = Depends(get_db)):
    """Get a specific NHL game by ID."""
    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    return {
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
        "home_score": game.home_score,
        "away_score": game.away_score,
    }


@router.get("/games/refresh", response_model=dict)
async def refresh_games(
    db: Session = Depends(get_db),
    days: int = Query(7, description="Number of days to fetch"),
):
    """
    Refresh NHL games data from external API.
    
    This endpoint fetches the latest NHL games data from the external API
    and updates the database.
    """
    sportsbook_service = SportsbookService()
    
    # Fetch games from external API
    try:
        games_updated = await sportsbook_service.refresh_games(db, days)
        return {"message": f"Successfully refreshed games data. {games_updated} games updated."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to refresh games: {str(e)}")


@router.get("/teams", response_model=List[dict])
async def get_teams(db: Session = Depends(get_db)):
    """Get all NHL teams."""
    teams = db.query(Team).order_by(Team.name).all()
    
    result = []
    for team in teams:
        result.append({
            "id": team.id,
            "name": team.name,
            "abbreviation": team.abbreviation,
            "division": team.division,
            "conference": team.conference,
            "logo_url": team.logo_url,
        })
    
    return result


@router.get("/teams/{team_id}", response_model=dict)
async def get_team(team_id: int, db: Session = Depends(get_db)):
    """Get a specific NHL team by ID."""
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    return {
        "id": team.id,
        "name": team.name,
        "abbreviation": team.abbreviation,
        "division": team.division,
        "conference": team.conference,
        "logo_url": team.logo_url,
    }
