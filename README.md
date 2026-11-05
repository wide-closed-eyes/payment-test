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

**`consumer`** — подписан на `payments.new` с ручным ack. Эмулирует платёжный шлюз (задержка 2–5 с, 90 % `succeeded`, 10 % `failed`), сохраняет итоговый статус и затем отправляет webhook. Отказ шлюза — это обычный результат платежа, а не ошибка: он не ретраится. При технических ошибках, включая недоставленный webhook (нет соединения или ответ не 2xx), сообщение ретраится через TTL-очереди (5 с → 15 с → 45 с); после трёх попыток оно попадает в DLQ. При ретрае шлюз повторно не вызывается, отправляется только webhook.

Webhook доставляется по принципу at-least-once, поэтому получатель должен быть готов к повторам:

```json
{
  "payment_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "status": "succeeded",
  "amount": "10.11",
  "currency": "RUB",
  "metadata": {"order_id": "123"},
  "idempotency_key": "order-123"
}
```

Outbox гарантирует, что платёж не потеряется при временной недоступности RabbitMQ: HTTP-запрос завершится успешно, событие будет опубликовано позже. API также запускается без брокера: воркер подключается к RabbitMQ в фоне и повторяет попытки, пока тот не станет доступен.

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

`amount`: число, не меньше `0`

`currency`: `RUB` | `USD` | `EUR`

**Ответ**

```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "status": "pending",
  "created_at": "28-10-2026 12:34"
}
```

**Коды ошибок**

| Код | Причина |
|---|---|
| `401` | Отсутствует или неверен `X-API-Key` |
| `422` | Некорректное тело запроса или заголовки |

Повторный запрос с тем же `Idempotency-Key` не создаёт новый платёж: возвращается `202` с уже созданным платежом и его текущим статусом. Тело повторного запроса не сверяется с исходным.

---

### `GET /api/v1/payments/{payment_id}` → `200 OK`

**Заголовки**: `X-API-Key` (обязательно).

**Ответ**

```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
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

**Коды ошибок**: `401` — отсутствует или неверен ключ, `404` — платёж не найден.

---

## Тесты

### e2e

```bash
chmod +x tests/curl.sh && ./tests/curl.sh
```

### Unit

```bash
# api-service
cd api-service && poetry install --with dev --no-root && poetry run pytest

# consumer
cd consumer && poetry install --with dev --no-root && poetry run pytest
```
