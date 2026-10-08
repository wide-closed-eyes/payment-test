#!/bin/bash
# Скрипт для тестирования API платежей с проверкой идемпотентности.
# Требует: curl, jq (опционально, но рекомендуется).
#
# Использование:
#   chmod +x scripts/test_api.sh
#   ./scripts/test_api.sh
#   HOST=http://localhost:8001 API_KEY=my-key ./scripts/test_api.sh

set -euo pipefail

HOST="${HOST:-http://localhost:8000}"
API_KEY="${API_KEY:-test-payment-123}"
CONTENT_TYPE="application/json"
IDEMPOTENCY_KEY="key-$RANDOM"

# Цветной вывод, если терминал поддерживает
if [ -t 1 ]; then
    GREEN='\033[0;32m'
    RED='\033[0;31m'
    YELLOW='\033[0;33m'
    NC='\033[0m'
else
    GREEN=''; RED=''; YELLOW=''; NC=''
fi

section() {
    echo
    echo -e "${YELLOW}============================================================${NC}"
    echo -e "${YELLOW}  $1${NC}"
    echo -e "${YELLOW}============================================================${NC}"
}

ok()   { echo -e "${GREEN}✓ $1${NC}"; }
fail() { echo -e "${RED}✗ $1${NC}"; }

# ---------------------------------------------------------------------------
# 1. Создание платежа
# ---------------------------------------------------------------------------
section "1. Создать платёж (Idempotency-Key: $IDEMPOTENCY_KEY)"

CREATE_RESPONSE=$(curl -sS -w "\n%{http_code}" \
    -X POST "$HOST/api/v1/payments" \
    -H "Content-Type: $CONTENT_TYPE" \
    -H "Idempotency-Key: $IDEMPOTENCY_KEY" \
    -H "X-API-Key: $API_KEY" \
    -d '{
        "amount": 10.11,
        "currency": "RUB",
        "description": "description",
        "metadata": {"user": "UserName"},
        "webhook_url": "https://example.com/webhook"
    }')

CREATE_BODY=$(echo "$CREATE_RESPONSE" | sed '$d')
CREATE_STATUS=$(echo "$CREATE_RESPONSE" | tail -n1)

echo "HTTP $CREATE_STATUS"
echo "$CREATE_BODY" | jq . 2>/dev/null || echo "$CREATE_BODY"

PAYMENT_ID=$(echo "$CREATE_BODY" | jq -r '.id // empty' 2>/dev/null)

if [ -z "$PAYMENT_ID" ]; then
    fail "Не удалось извлечь id платежа из ответа"
    exit 1
fi
ok "Создан платёж с id=$PAYMENT_ID"

# ---------------------------------------------------------------------------
# 2. Получение платежа по id
# ---------------------------------------------------------------------------
section "2. Получить платёж по id ($PAYMENT_ID)"

GET_RESPONSE=$(curl -sS -w "\n%{http_code}" \
    -X GET "$HOST/api/v1/payments/$PAYMENT_ID" \
    -H "Accept: $CONTENT_TYPE" \
    -H "X-API-Key: $API_KEY")

GET_BODY=$(echo "$GET_RESPONSE" | sed '$d')
GET_STATUS=$(echo "$GET_RESPONSE" | tail -n1)

echo "HTTP $GET_STATUS"
echo "$GET_BODY" | jq . 2>/dev/null || echo "$GET_BODY"

if [ "$GET_STATUS" = "200" ]; then
    ok "Платёж найден по id"
else
    fail "Платёж не найден (HTTP $GET_STATUS)"
fi

# ---------------------------------------------------------------------------
# 3. Проверка идемпотентности: тот же ключ, другое тело
# ---------------------------------------------------------------------------
section "3. Повторить платёж с тем же Idempotency-Key (ожидается ошибка 409)"

REPEAT_RESPONSE=$(curl -sS -w "\n%{http_code}" \
    -X POST "$HOST/api/v1/payments" \
    -H "Content-Type: $CONTENT_TYPE" \
    -H "Idempotency-Key: $IDEMPOTENCY_KEY" \
    -H "X-API-Key: $API_KEY" \
    -d '{
        "amount": 99.99,
        "currency": "RUB",
        "description": "another description",
        "metadata": {"target": "shopping"},
        "webhook_url": "http://localhost:12789/webhook"
    }')

REPEAT_BODY=$(echo "$REPEAT_RESPONSE" | sed '$d')
REPEAT_STATUS=$(echo "$REPEAT_RESPONSE" | tail -n1)

echo "HTTP $REPEAT_STATUS"
echo "$REPEAT_BODY" | jq . 2>/dev/null || echo "$REPEAT_BODY"

if [ "$REPEAT_STATUS" = "409" ] || [ "$REPEAT_STATUS" = "422" ]; then
    ok "Идемпотентность работает: повторный ключ отклонён (HTTP $REPEAT_STATUS)"
else
    fail "Ожидался 409/422, получен HTTP $REPEAT_STATUS"
fi

# ---------------------------------------------------------------------------
# 4. Создание платежа с другим Idempotency-Key
# ---------------------------------------------------------------------------
IDEMPOTENCY_KEY_2="$IDEMPOTENCY_KEY-2"
section "4. Создать платёж с другим Idempotency-Key ($IDEMPOTENCY_KEY_2)"

NEW_RESPONSE=$(curl -sS -w "\n%{http_code}" \
    -X POST "$HOST/api/v1/payments" \
    -H "Content-Type: $CONTENT_TYPE" \
    -H "Idempotency-Key: $IDEMPOTENCY_KEY_2" \
    -H "X-API-Key: $API_KEY" \
    -d '{
        "amount": 55.55,
        "currency": "USD",
        "description": "another payment",
        "metadata": {},
        "webhook_url": "http://localhost:12789/webhook"
    }')

NEW_BODY=$(echo "$NEW_RESPONSE" | sed '$d')
NEW_STATUS=$(echo "$NEW_RESPONSE" | tail -n1)

echo "HTTP $NEW_STATUS"
echo "$NEW_BODY" | jq . 2>/dev/null || echo "$NEW_BODY"

NEW_PAYMENT_ID=$(echo "$NEW_BODY" | jq -r '.id // empty' 2>/dev/null)

if [ -n "$NEW_PAYMENT_ID" ] && [ "$NEW_PAYMENT_ID" != "$PAYMENT_ID" ]; then
    ok "Создан новый платёж с id=$NEW_PAYMENT_ID (отличается от предыдущего)"
else
    fail "Не удалось создать новый платёж или id совпадает со старым"
fi

echo
echo -e "${GREEN}Все проверки выполнены.${NC}"