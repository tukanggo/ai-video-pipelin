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
# 自动获取 GitHub 仓库名，格式如 tukanggo/ai-video-pipeline
GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY", "tukanggo/ai-video-pipeline") 
DATABASE_ID = "401e3e5446a9805ea91ddcbb6942de7a"

# 初始化 Gemini
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
    
    # 💡 核心修复：将旧的错误的 gemini-3.8-flash 替换为官方稳定的 gemini-2.5-flash
    model = genai.GenerativeModel("gemini-2.5-flash")
    
    prompt = f"""
    你是一位专业的室内设计短视频编导与内容创作者。请根据以下设计主题，为一期约 60 秒的短视频创作一份分步执行的分镜脚本。
    
    【项目信息】
    - 主题名称：{topic['title']}
    - 核心痛点：{topic['focus']}
    - 施工工艺：{topic['craft']}
    
    【核心格式要求】
    每一幕必须严格包含以下结构，切勿漏掉 Emoji 标签：
    - 📌 **幕号与主题** 
    - ⏱️ **时间轴** 
    - 🎙️ **口播旁白 (Voiceover)**: (纯中文口播台词，语气自然流畅，适合短视频口播，绝对不要包含任何英文提示词或代码符号)
    - 🎵 **音效 (SFX)**: 
    - 🖼️ **第一步：生图提示词**: (必须提供详细的英文提示词，以 `>` 开头)
    - 🎥 **第二步：生视频提示词**: (必须提供详细的英文提示词，以 `>` 开头)
    """
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)
            return topic['title'], response.text
        except ResourceExhausted as e:
            if attempt < max_retries - 1:
                print(f"⚠️ Gemini 额度超限，正在进行第 {attempt + 1} 次重试（等待 60 秒）...")
                time.sleep(60)
            else:
                raise e
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"⚠️ 生成脚本出错 ({e})，正在进行第 {attempt + 1} 次重试（等待 10 秒）...")
                time.sleep(10)
            else:
                raise e

# ==================== 4. 完美精准过滤纯旁白 ====================
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
        full_voiceover = " ".join(voiceover_lines)
        if len(full_voiceover) > 5:
            print(f"🎙️ 成功精准提取纯旁白 ({len(full_voiceover)} 字): {full_voiceover[:120]}...")
            return full_voiceover

    pattern = r"(?:🎙️|口播旁白|Voiceover).*?[:：]\s*\*?\*?([^\n#*]+)"
    matches = re.findall(pattern, script_text)
    if matches:
        clean_parts = [m.strip(" *`-_'") for m in matches if len(m.strip()) > 2]
        full_voiceover = " ".join(clean_parts)
        if len(full_voiceover) > 5:
            print(f"🎙️ 备用正则命中旁白 ({len(full_voiceover)} 字): {full_voiceover[:120]}...")
            return full_voiceover

    print("⚠️ 警告：未能精准匹配旁白，启动中文字符全局兜底...")
    chinese_chars = "".join(re.findall(r'[\u4e00-\u9fa5，。！？、：；“”‘’]', script_text))
    if len(chinese_chars) > 10:
        return chinese_chars[:800]
        
    return script_text[:500]

# ==================== 5. 自动根据脚本生成 AI 效果图 ====================
def generate_image_from_script(script_text, output_filename="scene_image.jpg"):
    print("🎨 正在从脚本中解析生图提示词 (Image Prompt)...")
    
    image_prompt = ""
    lines = script_text.split('\n')
    capture = False
    
    for line in lines:
        if "生图提示词" in line or "Image Prompt" in line:
            capture = True
            parts = line.split(':', 1)
            if len(parts) > 1 and len(parts[1].strip()) > 5:
                content = parts[1].strip(" >*`-_'")
                if not any(tag in content for tag in ["生图提示词", "第一步"]):
                    image_prompt = content
                    break
            continue
        
        if capture:
            cleaned_line = line.strip(" >*`-_'")
            if cleaned_line and not any(tag in cleaned_line for tag in ["🎥", "第二步", "时间轴", "幕号"]):
                image_prompt = cleaned_line
                break
                
    if not image_prompt or len(image_prompt) < 15:
        match = re.search(r"生图提示词[^\n]*[:：]\s*(?:>)?\s*([A-Za-z0-9\s,\.\-_'\"!#]+)", script_text)
        if match:
            image_prompt = match.group(1).strip(" >*`-_'")

    if not image_prompt or len(image_prompt) < 15:
        print("⚠️ 未能提取到有效英文 Prompt，已启用室内设计高清保底 Prompt。")
        image_prompt = "Dated and cluttered Malaysian apartment kitchen, worn-out mosaic tiles, peeling cabinets, dim flickering light, documentary photography, 8k, photorealistic."
    else:
        print(f"✨ 成功锁定生图 Prompt: {image_prompt[:100]}...")

    print("🖼️ 正在请求免费 AI 生图 API 渲染效果图...")
    encoded_prompt = urllib.parse.quote(image_prompt)
    image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1280&height=720&nologo=true"
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.get(image_url, timeout=45)
            if response.status_code == 200 and len(response.content) > 5000:
                with open(output_filename, "wb") as f:
                    f.write(response.content)
                print(f"✅ AI 效果图生成成功并保存至: {output_filename} (大小: {len(response.content)} 字节)")
                return True
            else:
                print(f"⚠️ 第 {attempt + 1} 次生图返回异常，正在重试...")
        except Exception as e:
            print(f"⚠️ 生图网络请求异常: {e}，正在重试...")
            
        time.sleep(5)
        
    print("❌ 警告：多次尝试后免费生图 API 响应失败。")
    return False

