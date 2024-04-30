from dash import Dash

def create_app():
    """Create and return a Dash application."""
    app = Dash(__name__)
    app.title = 'Trade Network'

    from .layout import init_layout
    from .callbacks import register_callbacks

    init_layout(app)
    register_callbacks(app)

    return app
