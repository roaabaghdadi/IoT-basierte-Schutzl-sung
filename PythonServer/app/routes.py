
from flask import Blueprint, request, jsonify, render_template, session, redirect, url_for
from app import db
from app.models import SensorData, User, Alert
from config import Config
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta

main_bp = Blueprint('main', __name__)


@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()

        if user and user.password == password:
            session['user_id'] = user.id
            return redirect('/')
        else:
            return render_template('login.html', error='Invalid email or password')

    return render_template('login.html')


@main_bp.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect('/login')


@main_bp.route('/')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')
    twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
    SensorData.query.filter(SensorData.timestamp < twenty_four_hours_ago).delete()
    db.session.commit()
    latest_data = SensorData.query.order_by(SensorData.timestamp.desc()).limit(100).all()
    return render_template('index.html', data=latest_data)


@main_bp.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'user_id' not in session:
        return redirect('/login')

    if request.method == 'POST':
        alert_type = request.form['alert_type']
        threshold = float(request.form['threshold'])
        sensor_type = request.form['sensor_type']
        user_id = session['user_id']

        new_alert = Alert(
            alert_type=alert_type,
            threshold_value=threshold,
            sensor_type=sensor_type,
            user_id=user_id
        )

        # Set email or URL based on the alert_type
        if alert_type == 'email':
            new_alert.email = request.form['email']
        else:  # url
            new_alert.url = request.form['url']

        db.session.add(new_alert)
        db.session.commit()

        return redirect('/settings')

    user_alerts = Alert.query.filter_by(user_id=session['user_id']).all()
    return render_template('settings.html', alerts=user_alerts)


@main_bp.route('/settings/delete/<int:alert_id>', methods=['POST'])
def delete_alert(alert_id):
    if 'user_id' not in session:
        return redirect('/login')

    alert = Alert.query.get_or_404(alert_id)

    if alert.user_id != session['user_id']:
        return jsonify({"status": "error", "message": "Unauthorized"}), 403

    db.session.delete(alert)
    db.session.commit()

    return redirect('/settings')


