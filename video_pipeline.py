import os
import requests
import google.generativeai as genai

# 从环境变量中读取密钥和配置
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
NOTION_API_KEY = os.environ.get("NOTION_API_KEY")
DATABASE_ID = "401e3e5446a9805ea91ddcbb6942de7a"

# 初始化 Gemini
genai.configure(api_key=GEMINI_API_KEY)

def generate_script():
    print("Generating video script for [AI Automation Workflow]...")
    # 使用你目前在用的 gemini-3.8-flash 模型
    model = genai.GenerativeModel("gemini-3.8-flash")
    
    prompt = (
        "请为一期关于『AI Automation Workflow（AI自动化工作流）』的短视频创作一份详细的分镜脚本。 "
        "包含画面视觉（Visuals）和旁白/配音（Voiceover），内容要生动、干货满满，适合发布在抖音或 TikTok 上。"
    )
    
    response = model.generate_content(prompt)
    return response.text

def split_text_into_chunks(text, max_length=2000):
    """将长文本切分为不超过 max_length 字符的列表，适配 Notion 的 rich_text 限制"""
    return [text[i:i + max_length] for i in range(0, len(text), max_length)]

def save_to_notion(script_content):
    print("Writing to Notion database...")
    
    url = "https://api.notion.com/v1/pages"
    
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    
    # 将超长的脚本进行自动分块（每块最多 2000 个字符）
    script_chunks = split_text_into_chunks(script_content, max_length=2000)
    
    # 构造 Notion 的富文本数组结构
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
                            "content": "AI Automation Workflow Script"
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
        print("Success: Script successfully saved to Notion!")
    else:
        print(f"Error: Failed to write -> {response.text}")

if __name__ == "__main__":
    script = generate_script()
    save_to_notion(script)
