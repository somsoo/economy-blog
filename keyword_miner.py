import os
import requests
import json
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
    # Fetch from multiple Google News RSS feeds to ensure high volume and variety
    urls = [
        "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/headlines/section/topic/TECHNOLOGY?hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/headlines/section/topic/NATION?hl=en-US&gl=US&ceid=US:en"
    ]
    headers = {"User-Agent": "Mozilla/5.0"}
    all_headlines = []
    
    for url in urls:
        try:
            response = requests.get(url, headers=headers, timeout=10)
            root = ET.fromstring(response.content)
            headlines = [item.find('title').text for item in root.findall('.//item') if item.find('title') is not None]
            all_headlines.extend(headlines)
        except Exception as e:
            print(f"Error fetching Google News {url}: {e}")
            
    # Return up to 150 diverse headlines to prevent trivial topic selection
    return list(set(all_headlines))[:150]

def get_golden_keyword_us():
    history_file = 'posted_history.txt'
    history = []
    if os.path.exists(history_file):
        with open(history_file, 'r', encoding='utf-8') as f:
            history = [line.strip().lower() for line in f if line.strip()]

    headlines = get_us_news_headlines()
    if not headlines:
        headlines = ["Stock market hits record high", "AI investments soar globally"]

    prompt = f'''
    Here are the latest news headlines from the US (Business, Tech, Nation):
    {json.dumps(headlines)}
    
    Previous keywords we already wrote about (DO NOT reuse these or similar topics):
    {json.dumps(history[-30:])}
    
    As an expert Wall Street editor, review ALL these headlines and select exactly ONE overarching "Golden Keyword" (2-5 words) that is highly profitable, substantive, and deeply analytical (e.g., "AI Data Center Energy Crisis", "Federal Reserve Rate Cut Impact"). 
    ABSOLUTELY AVOID trivial news, daily quiz answers, or minor gossip. We need heavy, high-quality financial/tech analysis topics.
    
    Return ONLY a JSON object: {{"golden_keyword": "Your chosen keyword"}}
    '''
    
    try:
        res = generate_with_retry(prompt, is_json=True)
        data = json.loads(res)
        kw = data.get("golden_keyword", "Global Economic Trends")
        
        # Save to history
        with open(history_file, 'a', encoding='utf-8') as f:
            f.write(kw + "\\n")
        return kw
    except Exception as e:
        print(f"Error in golden keyword generation: {e}")
        return "Global Macroeconomic Outlook"

if __name__ == '__main__':
    print(get_golden_keyword_us())
