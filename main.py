from app import app
from routes import init_app
from dotenv import load_dotenv

init_app()

# Load variables from .env file
load_dotenv()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=True)
