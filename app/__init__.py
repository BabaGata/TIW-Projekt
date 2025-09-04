from flask import Flask

def create_app():
    app = Flask(__name__)
    app.config.from_object("config.Config")

    # Import and register routes
    from . import routes
    app.register_blueprint(routes.bp)   # <--- THIS LINE WAS MISSING

    return app