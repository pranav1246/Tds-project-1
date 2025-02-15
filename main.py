import os
import json
import subprocess
import sqlite3
import re
from datetime import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
import openai
import httpx

# Load environment variables from .env file
load_dotenv()
AIPROXY_TOKEN = os.getenv("AIPROXY_TOKEN")
if not AIPROXY_TOKEN:
    raise ValueError("AIPROXY_TOKEN not set. Please add it to your environment or .env file.")


app = FastAPI()

class TaskRequest(BaseModel):
    task: str

# ------------------ Helper Functions ------------------
def read_file_content(filepath):
    file_path = os.path.join("/data", filepath)
    if not os.path.exists(file_path):
        return None
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        with open(file_path, "rb") as f:
            return f.read()

def write_output_file(filepath, content):
    output_path = os.path.join("/data", filepath)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

client = openai.OpenAI(api_key=AIPROXY_TOKEN)

# def query_llm(task_description, file_content=None):
#     prompt = f"""
#     Task: {task_description}
    
#     Data:
#     {file_content if file_content else "No additional data provided"}
    
#     Process this task and return ONLY the final output, without explanations.
#     """

#     response = client.chat.completions.create(
#         model="gpt-4o-mini",
#         messages=[
#             {"role": "system", "content": "You are an AI assistant performing automated tasks."},
#             {"role": "user", "content": prompt}
#         ],
#         max_tokens=200
#     )

#     return response.choices[0].message.content.strip()

def query_llm(prompt, file_content=None):
    full_prompt = f"""Task: {prompt}

Data:
{file_content if file_content else "No additional data provided"}

Process this task and return ONLY the final output, without any extra explanation."""
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are an AI assistant performing automated tasks."},
            {"role": "user", "content": full_prompt}
        ],
        max_tokens=200,
    )
    return response.choices[0].message.content.strip()

def parse_task_description(task_desc: str) -> str:
    """
    Use the LLM to map a free-text task description to a canonical task key.
    """
    prompt = f"""
You are an automation assistant. Given the following task description, determine the canonical task identifier from the list below:

- a1: Run the datagen.py script to generate data files.
- a2: Format /data/format.md using Prettier.
- a3: Count the number of Wednesdays in /data/dates.txt and write the number to /data/dates-wednesdays.txt.
- a4: Sort the contacts in /data/contacts.json by last_name then first_name.
- a5: Write the first line of the 10 most recent .log files in /data/logs/ to /data/logs-recent.txt.
- a6: Create an index for Markdown files in /data/docs/ mapping each filename to its first H1.
- a7: Extract the sender’s email from /data/email.txt.
- a8: Extract the credit card number from /data/credit-card.png.
- a9: Find the most similar pair of comments in /data/comments.txt.
- a10: Calculate total sales of "Gold" tickets from /data/ticket-sales.db.

Return only the canonical task key (for example, "a3") if applicable, or "unknown" if none match.

Task description: "{task_desc}"
"""
    response = query_llm(prompt)
    task_key = response.strip().lower()
    return task_key

# ------------------ Task Functions for A1 to A10 ------------------
def run_a1():
    user_email = os.getenv("USER_EMAIL", "your.email@example.com")
    command = ["uv", "run", "https://raw.githubusercontent.com/sanand0/tools-in-data-science-public/tds-2025-01/project-1/datagen.py", user_email]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(result.stderr)
    return "A1 executed: Data generation script ran successfully."

def run_a2():
    command = ["prettier", "--write", "/data/format.md"]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(result.stderr)
    return "A2 executed: Markdown file formatted."

def run_a3():
    input_file = "/data/dates.txt"
    output_file = "dates-wednesdays.txt"
    date_formats = ["%d-%b-%Y", "%b %d, %Y", "%Y-%m-%d", "%Y/%m/%d %H:%M:%S"]
    wednesday_count = 0
    try:
        with open(input_file, "r") as f:
            lines = f.readlines()
    except Exception as e:
        raise Exception(f"Error reading {input_file}: {str(e)}")
    for line in lines:
        line = line.strip()
        parsed_date = None
        for fmt in date_formats:
            try:
                parsed_date = datetime.strptime(line, fmt)
                break
            except ValueError:
                continue
        if parsed_date and parsed_date.weekday() == 2:
            wednesday_count += 1
    write_output_file(output_file, str(wednesday_count))
    return f"A3 executed: Counted {wednesday_count} Wednesdays."

def run_a4():
    input_file = "/data/contacts.json"
    output_file = "contacts-sorted.json"
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            contacts = json.load(f)
        sorted_contacts = sorted(contacts, key=lambda c: (c.get("last_name", "").lower(), c.get("first_name", "").lower()))
        write_output_file(output_file, json.dumps(sorted_contacts))
        return "A4 executed: Contacts sorted."
    except Exception as e:
        raise Exception(f"A4 error: {str(e)}")

def run_a5():
    log_dir = "/data/logs"
    output_file = "logs-recent.txt"
    try:
        logs = []
        for filename in os.listdir(log_dir):
            if filename.endswith(".log"):
                path = os.path.join(log_dir, filename)
                mtime = os.path.getmtime(path)
                logs.append((mtime, path))
        logs = sorted(logs, key=lambda x: x[0], reverse=True)[:10]
        output_lines = []
        for _, path in logs:
            with open(path, "r", encoding="utf-8") as f:
                first_line = f.readline().strip()
                output_lines.append(first_line)
        write_output_file(output_file, "\n".join(output_lines))
        return "A5 executed: Recent logs processed."
    except Exception as e:
        raise Exception(f"A5 error: {str(e)}")

