import os
import time
import random
import asyncio
import requests
import json
import re
import urllib.parse
import edge_tts
import google.generativeai as genai

# ==================== 1. 配置与环境变量 ====================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
NOTION_API_KEY = os.environ.get("NOTION_API_KEY")
GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY", "tukanggo/ai-video-pipeline") 
DATABASE_ID = "401e3e5446a9805ea91ddcbb6942de7a"

if not GEMINI_API_KEY:
    raise ValueError("❌ 错误：未检测到 GEMINI_API_KEY 环境变量，请在 Secrets 中配置。")

genai.configure(api_key=GEMINI_API_KEY)

# ==================== 2. 生成完全由 AI 自由创作的 7 幕装修短视频脚本 ====================
def generate_script_json():
    print("📌 正在让 Gemini 自由发散创作一期最新的马来西亚房屋装修/家居改造短视频脚本...")
    
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        generation_config={"response_mime_type": "application/json"}
    )
    
    prompt = f"""
    你是一位专业的马来西亚房屋装修（Home Improvement）与短视频内容专家。请自行构思并创作一期约 60 秒的爆款短视频脚本。
    
    【创作方向要求】
    - 聚焦于马来西亚真实住宅（如排屋、公寓、半独立式房屋等）常见的家居改造、空间痛点、收纳升级或美学装修。
    - 每次生成的主题和空间必须完全不同（例如：干湿分离厨房改造、阁楼书房、隐形门玄关、老房卫生间防水与微水泥翻新、儿童房多功能榻榻米等）。
    
    【节奏与结构要求 (Pacing)】
    必须严格按照 3 个阶段展开，共拆分为 7 个独立的幕（Scene 1 至 Scene 7）：
    - 阶段一 (0-15s / 第1-2幕)：老旧痛点与视觉反差
    - 阶段二 (15-45s / 第3-5幕)：匠心硬核施工与材质工艺
    - 阶段三 (45-60s / 第6-7幕)：全景焕新呈现与细节特写
    
    【输出格式要求】
    必须严格输出一个 JSON 对象，包含以下字段（必须包含 7 个 acts）：
    {{
      "title": "装修主题名称（包含吸引眼球的亮点）",
      "acts": [
        {{
          "act_number": "第一幕",
          "time": "00:00 - 00:07",
          "voiceover": "纯中文口播台词...",
          "sfx": "音效描述...",
          "image_prompt": "Detailed English image prompt for scene 1, photorealistic, 8k...",
          "video_prompt": "English video prompt..."
        }},
        {{
          "act_number": "第二幕",
          "time": "00:07 - 00:15",
          "voiceover": "纯中文口播台词...",
          "sfx": "音效描述...",
          "image_prompt": "Detailed English image prompt for scene 2, photorealistic, 8k...",
          "video_prompt": "English video prompt..."
        }},
        {{
          "act_number": "第三幕",
          "time": "00:15 - 00:25",
          "voiceover": "纯中文口播台词...",
          "sfx": "音效描述...",
          "image_prompt": "Detailed English image prompt for scene 3, photorealistic, 8k...",
          "video_prompt": "English video prompt..."
        }},
        {{
          "act_number": "第四幕",
          "time": "00:25 - 00:35",
          "voiceover": "纯中文口播台词...",
          "sfx": "音效描述...",
          "image_prompt": "Detailed English image prompt for scene 4, photorealistic, 8k...",
          "video_prompt": "English video prompt..."
        }},
        {{
          "act_number": "第五幕",
          "time": "00:35 - 00:45",
          "voiceover": "纯中文口播台词...",
          "sfx": "音效描述...",
          "image_prompt": "Detailed English image prompt for scene 5, photorealistic, 8k...",
          "video_prompt": "English video prompt..."
        }},
        {{
          "act_number": "第六幕",
          "time": "00:45 - 00:55",
          "voiceover": "纯中文口播台词...",
          "sfx": "音效描述...",
          "image_prompt": "Detailed English image prompt for scene 6, photorealistic, 8k...",
          "video_prompt": "English video prompt..."
        }},
        {{
          "act_number": "第七幕",
          "time": "00:55 - 01:00",
          "voiceover": "纯中文口播台词...",
          "sfx": "音效描述...",
          "image_prompt": "Detailed English image prompt for scene 7, photorealistic, 8k...",
          "video_prompt": "English video prompt..."
        }}
      ]
    }}
    """
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)
            data = json.loads(response.text)
            
            markdown_script = f"# {data['title']}\n\n"
            for act in data['acts']:
                markdown_script += f"📌 **{act['act_number']}**\n"
                markdown_script += f"⏱️ **时间轴**: {act['time']}\n"
                markdown_script += f"🎙️ **口播旁白 (Voiceover)**: {act['voiceover']}\n"
                markdown_script += f"🎵 **音效 (SFX)**: {act['sfx']}\n"
                markdown_script += f"🖼️ **第一步：生图提示词**: > {act['image_prompt']}\n"
                markdown_script += f"🎥 **第二步：生视频提示词**: > {act['video_prompt']}\n\n---\n\n"
            
            prompts = [act['image_prompt'] for act in data['acts']]
            
            return data['title'], markdown_script, prompts
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"⚠️ 自由创作 JSON 脚本出错 ({e})，正在重试（等待 5 秒）...")
                time.sleep(5)
            else:
                raise e

