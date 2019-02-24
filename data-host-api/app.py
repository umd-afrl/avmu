from flask import Flask, Response
import avmuCapture
import cv2

vc = cv2.VideoCapture(0)

cap = avmuCapture.AvmuCapture()

cap.start_threads()

app = Flask(__name__)


@app.route('/snakecam')
def get_snakecam():
    return Response(snakecam_frame_gen(), mimetype='multipart/x-mixed-replace; boundary=frame')


def snakecam_frame_gen():
    while True:
        rval, frame = vc.read()
        cv2.imwrite('snakecam.jpg', frame)
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + open('snakecam.jpg', 'rb').read() + b'\r\n')


def akela_frame_gen(): 
    while True:
        cap.get_image_lock()
        akela_image_data = open('akela.jpg', 'rb').read()
        cap.release_image_lock()
        frame = (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + akela_image_data + b'\r\n')
        yield frame


@app.route('/akela')
def get_akela():
    return Response(akela_frame_gen(), mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == '__main__':
    app.run(host='0.0.0.0', threaded=True)
