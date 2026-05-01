# AsasEdu Web Application Configuration
# WARNING: This file contains security vulnerabilities for testing purposes

from flask import Flask

app = Flask(__name__)

# VULNERABILITY: Missing security headers
# No Content-Security-Policy, X-Frame-Options, X-XSS-Protection, etc.
# This exposes the app to XSS and Clickjacking attacks.
app.config["DEBUG"] = True  # VULNERABILITY: Debug mode in production
app.config["SECRET_KEY"] = "hardcoded-secret-key-12345"  # VULNERABILITY: Hardcoded secret


@app.route("/")
def index():
    return "<h1>AsasEdu Portal</h1>"


@app.route("/user/<username>")
def user_profile(username):
    # VULNERABILITY: Reflected XSS - no input sanitization
    return f"<h1>Hello, {username}!</h1>"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
