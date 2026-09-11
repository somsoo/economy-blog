import os
import requests
import json
import xml.etree.ElementTree as ET
import google.generativeai as genai
import time
import re

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
                if response.text and response.text.strip():
                    return response.text.strip()
            except Exception as e:
                time.sleep(1)
                continue
    raise Exception("Critical: All API keys and models exhausted in keyword_miner!")

def get_us_news_articles():
    """Google News RSS에서 최신 경제/기술 뉴스 기사의 제목, 설명, 출처 수집"""
    urls = [
        "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/headlines/section/topic/TECHNOLOGY?hl=en-US&gl=US&ceid=US:en"
    ]
    headers = {"User-Agent": "Mozilla/5.0"}
    articles = []
    
    for url in urls:
        try:
            response = requests.get(url, headers=headers, timeout=10)
            root = ET.fromstring(response.content)
            for item in root.findall('.//item'):
                title = item.find('title').text if item.find('title') is not None else ""
                desc = item.find('description').text if item.find('description') is not None else ""
                clean_desc = re.sub(r'<[^>]+>', ' ', desc).strip()
                pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ""
                
                if title:
                    articles.append({
                        "title": title,
                        "description": clean_desc,
                        "date": pub_date
                    })
        except Exception as e:
            print(f"Error fetching Google News {url}: {e}")
            
    return articles[:80]

def get_golden_keyword_and_source():
    """
    1) 뉴스 기사 수집
    2) 최고 수익성/분석 가치가 높은 골든 키워드 1개 도출
    3) 해당 키워드와 관련된 팩트 원문 텍스트(Grounding Context)를 함께 묶어 반환
    """
    history_file = 'posted_history.txt'
    history = []
    if os.path.exists(history_file):
        with open(history_file, 'r', encoding='utf-8') as f:
            history = [line.strip().lower() for line in f if line.strip()]

    articles = get_us_news_articles()
    if not articles:
        articles = [{"title": "Federal Reserve Monetary Policy Update 2026", "description": "Interest rates remain steady as market analysts assess macro liquidity and economic data.", "date": "2026"}]

    headlines = [a["title"] for a in articles]
    
    prompt = f"""
    Here are the latest US financial and tech news headlines:
    {json.dumps(headlines[:50])}
    
    Previously covered topics (DO NOT repeat):
    {json.dumps(history[-30:])}
    
    As an expert Wall Street editor, select exactly ONE overarching "Golden Keyword" (2-5 words) that provides deep macroeconomic or tech infrastructure analytical value (e.g. "AI Data Center Power Infrastructure", "Treasury Yield Curve Inversion").
    
    Return ONLY a JSON object: {{"golden_keyword": "Your chosen keyword"}}
    """
    
    try:
        res = generate_with_retry(prompt, is_json=True)
        data = json.loads(res)
        kw = data.get("golden_keyword", "Global Economic Trends")
    except Exception as e:
        print(f"Error in golden keyword generation: {e}")
        kw = "Federal Reserve Liquidity Outlook"

    # Save to history
    with open(history_file, 'a', encoding='utf-8') as f:
        f.write(kw + "\n")

    # 관련 기사들의 설명을 조합하여 Source Material 구성 (그라운딩 텍스트)
    kw_words = set(re.findall(r'\w+', kw.lower()))
    relevant_snippets = []
    for a in articles:
        article_words = set(re.findall(r'\w+', (a["title"] + " " + a["description"]).lower()))
        if kw_words.intersection(article_words) or len(relevant_snippets) < 3:
            snippet = f"- Headline: {a['title']}\n  Context: {a['description']} (Date: {a['date']})"
            relevant_snippets.append(snippet)
            if len(relevant_snippets) >= 5:
                break

    source_text = "\n\n".join(relevant_snippets)
    return kw, source_text

if __name__ == '__main__':
    kw, src = get_golden_keyword_and_source()
    print("Keyword:", kw)
    print("Source snippet length:", len(src))
