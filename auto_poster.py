import os
import random
import time
import json
import urllib.parse
from datetime import datetime
import google.generativeai as genai
import requests
import io
import re
try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    pass

# =================================================================
# 1. API & Failover Setup
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
# 2. Keyword & Image Logic
# =================================================================
from keyword_miner import get_golden_keyword_us

def create_text_thumbnail(text, filename_prefix):
    os.makedirs('assets/images', exist_ok=True)
    img_path = f'assets/images/{filename_prefix}.webp'
    
    img = Image.new('RGB', (800, 800), color=(245, 245, 245))
    draw = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/roboto/Roboto-Bold.ttf", 60)
    except:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf", 60)
        except:
            font = ImageFont.load_default()

    lines = text.split('\n')
    y_text = 300
    for line in lines:
        try:
            bbox = draw.textbbox((0, 0), line, font=font)
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
        except:
            width, height = 400, 60
        draw.text(((800 - width) / 2, y_text), line, font=font, fill=(50, 50, 50))
        y_text += height + 20
        
    img.save(img_path, 'WEBP', quality=90)
    return img_path

def download_vibe_image(prompt, filename_prefix):
    os.makedirs('assets/images', exist_ok=True)
    img_path = f'assets/images/{filename_prefix}.jpg'
    keywords = ','.join([p.strip().replace(' ', '') for p in prompt.split(',')])
    url = f"https://loremflickr.com/800/500/{keywords}/all"
    try:
        r = requests.get(url, timeout=10, allow_redirects=True)
        if r.status_code == 200:
            with open(img_path, 'wb') as f:
                f.write(r.content)
            return img_path
    except Exception as e:
        print(f"Vibe image failed: {e}")
    return ""

def generate_post():
    golden_keyword = get_golden_keyword_us()
    print(f"Selected Golden Keyword: {golden_keyword}")

    # [Pass 4: Thumbnail Catchphrase]
    thumb_prompt = f"""
Create a catchy 2-line hook for a blog thumbnail about: {golden_keyword}.
Rule: No fear-mongering, no extreme words. Professional, informational and clean tone.
Output strictly 2 lines in English.
Example format:
First Line
Second Line
"""
    try:
        thumb_text = generate_with_retry(thumb_prompt).strip().replace('"', '').replace("'", '')
    except:
        thumb_text = f"[{golden_keyword}]\nMust Know Financial Info"

    thumb_filename = f"thumb_{int(time.time())}"
    thumb_rel_path = create_text_thumbnail(thumb_text, thumb_filename)
    image_markdown = f"![{golden_keyword}]({{{{ '/' | append: '{thumb_rel_path}' | relative_url }}}})\n\n"

    # [Vibe Image Generation]
    vibe_prompt = f"""
Translate the following topic into 2 English keywords that represent a clean, aesthetic financial/business mood. Output ONLY the keywords separated by comma.
Topic: {golden_keyword}
"""
    try:
        vibe_keywords = generate_with_retry(vibe_prompt).strip()
    except:
        vibe_keywords = "finance,business"
        
    vibe_rel_path = download_vibe_image(vibe_keywords, f"vibe_{int(time.time())}")
    vibe_markdown = f"![Aesthetic Finance]({{{{ '/' | append: '{vibe_rel_path}' | relative_url }}}})" if vibe_rel_path else ""

    # [Pass 1: Write]
    draft_prompt = f"""Act as an expert Financial Analyst. Write a highly engaging, long-form, SEO-optimized blog post in English targeted at the following golden long-tail keyword: "{golden_keyword}".
- Length: 1500 words (deep financial analysis, statistics).
- Tone: Objective, factual data. No extreme or fear-mongering words.
- Use markdown headings (##, ###).
"""
    draft_content = generate_with_retry(draft_prompt).strip()

    # [Pass 2: Check]
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

    # [Pass 3: Revise]
    rewrite_prompt = f"""Act as a highly engaging Wall Street influencer and friendly finance blogger.
Revise the following [Draft] by strictly applying the [Expert Feedback] to create a flawless, SEO/AEO/GEO optimized final post in English (approx 2000 words).
Remove any robotic AI cliches ("In conclusion", "Hello everyone"). Write in a conversational, highly engaging, and slightly casual "human" tone.

[Expert Feedback]
{feedback_content}

[Draft]
{draft_content}

[Visual Formatting Rule]
1. Exactly once in the middle of the article, insert the following vibe image markdown at a natural breaking point:
{vibe_markdown}

Important: The very first line MUST be the exact title of the post, starting with 'Title: '. 
The rest should be standard Markdown format.
"""
    final_text = generate_with_retry(rewrite_prompt).strip()

    lines = final_text.split('\n')
    title = "Market Update"
    body_content = final_text
    
    if lines and lines[0].lower().startswith("title:"):
        title = lines[0][6:].strip().replace('"', "'")
        title = title.replace('Title:', '').strip()
        body_content = '\n'.join(lines[1:]).strip()
        
    body_content = re.sub(r'^---.*?---\s*', '', body_content, flags=re.DOTALL)
    body_content = re.sub(r'^\s*layout:.*?\n\s*', '', body_content, flags=re.DOTALL)

    # AdSense Setup (Economy Blog specific slots)
    ad_top = '''
<div class="manual-ad-container" style="margin: 25px 0; text-align: center;">
    <ins class="adsbygoogle"
         style="display:block"
         data-ad-client="ca-pub-2228289204702106"
         data-ad-slot="7975218548"
         data-ad-format="auto"
         data-full-width-responsive="true"></ins>
    <script>(adsbygoogle = window.adsbygoogle || []).push({});</script>
</div>'''
    ad_middle = '''
<div class="manual-ad-container" style="margin: 25px 0; text-align: center;">
    <ins class="adsbygoogle"
         style="display:block"
         data-ad-client="ca-pub-2228289204702106"
         data-ad-slot="4854231186"
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

    lines = body_content.split('\n')
    if len(lines) > 10:
        mid_idx = len(lines) // 2
        body_content = "\n".join(lines[:mid_idx]) + "\n\n" + ad_middle + "\n\n" + "\n".join(lines[mid_idx:])
        
    final_body = image_markdown + ad_top + "\n\n" + body_content + "\n\n" + ad_bottom
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
