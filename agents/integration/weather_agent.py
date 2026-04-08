import requests
from memory.vector_memory import store_memory


GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"


def clean_city_name(city):
    city = str(city).strip()

    noise_phrases = [
        "weather in",
        "weather for",
        "temperature in",
        "forecast for",
        "forecast in",
        "what is the weather in",
        "how is the weather in"
    ]

    city_lower = city.lower()
    for phrase in noise_phrases:
        if city_lower.startswith(phrase):
            city = city[len(phrase):].strip()
            break

    return city


def weather_code_to_text(code):
    weather_codes = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Fog",
        48: "Depositing rime fog",
        51: "Light drizzle",
        53: "Moderate drizzle",
        55: "Dense drizzle",
        56: "Light freezing drizzle",
        57: "Dense freezing drizzle",
        61: "Light rain",
        63: "Moderate rain",
        65: "Heavy rain",
        66: "Light freezing rain",
        67: "Heavy freezing rain",
        71: "Light snow",
        73: "Moderate snow",
        75: "Heavy snow",
        77: "Snow grains",
        80: "Light rain showers",
        81: "Moderate rain showers",
        82: "Violent rain showers",
        85: "Light snow showers",
        86: "Heavy snow showers",
        95: "Thunderstorm",
        96: "Thunderstorm with light hail",
        99: "Thunderstorm with heavy hail"
    }
    return weather_codes.get(code, "Unknown")


def get_coordinates(city):
    response = requests.get(
        GEOCODE_URL,
        params={"name": city, "count": 1},
        timeout=10
    )
    response.raise_for_status()

    data = response.json()
    if not data.get("results"):
        return None

    return data["results"][0]


def get_weather(city):
    try:
        city = clean_city_name(city)

        if not city:
            return "Please provide a city name."

        location = get_coordinates(city)
        if not location:
            return f"Sorry, I could not find weather data for {city}. Please check the city name."

        lat = location["latitude"]
        lon = location["longitude"]
        name = location["name"]
        country = location.get("country", "")
        admin1 = location.get("admin1", "")

        response = requests.get(
            WEATHER_URL,
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code,apparent_temperature",
                "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum",
                "timezone": "auto",
                "forecast_days": 3
            },
            timeout=10
        )
        response.raise_for_status()

        weather_data = response.json()
        current = weather_data.get("current", {})
        daily = weather_data.get("daily", {})

        temp = current.get("temperature_2m", "N/A")
        feels_like = current.get("apparent_temperature", "N/A")
        humidity = current.get("relative_humidity_2m", "N/A")
        wind = current.get("wind_speed_10m", "N/A")
        code = current.get("weather_code", -1)
        condition = weather_code_to_text(code)

        max_temps = daily.get("temperature_2m_max", [])
        min_temps = daily.get("temperature_2m_min", [])
        daily_codes = daily.get("weather_code", [])
        rain = daily.get("precipitation_sum", [])

        location_line = f"{name}, {admin1}, {country}" if admin1 else f"{name}, {country}"

        result = (
            f"Weather Report for {location_line}\n\n"
            f"Current Conditions:\n"
            f"Temperature: {temp}°C\n"
            f"Feels Like: {feels_like}°C\n"
            f"Condition: {condition}\n"
            f"Humidity: {humidity}%\n"
            f"Wind Speed: {wind} km/h\n\n"
            f"3-Day Forecast:\n"
        )

        day_names = ["Today", "Tomorrow", "Day 3"]
        for i in range(min(3, len(max_temps), len(min_temps))):
            day_condition = weather_code_to_text(daily_codes[i]) if i < len(daily_codes) else "Unknown"
            day_rain = rain[i] if i < len(rain) else 0
            result += (
                f"{day_names[i]}: High {max_temps[i]}°C / Low {min_temps[i]}°C | "
                f"{day_condition} | Rain: {day_rain} mm\n"
            )

        store_memory(
            f"Weather checked for {location_line}",
            {
                "type": "weather",
                "city": name,
                "country": country
            }
        )

        return result.strip()

    except requests.exceptions.Timeout:
        return "Weather service timed out. Please try again."
    except requests.exceptions.RequestException as e:
        return f"Could not fetch weather data due to a network issue: {str(e)}"
    except Exception as e:
        return f"Could not fetch weather data. Error: {str(e)}"