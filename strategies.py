import random

def strategy(user_input, instruments_list, trade_data):
    """
    Determines the trading strategy to use based on user input.

    Parameters:
    user_input (dict): Contains user preferences and settings for the trading strategy.
        - "account_type" (str): Type of account being used, e.g., "demo" or "live".
        - "trading_type" (str): Strategy type, e.g., "martingale" or "compounding".
        - "bet_level" (int): Level of bet in the strategy.
        - "bet_amounts" (list): List of bet amounts at each level.
        - "financial_instruments" (str): Type of financial instrument being traded, e.g., 'currency', 'cryptocurrency', 'commodity', 'stock', 'all'.
        - "market_type" (str): Type of market, e.g., "otc", "real", or "all".
        - "time_option" (int): Time type for trading, binary value 1 or 100.
        - "trade_time" (int): Duration of the trade, in seconds.
        - "minimum_return" (int): Minimum return percentage expected.
        - "trade_option" (str): Trade option to use, either 'call', 'put', or 'random' (default).
        - "profit_target" (int): Target profit for the trading session.
        - "loss_target" (int): Maximum allowable loss for the trading session.
    instruments_list (dict): Contains data about available financial instruments (input from the market).
        - This data should be checked in the config directory.
    trade_data (dict): Contains the current open trade data.
        - This data should be loaded from a JSON file in the cache directory.

    Returns:
    str: The trade option to use, either 'call' or 'put'.
    """
    # If 'trade_option' is set to 'random' (default), randomly select between 'call' or 'put'.
    # If 'trade_option' is explicitly set to 'call' or 'put', use that value.
    # Ensure that 'trade_option' is correctly set before returning it to the BOT for executing the trade.
    #user_input['trade_option'] = apply your logic
    if user_input['trade_option'] == 'random':
        return random.choice(['call', 'put'])
    # Else return a specified one
    return user_input['trade_option']

"""
# Example user input
user_input = {
    # This data should be populated from a JSON file "user_input.json" in the config directory
    "account_type": "demo",        # Type of account: 'demo' or 'live'
    "trading_type": "martingale",  # Strategy type: 'martingale' or 'compounding'
    "bet_level": 7,                # Current bet level
    "bet_amounts": [1, 2, 4, 8, 16, 32, 64],  # Bet amounts at each level
    "financial_instruments": "currency",  # Type of financial instrument
    "market_type": "otc",          # Market type: 'otc', 'real', or 'all'
    "time_option": 1,              # Time type for trading: binary value 1 or 100
    "trade_time": 5,               # Trade duration in seconds
    "minimum_return": 80,          # Minimum return percentage
    "trade_option": "random",      # Trade option: 'call', 'put', or 'random' (default)
    "profit_target": 10,           # Target profit
    "loss_target": 1000            # Maximum allowable loss
}

# Example instruments_list (to be checked in the config directory)
instruments_list = {
    # This data should be populated from a JSON file "instruments_list.json" in the config directory
}

# Example trade_data (to be checked in the cache directory)
trade_data = {
    # This data should be populated from a JSON file "new_order.json" in the cache directory
}
"""
