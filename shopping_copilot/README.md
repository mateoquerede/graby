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

1. Easiest: run `run.bat` from repository root. It installs dependencies if needed, then starts shopping.
2. If `shared/settings.json` has no Coto credentials, `run.bat` asks for email and password in terminal and saves them automatically.
3. Run `run.bat` again to execute the bot.

Alternative:
1. From repository root, run `install.bat` (double click or terminal).
2. Run `shopping.bat` from repository root.

Manual install (optional):
1. Install dependencies: `pip install -r src/requirements.txt`
2. Install Ollama and the llama3 model
3. Configure `shared/settings.json`
4. Run: `python -m shopping_copilot.src.main`

### Debug logs

Set `"debug": true` in `shared/settings.json` to enable verbose internal logs.
With `"debug": false`, the bot keeps visible only useful progress, warnings, errors,
and the final product-selection reason.

## How it works

The bot loads the shopping list, plans searches, logs in, clears the cart, searches and adds products automatically, and leaves the cart ready for manual checkout.