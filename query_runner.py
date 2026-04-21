import sqlite3
import pandas as pd
from database import DB_PATH

def run_query(sql: str) -> tuple[pd.DataFrame | None, str | None]:
    '''
    Runs a SQL query on ipl.db and returns the results.
 
    Two possible outcomes:
      Success → (DataFrame, None)   — DataFrame has the results
      Failure → (None, error_msg)   — error_msg explains what went wrong
 
    The caller (app.py) checks which one it got and handles accordingly.
    '''
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query(sql, conn)
        conn.close()
        return df, None
 
    except Exception as e:
        return None, str(e)
    

if __name__ == '__main__':
    # Quick test run a few queries directly on the DB
    # This verifies ipl.db was built correctly by database.py
 
    test_queries = [
        ('All teams',
         "SELECT * FROM teams;"),
 
        ('Top 5 six hitters',
         "SELECT batter, COUNT(*) as sixes FROM deliveries WHERE batter_runs=6 GROUP BY batter ORDER BY sixes DESC LIMIT 5;"),
 
        ('Total matches per season',
         "SELECT season, COUNT(*) as matches FROM matches GROUP BY season ORDER BY season;"),
    ]
 
    for title, sql in test_queries:
        print(f"\n{'='*50}")
        print(f'Test: {title}')
        print(f'SQL : {sql}')
        df, err = run_query(sql)
        if err:
            print(f'ERROR: {err}')
        else:
            print(df.to_string(index=False))

