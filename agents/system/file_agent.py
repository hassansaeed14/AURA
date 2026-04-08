import os
import re
from groq import Groq
from config.settings import GROQ_API_KEY, MODEL_NAME
from memory.vector_memory import store_memory


client = Groq(api_key=GROQ_API_KEY)

SUPPORTED_TEXT_EXTENSIONS = {".txt", ".md", ".py", ".js", ".html", ".css", ".json"}
SUPPORTED_PDF_EXTENSIONS = {".pdf"}


def clean(text):
    if not text:
        return "I couldn't analyze the file right now."

    text = str(text)
    text = re.sub(r"\*{1,3}(.*?)\*{1,3}", r"\1", text)
    text = re.sub(r"#{1,6}\s*", "", text)
    text = re.sub(r"`{3}[\w]*\n?", "", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def summarize_content(content, file_type="Text Document"):
    try:
        content_preview = content[:4000]

        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are AURA File Agent. "
                        "Summarize file content clearly in plain text.\n\n"
                        "Structure:\n"
                        "FILE SUMMARY\n"
                        "FILE TYPE\n"
                        "MAIN CONTENT\n"
                        "KEY POINTS\n"
                        "CONCLUSION\n\n"
                        "Do not use markdown symbols like *, #, or backticks."
                    )
                },
                {
                    "role": "user",
                    "content": f"Summarize this {file_type} content:\n{content_preview}"
                }
            ],
            max_tokens=900,
            temperature=0.3
        )

        result = response.choices[0].message.content if response.choices else ""
        return clean(result)

    except Exception as e:
        return f"File summarization error: {str(e)}"


def read_text_file(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        if not content.strip():
            return f"The file is empty: {file_path}"

        store_memory(
            f"Text file read: {file_path}",
            {
                "type": "file",
                "file_path": file_path,
                "file_kind": "text"
            }
        )

        if len(content) > 3000:
            return summarize_content(content, "Text Document")

        return f"FILE CONTENT\n\n{content}"

    except UnicodeDecodeError:
        try:
            with open(file_path, "r", encoding="latin-1") as f:
                content = f.read()

            store_memory(
                f"Text file read with fallback encoding: {file_path}",
                {
                    "type": "file",
                    "file_path": file_path,
                    "file_kind": "text"
                }
            )

            if len(content) > 3000:
                return summarize_content(content, "Text Document")

            return f"FILE CONTENT\n\n{content}"

        except Exception as e:
            return f"Could not decode file: {str(e)}"

    except FileNotFoundError:
        return f"File not found: {file_path}"
    except Exception as e:
        return f"Could not read file: {str(e)}"


def read_pdf_file(file_path):
    try:
        import PyPDF2

        text = ""
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)

            for page in reader.pages[:10]:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"

        if not text.strip():
            return "Could not extract readable text from the PDF."

        store_memory(
            f"PDF file read: {file_path}",
            {
                "type": "file",
                "file_path": file_path,
                "file_kind": "pdf"
            }
        )

        return summarize_content(text, "PDF Document")

    except ImportError:
        return "PDF reading requires PyPDF2. Run: pip install PyPDF2"
    except FileNotFoundError:
        return f"File not found: {file_path}"
    except Exception as e:
        return f"Could not read PDF: {str(e)}"


def list_files(directory="."):
    try:
        files = os.listdir(directory)

        folders = sorted([f for f in files if os.path.isdir(os.path.join(directory, f))])
        file_list = sorted([f for f in files if os.path.isfile(os.path.join(directory, f))])

        result = f"FILES IN {directory}\n\n"

        if folders:
            result += "FOLDERS:\n"
            for folder in folders:
                result += f"  {folder}/\n"
            result += "\n"

        if file_list:
            result += "FILES:\n"
            for file_name in file_list:
                full_path = os.path.join(directory, file_name)
                size = os.path.getsize(full_path)
                result += f"  {file_name} ({size} bytes)\n"

        if not folders and not file_list:
            result += "No files or folders found."

        store_memory(
            f"Files listed in: {directory}",
            {
                "type": "file_list",
                "directory": directory
            }
        )

        return result.strip()

    except Exception as e:
        return f"Could not list files: {str(e)}"


def extract_file_path(command):
    command = command.strip()

    prefixes = [
        "read file",
        "open file",
        "analyze file",
        "read pdf",
        "read document"
    ]

    lowered = command.lower()
    for prefix in prefixes:
        if lowered.startswith(prefix):
            return command[len(prefix):].strip()

    return command


def analyze_file(file_path):
    file_path = extract_file_path(file_path)
    ext = os.path.splitext(file_path)[1].lower()

    if ext in SUPPORTED_PDF_EXTENSIONS:
        return read_pdf_file(file_path)

    if ext in SUPPORTED_TEXT_EXTENSIONS:
        return read_text_file(file_path)

    if not ext:
        return (
            "Please provide a valid file path with an extension.\n"
            "Supported: .pdf, .txt, .md, .py, .js, .html, .css, .json"
        )

    return (
        f"File type {ext} is not supported yet.\n"
        "Supported: .pdf, .txt, .md, .py, .js, .html, .css, .json"
    )