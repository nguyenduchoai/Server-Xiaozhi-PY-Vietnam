#!/bin/bash
# BYO & Device API Integration Tests
# Run: bash backend/tests/test_byo_device.sh

BASE_URL="http://localhost:8002/api/v1"
PASS=0
FAIL=0
TOTAL=0

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Get auth token
echo "🔐 Authenticating..."
TOKEN=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@xiaozhi-ai-iot.vn&password=Admin@123" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))")

if [ -z "$TOKEN" ]; then
  echo -e "${RED}❌ Authentication failed${NC}"
  exit 1
fi
echo -e "${GREEN}✅ Authenticated${NC}"
echo ""

# Test function
test_api() {
  local name="$1"
  local method="$2"
  local endpoint="$3"
  local data="$4"
  local expected_status="$5"
  local auth="$6"
  
  TOTAL=$((TOTAL + 1))
  
  HEADERS="-H 'Content-Type: application/json'"
  if [ "$auth" == "true" ]; then
    HEADERS="$HEADERS -H 'Authorization: Bearer $TOKEN'"
  fi
  
  if [ "$method" == "GET" ]; then
    RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL$endpoint" -H "Authorization: Bearer $TOKEN")
  elif [ "$method" == "POST" ]; then
    if [ -n "$data" ]; then
      RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL$endpoint" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $TOKEN" \
        -d "$data")
    else
      RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL$endpoint" \
        -H "Authorization: Bearer $TOKEN")
    fi
  elif [ "$method" == "POST_NOAUTH" ]; then
    RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL$endpoint" \
      -H "Content-Type: application/json" \
      -d "$data")
  elif [ "$method" == "DELETE" ]; then
    RESPONSE=$(curl -s -w "\n%{http_code}" -X DELETE "$BASE_URL$endpoint" \
      -H "Authorization: Bearer $TOKEN")
  elif [ "$method" == "PATCH" ]; then
    RESPONSE=$(curl -s -w "\n%{http_code}" -X PATCH "$BASE_URL$endpoint" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $TOKEN" \
      -d "$data")
  fi
  
  STATUS=$(echo "$RESPONSE" | tail -n1)
  BODY=$(echo "$RESPONSE" | sed '$d')
  
  if [ "$STATUS" == "$expected_status" ]; then
    echo -e "${GREEN}✅ PASS${NC}: $name (HTTP $STATUS)"
    PASS=$((PASS + 1))
    return 0
  else
    echo -e "${RED}❌ FAIL${NC}: $name (Expected $expected_status, Got $STATUS)"
    echo "   Response: $(echo $BODY | head -c 200)"
    FAIL=$((FAIL + 1))
    return 1
  fi
}

echo "=========================================="
echo "🔧 BYO (Bring Your Own Key) API Tests"
echo "=========================================="

# BYO Provider Tests
test_api "List providers (empty)" "GET" "/providers" "" "200" "true"
test_api "Create OpenAI provider" "POST" "/providers" '{"provider_type":"openai","api_key":"sk-test-key-12345","is_active":true}' "201" "true"
test_api "List providers (after create)" "GET" "/providers" "" "200" "true"
test_api "Get provider types" "GET" "/providers/types" "" "200" "true"

echo ""
echo "=========================================="
echo "📱 Device Activation API Tests"
echo "=========================================="

# Device Activation Flow
MAC="AA:BB:CC:DD:EE:$(printf '%02X' $RANDOM)"
echo "Testing with MAC: $MAC"

test_api "Request activation code" "POST_NOAUTH" "/devices/request-activation" "{\"mac_address\":\"$MAC\",\"board\":\"ESP32-S3\",\"firmware_version\":\"1.0.0\"}" "200" "false"

# Get the code from response
CODE_RESPONSE=$(curl -s -X POST "$BASE_URL/devices/request-activation" \
  -H "Content-Type: application/json" \
  -d "{\"mac_address\":\"${MAC}2\",\"board\":\"ESP32\"}")
CODE=$(echo $CODE_RESPONSE | python3 -c "import sys,json; print(json.load(sys.stdin).get('code',''))" 2>/dev/null)
echo "   Activation code received: $CODE"

test_api "Check activation status" "GET" "/devices/activation-status/${MAC}2" "" "200" "false"
test_api "Activate device with code" "POST" "/devices/activate" "{\"code\":\"$CODE\"}" "200" "true"
test_api "Activate with invalid code" "POST" "/devices/activate" "{\"code\":\"000000\"}" "400" "true"

echo ""
echo "=========================================="
echo "📋 Device Management API Tests"
echo "=========================================="

# Get device list
DEVICES_RESPONSE=$(curl -s "$BASE_URL/agents" -H "Authorization: Bearer $TOKEN")

# Test device CRUD via agents endpoint
test_api "List user agents (for devices)" "GET" "/agents" "" "200" "true"

echo ""
echo "=========================================="
echo "🔌 Device-Agent Binding Tests"
echo "=========================================="

# Create an agent first
AGENT_RESPONSE=$(curl -s -X POST "$BASE_URL/agents" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name":"Test Agent for Device","description":"Testing device binding"}')
AGENT_ID=$(echo $AGENT_RESPONSE | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',d).get('id',''))" 2>/dev/null)

if [ -n "$AGENT_ID" ] && [ "$AGENT_ID" != "" ]; then
  echo "   Created test agent: $AGENT_ID"
  test_api "Get agent details" "GET" "/agents/$AGENT_ID" "" "200" "true"
  test_api "List agent devices" "GET" "/agents/$AGENT_ID/devices" "" "200" "true"
else
  echo -e "${YELLOW}⚠️  Could not create test agent${NC}"
fi

echo ""
echo "=========================================="
echo "🔑 BYO Provider Validation Tests"
echo "=========================================="

test_api "Create provider without API key (should fail)" "POST" "/providers" '{"provider_type":"openai","api_key":"","is_active":true}' "422" "true"
test_api "Create provider with invalid type" "POST" "/providers" '{"provider_type":"invalid_provider","api_key":"test","is_active":true}' "422" "true"

echo ""
echo "=========================================="
echo "🛡️ Security Tests"
echo "=========================================="

test_api "Access providers without auth" "GET" "/providers" "" "401" "false"
test_api "Device activation no auth required" "POST_NOAUTH" "/devices/request-activation" '{"mac_address":"FF:FF:FF:FF:FF:FF"}' "200" "false"

echo ""
echo "=========================================="
echo "📊 Summary"
echo "=========================================="
echo ""
echo -e "Total: $TOTAL | ${GREEN}Pass: $PASS${NC} | ${RED}Fail: $FAIL${NC}"
echo ""

if [ $FAIL -eq 0 ]; then
  echo -e "${GREEN}✅ ALL TESTS PASSED${NC}"
  exit 0
else
  echo -e "${RED}❌ SOME TESTS FAILED${NC}"
  exit 1
fi
