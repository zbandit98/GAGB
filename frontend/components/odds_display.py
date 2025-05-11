"""Odds display component for the Gradio frontend."""

import logging
from typing import Dict, List, Optional, Any

import gradio as gr

from frontend.utils.api_client import APIClient

logger = logging.getLogger(__name__)


def create_odds_display(api_client: APIClient, selected_game: gr.State) -> gr.Blocks:
    """
    Create an odds display component.
    
    Args:
        api_client: API client for interacting with the backend
        selected_game: State containing the selected game
        
    Returns:
        Odds display component
    """
    with gr.Blocks() as odds_display:
        gr.Markdown("## Betting Odds")
        
        with gr.Row():
            refresh_odds_btn = gr.Button("Refresh Odds")
        
        with gr.Tabs() as odds_tabs:
            with gr.TabItem("Compare Odds"):
                odds_table = gr.DataFrame(
                    headers=["Sportsbook", "Home ML", "Away ML", "Spread", "Home Spread", "Away Spread", "Total", "Over", "Under"],
                    label="Odds Comparison",
                )
            
            with gr.TabItem("Best Odds"):
                best_odds_json = gr.JSON(label="Best Available Odds")
            
            with gr.TabItem("Player Props"):
                with gr.Row():
                    prop_type_filter = gr.Dropdown(
                        choices=["All", "Points", "Goals", "Assists", "Shots on Goal"],
                        label="Prop Type",
                        value="All",
                    )
                    sportsbook_filter = gr.Dropdown(
                        choices=["All", "DraftKings", "FanDuel"],
                        label="Sportsbook",
                        value="All",
                    )
                    refresh_props_btn = gr.Button("Refresh Props")
                
                player_props_table = gr.DataFrame(
                    headers=["Player", "Team", "Prop Type", "Line", "Over Odds", "Under Odds", "Sportsbook"],
                    label="Player Props",
                )
        
        def load_odds_comparison(game):
            """Load odds comparison for the selected game."""
            if not game:
                return []
            
            try:
                game_id = game["id"]
                odds_list = api_client.compare_odds(game_id)
                
                # Format for display
                odds_data = []
                for odds in odds_list:
                    odds_data.append([
                        odds["sportsbook"],
                        f"{odds['home_moneyline']:+d}" if odds["home_moneyline"] is not None else "N/A",
                        f"{odds['away_moneyline']:+d}" if odds["away_moneyline"] is not None else "N/A",
                        f"{odds['home_spread']:.1f}" if odds["home_spread"] is not None else "N/A",
                        f"{odds['home_spread_odds']:+d}" if odds["home_spread_odds"] is not None else "N/A",
                        f"{odds['away_spread_odds']:+d}" if odds["away_spread_odds"] is not None else "N/A",
                        f"{odds['over_under']:.1f}" if odds["over_under"] is not None else "N/A",
                        f"{odds['over_odds']:+d}" if odds["over_odds"] is not None else "N/A",
                        f"{odds['under_odds']:+d}" if odds["under_odds"] is not None else "N/A",
                    ])
                
                return odds_data
            except Exception as e:
                logger.error(f"Error loading odds comparison: {str(e)}")
                return []
        
        def load_best_odds(game):
            """Load best odds for the selected game."""
            if not game:
                return {}
            
            try:
                game_id = game["id"]
                best_odds = api_client.get_best_odds(game_id)
                
                # Format for display
                game_info = {
                    "Game": f"{best_odds['game']['home_team']['name']} vs {best_odds['game']['away_team']['name']}",
                    "Date/Time": best_odds["game"]["game_time"].split("T")[0] + " " + best_odds["game"]["game_time"].split("T")[1][:5],
                    "Status": best_odds["game"]["status"].capitalize(),
                }
                
                best_odds_formatted = {
                    "Game Info": game_info,
                    "Best Odds": {
                        "Home Moneyline": {
                            "Team": best_odds["game"]["home_team"]["name"],
                            "Odds": f"{best_odds['best_odds']['home_moneyline']['odds']:+d}" if best_odds["best_odds"]["home_moneyline"]["odds"] is not None else "N/A",
                            "Sportsbook": best_odds["best_odds"]["home_moneyline"]["sportsbook"],
                        },
                        "Away Moneyline": {
                            "Team": best_odds["game"]["away_team"]["name"],
                            "Odds": f"{best_odds['best_odds']['away_moneyline']['odds']:+d}" if best_odds["best_odds"]["away_moneyline"]["odds"] is not None else "N/A",
                            "Sportsbook": best_odds["best_odds"]["away_moneyline"]["sportsbook"],
                        },
                        "Home Spread": {
                            "Team": best_odds["game"]["home_team"]["name"],
                            "Spread": f"{best_odds['best_odds']['home_spread']['spread']:.1f}" if best_odds["best_odds"]["home_spread"]["spread"] is not None else "N/A",
                            "Odds": f"{best_odds['best_odds']['home_spread']['odds']:+d}" if best_odds["best_odds"]["home_spread"]["odds"] is not None else "N/A",
                            "Sportsbook": best_odds["best_odds"]["home_spread"]["sportsbook"],
                        },
                        "Away Spread": {
                            "Team": best_odds["game"]["away_team"]["name"],
                            "Spread": f"{best_odds['best_odds']['away_spread']['spread']:.1f}" if best_odds["best_odds"]["away_spread"]["spread"] is not None else "N/A",
                            "Odds": f"{best_odds['best_odds']['away_spread']['odds']:+d}" if best_odds["best_odds"]["away_spread"]["odds"] is not None else "N/A",
                            "Sportsbook": best_odds["best_odds"]["away_spread"]["sportsbook"],
                        },
                        "Over": {
                            "Total": f"{best_odds['best_odds']['over']['total']:.1f}" if best_odds["best_odds"]["over"]["total"] is not None else "N/A",
                            "Odds": f"{best_odds['best_odds']['over']['odds']:+d}" if best_odds["best_odds"]["over"]["odds"] is not None else "N/A",
                            "Sportsbook": best_odds["best_odds"]["over"]["sportsbook"],
                        },
                        "Under": {
                            "Total": f"{best_odds['best_odds']['under']['total']:.1f}" if best_odds["best_odds"]["under"]["total"] is not None else "N/A",
                            "Odds": f"{best_odds['best_odds']['under']['odds']:+d}" if best_odds["best_odds"]["under"]["odds"] is not None else "N/A",
                            "Sportsbook": best_odds["best_odds"]["under"]["sportsbook"],
                        },
                    },
                }
                
                return best_odds_formatted
            except Exception as e:
                logger.error(f"Error loading best odds: {str(e)}")
                return {"error": str(e)}
        
        def refresh_odds(game):
            """Refresh odds for the selected game."""
            if not game:
                return [], {}
            
            try:
                game_id = game["id"]
                api_client.refresh_odds(game_id=game_id)
                
                # Reload odds
                odds_data = load_odds_comparison(game)
                best_odds_data = load_best_odds(game)
                
                return odds_data, best_odds_data
            except Exception as e:
                logger.error(f"Error refreshing odds: {str(e)}")
                return [], {"error": str(e)}
        
        def load_player_props(game, prop_type, sportsbook):
            """Load player props for the selected game."""
            if not game:
                return []
            
            try:
                game_id = game["id"]
                
                # Set up filters
                prop_type_filter = None if prop_type == "All" else prop_type.lower().replace(" ", "_")
                sportsbook_filter = None if sportsbook == "All" else sportsbook
                
                # Get player props
                props = api_client.get_player_props(
                    game_id=game_id,
                    prop_type=prop_type_filter,
                    sportsbook=sportsbook_filter,
                )
                
                # Format for display
                props_data = []
                for prop in props:
                    props_data.append([
                        prop["player"]["name"],
                        prop["player"]["team"]["name"],
                        prop["prop_type"].replace("_", " ").title(),
                        f"{prop['line']:.1f}",
                        f"{prop['over_odds']:+d}" if prop["over_odds"] is not None else "N/A",
                        f"{prop['under_odds']:+d}" if prop["under_odds"] is not None else "N/A",
                        prop["sportsbook"],
                    ])
                
                return props_data
            except Exception as e:
                logger.error(f"Error loading player props: {str(e)}")
                return []
        
        def refresh_player_props(game, prop_type, sportsbook):
            """Refresh player props for the selected game."""
            if not game:
                return []
            
            try:
                game_id = game["id"]
                
                # Refresh props
                api_client.refresh_player_props(game_id=game_id)
                
                # Reload props
                return load_player_props(game, prop_type, sportsbook)
            except Exception as e:
                logger.error(f"Error refreshing player props: {str(e)}")
                return []
        
        # Connect events
        selected_game.change(load_odds_comparison, inputs=selected_game, outputs=odds_table)
        selected_game.change(load_best_odds, inputs=selected_game, outputs=best_odds_json)
        selected_game.change(
            load_player_props,
            inputs=[selected_game, prop_type_filter, sportsbook_filter],
            outputs=player_props_table,
        )
        refresh_odds_btn.click(refresh_odds, inputs=selected_game, outputs=[odds_table, best_odds_json])
        refresh_props_btn.click(
            refresh_player_props,
            inputs=[selected_game, prop_type_filter, sportsbook_filter],
            outputs=player_props_table,
        )
        prop_type_filter.change(
            load_player_props,
            inputs=[selected_game, prop_type_filter, sportsbook_filter],
            outputs=player_props_table,
        )
        sportsbook_filter.change(
            load_player_props,
            inputs=[selected_game, prop_type_filter, sportsbook_filter],
            outputs=player_props_table,
        )
    
    return odds_display
