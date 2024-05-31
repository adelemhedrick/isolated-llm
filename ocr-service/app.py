from flask import Flask, request, jsonify
import pytesseract
from PIL import Image
import logging
from logging.handlers import RotatingFileHandler
import os
from PIL import Image, UnidentifiedImageError

app = Flask(__name__)

# Setup logging
logging.basicConfig(level=logging.DEBUG)
handler = RotatingFileHandler('ocr-service.log', maxBytes=10000, backupCount=1)
handler.setLevel(logging.DEBUG)
app.logger.addHandler(handler)

UPLOAD_FOLDER = '/app/uploads'

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


@app.route('/ocr', methods=['POST'])
def perform_ocr():
    app.logger.debug("Received OCR request")
    
    # Get file path from request
    file_path = request.json.get('file_path')
    full_path = os.path.join(UPLOAD_FOLDER, file_path)
    app.logger.debug(f"File path received: {full_path}")
    
    if not file_path:
        app.logger.error("No file path provided in request")
        return jsonify({"error": "No file path provided"}), 400

    full_path = strip_metadata(full_path)
    full_path = convert_image_to_supported_format(full_path)

    try:
        with Image.open(full_path) as img:
            app.logger.debug(f"Opened image format: {img.format}, size: {img.size}, mode: {img.mode}")
            extracted_text = pytesseract.image_to_string(img)
            app.logger.debug(f"OCR successful. Extracted text: {extracted_text[:100]}")  # Show a preview of the text
            return jsonify({"extracted_text": extracted_text}), 200
    except UnidentifiedImageError as e:
        app.logger.error(f"Unsupported image format: {e}")
        return jsonify({"error": "Unsupported image format"}), 415
    except Exception as e:
        app.logger.error(f"OCR failed: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
