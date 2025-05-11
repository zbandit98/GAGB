"""Gradio frontend for the GAGB application."""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any

import gradio as gr
import httpx

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from frontend.components.game_selector import create_game_selector
from frontend.components.odds_display import create_odds_display
from frontend.components.parlay_builder import create_parlay_builder
from frontend.components.analysis_display import create_analysis_display
from frontend.utils.api_client import APIClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def create_app():
    """Create the Gradio app."""
    # Initialize API client
    api_client = APIClient(base_url="http://localhost:8000")
    
    # Create the app
    with gr.Blocks(title="GAGB - Sports Betting Assistant", theme=gr.themes.Soft()) as app:
        gr.Markdown(
            """
            # GAGB - Generative AI Gambling Bot
            
            A sports betting decision assistant that leverages news sources, sportsbook APIs, and generative AI to create optimized parlays for NHL betting.
            """
        )
        
        with gr.Tabs() as tabs:
            with gr.TabItem("Upcoming Games"):
                game_selector, selected_game = create_game_selector(api_client)
                
                with gr.Row():
                    with gr.Column(scale=2):
                        odds_display = create_odds_display(api_client, selected_game)
                    
                    with gr.Column(scale=3):
                        analysis_display = create_analysis_display(api_client, selected_game)
            
            with gr.TabItem("Parlay Builder"):
                parlay_builder = create_parlay_builder(api_client)
            
            with gr.TabItem("My Parlays"):
                with gr.Row():
                    with gr.Column():
                        parlay_status = gr.Dropdown(
                            choices=["All", "Pending", "Won", "Lost", "Partially Won"],
                            value="All",
                            label="Filter by Status",
                        )
                        refresh_parlays_btn = gr.Button("Refresh Parlays")
                
                parlays_table = gr.DataFrame(
                    headers=["ID", "Name", "Stake", "Odds", "Potential Payout", "Status", "Created"],
                    label="My Parlays",
                )
                
                parlay_details = gr.JSON(label="Parlay Details")
                
                def load_parlays(status):
                    """Load parlays from the API."""
                    try:
                        status_param = status.lower() if status != "All" else None
                        parlays = api_client.get_parlays(status=status_param)
                        
                        # Format for display
                        parlays_data = []
                        for parlay in parlays:
                            parlays_data.append([
                                parlay["id"],
                                parlay["name"],
                                f"${parlay['stake']:.2f}",
                                f"{parlay['total_odds']:.2f}",
                                f"${parlay['potential_payout']:.2f}",
                                parlay["status"].capitalize(),
                                parlay["created_at"].split("T")[0],
                            ])
                        
                        return parlays_data
                    except Exception as e:
                        logger.error(f"Error loading parlays: {str(e)}")
                        return []
                
                def get_parlay_details(evt: gr.SelectData):
                    """Get details for a selected parlay."""
                    try:
                        parlay_id = int(evt.value[0])
                        parlay = api_client.get_parlay(parlay_id)
                        return parlay
                    except Exception as e:
                        logger.error(f"Error getting parlay details: {str(e)}")
                        return {"error": str(e)}
                
                # Connect events
                parlay_status.change(load_parlays, inputs=parlay_status, outputs=parlays_table)
                refresh_parlays_btn.click(load_parlays, inputs=parlay_status, outputs=parlays_table)
                parlays_table.select(get_parlay_details, outputs=parlay_details)
            
            with gr.TabItem("Refresh Data"):
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("### Refresh Games")
                        days_input = gr.Slider(
                            minimum=1,
                            maximum=14,
                            value=7,
                            step=1,
                            label="Days to Fetch",
                        )
                        refresh_games_btn = gr.Button("Refresh Games")
                        games_result = gr.Textbox(label="Result")
                    
                    with gr.Column():
                        gr.Markdown("### Refresh Odds")
                        refresh_odds_btn = gr.Button("Refresh Odds")
                        odds_result = gr.Textbox(label="Result")
                
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("### Refresh News")
                        news_source = gr.Dropdown(
                            choices=["All", "ESPN", "The Athletic"],
                            value="All",
                            label="News Source",
                        )
                        news_days = gr.Slider(
                            minimum=1,
                            maximum=7,
                            value=1,
                            step=1,
                            label="Days to Fetch",
                        )
                        refresh_news_btn = gr.Button("Refresh News")
                        news_result = gr.Textbox(label="Result")
                    
                    with gr.Column():
                        gr.Markdown("### Update Parlay Statuses")
                        update_parlays_btn = gr.Button("Update Parlay Statuses")
                        update_result = gr.Textbox(label="Result")
                
                def refresh_games(days):
                    """Refresh games data from the API."""
                    try:
                        result = api_client.refresh_games(days=days)
                        return result.get("message", "Games refreshed successfully")
                    except Exception as e:
                        logger.error(f"Error refreshing games: {str(e)}")
                        return f"Error: {str(e)}"
                
                def refresh_odds():
                    """Refresh odds data from the API."""
                    try:
                        result = api_client.refresh_odds()
                        return result.get("message", "Odds refreshed successfully")
                    except Exception as e:
                        logger.error(f"Error refreshing odds: {str(e)}")
                        return f"Error: {str(e)}"
                
                def refresh_news(source, days):
                    """Refresh news data from the API."""
                    try:
                        source_param = None if source == "All" else source
                        result = api_client.refresh_news(source=source_param, days=days)
                        return result.get("message", "News refreshed successfully")
                    except Exception as e:
                        logger.error(f"Error refreshing news: {str(e)}")
                        return f"Error: {str(e)}"
                
                def update_parlay_statuses():
                    """Update parlay statuses from the API."""
                    try:
                        result = api_client.update_parlay_statuses()
                        return result.get("message", "Parlay statuses updated successfully")
                    except Exception as e:
                        logger.error(f"Error updating parlay statuses: {str(e)}")
                        return f"Error: {str(e)}"
                
                # Connect events
                refresh_games_btn.click(refresh_games, inputs=days_input, outputs=games_result)
                refresh_odds_btn.click(refresh_odds, outputs=odds_result)
                refresh_news_btn.click(refresh_news, inputs=[news_source, news_days], outputs=news_result)
                update_parlays_btn.click(update_parlay_statuses, outputs=update_result)
        
        # Load initial data
        parlay_status.change(fn=None)
    
    return app


if __name__ == "__main__":
    app = create_app()
    app.launch(server_name="0.0.0.0", server_port=7860)
