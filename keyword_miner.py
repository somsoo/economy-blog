import os
import requests
import json
import random
import xml.etree.ElementTree as ET
import google.generativeai as genai
import time

def generate_with_retry(prompt, is_json=False):
    api_keys_str = os.environ.get('GEMINI_API_KEY', '')
    if not api_keys_str:
        raise ValueError('GEMINI_API_KEY is not set.')
    API_KEYS = [k.strip() for k in api_keys_str.split(',') if k.strip()]
    MODELS = ['gemini-3.5-flash-lite', 'gemini-3.1-flash-lite']
    
    generation_config = {"response_mime_type": "application/json"} if is_json else None
    
    for key in API_KEYS:
        genai.configure(api_key=key)
        for model_name in MODELS:
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt, generation_config=generation_config)
                return response.text
            except Exception as e:
                time.sleep(2)
                continue
    raise Exception("Critical: All API keys and models exhausted in keyword_miner!")

def get_us_news_headlines():
    # Fetch Google News US Finance RSS
    url = "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=en-US&gl=US&ceid=US:en"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        root = ET.fromstring(response.content)
        headlines = [item.find('title').text for item in root.findall('.//item') if item.find('title') is not None]
        return headlines[:15]
    except Exception as e:
        print(f"Error fetching Google News: {e}")
        return ["Stock market hits record high", "Fed interest rate decision impacts crypto", "Tech stocks rally as AI spending grows"]

def get_golden_keyword_us():
    history_file = 'posted_history.txt'
    history = []
    if os.path.exists(history_file):
        with open(history_file, 'r', encoding='utf-8') as f:
            history = [line.strip().lower() for line in f if line.strip()]

    # STEP 1: Real-time News Seed
    headlines = get_us_news_headlines()
    
    # STEP 2: AI Seed Noun Extraction
    prompt = f"""
    Analyze the following US financial news headlines. Extract exactly 5 core seed noun phrases (2-4 words each) that are highly relevant to finance, crypto, or tech stocks right now.
    Only output JSON:
    {{
        "seeds": ["seed one", "seed two", "seed three", "seed four", "seed five"]
    }}
    
    [Headlines]:
    {chr(10).join(headlines)}
    """
    try:
        res = generate_with_retry(prompt, is_json=True)
        seeds = json.loads(res).get('seeds', [])
    except Exception as e:
        print(f"AI Seed extraction failed: {e}")
        seeds = ["crypto regulations", "AI stocks", "fed interest rate", "tech earnings", "dividend yield"]

    # STEP 3 & 4: Expansion and Filtering
    for seed in seeds:
        try:
            url = f"http://suggestqueries.google.com/complete/search?client=chrome&q={seed}"
            headers = {"User-Agent": "Mozilla/5.0"}
            res = requests.get(url, headers=headers, timeout=5)
            suggestions = json.loads(res.text)[1]
            
            # Find a suggestion not in history
            for long_tail in suggestions:
                long_tail = long_tail.lower()
                if long_tail not in history and len(long_tail.split()) >= 3:
                    # Update history
                    with open(history_file, 'a', encoding='utf-8') as f:
                        f.write(long_tail + '\n')
                    return long_tail
        except Exception as e:
            print(f"Autocomplete fetch failed for {seed}: {e}")
            continue
            
    # Fallback
    fallback = seeds[0] if seeds else "tech stocks 2024"
    if fallback not in history:
        with open(history_file, 'a', encoding='utf-8') as f:
            f.write(fallback + '\n')
    return fallback
