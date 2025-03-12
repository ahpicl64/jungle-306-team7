from ast import Return
from bson import ObjectId
from pymongo import MongoClient
from flask import Flask, render_template, jsonify, request
from flask_jwt_extended import JWTManager

# auth 관련 api import
from apis.user_api import auth_routes
from apis.challenge_api import challenge_routes


app = Flask(__name__)

# === MongoDB 설정 ===
client = MongoClient('localhost', 27017)
db = client.jungle7

# === JWT 토큰 관련 설정 ===
# 토큰 생성에 사용될 Secret Key를 flask 환경 변수에 등록
app.config.update(
			DEBUG = True,
            # TODO: 배포할 때는 환경변수 처리해야 함
			JWT_SECRET_KEY = "JWTSECRETKEY"
		)

# JWT 확장 모듈을 flask 어플리케이션에 등록
jwt = JWTManager(app)

# === 블루프린트 등록 ===
app.register_blueprint(auth_routes)
# *** 각 import한 api 블루프린트 등록 
app.register_blueprint(challenge_routes)

#  === HTML 렌더링 ===
@app.route('/')
def home():
    return render_template('index.html')

# 회원가입 페이지로 이동하는 함수
@app.route('/signup')
def signUp():
    return render_template('sign_up.html')

# 로그인 페이지로 이동하는 함수
@app.route('/signin')
def signIn():
    return render_template('sign_in.html')

# 챌린지 목록 페이지로 이동하는 함수
@app.route('/challenge')
def list():
    return render_template('chal_list.html')

@app.route('/challenge/<id>')
def detail(id):
    return render_template('chal_detail.html', challenge_id=id)

@app.route('/generate')
def generate():
    return render_template('generate_chal.html')

@app.route('/mypage')
def mypage():
    return render_template('my_chal.html')


if __name__ == '__main__':
    # TODO: 포트 번호 5000으로 변경
    app.run('0.0.0.0', port=5001, debug=True)