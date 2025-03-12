from datetime import datetime
import os
import uuid
from flask import Blueprint, Flask, render_template, jsonify, request
from bson import ObjectId
from pymongo import MongoClient
from models.user_model import search_user, user_join_challenge

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
    user_join_challenge(ObjectId(challenge_id))

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

    # 참가자 목록을 verification_count 기준으로 정렬 (내림차순)
    ranked_participants = sorted(
        challenge.get("participants", []), 
        key=lambda p: p.get("verification_count", 0), 
        reverse=True
    )

    # 순위(rank) 추가
    for rank, participant in enumerate(ranked_participants, start=1):
        participant["rank"] = rank  # 1부터 시작하는 랭크 부여

    # id가 일치하는 challenge를 detail.html로 render해서 challenge로 보냄
    return render_template(
        "chal_detail.html", 
        challenge=challenge, 
        has_participated=participation, 
        participants=ranked_participants  # 정렬된 참가자 목록 전달
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
    challenge_id = ObjectId(data.get("challenge_id"))
    my_id = ObjectId(request.cookies.get("user_id"))

    print(type(my_id), my_id)  
    print(type(challenge_id), challenge_id)

    # 사용자 정보 조회, 데이터 생성
    participant_data = find_user_data(my_id)

    # challenge 컬렉션에 데이터 push
    result = challenges.update_one(
        {"_id": ObjectId(challenge_id)}, {"$push": {"participants": participant_data}}
    )

    # user 컬렉션에 데이터 push
    user_result = users.update_one(
        {'_id': ObjectId(my_id)}, {'$push':{'joined_challenges': challenge_id}}
    )

    # result 결과 데이터 push(수정 카운트 여부)가 제대로 성공했는지 확인 후 결과출력
    if result.modified_count > 0 and user_result.modified_count > 0:
        return jsonify({"result": "success"})
    else:
        return jsonify({"result": "fail"}), 400

# 챌린지 포기 기능
@challenge_routes.route("/api/challenge/abandon", methods=["POST"])
def abandon_challenge():
    data = request.json  # 파싱
    challenge_id = data.get("challenge_id")
    my_id = request.cookies.get("user_id")

    print(f"🔥 챌린지 포기 요청: user_id={my_id}, challenge_id={challenge_id}")

    # 챌린지 컬렉션에서 참가자 제거
    result = challenges.update_one(
        {"_id": ObjectId(challenge_id)},
        {"$pull": {"participants": {"participant_id": my_id}}},
    )
    print(f"🟢 챌린지에서 사용자 제거 완료: {result.matched_count}개 문서 수정됨")

    # 사용자의 joined_challenges 배열에서 해당 챌린지 제거
    user_result = users.update_one(
        {"_id": ObjectId(my_id)},
        {"$pull": {"joined_challenges": {"challenge_id": {"$in": [ObjectId(challenge_id), challenge_id]}}}},  
    )

    print(f"🔵 유저 컬렉션 업데이트 결과: {user_result.matched_count}개 문서 수정됨")

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
    challenge_info = None

    # challenge name과 참여 인원 수집
    for challenge in joined_challenges["joined_challenges"]:
        challenge_info = db.challenges.find_one(
            {"_id": ObjectId(challenge["challenge_id"])}
        )
        if challenge_info:
            print(challenge_info)
            challenges_data.append(
                {
                    "name": challenge_info["name"],
                    "participant_count": len(challenge_info["participants"]),
                }
            )
    # challenge name과 participant_count를 my_chal.html로 render해서 challenges로 보냄
    return render_template("my_chal.html", challenges=challenges_data)


# (회원 메인 페이지 상단) 본인 참여 챌린지 목록
@challenge_routes.route("/")
# 사용자 user_id 가져오기
def get_challenges():
    user_id = request.cookies.get("user_id")

    # 사용자가 참여 중인 챌린지 목록 가져오기
    user_data = db.users.find_one(
        {"_id": ObjectId(user_id)}, {"joined_challenges": 1}
    )

    # 참여 중인 챌린지가 없는 경우 null data를 index.html로 render해서 challenges로 보냄
    if not user_data or "joined_challenges" not in user_data:
        return render_template("index.html", challenges=[])

    joined_challenges = user_data["joined_challenges"]
    challenges_data = []

    # challenge name과 진행기간 수집
    for challenge in joined_challenges:
        challenge_id = challenge.get("challenge_id") if isinstance(challenge, dict) else challenge
        # challenge_info = db.challenges.find_one({"_id": challenge_id})
        print("=======challenge_id",challenge_id)

        # challenge_id가 존재하면 ObjectId로 변환
        if isinstance(challenge_id, str):
            challenge_id = ObjectId(challenge_id)

        challenge_info = db.challenges.find_one({"_id": challenge_id})
        print("=======challenge_info", challenge_info)

        if challenge_info:
            # 해당 챌린지의 participants 리스트에서 현재 사용자 찾기
            participant = next(
                (p for p in challenge_info.get("participants", []) if p["participant_id"] == user_id),
                None,
            )

            # 사용자 인증 횟수 가져오기 (없으면 0)
            verification_count = participant["verification_count"] if participant else 0

            challenges_data.append(
                {
                    'id': challenge_info["_id"],
                    "name": challenge_info["name"],
                    "duration": challenge_info["duration"],
                    "verification_count": verification_count,
                }
            )

    # 최신 참여 챌린지 3개만 선택 (최근 것이 리스트 마지막에 있으므로 뒤에서 3개 추출)
    challenges_data = sorted(challenges_data, key=lambda x: x["name"], reverse=True)[:3]

    # 3개 이상이면 3개까지만 출력, 3개 미만이면 전부 출력
    if len(challenges_data) > 3:
        challenges_data = challenges_data[:3]

    print("🤍",challenges_data)
    # 전체 챌린지 중 4개만 가져오기
    all_challenges = list(db.challenges.find().sort("start_date", -1).limit(4))
    for challenge in all_challenges:
        challenge["_id"] = str(challenge["_id"])  # ObjectId를 문자열로 변환


    user_id = request.cookies.get("user_id")
    user = search_user(user_id)
    
    name = user.get("name") if user else "Guest"

    return render_template(
        "index.html", challenges=challenges_data, all_challenges=all_challenges, user_name=name
    )


#  -- 이미지 파일 업로드 세팅 --
UPLOAD_FOLDER = "static/challenges" # 프로필 사진을 업로드할 폴더 지정
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"} # 허용할 파일 확장자

# 폴더가 없으면 생성
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# 확장자 체크 함수
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# 챌린지 인증하기 선택시 당일자 인증 기능
@challenge_routes.route("/api/challenge/verification", methods=["POST"])
def verificate_challenge():
    # 챌린지 ID 및 사용자 ID 가져오기
    challenge_id = request.form.get("challenge_id")
    user_id = request.cookies.get("user_id")

    # 오늘 날짜 확인 (YYYY-MM-DD 형식)
    today_date = datetime.now().strftime("%Y-%m-%d")

    # 챌린지 참여자의 기존 인증 내역 확인
    challenge = challenges.find_one(
        {
            "_id": ObjectId(challenge_id), 
            "participants.participant_id": user_id
        },
        {"participants.$": 1}  # 해당 user_id의 참여 정보만 가져오기
    )

    if not challenge or "participants" not in challenge:
        return jsonify({"result": "fail", "message": "참여 정보를 찾을 수 없습니다."})

    participant = challenge["participants"][0]  # 해당 사용자의 참여 정보

    # 오늘자 인증이 기존에 수행되었는지 확인
    for photo in participant.get("verification_image", []):
        if photo["date"] == today_date:
            return jsonify({"result": "fail", "message": "오늘 인증은 이미 완료되었습니다!"})

    # 인증 사진 이미지 처리
    challenge_image = request.files.get("challenge_image")
    if challenge_image and allowed_file(challenge_image.filename):
        # 파일 확장자 추출
        ext = challenge_image.filename.rsplit(".", 1)[-1]
    
        # 랜덤한 파일명 생성 (UUID 사용) -> 한글 제거
        filename = f"{uuid.uuid4().hex}.{ext}"
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        
        # 파일 저장
        challenge_image.save(file_path)
        db_path = f'/static/challenges/{filename}'

    # MongoDB 업데이트 (count 증가, 인증 정보 추가)
    result = challenges.update_one(
        {"_id": ObjectId(challenge_id), "participants.participant_id": user_id},  # 해당 유저의 데이터 찾기
        {
            "$inc": {"participants.$.verification_count": 1},  # count 1 증가
            "$push": {"participants.$.verification_image": {"photo_url": db_path, "date": today_date}}
        }
    )

    if result.modified_count > 0:
        return jsonify({"result": "success"})
    else:
        return jsonify({"result": "fail", "message": "인증에 실패했습니다."}), 400