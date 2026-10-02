const textModeButton = document.querySelector('#textModeButton');
const gifModeButton = document.querySelector('#gifModeButton');
const textWorkspace = document.querySelector('#textWorkspace');
const gifWorkspace = document.querySelector('#gifWorkspace');
const gifFileInput = document.querySelector('#gifFile');
const uploadZone = document.querySelector('#uploadZone');
const uploadTitle = document.querySelector('#uploadTitle');
const uploadHint = document.querySelector('#uploadHint');
const gifFileInfo = document.querySelector('#gifFileInfo');
const gifFileName = document.querySelector('#gifFileName');
const gifMetadata = document.querySelector('#gifMetadata');
const gifControls = document.querySelector('#gifControls');
const gifEmptyPreview = document.querySelector('#gifEmptyPreview');
const cropCanvas = document.querySelector('#cropCanvas');
const cropScreen = document.querySelector('#cropScreen');
const cropContext = cropCanvas.getContext('2d', { willReadFrequently: true });
const convertGifButton = document.querySelector('#convertGifButton');
const convertGifLabel = document.querySelector('#convertGifLabel');
const gifPreviewStatus = document.querySelector('#gifPreviewStatus');
const gifStatusMessage = document.querySelector('#gifStatusMessage');
const gifDownloadButton = document.querySelector('#gifDownloadButton');
const convertedGifPreview = document.querySelector('#convertedGifPreview');
const sourceSummary = document.querySelector('#sourceSummary');
const fitMode = document.querySelector('#fitMode');
const zoomSlider = document.querySelector('#zoom');
const zoomValue = document.querySelector('#zoomValue');
const thresholdSlider = document.querySelector('#threshold');
const thresholdValue = document.querySelector('#thresholdValue');
const speedSlider = document.querySelector('#speed');
const speedValue = document.querySelector('#speedValue');
const invertInput = document.querySelector('#invert');
const ditherInput = document.querySelector('#dither');

const MAX_GIF_BYTES = 20 * 1024 * 1024;
let sourceFile = null;
let sourceUrl = null;
let sourceImage = null;
let sourceMetadata = null;
let outputUrl = null;
let previewFrame = 0;
let previewRaf = 0;
let dragging = false;
let dragPoint = null;
let positionX = 0;
let positionY = 0;

function selectMode(mode) {
  const showGif = mode === 'gif';
  gifModeButton.classList.toggle('is-active', showGif);
  textModeButton.classList.toggle('is-active', !showGif);
  gifModeButton.setAttribute('aria-pressed', String(showGif));
  textModeButton.setAttribute('aria-pressed', String(!showGif));
  gifWorkspace.hidden = !showGif;
  textWorkspace.hidden = showGif;
}

function setGifStatus(message = '', success = false) {
  gifStatusMessage.textContent = message;
  gifStatusMessage.classList.toggle('success', success);
}

function revokeUrl(url) {
  if (url) URL.revokeObjectURL(url);
}

function updateLabels() {
  zoomValue.textContent = `${Number(zoomSlider.value).toFixed(2).replace('.', ',')}×`;
  thresholdValue.textContent = thresholdSlider.value;
  speedValue.textContent = `${Number(speedSlider.value).toFixed(2).replace('.', ',')}×`;
}

function transformedRect() {
  if (!sourceImage) return null;
  const targetWidth = 128;
  const targetHeight = 40;
  const fitScale = fitMode.value === 'cover'
    ? Math.max(targetWidth / sourceImage.naturalWidth, targetHeight / sourceImage.naturalHeight)
    : Math.min(targetWidth / sourceImage.naturalWidth, targetHeight / sourceImage.naturalHeight);
  const scale = fitScale * Number(zoomSlider.value);
  const width = sourceImage.naturalWidth * scale;
  const height = sourceImage.naturalHeight * scale;
  const dx = width >= targetWidth
    ? -Math.round((width - targetWidth) * (positionX + 100) / 200)
    : Math.round((targetWidth - width) * (positionX + 100) / 200);
  const dy = height >= targetHeight
    ? -Math.round((height - targetHeight) * (positionY + 100) / 200)
    : Math.round((targetHeight - height) * (positionY + 100) / 200);
  return { dx, dy, width, height };
}

