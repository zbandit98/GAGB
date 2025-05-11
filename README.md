# GAGB - Generative AI Gambling Bot

A sports betting decision assistant that leverages news sources, sportsbook APIs, and generative AI to create optimized parlays for NHL betting.

## Features

- **Odds Comparison**: Compare betting odds from multiple sportsbooks (DraftKings, FanDuel)
- **Optimal Parlay Generation**: AI-powered generation of optimal parlays based on available odds
- **News Analysis**: Integration with sports news sources (ESPN, The Athletic) for informed decisions
- **Justification**: Detailed justification for each leg of the parlay based on news and historical analysis
- **Confidence Scoring**: Assessment of parlay confidence based on comprehensive analysis

## Tech Stack

- **Backend**: FastAPI
- **Frontend**: Gradio
- **Dependency Management**: UV
- **Database**: SQLite (initially)
- **AI Integration**: Claude/Anthropic API

## Project Structure

```
gagb/
├── backend/         # FastAPI application
│   ├── app/         # Application code
│   └── tests/       # Backend tests
├── frontend/        # Gradio UI
└── scripts/         # Utility scripts
```

## Getting Started

### Prerequisites

- Python 3.9+
- UV package manager

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/gagb.git
   cd gagb
   ```

2. Create a virtual environment and install dependencies:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   uv pip install -e ".[dev]"
   ```

3. Create a `.env` file based on `.env.example` and add your API keys.

### Running the Application

1. Start the FastAPI backend:
   ```
   uvicorn backend.app.main:app --reload
   ```

2. In a separate terminal, start the Gradio frontend:
   ```
   python -m frontend.app
   ```

3. Access the application at http://localhost:7860

## Development

### Running Tests

```
pytest
```

### Code Formatting

```
black .
isort .
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