def run_a6():
    docs_dir = "/data/docs"
    index = {}
    try:
        for root, dirs, files in os.walk(docs_dir):
            for file in files:
                if file.endswith(".md"):
                    full_path = os.path.join(root, file)
                    with open(full_path, "r", encoding="utf-8") as f:
                        for line in f:
                            if line.strip().startswith("# "):
                                title = line.strip()[2:].strip()
                                relative_path = os.path.relpath(full_path, docs_dir)
                                index[relative_path] = title
                                break
        write_output_file("docs/index.json", json.dumps(index))
        return "A6 executed: Docs index created."
    except Exception as e:
        raise Exception(f"A6 error: {str(e)}")

def run_a7():
    input_file = "/data/email.txt"
    output_file = "email-sender.txt"
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        raise Exception(f"A7 error reading email.txt: {str(e)}")
    prompt = f"Extract the sender's email address from the following email message:\n\n{content}\n\nReturn only the email address."
    response = query_llm(prompt)
    write_output_file(output_file, response)
    return "A7 executed: Sender's email extracted."

def run_a8():
    input_file = "/data/credit-card.png"
    output_file = "credit-card.txt"
    try:
        with open(input_file, "rb") as f:
            img_data = f.read()
    except Exception as e:
        raise Exception(f"A8 error reading credit-card.png: {str(e)}")
    import base64
    img_b64 = base64.b64encode(img_data).decode("utf-8")
    prompt = f"Extract the credit card number from the following base64-encoded image data and return it without spaces:\n\n{img_b64}"
    response = query_llm(prompt)
    write_output_file(output_file, response)
    return "A8 executed: Credit card number extracted."

def run_a9():
    input_file = "/data/comments.txt"
    output_file = "comments-similar.txt"
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            comments = [line.strip() for line in f if line.strip()]
    except Exception as e:
        raise Exception(f"A9 error reading comments.txt: {str(e)}")
    prompt = "From the following list of comments, find the most similar pair and return them on two separate lines:\n\n" + "\n".join(comments)
    response = query_llm(prompt)
    write_output_file(output_file, response)
    return "A9 executed: Similar comments identified."

def run_a10():
    db_path = "/data/ticket-sales.db"
    output_file = "ticket-sales-gold.txt"
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT SUM(units * price) FROM tickets WHERE type = 'Gold'")
        result = cursor.fetchone()
        conn.close()
        total = str(result[0]) if result and result[0] is not None else "0"
    except Exception as e:
        raise Exception(f"A10 database error: {str(e)}")
    write_output_file(output_file, total)
    return "A10 executed: Gold ticket sales calculated."





def run_b5():
    db_path = "/data/sample.db"
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM sample_table")
        result = cursor.fetchone()
        conn.close()
        total = str(result[0]) if result and result[0] is not None else "0"
    except Exception as e:
        raise Exception("B5 error: " + str(e))
    write_output_file("sample-row-count.txt", total)
    return "B5 executed: SQL query processed."

def run_b6(url):
    import requests
    from bs4 import BeautifulSoup
    url = url
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        text = soup.get_text()
        write_output_file("webdata.txt", text)
        return "B6 executed: Website data scraped."
    else:
        raise Exception("B6 error: Website scrape failed.")

def run_b7():
    from PIL import Image
    input_image = "/data/credit-card.png"
    output_image = "credit-card-resized.png"
    try:
        with Image.open(input_image) as img:
            img = img.resize((int(img.width/2), int(img.height/2)))
            img.save(os.path.join("/data", output_image))
        return "B7 executed: Image resized."
    except Exception as e:
        raise Exception("B7 error: " + str(e))

def run_b8():
    return "B8 executed: Audio transcription simulated."

def run_b9():
    import markdown
    input_file = "/data/format.md"
    output_file = "format.html"
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            md_content = f.read()
        html_content = markdown.markdown(md_content)
        write_output_file(output_file, html_content)
        return "B9 executed: Markdown converted to HTML."
    except Exception as e:
        raise Exception("B9 error: " + str(e))

def run_b10():
    import csv
    output_rows = []
    input_file = "/data/sample.csv"
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("active", "").lower() == "true":
                    output_rows.append(row)
        write_output_file("filtered-sample.json", json.dumps(output_rows))
        return "B10 executed: CSV filtered to JSON."
    except Exception as e:
        raise Exception("B10 error: " + str(e))


TASK_MAP = {
    "a1": run_a1,
    "a2": run_a2,
    "a3": run_a3,
    "a4": run_a4,
    "a5": run_a5,
    "a6": run_a6,
    "a7": run_a7,
    "a8": run_a8,
    "a9": run_a9,
    "a10": run_a10,
    "b5": run_b5,
    "b6": run_b6,
    "b7": run_b7,
    "b8": run_b8,
    "b9": run_b9,
    "b10": run_b10,
}

@app.post("/run")
async def run_task(task_request: TaskRequest):
    # Get the free-text task description
    task_description = task_request.task.strip()
    # Use the LLM to parse the description into a canonical task key
    task_key = parse_task_description(task_description)
    if task_key not in TASK_MAP:
        raise HTTPException(status_code=400, detail=f"Unknown or unmapped task identifier: {task_key}")
    try:
        result_message = TASK_MAP[task_key]()
        return {"status": "success", "message": result_message}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/read")
async def read_file(path: str):
    file_path = os.path.join("/data", path)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return {"status": "success", "content": content}
    except Exception as e:  
        raise HTTPException(status_code=500, detail=str(e))