# ==================== 3. 提取纯旁白 ====================
def extract_voiceovers(script_text):
    print("🔍 正在从脚本中精准提取纯口播旁白...")
    voiceovers = re.findall(r'🎙️\s*\*\*口播旁白.*?[:：]\*\*\s*(.+?)(?=\n[🎵🖼️🎥📌]|\Z)', script_text, re.DOTALL)
    if voiceovers:
        return " ".join([v.strip() for v in voiceovers])
    
    chinese_chars = "".join(re.findall(r'[\u4e00-\u9fa5，。！？、：；“”‘’]', script_text))
    return chinese_chars[:800] if len(chinese_chars) > 10 else script_text[:500]

# ==================== 4. 串行防流控渲染全部 7 张高清图 ====================
def generate_images_from_prompts(prompts):
    print(f"✨ 成功获取到 {len(prompts)} 个独立分镜 Prompt，开始依次渲染全部 7 张高清图（已启用防流控保护）...")
    
    generated_files = []
    for idx, prompt_text in enumerate(prompts, start=1):
        filename = f"scene_image_{idx}.jpg"
        
        hd_prompt = f"{prompt_text}, highly detailed, architectural interior photography, photorealistic, 8k resolution, cinematic lighting"
        
        print(f"🖼️ 正在渲染第 {idx}/7 幕高清图 ({filename})...")
        
        encoded_prompt = urllib.parse.quote(hd_prompt)
        image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1080&height=1920&nologo=true"
        
        success = False
        for attempt in range(1, 6):
            try:
                res = requests.get(image_url, timeout=60)
                if res.status_code == 200 and len(res.content) > 15000:
                    with open(filename, "wb") as f:
                        f.write(res.content)
                    print(f"   ✅ {filename} 渲染并保存成功 ({len(res.content) // 1024} KB)")
                    generated_files.append(filename)
                    success = True
                    break
                else:
                    print(f"   ⚠️ 第 {idx} 幕尝试 {attempt} 失败 (状态码: {res.status_code})，重试中...")
            except Exception as e:
                print(f"   ⚠️ 第 {idx} 幕尝试 {attempt} 异常 ({e})，重试中...")
            
            time.sleep(5 * attempt)
            
        if not success:
            print(f"   ❌ {filename} 连续重试后依然生成失败，使用首张图进行兜底对齐...")
            if os.path.exists("scene_image_1.jpg"):
                with open("scene_image_1.jpg", "rb") as src:
                    with open(filename, "wb") as dst:
                        dst.write(src.read())
                print(f"   🔄 已将 {filename} 通过备用图兜底。")
                generated_files.append(filename)
                
        time.sleep(4)
            
    return generated_files

