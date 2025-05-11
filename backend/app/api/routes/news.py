"""API routes for sports news articles."""

from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.models import NewsArticle, Team, Player
from backend.app.services.news_service import NewsService

router = APIRouter()


@router.get("/news", response_model=List[dict])
async def get_news(
    db: Session = Depends(get_db),
    team_id: Optional[int] = Query(None, description="Filter by team ID"),
    player_id: Optional[int] = Query(None, description="Filter by player ID"),
    source: Optional[str] = Query(None, description="Filter by source (e.g., ESPN, The Athletic)"),
    days: Optional[int] = Query(7, description="Number of days to look back"),
    limit: Optional[int] = Query(20, description="Maximum number of articles to return"),
):
    """
    Get sports news articles with optional filtering.
    
    - If team_id is provided, returns articles mentioning that team
    - If player_id is provided, returns articles mentioning that player
    - If source is provided, returns articles from that source
    - days parameter controls how far back to look for articles
    - limit parameter controls the maximum number of articles to return
    """
    query = db.query(NewsArticle)
    
    # Apply team filter
    if team_id:
        team = db.query(Team).filter(Team.id == team_id).first()
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
        query = query.filter(NewsArticle.teams.any(id=team_id))
    
    # Apply player filter
    if player_id:
        player = db.query(Player).filter(Player.id == player_id).first()
        if not player:
            raise HTTPException(status_code=404, detail="Player not found")
        query = query.filter(NewsArticle.players.any(id=player_id))
    
    # Apply source filter
    if source:
        query = query.filter(NewsArticle.source == source)
    
    # Apply date filter
    if days:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        query = query.filter(NewsArticle.published_date >= cutoff_date)
    
    # Order by published date (newest first) and limit results
    query = query.order_by(NewsArticle.published_date.desc()).limit(limit)
    
    articles = query.all()
    
    # Convert to dictionary with team and player information
    result = []
    for article in articles:
        teams = [{"id": team.id, "name": team.name} for team in article.teams]
        players = [{"id": player.id, "name": player.name} for player in article.players]
        
        result.append({
            "id": article.id,
            "source": article.source,
            "title": article.title,
            "url": article.url,
            "summary": article.summary,
            "published_date": article.published_date.isoformat(),
            "teams": teams,
            "players": players,
        })
    
    return result


@router.get("/news/{article_id}", response_model=dict)
async def get_article(article_id: int, db: Session = Depends(get_db)):
    """Get a specific news article by ID."""
    article = db.query(NewsArticle).filter(NewsArticle.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    teams = [{"id": team.id, "name": team.name} for team in article.teams]
    players = [{"id": player.id, "name": player.name} for player in article.players]
    
    return {
        "id": article.id,
        "source": article.source,
        "title": article.title,
        "url": article.url,
        "content": article.content,
        "summary": article.summary,
        "published_date": article.published_date.isoformat(),
        "teams": teams,
        "players": players,
    }


@router.get("/news/team/{team_id}", response_model=List[dict])
async def get_team_news(
    team_id: int,
    db: Session = Depends(get_db),
    days: Optional[int] = Query(7, description="Number of days to look back"),
    limit: Optional[int] = Query(20, description="Maximum number of articles to return"),
):
    """Get news articles for a specific team."""
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    # Get articles mentioning the team
    query = db.query(NewsArticle).filter(NewsArticle.teams.any(id=team_id))
    
    # Apply date filter
    if days:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        query = query.filter(NewsArticle.published_date >= cutoff_date)
    
    # Order by published date (newest first) and limit results
    query = query.order_by(NewsArticle.published_date.desc()).limit(limit)
    
    articles = query.all()
    
    # Convert to dictionary
    result = []
    for article in articles:
        result.append({
            "id": article.id,
            "source": article.source,
            "title": article.title,
            "url": article.url,
            "summary": article.summary,
            "published_date": article.published_date.isoformat(),
        })
    
    return result


@router.get("/news/player/{player_id}", response_model=List[dict])
async def get_player_news(
    player_id: int,
    db: Session = Depends(get_db),
    days: Optional[int] = Query(7, description="Number of days to look back"),
    limit: Optional[int] = Query(20, description="Maximum number of articles to return"),
):
    """Get news articles for a specific player."""
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    # Get articles mentioning the player
    query = db.query(NewsArticle).filter(NewsArticle.players.any(id=player_id))
    
    # Apply date filter
    if days:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        query = query.filter(NewsArticle.published_date >= cutoff_date)
    
    # Order by published date (newest first) and limit results
    query = query.order_by(NewsArticle.published_date.desc()).limit(limit)
    
    articles = query.all()
    
    # Convert to dictionary
    result = []
    for article in articles:
        result.append({
            "id": article.id,
            "source": article.source,
            "title": article.title,
            "url": article.url,
            "summary": article.summary,
            "published_date": article.published_date.isoformat(),
        })
    
    return result


@router.get("/news/refresh", response_model=dict)
async def refresh_news(
    db: Session = Depends(get_db),
    source: Optional[str] = Query(None, description="Refresh news from a specific source"),
    days: Optional[int] = Query(1, description="Number of days to fetch"),
):
    """
    Refresh sports news data from external sources.
    
    This endpoint fetches the latest sports news data from the external sources
    (ESPN, The Athletic) and updates the database.
    
    - If source is provided, refreshes news from that specific source
    - days parameter controls how far back to look for articles
    """
    news_service = NewsService()
    
    # Fetch news from external sources
    try:
        if source:
            articles_updated = await news_service.refresh_news_from_source(db, source, days)
            return {"message": f"Successfully refreshed news from {source}. {articles_updated} articles updated."}
        else:
            articles_updated = await news_service.refresh_news(db, days)
            return {"message": f"Successfully refreshed news data. {articles_updated} articles updated."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to refresh news: {str(e)}")
