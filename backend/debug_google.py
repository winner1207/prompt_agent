import os
import requests
import json
from dotenv import load_dotenv

# 1. 强制加载配置
load_dotenv()

# 2. 这里的配置必须与 .env 一致，手动填入你的新 KEY 和端口进行测试
API_KEY = os.getenv("GOOGLE_API_KEY") 
PROXY_URL = "http://10.100.2.21:7897" # 强烈建议用 127.0.0.1

print(f"[-] 正在测试连接...")
print(f"[-] API Key (前5位): {API_KEY[:5]}...")
print(f"[-] 代理地址: {PROXY_URL}")

# 3. 构造原生 HTTP 请求 (绕过所有 SDK)
url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={API_KEY}"

headers = {
    "Content-Type": "application/json"
}

data = {
    "contents": [{
        "parts": [{"text": "你好，如果能收到这条消息，请回复'Success'。"}]
    }]
}

proxies = {
    "http": PROXY_URL,
    "https": PROXY_URL
}

try:
    print("[-] 发送请求中 (约需 5-10秒)...")
    response = requests.post(url, headers=headers, json=data, proxies=proxies, timeout=10)
    
    print(f"[-] 状态码: {response.status_code}")
    
    if response.status_code == 200:
        print("[SUCCESS] ✅ 连接成功！")
        print("返回内容:", response.json())
    else:
        print("[ERROR] ❌ 连接失败")
        print("错误详情:", response.text)

except Exception as e:
    print(f"[FATAL] ⛔ 请求发生异常: {str(e)}")
    print("建议：检查 Clash 是否开启了 System Proxy，或者端口是否真的是 7897")