import os
import json
from groq import Groq
from config.settings import GROQ_API_KEY, MODEL_NAME

client = Groq(api_key=GROQ_API_KEY)

def read_text_file(file_path):
    print(f"\nAURA File Agent: reading {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Summarize if too long
        if len(content) > 3000:
            content_preview = content[:3000]
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are AURA File Agent. "
                            "Summarize the file content clearly. "
                            "Format:\n"
                            "FILE SUMMARY\n\n"
                            "FILE TYPE: Text Document\n"
                            "MAIN CONTENT:\n[Summary]\n\n"
                            "KEY POINTS:\n"
                            "1. [Point]\n"
                            "2. [Point]\n"
                            "3. [Point]"
                        )
                    },
                    {
                        "role": "user",
                        "content": f"Summarize this file content: {content_preview}"
                    }
                ],
                max_tokens=800
            )
            return response.choices[0].message.content
        
        return f"FILE CONTENT:\n\n{content}"
    
    except FileNotFoundError:
        return f"File not found: {file_path}"
    except Exception as e:
        return f"Could not read file: {str(e)}"

def read_pdf_file(file_path):
    print(f"\nAURA File Agent: reading PDF {file_path}")
    try:
        import PyPDF2
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            text = ""
            for page in reader.pages[:10]:
                text += page.extract_text()
        
        if not text:
            return "Could not extract text from PDF."
        
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are AURA File Agent. "
                        "Summarize the PDF content. "
                        "Format:\n"
                        "PDF SUMMARY\n\n"
                        "OVERVIEW:\n[Brief overview]\n\n"
                        "MAIN TOPICS:\n"
                        "1. [Topic]\n"
                        "2. [Topic]\n\n"
                        "KEY INFORMATION:\n[Important details]\n\n"
                        "CONCLUSION:\n[Main takeaway]"
                    )
                },
                {
                    "role": "user",
                    "content": f"Summarize this PDF: {text[:3000]}"
                }
            ],
            max_tokens=1000
        )
        return response.choices[0].message.content
    
    except ImportError:
        return "PDF reading requires PyPDF2. Run: pip install PyPDF2"
    except Exception as e:
        return f"Could not read PDF: {str(e)}"

def list_files(directory="."):
    print(f"\nAURA File Agent: listing {directory}")
    try:
        files = os.listdir(directory)
        result = f"FILES IN {directory}\n\n"
        
        folders = [f for f in files if os.path.isdir(os.path.join(directory, f))]
        file_list = [f for f in files if os.path.isfile(os.path.join(directory, f))]
        
        if folders:
            result += "FOLDERS:\n"
            for folder in folders:
                result += f"  {folder}/\n"
            result += "\n"
        
        if file_list:
            result += "FILES:\n"
            for file in file_list:
                size = os.path.getsize(os.path.join(directory, file))
                result += f"  {file} ({size} bytes)\n"
        
        return result
    
    except Exception as e:
        return f"Could not list files: {str(e)}"

def analyze_file(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext == '.pdf':
        return read_pdf_file(file_path)
    elif ext in ['.txt', '.md', '.py', '.js', '.html', '.css', '.json']:
        return read_text_file(file_path)
    else:
        return f"File type {ext} not supported yet. Supported: .pdf, .txt, .md, .py, .js, .html, .css, .json"