'use strict';

const $ = (id) => document.getElementById(id);
const form = $('search-form');
const cityInput = $('city-input');
const submitButton = $('search-button');
const status = $('status');
const weatherCard = $('weather-card');
const jsonOutput = $('json-output');
const copyJsonButton = $('copy-json');
let latestRawJson = '';

function displayNumber(value, suffix) {
  return typeof value === 'number' && Number.isFinite(value)
    ? `${new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 1 }).format(value)} ${suffix}`
    : '—';
}

function weatherIconUrl(icon) {
  if (typeof icon !== 'string' || !icon) return null;
  try {
    const url = new URL(icon.startsWith('//') ? `https:${icon}` : icon);
    return url.protocol === 'https:' && url.hostname === 'cdn.weatherapi.com' ? url.href : null;
  } catch (_) { return null; }
}

function setStatus(message, type = '') {
  status.textContent = message;
  status.className = `status ${type}`;
}

function addMapRow(path, value) {
  const row = document.createElement('div');
  row.className = 'field-row';
  const field = document.createElement('code');
  field.textContent = path;
  const display = document.createElement('strong');
  display.textContent = value;
  row.append(field, display);
  $('field-map').append(row);
}

function renderWeather(data) {
  const { location, current } = data;
  if (!location || !current || typeof current.temp_c !== 'number') {
    throw new Error('Сервер вернул неожиданный формат погодных данных.');
  }
  $('place-name').textContent = location.name || 'Неизвестное место';
  $('place-region').textContent = [location.region, location.country].filter(Boolean).join(', ');
  $('updated-at').textContent = current.last_updated ? `Данные обновлены: ${current.last_updated} (местное время)` : '';
  $('temperature').textContent = displayNumber(current.temp_c, '°C');
  $('condition-text').textContent = current.condition?.text || 'Нет описания';
  $('feels-like').textContent = displayNumber(current.feelslike_c, '°C');
  $('humidity').textContent = displayNumber(current.humidity, '%');
  $('wind').textContent = displayNumber(current.wind_kph, 'км/ч');
  $('pressure').textContent = displayNumber(current.pressure_mb, 'гПа');
  const icon = weatherIconUrl(current.condition?.icon);
  const iconElement = $('condition-icon');
  iconElement.hidden = !icon;
  if (icon) iconElement.src = icon;
  weatherCard.hidden = false;

  $('field-map').replaceChildren();
  addMapRow('location.name', location.name ?? '—');
  addMapRow('current.temp_c', displayNumber(current.temp_c, '°C'));
  addMapRow('current.condition.text', current.condition?.text ?? '—');
  addMapRow('current.feelslike_c', displayNumber(current.feelslike_c, '°C'));
  addMapRow('current.humidity', displayNumber(current.humidity, '%'));
  addMapRow('current.wind_kph', displayNumber(current.wind_kph, 'км/ч'));
  addMapRow('current.pressure_mb', displayNumber(current.pressure_mb, 'гПа'));
}

async function requestWeather(city) {
  submitButton.disabled = true;
  submitButton.textContent = 'Загрузка…';
  setStatus('Получаем погодные данные…');
  weatherCard.hidden = true;
  const localUrl = `/api/weather?city=${encodeURIComponent(city)}`;
  $('client-url').textContent = localUrl;
  $('client-status').textContent = 'Выполняется…';
  $('client-status').classList.remove('success');
  $('provider-status').textContent = 'Ожидает ответа';
  $('provider-status').classList.remove('success');
  $('provider-url').textContent = `https://api.weatherapi.com/v1/current.json?key=***&q=${encodeURIComponent(city)}&lang=ru`;
  try {
    const response = await fetch(localUrl, { headers: { 'Accept': 'application/json' }, cache: 'no-store' });
    const payload = await response.json();
    $('client-status').textContent = `HTTP ${response.status}`;
    if (!response.ok) {
      if (payload.provider_status) $('provider-status').textContent = `HTTP ${payload.provider_status}`;
      throw new Error(payload.error || `HTTP ${response.status}`);
    }
    renderWeather(payload.weather);
    const trace = payload.trace;
    $('client-url').textContent = trace.browser.url;
    $('provider-url').textContent = trace.provider.url;
    $('client-status').textContent = `HTTP ${trace.browser.status}`;
    $('provider-status').textContent = `HTTP ${trace.provider.status}`;
    $('client-status').classList.add('success');
    $('provider-status').classList.add('success');
    latestRawJson = JSON.stringify(payload.weather, null, 2);
    jsonOutput.textContent = latestRawJson;
    copyJsonButton.disabled = false;
    setStatus('Данные получены от WeatherAPI.com.', 'ok');
  } catch (error) {
    latestRawJson = '';
    copyJsonButton.disabled = true;
    jsonOutput.textContent = 'Ответ не получен. Проверьте сообщение об ошибке и серверный терминал.';
    $('field-map').replaceChildren();
    const note = document.createElement('p');
    note.className = 'empty-map';
    note.textContent = 'Данные не получены.';
    $('field-map').append(note);
    setStatus(error instanceof TypeError ? 'Не удалось связаться с нашим сервером. Запустите python server.py.' : error.message, 'error');
  } finally {
    submitButton.disabled = false;
    submitButton.innerHTML = 'Показать погоду <span aria-hidden="true">→</span>';
  }
}

form.addEventListener('submit', (event) => {
  event.preventDefault();
  const city = cityInput.value.trim();
  if (city) requestWeather(city);
});

copyJsonButton.addEventListener('click', async () => {
  if (!latestRawJson) return;
  try {
    await navigator.clipboard.writeText(latestRawJson);
    copyJsonButton.textContent = 'Скопировано';
    setTimeout(() => { copyJsonButton.textContent = 'Копировать JSON'; }, 1800);
  } catch (_) {
    copyJsonButton.textContent = 'Не удалось скопировать';
  }
});
