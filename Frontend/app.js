const backend = window.BACKEND_BASE || 'http://127.0.0.1:5000';

function el(id){ return document.getElementById(id); }

const form = el('uploadForm');
const input = el('fileInput');
const statusBox = el('status');
const countersBox = el('counters');
const results = el('results');
const imgInput = el('imgInput');
const imgProcessed = el('imgProcessed');
const svgObject = el('svgObject');
const svgDownload = el('svgDownload');
const recreatedWrap = el('recreated');
const samplesWrap = el('samples');

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  if (!input.files[0]) return;
  statusBox.textContent = 'Uploading and processing…';
  if (countersBox) countersBox.textContent = '';
  form.querySelector('button').disabled = true;
  results.hidden = true;
  recreatedWrap.innerHTML = '';

  try {
    const fd = new FormData();
    fd.append('image', input.files[0]);
    const res = await fetch(`${backend}/upload`, { method: 'POST', body: fd });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Upload failed');

    // display
    imgInput.src = data.input;
    imgProcessed.src = data.processed;
    svgObject.data = data.svg;
    svgDownload.href = data.svg;
    svgDownload.download = 'kolam.svg';

    // Show specific recreation images: linemask, edges, dotsmask
    const selected = data.recreated && Array.isArray(data.recreated) ? data.recreated : (()=>{
      const list = [];
      if (data.debug_files){
        const map = data.debug_files;
        if (map.line_mask) list.push(map.line_mask);
        if (map.edges) list.push(map.edges);
        if (map.dots_mask || map.dotsmask) list.push(map.dots_mask || map.dotsmask);
      }
      return list;
    })();

    selected.forEach((url) => {
      const figure = document.createElement('div');
      const img = document.createElement('img');
      img.src = url; img.alt = 'recreated';
      figure.appendChild(img);
      recreatedWrap.appendChild(figure);
    });

    results.hidden = false;
    if (countersBox) countersBox.textContent = `Dots: ${data.dots_count} · Lines: ${data.lines_count} (may be inaccurate, still under development)`;
  } catch (err) {
    statusBox.textContent = `Error: ${err.message}`;
  } finally {
    form.querySelector('button').disabled = false;
  }
});

// Sample images support: when you share images, place them under Frontend/samples/ and reference here.
// Provide files named as below in Frontend/samples/ and they'll appear automatically.
const SAMPLES = [
  'samples/kolam1.jpg',
  'samples/kolam2.jpg',
  'samples/kolam3.jpg',
  'samples/kolam4.jpg'
];

async function loadSampleToInput(src){
  const res = await fetch(src);
  if (!res.ok) throw new Error('Sample not found');
  const blob = await res.blob();
  const filename = src.split('/').pop() || 'sample.jpg';
  const file = new File([blob], filename, { type: blob.type || 'image/jpeg' });
  const dt = new DataTransfer();
  dt.items.add(file);
  input.files = dt.files;
}

function renderSamples(){
  if (!samplesWrap) return;
  SAMPLES.forEach((src) => {
    const img = new Image();
    img.src = src;
    img.onload = () => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.title = 'Try this sample';
      btn.appendChild(img);
      btn.addEventListener('click', async () => {
        try {
          await loadSampleToInput(src);
          form.requestSubmit();
        } catch (e) {
          console.error(e);
        }
      });
      samplesWrap.appendChild(btn);
    };
    img.onerror = () => {};
  });
}

renderSamples();


