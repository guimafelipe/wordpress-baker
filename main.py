import os
import re
import requests
import pickle
from typing import Dict


SITE_BASE_1 = "https://www.titanus.com.br/"
SITE_BASE_2 = "http://www.titanus.com.br/"
SITEMAP_URL = "https://www.titanus.com.br/sitemap.xml"
OUTPUT_DIR = os.path.join(os.getcwd(), "output")
html_and_css_body_replaces_before_save = {
    SITE_BASE_1: "/",
    SITE_BASE_2: "/",
    "/wp-content/themes/california-wp/css/master-min.php": "/wp-content/themes/california-wp/css/master-min.css"
}


def main():
    visited, ignored, failed = set(), set(), set()
    crawl(SITEMAP_URL, visited, ignored, failed)
    report = {
        "visited": visited,
        "ignored": ignored,
        "failed": failed,
    }
    pickle.dump(report, open("report.pickle", "wb"))


xml_link_pattern = re.compile(r"<loc>([^\"]*?)</loc>")
html_link_patterns = [
    re.compile(r"href=\"([^\"]*?)\""),
    re.compile(r"src=\"([^\"]*?)\""),
    re.compile(r"href='([^\']*?)'"),
    re.compile(r"src='([^']*?)'"),
    re.compile(r"url\('[^']*?'\)"),
    re.compile(r"url\(\"[^\"]*?\"\)"),
]
html_srcset_pattern = re.compile("srcset=\"([^\"]*?)\"")
css_link_patterns = [
    re.compile(r"url\('[^']*?'\)"),
    re.compile(r"url\(\"[^\"]*?\"\)"),
]

def crawl(url: str, visited: set, failed: set, ignored: set):
    try:
        interrogation_idx = url.rindex("?")
        url = url[:interrogation_idx]
    except:
        pass

    if url in visited or url in ignored:
        return

    if not url.endswith(".xml") and not url.endswith("/") and not url.endswith(".jpg") \
        and not url.endswith(".css") and not url.endswith(".png") and not url.endswith(".js") \
        and not url.endswith(".html") and not url.endswith(".htm") and not url.endswith(".php") \
        and not url.endswith(".woff") and not url.endswith(".woff2") and not url.endswith(".ttf"):
        ignored.add(url)
        return
    if not url.startswith(SITE_BASE_1) and not url.startswith(SITE_BASE_2):
        ignored.add(url)
        return

    visited.add(url)
    print(f"Crawling: {url} ... ", end="", flush=True)
    try:
        response = requests.get(url)
        print(response.status_code)
    except Exception as err:
        print()
        failed.add(url)
        print("ERROR:", err)
        return
    
    if response.status_code != 200:
        if url == SITEMAP_URL:
            print("Please install the Wordpress Plugin: Google XML Sitemaps")
            exit(1)
        else:
            failed.add(url)
        return

    save(url, response.content)

    if url.endswith(".xml"):
        urls = xml_link_pattern.findall(response.text)
        for target_url in urls:
            crawl(target_url, visited, ignored, failed)
    elif url.endswith("/") or url.endswith(".php") or url.endswith(".html") or url.endswith(".htm"):
        for pattern in html_link_patterns:
            urls = pattern.findall(response.text)
            for target_url in urls:
                crawl(target_url, visited, ignored, failed)
        srcsets = html_srcset_pattern.findall(response.text)
        for srcset in srcsets:
            try:
                params = srcset.split(",")
                for param in params:
                    param = param.strip()
                    target_url, arg = param.split(" ")
                    crawl(target_url, visited, ignored, failed)
            except:
                print("SRCSET ERROR:", srcset)
    elif url.endswith(".css"):
        for pattern in css_link_patterns:
            urls = pattern.findall(response.text)
            for target_url in urls:
                crawl(target_url, visited, ignored, failed)


def save(remote_path: str, response_content: bytes):
    remote_path = remote_path.replace(SITE_BASE_1, "").replace(SITE_BASE_2, "")

    if remote_path.endswith("wp-content/themes/california-wp/css/master-min.php"):
        remote_path = remote_path.replace(".php", ".css")  # HACKY

    if remote_path.endswith("/") or len(remote_path) == 0:
        local_path = os.path.join(OUTPUT_DIR, *remote_path.split("/"), "index.html")
    else:
        local_path = os.path.join(OUTPUT_DIR, *remote_path.split("/"))
    
    local_dir = os.path.dirname(local_path)
    if not os.path.exists(local_dir):
        os.makedirs(local_dir)

    try:
        # rewrite links to work on localhost:
        if local_path.endswith(".html") or local_path.endswith(".htm") or local_path.endswith(".css"):
            response_text = response_content.decode("utf8")
            for old, new in html_and_css_body_replaces_before_save.items():
                response_text = response_text.replace(old, new)
            response_content = response_text.encode("utf8")

        with open(local_path, "wb") as file:
            file.write(response_content)
        print("File written:", local_path)
    except Exception as err:
        print("ERROR:", err)


main()
