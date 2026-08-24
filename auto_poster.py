import os
import random
from datetime import datetime
from google import genai
import requests
import xml.etree.ElementTree as ET

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables.")

client = genai.Client(api_key=GEMINI_API_KEY)

def get_trending_keywords():
    try:
        url = "https://trends.google.com/trends/trendingsearches/daily/rss?geo=US"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        root = ET.fromstring(response.content)
        keywords = [item.find('title').text for item in root.findall('.//item') if item.find('title') is not None]
        return ", ".join(keywords[:10])
    except Exception as e:
        print(f"Trend Fetch Error: {e}")
        return "Federal Reserve, AI Stocks, Crypto Regulations, Dividend Yield"

def generate_post():
    trends = get_trending_keywords()
    
    prompt = f"""Act as an expert Financial Analyst, SEO Marketer, and Blog Writer for a Finance & Crypto blog.
Select ONE of the following real-time US trending topics that best fits the finance/crypto niche:
[Current US Trends]: {trends}

Write a highly engaging, long-form, SEO/AEO/GEO-optimized blog post in English targeted at the selected keyword.

Requirements:
- Length: 1200 to 1500 words (Be extremely detailed, provide deep financial analysis, statistics, and actionable advice).
- Structure: Catchy Title, Engaging Introduction, well-structured headings (H2, H3), Bullet points, Conclusion.
- SEO/AEO/GEO: Naturally include the keyword in the title, intro, and headings. Optimize for Answer Engine Optimization (AEO) by answering direct questions clearly, and Geo-specific intent if applicable.
- Tone: You are a real person sharing insights and honest opinions. Conversational, highly engaging, and slightly casual "human" tone. NOT a robotic corporate analyst.
- Safety: Objective, factual data. No illegal financial advice.

Important: The very first line of your response MUST be the exact title of the post, starting with 'Title: '. Do not use markdown formatting for the title line.
The rest of the response should be the body of the post in standard Markdown format."""

    models_to_try = ['gemini-3.5-flash-lite', 'gemini-3.1-flash-lite']
    response = None
    for model_name in models_to_try:
        try:
            response = client.models.generate_content(model=model_name, contents=prompt)
            break
        except:
            continue
            
    if not response:
        raise Exception('All models failed.')
    
    text = response.text.strip()
    
    # --- 2nd Pass: Review and Revise ---
    eval_prompt = f"""You are a master Editor and SEO/AEO/GEO Specialist.
Review the following blog post draft:

Draft:
{text}

Evaluate the draft on three criteria (0-100 score each):
1. SEO: Keyword usage, headers, readability.
2. GEO: Clear structured data, bullet points, concise facts.
3. AEO: Direct answers to the user's implicit question.

If the total score is below 285/300, completely REWRITE the draft to be perfectly optimized. 
CRITICAL: The very first line of your response MUST still be the exact title of the post, starting with 'Title: '. Do not use markdown formatting for the title line.
The rest of the response should be the heavily revised and optimized body of the post in standard Markdown format."""

    revised_response = None
    for model_name in models_to_try:
        try:
            revised_response = client.models.generate_content(model=model_name, contents=eval_prompt)
            break
        except:
            continue
            
    if revised_response and revised_response.text.strip():
        text = revised_response.text.strip()

    lines = text.split('\n')
    title = "Finance Update"
    
    if lines and lines[0].lower().startswith("title:"):
        title = lines[0][6:].strip().replace('"', "'")
        body = '\n'.join(lines[1:]).strip()
    else:
        body = text
        
    return title, body

def save_post(title, body):
    now = datetime.utcnow()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%Y-%m-%d %H:%M:%S")
    slug = "".join(c if c.isalnum() else "-" for c in title.lower())
    slug = "-".join(filter(None, slug.split("-")))[:50]
    filename = f"{date_str}-{slug}.md"
    filepath = os.path.join('_posts', filename)
    os.makedirs('_posts', exist_ok=True)
    
    frontmatter = f"---\nlayout: post\ntitle: \"{title}\"\ndate: {time_str}\ncategories: [Finance]\n---\n\n{body}\n"
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(frontmatter)

if __name__ == "__main__":
    title, body = generate_post()
    save_post(title, body)
