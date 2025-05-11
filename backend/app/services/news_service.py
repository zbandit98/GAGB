"""Service for fetching and processing sports news articles."""

import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from backend.app.config import get_settings
from backend.app.core.models import NewsArticle, Player, Team

logger = logging.getLogger(__name__)


class NewsService:
    """Service for fetching and processing sports news articles."""

    def __init__(self):
        """Initialize the news service."""
        self.settings = get_settings()
        self.espn_api_key = self.settings.espn_api_key
        self.the_athletic_api_key = self.settings.the_athletic_api_key
        self.http_client = httpx.AsyncClient(timeout=30.0)

    async def refresh_news(self, db: Session, days: int = 1) -> int:
        """
        Refresh sports news data from all configured sources.
        
        Args:
            db: Database session
            days: Number of days to fetch
            
        Returns:
            Number of articles updated
        """
        logger.info(f"Refreshing sports news data for the past {days} days")
        
        # Refresh news from each source
        espn_count = await self.refresh_news_from_source(db, "ESPN", days)
        athletic_count = await self.refresh_news_from_source(db, "The Athletic", days)
        
        total_count = espn_count + athletic_count
        logger.info(f"Updated {total_count} news articles")
        return total_count

    async def refresh_news_from_source(self, db: Session, source: str, days: int = 1) -> int:
        """
        Refresh sports news data from a specific source.
        
        Args:
            db: Database session
            source: News source (ESPN, The Athletic)
            days: Number of days to fetch
            
        Returns:
            Number of articles updated
        """
        logger.info(f"Refreshing sports news data from {source} for the past {days} days")
        
        if source == "ESPN":
            articles = await self._fetch_espn_articles(days)
        elif source == "The Athletic":
            articles = await self._fetch_athletic_articles(days)
        else:
            logger.warning(f"Unknown news source: {source}")
            return 0
        
        # Process and store articles
        articles_updated = 0
        for article_data in articles:
            # Check if article already exists
            existing_article = db.query(NewsArticle).filter(
                NewsArticle.url == article_data["url"]
            ).first()
            
            if existing_article:
                # Update existing article
                existing_article.title = article_data["title"]
                existing_article.content = article_data["content"]
                existing_article.summary = article_data.get("summary")
                existing_article.published_date = article_data["published_date"]
                db.add(existing_article)
                articles_updated += 1
            else:
                # Create new article
                new_article = NewsArticle(
                    external_id=article_data.get("external_id"),
                    source=source,
                    title=article_data["title"],
                    url=article_data["url"],
                    content=article_data["content"],
                    summary=article_data.get("summary"),
                    published_date=article_data["published_date"],
                )
                db.add(new_article)
                db.flush()  # Flush to get the article ID
                
                # Process article content to identify teams and players
                teams, players = await self._extract_entities(db, article_data["content"])
                
                # Associate teams with article
                for team in teams:
                    new_article.teams.append(team)
                
                # Associate players with article
                for player in players:
                    new_article.players.append(player)
                
                articles_updated += 1
        
        db.commit()
        logger.info(f"Updated {articles_updated} articles from {source}")
        return articles_updated

    async def _fetch_espn_articles(self, days: int) -> List[Dict]:
        """
        Fetch NHL articles from ESPN (simulated).
        
        Args:
            days: Number of days to fetch
            
        Returns:
            List of article data
        """
        # In a real implementation, this would fetch data from the ESPN API
        # For now, we'll simulate it with mock data
        
        # Simulate API call
        if not self.espn_api_key:
            logger.warning("ESPN API key not configured")
            return []
        
        # Generate mock articles
        articles = []
        now = datetime.utcnow()
        
        # Sample article titles and content
        sample_articles = [
            {
                "title": "NHL Power Rankings: Top teams heading into the playoffs",
                "content": """
                The NHL regular season is winding down, and the playoff picture is becoming clearer.
                
                The Boston Bruins have been dominant all season, setting records and establishing themselves as the team to beat.
                
                Meanwhile, the Toronto Maple Leafs and Tampa Bay Lightning continue their rivalry in the Atlantic Division.
                
                In the Western Conference, the Colorado Avalanche are looking to defend their Stanley Cup title, but the Vegas Golden Knights and Edmonton Oilers pose serious threats.
                
                Connor McDavid continues his incredible season, leading the league in points and making a strong case for the Hart Trophy.
                """
            },
            {
                "title": "Injury updates: Key players returning for playoff push",
                "content": """
                Several NHL teams are getting healthier at the right time as the playoffs approach.
                
                The Florida Panthers expect Aleksander Barkov to return from his lower-body injury this week, providing a huge boost to their top line.
                
                For the New York Rangers, Igor Shesterkin has recovered from his minor ailment and will be back between the pipes for the final stretch of regular season games.
                
                The Dallas Stars received good news as Roope Hintz is cleared to play after missing several games.
                
                However, the Tampa Bay Lightning will be without Victor Hedman for at least another week as he continues to recover from an upper-body injury.
                """
            },
            {
                "title": "NHL trade deadline winners and losers",
                "content": """
                With the NHL trade deadline now behind us, it's time to assess which teams improved their chances and which ones missed opportunities.
                
                The Boston Bruins strengthened their already formidable roster by adding depth pieces without disrupting their chemistry.
                
                The Edmonton Oilers made a splash by acquiring a top-four defenseman to support Connor McDavid and Leon Draisaitl in their quest for the Stanley Cup.
                
                The Toronto Maple Leafs addressed their goaltending concerns and added grit to their lineup, potentially solving issues that have plagued them in previous playoff runs.
                
                On the other hand, the Pittsburgh Penguins stood pat despite their struggles, raising questions about their direction with an aging core of Sidney Crosby, Evgeni Malkin, and Kris Letang.
                """
            },
        ]
        
        # Generate articles for each day
        for day in range(days):
            article_date = now - timedelta(days=day)
            
            # Add 1-2 articles per day
            for i in range(1, 3):
                if day * 2 + i <= len(sample_articles):
                    article_idx = (day * 2 + i - 1) % len(sample_articles)
                    article = sample_articles[article_idx]
                    
                    article_time = article_date.replace(
                        hour=10 + i * 3,
                        minute=0,
                        second=0,
                        microsecond=0,
                    )
                    
                    articles.append({
                        "external_id": f"ESPN-NHL-{article_date.strftime('%Y%m%d')}-{i}",
                        "title": article["title"],
                        "url": f"https://www.espn.com/nhl/story/_/id/{article_date.strftime('%Y%m%d')}{i:02d}/{article['title'].lower().replace(' ', '-')}",
                        "content": article["content"],
                        "summary": article["content"].split("\n\n")[0],
                        "published_date": article_time,
                    })
        
        return articles

    async def _fetch_athletic_articles(self, days: int) -> List[Dict]:
        """
        Fetch NHL articles from The Athletic (simulated).
        
        Args:
            days: Number of days to fetch
            
        Returns:
            List of article data
        """
        # In a real implementation, this would fetch data from The Athletic API or scrape their website
        # For now, we'll simulate it with mock data
        
        # Simulate API call
        if not self.the_athletic_api_key:
            logger.warning("The Athletic API key not configured")
            return []
        
        # Generate mock articles
        articles = []
        now = datetime.utcnow()
        
        # Sample article titles and content
        sample_articles = [
            {
                "title": "NHL playoff race: Breaking down the final stretch",
                "content": """
                As the NHL regular season enters its final weeks, the playoff races in both conferences are heating up.
                
                In the Eastern Conference, the Boston Bruins have secured their spot, but several teams are battling for the remaining positions. The Florida Panthers and Tampa Bay Lightning are neck-and-neck in the Atlantic Division.
                
                The Metropolitan Division sees the Carolina Hurricanes and New York Rangers fighting for the top spot, with the Pittsburgh Penguins trying to extend their playoff streak.
                
                Out West, the Colorado Avalanche and Vegas Golden Knights look strong, while the Edmonton Oilers are riding the incredible performances of Connor McDavid and Leon Draisaitl.
                
                The Dallas Stars have been a surprise contender, with Jake Oettinger establishing himself as one of the league's top goaltenders.
                """
            },
            {
                "title": "Inside the Bruins' historic season: What makes them so dominant",
                "content": """
                The Boston Bruins are having a season for the ages, challenging NHL records and dominating opponents with remarkable consistency.
                
                Their success starts with the goaltending tandem of Linus Ullmark and Jeremy Swayman, arguably the best in the league. Ullmark, in particular, has put together a Vezina Trophy-worthy campaign.
                
                On defense, Charlie McAvoy has elevated his game to elite status, while Hampus Lindholm has been a perfect fit since arriving from Anaheim last season.
                
                Offensively, David Pastrnak continues to be one of the NHL's most lethal scorers, while the ageless Patrice Bergeron still excels at both ends of the ice.
                
                Coach Jim Montgomery deserves immense credit for implementing a system that maximizes his players' strengths while maintaining defensive responsibility.
                """
            },
            {
                "title": "NHL Draft: Top prospects to watch",
                "content": """
                With the NHL regular season winding down, teams at the bottom of the standings are turning their attention to the upcoming draft.
                
                This year's draft class is headlined by Connor Bedard, a generational talent who has drawn comparisons to Sidney Crosby and Connor McDavid. The team that wins the draft lottery will be getting a franchise-altering player.
                
                Beyond Bedard, Adam Fantilli has established himself as a clear number two prospect, showcasing his skills at the University of Michigan.
                
                Defenseman Leo Carlsson could be the first blueliner off the board, with his combination of size, skating, and offensive instincts.
                
                Russian forward Matvei Michkov is perhaps the most intriguing prospect, with elite talent but questions about when he'll come to North America.
                """
            },
        ]
        
        # Generate articles for each day
        for day in range(days):
            article_date = now - timedelta(days=day)
            
            # Add 1-2 articles per day
            for i in range(1, 3):
                if day * 2 + i <= len(sample_articles):
                    article_idx = (day * 2 + i - 1) % len(sample_articles)
                    article = sample_articles[article_idx]
                    
                    article_time = article_date.replace(
                        hour=9 + i * 3,
                        minute=30,
                        second=0,
                        microsecond=0,
                    )
                    
                    articles.append({
                        "external_id": f"ATHLETIC-NHL-{article_date.strftime('%Y%m%d')}-{i}",
                        "title": article["title"],
                        "url": f"https://theathletic.com/nhl/{article_date.strftime('%Y/%m/%d')}/{article['title'].lower().replace(' ', '-')}/",
                        "content": article["content"],
                        "summary": article["content"].split("\n\n")[0],
                        "published_date": article_time,
                    })
        
        return articles

    async def _extract_entities(self, db: Session, content: str) -> Tuple[List[Team], List[Player]]:
        """
        Extract team and player entities from article content.
        
        Args:
            db: Database session
            content: Article content
            
        Returns:
            Tuple of (teams, players) mentioned in the content
        """
        # Get all teams and players from the database
        all_teams = db.query(Team).all()
        all_players = db.query(Player).all()
        
        # Create sets to store unique entities
        mentioned_teams = set()
        mentioned_players = set()
        
        # Extract team mentions
        for team in all_teams:
            # Check for team name
            if team.name in content:
                mentioned_teams.add(team)
            # Check for team abbreviation
            elif team.abbreviation in content:
                mentioned_teams.add(team)
        
        # Extract player mentions
        for player in all_players:
            if player.name in content:
                mentioned_players.add(player)
                # Also add the player's team
                if player.team:
                    mentioned_teams.add(player.team)
        
        return list(mentioned_teams), list(mentioned_players)

    async def close(self):
        """Close the HTTP client."""
        await self.http_client.aclose()
