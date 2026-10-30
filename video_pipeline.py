import os
import time
import random
import asyncio
import requests
import re
import edge_tts
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted

# ==================== 1. 配置与环境变量 ====================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
NOTION_API_KEY = os.environ.get("NOTION_API_KEY")
# 自动获取 GitHub 仓库名（如 tukanggo/ai-video-pipeline），如果为空则使用你的默认仓库
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
    
    model = genai.GenerativeModel("gemini-3.8-flash")
    prompt = f"""
    你是一位专业的室内设计短视频编导与内容创作者。请根据以下设计主题，为一期约 60 秒的短视频创作一份分步执行的分镜脚本。
    
    【项目信息】
    - 主题名称：{topic['title']}
    - 核心痛点：{topic['focus']}
    - 施工工艺：{topic['craft']}
    
    【核心格式要求】
    每一幕必须严格包含以下结构：
    - 📌 **幕号与主题** 
    - ⏱️ **时间轴** 
    - 🎙️ **口播旁白 (Voiceover)**: (纯中文口播台词，语气自然流畅，适合短视频口播，绝对不要包含任何英文提示词或代码符号)
    - 🎵 **音效 (SFX)**: 
    - 🖼️ **第一步：生图提示词**: 
    - 🎥 **第二步：生视频提示词**: 
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

# ==================== 4. 智能提取纯旁白 ====================
def extract_voiceovers(script_text):
    """
    精确提取所有 '🎙️ 口播旁白' 后面的中文台词，过滤掉所有时间轴、音效和生图提示词。
    """
    # 正则匹配旁白
    pattern = r"(?:🎙️|\*\*?口播旁白[^:\n]*[:：]\*\*?)\s*([^\n#*]+)"
    matches = re.findall(pattern, script_text)
    
    if matches:
        clean_lines = [m.strip(" *`-_") for m in matches if len(m.strip()) > 2]
        full_voiceover = " ".join(clean_lines)
        if len(full_voiceover) > 10:
            print(f"🎙️ 成功提取纯旁白文本 ({len(full_voiceover)}字): {full_voiceover[:120]}...")
            return full_voiceover

    # 兜底：如果正则未匹配到，提取全文中的中文字符
    print("⚠️ 警告：正则未严格匹配旁白标签，启动中文通用兜底提取...")
    chinese_chars = "".join(re.findall(r'[\u4e00-\u9fa5，。！？、]', script_text))
    if len(chinese_chars) > 20:
        return chinese_chars[:800]
        
    return script_text[:500]

# ==================== 5. Edge-TTS 语音合成（带防 0KB 校验） ====================
async def text_to_speech(text, output_filename="voiceover.mp3"):
    """安全稳健的 Edge-TTS 合成函数，带防 0KB 损坏校验与自动重试"""
    if not text or len(text.strip()) < 5:
        print("⚠️ 警告：检测到提取的旁白文本为空，已自动启用保底文案。")
        text = "欢迎来到本期马来西亚室内设计改造分享，让我们一起打造兼具美学与实用性的高级感生活空间。"

    print(f"🔊 正在使用 Edge-TTS 合成微软晓晓语音 (有效字数: {len(text)})...")
    voice = "zh-CN-XiaoxiaoNeural"
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # 过滤换行符等潜在干扰字符
            safe_text = re.sub(r'[\r\n\t]', ' ', text)
            
            communicate = edge_tts.Communicate(safe_text, voice)
            await communicate.save(output_filename)
            
            # 核心校验：文件必须存在且大小超过 1KB（彻底杜绝 0 KB 损坏）
            if os.path.exists(output_filename) and os.path.getsize(output_filename) > 1024:
                file_size = os.path.getsize(output_filename)
                print(f"✅ 语音合成成功: {output_filename} (文件大小: {file_size} 字节)")
                return
            else:
                print(f"⚠️ 第 {attempt + 1} 次生成的文件异常（大小 <= 1KB 或 0 KB），正在重试...")
        except Exception as e:
            print(f"⚠️ TTS 合成异常: {e}，正在进行第 {attempt + 1} 次重试...")
            
        await asyncio.sleep(5)
        
    raise Exception("❌ 致命错误：多次尝试后 Edge-TTS 依然无法生成有效的 MP3 文件。")

# ==================== 6. 切片与写入 Notion 数据库 ====================
def split_text_into_chunks(text, max_length=1900):
    return [text[i:i + max_length] for i in range(0, len(text), max_length)]

def save_to_notion_with_audio(topic_title, script_content):
    print("📤 正在将脚本与原生音频播放器写入 Notion 数据库...")
    
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    
    # 构造公开的 GitHub Raw 音频直链
    audio_public_url = f"https://raw.githubusercontent.com/{GITHUB_REPOSITORY}/main/voiceover.mp3"
    
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
        # 在 Notion 页面正文中直接挂载原生音频播放器块
        "children": [
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
        print(f"🎉 Success: '{topic_title}' 及其配套音频已成功写入 Notion！")
    else:
        print(f"❌ Error: 写入 Notion 失败 -> {response.text}")

# ==================== 主程序入口 ====================
if __name__ == "__main__":
    # 1. 生成大纲分镜脚本
    title, script = generate_script()
    
    # 2. 精准提取纯旁白台词
    voiceover_text = extract_voiceovers(script)
    
    # 3. 异步合成语音并保存为 voiceover.mp3
    asyncio.run(text_to_speech(voiceover_text, "voiceover.mp3"))
    
    # 4. 写入 Notion 数据库（并嵌入音频外链）
    save_to_notion_with_audio(title, script)
