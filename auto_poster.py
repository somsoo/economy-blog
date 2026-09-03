import os
import json
import random
import time
import re
from datetime import datetime
import google.generativeai as genai

# Import keyword_miner
import keyword_miner

# Setup Gemini API
api_keys_str = os.environ.get('GEMINI_API_KEY', '')
if not api_keys_str:
    print('GEMINI_API_KEY is not set.')
    exit(1)
API_KEYS = [k.strip() for k in api_keys_str.split(',') if k.strip()]
models_to_use = ['gemini-3.5-flash-lite', 'gemini-3.1-flash-lite']
genai.configure(api_key=API_KEYS[0])

def generate_with_retry(prompt, is_json=False):
    for model_name in models_to_use:
        try:
            model = genai.GenerativeModel(model_name)
            config = genai.GenerationConfig(response_mime_type="application/json") if is_json else None
            response = model.generate_content(prompt, generation_config=config)
            if response.text:
                return response.text
        except Exception as e:
            print(f"Model {model_name} failed: {e}")
    raise Exception("Critical: All API models exhausted!")

def create_text_thumbnail(text, filename_prefix="thumb"):
    import urllib.request
    import os
    lines = text.strip().split('\n')
    lines = [line for line in lines if line.strip()][:3]
    img_width, img_height = 1200, 500
    background_color = (30, 45, 65) # Dark Navy Blue for economy
    text_color = (255, 255, 255)
    try:
        from PIL import Image, ImageDraw, ImageFont
        img = Image.new('RGB', (img_width, img_height), color=background_color)
        draw = ImageDraw.Draw(img)
        
        font_path = "NanumGothic-Bold.ttf"
        if not os.path.exists(font_path):
            try:
                urllib.request.urlretrieve("https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Bold.ttf", font_path)
            except:
                pass
                
        try:
            font = ImageFont.truetype(font_path, 80)
        except:
            font = ImageFont.load_default()
            
        draw.rectangle([30, 30, img_width-30, img_height-30], outline=(100, 150, 200), width=3)
        y_text = (img_height // 2) - (len(lines) * 50)
        for line in lines:
            line = line.strip()
            if not line: continue
            try:
                bbox = draw.textbbox((0, 0), line, font=font)
                width = bbox[2] - bbox[0]
                height = bbox[3] - bbox[1]
            except:
                width = len(line) * 20; height = 80
            draw.text(((img_width - width) / 2, y_text), line, font=font, fill=text_color)
            y_text += height + 40
            
        os.makedirs('assets/images', exist_ok=True)
        img_path = f'assets/images/{filename_prefix}.webp'
        img.save(img_path, 'WEBP', quality=85)
        return img_path
    except Exception as e:
        print(f"Thumbnail error: {e}")
        return ""

def generate_post(keyword):
    # Step 1: Profiling (English)
    profile_prompt = f"You are a Wall Street financial analyst. Briefly analyze the target audience for the topic '{keyword}' in 3 sentences."
    profiling = generate_with_retry(profile_prompt)
    
    # Step 2: Outline
    outline_prompt = f"Based on '{profiling}', create a blog post outline for '{keyword}' with 4 H2 headings. Output in Markdown."
    outline = generate_with_retry(outline_prompt)

    # Step 3: Draft
    draft_prompt = f"Write a 1500-word expert financial blog post on '{keyword}' based on this outline:\n{outline}\nRule: Write ENTIRELY in English. Use professional yet accessible tone."
    draft = generate_with_retry(draft_prompt)

    # Step 4: Critique
    critique_prompt = f"As a Senior SEO Expert, provide 3 brief actionable improvements for this draft to boost Google rankings:\n{draft}"
    critique = generate_with_retry(critique_prompt)

    # Step 5: Rewrite with Multiple Images
    rewrite_prompt = f"Rewrite the draft into a final 2000-word SEO-optimized post (English Only) using this critique:\n{critique}\nDraft:\n{draft}\n\nCRITICAL RULE: Insert the exact text '[VIBE_IMAGE_HERE]' immediately after EVERY H2 heading (##) to allow for image placement.\nDO NOT use markdown code blocks like `json."
    final_text = generate_with_retry(rewrite_prompt)
    final_text = re.sub(r'(?i)^(?:#+\s*)?H[23]:\s*', '', final_text, flags=re.MULTILINE)
    final_text = re.sub(r'^---.*?---\s*', '', final_text, flags=re.DOTALL)

    # Step 6: Metadata
    meta_prompt = f"Return a JSON object for this post:\n{{ 'title': 'Catchy SEO title for {keyword}', 'thumb_hook': '2-line short catchy text for thumbnail\\\nabout {keyword}', 'vibe_keywords': '1-2 words for pixabay image search (e.g. stock, finance)' }}"
    meta_json_str = generate_with_retry(meta_prompt, is_json=True)
    try:
        meta = json.loads(meta_json_str)
        title, thumb_hook, vibe_keywords = meta['title'], meta['thumb_hook'], meta['vibe_keywords']
    except:
        title, thumb_hook, vibe_keywords = f"{keyword} Analysis", f"{keyword}\nMarket Insights", "finance"

    image_urls = []
    try:
        import urllib.parse, requests
        url = f"https://pixabay.com/api/?key=57366919-c2774ae5199cc6a6cdb9a301d&q={urllib.parse.quote(vibe_keywords)}&image_type=photo&orientation=horizontal&per_page=10"
        r = requests.get(url, timeout=10)
        data = r.json()
        if data.get('hits'):
            image_urls = [hit.get('largeImageURL', hit.get('webformatURL')) for hit in data['hits']]
    except:
        pass

    def download_vibe_image(img_url, filename_prefix):
        if not img_url: return ""
        try:
            import requests, io
            from PIL import Image
            os.makedirs('assets/images', exist_ok=True)
            img_r = requests.get(img_url, timeout=10)
            image = Image.open(io.BytesIO(img_r.content))
            base_width = 800
            if image.size[0] > base_width:
                wpercent = (base_width / float(image.size[0]))
                hsize = int((float(image.size[1]) * float(wpercent)))
                image = image.resize((base_width, hsize), Image.Resampling.LANCZOS)
            img_path = f'assets/images/{filename_prefix}.webp'
            image.save(img_path, 'WEBP', quality=85)
            return img_path
        except:
            return ""

    parts = final_text.split('[VIBE_IMAGE_HERE]')
    processed_text = parts[0]
    img_idx = 0
    for part in parts[1:]:
        v_path = ""
        if img_idx < len(image_urls):
            v_path = download_vibe_image(image_urls[img_idx], f"vibe_{int(time.time())}_{img_idx}")
            img_idx += 1
        if v_path:
            processed_text += f"\n<br>\n![Finance Vibe]({{{{ '/' | append: '{v_path}' | relative_url }}}})\n<br>\n"
        processed_text += part

    ad_middle = '\n<div class="manual-ad-container" style="margin: 25px 0; text-align: center;">\n<ins class="adsbygoogle" style="display:block" data-ad-client="ca-pub-2228289204702106" data-ad-slot="5979106011" data-ad-format="auto" data-full-width-responsive="true"></ins>\n<script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script>\n</div>\n'
    ad_bottom = '\n<div class="manual-ad-container" style="margin: 25px 0; text-align: center;">\n<ins class="adsbygoogle" style="display:block" data-ad-client="ca-pub-2228289204702106" data-ad-slot="2231432699" data-ad-format="auto" data-full-width-responsive="true"></ins>\n<script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script>\n</div>\n'
    
    # insert ad middle randomly if possible
    paragraphs = processed_text.split('\n\n')
    if len(paragraphs) > 4:
        paragraphs.insert(len(paragraphs)//2, ad_middle)
    final_text = '\n\n'.join(paragraphs) + ad_bottom

    import time
    thumb_filename = f"thumb_{int(time.time())}"
    thumb_rel_path = create_text_thumbnail(thumb_hook, thumb_filename)

    return title, final_text, thumb_rel_path

def main():
    import datetime
    
    # FETCH REAL TIME KEYWORD
    print("Fetching golden keyword from Google News US...")
    try:
        keyword = keyword_miner.get_golden_keyword_us()
        if not keyword:
            keyword = "US Stock Market Trends"
    except Exception as e:
        print(f"Error fetching keyword: {e}")
        keyword = "US Stock Market Trends"
        
    print(f'Golden Keyword: {keyword}')
    
    title, post_content, thumb_path = generate_post(keyword)
    if post_content:
        date_str = datetime.datetime.now().strftime('%Y-%m-%d')
        safe_title = "".join(c if c.isalnum() else "-" for c in keyword.lower())
        safe_title = "-".join(filter(None, safe_title.split("-")))[:50]
        if not safe_title: safe_title = str(int(time.time()))
        
        filename = f'_posts/{date_str}-{safe_title}.md'
        os.makedirs('_posts', exist_ok=True)
        frontmatter = f"---\nlayout: post\ntitle: \"{title}\"\ndate: {date_str}\nimage: {thumb_path}\n---\n\n"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(frontmatter + post_content)
        print(f'Successfully generated {filename}')

if __name__ == '__main__':
    main()
