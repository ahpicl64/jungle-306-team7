from datetime import datetime
from flask import Blueprint, Flask, render_template, jsonify, request
from bson import ObjectId
from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
db = client.jungle7
challenges = db.challenges #챌린지 컬렉션
generate_routes = Blueprint('generate', __name__) # 블루프린트 생성



@generate_routes.route("/api/challenge", methods=["POST"])
def generate_challenge():
    data = request.json #파싱

    name_receive = data.get("name")
    start_date_receive = data.get("start_date")
    end_date_receive = data.get("end_date")
    details_receive = data.get("details")
    verification_method_receive = data.get("verification_method")
    bet_required_receive = data.get("bet_required")

    duration = get_duration(start_date_receive, end_date_receive)

    challenge_id = ObjectId()

    challenge = {
        "challenge_id": str(challenge_id),
        "name": name_receive,
        #   "host_user_id": host_user_id,
        "start_date": start_date_receive,
        "end_date": end_date_receive,
        "duration": duration,
        "details": details_receive,
        "verification_method": verification_method_receive,
        "bet_required": bet_required_receive,
        "participants": [],
    }

    db.challenges.insert_one(challenge)
    return jsonify({"result": "success"})


def get_duration(start_date_str, end_date_str):
    # str 형태의 날짜를 datetime으로 변환
    start_dt = datetime.strptime(start_date_str, '%Y-%m-%d')
    end_dt = datetime.strptime(end_date_str, '%Y-%m-%d')
    result = end_dt - start_dt

    return result.days
