import pika, json

def upload(f, fs, channel, access):
    try:
        # push file to mongodb with gridfs
        fid = fs.put(f)
    except Exception as err:
        return f"internal server error - video to mongodb - {err}", 500
    
    # create message to be pushed to rabbitMQ
    message = {
        "video_fid": str(fid),
        "mp3_fid": None,
        "username": access["username"]
    }
    # push message to MQ
    try:
        channel.basic_publish(
            exchange="",    # default exchange - no name. Benefit: routing key will be same as queue name
            routing_key="video", # video will be the name of the queue
            body=json.dumps(message),
            properties=pika.BasicProperties(
                # make queue durable i.e. messages inside queue persistent
                delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE # makes sure the messages are persisted in the queue in an event of pod crash/ restart
            )
        )
    except Exception as err:
        # in case of failure, delete file from db.
        fs.delete(fid)
        # So, now there would be no message in queue and no file in db
        return f"internal server error - msg to rabbitmq - {err}", 500
