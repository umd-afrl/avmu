from flask import Flask, send_file, Response
import os
import distance_detector
import cv2
from threading import Thread

vc = cv2.VideoCapture(0)
cap = distance_detector.AvmuCapture()
cap.initialize()
cap.capture()


app = Flask(__name__)
@app.route('/radar')
def getImage():
    #start thread in akela_frame_gen
   #threadAkela = Thread(target = akela_frame_gen,args = ())
   #threadAkela.start()
   #threadAkela.join()
   return ("", 201, )

@app.route('/snakecam')
def getSnakecam():
    #start thread in snakecam_frame_gen
   #threadSnake = Thread(target = snakecam_frame_gen,args = ())
   #threadSnake.start()
   #threadSnake.join()
   return Response(snakecam_frame_gen(), mimetype='multipart/x-mixed-replace; boundary=frame')
    
def snakecam_frame_gen():
    while True:
        rval, frame = vc.read()
        cv2.imwrite('pic.jpg', frame)
        yield (b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + open('pic.jpg', 'rb').read() + b'\r\n')
 
def akela_frame_gen(): 
    while True:
        cap.capture()
        cap.generate_image()
        yield (b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + open('figure.jpg', 'rb').read() + b'\r\n')
@app.route('/akela')
def getAkela():
    return Response(akela_frame_gen(), mimetype='multipart/x-mixed-replace; boundary=frame')
 
if __name__ == '__main__':
    app.run(host='0.0.0.0')
