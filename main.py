import os
import time
import logging
from typing import List, Optional
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient
import google.generativeai as genai

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup

# --- CONFIGURATION ---
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="LinkedIn Insights Microservice")

client = AsyncIOMotorClient(MONGO_URI)
db = client.linkedin_db
pages_collection = db.pages

@app.on_event("startup")
async def create_indexes():
    await pages_collection.create_index("page_id", unique=True)

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

class Post(BaseModel):
    content: str
    likes: str 
    comments_count: str

class Page(BaseModel):
    page_id: str
    name: str
    url: str
    description: str
    followers: str 
    industry: str
    profile_pic: str
    posts: List[Post] = []
    ai_summary: Optional[str] = None

def get_real_linkedin_data(page_id: str):
    url = f"https://www.linkedin.com/company/{page_id}"
    logger.info(f"Starting generic scraper for: {url}")

    chrome_options = Options()
    chrome_options.add_argument("--headless") 
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    try:
        driver.get(url)
        time.sleep(5) 
        
        soup = BeautifulSoup(driver.page_source, "lxml")

        
        name_tag = soup.find("h1")
        name = name_tag.text.strip() if name_tag else page_id
        description = "Description not found."
        about_section = soup.find("p", {"class": "break-words white-space-pre-wrap"}) 
        if about_section:
            description = about_section.text.strip()

        industry = "Technology (Default)"
        followers = "Unknown"
        
        info_divs = soup.find_all("div", class_="inline-block")
        for div in info_divs:
            text = div.text.strip()
            if "followers" in text:
                followers = text
            elif "employees" not in text and len(text) > 3: # Crude heuristic for industry
                industry = text

        profile_pic = "https://via.placeholder.com/150"
        img_tag = soup.find("img", alt=name)
        if img_tag and img_tag.get("src"):
            profile_pic = img_tag.get("src")

        posts = []
        post_containers = soup.find_all("div", class_="attribution-recording-group")
        
        if not post_containers:
             post_containers = soup.find_all("p")[:5]

        for p in post_containers[:3]: # Limit to 3 posts
            text_content = p.text.strip()
            if len(text_content) > 20: # Filter out empty noise
                posts.append({
                    "content": text_content[:150] + "...",
                    "likes": "N/A (Login Required)",
                    "comments_count": "N/A"
                })

        return {
            "page_id": page_id,
            "name": name,
            "url": url,
            "description": description,
            "followers": followers,
            "industry": industry,
            "profile_pic": profile_pic,
            "posts": posts
        }

    except Exception as e:
        logger.error(f"Scraping Error: {e}")
        return {
             "page_id": page_id, 
             "name": page_id, 
             "url": url, 
             "description": "Failed to scrape (LinkedIn Blocked)", 
             "followers": "0", 
             "industry": "Unknown", 
             "profile_pic": "", 
             "posts": []
        }
    finally:
        driver.quit()


@app.get("/")
def home():
    return {"status": "running", "msg": "Go to /docs for Swagger UI"}

@app.get("/page/{page_id}", response_model=Page)
async def get_page_insights(page_id: str):
    existing_page = await pages_collection.find_one({"page_id": page_id})
    if existing_page:
        return existing_page

    scraped_data = get_real_linkedin_data(page_id)
    
    try:
        prompt = f"Summarize this company based on their description: {scraped_data['description']}"
        ai_response = model.generate_content(prompt)
        scraped_data['ai_summary'] = ai_response.text
    except Exception:
        scraped_data['ai_summary'] = "AI Summary unavailable."

    await pages_collection.insert_one(scraped_data)
    scraped_data.pop("_id", None)
    return scraped_data

@app.get("/search", response_model=List[Page])
async def search_pages(limit: int = 10):
    cursor = pages_collection.find().limit(limit)
    return await cursor.to_list(length=limit)