function applyThresholdAndDither(pixels) {
  const threshold = Number(thresholdSlider.value);
  const values = new Float32Array(128 * 40);
  for (let pixel = 0; pixel < values.length; pixel += 1) {
    const offset = pixel * 4;
    const alpha = pixels.data[offset + 3] / 255;
    values[pixel] = (0.2126 * pixels.data[offset] + 0.7152 * pixels.data[offset + 1] + 0.0722 * pixels.data[offset + 2]) * alpha;
  }

  for (let y = 0; y < 40; y += 1) {
    for (let x = 0; x < 128; x += 1) {
      const index = y * 128 + x;
      const oldValue = values[index];
      const newValue = oldValue >= threshold ? 255 : 0;
      if (ditherInput.checked) {
        const error = oldValue - newValue;
        if (x + 1 < 128) values[index + 1] += error * 7 / 16;
        if (y + 1 < 40) {
          if (x > 0) values[index + 127] += error * 3 / 16;
          values[index + 128] += error * 5 / 16;
          if (x + 1 < 128) values[index + 129] += error / 16;
        }
      }
      const isWhite = invertInput.checked ? newValue === 0 : newValue === 255;
      const color = isWhite ? 255 : 0;
      const offset = index * 4;
      pixels.data[offset] = color;
      pixels.data[offset + 1] = color;
      pixels.data[offset + 2] = color;
      pixels.data[offset + 3] = 255;
    }
  }
}

function drawPreview() {
  if (!sourceImage || !sourceImage.complete || !sourceImage.naturalWidth) return;
  const rect = transformedRect();
  cropContext.clearRect(0, 0, 128, 40);
  cropContext.fillStyle = '#000';
  cropContext.fillRect(0, 0, 128, 40);
  cropContext.drawImage(sourceImage, rect.dx, rect.dy, rect.width, rect.height);
  const pixels = cropContext.getImageData(0, 0, 128, 40);
  applyThresholdAndDither(pixels);
  cropContext.putImageData(pixels, 0, 0);
}

function animatePreview() {
  if (!sourceImage) return;
  drawPreview();
  previewRaf = requestAnimationFrame(animatePreview);
}

function redrawPreview() {
  updateLabels();
  if (!sourceImage) return;
  revokeUrl(outputUrl);
  outputUrl = null;
  convertedGifPreview.hidden = true;
  convertedGifPreview.removeAttribute('src');
  cropCanvas.hidden = false;
  gifEmptyPreview.hidden = true;
  gifDownloadButton.classList.add('is-disabled');
  gifDownloadButton.setAttribute('aria-disabled', 'true');
  gifDownloadButton.removeAttribute('href');
  gifPreviewStatus.textContent = 'AJUSTANDO';
  setGifStatus('Prévia em preto e branco. Converta para gerar o GIF final.');
  drawPreview();
}

async function chooseGif(file) {
  if (!file) return;
  if (file.size > MAX_GIF_BYTES) {
    setGifStatus('O GIF deve ter no máximo 20 MB.');
    return;
  }
  if (!file.name.toLowerCase().endsWith('.gif')) {
    setGifStatus('Escolha um arquivo com extensão .gif.');
    return;
  }

  convertGifButton.disabled = true;
  setGifStatus('Validando e lendo o GIF…');
  const formData = new FormData();
  formData.append('file', file);
  try {
    const response = await fetch('/api/gif/inspect', { method: 'POST', body: formData });
    const metadata = await response.json();
    if (!response.ok) throw new Error(metadata.error || 'Não foi possível ler esse GIF.');

    cancelAnimationFrame(previewRaf);
    sourceFile = file;
    sourceMetadata = metadata;
    positionX = 0;
    positionY = 0;
    revokeUrl(sourceUrl);
    sourceUrl = URL.createObjectURL(file);
    sourceImage = new Image();
    sourceImage.onload = () => {
      previewFrame = 0;
      previewRaf = requestAnimationFrame(animatePreview);
      gifFileName.textContent = file.name;
      gifMetadata.textContent = `${metadata.width} × ${metadata.height} px · ${metadata.frames} quadros · ${(metadata.duration_ms / 1000).toFixed(2)} s`;
      sourceSummary.textContent = `${metadata.width} × ${metadata.height} · ${metadata.frames} quadros`;
      gifFileInfo.hidden = false;
      gifControls.hidden = false;
      uploadTitle.textContent = 'Trocar GIF';
      uploadHint.textContent = 'ou arraste outro arquivo · máximo 20 MB';
      convertGifButton.disabled = false;
      redrawPreview();
    };
    sourceImage.onerror = () => {
      clearGif();
      setGifStatus('O navegador não conseguiu abrir esse GIF.');
    };
    sourceImage.src = sourceUrl;
  } catch (error) {
    convertGifButton.disabled = true;
    setGifStatus(error instanceof Error ? error.message : 'Não foi possível abrir o GIF.');
  }
}

