import os
import json
import random
import asyncio
import aiohttp
import requests
import numpy as np
from io import BytesIO
from config import filelist
from config import pokemons
from PIL import Image, ImageOps
from keras.models import load_model
from keras.layers import DepthwiseConv2D

class CustomDepthwiseConv2D(DepthwiseConv2D):
    def __init__(self, **kwargs):
        kwargs.pop('groups', None)
        super().__init__(**kwargs)

model_list = []
for file in filelist:
    model_list.append(
        load_model(
            f'models/{file}',
            custom_objects={'DepthwiseConv2D': CustomDepthwiseConv2D},
            compile=False
        )
    )

def preprocess_image(image: Image.Image) -> np.ndarray:
    size = (224, 224)
    image = ImageOps.fit(image, size, Image.LANCZOS)
    image_array = np.asarray(image)
    
    normalized_image_array = (image_array.astype(np.float32) / 127.0) - 1
    
    return np.expand_dims(normalized_image_array, axis=0)

def predict_image(image_path: str) -> dict:
    with open(image_path, 'rb') as f:
        image = Image.open(f)
        if image.mode != 'RGB':
            image = image.convert('RGB')
    
    preprocessed = preprocess_image(image)
    
    all_predictions = []
    for model in model_list:
        pred = model.predict(preprocessed, verbose=0)[0]
        all_predictions.append(pred)
    
    combined = np.concatenate(all_predictions, axis=None)
    top_indices = np.argsort(combined)[-3:][::-1]
    
    return {
        'pokemon': pokemons[top_indices[0]],
        'predictions': [
            {'name': pokemons[i], 'confidence': float(combined[i])}
            for i in top_indices
        ]
    }

async def async_predict(image_path: str) -> str:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, predict_image, image_path)

class FileUploadHandler:
    def __init__(self, upload_folder='img_history'):
        self.upload_folder = upload_folder
        os.makedirs(upload_folder, exist_ok=True)

    def save_uploaded_file(self, file) -> str:
        if not file:
            raise ValueError("No file uploaded")
            
        filename = file.filename
        ext = os.path.splitext(filename)[1]
        random_name = f"{random.getrandbits(32):08x}{ext}"
        
        file_path = os.path.join(self.upload_folder, random_name)
        file.save(file_path)
        return file_path

    async def process_upload(self, file) -> str:
        saved_path = self.save_uploaded_file(file)
        return await async_predict(saved_path)