def send_alert_email(alert_email, sensor_type, value, unit, threshold):
    """
    Send email notification when sensor value exceeds threshold
    """
    try:
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        sender_email = Config.GMAIL_EMAIL
        sender_password = Config.GMAIL_APP_PASSWORD

        message = MIMEMultipart("alternative")
        message["Subject"] = f"🚨 IoT Safety Alert - {sensor_type} Threshold Exceeded"
        message["From"] = sender_email
        message["To"] = alert_email

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #ff4757; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                .content {{ background: #f9f9f9; padding: 20px; border: 1px solid #ddd; }}
                .alert-box {{ background: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin: 20px 0; }}
                .value {{ font-size: 24px; font-weight: bold; color: #ff4757; }}
                .threshold {{ font-size: 18px; color: #666; }}
                .footer {{ background: #f1f2f6; padding: 15px; text-align: center; border-radius: 0 0 5px 5px; font-size: 12px; color: #666; }}
                .action-button {{ display: inline-block; background: #3742fa; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin: 10px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🚨 SAFETY ALERT</h1>
                    <p>IoT Safety System - Your Threshold Exceeded</p>
                </div>
                <div class="content">
                    <h2>⚠️ Immediate Attention Required</h2>
                    <p>A sensor reading has exceeded your configured safety threshold:</p>

                    <div class="alert-box">
                        <h3>{sensor_type}</h3>
                        <p>Current Reading: <span class="value">{value} {unit}</span></p>
                        <p>Your Threshold: <span class="threshold">{threshold} {unit}</span></p>
                        <p><strong>Exceeded by: {value - threshold:.2f} {unit}</strong></p>
                        <p><strong>Status: CRITICAL</strong></p>
                    </div>

                    <p><strong>Recommended Actions:</strong></p>
                    <ul>
                        <li>Check the affected area immediately</li>
                        <li>Ensure proper ventilation if gas-related</li>
                        <li>Evacuate if necessary</li>
                        <li>Contact emergency services if danger is imminent</li>
                    </ul>

                    <a href="http://your-domain.com/settings" class="action-button">Adjust Your Settings</a>
                </div>
                <div class="footer">
                    <p>This is an automated message from IoT Safety System</p>
                    <p>You are receiving this because you configured an alert for {sensor_type} with threshold {threshold}{unit}</p>
                    <p>Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
            </div>
        </body>
        </html>
        """

        message.attach(MIMEText(html_content, "html"))

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, alert_email, message.as_string())

        print(f"Alert email sent to {alert_email} for {sensor_type}")
        return True

    except Exception as e:
        print(f"Failed to send email: {str(e)}")
        return False


def send_alert_url(alert_url, sensor_type, value, unit, threshold):
    """
    Send alert notification to a URL endpoint (webhook)
    """
    try:
        payload = {
            "alert_type": "sensor_threshold_exceeded",
            "sensor_type": sensor_type,
            "current_value": value,
            "unit": unit,
            "threshold": threshold,
            "exceeded_by": value - threshold,
            "status": "critical",
            "timestamp": datetime.now().isoformat()
        }

        response = requests.post(
            alert_url,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )

        response.raise_for_status()

        print(f"Alert sent to URL {alert_url} for {sensor_type}")
        return True

    except requests.exceptions.RequestException as e:
        print(f"Error sending alert to URL {alert_url}: {str(e)}")
        return False


@main_bp.route('/api/data', methods=['POST'])
def receive_data():
    data = request.get_json()
    if not data or 'temperature' not in data or 'gas_level' not in data:
        return jsonify({"status": "error", "message": "Invalid data"}), 400

    all_alerts = Alert.query.all()

    temp_thresholds = []
    humidity_thresholds = []
    gas_thresholds = []
    co_thresholds = []

    for alert in all_alerts:
        if alert.sensor_type == 'DHT11_Temp':
            temp_thresholds.append(alert.threshold_value)
        elif alert.sensor_type == 'DHT11_Humidity':
            humidity_thresholds.append(alert.threshold_value)
        elif alert.sensor_type == 'MQ2':
            gas_thresholds.append(alert.threshold_value)
        elif alert.sensor_type == 'MQ2_CO':
            co_thresholds.append(alert.threshold_value)


    temp_threshold = min(temp_thresholds) if temp_thresholds else Config.TEMP_THRESHOLD
    humidity_threshold = min(humidity_thresholds) if humidity_thresholds else Config.HUMIDITY_THRESHOLD
    gas_threshold = min(gas_thresholds) if gas_thresholds else Config.GAS_THRESHOLD
    co_threshold = min(co_thresholds) if co_thresholds else Config.CO_THRESHOLD

    # Temperature data
    temp_value = float(data['temperature'])
    temp_status = 'critical' if temp_value > temp_threshold else 'normal'
    temp_entry = SensorData(sensor_type='DHT11_Temp', value=temp_value, unit='°C', status=temp_status)
    db.session.add(temp_entry)

    humidity_value = float(data['humidity'])
    humidity_status = 'critical' if humidity_value > humidity_threshold else 'normal'
    humidity_entry = SensorData(sensor_type='DHT11_Humidity', value=humidity_value, unit='%', status=humidity_status)
    db.session.add(humidity_entry)

    gas_value = float(data['gas_level'])
    gas_status = 'critical' if gas_value > gas_threshold else 'normal'
    gas_entry = SensorData(sensor_type='MQ2', value=gas_value, unit='ppm', status=gas_status)
    db.session.add(gas_entry)

    co_value = float(data['co_ppm'])
    co_status = 'critical' if co_value > co_threshold else 'normal'
    co_entry = SensorData(sensor_type='MQ2_CO', value=co_value, unit='ppm', status=co_status)
    db.session.add(co_entry)

    db.session.commit()

    sensors_to_check = [
        ('DHT11_Temp', temp_value, '°C', temp_status),
        ('DHT11_Humidity', humidity_value, '%', humidity_status),
        ('MQ2', gas_value, 'ppm', gas_status),
        ('MQ2_CO', co_value, 'ppm', co_status)
    ]

    for sensor_type, value, unit, status in sensors_to_check:
        if status == 'critical':
            sensor_alerts = Alert.query.filter_by(sensor_type=sensor_type).all()

            for alert in sensor_alerts:
                if value > alert.threshold_value:
                    if alert.alert_type == 'email' and alert.email:
                        send_alert_email(
                            alert_email=alert.email,
                            sensor_type=sensor_type,
                            value=value,
                            unit=unit,
                            threshold=alert.threshold_value
                        )
                    elif alert.alert_type == 'url' and alert.url:
                        send_alert_url(
                            alert_url=alert.url,
                            sensor_type=sensor_type,
                            value=value,
                            unit=unit,
                            threshold=alert.threshold_value
                        )

            print(f"ALARM! Critical value detected for {sensor_type}: {value} {unit}")

    return jsonify({"status": "success"}), 201