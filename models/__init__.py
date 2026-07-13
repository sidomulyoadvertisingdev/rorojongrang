from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message_category = "info"

from models.user import User
from models.task import ScrapingTask
from models.business import Business
from models.wa_template import WaTemplate
from models.wa_link import WaLink
from models.wa_click import WaClick
