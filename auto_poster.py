import os
import random
import time
import json
import urllib.parse
from datetime import datetime
import google.generativeai as genai
import requests
import xml.etree.ElementTree as ET
import io
try:
    from PIL import Image
except ImportError:
    pass

# =================================================================
# 1. API & Failover Setup (Dynamic Rotation)
# =================================================================
api_keys_str = os.environ.get('GEMINI_API_KEY', '')
if not api_keys_str:
    print('GEMINI_API_KEY is not set.')
    exit(1)

API_KEYS = [k.strip() for k in api_keys_str.split(',') if k.strip()]
MODELS = ['gemini-3.5-flash-lite', 'gemini-3.1-flash-lite']

def generate_with_retry(prompt, is_json=False):
    generation_config = {"response_mime_type": "application/json"} if is_json else None
    
    for key in API_KEYS:
        genai.configure(api_key=key)
        for model_name in MODELS:
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt, generation_config=generation_config)
                return response.text
            except Exception as e:
                print(f"Fallback triggered: Failed on {model_name} with key ...{key[-4:]} -> {e}")
                time.sleep(2)
                continue
                
    raise Exception("Critical: All API keys and models are exhausted!")

# =================================================================
# 2. Economy Fetch Logic (DO NOT MODIFY)
# =================================================================
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
    
    # [Pass 1: 글쓰기 (Write)]
    draft_prompt = f"""Act as an expert Financial Analyst. Select ONE of the following real-time US trending topics that best fits the finance/crypto niche:
[Current US Trends]: {trends}

Write a highly engaging, long-form, SEO-optimized blog post in English targeted at the selected keyword.
- Length: 1500 words (deep financial analysis, statistics).
- Tone: Objective, factual data.
"""
    draft_content = generate_with_retry(draft_prompt).strip()

    # [Pass 2: 검사 (Check)]
    check_prompt = f"""Review the following financial blog draft as a top-tier SEO, AEO (Answer Engine Optimization), and GEO (Generative Engine Optimization) expert targeting the US market.

[Draft]
{draft_content}

Critique the draft based on:
1. SEO: Are long-tail keywords naturally placed in headings and intro?
2. AEO: Are there clear, direct answers to common investor questions?
3. GEO: Is the content perfectly tailored for US retail investors?
Provide 5 actionable feedback points for improvement.
"""
    feedback_content = generate_with_retry(check_prompt).strip()

    # [Pass 3: 수정 (Revise)]
    rewrite_prompt = f"""Act as a highly engaging Wall Street influencer and friendly finance blogger.
Revise the following [Draft] by strictly applying the [Expert Feedback] to create a flawless, SEO/AEO/GEO optimized final post in English (approx 2000 words).
Remove any robotic AI cliches ("In conclusion", "Hello everyone"). Write in a conversational, highly engaging, and slightly casual "human" tone.

[Expert Feedback]
{feedback_content}

[Draft]
{draft_content}

Important: The very first line MUST be the exact title of the post, starting with 'Title: '. 
The rest should be standard Markdown format.
"""
    
    final_text = generate_with_retry(rewrite_prompt).strip()

    lines = final_text.split('\n')
    title = "Market Update"
    body_content = final_text
    
    if lines and lines[0].lower().startswith("title:"):
        title = lines[0][6:].strip().replace('"', "'")
        body_content = '\n'.join(lines[1:]).strip()

    # =================================================================
    # 3. Image Generation (Optimized for SEO - WebP Compression)
    # =================================================================
    # [Pass 4: 심플 프롬프트 기반 실사 상징물 이미지 기획]
    image_prompt_gen = f"""
    Based on the topic "{title}", choose ONE symbolic inanimate object (e.g. golden coin, spray bottle, dog toy) that visually represents the core topic.
    Do NOT include humans or complex landscapes. 
    Output JSON only:
    {{
        "object": "specific object name in English (e.g., golden coin, red rubber dog toy)"
    }}
    """
    try:
        img_response_text = generate_with_retry(image_prompt_gen, is_json=True)
        import json
        img_data = json.loads(img_response_text)
        obj_name = img_data.get('object', 'abstract object')
    except Exception as e:
        obj_name = 'simple object'

    final_img_prompt = f'A realistic photograph of a {obj_name} on a clean desk, bright natural lighting, simple and clear'
    encoded_prompt = urllib.parse.quote(final_img_prompt)

    os.makedirs('assets/images', exist_ok=True)
    file_date_str = datetime.now().strftime('%Y-%m-%d')
    file_time_str = datetime.now().strftime('%H-%M-%S')
    image_filename = f'{file_date_str}-{file_time_str}.webp'
    image_path = f'assets/images/{image_filename}'

    print('Requesting Pollinations Image...')
    time.sleep(5)
    img_url = f'https://image.pollinations.ai/prompt/{encoded_prompt}?width=800&height=800&nologo=true&private=true&model=flux'
    
    try:
        r = requests.get(img_url, timeout=120)
        if r.status_code == 200:
            img_raw = Image.open(io.BytesIO(r.content))
            if img_raw.mode in ("RGBA", "P"):
                img_raw = img_raw.convert("RGB")
            img_raw.thumbnail((800, 800), Image.Resampling.LANCZOS)
            img_raw.save(image_path, "WEBP", quality=80)
            
            markdown_image = f'\n\n![{title}](/{image_path})\n\n'
            # Insert image after first paragraph
            insert_pos = body_content.find('\n', 150)
            if insert_pos == -1:
                insert_pos = 150
            body_content = body_content[:insert_pos] + markdown_image + body_content[insert_pos:]
    except Exception as e:
        print(f'Image processing skipped due to error: {e}')

    # AdSense injection
    ad_top = '''
<div class="manual-ad-container" style="margin: 25px 0; text-align: center;">
    <ins class="adsbygoogle"
         style="display:block"
         data-ad-client="ca-pub-2228289204702106"
         data-ad-slot="2228067849"
         data-ad-format="auto"
         data-full-width-responsive="true"></ins>
    <script>(adsbygoogle = window.adsbygoogle || []).push({});</script>
</div>'''
    ad_middle = '''
<div class="manual-ad-container" style="margin: 35px 0; text-align: center;">
    <ins class="adsbygoogle"
         style="display:block"
         data-ad-client="ca-pub-2228289204702106"
         data-ad-slot="2228067849"
         data-ad-format="auto"
         data-full-width-responsive="true"></ins>
    <script>(adsbygoogle = window.adsbygoogle || []).push({});</script>
</div>'''
    ad_bottom = '''
<div class="manual-ad-container" style="margin: 35px 0 10px 0; text-align: center;">
    <ins class="adsbygoogle"
         style="display:block"
         data-ad-client="ca-pub-2228289204702106"
         data-ad-slot="2228067849"
         data-ad-format="auto"
         data-full-width-responsive="true"></ins>
    <script>(adsbygoogle = window.adsbygoogle || []).push({});</script>
</div>'''

    body_lines = body_content.split('\n')
    if len(body_lines) > 5:
        mid_idx = len(body_lines) // 2
        body_content = "\n".join(body_lines[:mid_idx]) + "\n" + ad_middle + "\n" + "\n".join(body_lines[mid_idx:])
        
    final_body = ad_top + "\n" + body_content + "\n" + ad_bottom
    return title, final_body


def save_post(title, body):
    now = datetime.utcnow()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%Y-%m-%d %H:%M:%S")
    slug = "".join(c if c.isalnum() else "-" for c in title.lower())
    slug = "-".join(filter(None, slug.split("-")))[:50]
    if not slug:
        slug = str(int(time.time()))
    filename = f"{date_str}-{slug}.md"
    filepath = os.path.join('_posts', filename)
    os.makedirs('_posts', exist_ok=True)
    
    frontmatter = f"---\nlayout: post\ntitle: \"{title}\"\ndate: {time_str}\ncategories: [Finance]\n---\n\n{body}\n"
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(frontmatter)

if __name__ == "__main__":
    title, body = generate_post()
    save_post(title, body)
