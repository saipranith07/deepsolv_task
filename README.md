# GenAI Developer Assignment - LinkedIn Insights Microservice

## 📄 Project Overview
This project is a Microservice designed to fetch, store, and analyze LinkedIn Company Page insights. It was built to meet the assignment requirements of creating a robust backend system with **AI integration** and **Database persistence**, optimized for a quick turnaround time.

---

## 🚀 What I Did (My Approach)

To solve the problem of scraping dynamic LinkedIn data and providing AI summaries, I implemented the following architecture:

1.  **Backend Framework:** I chose **FastAPI** over Django/Flask because it is faster, lightweight, and has built-in support for asynchronous operations (crucial for scraping).
2.  **Database Strategy:** I used **MongoDB Atlas (NoSQL)**. Since scraped data (followers, posts, descriptions) varies per company, a flexible JSON-like document structure was better than a rigid SQL schema.
3.  **The Scraping Solution:**
    * I initially considered simple `requests`, but LinkedIn blocks standard HTTP requests.
    * **Solution:** I implemented a **Selenium-based "Smart Scraper"** using Headless Chrome. This mimics a real user (with specific User-Agents) to successfully load the dynamic JavaScript content on public profile pages.
4.  **AI Integration:** I integrated **Google Gemini 1.5 Flash** to process the scraped description and follower stats into a concise "AI Summary," providing value beyond raw data.
5.  **Deployment Readiness:** I built a custom **Dockerfile** that installs Google Chrome and its drivers inside the container, ensuring the scraper works in a cloud environment.

---

## 🛠️ How I Executed It (Step-by-Step)

### Step 1: Database Setup (MongoDB Atlas)
* Created a free tier cluster on MongoDB Atlas.
* Configured **Network Access** to `0.0.0.0/0` (Allow Anywhere) to ensure the cloud-hosted application can connect to the DB without IP restrictions.
* Obtained the connection string and secured it using a `.env` file.

### Step 2: Developing the Microservice
* **API Design:** I created two main endpoints:
    * `GET /page/{page_id}`: The core logic. It checks the DB first (Cache). If data is missing, it triggers the Selenium scraper, generates an AI summary, saves it to Mongo, and returns the result.
    * `GET /search`: Allows filtering stored pages by industry or follower count.
* **Asynchronous Coding:** Used `async/await` and `Motor` (Async Mongo driver) to ensure the server remains responsive while the scraper runs in the background.

### Step 3: Tackling the Scraping Challenge
* Implemented `selenium` with `webdriver-manager`.
* Configured Chrome options to run `--headless` (invisible) and added `no-sandbox` to prevent crashes in the server environment.
* Used **XPath** and flexible text search (e.g., finding elements containing "followers") instead of rigid CSS classes, making the scraper more resistant to LinkedIn's code changes.

### Step 4: Containerization (Docker)
* Standard Python images do not have Chrome installed.
* I wrote a specialized `Dockerfile` that:
    1.  Downloads and installs the Google Chrome signing keys (using `gpg`).
    2.  Installs the stable version of Google Chrome.
    3.  Installs Python dependencies (`selenium`, `fastapi`, `uvicorn`).
    4.  Exposes the necessary ports for Render/Cloud hosting.

---

## 📊 The Results

### 1. Simple User Interface (Swagger UI)
Due to the strict timeline (24 hours), I prioritized backend robustness over a custom frontend. The application utilizes **FastAPI's automatic Swagger UI**, which provides an interactive dashboard to test APIs directly.

* **URL:** `/docs`
* **Functionality:** Allows users to input a Company ID, execute the scraper, and see the JSON response visually.

### 2. Output Data Sample
When querying for `google`, the system successfully scrapes and returns:

```json
{
  "page_id": "google",
  "name": "Google",
  "url": "[https://www.linkedin.com/company/google](https://www.linkedin.com/company/google)",
  "description": "A problem isn't truly solved until it's solved for everyone. Google’s mission is to organize the world’s information...",
  "followers": "33,124,000 followers",
  "industry": "Software Development",
  "profile_pic": "[https://media.licdn.com/dms/image/](https://media.licdn.com/dms/image/)...",
  "ai_summary": "Google is a massive global Software Development company with over 33 million followers. They focus on organizing information and making it universally accessible.",
  "posts": [
    {
      "content": "Join us at Google Cloud Next '24 to learn about the latest...",
      "likes": "N/A (Login Required)",
      "comments_count": "N/A"
    }
  ]
}