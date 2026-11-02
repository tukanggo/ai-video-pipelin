import os
import time
import random
import asyncio
import requests
import re
import urllib.parse
import edge_tts
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted

# ==================== 1. 配置与环境变量 ====================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
NOTION_API_KEY = os.environ.get("NOTION_API_KEY")
GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY", "tukanggo/ai-video-pipeline") 
DATABASE_ID = "401e3e5446a9805ea91ddcbb6942de7a"

if not GEMINI_API_KEY:
    raise ValueError("❌ 错误：未检测到 GEMINI_API_KEY 环境变量，请在 Secrets 中配置。")

genai.configure(api_key=GEMINI_API_KEY)

# ==================== 2. 设计主题素材库 ====================
DESIGN_TOPICS = [
    {
        "title": "马来西亚老旧公寓厨房改造 (Modern Japandi Kitchen)",
        "focus": "针对采光暗淡、收纳混乱的老旧厨房，打造现代禅意与 Japandi 日式原木风。",
        "craft": "展示微水泥涂墙、定制木作安装、隐藏式暖光 LED 灯带铺设。"
    },
    {
        "title": "狭长型客厅与电视墙改造 (Minimalist Warm Living Room)",
        "focus": "针对传统排屋客厅空间压抑、采光不足、杂物暴露的痛点。",
        "craft": "展示无主灯设计、木饰面格栅背景墙隐形收纳、微水泥地面铺设。"
    }
]

# ==================== 3. 生成 Gemini 分镜脚本 ====================
def generate_script():
    topic = random.choice(DESIGN_TOPICS)
    print(f"📌 正在调用 Gemini 生成设计短视频脚本: [{topic['title']}]...")
    
    model = genai.GenerativeModel("gemini-3.6-flash")
    
    prompt = f"""
    你是一位专业的室内设计短视频编导与内容创作者。请根据以下设计主题，为一期约 60 秒的短视频创作一份分步执行的分镜脚本（必须严格分为 4 幕：第一幕、第二幕、第三幕、第四幕）。
    
    【项目信息】
    - 主题名称：{topic['title']}
    - 核心痛点：{topic['focus']}
    - 施工工艺：{topic['craft']}
    
    【核心格式要求】
    每一幕必须严格包含以下结构，切勿漏掉 Emoji 标签：
    - 📌 **幕号与主题** 
    - ⏱️ **时间轴** 
    - 🎙️ **口播旁白 (Voiceover)**: (纯中文口播台词，语气自然流畅)
    - 🎵 **音效 (SFX)**: 
    - 🖼️ **第一步：生图提示词**: (必须提供详细的英文提示词，以 `>` 开头)
    - 🎥 **第二步：生视频提示词**: (必须提供详细的英文提示词，以 `>` 开头)
    """
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)
            return topic['title'], response.text
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"⚠️ 生成脚本出错 ({e})，正在重试（等待 10 秒）...")
                time.sleep(10)
            else:
                raise e

# ==================== 4. 提取纯旁白 ====================
def extract_voiceovers(script_text):
    print("🔍 正在从脚本中精准过滤并提取纯口播旁白...")
    voiceover_lines = []
    lines = script_text.split('\n')
    capture = False
    
    for line in lines:
        if "口播旁白" in line or "Voiceover" in line:
            parts = re.split(r'[:：]', line, 1)
            if len(parts) > 1:
                content = parts[1].strip(" *`-_'")
                if content and not content.startswith("Voiceover") and not content.startswith("口播旁白"):
                    voiceover_lines.append(content)
            capture = True
            continue
        
        if capture and any(tag in line for tag in ["⏱️", "🎵", "🖼️", "🎥", "###", "---"]):
            capture = False
        elif capture:
            content = line.strip(" *`-_'")
            if content and not any(tag in content for tag in ["时间轴", "音效", "提示词", "生图", "生视频"]):
                voiceover_lines.append(content)
    
    if voiceover_lines:
        return " ".join(voiceover_lines)
        
    chinese_chars = "".join(re.findall(r'[\u4e00-\u9fa5，。！？、：；“”‘’]', script_text))
    return chinese_chars[:800] if len(chinese_chars) > 10 else script_text[:500]

