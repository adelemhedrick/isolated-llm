from flask import Flask, request, jsonify
import os
import requests
from werkzeug.utils import secure_filename
import logging
from logging.handlers import RotatingFileHandler
from PIL import Image, ImageSequence

app = Flask(__name__)

# Setup logging
logging.basicConfig(level=logging.DEBUG)
handler = RotatingFileHandler('api-server.log', maxBytes=10000, backupCount=1)
handler.setLevel(logging.DEBUG)
app.logger.addHandler(handler)

UPLOAD_FOLDER = '/app/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def strip_metadata(image_path):
    with Image.open(image_path) as img:
        data = img.convert('RGB')
        clean_image_path = image_path.rsplit('.', 1)[0] + '_clean.jpg'
        data.save(clean_image_path, 'JPEG')
        return clean_image_path

def convert_image_to_supported_format(file_path, target_format='JPEG'):
    try:
        with Image.open(file_path) as img:
            app.logger.debug(f"Opened image format: {img.format}, size: {img.size}, mode: {img.mode}")

            if img.format in ['JPEG', 'PNG']:
                app.logger.debug("Image format is already supported. No conversion needed.")
                return file_path

            if img.format == 'MPO':
                app.logger.debug("Handling MPO format.")
                images = list(ImageSequence.Iterator(img))
                if images:
                    first_image = images[0].convert('RGB')
                    new_file_path = file_path.rsplit('.', 1)[0] + '_converted.' + target_format.lower()
                    first_image.save(new_file_path, target_format)
                    app.logger.debug(f"Converted first image from MPO to {target_format}, saved as {new_file_path}")
                    return new_file_path
                else:
                    app.logger.error("No images found in MPO file.")
                    return None
            else:
                rgb_im = img.convert('RGB')
                new_file_path = file_path.rsplit('.', 1)[0] + '_converted.' + target_format.lower()
                rgb_im.save(new_file_path, target_format)
                app.logger.debug(f"Converted image to {target_format}, saved as {new_file_path}")
                return new_file_path

    except Exception as e:
        app.logger.error(f"Failed to convert image: {e}")
        return None


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['POST'])
def upload_file():
    app.logger.debug("Received request to upload file")
    if 'file' not in request.files:
        app.logger.error("No file part in request")
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        app.logger.error("No file selected for upload")
        return jsonify({"error": "No selected file"}), 400
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        app.logger.debug(f"File has been saved to {file_path}")
        file.save(file_path)

        file_path = strip_metadata(file_path)
        
        # Convert image if necessary
        converted_path = convert_image_to_supported_format(file_path)
        if converted_path:
            file_path = converted_path  # Update to use the converted image path
        else:
            return jsonify({"error": "Failed to convert image"}), 500

        # Call OCR service
        try:
            response = requests.post('http://ocr-service:5001/ocr', json={"file_path": filename}, timeout=10)
            response.raise_for_status()
            app.logger.debug("OCR service responded with success")
            return jsonify({"message": "File uploaded and processed", "data": response.json()}), 200
        except requests.exceptions.HTTPError as e:
            app.logger.error(f"HTTP error from OCR service: {e}")
            return jsonify({"error": "OCR processing failed"}), response.status_code
        except requests.exceptions.RequestException as e:
            app.logger.error(f"Request failed: {e}")
            return jsonify({"error": "Connection to OCR service failed"}), 500
    else:
        app.logger.error("File type not allowed")
        return jsonify({"error": "File type not allowed"}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
