import re
import math
import numpy as np
from datetime import datetime

def parse_trade_data(trade_input):
    """
    Parse the trade data input string into a structured format.
    
    Args:
        trade_input (str): String containing trade data in the format W2R, L1R, BE, etc.
        
    Returns:
        list: List of dictionaries with trade information
    """
    # Clean and split the input
    trade_input = trade_input.replace(" ", "")
    trade_entries = trade_input.split(",")
    
    trades = []
    
    for entry in trade_entries:
        entry = entry.strip().upper()
        
        # Skip empty entries
        if not entry:
            continue
            
        # Check for break-even trades
        if entry == "BE":
            trades.append({
                "type": "BE",
                "r_multiple": 0
            })
            continue
            
        # Parse win/loss trades with R-multiple
        match = re.match(r"([WL])([-+]?\d*\.?\d*)R?", entry)
        
        if match:
            trade_type, r_str = match.groups()
            
            # Default to 1R if no value is provided (e.g., "W" instead of "W1R")
            r_multiple = 1.0 if not r_str else float(r_str)
            
            trades.append({
                "type": trade_type,
                "r_multiple": r_multiple
            })
        else:
            # Invalid format
            return None
            
    return trades

def analyze_trades(trades_data, initial_balance=25000.0, risk_amount=250.0):
    """
    Analyze the trade data and calculate performance metrics.
    
    Args:
        trades_data (list): List of dictionaries containing trade data for each day
        initial_balance (float): Initial account balance
        risk_amount (float): Risk amount per trade (1R)
        
    Returns:
        dict: Dictionary with analysis results
    """
    # Initialize variables for overall metrics
    total_trades = 0
    total_wins = 0
    total_losses = 0
    total_breakeven = 0
    total_r_won = 0
    total_r_lost = 0
    
    # Initialize daily results
    daily_results = []
    
    # Track account balance
    current_balance = initial_balance
    peak_balance = initial_balance
    
    # For tracking equity curve and drawdown
    equity_curve = [initial_balance]
    daily_returns = []
    
    # For tracking win/loss streaks
    current_win_streak = 0
    current_loss_streak = 0
    max_win_streak = 0
    max_loss_streak = 0
    
    # For tracking time-based performance
    day_of_week_performance = {'Monday': [], 'Tuesday': [], 'Wednesday': [], 'Thursday': [], 'Friday': []}
    week_of_month_performance = {1: [], 2: [], 3: [], 4: [], 5: []}  # 1st to 5th week
    month_performance = {1: [], 2: [], 3: [], 4: [], 5: [], 6: [], 7: [], 8: [], 9: [], 10: [], 11: [], 12: []}
    
    # Create a list of all trade R-multiples for SQN calculation
    all_trade_r = []
    
    # Process each trading day
    for day_data in trades_data:
        day_number = day_data['day']
        day_date = day_data['date']
        day_trades = day_data['trades']
        
        # Parse date and get time periods
        try:
            date_obj = datetime.strptime(day_date, "%Y-%m-%d")
            day_of_week = date_obj.strftime("%A")
            
            # Get month (1-12)
            month = date_obj.month
            
            # Calculate week of month (1-5)
            # First get the first day of the month
            first_day = date_obj.replace(day=1)
            # Get days since the first Monday (or start of week) of the month
            dom = date_obj.day
            adjusted_dom = dom + first_day.weekday()
            week_of_month = (adjusted_dom - 1) // 7 + 1
        except:
            day_of_week = "Unknown"
            month = None
            week_of_month = None
        
        # Track consecutive wins/losses within this day
        day_had_win = False
        day_had_loss = False
        
        # Calculate daily metrics
        day_trade_count = len(day_trades)
        day_wins = sum(1 for trade in day_trades if trade['type'] == 'W')
        day_losses = sum(1 for trade in day_trades if trade['type'] == 'L')
        day_breakeven = sum(1 for trade in day_trades if trade['type'] == 'BE')
        
        day_r_won = sum(trade['r_multiple'] for trade in day_trades if trade['type'] == 'W')
        day_r_lost = sum(trade['r_multiple'] for trade in day_trades if trade['type'] == 'L')
        day_net_r = day_r_won - day_r_lost
        
        # Add individual trade R values to master list
        for trade in day_trades:
            if trade['type'] == 'W':
                all_trade_r.append(trade['r_multiple'])
                day_had_win = True
            elif trade['type'] == 'L':
                all_trade_r.append(-trade['r_multiple'])
                day_had_loss = True
            # BE trades contribute 0R
            else:
                all_trade_r.append(0)
        
        # Calculate win rate (excluding break-even trades)
        non_be_trades = day_wins + day_losses
        day_win_rate = (day_wins / non_be_trades * 100) if non_be_trades > 0 else 0
        
        # Calculate daily P&L in dollar terms
        day_pnl = day_net_r * risk_amount
        
        # Update account balance
        previous_balance = current_balance
        current_balance += day_pnl
        
        # Update peak balance for drawdown calculation
        if current_balance > peak_balance:
            peak_balance = current_balance
        
        # Calculate daily return for Sharpe ratio
        if previous_balance > 0:
            daily_return = day_pnl / previous_balance
            daily_returns.append(daily_return)
        
        # Update win/loss streaks
        if day_net_r > 0:
            current_win_streak += 1
            current_loss_streak = 0
            if current_win_streak > max_win_streak:
                max_win_streak = current_win_streak
        elif day_net_r < 0:
            current_loss_streak += 1
            current_win_streak = 0
            if current_loss_streak > max_loss_streak:
                max_loss_streak = current_loss_streak
        # If day_net_r is 0, neither streak is affected
        
        # Track time-period performance
        if day_of_week in day_of_week_performance:
            day_of_week_performance[day_of_week].append(day_net_r)
            
        if week_of_month is not None and week_of_month in week_of_month_performance:
            week_of_month_performance[week_of_month].append(day_net_r)
            
        if month is not None and month in month_performance:
            month_performance[month].append(day_net_r)
        
        # Store equity point for drawdown calculations
        equity_curve.append(current_balance)
        
        # Store daily results
        daily_results.append({
            'day': day_number,
            'date': day_date,
            'day_of_week': day_of_week,
            'week_of_month': week_of_month,
            'month': month,
            'num_trades': day_trade_count,
            'wins': day_wins,
            'losses': day_losses,
            'breakeven': day_breakeven,
            'r_won': day_r_won,
            'r_lost': day_r_lost,
            'net_r': day_net_r,
            'win_rate': day_win_rate,
            'daily_pnl': day_pnl,
            'end_balance': current_balance
        })
        
        # Update overall totals
        total_trades += day_trade_count
        total_wins += day_wins
        total_losses += day_losses
        total_breakeven += day_breakeven
        total_r_won += day_r_won
        total_r_lost += day_r_lost
    
    # Calculate overall metrics
    total_non_be_trades = total_wins + total_losses
    overall_win_rate = (total_wins / total_non_be_trades * 100) if total_non_be_trades > 0 else 0
    
    total_r = total_r_won - total_r_lost
    
    profit_factor = (total_r_won / total_r_lost) if total_r_lost > 0 else float('inf')
    
    avg_win_r = (total_r_won / total_wins) if total_wins > 0 else 0
    avg_loss_r = (total_r_lost / total_losses) if total_losses > 0 else 0
    avg_risk_reward = (avg_win_r / avg_loss_r) if avg_loss_r > 0 else float('inf')
    
    net_pnl = total_r * risk_amount
    
    # Calculate Maximum Drawdown
    max_drawdown_pct = 0
    max_drawdown_amount = 0
    
    if len(equity_curve) > 1:
        peak = equity_curve[0]
        for equity in equity_curve[1:]:
            if equity > peak:
                peak = equity
            drawdown = peak - equity
            drawdown_pct = (drawdown / peak) * 100 if peak > 0 else 0
            
            if drawdown > max_drawdown_amount:
                max_drawdown_amount = drawdown
                max_drawdown_pct = drawdown_pct
    
    # Calculate Expectancy
    expectancy = (overall_win_rate/100 * avg_win_r) - ((100-overall_win_rate)/100 * avg_loss_r)
    
    # Calculate Sharpe Ratio (assuming risk-free rate of 0%)
    if len(daily_returns) > 1:
        avg_return = sum(daily_returns) / len(daily_returns)
        std_dev = math.sqrt(sum((r - avg_return) ** 2 for r in daily_returns) / len(daily_returns))
        sharpe_ratio = (avg_return / std_dev) * math.sqrt(252) if std_dev > 0 else 0
    else:
        sharpe_ratio = 0
    
    # Calculate System Quality Number (SQN)
    if len(all_trade_r) > 1:
        avg_r = sum(all_trade_r) / len(all_trade_r)
        std_dev_r = math.sqrt(sum((r - avg_r) ** 2 for r in all_trade_r) / len(all_trade_r))
        sqn = (avg_r * math.sqrt(len(all_trade_r))) / std_dev_r if std_dev_r > 0 else 0
    else:
        sqn = 0
    
    # Calculate time period performance averages
    # Day of week performance
    day_of_week_avg = {}
    for day, results in day_of_week_performance.items():
        if results:
            day_of_week_avg[day] = sum(results) / len(results)
        else:
            day_of_week_avg[day] = 0
            
    # Week of month performance
    week_of_month_avg = {}
    for week_num, results in week_of_month_performance.items():
        if results:
            week_name = f"Week {week_num}"
            week_of_month_avg[week_name] = sum(results) / len(results)
    
    # Month performance
    month_avg = {}
    month_names = {
        1: 'January', 2: 'February', 3: 'March', 4: 'April', 
        5: 'May', 6: 'June', 7: 'July', 8: 'August', 
        9: 'September', 10: 'October', 11: 'November', 12: 'December'
    }
    for month_num, results in month_performance.items():
        if results:
            month_name = month_names[month_num]
            month_avg[month_name] = sum(results) / len(results)
    
    # Compile results
    results = {
        'overall': {
            'total_trades': total_trades,
            'win_rate': overall_win_rate,
            'total_r': total_r,
            'profit_factor': profit_factor,
            'avg_win_r': avg_win_r,
            'avg_loss_r': avg_loss_r,
            'avg_risk_reward': avg_risk_reward,
            'net_pnl': net_pnl,
            'final_balance': current_balance,
            # New metrics
            'max_drawdown_pct': max_drawdown_pct,
            'max_drawdown_amount': max_drawdown_amount,
            'expectancy': expectancy,
            'max_win_streak': max_win_streak,
            'max_loss_streak': max_loss_streak,
            'sharpe_ratio': sharpe_ratio,
            'sqn': sqn,
            'day_of_week_performance': day_of_week_avg,
            'week_of_month_performance': week_of_month_avg,
            'month_performance': month_avg
        },
        'daily': daily_results
    }
    
    return results
