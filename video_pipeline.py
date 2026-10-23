import os
import time
import random
import requests
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted

# 从环境变量中读取密钥和配置
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
NOTION_API_KEY = os.environ.get("NOTION_API_KEY")
DATABASE_ID = "401e3e5446a9805ea91ddcbb6942de7a"

# 初始化 Gemini
genai.configure(api_key=GEMINI_API_KEY)

# 💡 你的专属室内设计与房屋改造主题库
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
    },
    {
        "title": "顶楼阳光房/露台花园改造 (Tropical Zen Balcony & Lounge)",
        "focus": "针对闷热、暴晒、荒废的露台或阳台空间。",
        "craft": "展示防腐木地台、垂直绿化垂直竹墙、户外折叠遮阳篷与氛围暖光安装。"
    },
    {
        "title": "小户型主卧衣帽间一体化改造 (Wabi-Sabi Master Bedroom)",
        "focus": "针对主卧空间局促、储物空间不足、缺乏氛围感的问题。",
        "craft": "展示弧形艺术墙面涂刷、嵌入式通顶无把手衣柜、床头悬浮灯带安装。"
    },
    {
        "title": "工业风复式 Loft 楼梯与书房改造 (Industrial Japandi Loft)",
        "focus": "针对老旧铁艺楼梯冰冷、畸形角落浪费、采光被遮挡的痛点。",
        "craft": "展示钢木结合悬浮踏步安装、墙面艺术涂料、定制原木转角书桌。"
    }
]

def generate_script():
    # 随机选择一个室内设计主题
    topic = random.choice(DESIGN_TOPICS)
    print(f"Generating modular design script for: [{topic['title']}]...")
    
    # 💡 修正：使用正确的 gemini-2.5-flash 模型
    model = genai.GenerativeModel("gemini-2.5-flash")
    
    # 💡 完美融合了室内设计主题与“分步卡片式格式”的 Prompt 模板
    prompt = f"""
    你是一位专业的室内设计短视频编导与内容创作者。请根据以下设计主题，为一期约 60 秒的短视频创作一份分步执行的分镜脚本。
    
    【项目信息】
    - 主题名称：{topic['title']}
    - 核心痛点：{topic['focus']}
    - 施工工艺：{topic['craft']}
    
    【节奏与结构要求 (Pacing)】
    严格按照 3 个阶段（0-15s 老旧痛点、15-45s 匠心施工、45-60s 焕新呈现）展开，共拆分为 6 到 7 个独立的幕（Scene）。
    
    【核心格式要求】
    为了方便创作者在 Canva 生成图片、在 Runway/剪映生成视频以及录制配音，每一幕必须严格包含以下 5 个模块：
    - 📌 **幕号与主题** (例如: 第一幕：黄金3秒抓眼球)
    - ⏱️ **时间轴** (例如: 00:00 - 00:04)
    - 🎙️ **口播旁白 (Voiceover)**: (干货、有高级感或反差感的中文台词)
    - 🎵 **音效 (SFX)**: (如：工具敲击声、清脆治愈的升华音效等)
    - 🖼️ **第一步：生图提示词 (Image Prompt / Canva & Midjourney)**: (详细的英文画面描述，带 cinematic, photorealistic, 8k --ar 16:9 等参数)
    - 🎥 **第二步：生视频提示词 (Video Prompt / Runway & Kling)**: (动态镜头运动英文提示词，如 camera zooms in, 60fps)
    
    请确保内容生动、极具高级感和纪录片质感，适合直接复制粘贴去生产。
    """
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)
            return topic['title'], response.text
        except ResourceExhausted as e:
            if attempt < max_retries - 1:
                print(f"触发免费版频率限制 (429)，正在等待 60 秒后进行第 {attempt + 2} 次重试...")
                time.sleep(60)
            else:
                print("已达到最大重试次数，API 额度耗尽。")
                raise e

def split_text_into_chunks(text, max_length=1900):
    """将长文本严格切分为安全长度（设为1900以防中文多字节边界溢出）的列表，适配 Notion 的 rich_text 限制"""
    return [text[i:i + max_length] for i in range(0, len(text), max_length)]

def save_to_notion(topic_title, script_content):
    print("Writing to Notion database...")
    
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    
    # 💡 将长脚本切分为多个 <2000 字符的片段
    script_chunks = split_text_into_chunks(script_content, max_length=1900)
    
    rich_text_array = []
    for chunk in script_chunks:
        rich_text_array.append({
            "type": "text",
            "text": {
                "content": chunk
            }
        })
    
    payload = {
        "parent": {"database_id": DATABASE_ID},
        "properties": {
            "Name": {
                "title": [
                    {
                        "text": {
                            "content": topic_title
                        }
                    }
                ]
            },
            "Script": {
                "rich_text": rich_text_array
            }
        }
    }
    
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code == 200:
        print(f"Success: Modular design script '{topic_title}' successfully saved to Notion!")
    else:
        print(f"Error: Failed to write -> {response.text}")

if __name__ == "__main__":
    title, script = generate_script()
    save_to_notion(title, script)
