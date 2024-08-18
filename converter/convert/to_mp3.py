import pika, json, tempfile, os
from bson.objectid import ObjectId
import moviepy.editor
import pika.spec

def start(message, fs_videos, fs_mp3s, channel):
    message = json.loads(message) # deserialize json string to python object  

    # empty temp file - to write content of video to this file
    tf = tempfile.NamedTemporaryFile()  # this will create a named temp file in a temp directory
    # video contents
    out = fs_videos.get(ObjectId(message["video_fid"])) # out is an object which has the method 'read'
    # add video contents to empty file
    tf.write(out.read())
    # create audio from temp video file
    audio = moviepy.editor.VideoFileClip(tf.name).audio     # tf.name will resolve to the absolute path of temp file, audio is an object
    # Close temp file - this will destroy the temp file as well
    tf.close()

    # write audio to the file
    tf_path = tempfile.gettempdir() + f"/{message['video_fid']}.mp3"
    audio.write_audiofile(tf_path)

    # save file to mongo
    f = open(tf_path, "rb")
    data = f.read()
    fid = fs_mp3s.put(data)
    f.close()
    os.remove(tf_path)  #  we are removing temp file manually coz the file was not created by tempfile but with write_audiofile method

    message["mp3_fid"] = str(fid)

    # put message on rabbitmq
    try:
        channel.basic_publish(
            exchange="",
            routing_key=os.environ.get("MP3_QUEUE"),
            body=json.dumps(message),
            properties=pika.BasicProperties(delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE),
        )
    except Exception as err:
        # if we are not able to put message to queue for some reason, then delete the audio file from mongo
        fs_mp3s.delete(fid)
        return "failed to publish message"