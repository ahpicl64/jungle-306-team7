from flask import Blueprint, request, jsonify
from bson import ObjectId
from flask_jwt_extended import create_access_token
from models.user_model import create_user, get_user_by_email, find_user
import datetime

auth_routes = Blueprint('auth', __name__)  # 블루프린트 생성

# === Sign In (로그인) API ===
@auth_routes.route("/api/signin", methods=['POST'])
def signin_proc():
    user_id = request.json.get('email')  # JSON 방식으로 받음
    user_pw = request.json.get('password')

    user_info = find_user(user_id, user_pw)

    if user_info:
        access_token = create_access_token(identity=str(user_info['_id']), expires_delta=datetime.timedelta(hours=2)) # 만료 시간(2시간 후)
        return jsonify({
            'result': "success",
            'access_token': access_token,
            'name': user_info['name'],
            'user_id': str(user_info['_id'])
        })
    else:
        return jsonify({'result': "failure"})


# === Sign Up (회원가입) API ===
@auth_routes.route("/api/signup", methods=['POST'])
def signup_proc():
    data = request.json
    if get_user_by_email(data["email"]):
        return jsonify({"result": "fail", "message": "이미 존재하는 이메일입니다!"})

    user_id = create_user(data["name"], data["email"], data["password"])
    return jsonify({"result": "success", "user_id": str(user_id)})