# Consumption Helper

An automated module to synchronize product consumption in Grocy using configurable rules.

## Project Structure

- `src/`: Project source code
  - `sync_consumption.py`: Main entry point that runs the synchronization
  - `shared_config.py`: Loads configuration from shared files
  - `consumption_state.json`: Persistent state of the synchronization (generated)

- Configuration files (JSON):
  - `../shared/settings.json`: Grocy credentials and settings
  - `../shared/grocy/consumption_rules.json`: Rules to mark products as consumed

## Installation

1. Install dependencies: `pip install -r ../shopping_copilot/src/requirements.txt`
2. Configure Grocy credentials in `shared/settings.json`
3. Define consumption rules in `shared/grocy/consumption_rules.json`

## Configuration

### consumption_rules.json

Define rules to automate product consumption. Example:

```json
{
  "settings": {
    "min_days_until_restock": 3,
    "shopping_list_id": 1,
    "dry_run": false
  },
  "products": {
    "Milk": {
      "grocy_product_id": 123,
      "consume_amount": 1,
      "consume_every_days": 7,
      "min_stock": 2,
      "buy_amount": 1
    }
  }
}
```

## How it works

The module:
- Loads settings and consumption rules
- Connects to the Grocy API
- Processes rules and marks products as consumed automatically
- Keeps persistent state in `consumption_state.json`
