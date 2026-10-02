const textArea = document.querySelector('#animationText');
const durationInput = document.querySelector('#duration');
const durationValue = document.querySelector('#durationValue');
const charCount = document.querySelector('#characterCount');
const lineCount = document.querySelector('#lineCount');
const generateButton = document.querySelector('#generateButton');
const buttonLabel = document.querySelector('#buttonLabel');
const previewStatus = document.querySelector('#previewStatus');
const statusMessage = document.querySelector('#statusMessage');
const previewImage = document.querySelector('#gifPreview');
const emptyPreview = document.querySelector('#emptyPreview');
const downloadButton = document.querySelector('#downloadButton');
const oledAnnouncement = document.querySelector('#oledAnnouncement');
const range = document.querySelector('#duration');
const MAX_COLUMNS = 21;
const MAX_LINES = 100;
const MAX_TEXT_LENGTH = 4096;
const BACKSLASH = String.fromCharCode(92);
const NEWLINE = String.fromCharCode(10);
const CARRIAGE_RETURN = String.fromCharCode(13);
let currentObjectUrl = null;

function tokenizeLine(line) {
  const glyphs = [];
  for (let index = 0; index < line.length;) {
    if (line[index] === BACKSLASH) {
      const digits = line.slice(index + 1, index + 4);
      if (digits.length !== 3 || [...digits].some((digit) => digit < '0' || digit > '9')) {
        throw new Error('Use escapes com três dígitos, como \\065.');
      }
      const code = Number(digits);
      if (code > 127) throw new Error('Os códigos de escape devem estar entre 000 e 127.');
      glyphs.push({ text: line.slice(index, index + 4), whitespace: code === 32 });
      index += 4;
      continue;
    }

    const glyph = String.fromCodePoint(line.codePointAt(index));
    glyphs.push({ text: glyph, whitespace: glyph === ' ' || glyph === '\t' });
    index += glyph.length;
  }
  return glyphs;
}

function wrapLine(line) {
  const glyphs = tokenizeLine(line);
  if (glyphs.length <= MAX_COLUMNS) return [line];

  const rows = [];
  let start = 0;
  while (glyphs.length - start > MAX_COLUMNS) {
    const limit = start + MAX_COLUMNS;
    let end = limit;
    for (let index = limit - 1; index > start; index -= 1) {
      if (glyphs[index].whitespace) {
        end = index + 1;
        break;
      }
    }
    rows.push(glyphs.slice(start, end).map((glyph) => glyph.text).join(''));
    start = end;
  }
  rows.push(glyphs.slice(start).map((glyph) => glyph.text).join(''));
  return rows;
}

function wrapText(text) {
  return text
    .replaceAll(CARRIAGE_RETURN + NEWLINE, NEWLINE)
    .replaceAll(CARRIAGE_RETURN, NEWLINE)
    .split(NEWLINE)
    .flatMap(wrapLine)
    .join(NEWLINE);
}

function updateTextMetrics() {
  let measuredText = textArea.value;
  let lines = measuredText.split(/\r\n|\r|\n/).length;
  try {
    measuredText = wrapText(measuredText);
    lines = measuredText.split(NEWLINE).length;
  } catch (_error) {
    // Keep the raw counts visible until the user corrects an invalid escape.
  }
  charCount.textContent = `${measuredText.length} / ${MAX_TEXT_LENGTH}`;
  lineCount.textContent = `${lines} ${lines === 1 ? 'linha' : 'linhas'} no OLED`;
}

function updateRange() {
  const min = Number(range.min);
  const max = Number(range.max);
  const progress = ((Number(range.value) - min) / (max - min)) * 100;
  range.style.setProperty('--range-progress', `${progress}%`);
  durationValue.textContent = range.value;
}

function setStatus(message = '', type = '') {
  statusMessage.textContent = message;
  statusMessage.classList.toggle('success', type === 'success');
}

