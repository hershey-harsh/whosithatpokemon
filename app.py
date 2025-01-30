import os
import random
from flask import Flask, request, jsonify, send_from_directory, url_for
from data import DataManager
from helper import FileUploadHandler, predict_image, async_predict
from flask import Flask, render_template
import logging

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
app.config['UPLOAD_FOLDER'] = 'img_history'
app.config['JSON_AS_ASCII'] = False
# app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

data_manager = DataManager()
file_handler = FileUploadHandler(app.config['UPLOAD_FOLDER'])

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
        response = requests.get(data['url'], stream=True)
        response.raise_for_status()
        image = Image.open(BytesIO(response.content))
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        temp_path = f"temp_{random.getrandbits(32)}.png"
        image.save(temp_path)
        
        prediction_result = predict_image(temp_path)
        pokemon_name = prediction_result['pokemon']
        os.remove(temp_path)
        
        species = data_manager.species_by_name(pokemon_name)
        if not species:
            return jsonify({'error': 'Pokemon not found'}), 404
        
        response_data = format_species_response(species)
        response_data['predictions'] = prediction_result['predictions']
        return jsonify(response_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/predict/upload', methods=['POST'])
def predict_from_upload():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if not file or file.filename == '':
        return jsonify({'error': 'Invalid file'}), 400
    
    try:
        saved_path = file_handler.save_uploaded_file(file)
        app.logger.debug(f"File saved to: {saved_path}")
        
        prediction_result = predict_image(saved_path)
        app.logger.debug(f"Prediction result: {prediction_result}")
        
        species = data_manager.species_by_name(prediction_result['pokemon'])
        if not species:
            return jsonify({'error': 'Pokemon not found'}), 404
        
        response = format_species_response(species)
        response['predictions'] = prediction_result['predictions']
        return jsonify(response)
        
    except Exception as e:
        app.logger.error(f"Error processing request: {str(e)}", exc_info=True)
        return jsonify({'error': f"Internal server error: {str(e)}"}), 500


@app.route('/pokemon/<name>', methods=['GET'])
def get_pokemon(name):
    species = data_manager.species_by_name(name)
    return jsonify(format_species_response(species)) if species else jsonify({'error': 'Pokemon not found'}), 404

@app.route('/pokemon/<name>/evolutions', methods=['GET'])
def get_evolutions(name):
    species = data_manager.species_by_name(name)
    if not species:
        return jsonify({'error': 'Pokemon not found'}), 404
    
    evolutions = {
        'from': format_evolution(species.evolution_from),
        'to': format_evolution(species.evolution_to)
    }
    return jsonify(evolutions)

@app.route('/images/<filename>', methods=['GET'])
def get_image(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/random', methods=['GET'])
def random_pokemon():
    species = data_manager.random_spawn()
    return jsonify(format_species_response(species))

@app.route('/types', methods=['GET'])
def get_all_types():
    types = sorted(data_manager.unique_types())
    return jsonify({'types': types})

@app.route('/pokemon/type/<type_name>', methods=['GET'])
def get_by_type(type_name):
    species_list = data_manager.species_by_type(type_name.lower())
    if not species_list:
        return jsonify({'error': 'Invalid type'}), 404
    return jsonify([format_species_response(s) for s in species_list])

@app.route('/regions', methods=['GET'])
def get_regions():
    regions = sorted(data_manager.unique_regions())
    return jsonify({'regions': regions})

@app.route('/pokemon/region/<region>', methods=['GET'])
def get_by_region(region):
    species_list = data_manager.species_by_region(region.lower())
    if not species_list:
        return jsonify({'error': 'Invalid region'}), 404
    return jsonify([format_species_response(s) for s in species_list])

@app.route('/status', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'model_count': len(filelist),
        'total_pokemon': len(data_manager.all_species())
    })

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

def format_evolution(evolution):
    if not evolution or not evolution.items:
        return None
    return [{'target': item.target.name, 'trigger': item.trigger.text} for item in evolution.items]

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)