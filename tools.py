import httpx

from db import SessionLocal
import models

# Turn Open-Meteo's numeric weather code into a readable word
def describe(code):
    if code == 0:
        return "clear sky"
    if code in (1, 2, 3):
        return "partly cloudy"
    if code in (45, 48):
        return "foggy"
    if 51 <= code <= 67:
        return "rainy"
    if 71 <= code <= 77:
        return "snowy"
    if 80 <= code <= 82:
        return "rain showers"
    if code >= 95:
        return "thunderstorm"
    return "unknown"


def get_weather(city):
    try:
        # Step 1: look up the city's latitude/longitude
        geo = httpx.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1},
            timeout=10,
        ).json()
        if not geo.get("results"):
            return {"error": f"Could not find a city called {city}"}
        place = geo["results"][0]

        # Step 2: get the current weather at those coordinates
        current = httpx.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": place["latitude"],
                "longitude": place["longitude"],
                "current": "temperature_2m,weather_code",
            },
            timeout=10,
        ).json()["current"]

        return {
            "city": place["name"],
            "country": place.get("country"),
            "temp_c": current["temperature_2m"],
            "condition": describe(current["weather_code"]),
        }
    except httpx.HTTPError:
        return {"error": "The weather service could not be reached"}


def calculate(a, b, operation):
    if operation == "add":
        return {"result": a + b}
    if operation == "subtract":
        return {"result": a - b}
    if operation == "multiply":
        return {"result": a * b}
    if operation == "divide":
        if b == 0:
            return {"error": "Cannot divide by zero"}
        return {"result": a / b}
    return {"error": f"Unknown operation {operation}"}

def convert_currency(amount, from_currency, to_currency):
    try:
        data = httpx.get(
            f"https://open.er-api.com/v6/latest/{from_currency.upper()}",
            timeout=10,
        ).json()
        if data.get("result") != "success":
            return {"error": f"Unknown currency {from_currency}"}

        rate = data["rates"].get(to_currency.upper())
        if rate is None:
            return {"error": f"Unknown currency {to_currency}"}

        return {
            "amount": amount,
            "from": from_currency.upper(),
            "to": to_currency.upper(),
            "rate": rate,
            "converted": round(amount * rate, 2),
        }
    except (httpx.HTTPError, ValueError):
        return {"error": "The exchange rate service could not be reached"}


def save_note(content, user_id):
    with SessionLocal() as db:
        note = models.Note(user_id=user_id, content=content)
        db.add(note)
        db.commit()
        return {"saved": True, "note_id": note.id}


def list_notes(user_id, limit=20):
    with SessionLocal() as db:
        rows = (
            db.query(models.Note)
            .filter(models.Note.user_id == user_id)
            .order_by(models.Note.id.desc())
            .limit(limit)
            .all()
        )
        return {
            "notes": [
                {"id": n.id, "content": n.content, "created_at": n.created_at.isoformat()}
                for n in rows
            ]
        }


# The menu we show the model
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get the current weather for a city",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City name, e.g. Cairo"}
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Do exact arithmetic on two numbers",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {"type": "number", "description": "The first number"},
                    "b": {"type": "number", "description": "The second number"},
                    "operation": {
                        "type": "string",
                        "enum": ["add", "subtract", "multiply", "divide"],
                        "description": "The operation to perform",
                    },
                },
                "required": ["a", "b", "operation"],
            },
        },
    },

        {
        "type": "function",
        "function": {
            "name": "convert_currency",
            "description": "Convert an amount of money from one currency to another using current exchange rates",
            "parameters": {
                "type": "object",
                "properties": {
                    "amount": {"type": "number", "description": "The amount of money to convert"},
                    "from_currency": {"type": "string", "description": "3-letter currency code to convert from, e.g. USD"},
                    "to_currency": {"type": "string", "description": "3-letter currency code to convert to, e.g. EGP"},
                },
                "required": ["amount", "from_currency", "to_currency"],
            },
        },
    },

        {
        "type": "function",
        "function": {
            "name": "save_note",
            "description": "Save a note for the user so they can read it later",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "The text of the note to save"}
                },
                "required": ["content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_notes",
            "description": "Show the user's saved notes, newest first",
            "parameters": {"type": "object", "properties": {}},
        },
    }
]

# Map tool names to the real Python functions
AVAILABLE_TOOLS = {"get_weather": get_weather,
                    "calculate": calculate,
                    "convert_currency": convert_currency,
                    "save_note": save_note,
                    "list_notes": list_notes}