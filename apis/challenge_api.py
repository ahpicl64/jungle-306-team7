from datetime import datetime
from flask import Blueprint, Flask, render_template, jsonify, request
from bson import ObjectId
from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
db = client.jungle7
users = db.users
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

    host_user_id = request.cookies.get("user_id")

    # 챌린지 추최자의 정보 획득
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

    challenge_id = db.challenges.insert_one(challenge).inserted_id
    return jsonify({"result": "success", "challenge_id": str(challenge_id)})


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


# 접속된 url에 있는 값(challenge/~id)을 변수로 받아 함수 인자로 전달
@challenge_routes.route("/challenge/<id>")
def detail(id):
    # challenges 내의 "_id"중 받아온 id와 일치하는지 확인(이때 ObjectId로 형변환)
    challenge = challenges.find_one({"_id": ObjectId(id)})
    user_id = request.cookies.get("user_id")
    participation = check_participation(challenge, user_id)
    # id가 일치하는 challenge를 detail.html로 render해서 challenge로 보냄
    return render_template(
        "chal_detail.html", challenge=challenge, has_participated=participation
    )


# 참가자 목록과 사용자 id를 대조하여 챌린지 참가여부 검증 기능
def check_participation(challenge, user_id):
    for participant in challenge.get("participants", []):
        if participant.get("participant_id") == user_id:
            return True
    return False


# 유저 id 참조, 데이터(이름, 프로필 사진) 조회하는 기능
def find_user_data(id):
    # user collection 내 일치하는 id 조회, 해당되는 id의 이름, 프로필 사진 가져오기
    user = users.find_one({"_id": ObjectId(id)}, {"name": 1, "profile_image": 1})

    # 참가자 정보 결합
    participant_data = {
        "participant_id": id,
        "name": user["name"],
        "profile_image": user["profile_image"],
        "verification_count": 0,
        "verification_image": [
            # 추후 구현 : 인증하기 클릭 후 조작시 인증사진, today data 배열로 추가하는 기능
        ],
    }

    return participant_data


# 참가하기 선택시 참가자 추가 기능
@challenge_routes.route("/api/challenge/join", methods=["POST"])
def join_challenge():
    data = request.json

    # 본문의 챌린지 id
    challenge_id = data.get("challenge_id")
    my_id = request.cookies.get("user_id")

    # 사용자 정보 조회, 데이터 생성
    participant_data = find_user_data(my_id)

    # challenge 컬렉션에 데이터 push
    result = challenges.update_one(
        {"_id": ObjectId(challenge_id)}, {"$push": {"participants": participant_data}}
    )

    # result 결과 데이터 push(수정 카운트 여부)가 제대로 성공했는지 확인 후 결과출력
    if result.modified_count > 0:
        return jsonify({"result": "success"})
    else:
        return jsonify({"result": "fail"}), 400


# 챌린지 포기 기능
@challenge_routes.route("/api/challenge/abandon", methods=["POST"])
def abandon_challenge():
    data = request.json  # 파싱
    challenge_id = data.get("challenge_id")
    my_id = request.cookies.get("user_id")

    result = challenges.update_one(
        {"_id": ObjectId(challenge_id)},
        {"$pull": {"participants": {"participant_id": my_id}}},
    )
    return jsonify({"result": "success"})


# 사용자 참여 챌린지 목록 조회 기능
@challenge_routes.route("/mypage")
# 사용자의 user_id 가져오기
def get_user_challenges():
    user_id = request.cookies.get("user_id")

    # 사용자가 참여 중인 챌린지 목록 가져오기
    joined_challenges = db.users.find_one(
        {"_id": ObjectId(user_id)}, {"joined_challenges": 1}
    )

    # 참여 중인 챌린지가 없는 경우 null data를 my_chal.html로 render해서 challenges로 보냄냄
    if not joined_challenges or "joined_challenges" not in joined_challenges:
        return render_template("my_chal.html", challenges=[])

    challenges_data = []

    # challenge name과 참여 인원 수집
    for challenge in joined_challenges["joined_challenges"]:
        challenge_info = db.challenges.find_one(
            {"_id": ObjectId(challenge["challenge_id"])}
        )
        if challenge_info:
            challenges_data.append(
                {
                    "name": challenge_info["name"],
                    "participant_count": len(challenge_info["participants"]),
                }
            )
    # challenge name과 participant_count를 my_chal.html로 render해서 challenges로 보냄
    return render_template("my_chal.html", challenges=challenges_data)


# (회원 메인 페이지 상단) 본인 참여 챌린지 목록
@challenge_routes.route("/", methods=["GET"])
# 사용자 user_id 가져오기
def get_challenges():
    user_id = request.cookies.get("user_id")

    # 사용자가 참여 중인 챌린지 목록 가져오기
    joined_challenges = db.users.find_one(
        {"_id": ObjectId(user_id)}, {"joined_challenges": 1}
    )

    # 참여 중인 챌린지가 없는 경우 null data를 index.html로 render해서 challenges로 보냄
    if not joined_challenges or "joined_challenges" not in joined_challenges:
        return render_template("index.html", challenges=[])

    challenges_data = []
    # challenge name과 진행기간 수집
    for challenge in joined_challenges["joined_challenges"]:
        challenge_info = db.challenges.find_one(
            {"_id": ObjectId(challenge["challenge_id"])}
        )
        if challenge_info:
            # 해당 챌린지의 participants 리스트에서 현재 사용자 찾기
            participant = next(
                (
                    p
                    for p in challenge_info["participants"]
                    if p["participant_id"] == user_id
                ),
                None,
            )

            challenges_data.append(
                {
                    "name": challenge_info["name"],
                    "verification_count": (
                        participant["verification_count"] if participant else 0
                    ),
                    "duration": challenge_info["duration"],
                }
            )

    # 최신 참여 챌린지 3개만 선택 (최근 것이 리스트 마지막에 있으므로 뒤에서 3개 추출)
    challenges_data = sorted(challenges_data, key=lambda x: x["name"], reverse=True)[:3]

    # 전체 챌린지 중 4개만 가져오기
    all_challenges = list(challenges.find().sort("start_date", -1).limit(4))
    for challenge in all_challenges:
        challenge["_id"] = str(challenge["_id"])  # ObjectId를 문자열로 변환

    return render_template(
        "index.html", challenges=challenges_data, all_challenges=all_challenges
    )
