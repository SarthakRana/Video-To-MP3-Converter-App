import pika, sys, os, time
from pymongo import MongoClient
import gridfs
from convert import to_mp3

def main():
    # client = MongoClient("host.minikube.internal", 27017)
    client = MongoClient("mongodb-service", 27017)
    db_videos = client.videos
    db_mp3s = client.mp3s
    # gridfs
    fs_videos = gridfs.GridFS(db_videos)
    fs_mp3s = gridfs.GridFS(db_mp3s)

    # rabbitmq connection
    connection = pika.BlockingConnection(pika.ConnectionParameters(host="rabbitmq"))
    channel = connection.channel()


    def callback(ch, method, properties, body):
        """
        Callback function which gets called when message is consumed by the consumer.
        """
        err = to_mp3.start(body, fs_videos, fs_mp3s, ch)
        if err:
            # negative ack - we will not acknowledge that we received and processed the message. So, the message won't be deleted from queue.
            ch.basic_nack(delivery_tag=method.delivery_tag) 
            # delivery_tag uniquely identifies delivery on a channel. When we send this delivery_tag, rabbitmq would know that this message was not acknowledged and is not to be removed 
        else:
            ch.basic_ack(delivery_tag=method.delivery_tag)


    channel.basic_consume(
        queue=os.environ.get("VIDEO_QUEUE"), on_message_callback=callback
    )

    print("Waiting for messages. To exit press CTRL+C")

    channel.start_consuming()   # this will start listening to the queue where video messages are put.


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupted")
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)