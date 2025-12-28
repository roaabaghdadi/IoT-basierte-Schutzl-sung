from flask import Flask, request, jsonify, render_template
from datetime import datetime
import json

app = Flask(__name__)

# In-memory storage for alerts (in production, you'd use a database)
alerts = []

@app.route('/')
def index():
    """Display all received alerts"""
    return render_template('alerts.html', alerts=alerts[::-1])
@app.route('/api/alert', methods=['POST'])
def receive_alert():
    """Receive alert from the main IoT system"""
    if not request.is_json:
        return jsonify({"status": "error", "message": "Request must be JSON"}), 400

    data = request.get_json()

    # Add timestamp if not provided
    if 'timestamp' not in data:
        data['timestamp'] = datetime.now().isoformat()

    # Add the alert to our storage
    alerts.append(data)

    # Keep only the last 50 alerts to avoid memory issues
    if len(alerts) > 50:
        alerts.pop(0)

    # Log the alert
    print(f"Received alert: {json.dumps(data, indent=2)}")

    return jsonify({"status": "success", "message": "Alert received"}), 201

@app.route('/api/alerts', methods=['GET'])
def get_alerts():
    """Return all alerts as JSON"""
    return jsonify(alerts)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)