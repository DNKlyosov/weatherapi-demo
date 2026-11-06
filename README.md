# Погода — интеграция с WeatherAPI.com

Небольшой веб-сайт для лекции по HTTP и API. Пользователь вводит город и видит **реальные текущие погодные данные** от [WeatherAPI.com](https://www.weatherapi.com/). В разделе «Как получены эти данные?» показаны HTTP-запросы, URL, исходный JSON-ответ и соответствие полей JSON элементам страницы.

## Как работает

```text
Браузер (HTML + JS)
    │ GET /api/weather?city=Белгород
    ▼
Наш Python-сервер (server.py; ключ в переменной окружения)
    │ GET https://api.weatherapi.com/v1/current.json?key=***&q=Белгород&lang=ru
    ▼
WeatherAPI.com → JSON → наш сервер → браузер → карточка погоды
```

Это **один внешний API-запрос** на получение погоды по названию города. В отличие от Open-Meteo, отдельный поиск координат для этого примера не нужен. API-ключ не отправляется браузеру и не хранится в репозитории. В сетевой панели браузера видно обращение к *нашему* серверу; исходящий запрос к WeatherAPI.com виден в терминале Python (с замаскированным ключом).

## Запуск в VS Code на Windows

1. Откройте эту папку через **File → Open Folder**.
2. Зарегистрируйтесь на [WeatherAPI.com](https://www.weatherapi.com/signup.aspx), найдите свой API-ключ в личном кабинете.
3. Откройте терминал PowerShell в VS Code и выполните:

   ```powershell
   Copy-Item .env.example .env
   code .env
   ```

4. Замените `ВСТАВЬТЕ_СВОЙ_КЛЮЧ` на ваш действующий ключ, сохраните `.env`.
5. Запустите сервер:

   ```powershell
   py server.py
   ```

6. Откройте **http://localhost:8000**. Введите «Белгород», нажмите **Показать погоду**.
7. Разверните **«Как получены эти данные?»**. Здесь видны URL, статусы, JSON и то, какие поля используются в карточке.
8. Остановите сервер: `Ctrl+C` в терминале.

Нужен установленный Python 3.10+; дополнительных пакетов нет.

### Проверка без ключа

Сайт откроется, но при нажатии кнопки покажет сообщение «API-ключ ещё не настроен». **Вымышленные погодные данные не подставляются.** Если ключ неверен или лимит исчерпан, показывается ошибка от WeatherAPI.com.

## GitHub Codespaces

1. Создайте репозиторий GitHub и загрузите эти файлы, включая папку `.devcontainer`. **Не загружайте `.env`** (файл исключён через `.gitignore`).
2. На GitHub откройте **Settings → Secrets and variables → Codespaces**, создайте секрет `WEATHERAPI_KEY` со значением ключа (для данного репозитория).
3. Выберите **Code → Codespaces → Create codespace on main**.
4. В терминале Codespaces выполните:

   ```bash
   python3 server.py
   ```

5. Во вкладке **PORTS** откройте порт **8000** через **Open in Browser**. По умолчанию порт Private, что подходит для преподавателя.

При открытии порта Public любой, у кого есть ссылка, сможет обращаться к нашему серверу, расходуя квоту вашего WeatherAPI.com. Для занятия лучше использовать Private и демонстрацию с экрана.

**GitHub Pages не подходит для этого варианта**, поскольку он публикует только статические файлы, а здесь нужен Python-сервер.

## Как показать на лекции (5–7 минут)

1. Откройте [документацию Realtime Weather API](https://www.weatherapi.com/docs/realtime-api/) и найдите поля `temp_c`, `humidity`, `wind_kph`, `condition.text`.
2. На странице [Request URL](https://www.weatherapi.com/docs/request/) найдите операцию `/v1/current.json`. В [Request Parameters](https://www.weatherapi.com/docs/request-parameters/) посмотрите параметры `key` и `q`, в [Multilingual](https://www.weatherapi.com/docs/multilingual/) — `lang=ru`.
3. Введите город на сайте. Откройте технический раздел и покажите два GET-запроса.
4. Откройте в браузере **F12 → Network → Fetch/XHR**. Укажите запрос `/api/weather?city=...`. Поясните, что это запрос **к нашему** серверу.
5. Вернитесь в терминал Python и покажите строку `[upstream] GET https://api.weatherapi.com/...` — это **запрос нашего сервера к внешнему API**.
6. В техническом разделе найдите поле `current.temp_c` в исходном JSON и то же значение в карточке погоды.

## Содержание репозитория

- `index.html` — структура страницы.
- `styles.css` — оформление и адаптивная вёрстка.
- `app.js` — браузерный `fetch('/api/weather?city=...')`, обработка ответа.
- `server.py` — локальный сервер и запрос к WeatherAPI.com с секретным ключом.
- `.env.example` — пример настройки; настоящий `.env` не публикуется.
- `.devcontainer/devcontainer.json` — проброс порта 8000 для Codespaces.
- `tests/test_server.py` — проверки серверной логики с искусственными ответами вместо настоящего сервиса.

## Документация WeatherAPI.com

- [Главная документация](https://www.weatherapi.com/docs/)
- [Request URL / API Methods](https://www.weatherapi.com/docs/request/)
- [Request Parameters](https://www.weatherapi.com/docs/request-parameters/)
- [Realtime API / JSON fields](https://www.weatherapi.com/docs/realtime-api/)
- [Коды ошибок](https://www.weatherapi.com/docs/error-codes/)

**Ограничения:** сетевое соединение из России зависит от провайдера/маршрутизации; его нужно проверить в вашей сети. Ответы без ключа не проверяют реальную погоду. При каждом нажатии «Показать погоду» сервер выполняет новый запрос WeatherAPI.com (если ключ настроен).
