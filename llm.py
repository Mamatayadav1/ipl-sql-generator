import os
from dotenv import load_dotenv
from database import get_schema

# Loading .env file so GROQ_API_KEY is available
load_dotenv()

def build_prompt(user_question: str) -> str:
    schema = get_schema()
    return f'''You are an expert SQL assistant who specializes in cricket and IPL data.
 
You have access to an IPL SQLite database with the following schema:
 
{schema}
 
STRICT RULES — follow these exactly:
1. Return ONLY the raw SQL query. No explanation, no markdown, no code fences, no preamble.
2. Use only the tables and columns defined in the schema above.
3. For player stats (runs, wickets, sixes) always query the deliveries table.
4. When joining with teams table, use team_id as the join key.
5. When looking up a player, match on deliveries.batter or deliveries.bowler (these are name strings).
6. To filter by year, use the season column in matches table (e.g. season LIKE '%2024%').
7. Always add LIMIT 10 unless the question asks for a specific number or all records.
8. End every query with a semicolon.
9. If the question is ambiguous, make a reasonable cricket assumption.
 
User question: {user_question}
 
SQL query:'''
 
 
def clean_sql(raw: str) -> str:
    raw = raw.strip()
    if '```' in raw:
        lines = raw.split('\n')
        cleaned = [l for l in lines if not l.strip().startswith('```')]
        raw = '\n'.join(cleaned).strip()
    if ';' in raw:
        raw = raw[:raw.index(';') + 1]
    return raw.strip()
 
 
def generate_with_groq(prompt: str) -> str:
    from groq import Groq
    client = Groq(api_key=os.getenv('GROQ_API_KEY'))
    response = client.chat.completions.create(
        model='llama-3.3-70b-versatile',
        messages=[
            {'role': 'system', 'content': 'You are an expert SQL assistant. Return only raw SQL queries, nothing else.'},
            {'role': 'user', 'content': prompt}
        ],
        temperature=0.1,
        max_tokens=500,
    )
    return response.choices[0].message.content
 
 
def generate_with_ollama(prompt: str) -> str:
    import ollama
    response = ollama.chat(
        model='llama3.2:latest',
        messages=[{'role': 'user', 'content': prompt}]
    )
    return response['message']['content']
 
 
def generate_sql(user_question: str) -> tuple[str, str]:
    '''
    Returns (sql_query, source) where source is 'Groq' or 'Ollama'
    Tries Groq first, falls back to Ollama if no key or Groq fails.
    '''
    prompt = build_prompt(user_question)
    groq_key = os.getenv('GROQ_API_KEY')
 
    if groq_key:
        try:
            raw = generate_with_groq(prompt)
            return clean_sql(raw), 'Groq'
        except Exception as e:
            print(f'Groq failed: {e} — falling back to Ollama')

    try:
        raw = generate_with_ollama(prompt)
        return clean_sql(raw), 'Ollama'
    except Exception as e:
        raise RuntimeError(
            f'Both Groq and Ollama failed.\n'
            f'For Groq: Add GROQ_API_KEY to your .env file\n'
            f'For Ollama: Make sure Ollama app is running\n'
            f'Error: {e}'
        )
 
 
if __name__ == '__main__':
    test_questions = [
        'Who hit the most sixes in IPL history?',
        'Which team has won the most matches?',
        "What is Jasprit Bumrah\'s total wickets?",
    ]
 
    print('Testing LLM connection...\n')
 
    for q in test_questions:
        print(f'Question : {q}')
        sql, source = generate_sql(q)
        print(f'Source   : {source}')
        print(f'SQL      : {sql}')
        print('-' * 60)
