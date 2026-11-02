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
    
    model = genai.GenerativeModel("gemini-2.5-flash")
    
    prompt = f"""
    你是一位专业的室内设计短视频编导与内容创作者。请根据以下设计主题，为一期约 60 秒的短视频创作一份分步执行的分镜脚本（建议分为 3-4 个幕）。
    
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
    - 🖼️ **第一步：生图提示词**: (必须提供详细的高清英文提示词，以 `>` 开头)
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

# ==================== 5. 多图并发生成：1080P 超高清画质 ====================
def generate_all_images_from_script(script_text):
    print("🎨 正在扫描脚本中的所有生图提示词并准备进行 1080P 超高清渲染...")
    
    pattern = r"(?:生图提示词|Image Prompt).*?[:：]\s*(?:>)?\s*([A-Za-z0-9\s,\.\-_'\"!#]+?)(?=\n\s*[-*#]|\n\s*[⏱️🎙️🎵🎥🎬]|$)"
    matches = re.findall(pattern, script_text, re.DOTALL)
    
    prompts = [m.strip(" >*`-_'\"") for m in matches if len(m.strip()) > 15]
    
    if not prompts:
        lines = script_text.split('\n')
        for i, line in enumerate(lines):
            if "生图提示词" in line or "Image Prompt" in line:
                if i + 1 < len(lines):
                    p = lines[i+1].strip(" >*`-_'")
                    if len(p) > 15 and p not in prompts:
                        prompts.append(p)
                        
    if not prompts:
        prompts = [
            "Modern minimalist interior design, cozy lighting, photorealistic interior photography.",
            "Renovation work in progress, professional craftsmanship, warm wabi-sabi style."
        ]
        
    print(f"✨ 成功检测到 {len(prompts)} 个分镜，开始并行渲染 1080P 超高清效果图...")
    
    generated_files = []
    for idx, prompt_text in enumerate(prompts, start=1):
        filename = f"scene_image_{idx}.jpg"
        
        # 自动追加摄影级超高清画质关键词
        hd_prompt = f"{prompt_text}, highly detailed, architectural interior photography, photorealistic, 8k resolution, Unreal Engine 5 render, cinematic lighting"
        
        print(f"🖼️ 正在生成第 {idx} 张 1080P 高清图: {hd_prompt[:60]}...")
        
        encoded_prompt = urllib.parse.quote(hd_prompt)
        # 设定 1920x1080 全高清分辨率
        image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1920&height=1080&nologo=true&enhance=true"
        
        success = False
        for attempt in range(3):
            try:
                res = requests.get(image_url, timeout=50)
                if res.status_code == 200 and len(res.content) > 15000:
                    with open(filename, "wb") as f:
                        f.write(res.content)
                    print(f"   ✅ 第 {idx} 张高清图生成成功 -> {filename} ({len(res.content) // 1024} KB)")
                    generated_files.append(filename)
                    success = True
                    break
            except Exception as e:
                print(f"   ⚠️ 第 {idx} 张图下载异常 ({e})，重试中...")
            time.sleep(4)
            
        if not success:
            print(f"   ❌ 第 {idx} 张高清图生成失败，跳过。")
            
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

# ==================== 7. Notion 多图多媒体动态组装 ====================
def split_text_into_chunks(text, max_length=1900):
    return [text[i:i + max_length] for i in range(0, len(text), max_length)]

def save_to_notion_with_all_media(topic_title, script_content, image_files):
    print("📤 正在将完整脚本、多张 1080P 效果图与音频播放器同步写入 Notion...")
    
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
    
    # 按顺序依次插入所有生成的 1080P 高清图片块
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
        
    # 在图片下方挂载全局语音播放器
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
        print(f"🎉 Success: '{topic_title}' 及其 {len(image_files)} 张 1080P 效果图与音频已成功同步至 Notion！")
    else:
        print(f"❌ Error: 写入 Notion 失败 -> {response.text}")

# ==================== 主程序入口 ====================
if __name__ == "__main__":
    # 1. 生成分镜脚本
    title, script = generate_script()
    
    # 2. 提取并合成旁白语音
    voiceover_text = extract_voiceovers(script)
    asyncio.run(text_to_speech(voiceover_text, "voiceover.mp3"))
    
    # 3. 扫描脚本并批量生成所有分镜的 1080P 高清图 -> scene_image_1.jpg, scene_image_2.jpg...
    image_files = generate_all_images_from_script(script)
    
    # 4. 同步写入 Notion
    save_to_notion_with_all_media(title, script, image_files)