# ==================== 5. 终极全局暴力捕获：确保 100% 独立生成每一幕的高清图 ====================
def generate_one_image_per_act(script_text):
    print("🎨 正在使用全局正则扫描器，强力提取脚本中的所有生图提示词并独立渲染...")
    
    raw_matches = re.findall(r'(?:生图提示词|Image Prompt)\s*[:：]\s*(?:>)?\s*([A-Za-z0-9\s,\.\-_\'\"!#\-\–—\(\)]+)', script_text)
    
    prompts = []
    for m in raw_matches:
        cleaned = m.strip(" >*`-_'\"")
        if len(cleaned) > 15 and cleaned not in prompts:
            prompts.append(cleaned)
            
    if len(prompts) < 2:
        print("⚠️ 全局扫描未满，启动多幕标准保底方案，确保生成 4 张高清分镜图...")
        prompts = [
            "A cinematic wide-angle photograph of an old, dark, cluttered Malaysian apartment kitchen, dated yellowed tiles, disorganized countertops, dim lighting, 8k resolution --ar 9:16",
            "Construction montage shot of a interior renovation in progress, plasterer applying warm grey smooth microcement to a wall, oak wood cabinet, 8k --ar 9:16",
            "Stunning transformation shot of a modern Japandi style kitchen in a bright apartment, natural sunlight, smooth microcement walls, flawless oak cabinetry, 8k --ar 9:16",
            "Aesthetic close-up detail shot of the Japandi kitchen, warm LED light casting a soft glow on a textured microcement wall, photorealistic --ar 9:16"
        ]

    print(f"✨ 成功锁定 {len(prompts)} 个分镜生图任务，开始依次独立渲染每一幕的高清图...")

    generated_files = []
    for idx, prompt_text in enumerate(prompts, start=1):
        filename = f"scene_image_{idx}.jpg"
        
        hd_prompt = f"{prompt_text}, highly detailed, architectural interior photography, photorealistic, 8k resolution, cinematic lighting"
        
        print(f"🖼️ 正在渲染第 {idx} 幕高清图 ({filename})...")
        
        encoded_prompt = urllib.parse.quote(hd_prompt)
        image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1080&height=1920&nologo=true&enhance=true"
        
        success = False
        for attempt in range(3):
            try:
                res = requests.get(image_url, timeout=50)
                if res.status_code == 200 and len(res.content) > 15000:
                    with open(filename, "wb") as f:
                        f.write(res.content)
                    print(f"   ✅ {filename} 生成并保存成功 ({len(res.content) // 1024} KB)")
                    generated_files.append(filename)
                    success = True
                    break
            except Exception as e:
                print(f"   ⚠️ {filename} 下载异常 ({e})，重试中...")
            time.sleep(3)
            
        if not success:
            print(f"   ❌ {filename} 生成失败，跳过。")
            
    print(f"🎉 成功完成所有分幕图片渲染，共生成 {len(generated_files)} 张独立高清图！")
    return generated_files

# ==================== 6. Edge-TTS 语音合成 ====================
async def text_to_speech(text, output_filename="voiceover.mp3"):
    if not text or len(text.strip()) < 5:
        text = "欢迎来到本期马来西亚室内设计改造分享，让我们一起打造高品质生活空间。"

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

# ==================== 7. Notion 动态按幕多图排版同步 ====================
def split_text_into_chunks(text, max_length=1900):
    return [text[i:i + max_length] for i in range(0, len(text), max_length)]

def save_to_notion_with_all_media(topic_title, script_content, image_files):
    print("📤 正在将完整脚本、每一幕专属高清图与音频播放器同步写入 Notion...")
    
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    
    audio_public_url = f"https://raw.githubusercontent.com/{GITHUB_REPOSITORY}/main/voiceover.mp3"
    
    script_chunks = split_text_into_chunks(script_content, max_length=1900)
    rich_text_array = [{"type": "text", "text": {"content": chunk}} for chunk in script_chunks]
    
    children_blocks = []
    
    for img in image_files:
        img_public_url = f"https://raw.githubusercontent.com/{GITHUB_REPOSITORY}/main/{img}"
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
    # 每次运行前自动清理本地旧的图片文件，确保全新生成
    for f in os.listdir("."):
        if f.startswith("scene_image_") and f.endswith(".jpg"):
            try:
                os.remove(f)
            except:
                pass

    title, script = generate_script()
    voiceover_text = extract_voiceovers(script)
    asyncio.run(text_to_speech(voiceover_text, "voiceover.mp3"))
    image_files = generate_one_image_per_act(script)
    save_to_notion_with_all_media(title, script, image_files)
