# gridfs to store  and retreive large files in mongoDB
# pika to interface with RabbitMQ
import os, gridfs, pika, json   
from flask import Flask, request, send_file
from flask_pymongo import PyMongo
from auth import validate
from auth_svc import access
from storage import util
from bson.objectid import ObjectId

server = Flask(__name__)
# connect mongo to server/ app
mongo_video = PyMongo(server, uri="mongodb://mongodb-service:27017/videos")
mongo_mp3 = PyMongo(server, uri="mongodb://mongodb-service:27017/mp3s")

# grid fs wrapper to intrerface with database
fs_videos = gridfs.GridFS(mongo_video.db)
fs_mp3s = gridfs.GridFS(mongo_mp3.db)

# connection with rabbitMQ
# BlockingConnection makes communication with RabbitMQ synchronous as its block user to do anything till he gets the response.
connection = pika.BlockingConnection(pika.ConnectionParameters("rabbitmq"))
channel = connection.channel()

@server.route("/login", methods=["POST"])
def login():
    token, err = access.login(request)
    if not err:
        return token
    else:
        return err


@server.route("/upload", methods=["POST"])
def upload():
    access, err = validate.token(request)   # access will have the decoded body of the payload with our claims
    if err:
        return err
    access = json.loads(access)

    if access["admin"]:
        # only 1 file at a time
        if len(request.files) > 1 and len(request.files) < 1:
            return "exactly 1 file required", 400
        
        for _, f in request.files.items():
            err = util.upload(f, fs_videos, channel, access)
            if err:
                return err
        return "success", 200
    else:
        return "not authorized", 401


@server.route("/download", methods=["GET"])
def download():
    access, err = validate.token(request)
    if err:
        return err
    access = json.loads(access)

    if access["admin"]:
        fid_string = request.args.get("fid")
        if not fid_string:
            return "fid is required", 400
        try:
            out = fs_mp3s.get(ObjectId(fid_string))
            return send_file(out, download_name=f'{fid_string}.mp3')
        except Exception as err:
            return f"internal server error - mp3 file download - {err}", 500
    return "not authorized", 401


if __name__ == "__main__":
    server.run(host="0.0.0.0", port=8080)