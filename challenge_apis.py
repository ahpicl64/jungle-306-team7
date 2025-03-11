from flask import Flask, render_template, jsonify, request

app = Flask(__name__)

import requests
from bs4 import BeautifulSoup

from pymongo import MongoClient

client = MongoClient("localhost", 27017)
db = client.jungle7


@app.route("/challenge", methods=["POST"])
def generate_challenge():
    name_receive = request.form["name"]
    start_date_receive = request.form["start_date"]
    end_date_receive = request.form["end_date"]
    details_receive = request.form["details"]
    verification_method_receive = request.form["verification_method"]
    bet_required_receive = request.form["bet_required"]

    challenge = {
        # "_id": _id_received, 몽고DB에서 insertedID
        "name": name_receive,
        #   "host_user_id": host_user_id,
        "start_date": start_date_receive,
        "end_date": end_date_receive,
        #   "duration": 30(int),
        "details": details_receive,
        "verification_method": verification_method_receive,
        "bet_required": bet_required_receive,
        "participants": [],
    }

    db.challenges.insert_one(challenge)
    return jsonify({"result": "success"})
