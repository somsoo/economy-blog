import os
import random
from datetime import datetime
from google import genai

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables.")

client = genai.Client(api_key=GEMINI_API_KEY)

def generate_post():
    topics = [
        "Cryptocurrency and Real World Assets (RWA)",
        "Dividend ETFs for long-term passive income",
        "AI and Tech Stocks: Next big opportunities",
        "Macroeconomics: Federal Reserve and interest rates impact on crypto",
        "Personal finance tips for high-income earners"
    ]
    topic = random.choice(topics)
    
        prompt = f"""Act as an expert Financial Analyst, SEO Marketer, and Blog Writer for a Finance & Crypto blog.
    
Write a highly engaging, long-form, SEO/AEO/GEO-optimized blog post in English about: {topic}.

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
            print(f'Successfully generated content using model: {model_name}')
            break
        except Exception as e:
            if '429' in str(e) or 'quota' in str(e).lower():
                print(f'Quota exceeded for model {model_name}. Trying next model...')
                continue
            else:
                print(f'Error with {model_name}: {e}')
                continue
                
    if not response:
        raise Exception('All models failed.')
    

    text = response.text.strip()
    
    # --- 2nd Pass: Review and Revise ---
    print("Evaluating draft...")
    eval_prompt = f"""You are a master Editor and SEO/AEO/GEO Specialist.
Review the following blog post draft:

Draft:
{text}

Evaluate the draft on three criteria (0-100 score each):
1. SEO (Search Engine Optimization): Keyword usage, headers, readability.
2. GEO (Generative Engine Optimization): Clear structured data, bullet points, concise facts for AI to parse.
3. AEO (Answer Engine Optimization): Direct answers to the user's implicit question.

If the total score is below 285/300, or if it can be significantly improved, completely REWRITE the draft to be perfectly optimized. 
CRITICAL: The very first line of your response MUST still be the exact title of the post, starting with 'Title: '. Do not use markdown formatting for the title line.
The rest of the response should be the heavily revised and optimized body of the post in standard Markdown format."""

    revised_response = None
    for model_name in models_to_try:
        try:
            revised_response = client.models.generate_content(model=model_name, contents=eval_prompt)
            print(f'Successfully revised content using model: {model_name}')
            break
        except Exception as e:
            continue
            
    if revised_response and revised_response.text.strip():
        text = revised_response.text.strip()

    lines = text.split('\n')
    title = "Finance Update"
    body = text
    
    if lines and lines[0].lower().startswith("title:"):
        title = lines[0][6:].strip().replace('"', "'")
        body = '\n'.join(lines[1:]).strip()
        
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
    
    frontmatter = f"""---
layout: post
title: "{title}"
date: {time_str}
categories: [Finance]
---

{body}
"""
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(frontmatter)

if __name__ == "__main__":
    title, body = generate_post()
    save_post(title, body)
