import os
import datetime
from groq import Groq
from config.settings import GROQ_API_KEY, MODEL_NAME

client = Groq(api_key=GROQ_API_KEY)

def take_screenshot(filename=None):
    print(f"\nAURA Screenshot Agent: taking screenshot")
    try:
        import pyautogui
        
        if not filename:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
        
        screenshot = pyautogui.screenshot()
        screenshot.save(filename)
        
        return (
            f"SCREENSHOT TAKEN\n\n"
            f"File: {filename}\n"
            f"Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Location: {os.path.abspath(filename)}\n\n"
            f"Screenshot saved successfully!"
        )
    
    except ImportError:
        return "Screenshot requires pyautogui. Run: pip install pyautogui"
    except Exception as e:
        return f"Could not take screenshot: {str(e)}"

def take_region_screenshot(x, y, width, height, filename=None):
    try:
        import pyautogui
        
        if not filename:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"region_{timestamp}.png"
        
        screenshot = pyautogui.screenshot(region=(x, y, width, height))
        screenshot.save(filename)
        
        return f"Region screenshot saved: {filename}"
    
    except ImportError:
        return "Screenshot requires pyautogui. Run: pip install pyautogui"
    except Exception as e:
        return f"Could not take screenshot: {str(e)}"