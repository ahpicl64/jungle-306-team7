from datetime import datetime
from flask import Blueprint, Flask, render_template, jsonify, request
from bson import ObjectId
from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
db = client.jungle7
challenges = db.challenges  # 챌린지 컬렉션
challenge_routes = Blueprint("challenge", __name__)  # 블루프린트 생성


@challenge_routes.route("/api/challenge", methods=["POST"])
def generate_challenge():
    data = request.json  # 파싱

    name_receive = data.get("name")
    start_date_receive = data.get("start_date")
    end_date_receive = data.get("end_date")
    details_receive = data.get("details")
    verification_method_receive = data.get("verification_method")
    bet_required_receive = data.get("bet_required")

    duration = get_duration(start_date_receive, end_date_receive)

    host_user_id : request.cookies.get("user_id")

    #챌린지 추최자의 정보 획득
    participant_data = find_user_data(host_user_id)

    challenge = {
        "name": name_receive,
        "host_user_id": host_user_id,
        "start_date": start_date_receive,
        "end_date": end_date_receive,
        "duration": duration,
        "details": details_receive,
        "verification_method": verification_method_receive,
        "bet_required": bet_required_receive,
        "participants": [participant_data],
    }

    join_challenge()

    challenge_id = db.challenges.insert_one(challenge).inserted_id
    return jsonify({"result": "success"},{'challenge_id':str(challenge_id)})


def get_duration(start_date_str, end_date_str):
    # str 형태의 날짜를 datetime으로 변환
    start_dt = datetime.strptime(start_date_str, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date_str, "%Y-%m-%d")
    result = end_dt - start_dt

    return result.days + 1

# 챌린지 목록 라우팅
@challenge_routes.route("/challenge")
def challenge_list():
    challenges_data = list(challenges.find({}))

    for challenge in challenges_data:
        challenge["_id"] = str(challenge.get("_id"))
        
    return render_template("chal_list.html", challenges=challenges_data)

@challenge_routes.route("/challenge/<id>")
# 접속된 url에 있는 값(challenge/~id)을 변수로 받아 함수 인자로 전달 
def detail(id):
    # challenges 내의 "_id"중 받아온 id와 일치하는지 확인(이때 ObjectId로 형변환)
    challenge = db.challenges.find_one({"_id": ObjectId(id)})
    
    # id가 일치하는 challenge를 detail.html로 render해서 challenge로 보냄
    return render_template("chal_detail.html", challenge=challenge)


# 유저 id 참조, 데이터(이름, 프로필 사진) 조회하는 기능 
def find_user_data(id):
    #user collection 내 일치하는 id 조회, 해당되는 id의 이름, 프로필 사진 가져오기
    user = db.user.find_one({"_id":ObjectId(id)}, {"name": 1, "profile_image": 1})

    #참가자 정보 결합
    participant_data = {
        "participant_id": id,
        "name": user["name"],
        "profile_image": user["profile_image"],
        "count": 0,
        "verification_image" : [
            # 추후 구현 : 인증하기 클릭 후 조작시 인증사진, today data 배열로 추가하는 기능
        ]
    }

    return participant_data


# 유저 조회하여 해당하는 데이터를 추가하는 기능
@challenge_routes.route("/api/challenge/join", methods=["POST"])
def join_challenge():
    data = request.json

    challenge_id = data.get("challenge_id")
    user_id = request.cookies.get("user_id")

    participant_data = find_user_data(user_id)
    if not participant_data:
        return jsonify
    

#사용자의 참여 중인 챌린지 목록 조회 기능
@challenge_routes.route("/mypage")
#사용자의 user_id 가져오기
def get_user_challenges():
    user_id = request.cookies.get("user_id")

    #사용자가 참여 중인 챌린지 목록 가져오기
    joined_challenges = db.users.find_one({"_id":ObjectId(user_id)}, {"joined_challenges":1})

    #참여 중인 챌린지가 없는 경우 null data를 my_chal.html로 render해서 challenges로 보냄냄
    if not joined_challenges or "joined_challenges" not in joined_challenges:
        return render_template("my_chal.html",challenges=[])
    
    challenges_data = []

    #challenge name과 참여 인원 수집집
    for challenge in joined_challenges["joined_challenges"]:
        challenge_info = db.challenges.find_one({"_id":ObjectId(challenge["challenge_id"])})
        if challenge_info:
            challenges_data.append({
                "name":challenge_info["name"],
                "participant_count":len(challenge_info["participants"])
            })
    #challenge name과 participant_count를 my_chal.html로 render해서 challenges로 보냄
    return render_template("my_chal.html",challenges=challenges_data)