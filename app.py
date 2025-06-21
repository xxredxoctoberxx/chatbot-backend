from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from openai import OpenAI
from config import config
import os
import uuid
import logging
from datetime import datetime

# Load environment + select config
env = os.getenv("FLASK_ENV", "default")
app = Flask(__name__)
app.config.from_object(config[env])

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("chatbot")

# Enable CORS and WebSockets
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize OpenAI
client = OpenAI(api_key=app.config["OPENAI_API_KEY"])
MODEL_NAME = app.config["OPENAI_MODEL"]

def system_message():
    return {
        "role": "system",
        "content": "You are a helpful, friendly AI assistant. Provide concise, accurate, and helpful responses to user queries."
    }

def get_openai_response(messages):
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            max_tokens=1000,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error("OpenAI API error: %s", e)
        raise

@app.route("/api/chat", methods=["POST"])
def chat_api():
    try:
        data = request.get_json()
        messages = data.get("messages", [])

        if not messages:
            return jsonify({"error": "No messages provided"}), 400

        if not any(m["role"] == "system" for m in messages):
            messages.insert(0, system_message())

        reply = get_openai_response(messages)

        return jsonify({
            "message": {
                "id": str(uuid.uuid4()),
                "role": "assistant",
                "content": reply,
                "timestamp": datetime.utcnow().isoformat()
            }
        })

    except Exception as e:
        logger.exception("Error in /api/chat")
        return jsonify({"error": str(e)}), 500

@socketio.on("connect")
def on_connect():
    logger.info("Socket connected")
    emit("status", {"message": "Connected"})

@socketio.on("disconnect")
def on_disconnect():
    logger.info("Socket disconnected")

@socketio.on("chat_message")
def handle_socket_chat(data):
    try:
        messages = data.get("messages", [])
        if not messages:
            emit("error", {"message": "No messages provided"})
            return

        if not any(m["role"] == "system" for m in messages):
            messages.insert(0, system_message())

        reply = get_openai_response(messages)

        emit("chat_response", {
            "message": {
                "id": str(uuid.uuid4()),
                "role": "assistant",
                "content": reply,
                "timestamp": datetime.utcnow().isoformat()
            }
        })

    except Exception as e:
        logger.exception("WebSocket error")
        emit("error", {"message": str(e)})

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    port = app.config["PORT"]
    socketio.run(app, host="0.0.0.0", port=port)
