"""Game selector component for the Gradio frontend."""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any

import gradio as gr

from frontend.utils.api_client import APIClient

logger = logging.getLogger(__name__)


def create_game_selector(api_client: APIClient) -> Tuple[gr.Blocks, gr.State]:
    """
    Create a game selector component.
    
    Args:
        api_client: API client for interacting with the backend
        
    Returns:
        Tuple of (game_selector, selected_game)
    """
    with gr.Blocks() as game_selector:
        selected_game = gr.State(None)
        
        with gr.Row():
            with gr.Column(scale=1):
                date_picker = gr.Textbox(
                    label="Date (YYYY-MM-DD)",
                    placeholder="Leave empty for upcoming games",
                )
                days_slider = gr.Slider(
                    minimum=1,
                    maximum=14,
                    value=7,
                    step=1,
                    label="Days to Show",
                )
            
            with gr.Column(scale=1):
                team_dropdown = gr.Dropdown(
                    choices=[],
                    label="Filter by Team",
                    multiselect=False,
                )
                status_dropdown = gr.Dropdown(
                    choices=["All", "Scheduled", "In Progress", "Finished"],
                    value="All",
                    label="Filter by Status",
                )
            
            with gr.Column(scale=1):
                refresh_btn = gr.Button("Refresh Games")
        
        games_table = gr.DataFrame(
            headers=["ID", "Home Team", "Away Team", "Date/Time", "Status"],
            label="Upcoming Games",
        )
        
        def load_teams():
            """Load teams from the API."""
            try:
                teams = api_client.get_teams()
                return [{"value": None, "label": "All Teams"}] + [
                    {"value": team["id"], "label": team["name"]}
                    for team in teams
                ]
            except Exception as e:
                logger.error(f"Error loading teams: {str(e)}")
                return [{"value": None, "label": "All Teams"}]
        
        def load_games(date, days, team_id, status):
            """Load games from the API."""
            try:
                # Convert status to API format
                api_status = status.lower() if status != "All" else None
                
                # Convert team_id to int if not None
                api_team_id = int(team_id) if team_id else None
                
                # Get games from API
                games = api_client.get_games(
                    date=date if date else None,
                    team_id=api_team_id,
                    status=api_status,
                    days=days,
                )
                
                # Format for display
                games_data = []
                for game in games:
                    games_data.append([
                        game["id"],
                        game["home_team"]["name"],
                        game["away_team"]["name"],
                        game["game_time"].split("T")[0] + " " + game["game_time"].split("T")[1][:5],
                        game["status"].capitalize(),
                    ])
                
                return games_data
            except Exception as e:
                logger.error(f"Error loading games: {str(e)}")
                return []
        
        def select_game(evt: gr.SelectData):
            """Select a game from the table."""
            try:
                game_id = int(evt.value[0])
                game = api_client.get_game(game_id)
                return game
            except Exception as e:
                logger.error(f"Error selecting game: {str(e)}")
                return None
        
        # Connect events
        team_dropdown.choices = load_teams()
        refresh_btn.click(
            load_games,
            inputs=[date_picker, days_slider, team_dropdown, status_dropdown],
            outputs=games_table,
        )
        date_picker.change(
            load_games,
            inputs=[date_picker, days_slider, team_dropdown, status_dropdown],
            outputs=games_table,
        )
        days_slider.change(
            load_games,
            inputs=[date_picker, days_slider, team_dropdown, status_dropdown],
            outputs=games_table,
        )
        team_dropdown.change(
            load_games,
            inputs=[date_picker, days_slider, team_dropdown, status_dropdown],
            outputs=games_table,
        )
        status_dropdown.change(
            load_games,
            inputs=[date_picker, days_slider, team_dropdown, status_dropdown],
            outputs=games_table,
        )
        games_table.select(select_game, outputs=selected_game)
        
        # Load initial data
        refresh_btn.click(fn=None)
    
    return game_selector, selected_game