# ==================== 5. Edge-TTS 语音合成 ====================
async def text_to_speech(text, output_filename="voiceover.mp3"):
    if not text or len(text.strip()) < 5:
        text = "欢迎来到本期马来西亚房屋改造分享，让我们一起打造高品质生活空间。"

    print(f"🔊 正在使用 Edge-TTS 合成语音 (有效字数: {len(text)})...")
    voice = "zh-CN-XiaoxiaoNeural"
    
    for attempt in range(3):
        try:
            safe_text = re.sub(r'[\r\n\t]', ' ', text)
            communicate = edge_tts.Communicate(safe_text, voice)
            await communicate.save(output_filename)
            
            if os.path.exists(output_filename) and os.path.getsize(output_filename) > 1024:
                print(f"✅ 语音合成成功: {output_filename}")
                return
        except Exception as e:
            print(f"⚠️ TTS 异常: {e}，重试中...")
        await asyncio.sleep(3)
        
    raise Exception("❌ 致命错误：Edge-TTS 无法生成有效的 MP3 文件。")

# ==================== 6. Notion 动态按幕多图排版同步（带防缓存时间戳） ====================
def split_text_into_chunks(text, max_length=1900):
    return [text[i:i + max_length] for i in range(0, len(text), max_length)]

def save_to_notion_with_all_media(topic_title, script_content, image_files):
    print("📤 正在将完整脚本、全部 7 张专属高清图与音频播放器同步写入 Notion...")
    
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    
    timestamp = int(time.time())
    audio_public_url = f"https://raw.githubusercontent.com/{GITHUB_REPOSITORY}/main/voiceover.mp3?v={timestamp}"
    
    script_chunks = split_text_into_chunks(script_content, max_length=1900)
    rich_text_array = [{"type": "text", "text": {"content": chunk}} for chunk in script_chunks]
    
    children_blocks = []
    
    for img in image_files:
        img_public_url = f"https://raw.githubusercontent.com/{GITHUB_REPOSITORY}/main/{img}?v={timestamp}"
        children_blocks.append({
            "object": "block",
            "type": "image",
            "image": {
                "type": "external",
                "external": {"url": img_public_url}
            }
        })
        
    children_blocks.append({
        "object": "block",
        "type": "audio",
        "audio": {
            "type": "external",
            "external": {"url": audio_public_url}
        }
    })
    
    payload = {
        "parent": {"database_id": DATABASE_ID},
        "properties": {
            "Name": {"title": [{"text": {"content": topic_title}}]},
            "Script": {"rich_text": rich_text_array}
        },
        "children": children_blocks
    }
    
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        print(f"🎉 Success: '{topic_title}' 及其 {len(image_files)} 张分幕专属高清图与音频已成功同步至 Notion！")
    else:
        print(f"❌ Error: 写入 Notion 失败 -> {response.text}")

# ==================== 主程序入口 ====================
if __name__ == "__main__":
    for f in os.listdir("."):
        if f.startswith("scene_image_") and f.endswith(".jpg"):
            try:
                os.remove(f)
            except:
                pass

    # 1. 动态生成 7 幕房屋装修创意脚本
    title, script, prompts = generate_script_json()
    
    # 2. 提取并合成旁白语音
    voiceover_text = extract_voiceovers(script)
    asyncio.run(text_to_speech(voiceover_text, "voiceover.mp3"))
    
    # 3. 渲染全部 7 张高清图
    image_files = generate_images_from_prompts(prompts)
    
    # 4. 同步写入 Notion
    save_to_notion_with_all_media(title, script, image_files)
