"""
微信公众号文章提取脚本
用法: D:/Anaconda3/python.exe wechat_fetch.py <文章链接>
输出: Markdown 格式到 stdout
"""
import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from scrapling import Fetcher
from html2text import HTML2Text

def fetch_article(url):
    f = Fetcher()
    resp = f.get(url)
    if resp.status != 200:
        print(f"ERROR: HTTP {resp.status}")
        return

    h = HTML2Text()
    h.body_width = 0
    h.ignore_links = False
    h.ignore_images = False
    h.ignore_emphasis = False
    h.skip_internal_links = False
    h.mark_code = True

    print(h.handle(resp.text)[:5000])


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "https://mp.weixin.qq.com/s/HCBkgfIZkL939cQR67quEg"
    fetch_article(url)
