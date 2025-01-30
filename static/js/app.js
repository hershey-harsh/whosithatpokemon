const uploadInput = document.getElementById('pokemon-upload');
const resultSection = document.getElementById('result-section');
const dropZone = document.getElementById('drop-zone');
const uploadSection = document.getElementById('upload-section');
const uploadAnotherBtn = document.getElementById('upload-another');
let loadingInterval;

dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('drag-over');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('drag-over');
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('drag-over');
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        uploadInput.files = files;
        handleFileUpload(files[0]);
    }
});

uploadInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        handleFileUpload(e.target.files[0]);
    }
});

uploadAnotherBtn.addEventListener('click', () => {
    uploadSection.classList.remove('hidden');
    resultSection.classList.add('hidden');
    uploadAnotherBtn.classList.add('hidden');
    uploadInput.value = '';
});

function startLoadingAnimation() {
    const loadingBar = document.querySelector('.loading-bar');
    loadingBar.style.width = '0%';
    let width = 0;
    loadingInterval = setInterval(() => {
        if(width < 90) {
            width += 1 + (Math.random() * 3);
            loadingBar.style.width = Math.min(width, 90) + '%';
        }
    }, 200);
}

function stopLoadingAnimation() {
    clearInterval(loadingInterval);
    const loadingBar = document.querySelector('.loading-bar');
    loadingBar.style.width = '100%';
    setTimeout(() => {
        document.getElementById('loading-container').classList.add('hidden');
    }, 500);
}

async function handleFileUpload(file) {
    const formData = new FormData();
    formData.append('file', file);

    try {
        uploadSection.classList.add('hidden');
        uploadAnotherBtn.classList.add('hidden');
        resultSection.classList.remove('hidden');
        document.getElementById('loading-container').classList.remove('hidden');
        startLoadingAnimation();

        const response = await fetch('/predict/upload', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        stopLoadingAnimation();
        const predictions = await getPredictions(file);
        data.predictions = predictions;
        displayResult(data);
        uploadAnotherBtn.classList.remove('hidden');
    } catch (error) {
        console.error('Error:', error);
        stopLoadingAnimation();
        uploadSection.classList.remove('hidden');
        uploadAnotherBtn.classList.add('hidden');
    }
}

async function getPredictions(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const response = await fetch('/predict/upload', {
            method: 'POST',
            body: formData
        });
        const data = await response.json();
        return data.predictions || [];
    } catch (error) {
        console.error('Prediction error:', error);
        return [];
    }
}

function displayResult(pokemon) {
    const dexNumber = String(pokemon.dex_number).padStart(3, '0');
    const pokemonImage = `https://raw.githubusercontent.com/poketwo/data/master/images/${dexNumber}.png`;

    document.getElementById('pokemon-name').textContent = pokemon.name;
    document.getElementById('pokemon-dex').textContent = `#${dexNumber}`;
    document.getElementById('pokemon-height').textContent = `${pokemon.height}m`;
    document.getElementById('pokemon-weight').textContent = `${pokemon.weight}kg`;
    document.getElementById('pokemon-image').src = pokemonImage;
    document.getElementById('pokemon-description').textContent = pokemon.description;

    const typesContainer = document.getElementById('pokemon-types');
    typesContainer.innerHTML = pokemon.types.map(type => 
        `<span class="px-4 py-2 bg-red-100 text-red-600 rounded-full">${type}</span>`
    ).join('');

    const statsContainer = document.getElementById('pokemon-stats');
    statsContainer.innerHTML = Object.entries(pokemon.base_stats).map(([stat, value]) => `
        <div class="bg-gray-100 p-4 rounded-lg">
            <p class="text-gray-500 capitalize">${stat.replace('_', ' ')}</p>
            <p class="text-xl font-semibold">${value}</p>
        </div>
    `).join('');

    const predictionBars = document.getElementById('prediction-bars');
    if (pokemon.predictions && pokemon.predictions.length > 0) {
        const validPredictions = pokemon.predictions
            .filter(pred => pred.name && pred.name.trim() !== '')
            .slice(0, 3);

        predictionBars.innerHTML = validPredictions.map((pred, index) => {
            const confidence = pred.confidence * 100;
            const colors = ['bg-green-600', 'bg-blue-600', 'bg-red-600'];
            
            return `
            <div class="w-full mb-4">
                <div class="flex justify-between mb-1">
                    <span class="text-sm font-medium">${pred.name}</span>
                    <span class="text-sm text-gray-600">${confidence.toFixed(1)}%</span>
                </div>
                <div class="w-full bg-gray-200 rounded-lg overflow-hidden">
                    <div class="${colors[index]} text-xs font-medium text-white 
                            flex items-center justify-center rounded-lg" 
                        style="width: ${Math.min(confidence, 100).toFixed(1)}%; height: 40px;">
                        ${confidence.toFixed(1)}%
                    </div>
                </div>
            </div>
            `;
        }).join('');
    } else {
        predictionBars.innerHTML = '<p class="text-gray-500">No prediction data available</p>';
    }
}

function positionSVGs() {
    const elements = document.querySelectorAll('.pokemon-deco');
    const placedPositions = [];
    const viewportPadding = 50;

    elements.forEach(element => {
        const width = parseInt(element.style.width, 10);
        const height = width;
        const vw = window.innerWidth;
        const vh = window.innerHeight;
        
        let x, y;
        let validPosition = false;
        let attempts = 0;

        while (!validPosition && attempts < 100) {
            x = Math.random() * (vw - width - viewportPadding * 2) + viewportPadding;
            y = Math.random() * (vh - height - viewportPadding * 2) + viewportPadding;

            validPosition = placedPositions.every(pos => {
                const horizontalOverlap = !(x + width < pos.x || x > pos.x + pos.width);
                const verticalOverlap = !(y + height < pos.y || y > pos.y + pos.height);
                return !(horizontalOverlap && verticalOverlap);
            });

            attempts++;
        }

        element.style.left = `${(x / vw) * 100}%`;
        element.style.top = `${(y / vh) * 100}%`;
        placedPositions.push({ x, y, width, height });
    });
}

window.addEventListener('load', positionSVGs);
window.addEventListener('resize', positionSVGs);