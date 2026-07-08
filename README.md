Авторизация через email (OTP)

FastAPI + SQLModel + SQLite. Регистрация и вход без пароля, подтверждение через одноразовый 6-значный код, отправляемый на email.

Технологии: Python 3.10+, FastAPI, SQLModel, SQLite, Pydantic v2, Uvicorn.

Установка и запуск:

```bash
python3 -m venv venv
source venv/bin/activate        # для Windows: venv\Scripts\activate

pip install -r requirements.txt

uvicorn main:app --reload
```

После запуска API доступен на http://127.0.0.1:8000, документация Swagger — на http://127.0.0.1:8000/docs

База данных app.db создаётся автоматически при первом запуске в той же папке, где лежит main.py.

Как проверить сценарий вручную через /docs:

1. POST /auth/register — тело запроса:
```json
{"email": "user@example.com"}
```
Код подтверждения выводится в консоль сервера (вместо реальной отправки письма используется print в терминал).

2. Скопировать 6-значный код из консоли сервера.

3. POST /auth/verify — тело запроса:
```json
{"email": "user@example.com", "code": "полученный код"}
```
Подтверждает email.

4. POST /auth/login — тело запроса:
```json
{"email": "user@example.com"}
```
Присылает новый код для входа, старый автоматически деактивируется.

5. Скопировать новый код из консоли.

6. POST /auth/confirm — тело запроса:
```json
{"email": "user@example.com", "code": "новый код"}
```
Подтверждает вход.


