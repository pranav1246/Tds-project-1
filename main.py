import os
import json
import subprocess
import tempfile
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import openai
import uvicorn
import jsonschema

app = FastAPI()

class TaskRequest(BaseModel):
    task: str

# JSON schema for expected output
OUTPUT_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "TaskOutput",
    "type": "object",
    "properties": {
        "status": {"type": "string", "enum": ["success", "failure"]},
        "result": {"type": "string"}
    },
    "required": ["status", "result"]
}

# Global system message with all instructions
SYSTEM_MESSAGE = """
You are a Python coding assistant for DataWorks automation tasks.
Generate self-contained Python code that performs the given task exactly as described.
The code must:
  - Only access files under the /data directory.
  - Use external commands (e.g., via subprocess) if needed.
  - Not delete any files.
  - Print a JSON object as its final output (and nothing else) that conforms to this schema:
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "TaskOutput",
  "type": "object",
  "properties": {
    "status": {"type": "string", "enum": ["success", "failure"]},
    "result": {"type": "string"}
  },
  "required": ["status", "result"]
}
Keep this context for all tasks.
"""

# Set the OpenAI API key from environment variable AIPROXY_TOKEN
api_key = os.getenv("AIPROXY_TOKEN")

if not api_key:
    raise ValueError("AIPROXY_TOKEN environment variable is not set.")

client = openai.OpenAI(api_key=api_key)


def generate_code(task: str, error_context: str = None) -> str:
    """
    Calls the LLM (GPT-4o-Mini) with the system instructions and minimal user prompt.
    If error_context is provided (from a previous failed attempt), it is appended.
    """
    if error_context:
        user_message = f"Task: {task}\nError: {error_context}"
    else:
        user_message = f"Task: {task}"
    response =  client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_MESSAGE},
            {"role": "user", "content": user_message}
        ],
        max_tokens=800,
    )
    code = response.choices[0].message.content.strip()
    return code

@app.post("/run")
async def run_task(task_request: TaskRequest):
    task = task_request.task.strip()
    max_attempts = 3
    attempt = 0
    error_message = ""
    generated_code = None

    while attempt < max_attempts:
        try:
            generated_code = generate_code(task, error_context=error_message if attempt > 0 else None)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"LLM code generation failed: {e}")

        # Write the generated code to a temporary file.
        try:
            with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w", encoding="utf-8") as tmp:
                tmp.write(generated_code)
                tmp_file_path = tmp.name
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to write generated code to file: {e}")

        # Execute the generated code.
        try:
            result = subprocess.run(["python3", tmp_file_path], capture_output=True, text=True, timeout=60)
            output = result.stdout.strip()
            err_output = result.stderr.strip()
        except Exception as e:
            os.remove(tmp_file_path)
            raise HTTPException(status_code=500, detail=f"Error executing generated code: {e}")
        finally:
            os.remove(tmp_file_path)

        # Check if execution was successful by validating output JSON.
        if result.returncode == 0:
            try:
                output_json = json.loads(output)
                jsonschema.validate(instance=output_json, schema=OUTPUT_SCHEMA)
                return {"status": "success", "generated_code": generated_code, "output": output_json}
            except (json.JSONDecodeError, jsonschema.ValidationError) as ve:
                error_message = f"Output JSON error: {ve}. StdErr: {err_output}"
        else:
            error_message = f"Non-zero return code {result.returncode}. StdErr: {err_output}"
        attempt += 1

    raise HTTPException(
        status_code=500,
        detail=f"Task failed after {max_attempts} attempts. Last error: {error_message}. Generated code: {generated_code}"
    )

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

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
