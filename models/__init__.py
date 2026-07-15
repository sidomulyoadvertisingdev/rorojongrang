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
from models.data_upload import DataUpload
from models.data_record import DataRecord
from models.activity_log import ActivityLog
from models.feedback import Feedback
from models.team_board import TeamBoard
from models.board_column import BoardColumn
from models.board_task import BoardTask
from models.task_checklist import TaskChecklist
from models.task_activity import TaskActivity
from models.lead_pipeline import LeadPipeline
from models.lead_activity import LeadActivity
from models.followup import FollowUp
from models.campaign import Campaign, CampaignMetric
from models.user_drive_token import UserDriveToken
from models.task_attachment import TaskAttachment
from models.campaign_attachment import CampaignAttachment
