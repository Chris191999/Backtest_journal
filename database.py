import sqlite3
import os
import json
from datetime import datetime

# Database file path
DB_PATH = 'trading_data.db'

def init_db():
    """
    Initialize the database by creating necessary tables if they don't exist.
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # First, create basic tables if they don't exist
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS trading_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            initial_balance REAL NOT NULL,
            risk_percentage REAL NOT NULL,
            notes TEXT
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS trading_days (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            day_number INTEGER NOT NULL,
            date TEXT NOT NULL,
            trades_data TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES trading_sessions (id) ON DELETE CASCADE
        )
        ''')
        
        # Now check if we need to add the new columns
        try:
            # Check for trading_rules column
            cursor.execute("PRAGMA table_info(trading_sessions)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'trading_rules' not in columns:
                print("Adding trading_rules column to trading_sessions table")
                cursor.execute("ALTER TABLE trading_sessions ADD COLUMN trading_rules TEXT")
            
            # Check for rules_followed column
            cursor.execute("PRAGMA table_info(trading_days)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'rules_followed' not in columns:
                print("Adding rules_followed column to trading_days table")
                cursor.execute("ALTER TABLE trading_days ADD COLUMN rules_followed TEXT")
        except Exception as alter_e:
            print(f"Error updating table schema: {alter_e}")
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Database initialization error: {e}")
        return False

def create_trading_session(name, initial_balance, risk_percentage, notes=None, trading_rules=None):
    """
    Create a new trading session (backtest).
    
    Args:
        name (str): Name of the trading session
        initial_balance (float): Initial account balance
        risk_percentage (float): Risk percentage per trade
        notes (str, optional): Additional notes
        trading_rules (list, optional): List of trading rules
        
    Returns:
        int: ID of the created session, or None if failed
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Convert trading rules to JSON if provided
        rules_json = json.dumps(trading_rules) if trading_rules else None
        
        cursor.execute('''
        INSERT INTO trading_sessions (name, created_at, initial_balance, risk_percentage, notes, trading_rules)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (name, created_at, initial_balance, risk_percentage, notes, rules_json))
        
        session_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return session_id
    except Exception as e:
        print(f"Error creating trading session: {e}")
        return None

def add_trading_day(session_id, day_number, date, trades_data, rules_followed=None):
    """
    Add a trading day to an existing session.
    
    Args:
        session_id (int): ID of the trading session
        day_number (int): Day number in the trading session
        date (str): Date of the trading day
        trades_data (list): List of trade dictionaries
        rules_followed (list, optional): List of rules followed for this day
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Convert trades_data and rules_followed to JSON strings
        trades_json = json.dumps(trades_data)
        rules_json = json.dumps(rules_followed) if rules_followed else None
        
        cursor.execute('''
        INSERT INTO trading_days (session_id, day_number, date, trades_data, rules_followed)
        VALUES (?, ?, ?, ?, ?)
        ''', (session_id, day_number, date, trades_json, rules_json))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error adding trading day: {e}")
        return False

def get_trading_sessions():
    """
    Get all trading sessions.
    
    Returns:
        list: List of dictionaries containing session information
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT id, name, created_at, initial_balance, risk_percentage, notes
        FROM trading_sessions
        ORDER BY created_at DESC
        ''')
        
        sessions = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return sessions
    except Exception as e:
        print(f"Error getting trading sessions: {e}")
        return []

