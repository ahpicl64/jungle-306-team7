import datetime
import os
import uuid
from bson import ObjectId
from flask import Blueprint, request, jsonify, make_response
from flask_jwt_extended import create_access_token, set_access_cookies
from flask_jwt_extended import jwt_required
from models.user_model import create_user, get_user_by_email, find_user, search_user

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


UPLOAD_FOLDER = "static/profiles" # 프로필 사진을 업로드할 폴더 지정
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"} # 허용할 파일 확장자

# 폴더가 없으면 생성
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# 확장자 체크 함수
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# === Sign Up (회원가입) API ===
@auth_routes.route("/api/signup", methods=['POST'])
def signup_proc():
    name = request.form.get("name")
    email = request.form.get("email")
    password = request.form.get("password")

    if get_user_by_email(email):
        return jsonify({"result": "fail", "message": "이미 존재하는 이메일입니다!"})

    # 파일 업로드 처리
    profile_image = request.files.get("profile_image")
    if profile_image and allowed_file(profile_image.filename):
        # 파일 확장자 추출
        ext = profile_image.filename.rsplit(".", 1)[-1]
    
        # 랜덤한 파일명 생성 (UUID 사용) -> 한글 제거
        filename = f"{uuid.uuid4().hex}.{ext}"
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        
        # 파일 저장
        profile_image.save(file_path)
        db_path = f'/static/profiles/{filename}'
    else:
        db_path = "/static/logo.png" # 기본 프로필 이미지

    # 유저 생성 (프로필 이미지 포함)
    user_id = create_user(name, email, password, db_path)

    return jsonify({"result": "success", "user_id": str(user_id)})

# === 참여한 챌린지 추가 API ===
# @auth_routes.route("/api/user-challenge/join", methods=['POST'])
# # @jwt_required()
# def join_challenge_proc():
#     challenge_id = request.json.get('challenge_id')
    
#     if challenge_id and join_challenge(challenge_id):
#         return jsonify({"result": "success", "message": "챌린지 참여 완료!"})

# === 유저의 id를 받으면 유저 이름을 반환하는 함수 ===
@auth_routes.route("/api/user/<user_id>", methods=['GET'])
# @jwt_required()
def get_user_info(user_id):
    user = search_user(user_id)

    if user:
        return jsonify({"result": "success", "name": user.get("name", "알 수 없음")})
    else:
        return jsonify({"result": "fail", "message": "사용자를 찾을 수 없습니다."}), 404