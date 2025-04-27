import csv
import os
from datetime import datetime

def save_data(trades_data, filename):
    """
    Save the trading data to a CSV file.
    
    Args:
        trades_data (list): List of dictionaries containing trade data for each day
        filename (str): Filename to save the data
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with open(filename, 'w', newline='') as f:
            # Create CSV writer
            writer = csv.writer(f)
            
            # Write header
            writer.writerow(['Day', 'Date', 'Trades'])
            
            # Write data for each day
            for day in trades_data:
                # Convert trades to string format
                trade_strings = []
                for trade in day['trades']:
                    if trade['type'] == 'BE':
                        trade_strings.append('BE')
                    else:
                        trade_strings.append(f"{trade['type']}{trade['r_multiple']}R")
                
                trades_str = ','.join(trade_strings)
                writer.writerow([day['day'], day['date'], trades_str])
                
        return True
    except Exception as e:
        print(f"Error saving data: {e}")
        return False

def load_data(filename):
    """
    Load trading data from a CSV file.
    
    Args:
        filename (str): Filename to load the data from
    
    Returns:
        list: List of dictionaries containing trade data for each day, or None if loading fails
    """
    try:
        trades_data = []
        
        with open(filename, 'r', newline='') as f:
            reader = csv.reader(f)
            
            # Skip header
            next(reader)
            
            # Read each row
            for row in reader:
                if len(row) != 3:
                    continue
                    
                day_num, date_str, trades_str = row
                
                # Parse trades
                from trade_analyzer import parse_trade_data
                trades = parse_trade_data(trades_str)
                
                if trades:
                    day_data = {
                        'day': int(day_num),
                        'date': date_str,
                        'trades': trades
                    }
                    trades_data.append(day_data)
        
        return trades_data
    except Exception as e:
        print(f"Error loading data: {e}")
        return None
