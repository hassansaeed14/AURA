import requests
from groq import Groq
from config.settings import GROQ_API_KEY, MODEL_NAME

client = Groq(api_key=GROQ_API_KEY)

def convert_currency(amount, from_currency, to_currency):
    print(f"\nAURA Currency Agent: {amount} {from_currency} to {to_currency}")

    try:
        # Free currency API
        url = f"https://api.exchangerate-api.com/v4/latest/{from_currency.upper()}"
        response = requests.get(url, timeout=10)
        data = response.json()

        if 'rates' in data:
            rate = data['rates'].get(to_currency.upper())
            if rate:
                result = float(amount) * rate
                return (
                    f"Currency Conversion\n\n"
                    f"{amount} {from_currency.upper()} = {result:.2f} {to_currency.upper()}\n\n"
                    f"Exchange Rate: 1 {from_currency.upper()} = {rate:.4f} {to_currency.upper()}\n"
                    f"Last Updated: {data.get('date', 'Today')}"
                )

    except:
        pass

    # Fallback to AI
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are AURA Currency Agent. "
                    "Provide currency conversion information. "
                    "Give approximate rates and explain the conversion. "
                    "No markdown symbols."
                )
            },
            {
                "role": "user",
                "content": f"Convert {amount} {from_currency} to {to_currency}"
            }
        ],
        max_tokens=300
    )
    return response.choices[0].message.content

def get_crypto_price(crypto):
    print(f"\nAURA Currency Agent: {crypto} price")
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={crypto.lower()}&vs_currencies=usd,pkr"
        response = requests.get(url, timeout=10)
        data = response.json()

        if data:
            coin_data = list(data.values())[0]
            usd = coin_data.get('usd', 'N/A')
            pkr = coin_data.get('pkr', 'N/A')
            return (
                f"Crypto Price: {crypto.upper()}\n\n"
                f"USD: ${usd:,.2f}\n"
                f"PKR: Rs {pkr:,.2f}\n\n"
                f"Data from CoinGecko"
            )
    except:
        pass

    return client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": f"What is current price of {crypto}?"}],
        max_tokens=200
    ).choices[0].message.content