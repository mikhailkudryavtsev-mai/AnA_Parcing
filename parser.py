import requests

url = "https://mai.ru/press/news/?tags=10312"

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


response = requests.get(url, headers=headers, timeout=20)

print(response.status_code)

if response.status_code == 200:
    with open("page.html", "w", encoding="utf-8") as f:
        f.write(response.text)
    print(response.text[:2000])
else:
    print(response.status_code)
    print(response.text[:500])
