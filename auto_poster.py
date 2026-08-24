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
    
    prompt = f"""You are a professional financial blogger.
Write a highly engaging, SEO-optimized blog post in English about: {topic}.
Include a catchy title, introduction, 3-4 main points with subheadings (##), and a conclusion.
Make sure the content is formatting in Markdown.
Important: The very first line of your response MUST be the exact title of the post, starting with 'Title: '. Do not use markdown formatting for the title line.
The rest of the response should be the body of the post.
"""

    response = client.models.generate_content(
        model='gemini-3.5-flash-lite',
        contents=prompt
    )
    
    text = response.text.strip()
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