function clearGif() {
  cancelAnimationFrame(previewRaf);
  sourceImage = null;
  sourceFile = null;
  sourceMetadata = null;
  gifFileInput.value = '';
  gifFileInfo.hidden = true;
  gifControls.hidden = true;
  uploadTitle.textContent = 'Escolha um GIF animado';
  uploadHint.textContent = 'ou arraste o arquivo aqui · máximo 20 MB';
  sourceSummary.textContent = '—';
  convertGifButton.disabled = true;
  cropCanvas.hidden = true;
  convertedGifPreview.hidden = true;
  gifEmptyPreview.hidden = false;
  gifPreviewStatus.textContent = 'AGUARDANDO';
  revokeUrl(sourceUrl);
  revokeUrl(outputUrl);
  sourceUrl = null;
  outputUrl = null;
  gifDownloadButton.classList.add('is-disabled');
  gifDownloadButton.setAttribute('aria-disabled', 'true');
  gifDownloadButton.removeAttribute('href');
  setGifStatus('');
}

async function convertUploadedGif() {
  if (!sourceFile) return;
  convertGifButton.disabled = true;
  convertGifLabel.textContent = 'Convertendo…';
  gifPreviewStatus.textContent = 'CONVERTENDO';
  setGifStatus('Convertendo todos os quadros para 128 × 40…');
  const formData = new FormData();
  formData.append('file', sourceFile);
  formData.append('settings', JSON.stringify({
    fit: fitMode.value,
    zoom: Number(zoomSlider.value),
    position_x: positionX,
    position_y: positionY,
    threshold: Number(thresholdSlider.value),
    invert: invertInput.checked,
    dither: ditherInput.checked,
    speed: Number(speedSlider.value),
  }));
  try {
    const response = await fetch('/api/gif/convert', { method: 'POST', body: formData });
    if (!response.ok) {
      const payload = await response.json();
      throw new Error(payload.error || 'Falha ao converter o GIF.');
    }
    const result = await response.blob();
    revokeUrl(outputUrl);
    outputUrl = URL.createObjectURL(result);
    convertedGifPreview.src = outputUrl;
    convertedGifPreview.hidden = false;
    cropCanvas.hidden = true;
    gifDownloadButton.href = outputUrl;
    gifDownloadButton.setAttribute('aria-disabled', 'false');
    gifDownloadButton.classList.remove('is-disabled');
    gifPreviewStatus.textContent = 'PRONTO';
    setGifStatus('GIF convertido e pronto para baixar.', true);
  } catch (error) {
    gifPreviewStatus.textContent = 'ERRO';
    setGifStatus(error instanceof Error ? error.message : 'Falha ao converter o GIF.');
  } finally {
    convertGifButton.disabled = !sourceFile;
    convertGifLabel.textContent = 'Converter para OLED';
  }
}

textModeButton.addEventListener('click', () => selectMode('text'));
gifModeButton.addEventListener('click', () => selectMode('gif'));
gifFileInput.addEventListener('change', () => chooseGif(gifFileInput.files[0]));
document.querySelector('#removeGif').addEventListener('click', clearGif);
convertGifButton.addEventListener('click', convertUploadedGif);

for (const control of [fitMode, zoomSlider, thresholdSlider, speedSlider, invertInput, ditherInput]) {
  control.addEventListener('input', redrawPreview);
  control.addEventListener('change', redrawPreview);
}

uploadZone.addEventListener('dragover', (event) => {
  event.preventDefault();
  uploadZone.classList.add('is-dragging');
});
uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('is-dragging'));
uploadZone.addEventListener('drop', (event) => {
  event.preventDefault();
  uploadZone.classList.remove('is-dragging');
  chooseGif(event.dataTransfer.files[0]);
});

cropScreen.addEventListener('pointerdown', (event) => {
  if (!sourceImage || cropCanvas.hidden) return;
  dragging = true;
  dragPoint = { x: event.clientX, y: event.clientY };
  cropScreen.classList.add('is-dragging');
  cropScreen.setPointerCapture(event.pointerId);
});
cropScreen.addEventListener('pointermove', (event) => {
  if (!dragging || !sourceImage) return;
  const rect = cropScreen.getBoundingClientRect();
  const scaled = transformedRect();
  const extraX = Math.max(1, (scaled.width - 128) / 2);
  const extraY = Math.max(1, (scaled.height - 40) / 2);
  positionX = Math.max(-100, Math.min(100, positionX - (event.clientX - dragPoint.x) * (128 / rect.width) / extraX * 100));
  positionY = Math.max(-100, Math.min(100, positionY - (event.clientY - dragPoint.y) * (40 / rect.height) / extraY * 100));
  dragPoint = { x: event.clientX, y: event.clientY };
  drawPreview();
});
cropScreen.addEventListener('pointerup', () => { dragging = false; cropScreen.classList.remove('is-dragging'); });
cropScreen.addEventListener('pointercancel', () => { dragging = false; cropScreen.classList.remove('is-dragging'); });

gifDownloadButton.addEventListener('click', (event) => {
  if (gifDownloadButton.getAttribute('aria-disabled') === 'true') event.preventDefault();
});
window.addEventListener('beforeunload', () => {
  cancelAnimationFrame(previewRaf);
  revokeUrl(sourceUrl);
  revokeUrl(outputUrl);
});
