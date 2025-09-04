import os
import time
import requests
import boto3
from bs4 import BeautifulSoup
from botocore.exceptions import NoCredentialsError, ClientError

URL = "https://bulbapedia.bulbagarden.net/wiki/List_of_Pok%C3%A9mon_by_National_Pok%C3%A9dex_number"
BUCKET_NAME = "tppokemon"
CATEGORY_PREFIX = "images_pokemon"
REGION = "eu-west-3"

HEADERS = {"User-Agent": "Mozilla/5.0"}

s3 = boto3.client("s3", region_name=REGION)

def get_pokemon_images():
    try:
        response = requests.get(URL, headers=HEADERS, timeout=15)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"❌ Erreur lors de la requête HTTP : {e}")
        return {}

    soup = BeautifulSoup(response.text, "html.parser")
    categories = {}

    for headline in soup.find_all("span", {"class": "mw-headline"}):
        category = headline.text.strip().replace(" ", "_")
        table = headline.find_parent().find_next_sibling("table")
        if not table:
            continue

        img_urls = []
        for img in table.find_all("img"):
            src = img.get("src")
            if src:
                if src.startswith("//"):
                    src = "https:" + src
                elif src.startswith("/"):
                    src = "https://bulbapedia.bulbagarden.net" + src
                img_urls.append(src)

        if img_urls:
            categories[category] = list(set(img_urls))

    return categories

def upload_to_s3(file_content, bucket, key):
    try:
        s3.put_object(Bucket=bucket, Key=key, Body=file_content)
        url = f"https://{bucket}.s3.{REGION}.amazonaws.com/{key}"
        print(f"✅ Upload S3 : {url}")
        return url
    except (NoCredentialsError, ClientError) as e:
        print(f"❌ Erreur upload S3 : {e}")
        return None

def scrape_and_upload():
    categories = get_pokemon_images()
    total = sum(len(urls) for urls in categories.values())
    print(f"📦 {total} images trouvées, upload vers {BUCKET_NAME}")

    for category, img_urls in categories.items():
        for i, url in enumerate(img_urls, start=1):
            try:
                response = requests.get(url, headers=HEADERS, timeout=15)
                response.raise_for_status()

                ext = os.path.splitext(url)[-1].split("?")[0] or ".png"
                s3_key = f"{CATEGORY_PREFIX}/{category}/pokemon_{i}{ext}"

                upload_to_s3(response.content, BUCKET_NAME, s3_key)
                time.sleep(1)
            except requests.RequestException as e:
                print(f"⚠️ Erreur téléchargement {url}: {e}")

if __name__ == "__main__":
    scrape_and_upload()
