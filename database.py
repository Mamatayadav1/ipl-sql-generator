import sqlite3
import pandas as pd
import os

DB_PATH = 'ipl.db'
DATA_DIR = 'data'

def load_csv(filename):
    '''Helper to load a CSV from the data / folder.'''
    path = os.path.join(DATA_DIR, filename)
    df = pd.read_csv(path)
    print(f" Loaded {filename}: {df.shape[0]} rows, {df.shape[1]} cols")
    return df

def create_database():
    '''
    Read all the CSVs and loads them into ipl.db as SQLite tables.
    Safe to run multiple times - it replaces tables cleanly each time.
    '''
    if os.path.exists(DB_PATH):
        print(f' Database {DB_PATH} already exists. Skipping rebuild.')
        print(f'(Delete ipl.db manually if you want to rebuild it)')
        return
    print('Building IPL Database from CSVs...\n')

    conn = sqlite3.connect(DB_PATH)

    # 1. Teams
    # 16 IPL teams. team_id is the key everything else references.
    print('Loading Teams...')
    teams = load_csv(r'C:\Users\HP\Downloads\ipl-sql-generator\data\teams_data.csv')
    teams.to_sql('teams', conn, if_exists='replace', index = False)


    # 2. Team Aliases
    # Same team has had different names over the years
    # e.g. 'Delhi Daredevils' → 'Delhi Capitals'
    print('Loading team aliases...')
    aliases = load_csv(r'C:\Users\HP\Downloads\ipl-sql-generator\data\team_aliases.csv')
    aliases.to_sql('team_aliases', conn, if_exists="replace", index=False)


    # 3. Players
    # 772 players. Has bat_style, bowl_style, field_pos.
    # Note: deliveries table stores player NAMES not player_ids,
    # so joins will be done on player_name matching batter/bowler columns
    print('Loading players...')
    players = load_csv(r'C:\Users\HP\Downloads\ipl-sql-generator\data\players-data-updated.csv')
    # Rename for cleaner SQL queries
    players.rename(columns={'player_full_name': 'full_name'}, inplace=True)
    players.to_sql('players', conn, if_exists='replace', index=False)


    # 4. Matches
    # 1169 matches from 2008-2025.
    # team1, team2, toss_winner, match_winner are all team_ids (int)
    print('Loading matches...')
    matches = load_csv(r'C:\Users\HP\Downloads\ipl-sql-generator\data\ipl_matches_data.csv')
    matches.to_sql('matches', conn, if_exists='replace', index=False)


    # 5. Deliveries (Ball by Ball)
    # 278,205 rows — one per ball bowled.
    # This is the MAIN table for player stats:
    # runs scored, wickets, extras, sixes, dot balls etc.
    # batter and bowler are stored as player NAME strings (not IDs)
    print('Loading deliveries (this may take a few seconds)...')
    deliveries = load_csv(r'C:\Users\HP\Downloads\ipl-sql-generator\data\ball_by_ball_data.csv')
    deliveries.to_sql('deliveries', conn, if_exists='replace', index=False)

    conn.close()

    print('\n✅ Database built successfully!')
    print(f'   Saved as: {DB_PATH}')


