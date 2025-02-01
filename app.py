import os
import logging
import tempfile
from io import BytesIO
from flask import Flask, request, jsonify, send_from_directory, render_template
from werkzeug.utils import secure_filename
from PIL import Image
import requests
from data import DataManager
from helper import FileUploadHandler, predict_image

app = Flask(__name__)
app.config.update({
    'JSON_AS_ASCII': False,
    'UPLOAD_FOLDER': 'img_history',
    'MAX_CONTENT_LENGTH': 16 * 1024 * 1024,  # 16MB
    'ALLOWED_EXTENSIONS': {'png', 'jpg', 'jpeg', 'gif'}
})

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

data_manager = DataManager()
file_handler = FileUploadHandler(app.config['UPLOAD_FOLDER'])

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def handle_prediction(image_path):
    """Common prediction handling logic"""
    prediction_result = predict_image(image_path)
    logger.info(f"Prediction result: {prediction_result}")
    
    species = data_manager.species_by_name(prediction_result['pokemon'])
    if not species:
        raise ValueError('Pokemon not found')
    
    response = format_species_response(species)
    response['predictions'] = prediction_result['predictions']
    return response

def download_image(url):
    """Download and validate image from URL"""
    response = requests.get(url, stream=True, timeout=10)
    response.raise_for_status()
    
    if 'image' not in response.headers.get('Content-Type', ''):
        raise ValueError('URL does not point to an image')
    
    image = Image.open(BytesIO(response.content))
    if image.mode != 'RGB':
        image = image.convert('RGB')
    return image

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/docs')
def docs():
    return render_template('docs.html')

@app.route('/predict/url', methods=['POST'])
def predict_from_url():
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({'error': 'Missing image URL'}), 400
    
    try:
        image = download_image(data['url'])
        with tempfile.NamedTemporaryFile(suffix='.png', delete=True) as temp_file:
            image.save(temp_file.name)
            response_data = handle_prediction(temp_file.name)
        return jsonify(response_data)
    except requests.exceptions.RequestException as e:
        logger.error(f"URL request failed: {str(e)}")
        return jsonify({'error': 'Invalid image URL'}), 400
    except Exception as e:
        logger.error(f"Prediction error: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/predict/upload', methods=['POST'])
def predict_from_upload():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if not file or file.filename == '':
        return jsonify({'error': 'Invalid file'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type'}), 400

    try:
        filename = secure_filename(file.filename)
        saved_path = file_handler.save_uploaded_file(file, filename)
        logger.info(f"File saved to: {saved_path}")
        
        response_data = handle_prediction(saved_path)
        return jsonify(response_data)
    except Exception as e:
        logger.error(f"Processing error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to process image'}), 500

@app.route('/pokemon/<name>', methods=['GET'])
def get_pokemon(name):
    species = data_manager.species_by_name(name)
    if not species:
        return jsonify({'error': 'Pokemon not found'}), 404
    return jsonify(format_species_response(species))

@app.route('/images/<filename>', methods=['GET'])
def get_image(filename):
    safe_filename = secure_filename(filename)
    return send_from_directory(
        app.config['UPLOAD_FOLDER'],
        safe_filename,
        mimetype='image/' + safe_filename.rsplit('.', 1)[1].lower()
    )

@app.route('/status', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'total_pokemon': len(data_manager.all_species()),
        'uploaded_images': len(os.listdir(app.config['UPLOAD_FOLDER']))
    })

@app.route('/pokemon/<name>/evolutions', methods=['GET'])
def get_evolutions(name):
    species = data_manager.species_by_name(name)
    if not species:
        return jsonify({'error': 'Pokemon not found'}), 404
    
    return jsonify({
        'from': format_evolution(species.evolution_from),
        'to': format_evolution(species.evolution_to)
    })

@app.route('/random', methods=['GET'])
def random_pokemon():
    species = data_manager.random_spawn()
    return jsonify(format_species_response(species))

@app.route('/types', methods=['GET'])
def get_all_types():
    return jsonify({'types': sorted(data_manager.unique_types())})

@app.route('/pokemon/type/<type_name>', methods=['GET'])
def get_by_type(type_name):
    species_list = data_manager.species_by_type(type_name.lower())
    return jsonify([format_species_response(s) for s in species_list]) if species_list else \
        jsonify({'error': 'Invalid type'}), 404

@app.route('/regions', methods=['GET'])
def get_regions():
    return jsonify({'regions': sorted(data_manager.unique_regions())})

@app.route('/pokemon/region/<region>', methods=['GET'])
def get_by_region(region):
    species_list = data_manager.species_by_region(region.lower())
    return jsonify([format_species_response(s) for s in species_list]) if species_list else \
        jsonify({'error': 'Invalid region'}), 404

def format_evolution(evolution):
    if not evolution or not evolution.items:
        return None
    return [{
        'target': item.target.name, 
        'trigger': item.trigger.text,
        'method': item.method.value if item.method else None
    } for item in evolution.items]

def format_species_response(species):
    return {
        'name': species.name,
        'dex_number': species.dex_number,
        'description': species.description,
        'types': species.types,
        'height': species.height,
        'weight': species.weight,
        'base_stats': {
            'hp': species.base_stats.hp,
            'attack': species.base_stats.atk,
            'defense': species.base_stats.defn,
            'special_attack': species.base_stats.satk,
            'special_defense': species.base_stats.sdef,
            'speed': species.base_stats.spd
        },
        'region': species.region,
        'image_url': species.image_url,
        'shiny_image_url': species.shiny_image_url
    }

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=os.environ.get('FLASK_DEBUG', False))
