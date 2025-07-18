from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from openai import OpenAI
from config import config
import os
import uuid
import logging
from datetime import datetime
import eventlet

'''Personal AI Assistant Chatbot Flask-Backend Service
By: daniliser95@gmail.com
Important notes for deployment:
1. Make sure you use python == 3.10.13
2. Run Command: gunicorn app:app --worker-class eventlet -w 1 --bind 0.0.0.0:$PORT
3. Render default PORT == 10000
4. use eventlet.monkey_patch()
5. use dnspython==2.4.2 to solve flask-openai connection issues
'''

# Monkey Patch 
eventlet.monkey_patch()

# Environment & Configurations
env = os.getenv("FLASK_ENV", "default")
app = Flask(__name__)
app.config.from_object(config[env])

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("chatbot")

CORS(app)
socketio = SocketIO(app, async_mode='eventlet', cors_allowed_origins="*")

client = OpenAI(api_key=app.config["OPENAI_API_KEY"])
MODEL_NAME = app.config["OPENAI_MODEL"]

with open("system_prompt.txt", "r", encoding="utf-8") as f:
    system_prompt = f.read().strip()

def system_message():
    return {
        "role": "system",
        "content": system_prompt
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
    port = int(os.environ.get("PORT", 10000))
    socketio.run(app, host="0.0.0.0", port=port)