# ==================== 6. Edge-TTS 语音合成（带防 0KB 校验） ====================
async def text_to_speech(text, output_filename="voiceover.mp3"):
    if not text or len(text.strip()) < 5:
        text = "欢迎来到本期马来西亚室内设计改造分享，让我们一起打造兼具美学与实用性的高级感生活空间。"

    print(f"🔊 正在使用 Edge-TTS 合成语音 (有效字数: {len(text)})...")
    voice = "zh-CN-XiaoxiaoNeural"
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            safe_text = re.sub(r'[\r\n\t]', ' ', text)
            communicate = edge_tts.Communicate(safe_text, voice)
            await communicate.save(output_filename)
            
            if os.path.exists(output_filename) and os.path.getsize(output_filename) > 1024:
                file_size = os.path.getsize(output_filename)
                print(f"✅ 语音合成成功: {output_filename} (文件大小: {file_size} 字节)")
                return
            else:
                print(f"⚠️ 第 {attempt + 1} 次生成的音频文件异常（大小 <= 1KB），正在重试...")
        except Exception as e:
            print(f"⚠️ TTS 合成异常: {e}，正在重试...")
            
        time.sleep(5)
        
    raise Exception("❌ 致命错误：多次尝试后 Edge-TTS 无法生成有效的 MP3 文件。")

# ==================== 7. 切片与写入 Notion 数据库（支持图文多媒体） ====================
def split_text_into_chunks(text, max_length=1900):
    return [text[i:i + max_length] for i in range(0, len(text), max_length)]

def save_to_notion_with_multimedia(topic_title, script_content):
    print("📤 正在将完整分镜脚本、AI 效果图与音频播放器同步写入 Notion...")
    
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    
    # 构造公开的 GitHub Raw 资源直链
    audio_public_url = f"https://raw.githubusercontent.com/{GITHUB_REPOSITORY}/main/voiceover.mp3"
    image_public_url = f"https://raw.githubusercontent.com/{GITHUB_REPOSITORY}/main/scene_image.jpg"
    
    script_chunks = split_text_into_chunks(script_content, max_length=1900)
    rich_text_array = [{"type": "text", "text": {"content": chunk}} for chunk in script_chunks]
    
    payload = {
        "parent": {"database_id": DATABASE_ID},
        "properties": {
            "Name": {
                "title": [{"text": {"content": topic_title}}]
            },
            "Script": {
                "rich_text": rich_text_array
            }
        },
        # 在 Notion 页面正文中同时嵌入“图片块”与“音频块”
        "children": [
            {
                "object": "block",
                "type": "image",
                "image": {
                    "type": "external",
                    "external": {
                        "url": image_public_url
                    }
                }
            },
            {
                "object": "block",
                "type": "audio",
                "audio": {
                    "type": "external",
                    "external": {
                        "url": audio_public_url
                    }
                }
            }
        ]
    }
    
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        print(f"🎉 Success: '{topic_title}' 及其配套效果图和音频已成功写入 Notion！")
    else:
        print(f"❌ Error: 写入 Notion 失败 -> {response.text}")

# ==================== 主程序入口 ====================
if __name__ == "__main__":
    # 1. 生成分镜脚本
    title, script = generate_script()
    
    # 2. 提取并合成旁白语音 -> voiceover.mp3
    voiceover_text = extract_voiceovers(script)
    asyncio.run(text_to_speech(voiceover_text, "voiceover.mp3"))
    
    # 3. 自动根据脚本生图提示词生成效果图 -> scene_image.jpg
    generate_image_from_script(script, "scene_image.jpg")
    
    # 4. 同步写入 Notion（同时包含图片与音频块）
    save_to_notion_with_multimedia(title, script)
