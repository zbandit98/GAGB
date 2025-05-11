"""Analysis display component for the Gradio frontend."""

import logging
from typing import Dict, List, Optional, Any

import gradio as gr

from frontend.utils.api_client import APIClient

logger = logging.getLogger(__name__)


def create_analysis_display(api_client: APIClient, selected_game: gr.State) -> gr.Blocks:
    """
    Create an analysis display component.
    
    Args:
        api_client: API client for interacting with the backend
        selected_game: State containing the selected game
        
    Returns:
        Analysis display component
    """
    with gr.Blocks() as analysis_display:
        gr.Markdown("## Game Analysis")
        
        with gr.Row():
            refresh_analysis_btn = gr.Button("Refresh Analysis")
            force_refresh = gr.Checkbox(label="Force Refresh", value=False)
        
        game_info = gr.Markdown()
        analysis_content = gr.Markdown()
        confidence_score = gr.Slider(
            minimum=0.0,
            maximum=1.0,
            value=0.0,
            step=0.01,
            label="Confidence Score",
            interactive=False,
        )
        
        def load_game_info(game):
            """Load game information."""
            if not game:
                return "No game selected"
            
            try:
                home_team = game["home_team"]["name"]
                away_team = game["away_team"]["name"]
                game_time = game["game_time"].split("T")[0] + " " + game["game_time"].split("T")[1][:5]
                status = game["status"].capitalize()
                
                return f"### {home_team} vs {away_team}\n**Date/Time:** {game_time}\n**Status:** {status}"
            except Exception as e:
                logger.error(f"Error loading game info: {str(e)}")
                return "Error loading game information"
        
        def load_analysis(game, refresh):
            """Load analysis for the selected game."""
            if not game:
                return "No game selected", 0.0
            
            try:
                game_id = game["id"]
                analysis = api_client.analyze_game(game_id, refresh=refresh)
                
                # Extract content and confidence score
                content = analysis["analysis"]["content"]
                confidence = analysis["analysis"]["confidence_score"]
                
                return content, confidence
            except Exception as e:
                logger.error(f"Error loading analysis: {str(e)}")
                return f"Error loading analysis: {str(e)}", 0.0
        
        # Connect events
        selected_game.change(load_game_info, inputs=selected_game, outputs=game_info)
        selected_game.change(
            load_analysis,
            inputs=[selected_game, force_refresh],
            outputs=[analysis_content, confidence_score],
        )
        refresh_analysis_btn.click(
            load_analysis,
            inputs=[selected_game, force_refresh],
            outputs=[analysis_content, confidence_score],
        )
    
    return analysis_display
