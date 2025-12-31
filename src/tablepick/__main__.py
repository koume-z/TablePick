'''
TablePickのエントリーポイント
全体の流れを制御する
'''

import sys
import requests
from urllib.parse import urlparse

headers = {"User-Agent": f"MyTool/1.1 (xxxx@xxx.com) UsedBaseLibrary/1.4"}

# ユーザーからURLを受け取る
target_url = input("input target URL: ")
parsed = urlparse(target_url)

# URLを検証する
if not parsed.scheme or not parsed.netloc:
    print("Error: Invalid URL format")
    sys.exit(1)

# URL先のコンテンツを取得する
try:
    print(f"Target URL: {target_url}")
    response = requests.get(target_url, headers=headers, timeout=10)
    print(f"HTTP Status Code: {response.status_code}")

    if response.status_code == 200:
        content = response.text
        print("Content retrieved successfully.")
    else:
        print(f" Failed: status code {response.status_code}")

except requests.exceptions.Timeout:
    print("Error: Request timed out")

except requests.exceptions.HTTPError as e:
    print(f"HTTP Error: {e}")

except requests.exceptions.ConnectionError as e:
    print(f"Connection Error: {e}")

