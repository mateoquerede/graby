# CotoBot

An automated bot for shopping on Coto Digital using Playwright and Ollama.

## Project Structure

- `src/`: Project source code
  - `main.py`: Main entry point
  - `planner.py`: Plans search queries using AI
  - `login.py`: Handles login to the site
  - `cart.py`: Manages the shopping cart
  - `search.py`: Product search functions
  - `product_parser.py`: Parses product details and pricing
  - `add_product.py`: Adds products to the cart
  - `evaluator.py`: Evaluates products with AI
  - `config.py`: Loads JSON configuration
  - `requirements.txt`: Python dependencies

- Configuration files (JSON):
  - `shopping_list.json`: Shopping list of products
  - `settings.json`: Login credentials (copy from `settings.example.json`)
  - `rules.json`: Rules for product evaluation
  - `blocked.json`: Blocked PLUs

## Installation

1. Install dependencies: `pip install -r src/requirements.txt`
2. Install Ollama and the llama3 model
3. Copy `settings.example.json` to `settings.json` and configure your credentials
4. Run: `python src/main.py`

## How it works

The bot loads the shopping list, plans searches, logs in, clears the cart, searches and adds products automatically, and leaves the cart ready for manual checkout.