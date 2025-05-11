"""Parlay builder component for the Gradio frontend."""

import logging
from typing import Dict, List, Optional, Any

import gradio as gr

from frontend.utils.api_client import APIClient

logger = logging.getLogger(__name__)


def create_parlay_builder(api_client: APIClient) -> gr.Blocks:
    """
    Create a parlay builder component.
    
    Args:
        api_client: API client for interacting with the backend
        
    Returns:
        Parlay builder component
    """
    with gr.Blocks() as parlay_builder:
        gr.Markdown("## Parlay Builder")
        
        with gr.Tabs() as parlay_tabs:
            with gr.TabItem("Manual Builder"):
                with gr.Row():
                    with gr.Column(scale=1):
                        parlay_name = gr.Textbox(
                            label="Parlay Name",
                            placeholder="Enter a name for your parlay",
                        )
                        stake_input = gr.Number(
                            label="Stake ($)",
                            value=10.0,
                            minimum=1.0,
                        )
                        
                        gr.Markdown("### Add Bet")
                        game_dropdown = gr.Dropdown(
                            choices=[],
                            label="Select Game",
                        )
                        bet_type = gr.Dropdown(
                            choices=["Moneyline", "Spread", "Over/Under", "Player Prop"],
                            label="Bet Type",
                            value="Moneyline",
                        )
                        player_dropdown = gr.Dropdown(
                            choices=[],
                            label="Player (for Props)",
                            visible=False,
                        )
                        prop_type = gr.Dropdown(
                            choices=["Points", "Goals", "Assists", "Shots on Goal"],
                            label="Prop Type",
                            visible=False,
                        )
                        selection = gr.Dropdown(
                            choices=[],
                            label="Selection",
                        )
                        add_bet_btn = gr.Button("Add Bet")
                    
                    with gr.Column(scale=2):
                        bets_table = gr.DataFrame(
                            headers=["Game", "Bet Type", "Selection", "Odds"],
                            label="Parlay Legs",
                        )
                        
                        with gr.Row():
                            total_odds = gr.Number(label="Total Odds", value=1.0, interactive=False)
                            potential_payout = gr.Number(label="Potential Payout ($)", value=0.0, interactive=False)
                        
                        create_parlay_btn = gr.Button("Create Parlay")
                        result_message = gr.Markdown()
            
            with gr.TabItem("AI Optimizer"):
                with gr.Row():
                    with gr.Column(scale=1):
                        ai_stake_input = gr.Number(
                            label="Stake ($)",
                            value=10.0,
                            minimum=1.0,
                        )
                        min_odds_input = gr.Number(
                            label="Minimum Total Odds",
                            value=2.0,
                            minimum=1.1,
                        )
                        max_legs_input = gr.Number(
                            label="Maximum Legs",
                            value=3,
                            minimum=1,
                            maximum=5,
                            step=1,
                        )
                        min_confidence_input = gr.Number(
                            label="Minimum Confidence",
                            value=0.6,
                            minimum=0.0,
                            maximum=1.0,
                            step=0.05,
                        )
                        game_filter = gr.CheckboxGroup(
                            choices=[],
                            label="Filter Games (Optional)",
                        )
                        optimize_btn = gr.Button("Optimize Parlay")
                    
                    with gr.Column(scale=2):
                        optimized_parlay = gr.JSON(label="Optimized Parlay")
                        save_optimized_btn = gr.Button("Save Optimized Parlay")
                        optimize_result = gr.Markdown()
        
        # State for storing bets
        bets_state = gr.State([])
        games_state = gr.State([])
        
        def load_games():
            """Load games from the API."""
            try:
                games = api_client.get_games(status="scheduled")
                
                # Store games in state
                games_dict = {game["id"]: game for game in games}
                
                # Format for dropdown
                game_choices = [
                    {
                        "value": game["id"],
                        "label": f"{game['home_team']['name']} vs {game['away_team']['name']} ({game['game_time'].split('T')[0]})",
                    }
                    for game in games
                ]
                
                # Format for checkbox group
                game_filter_choices = [
                    {
                        "value": game["id"],
                        "label": f"{game['home_team']['name']} vs {game['away_team']['name']} ({game['game_time'].split('T')[0]})",
                    }
                    for game in games
                ]
                
                return game_choices, game_filter_choices, games_dict
            except Exception as e:
                logger.error(f"Error loading games: {str(e)}")
                return [], [], {}
        
        def update_selection(game_id, bet_type, games_dict):
            """Update selection dropdown based on game and bet type."""
            if not game_id or not bet_type or not games_dict:
                return []
            
            try:
                game = games_dict.get(game_id)
                if not game:
                    return []
                
                if bet_type == "Moneyline":
                    return [
                        {"value": "home", "label": game["home_team"]["name"]},
                        {"value": "away", "label": game["away_team"]["name"]},
                    ]
                elif bet_type == "Spread":
                    return [
                        {"value": "home", "label": f"{game['home_team']['name']} -1.5"},
                        {"value": "away", "label": f"{game['away_team']['name']} +1.5"},
                    ]
                elif bet_type == "Over/Under":
                    return [
                        {"value": "over", "label": "Over 6.5"},
                        {"value": "under", "label": "Under 6.5"},
                    ]
                
                return []
            except Exception as e:
                logger.error(f"Error updating selection: {str(e)}")
                return []
        
        def add_bet(game_id, bet_type, selection, bets, games_dict, player_id=None, prop_type_value=None):
            """Add a bet to the parlay."""
            if not game_id or not bet_type or not selection or not games_dict:
                return bets, [], 1.0, 0.0
            
            try:
                game = games_dict.get(game_id)
                if not game:
                    return bets, [], 1.0, 0.0
                
                # Get odds for the bet
                odds = 1.91  # Default odds
                
                # In a real implementation, we would get the odds from the API
                # For now, we'll use some default values
                if bet_type == "Moneyline":
                    if selection == "home":
                        odds = 1.75
                    else:
                        odds = 2.05
                elif bet_type == "Spread":
                    odds = 1.91
                elif bet_type == "Over/Under":
                    odds = 1.91
                elif bet_type == "Player Prop":
                    if selection == "over":
                        odds = 1.85
                    else:
                        odds = 1.95
                
                # Add bet to list
                new_bet = {
                    "game_id": game_id,
                    "game_name": f"{game['home_team']['name']} vs {game['away_team']['name']}",
                    "bet_type": bet_type.lower(),
                    "selection": selection,
                    "odds": odds,
                }
                
                # Add player prop details if applicable
                if bet_type == "Player Prop" and player_id and prop_type_value:
                    new_bet["player_id"] = player_id
                    new_bet["prop_type"] = prop_type_value.lower()
                    
                    # Get player name from ID (in a real implementation, this would come from the API)
                    player_name = player_id
                    if "_" in player_id:
                        team_prefix, player_num = player_id.split("_", 1)
                        team_type = "Home" if team_prefix.startswith("h") else "Away"
                        player_name = f"{team_type} Player {player_num.split('_')[1]}"
                    
                    # Format selection for display
                    line = "0.5"
                    if prop_type_value.lower() == "shots on goal":
                        line = "2.5"
                    
                    display_selection = f"{player_name} {selection.capitalize()} {line} {prop_type_value}"
                    new_bet["display_selection"] = display_selection
                
                updated_bets = bets + [new_bet]
                
                # Format for display
                bets_data = []
                total_odds_value = 1.0
                
                for bet in updated_bets:
                    bets_data.append([
                        bet["game_name"],
                        bet["bet_type"].capitalize(),
                        bet["selection"].capitalize(),
                        f"{bet['odds']:.2f}",
                    ])
                    total_odds_value *= bet["odds"]
                
                # Calculate potential payout
                potential_payout_value = stake_input.value * total_odds_value
                
                return updated_bets, bets_data, total_odds_value, potential_payout_value
            except Exception as e:
                logger.error(f"Error adding bet: {str(e)}")
                return bets, [], 1.0, 0.0
        
        def update_potential_payout(stake, total_odds):
            """Update potential payout based on stake and total odds."""
            return stake * total_odds
        
        def create_parlay(name, stake, bets):
            """Create a parlay with the specified bets."""
            if not bets:
                return "Please add at least one bet to the parlay."
            
            try:
                # Format bets for API
                api_bets = []
                for bet in bets:
                    api_bets.append({
                        "game_id": bet["game_id"],
                        "bet_type": bet["bet_type"],
                        "selection": bet["selection"],
                        "odds": bet["odds"],
                    })
                
                # Create parlay
                parlay = api_client.create_parlay(name, stake, api_bets)
                
                return f"Parlay created successfully! ID: {parlay['id']}"
            except Exception as e:
                logger.error(f"Error creating parlay: {str(e)}")
                return f"Error creating parlay: {str(e)}"
        
        def optimize_parlay(stake, min_odds, max_legs, min_confidence, game_ids):
            """Optimize a parlay using AI."""
            try:
                # Convert game_ids to list of integers
                game_ids_list = [int(game_id) for game_id in game_ids] if game_ids else None
                
                # Call API to optimize parlay
                parlay = api_client.optimize_parlay(
                    stake=stake,
                    game_ids=game_ids_list,
                    min_odds=min_odds,
                    max_legs=max_legs,
                    min_confidence=min_confidence,
                )
                
                return parlay
            except Exception as e:
                logger.error(f"Error optimizing parlay: {str(e)}")
                return {"error": str(e)}
        
        def save_optimized_parlay(parlay):
            """Save an optimized parlay."""
            if not parlay or "error" in parlay:
                return "No valid parlay to save."
            
            try:
                # Format bets for API
                api_bets = []
                for leg in parlay["parlay"]["legs"]:
                    api_bets.append({
                        "game_id": leg["game"]["id"],
                        "bet_type": leg["bet_type"],
                        "selection": leg["selection"],
                        "odds": leg["odds"],
                        "justification": leg["justification"],
                    })
                
                # Create parlay
                saved_parlay = api_client.create_parlay(
                    parlay["parlay"]["name"],
                    parlay["parlay"]["stake"],
                    api_bets,
                )
                
                return f"Parlay saved successfully! ID: {saved_parlay['id']}"
            except Exception as e:
                logger.error(f"Error saving parlay: {str(e)}")
                return f"Error saving parlay: {str(e)}"
        
        # Load initial data
        game_choices, game_filter_choices, games_dict = load_games()
        game_dropdown.choices = game_choices
        game_filter.choices = game_filter_choices
        games_state.value = games_dict
        
        def update_bet_type_ui(bet_type_value):
            """Update UI based on bet type selection."""
            if bet_type_value == "Player Prop":
                return gr.update(visible=True), gr.update(visible=True)
            else:
                return gr.update(visible=False), gr.update(visible=False)
        
        def load_players(game_id, games_dict):
            """Load players for the selected game."""
            if not game_id or not games_dict:
                return []
            
            try:
                game = games_dict.get(game_id)
                if not game:
                    return []
                
                # In a real implementation, we would get the players from the API
                # For now, we'll use some mock data
                home_team = game["home_team"]["name"]
                away_team = game["away_team"]["name"]
                
                # Mock players for each team
                home_players = [
                    {"id": f"h1_{game_id}", "name": f"{home_team} Player 1", "position": "C"},
                    {"id": f"h2_{game_id}", "name": f"{home_team} Player 2", "position": "LW"},
                    {"id": f"h3_{game_id}", "name": f"{home_team} Player 3", "position": "RW"},
                    {"id": f"h4_{game_id}", "name": f"{home_team} Player 4", "position": "D"},
                    {"id": f"h5_{game_id}", "name": f"{home_team} Player 5", "position": "D"},
                ]
                
                away_players = [
                    {"id": f"a1_{game_id}", "name": f"{away_team} Player 1", "position": "C"},
                    {"id": f"a2_{game_id}", "name": f"{away_team} Player 2", "position": "LW"},
                    {"id": f"a3_{game_id}", "name": f"{away_team} Player 3", "position": "RW"},
                    {"id": f"a4_{game_id}", "name": f"{away_team} Player 4", "position": "D"},
                    {"id": f"a5_{game_id}", "name": f"{away_team} Player 5", "position": "D"},
                ]
                
                # Format for dropdown
                player_choices = []
                for player in home_players + away_players:
                    player_choices.append({
                        "value": player["id"],
                        "label": f"{player['name']} ({player['position']})",
                    })
                
                return player_choices
            except Exception as e:
                logger.error(f"Error loading players: {str(e)}")
                return []
        
        def update_prop_selection(prop_type_value):
            """Update selection dropdown based on prop type."""
            if not prop_type_value:
                return []
            
            try:
                prop_type_lower = prop_type_value.lower()
                
                if prop_type_lower == "points":
                    return [
                        {"value": "over", "label": "Over 0.5 Points"},
                        {"value": "under", "label": "Under 0.5 Points"},
                    ]
                elif prop_type_lower == "goals":
                    return [
                        {"value": "over", "label": "Over 0.5 Goals"},
                        {"value": "under", "label": "Under 0.5 Goals"},
                    ]
                elif prop_type_lower == "assists":
                    return [
                        {"value": "over", "label": "Over 0.5 Assists"},
                        {"value": "under", "label": "Under 0.5 Assists"},
                    ]
                elif prop_type_lower == "shots on goal":
                    return [
                        {"value": "over", "label": "Over 2.5 Shots"},
                        {"value": "under", "label": "Under 2.5 Shots"},
                    ]
                
                return []
            except Exception as e:
                logger.error(f"Error updating prop selection: {str(e)}")
                return []
        
        # Connect events
        game_dropdown.change(
            update_selection,
            inputs=[game_dropdown, bet_type, games_state],
            outputs=selection,
        )
        game_dropdown.change(
            load_players,
            inputs=[game_dropdown, games_state],
            outputs=player_dropdown,
        )
        bet_type.change(
            update_bet_type_ui,
            inputs=bet_type,
            outputs=[player_dropdown, prop_type],
        )
        bet_type.change(
            update_selection,
            inputs=[game_dropdown, bet_type, games_state],
            outputs=selection,
        )
        prop_type.change(
            update_prop_selection,
            inputs=prop_type,
            outputs=selection,
        )
        add_bet_btn.click(
            add_bet,
            inputs=[game_dropdown, bet_type, selection, bets_state, games_state, player_dropdown, prop_type],
            outputs=[bets_state, bets_table, total_odds, potential_payout],
        )
        stake_input.change(
            update_potential_payout,
            inputs=[stake_input, total_odds],
            outputs=potential_payout,
        )
        create_parlay_btn.click(
            create_parlay,
            inputs=[parlay_name, stake_input, bets_state],
            outputs=result_message,
        )
        optimize_btn.click(
            optimize_parlay,
            inputs=[ai_stake_input, min_odds_input, max_legs_input, min_confidence_input, game_filter],
            outputs=optimized_parlay,
        )
        save_optimized_btn.click(
            save_optimized_parlay,
            inputs=optimized_parlay,
            outputs=optimize_result,
        )
    
    return parlay_builder
