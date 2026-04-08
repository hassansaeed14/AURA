import requests
from groq import Groq
from config.settings import GROQ_API_KEY, MODEL_NAME

client = Groq(api_key=GROQ_API_KEY)

def get_weather(city):
    print(f"\nAURA Weather Agent: {city}")
    
    try:
        # Using Open-Meteo free API (no key needed)
        # First get coordinates
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1"
        geo_response = requests.get(geo_url, timeout=10)
        geo_data = geo_response.json()
        
        if not geo_data.get('results'):
            return f"Sorry, I could not find weather data for {city}. Please check the city name."
        
        location = geo_data['results'][0]
        lat = location['latitude']
        lon = location['longitude']
        name = location['name']
        country = location.get('country', '')
        
        # Get weather data
        weather_url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}"
            f"&current=temperature_2m,relative_humidity_2m,"
            f"wind_speed_10m,weather_code,apparent_temperature"
            f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum"
            f"&timezone=auto&forecast_days=3"
        )
        
        weather_response = requests.get(weather_url, timeout=10)
        weather_data = weather_response.json()
        
        current = weather_data['current']
        daily = weather_data['daily']
        
        temp = current['temperature_2m']
        feels_like = current['apparent_temperature']
        humidity = current['relative_humidity_2m']
        wind = current['wind_speed_10m']
        
        # Weather code to description
        weather_codes = {
            0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy",
            3: "Overcast", 45: "Foggy", 51: "Light drizzle",
            61: "Light rain", 63: "Moderate rain", 65: "Heavy rain",
            71: "Light snow", 73: "Moderate snow", 75: "Heavy snow",
            80: "Rain showers", 95: "Thunderstorm"
        }
        
        code = current['weather_code']
        condition = weather_codes.get(code, "Unknown")
        
        result = (
            f"Weather Report for {name}, {country}\n\n"
            f"Current Conditions:\n"
            f"Temperature: {temp}°C (Feels like {feels_like}°C)\n"
            f"Condition: {condition}\n"
            f"Humidity: {humidity}%\n"
            f"Wind Speed: {wind} km/h\n\n"
            f"3-Day Forecast:\n"
            f"Today: High {daily['temperature_2m_max'][0]}°C / Low {daily['temperature_2m_min'][0]}°C\n"
            f"Tomorrow: High {daily['temperature_2m_max'][1]}°C / Low {daily['temperature_2m_min'][1]}°C\n"
            f"Day 3: High {daily['temperature_2m_max'][2]}°C / Low {daily['temperature_2m_min'][2]}°C\n"
        )
        
        return result
        
    except Exception as e:
        return f"Could not fetch weather data. Error: {str(e)}"