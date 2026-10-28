# payment-service

Тестовый сервис платежей: **FastAPI** + **Outbox pattern** + **RabbitMQ**.

## Запуск

```bash
docker compose up -d
```

API: http://localhost:8000 · RabbitMQ UI: http://localhost:15672 (guest / guest)

## Архитектура

Два независимых Python-сервиса, разделяющих одну PostgreSQL-базу:

**`api-service`** — принимает HTTP-запросы. При создании платежа записывает строку в `payments` и строку в `outbox_events` в одной транзакции, возвращает `202`. Фоновый `OutboxWorker` (asyncio task) каждую секунду читает необработанные события через `SELECT … FOR UPDATE SKIP LOCKED` и публикует их в RabbitMQ.

**`consumer`** — подписан на `payments.new` с ручным ack. Выполняет мок-обработку, вызывает webhook, обновляет статус платежа. При ошибках ретраит через TTL-очереди (5 с → 15 с → 45 с); после трёх попыток направляет сообщение в DLQ.

Outbox гарантирует, что платёж не потеряется при временной недоступности RabbitMQ: HTTP-запрос завершится успешно, событие будет опубликовано позже.

## API

Все эндпоинты требуют заголовок `X-API-Key`. Значение задаётся переменной окружения `API_KEY`.

---

### `POST /api/v1/payments` → `202 Accepted`

**Заголовки**

| Заголовок | Обязательный | Описание |
|---|---|---|
| `X-API-Key` | да | Ключ авторизации |
| `Idempotency-Key` | да | Уникальный ключ запроса (до 64 символов) |

**Тело**

```json
{
  "amount": 10.11,
  "currency": "RUB",
  "description": "Оплата заказа",
  "metadata": {"order_id": "123"},
  "webhook_url": "https://example.com/hook"
}
```

`currency`: `RUB` | `USD` | `EUR`

**Ответ**

```json
{
  "payment_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "status": "pending",
  "created_at": "28-10-2026 12:34"
}
```

**Коды ошибок**

| Код | Причина |
|---|---|
| `403` | Неверный `X-API-Key` |
| `409` | Платёж с таким `Idempotency-Key` уже существует |
| `422` | Некорректное тело запроса |

---

### `GET /api/v1/payments/{payment_id}` → `200 OK`

**Заголовки**: `X-API-Key` (обязательно).

**Ответ**

```json
{
  "payment_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "amount": 10.11,
  "currency": "RUB",
  "description": "Оплата заказа",
  "metadata": {"order_id": "123"},
  "status": "succeeded",
  "idempotency_key": "order-123",
  "webhook_url": "https://example.com/hook",
  "created_at": "28-10-2026 12:34",
  "updated_at": "28-10-2026 12:35"
}
```

`status`: `pending` | `succeeded` | `failed`

**Коды ошибок**: `403` — неверный ключ, `404` — платёж не найден.

---

## Тесты

### e2e

```bash
chmod +x tests/curl.sh && ./tests/curl.sh
```

### Unit

```bash
# api-service
cd api-service && poetry install --with dev && poetry run pytest

# consumer
cd consumer && poetry install --with dev && poetry run pytest
```
