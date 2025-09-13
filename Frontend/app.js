const backend = window.BACKEND_BASE || 'http://127.0.0.1:5000';

function el(id){ return document.getElementById(id); }

const form = el('uploadForm');
const input = el('fileInput');
const statusBox = el('status');
const countersBox = el('counters');
const results = el('results');
const imgInput = el('imgInput');
const imgProcessed = el('imgProcessed');
const imgRecreated = el('imgRecreated');
const svgObject = el('svgObject');
const svgDownload = el('svgDownload');
const samplesWrap = el('samples');

form.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!input.files[0]) return;
    
    statusBox.innerHTML = `
        <div class="processing-animation">Processing your Kolam image...</div>
    `;
    
    form.querySelector('button').disabled = true;
    results.hidden = true;
    document.querySelector('.recreated-showcase').style.display = 'none'; // Hide showcase initially

    const formData = new FormData();
    formData.append('image', input.files[0]);

    try {
        const res = await fetch(`${backend}/upload`, {
            method: 'POST',
            body: formData
        });
        
        const data = await res.json();
        console.log('Response data:', data); // Debug log
        
        if (!res.ok) throw new Error(data.error || 'Processing failed');

        // Show results
        results.hidden = false;
        
        // Handle original and processed images
        if (data.input) {
            imgInput.src = data.input;
        }
        if (data.processed) {
            imgProcessed.src = data.processed;
        }

        // Handle recreated images
        const showcaseSection = document.querySelector('.recreated-showcase');
        if (data.debug_files && data.debug_files.dots_mask) {
            const recreatedImages = [
                { src: data.debug_files.line_mask, label: 'Line Detection' },
                { src: data.debug_files.edges, label: 'Edge Detection' },
                { src: data.debug_files.dots_mask, label: 'Dot Detection' }
            ];

            const recreatedContent = document.querySelector('.showcase-item');
            recreatedContent.innerHTML = `
                <h3>Recreated Images</h3>
                <div class="recreated-grid">
                    ${recreatedImages.map(img => `
                        <div class="recreated-image-wrapper">
                            <img src="${img.src}" alt="${img.label}" class="recreated-image">
                        </div>
                    `).join('')}
                </div>
            `;

            showcaseSection.style.display = 'block';
        }
        
        // Handle SVG if available
        if (data.svg) {
            svgObject.data = data.svg;
            svgDownload.href = data.svg;
            svgDownload.classList.add('active');
        }
        
        // Update counters
        if (data.dots_count !== undefined && data.lines_count !== undefined) {
            countersBox.style.display = 'flex';
            animateCounter(el('dotsCount'), data.dots_count, 3000);
            animateCounter(el('linesCount'), data.lines_count, 3000);
        }
        
        statusBox.innerHTML = '';
        
    } catch (err) {
        console.error('Processing error:', err);
        statusBox.innerHTML = `<div class="error">Error: ${err.message}</div>`;
    } finally {
        form.querySelector('button').disabled = false;
    }
});

function animateCounter(element, target, duration = 3000) {
    let start = 0;
    const increment = target / (duration / 16);
    const startTime = performance.now();
    
    function updateCount(currentTime) {
        const elapsed = currentTime - startTime;
        if (elapsed >= duration) {
            element.textContent = target;
            return;
        }
        
        start = (elapsed / duration) * target;
        element.textContent = Math.round(start);
        requestAnimationFrame(updateCount);
    }
    
    requestAnimationFrame(updateCount);
}

// Define sample images
const SAMPLES = [
    '/samples/kolam1.jpg',
    '/samples/kolam2.jpg',
    '/samples/kolam3.jpg',
    '/samples/kolam4.jpg'
];

// Add image error handlers
[imgInput, imgProcessed].forEach(img => {
    if (!img) return;
    
    img.onerror = function() {
        console.error(`Failed to load image: ${this.src}`);
        this.style.display = 'none';
    };
    
    img.onload = function() {
        console.log(`Successfully loaded image: ${this.src}`);
        this.style.display = 'block';
    };
});

// Render sample images
function renderSamples() {
    const samplesWrap = el('samples');
    if (!samplesWrap) return;
    
    SAMPLES.forEach(src => {
        const btn = document.createElement('button');
        btn.className = 'sample-btn';
        
        const img = new Image();
        // Use relative path for samples
        img.src = `.${src}`;
        img.alt = 'Sample Kolam';
        
        img.onload = () => {
            btn.appendChild(img);
            samplesWrap.appendChild(btn);
            
            btn.addEventListener('click', () => {
                fetch(img.src)
                    .then(res => res.blob())
                    .then(blob => {
                        const file = new File([blob], src.split('/').pop(), { type: 'image/jpeg' });
                        const dataTransfer = new DataTransfer();
                        dataTransfer.items.add(file);
                        input.files = dataTransfer.files;
                        form.requestSubmit();
                    });
            });
        };
        
        img.onerror = () => console.error(`Failed to load sample: ${src}`);
    });
}

// Initialize samples on page load
renderSamples();


