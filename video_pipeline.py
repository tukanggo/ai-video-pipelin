import os
import time
import random
import asyncio
import requests
import json
import re
import edge_tts
from google import genai
from google.genai import types

# ==================== 1. 配置与环境变量 ====================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
NOTION_API_KEY = os.environ.get("NOTION_API_KEY")
GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY", "tukanggo/ai-video-pipeline") 
DATABASE_ID = "401e3e5446a9805ea91ddcbb6942de7a"

if not GEMINI_API_KEY:
    raise ValueError("❌ 错误：未检测到 GEMINI_API_KEY 环境变量，请在 Secrets 中配置。")

# 初始化官方 GenAI 客户端
client = genai.Client(api_key=GEMINI_API_KEY)

# ==================== 2. 动态生成 7 幕房屋装修创意脚本 ====================
def generate_script_json():
    print("📌 正在调用 Gemini (Nano Banana) 自由发散创作一期最新的马来西亚房屋装修/家居改造短视频脚本...")
    
    prompt = """
    你是一位专业的马来西亚房屋装修（Home Improvement）与短视频内容专家。请自行构思并创作一期约 60 秒的爆款短视频脚本。
    
    【创作方向要求】
    - 聚焦于马来西亚真实住宅（如排屋公寓等）常见的家居改造、空间痛点、收纳升级或美学装修。
    - 每次生成的主题和空间必须完全不同。
    
    【节奏与结构要求 (Pacing)】
    必须严格按照 3 个阶段展开，共拆分为 7 个独立的幕（Scene 1 至 Scene 7）：
    - 阶段一 (0-15s / 第1-2幕)：老旧痛点与视觉反差
    - 阶段二 (15-45s / 第3-5幕)：匠心硬核施工与材质工艺
    - 阶段三 (45-60s / 第6-7幕)：全景焕新呈现与细节特写
    
    【输出格式要求】
    必须严格输出一个 JSON 对象，包含以下字段（必须包含 7 个 acts）：
    {
      "title": "装修主题名称（包含吸引眼球的亮点）",
      "acts": [
        {
          "act_number": "第一幕",
          "time": "00:00 - 00:07",
          "voiceover": "纯中文口播台词...",
          "sfx": "音效描述...",
          "image_prompt": "Detailed English image prompt for scene 1, photorealistic, 8k...",
          "video_prompt": "English video prompt..."
        },
        {
          "act_number": "第二幕",
          "time": "00:07 - 00:15",
          "voiceover": "纯中文口播台词...",
          "sfx": "音效描述...",
          "image_prompt": "Detailed English image prompt for scene 2, photorealistic, 8k...",
          "video_prompt": "English video prompt..."
        },
        {
          "act_number": "第三幕",
          "time": "00:15 - 00:25",
          "voiceover": "纯中文口播台词...",
          "sfx": "音效描述...",
          "image_prompt": "Detailed English image prompt for scene 3, photorealistic, 8k...",
          "video_prompt": "English video prompt..."
        },
        {
          "act_number": "第四幕",
          "time": "00:25 - 00:35",
          "voiceover": "纯中文口播台词...",
          "sfx": "音效描述...",
          "image_prompt": "Detailed English image prompt for scene 4, photorealistic, 8k...",
          "video_prompt": "English video prompt..."
        },
        {
          "act_number": "第五幕",
          "time": "00:35 - 00:45",
          "voiceover": "纯中文口播台词...",
          "sfx": "音效描述...",
          "image_prompt": "Detailed English image prompt for scene 5, photorealistic, 8k...",
          "video_prompt": "English video prompt..."
        },
        {
          "act_number": "第六幕",
          "time": "00:45 - 00:55",
          "voiceover": "纯中文口播台词...",
          "sfx": "音效描述...",
          "image_prompt": "Detailed English image prompt for scene 6, photorealistic, 8k...",
          "video_prompt": "English video prompt..."
        },
        {
          "act_number": "第七幕",
          "time": "00:55 - 01:00",
          "voiceover": "纯中文口播台词...",
          "sfx": "音效描述...",
          "image_prompt": "Detailed English image prompt for scene 7, photorealistic, 8k...",
          "video_prompt": "English video prompt..."
        }
      ]
    }
    """
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                ),
            )
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
                print(f"⚠️ 生成 JSON 脚本出错 ({e})，正在重试（等待 5 秒）...")
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

# ==================== 4. 使用 Nano Banana 原生生图生成全部 7 张高清图 ====================
def generate_images_with_nanobanana(prompts):
    print(f"✨ 成功获取到 {len(prompts)} 个独立分镜 Prompt，开始使用 Nano Banana (Gemini Native Image) 依次渲染全部 7 张高清图...")
    
    generated_files = []
    for idx, prompt_text in enumerate(prompts, start=1):
        filename = f"scene_image_{idx}.jpg"
        hd_prompt = f"{prompt_text}, highly detailed, architectural interior photography, photorealistic, 8k resolution, cinematic lighting, vertical 9:16 aspect ratio"
        
        print(f"🖼️ 正在调用 Nano Banana 渲染第 {idx}/7 幕高清图 ({filename})...")
        
        success = False
        for attempt in range(1, 4):
            try:
                # 调用 Gemini 的原生生图能力
                result = client.models.generate_images(
                    model='gemini-2.5-flash',
                    prompt=hd_prompt,
                    config=types.GenerateImagesConfig(
                        number_of_images=1,
                        output_mime_type="image/jpeg",
                        aspect_ratio="9:16",
                    )
                )
                
                for generated_image in result.generated_images:
                    image_bytes = generated_image.image.image_bytes
                    with open(filename, "wb") as f:
                        f.write(image_bytes)
                    print(f"   ✅ {filename} 原生渲染并保存成功 ({len(image_bytes) // 1024} KB)")
                    generated_files.append(filename)
                    success = True
                    break
                
                if success:
                    break
            except Exception as e:
                print(f"   ⚠️ 第 {idx} 幕生图尝试 {attempt} 异常 ({e})，重试中...")
            
            time.sleep(5)
            
        if not success:
            print(f"   ❌ {filename} 生成失败，使用首张图进行兜底...")
            if os.path.exists("scene_image_1.jpg"):
                with open("scene_image_1.jpg", "rb") as src:
                    with open(filename, "wb") as dst:
                        dst.write(src.read())
                generated_files.append(filename)
                
        time.sleep(3)
            
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
        print(f"🎉 Success: '{topic_title}' 及其 {len(image_files)} 张原生分幕高清图与音频已成功同步至 Notion！")
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

    # 1. 动态生成 7 幕装修创意脚本
    title, script, prompts = generate_script_json()
    
    # 2. 提取并合成旁白语音
    voiceover_text = extract_voiceovers(script)
    asyncio.run(text_to_speech(voiceover_text, "voiceover.mp3"))
    
    # 3. 使用 Nano Banana 原生模型渲染全部 7 张高清图
    image_files = generate_images_with_nanobanana(prompts)
    
    # 4. 同步写入 Notion
    save_to_notion_with_all_media(title, script, image_files)