def get_trading_days(session_id):
    """
    Get all trading days for a specific session.
    
    Args:
        session_id (int): ID of the trading session
        
    Returns:
        list: List of dictionaries containing day information and trades
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT id, day_number, date, trades_data, rules_followed
        FROM trading_days
        WHERE session_id = ?
        ORDER BY day_number
        ''', (session_id,))
        
        days_raw = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        # Process the data to convert the JSON string back to a list
        days = []
        for day in days_raw:
            day['trades'] = json.loads(day['trades_data'])
            del day['trades_data']
            
            # Process rules_followed if present
            if day['rules_followed'] and day['rules_followed'] != 'null':
                day['rules_followed'] = json.loads(day['rules_followed'])
            else:
                day['rules_followed'] = []
                
            days.append(day)
        
        return days
    except Exception as e:
        print(f"Error getting trading days: {e}")
        return []

def get_session_details(session_id):
    """
    Get details of a specific trading session.
    
    Args:
        session_id (int): ID of the trading session
        
    Returns:
        dict: Dictionary containing session information
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT id, name, created_at, initial_balance, risk_percentage, notes, trading_rules
        FROM trading_sessions
        WHERE id = ?
        ''', (session_id,))
        
        session = dict(cursor.fetchone())
        
        # Convert trading rules from JSON if exists
        if session['trading_rules']:
            session['trading_rules'] = json.loads(session['trading_rules'])
        
        conn.close()
        
        return session
    except Exception as e:
        print(f"Error getting session details: {e}")
        return None

def delete_trading_session(session_id):
    """
    Delete a trading session and all its trading days.
    
    Args:
        session_id (int): ID of the trading session
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Delete the session (cascade will delete days)
        cursor.execute('''
        DELETE FROM trading_sessions
        WHERE id = ?
        ''', (session_id,))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error deleting trading session: {e}")
        return False

def update_trading_session(session_id, name=None, initial_balance=None, risk_percentage=None, notes=None, trading_rules=None):
    """
    Update details of a trading session.
    
    Args:
        session_id (int): ID of the trading session
        name (str, optional): New name for the session
        initial_balance (float, optional): New initial balance
        risk_percentage (float, optional): New risk percentage
        notes (str, optional): New notes
        trading_rules (list, optional): New trading rules
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get current values
        cursor.execute('''
        SELECT name, initial_balance, risk_percentage, notes, trading_rules
        FROM trading_sessions
        WHERE id = ?
        ''', (session_id,))
        
        current = cursor.fetchone()
        
        # Update with new values or keep current values
        new_name = name if name is not None else current[0]
        new_balance = initial_balance if initial_balance is not None else current[1]
        new_risk = risk_percentage if risk_percentage is not None else current[2]
        new_notes = notes if notes is not None else current[3]
        
        # Handle trading rules separately
        if trading_rules is not None:
            # Convert to JSON
            new_rules_json = json.dumps(trading_rules)
        else:
            new_rules_json = current[4]  # Keep current rules
        
        cursor.execute('''
        UPDATE trading_sessions
        SET name = ?, initial_balance = ?, risk_percentage = ?, notes = ?, trading_rules = ?
        WHERE id = ?
        ''', (new_name, new_balance, new_risk, new_notes, new_rules_json, session_id))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error updating trading session: {e}")
        return False

def import_from_csv(session_name, csv_file_path, initial_balance, risk_percentage, notes=None, trading_rules=None):
    """
    Import trading data from a CSV file into a new session.
    
    Args:
        session_name (str): Name for the new trading session
        csv_file_path (str): Path to CSV file
        initial_balance (float): Initial account balance
        risk_percentage (float): Risk percentage per trade
        notes (str, optional): Additional notes
        trading_rules (list, optional): List of trading rules
        
    Returns:
        int: ID of the created session, or None if failed
    """
    try:
        # Create a new session
        session_id = create_trading_session(session_name, initial_balance, risk_percentage, notes, trading_rules)
        
        if session_id is None:
            return None
            
        # Import from CSV using existing utils.py functionality
        from utils import load_data
        trades_data = load_data(csv_file_path)
        
        if not trades_data:
            return None
            
        # Add each trading day to the database
        for day_data in trades_data:
            # Check if this day has rules_followed data
            rules_followed = day_data.get('rules_followed', [])
            
            add_trading_day(
                session_id, 
                day_data['day'], 
                day_data['date'], 
                day_data['trades'],
                rules_followed
            )
        
        return session_id
    except Exception as e:
        print(f"Error importing from CSV: {e}")
        return None

def export_to_csv(session_id, file_path):
    """
    Export a trading session to a CSV file.
    
    Args:
        session_id (int): ID of the trading session
        file_path (str): Path to save the CSV file
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get session days
        days = get_trading_days(session_id)
        
        # Format days for the existing save_data function
        formatted_days = []
        for day in days:
            day_data = {
                'day': day['day_number'],
                'date': day['date'],
                'trades': day['trades']
            }
            
            # Include rules_followed if present
            if 'rules_followed' in day and day['rules_followed']:
                day_data['rules_followed'] = day['rules_followed']
                
            formatted_days.append(day_data)
        
        # Use existing utils.py functionality to save
        from utils import save_data
        return save_data(formatted_days, file_path)
    except Exception as e:
        print(f"Error exporting to CSV: {e}")
        return False

def get_trading_rules(session_id):
    """
    Get trading rules for a specific session.
    
    Args:
        session_id (int): ID of the trading session
        
    Returns:
        list: List of trading rules, or None if not found
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT trading_rules
        FROM trading_sessions
        WHERE id = ?
        ''', (session_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result and result['trading_rules']:
            return json.loads(result['trading_rules'])
        else:
            return []
    except Exception as e:
        print(f"Error getting trading rules: {e}")
        return []

def set_trading_rules(session_id, trading_rules):
    """
    Set trading rules for a session.
    
    Args:
        session_id (int): ID of the trading session
        trading_rules (list): List of trading rules
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        rules_json = json.dumps(trading_rules)
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
        UPDATE trading_sessions
        SET trading_rules = ?
        WHERE id = ?
        ''', (rules_json, session_id))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error setting trading rules: {e}")
        return False

def update_day_rules_followed(session_id, day_number, rules_followed):
    """
    Update the rules followed for a specific trading day.
    
    Args:
        session_id (int): ID of the trading session
        day_number (int): The day number to update
        rules_followed (list): List of rule indexes that were followed
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        rules_json = json.dumps(rules_followed)
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
        UPDATE trading_days
        SET rules_followed = ?
        WHERE session_id = ? AND day_number = ?
        ''', (rules_json, session_id, day_number))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error updating day rules followed: {e}")
        return False

# Initialize the database when this module is imported
init_db()