from flask import Blueprint
api_v1_blueprint = Blueprint("api_v1", __name__)

from app.api.v1 import auth 
from app.api.v1 import notes
from app.api.v1 import shares
from app.api.v1 import query
from app.api.v1 import upload