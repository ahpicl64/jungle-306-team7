from pymongo import MongoClient
from flask_bcrypt import Bcrypt
from flask import request
from bson import ObjectId

client = MongoClient("mongodb://localhost:27017/")
db = client.jungle7

bcrypt = Bcrypt() # Bcrypt 인스턴스 생성
users = db.users  # 유저 컬렉션
challenges = db.challenges # 챌린지 컬렉션

# 회원가입 시 유저 생성 및 비밀번호 해싱
def create_user(name, email, password, profile_image_url):
    # 비밀번호 암호화
    password_hash = bcrypt.generate_password_hash(password)

    user = {
        "name": name,
        "email": email,
        "password": password_hash,
        "profile_image": profile_image_url,  # 프로필 사진 필드 추가
        "joined_challenges": []
    }
    return users.insert_one(user).inserted_id # 유저 생성 후 ID 반환

# 이메일로 유저 찾기
def get_user_by_email(email):
    return users.find_one({"email": email})

# 로그인 검증 함수
def find_user(email, password):
  user = users.find_one({'email': email})

  if user and bcrypt.check_password_hash(user['password'], password):
      return user # 일치하면 유저 정보 반환
  else:
      return None # 로그인 실패 시 None 반환

# 접속 유저에 해당 challenge 추가
def join_challenge(challenge_id):
    # 1. 쿠키에서 user_id 가져오기
    user_id = request.cookies.get("user_id")
    if not user_id:
        return False

    # 2. 유저의 joined_challenges 업데이트
    users.update_one(
        {"_id": ObjectId(user_id)},
        {"$push": {"joined_challenges": {"challenge_id": challenge_id}}}
    )
    return True