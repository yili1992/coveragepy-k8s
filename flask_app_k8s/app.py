from flask import Flask, redirect, request, jsonify
import logging
import os

ALLOWED_EXTENSIONS = ['xml']
UPLOAD_FOLDER = os.path.join(os.path.split(os.path.realpath(__file__))[0], 'uploads')
app = Flask(__name__)
app.logger.addHandler(logging.StreamHandler())
app.logger.setLevel(logging.INFO)


def init():
    if not os.path.exists(UPLOAD_FOLDER):
        os.mkdir(UPLOAD_FOLDER)


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


def save_file(file, dir):
    if file and allowed_file(file.filename):
        sub_dir = os.path.join(UPLOAD_FOLDER, dir)
        upload_to = os.path.join(sub_dir, file.filename)
        if not os.path.exists(sub_dir):
            os.mkdir(sub_dir)
        file.save(upload_to)
    return file.filename


@app.route('/upload', methods=['POST'])
def uploaded_file():
    if request.method == 'POST':
        file = request.files['file']
        dir = request.form.to_dict()['pod']
        filename = save_file(file, dir)
        result = {"code": "0",
                  "msg": "upload success",
                  "filename": dir+"/"+filename
        }

        return jsonify(result)

init()

if __name__ == "__main__":
    app.run(host="0.0.0.0")