function resetPreview() {
  if (currentObjectUrl) {
    URL.revokeObjectURL(currentObjectUrl);
    currentObjectUrl = null;
  }
  previewImage.removeAttribute('src');
  previewImage.hidden = true;
  emptyPreview.hidden = false;
  downloadButton.classList.add('is-disabled');
  downloadButton.setAttribute('aria-disabled', 'true');
  downloadButton.removeAttribute('href');
  previewStatus.textContent = 'AGUARDANDO';
}

async function generateAnimation() {
  let text;
  try {
    text = wrapText(textArea.value);
  } catch (error) {
    setStatus(error instanceof Error ? error.message : 'Verifique o código de escape digitado.');
    textArea.focus();
    return;
  }
  if (!text.trim()) {
    setStatus('Digite uma mensagem antes de criar a animação.');
    textArea.focus();
    return;
  }
  if (text.split(NEWLINE).length > MAX_LINES) {
    setStatus(`A animação pode ter no máximo ${MAX_LINES} linhas após a quebra automática.`);
    textArea.focus();
    return;
  }
  if (text.length > MAX_TEXT_LENGTH) {
    setStatus(`O texto formatado pode ter no máximo ${MAX_TEXT_LENGTH} caracteres.`);
    textArea.focus();
    return;
  }
  textArea.value = text;
  updateTextMetrics();
  generateButton.disabled = true;
  buttonLabel.textContent = 'Criando animação…';
  previewStatus.textContent = 'GERANDO';
  setStatus('');

  try {
    const response = await fetch('/api/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, duration: Number(durationInput.value) }),
    });
    const contentType = response.headers.get('content-type') || '';
    if (!response.ok) {
      const data = contentType.includes('application/json') ? await response.json() : null;
      throw new Error(data?.error || 'Não foi possível criar o GIF. Tente novamente.');
    }
    const gifBlob = await response.blob();
    if (currentObjectUrl) URL.revokeObjectURL(currentObjectUrl);
    currentObjectUrl = URL.createObjectURL(gifBlob);
    previewImage.onload = () => { oledAnnouncement.textContent = 'Animação pronta no display simulado.'; };
    previewImage.onerror = () => { setStatus('Não foi possível carregar a prévia do GIF.'); };
    previewImage.src = currentObjectUrl;
    previewImage.hidden = false;
    emptyPreview.hidden = true;
    downloadButton.href = currentObjectUrl;
    downloadButton.setAttribute('aria-disabled', 'false');
    downloadButton.classList.remove('is-disabled');
    previewStatus.textContent = 'ANIMANDO';
    setStatus('Pronto para o seu display OLED.', 'success');
  } catch (error) {
    resetPreview();
    setStatus(error instanceof Error ? error.message : 'Ocorreu um erro inesperado.');
  } finally {
    generateButton.disabled = false;
    buttonLabel.textContent = 'Criar animação';
  }
}

textArea.addEventListener('input', updateTextMetrics);
durationInput.addEventListener('input', updateRange);
generateButton.addEventListener('click', generateAnimation);
textArea.addEventListener('keydown', (event) => {
  if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') generateAnimation();
});
downloadButton.addEventListener('click', (event) => {
  if (downloadButton.getAttribute('aria-disabled') === 'true') event.preventDefault();
});
window.addEventListener('beforeunload', () => {
  if (currentObjectUrl) URL.revokeObjectURL(currentObjectUrl);
});

const helpDialog = document.querySelector('#helpDialog');
document.querySelector('#helpButton').addEventListener('click', () => helpDialog.showModal());
document.querySelector('#closeHelp').addEventListener('click', () => helpDialog.close());
document.querySelector('#doneHelp').addEventListener('click', () => helpDialog.close());
helpDialog.addEventListener('click', (event) => {
  if (event.target === helpDialog) helpDialog.close();
});

updateTextMetrics();
updateRange();
