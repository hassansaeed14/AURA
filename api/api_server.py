from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from brain.core_ai import process_command
from memory.memory_manager import save_chat, load_chat_history
import uvicorn

app = FastAPI()

app.mount("/static", StaticFiles(directory="interface/web"), name="static")

class Command(BaseModel):
    text: str

@app.get("/", response_class=HTMLResponse)
async def home():
    with open("interface/web/index.html", "r") as f:
        return f.read()

@app.post("/chat")
async def chat(command: Command):
    intent, response = process_command(command.text)
    save_chat(command.text, response)
    return {"intent": intent, "response": response}

@app.get("/history")
async def history():
    return load_chat_history()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)