def get_schema():
    '''
    Returns the DB schema as a clean string.
    This gets sent to the LLM so it knows what tables/columns exist.
    The more accurate this is, the better SQL the LLM generates.
    '''
    return '''
DATABASE: IPL Cricket Dataset (2008-2025), SQLite
 
TABLE: teams
  team_id    INTEGER  -- primary key
  team_name  TEXT     -- e.g. 'Mumbai Indians', 'Chennai Super Kings'
 
TABLE: team_aliases
  alias_id   INTEGER  -- primary key
  team_id    INTEGER  -- FK → teams.team_id
  alias_name TEXT     -- old names e.g. 'Delhi Daredevils', 'Deccan Chargers'
 
TABLE: players
  player_id  INTEGER  -- primary key
  player_name TEXT    -- short name (matches batter/bowler in deliveries)
  bat_style  TEXT     -- 'Right hand Bat' or 'Left hand Bat'
  bowl_style TEXT     -- e.g. 'Right arm Medium', 'Left arm Spin'
  field_pos  TEXT     -- 'Batsman', 'Bowler', 'All-Rounder', 'Wicket-Keeper'
  full_name  TEXT     -- full official name
 
TABLE: matches
  match_id        INTEGER  -- primary key
  season_id       INTEGER  -- numeric season ID
  season          TEXT     -- e.g. '2023', 'IPL 2024'
  match_date      TEXT     -- format: YYYY-MM-DD
  city            TEXT     -- e.g. 'Mumbai', 'Chennai', 'Kolkata'
  venue           TEXT     -- stadium name
  team1           INTEGER  -- FK → teams.team_id
  team2           INTEGER  -- FK → teams.team_id
  toss_winner     INTEGER  -- FK → teams.team_id
  toss_decision   TEXT     -- 'bat' or 'field'
  match_winner    INTEGER  -- FK → teams.team_id (NULL if no result)
  win_by_runs     REAL     -- runs margin (if batting team won)
  win_by_wickets  REAL     -- wickets margin (if chasing team won)
  player_of_match REAL     -- player_id of POTM
  result          TEXT     -- 'runs', 'wickets', 'no result', 'tie'
  event_name      TEXT     -- tournament name
  match_number    REAL     -- match number in season
 
TABLE: deliveries
  season_id    INTEGER  -- season number
  match_id     INTEGER  -- FK → matches.match_id
  batter       TEXT     -- batsman name (matches players.player_name)
  bowler       TEXT     -- bowler name  (matches players.player_name)
  non_striker  TEXT     -- non-striking batsman name
  team_batting INTEGER  -- FK → teams.team_id
  team_bowling INTEGER  -- FK → teams.team_id
  over_number  INTEGER  -- 0 to 19
  ball_number  INTEGER  -- ball within the over
  batter_runs  INTEGER  -- runs scored by batter on this ball (0-6)
  extras       INTEGER  -- extra runs on this ball
  total_runs   INTEGER  -- batter_runs + extras
  is_wicket    BOOLEAN  -- TRUE if a wicket fell on this ball
  is_wide_ball BOOLEAN
  is_no_ball   BOOLEAN
  is_leg_bye   BOOLEAN
  is_bye       BOOLEAN
  player_out   TEXT     -- name of dismissed batsman (NULL if no wicket)
  wicket_kind  TEXT     -- 'caught', 'bowled', 'lbw', 'run out' etc.
  fielders_involved TEXT
  innings      INTEGER  -- 1 or 2
  is_super_over BOOLEAN
 
USEFUL QUERY PATTERNS:
-- Total runs by a batter:
  SELECT batter, SUM(batter_runs) FROM deliveries GROUP BY batter ORDER BY 2 DESC
 
-- Wickets by a bowler (exclude run outs, which are not bowler's wicket):
  SELECT bowler, COUNT(*) FROM deliveries
  WHERE is_wicket=1 AND wicket_kind != 'run out'
  GROUP BY bowler ORDER BY 2 DESC
 
-- Match winner name (need JOIN with teams):
  SELECT m.match_id, t.team_name as winner
  FROM matches m JOIN teams t ON m.match_winner = t.team_id
 
-- Sixes hit:
  SELECT batter, COUNT(*) as sixes FROM deliveries
  WHERE batter_runs=6 GROUP BY batter ORDER BY 2 DESC
 
-- Economy rate of a bowler (runs per over, exclude wides/noballs from ball count):
  SELECT bowler,
    ROUND(SUM(total_runs)*6.0 / COUNT(*), 2) as economy
  FROM deliveries WHERE is_wide_ball=0 AND is_no_ball=0
  GROUP BY bowler HAVING COUNT(*) > 120
  ORDER BY economy
'''
 
 
if __name__ == "__main__":
    create_database()
 
    # Quick verification — print row counts
    print("\nVerifying tables...")
    conn = sqlite3.connect(DB_PATH)
    for table in ["teams", "team_aliases", "players", "matches", "deliveries"]:
        count = pd.read_sql(f"SELECT COUNT(*) as n FROM {table}", conn).iloc[0]["n"]
        print(f"  {table}: {count} rows")
    conn.close()
