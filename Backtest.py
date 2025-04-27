import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import csv
import os
from datetime import datetime
from trade_analyzer import analyze_trades, parse_trade_data
from utils import save_data, load_data
import database as db

# Set page configuration
st.set_page_config(
    page_title="Trading Performance Analyzer",
    page_icon="📈",
    layout="wide"
)

# Initialize session state variables if they don't exist
if 'account_balance' not in st.session_state:
    st.session_state.account_balance = 25000.0
if 'risk_percentage' not in st.session_state:
    st.session_state.risk_percentage = 1.0
if 'trades_data' not in st.session_state:
    st.session_state.trades_data = []
if 'saved_files' not in st.session_state:
    # Check for existing CSV files in the current directory
    st.session_state.saved_files = [f for f in os.listdir('.') if f.endswith('.csv') and f.startswith('trades_')]

# Title and description
st.title("Trading Performance Analyzer")
st.markdown("""
This application helps you analyze your trading performance from a backtest. 
Input your trades with their respective R-multiples, and get insights into your performance metrics.
""")

# Initialize session state for database management
if 'current_session_id' not in st.session_state:
    st.session_state.current_session_id = None
if 'sessions_list' not in st.session_state:
    st.session_state.sessions_list = []
    
# Add tabs for different sections
tab1, tab2 = st.tabs(["Trade Analysis", "Database Management"])

# Sidebar for account settings and file operations
with st.sidebar:
    st.header("Account Settings")
    
    # Account balance and risk settings
    new_balance = st.number_input("Starting Account Balance ($)", 
                                min_value=1000.0, 
                                max_value=1000000.0, 
                                value=float(st.session_state.account_balance),
                                step=1000.0)
    
    new_risk = st.number_input("Risk Percentage (%)", 
                             min_value=0.1, 
                             max_value=10.0, 
                             value=float(st.session_state.risk_percentage),
                             step=0.1)
    
    # Update session state if settings changed
    if new_balance != st.session_state.account_balance or new_risk != st.session_state.risk_percentage:
        st.session_state.account_balance = new_balance
        st.session_state.risk_percentage = new_risk
        st.success(f"Updated: ${new_balance} account with {new_risk}% risk")
    
    # Calculate risk amount
    risk_amount = st.session_state.account_balance * (st.session_state.risk_percentage / 100)
    st.info(f"Risk per trade: ${risk_amount:.2f} (1R)")
    
    # File operations
    st.header("Save/Load Data")
    
    # Save current data
    if st.button("Save Current Data") and len(st.session_state.trades_data) > 0:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"trades_{timestamp}.csv"
        save_data(st.session_state.trades_data, filename)
        st.session_state.saved_files.append(filename)
        st.success(f"Data saved as {filename}")
    
    # Load existing data
    if st.session_state.saved_files:
        selected_file = st.selectbox("Select file to load:", st.session_state.saved_files)
        if st.button("Load Selected Data"):
            loaded_data = load_data(selected_file)
            if loaded_data:
                st.session_state.trades_data = loaded_data
                st.success(f"Loaded {len(loaded_data)} trading days from {selected_file}")
                st.rerun()
    else:
        st.info("No saved data files found")

# Trade Analysis Tab Content
with tab1:
    # Initialize session state for trading rules if not exists
    if 'trading_rules' not in st.session_state:
        st.session_state.trading_rules = []
        # If we have a current session, try to load rules from it
        if st.session_state.current_session_id:
            st.session_state.trading_rules = db.get_trading_rules(st.session_state.current_session_id)
    
    # Main content - now with 3 columns to include trading rules
    col1, col2, col3 = st.columns([2, 2, 1])
    
    # First column: Trading Rules Management
    with col1:
        st.header("Trading Rules")
        
        # Display existing rules with checkboxes
        existing_rules = st.session_state.trading_rules
        
        # Add new rule form
        with st.form(key="add_rule_form"):
            new_rule = st.text_area("Enter new trading rule:", 
                               placeholder="e.g., Only enter trades with a minimum 2:1 risk/reward ratio")
            rule_submitted = st.form_submit_button("Add Rule")
            
            if rule_submitted and new_rule:
                if new_rule not in existing_rules:
                    existing_rules.append(new_rule)
                    st.session_state.trading_rules = existing_rules
                    
                    # If we have a current session, update the rules
                    if st.session_state.current_session_id:
                        db.set_trading_rules(st.session_state.current_session_id, existing_rules)
                    
                    st.success("Trading rule added!")
                    st.rerun()
                else:
                    st.warning("This rule already exists.")
        
        # Display existing rules with delete buttons
        if existing_rules:
            st.subheader("Your Trading System Rules:")
            
            for i, rule in enumerate(existing_rules):
                col_rule, col_del = st.columns([5, 1])
                with col_rule:
                    st.write(f"{i+1}. {rule}")
                with col_del:
                    if st.button("🗑️", key=f"delete_rule_{i}"):
                        existing_rules.pop(i)
                        st.session_state.trading_rules = existing_rules
                        
                        # If we have a current session, update the rules
                        if st.session_state.current_session_id:
                            db.set_trading_rules(st.session_state.current_session_id, existing_rules)
                        
                        st.rerun()
        else:
            st.info("No trading rules defined yet. Add rules to make your trading more systematic.")
    
    # Second column: Add new trading day
    with col2:
        st.header("Add New Trading Day")
        
        # Input form for adding new trading day
        with st.form(key="add_day_form"):
            day_number = len(st.session_state.trades_data) + 1
            st.subheader(f"Day {day_number}")
            
            date = st.date_input("Date", value=datetime.now().date())
            trade_input = st.text_area(
                "Enter trades (e.g., W2R, L1R, BE):",
                help="Format: W[R-multiple], L[R-multiple], BE (Break Even). Example: W2R, L1R, BE, W1.5R"
            )
            
            # Add rules followed checkboxes
            rules_followed = []
            if st.session_state.trading_rules:
                st.subheader("Rules followed today:")
                for i, rule in enumerate(st.session_state.trading_rules):
                    checked = st.checkbox(rule, key=f"rule_check_{i}")
                    if checked:
                        rules_followed.append(i)
            
            submitted = st.form_submit_button("Add Trading Day")
            
            if submitted and trade_input:
                trades = parse_trade_data(trade_input)
                if trades:
                    # Create a day entry with date and trades
                    day_data = {
                        "day": day_number,
                        "date": date.strftime("%Y-%m-%d"),
                        "trades": trades,
                        "rules_followed": rules_followed
                    }
                    st.session_state.trades_data.append(day_data)
                    
                    # If we have a current session, add the day to the database
                    if st.session_state.current_session_id:
                        db.add_trading_day(
                            st.session_state.current_session_id,
                            day_number,
                            date.strftime("%Y-%m-%d"),
                            trades,
                            rules_followed
                        )
                    
                    st.success(f"Added {len(trades)} trades for Day {day_number}")
                    st.rerun()
                else:
                    st.error("Invalid trade format. Please use the format W2R, L1R, BE, etc.")
    
    # Third column: Current Trading Days 
    with col3:
        st.header("Current Trading Days")
        
        if st.session_state.trades_data:
            for idx, day in enumerate(st.session_state.trades_data):
                with st.expander(f"Day {day['day']} - {day['date']}"):
                    # Display the trades for this day
                    trade_strings = []
                    for trade in day['trades']:
                        if trade['type'] == 'BE':
                            trade_strings.append("BE")
                        else:
                            r_value = trade['r_multiple']
                            trade_strings.append(f"{trade['type']}{r_value}R")
                    
                    st.write(", ".join(trade_strings))
                    
                    # Display rules followed on this day if any
                    if 'rules_followed' in day and day['rules_followed'] and st.session_state.trading_rules:
                        st.markdown("##### Rules Followed:")
                        for rule_idx in day['rules_followed']:
                            if rule_idx < len(st.session_state.trading_rules):
                                st.markdown(f"✅ {st.session_state.trading_rules[rule_idx]}")
                    
                    # Add a button to remove this day
                    if st.button(f"Remove Day {day['day']}", key=f"remove_day_{idx}"):
                        st.session_state.trades_data.pop(idx)
                        # Renumber the remaining days
                        for i, d in enumerate(st.session_state.trades_data):
                            d['day'] = i + 1
                        st.success(f"Removed Day {day['day']}")
                        st.rerun()
        else:
            st.info("No trading days added yet. Use the form on the left to add your first trading day.")
    
    # Analysis section if we have data
    if st.session_state.trades_data:
        st.header("Performance Analysis")
        
        # Calculate analysis metrics
        risk_amount = st.session_state.account_balance * (st.session_state.risk_percentage / 100)
        analysis_results = analyze_trades(st.session_state.trades_data, 
                                         initial_balance=float(st.session_state.account_balance), 
                                         risk_amount=float(risk_amount))
        
        # Display overall metrics
        overall_metrics = analysis_results['overall']
        
        # First row of metrics - original metrics
        st.subheader("Core Metrics")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Win Rate", f"{overall_metrics['win_rate']:.2f}%")
        with col2:
            st.metric("Profit Factor", f"{overall_metrics['profit_factor']:.2f}")
        with col3:
            st.metric("Total R", f"{overall_metrics['total_r']:.2f}R")
        with col4:
            pnl_change = overall_metrics['net_pnl']
            st.metric("Net P&L", f"${overall_metrics['net_pnl']:.2f}", 
                     delta=f"{(pnl_change / st.session_state.account_balance) * 100:.2f}%")
        
        # Second row - Risk/Reward metrics
        st.subheader("Risk & Reward Metrics")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Avg Win (R)", f"{overall_metrics['avg_win_r']:.2f}R")
        with col2:
            st.metric("Avg Loss (R)", f"{overall_metrics['avg_loss_r']:.2f}R")
        with col3:
            st.metric("Risk/Reward Ratio", f"{overall_metrics['avg_risk_reward']:.2f}")
        with col4:
            st.metric("Expectancy", f"{overall_metrics['expectancy']:.2f}R")
        
        # Third row - Drawdown and streak metrics
        st.subheader("Drawdown & Streak Analysis")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Max Drawdown", f"{overall_metrics['max_drawdown_pct']:.2f}%")
        with col2:
            st.metric("Max Drawdown ($)", f"${overall_metrics['max_drawdown_amount']:.2f}")
        with col3:
            st.metric("Longest Win Streak", f"{overall_metrics['max_win_streak']}")
        with col4:
            st.metric("Longest Loss Streak", f"{overall_metrics['max_loss_streak']}")
        
        # Fourth row - System quality metrics
        st.subheader("System Quality Metrics")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Sharpe Ratio", f"{overall_metrics['sharpe_ratio']:.2f}")
        with col2:
            st.metric("System Quality Number (SQN)", f"{overall_metrics['sqn']:.2f}")
        with col3:
            # Format total trade count with info about win/loss
            wins = sum(day['wins'] for day in analysis_results['daily'])
            losses = sum(day['losses'] for day in analysis_results['daily'])
            breakeven = sum(day['breakeven'] for day in analysis_results['daily'])
            st.metric("Total Trades", f"{overall_metrics['total_trades']} ({wins}W/{losses}L/{breakeven}BE)")
        
        # Plot equity curve
        st.subheader("Account Equity Curve")
        
        equity_df = pd.DataFrame(analysis_results['daily'])
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=[f"Day {d['day']}" for d in analysis_results['daily']],
            y=[d['end_balance'] for d in analysis_results['daily']],
            mode='lines+markers',
            name='Account Balance',
            line=dict(color='green', width=2),
            marker=dict(size=8)
        ))
        
        # Add starting balance as Day 0
        fig.add_trace(go.Scatter(
            x=['Day 0'] + [f"Day {d['day']}" for d in analysis_results['daily']],
            y=[st.session_state.account_balance] + [d['end_balance'] for d in analysis_results['daily']],
            mode='lines',
            line=dict(color='rgba(0,128,0,0.2)', width=1),
            showlegend=False
        ))
        
        # Draw horizontal line at starting balance
        fig.add_shape(
            type="line",
            x0='Day 0',
            y0=st.session_state.account_balance,
            x1=f"Day {len(analysis_results['daily'])}",
            y1=st.session_state.account_balance,
            line=dict(color="red", width=1, dash="dash"),
        )
        
        fig.update_layout(
            title='Account Equity Progression',
            xaxis_title='Trading Day',
            yaxis_title='Account Balance ($)',
            yaxis_tickprefix='$',
            height=500,
            margin=dict(l=20, r=20, t=50, b=20),
            hovermode='x unified'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Daily metrics table
        st.subheader("Daily Performance")
        
        daily_data = []
        for day in analysis_results['daily']:
            daily_data.append({
                'Day': day['day'],
                'Date': day['date'],
                'Trades': day['num_trades'],
                'Win Rate': f"{day['win_rate']:.2f}%",
                'R-Multiple': f"{day['net_r']:.2f}R",
                'Daily P&L': f"${day['daily_pnl']:.2f}",
                'End Balance': f"${day['end_balance']:.2f}"
            })
        
        daily_df = pd.DataFrame(daily_data)
        st.dataframe(daily_df, use_container_width=True)
    
        # Trade distribution analysis
        st.subheader("Trade Distribution")
        
        # Collect all trades
        all_trades = []
        for day in st.session_state.trades_data:
            for trade in day['trades']:
                if trade['type'] != 'BE':  # Skip BE trades for R-multiple distribution
                    all_trades.append(trade)
        
        if all_trades:
            # R-multiple distribution
            r_values = [trade['r_multiple'] if trade['type'] == 'W' else -trade['r_multiple'] for trade in all_trades if trade['type'] != 'BE']
            
            fig = go.Figure()
            fig.add_trace(go.Histogram(
                x=r_values,
                marker_color=['green' if r > 0 else 'red' for r in r_values],
                nbinsx=20,
                name='R-Multiple Distribution'
            ))
            
            fig.update_layout(
                title='R-Multiple Distribution',
                xaxis_title='R-Multiple',
                yaxis_title='Frequency',
                height=400,
                margin=dict(l=20, r=20, t=50, b=20)
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Trade type distribution
            win_count = sum(1 for trade in all_trades if trade['type'] == 'W')
            loss_count = sum(1 for trade in all_trades if trade['type'] == 'L')
            be_count = sum(1 for day in st.session_state.trades_data 
                          for trade in day['trades'] 
                          if trade['type'] == 'BE')
            
            fig = go.Figure(data=[go.Pie(
                labels=['Wins', 'Losses', 'Break Even'],
                values=[win_count, loss_count, be_count],
                marker_colors=['green', 'red', 'gray'],
                hole=.3
            )])
            
            fig.update_layout(
                title='Trade Outcome Distribution',
                height=400,
                margin=dict(l=20, r=20, t=50, b=20)
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Day of week performance chart
            st.subheader("Day of Week Performance")
            
            day_performance = overall_metrics['day_of_week_performance']
            days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
            
            # Filter out days with no data
            days_with_data = [day for day in days if day in day_performance and day_performance[day] != 0]
            
            if days_with_data:
                day_r_values = [day_performance.get(day, 0) for day in days_with_data]
                
                # Create the bar chart
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=days_with_data,
                    y=day_r_values,
                    marker_color=['green' if val > 0 else 'red' for val in day_r_values],
                    text=[f"{val:.2f}R" for val in day_r_values],
                    textposition='auto'
                ))
                
                fig.update_layout(
                    title='Average R-Multiple by Day of Week',
                    xaxis_title='Day of Week',
                    yaxis_title='Average R-Multiple',
                    height=400,
                    margin=dict(l=20, r=20, t=50, b=20)
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Show day of week metrics in a table
                day_performance_df = pd.DataFrame([
                    {'Day': day, 'Average R': f"{day_performance.get(day, 0):.2f}R"} 
                    for day in days if day in day_performance
                ])
                st.dataframe(day_performance_df, use_container_width=True)
                
                # Highlight the best and worst trading days
                if days_with_data:
                    best_day = max(days_with_data, key=lambda day: day_performance.get(day, 0))
                    worst_day = min(days_with_data, key=lambda day: day_performance.get(day, 0))
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.info(f"**Best day**: {best_day} ({day_performance[best_day]:.2f}R)")
                    with col2:
                        st.info(f"**Worst day**: {worst_day} ({day_performance[worst_day]:.2f}R)")
            else:
                st.info("Not enough data to analyze day of week performance.")
                
            # Trading Rules Adherence Analysis
            if st.session_state.trading_rules:
                st.subheader("Trading Rules Adherence Analysis")
                
                # Calculate rule adherence for each day
                rules_adherence = []
                rules_impact = {rule_idx: {'followed': {'wins': 0, 'losses': 0, 'r_total': 0, 'count': 0}, 
                                        'not_followed': {'wins': 0, 'losses': 0, 'r_total': 0, 'count': 0}}
                               for rule_idx in range(len(st.session_state.trading_rules))}
                
                days_with_rules = 0
                for day_idx, day in enumerate(st.session_state.trades_data):
                    if 'rules_followed' in day and day['rules_followed']:
                        days_with_rules += 1
                        # Calculate percentage of rules followed
                        adherence_pct = len(day['rules_followed']) / len(st.session_state.trading_rules) * 100
                        
                        # Get daily results
                        day_analysis = analysis_results['daily'][day_idx]
                        day_r = day_analysis['net_r']
                        day_wins = day_analysis['wins']
                        day_losses = day_analysis['losses']
                        
                        # Add to rules_adherence
                        rules_adherence.append({
                            'Day': day['day'],
                            'Date': day['date'],
                            'Rules Followed': len(day['rules_followed']),
                            'Total Rules': len(st.session_state.trading_rules),
                            'Adherence %': adherence_pct,
                            'Net R': day_r
                        })
                        
                        # Update impact of each rule
                        for rule_idx in range(len(st.session_state.trading_rules)):
                            if rule_idx in day['rules_followed']:
                                # Rule was followed this day
                                rules_impact[rule_idx]['followed']['r_total'] += day_r
                                rules_impact[rule_idx]['followed']['wins'] += day_wins
                                rules_impact[rule_idx]['followed']['losses'] += day_losses
                                rules_impact[rule_idx]['followed']['count'] += 1
                            else:
                                # Rule was not followed this day
                                rules_impact[rule_idx]['not_followed']['r_total'] += day_r
                                rules_impact[rule_idx]['not_followed']['wins'] += day_wins
                                rules_impact[rule_idx]['not_followed']['losses'] += day_losses
                                rules_impact[rule_idx]['not_followed']['count'] += 1
                
                if days_with_rules > 0:
                    # Show adherence table
                    adherence_df = pd.DataFrame(rules_adherence)
                    if not adherence_df.empty:
                        st.write("Daily Rules Adherence:")
                        st.dataframe(adherence_df, use_container_width=True)
                    
                    # Display correlation between rule adherence and performance
                    if len(rules_adherence) > 1:  # Need at least 2 points for correlation
                        try:
                            correlation = np.corrcoef(
                                [day['Adherence %'] for day in rules_adherence],
                                [day['Net R'] for day in rules_adherence]
                            )[0, 1]
                            
                            # Interpret correlation
                            if abs(correlation) < 0.2:
                                corr_str = "very weak"
                            elif abs(correlation) < 0.4:
                                corr_str = "weak"
                            elif abs(correlation) < 0.6:
                                corr_str = "moderate"
                            elif abs(correlation) < 0.8:
                                corr_str = "strong"
                            else:
                                corr_str = "very strong"
                                
                            direction = "positive" if correlation > 0 else "negative"
                            
                            if correlation > 0:
                                st.success(f"There is a {corr_str} {direction} correlation ({correlation:.2f}) between rule adherence and performance.")
                                if correlation > 0.4:
                                    st.success("👍 Following your trading rules is associated with better performance!")
                            else:
                                st.warning(f"There is a {corr_str} {direction} correlation ({correlation:.2f}) between rule adherence and performance.")
                                if correlation < -0.4:
                                    st.warning("⚠️ You might need to revise your trading rules as they appear to be negatively correlated with performance.")
                        except:
                            st.info("Could not calculate correlation between rule adherence and performance.")
                    
                    # Show impact of individual rules
                    st.subheader("Impact of Individual Trading Rules")
                    
                    rule_impact_data = []
                    for rule_idx, impact in rules_impact.items():
                        if rule_idx < len(st.session_state.trading_rules):
                            rule_text = st.session_state.trading_rules[rule_idx]
                            
                            # Calculate average R when followed vs not followed
                            avg_r_followed = impact['followed']['r_total'] / impact['followed']['count'] if impact['followed']['count'] > 0 else 0
                            avg_r_not_followed = impact['not_followed']['r_total'] / impact['not_followed']['count'] if impact['not_followed']['count'] > 0 else 0
                            
                            # Calculate win rate when followed vs not followed
                            win_rate_followed = (impact['followed']['wins'] / (impact['followed']['wins'] + impact['followed']['losses'])) * 100 if (impact['followed']['wins'] + impact['followed']['losses']) > 0 else 0
                            win_rate_not_followed = (impact['not_followed']['wins'] / (impact['not_followed']['wins'] + impact['not_followed']['losses'])) * 100 if (impact['not_followed']['wins'] + impact['not_followed']['losses']) > 0 else 0
                            
                            rule_impact_data.append({
                                'Rule': f"{rule_idx+1}. {rule_text[:50]}{'...' if len(rule_text) > 50 else ''}",
                                'Days Followed': impact['followed']['count'],
                                'Days Not Followed': impact['not_followed']['count'],
                                'Avg R (Followed)': f"{avg_r_followed:.2f}R",
                                'Avg R (Not Followed)': f"{avg_r_not_followed:.2f}R",
                                'Win Rate (Followed)': f"{win_rate_followed:.1f}%",
                                'Win Rate (Not Followed)': f"{win_rate_not_followed:.1f}%",
                                'R Difference': avg_r_followed - avg_r_not_followed
                            })
                    
                    if rule_impact_data:
                        # Sort by R difference (most positive impact first)
                        rule_impact_data.sort(key=lambda x: x['R Difference'], reverse=True)
                        
                        # Convert to DataFrame and display
                        impact_df = pd.DataFrame(rule_impact_data)
                        st.dataframe(impact_df, use_container_width=True)
                        
                        # Highlight most impactful rules
                        if len(rule_impact_data) > 0:
                            most_positive = rule_impact_data[0]
                            if most_positive['R Difference'] > 0:
                                st.success(f"💎 Most valuable rule: {most_positive['Rule']} " + 
                                          f"(+{most_positive['R Difference']:.2f}R improvement when followed)")
                            
                            # Find most negative if any
                            negative_rules = [r for r in rule_impact_data if r['R Difference'] < 0]
                            if negative_rules:
                                most_negative = min(negative_rules, key=lambda x: x['R Difference'])
                                st.warning(f"⚠️ Consider revising: {most_negative['Rule']} " + 
                                          f"({most_negative['R Difference']:.2f}R worse when followed)")
                else:
                    st.info("No trading days with rule data available. Add trading days and check which rules you followed to see analysis here.")

# Database Management Tab Content
with tab2:
    st.header("Database Management")
    
    # Fetch available sessions from the database at the start
    if not st.session_state.sessions_list:
        st.session_state.sessions_list = db.get_trading_sessions()
    
    # Create tabs for different database operations
    db_tab1, db_tab2, db_tab3 = st.tabs(["Create New Session", "Load Session", "Manage Sessions"])
    
    # Tab 1: Create New Session
    with db_tab1:
        st.subheader("Create New Trading Session")
        
        with st.form(key="create_session_form"):
            session_name = st.text_input("Session Name", 
                                         value=f"Trading Session {datetime.now().strftime('%Y-%m-%d')}")
            
            session_balance = st.number_input("Initial Account Balance ($)", 
                                          min_value=1000.0, 
                                          max_value=1000000.0, 
                                          value=float(st.session_state.account_balance),
                                          step=1000.0)
            
            session_risk = st.number_input("Risk Percentage (%)", 
                                       min_value=0.1, 
                                       max_value=10.0, 
                                       value=float(st.session_state.risk_percentage),
                                       step=0.1)
            
            session_notes = st.text_area("Notes (optional)", 
                                      placeholder="Add any additional notes about this trading session...")
            
            # Option to import trading rules
            import_rules = st.checkbox("Import existing trading rules", value=True)
            
            create_empty = st.checkbox("Create empty session", value=True)
            
            create_submitted = st.form_submit_button("Create Session")
            
            if create_submitted:
                # Use existing trading rules if requested
                trading_rules = st.session_state.trading_rules if import_rules else []
                
                # Create a new session in the database
                session_id = db.create_trading_session(
                    name=session_name,
                    initial_balance=float(session_balance),
                    risk_percentage=float(session_risk),
                    notes=session_notes,
                    trading_rules=trading_rules
                )
                
                if session_id:
                    st.success(f"Created new trading session: {session_name}")
                    
                    # If user wants to use current data, save it to the new session
                    if not create_empty and st.session_state.trades_data:
                        for day in st.session_state.trades_data:
                            db.add_trading_day(
                                session_id=session_id,
                                day_number=day['day'],
                                date=day['date'],
                                trades_data=day['trades']
                            )
                        st.success(f"Added {len(st.session_state.trades_data)} trading days to the new session")
                    
                    # Update session list
                    st.session_state.sessions_list = db.get_trading_sessions()
                    st.session_state.current_session_id = session_id
                    
                    st.rerun()
                else:
                    st.error("Failed to create new session")
    
    # Tab 2: Load Session
    with db_tab2:
        st.subheader("Load Trading Session")
        
        if st.session_state.sessions_list:
            # Create a selection dropdown for sessions
            session_options = {f"{s['name']} (Created: {s['created_at']})": s['id'] for s in st.session_state.sessions_list}
            selected_session_name = st.selectbox("Select a trading session to load:", 
                                             options=list(session_options.keys()))
            
            selected_session_id = session_options[selected_session_name]
            
            # Add a load button
            if st.button("Load Selected Session"):
                # Get session details
                session_details = db.get_session_details(selected_session_id)
                if session_details:
                    # Get all trading days for this session
                    session_days = db.get_trading_days(selected_session_id)
                    
                    # Load trading rules if they exist
                    if 'trading_rules' in session_details and session_details['trading_rules']:
                        st.session_state.trading_rules = session_details['trading_rules']
                    else:
                        st.session_state.trading_rules = []
                        
                    if session_days:
                        # Update session state with loaded data
                        st.session_state.trades_data = session_days
                        st.session_state.account_balance = float(session_details['initial_balance'])
                        st.session_state.risk_percentage = float(session_details['risk_percentage'])
                        st.session_state.current_session_id = selected_session_id
                        
                        st.success(f"Loaded trading session: {session_details['name']} with {len(session_days)} trading days")
                        st.rerun()
                    else:
                        st.warning(f"Trading session {session_details['name']} has no trading days")
                else:
                    st.error("Failed to load session details")
        else:
            st.info("No trading sessions found in the database. Create a new session first.")
    
    # Tab 3: Manage Sessions
    with db_tab3:
        st.subheader("Manage Trading Sessions")
        
        if st.session_state.sessions_list:
            # Display all sessions in a table
            sessions_df = pd.DataFrame([
                {
                    'ID': s['id'],
                    'Name': s['name'],
                    'Created': s['created_at'],
                    'Initial Balance': f"${s['initial_balance']:.2f}",
                    'Risk %': f"{s['risk_percentage']:.1f}%"
                }
                for s in st.session_state.sessions_list
            ])
            
            st.dataframe(sessions_df, use_container_width=True)
            
            # Selected session to manage
            selected_id = st.selectbox("Select a session to manage:", 
                                    options=[s['id'] for s in st.session_state.sessions_list],
                                    format_func=lambda x: next((s['name'] for s in st.session_state.sessions_list if s['id'] == x), str(x)))
            
            # Get details for the selected session
            selected_details = next((s for s in st.session_state.sessions_list if s['id'] == selected_id), None)
            
            if selected_details:
                # Actions for the selected session
                action_col1, action_col2 = st.columns(2)
                
                with action_col1:
                    if st.button("Delete Session", key=f"delete_{selected_id}"):
                        if db.delete_trading_session(selected_id):
                            st.success(f"Deleted session: {selected_details['name']}")
                            
                            # If this was the current session, clear it
                            if st.session_state.current_session_id == selected_id:
                                st.session_state.current_session_id = None
                                
                            # Refresh the sessions list
                            st.session_state.sessions_list = db.get_trading_sessions()
                            st.rerun()
                        else:
                            st.error("Failed to delete session")
                
                with action_col2:
                    if st.button("Export to CSV", key=f"export_{selected_id}"):
                        # Generate a filename
                        export_filename = f"exported_{selected_details['name'].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.csv"
                        
                        if db.export_to_csv(selected_id, export_filename):
                            st.success(f"Exported session to {export_filename}")
                            
                            # Add to saved files list for potential import later
                            if export_filename not in st.session_state.saved_files:
                                st.session_state.saved_files.append(export_filename)
                        else:
                            st.error("Failed to export session")
                
                # Show session details
                st.subheader(f"Session Details: {selected_details['name']}")
                
                # Get trading days for this session
                session_days = db.get_trading_days(selected_id)
                
                if session_days:
                    st.write(f"Number of trading days: {len(session_days)}")
                    
                    # Option to view details
                    if st.checkbox("View trading days", key=f"view_days_{selected_id}"):
                        # Get trading rules for this session
                        session_rules = db.get_trading_rules(selected_id)
                        
                        for day in session_days:
                            with st.expander(f"Day {day['day_number']} - {day['date']}"):
                                # Display the trades for this day
                                trade_strings = []
                                for trade in day['trades']:
                                    if trade['type'] == 'BE':
                                        trade_strings.append("BE")
                                    else:
                                        r_value = trade['r_multiple']
                                        trade_strings.append(f"{trade['type']}{r_value}R")
                                
                                st.write(", ".join(trade_strings))
                                
                                # Display rules followed on this day if any
                                if 'rules_followed' in day and day['rules_followed'] and session_rules:
                                    st.markdown("##### Rules Followed:")
                                    for rule_idx in day['rules_followed']:
                                        if rule_idx < len(session_rules):
                                            st.markdown(f"✅ {session_rules[rule_idx]}")
                                        
                                    # Calculate adherence percentage
                                    if session_rules:
                                        adherence = len(day['rules_followed']) / len(session_rules) * 100
                                        st.progress(adherence / 100)
                                        st.caption(f"Rule Adherence: {adherence:.1f}%")
                else:
                    st.info(f"This session has no trading days.")
                    
                # Edit session details
                if st.checkbox("Edit session details", key=f"edit_{selected_id}"):
                    with st.form(key=f"edit_form_{selected_id}"):
                        edit_name = st.text_input("Session Name", value=selected_details['name'])
                        edit_balance = st.number_input("Initial Account Balance ($)", 
                                                   min_value=1000.0,
                                                   value=float(selected_details['initial_balance']))
                        edit_risk = st.number_input("Risk Percentage (%)", 
                                                min_value=0.1,
                                                value=float(selected_details['risk_percentage']))
                        edit_notes = st.text_area("Notes", value=selected_details['notes'] or "")
                        
                        # Get current trading rules for this session
                        current_rules = db.get_trading_rules(selected_id)
                        
                        # Display current rules with option to edit 
                        st.subheader("Trading Rules")
                        rule_text = ""
                        if current_rules:
                            rule_text = "\n".join(current_rules)
                        
                        edit_rules = st.text_area("Trading Rules (one per line)", 
                                              value=rule_text,
                                              height=150, 
                                              help="Enter one rule per line. These rules will appear as checkboxes when adding trading days.")
                        
                        update_submitted = st.form_submit_button("Update Session")
                        
                        if update_submitted:
                            # Parse rules from text area (split by newlines and filter empty lines)
                            new_rules = [rule.strip() for rule in edit_rules.split('\n') if rule.strip()]
                            
                            if db.update_trading_session(
                                session_id=selected_id,
                                name=edit_name,
                                initial_balance=float(edit_balance),
                                risk_percentage=float(edit_risk),
                                notes=edit_notes,
                                trading_rules=new_rules
                            ):
                                st.success("Session details updated successfully")
                                
                                # Refresh the sessions list
                                st.session_state.sessions_list = db.get_trading_sessions()
                                
                                # If this is the current session, update account settings
                                if st.session_state.current_session_id == selected_id:
                                    st.session_state.account_balance = float(edit_balance)
                                    st.session_state.risk_percentage = float(edit_risk)
                                
                                st.rerun()
                            else:
                                st.error("Failed to update session details")
        else:
            st.info("No trading sessions found in the database. Create a new session first.")
