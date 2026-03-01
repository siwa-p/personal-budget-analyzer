#!/usr/bin/env bash
# =============================================================================
# Analytics Seed Data Script
# Seeds categories, 6 months of transactions, and Feb 2026 budgets into an
# existing user account for testing the analytics charts.
# Usage: ./seed_data.sh [BASE_URL] [EMAIL] [PASSWORD]
# =============================================================================

BASE_URL="${1:-http://localhost:8000}"
API="${BASE_URL}/api/v1"
EMAIL="${2:-}"
PASSWORD="${3:-}"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

if [ -z "$EMAIL" ]; then
  read -rp "Email: " EMAIL
fi
if [ -z "$PASSWORD" ]; then
  read -rs -p "Password: " PASSWORD
  echo
fi

# Helper: POST/GET/etc, returns "<status>\n<body>"
req() {
  local method="$1" url="$2"; shift 2
  local response
  response=$(curl -s -w "\n%{http_code}" "$url" -X "$method" "$@")
  echo "$(echo "$response" | tail -1)"
  echo "$response" | sed '$d'
}

extract_json() { echo "$1" | python3 -c "import sys,json; print(json.load(sys.stdin)$2)" 2>/dev/null; }

ok()   { echo -e "  ${GREEN}OK${NC}   $1"; }
fail() { echo -e "  ${RED}FAIL${NC} $1 — $2"; }
info() { echo -e "  ${CYAN}INFO${NC} $1"; }

echo ""
echo "============================================="
echo "  Analytics Seed Data"
echo "  ${BASE_URL}  →  ${EMAIL}"
echo "============================================="
echo ""

# ---- Login ----
echo -e "${YELLOW}[Login]${NC}"
RESPONSE=$(req POST "${API}/auth/login" \
  -d "username=${EMAIL}&password=${PASSWORD}")
STATUS=$(echo "$RESPONSE" | head -1)
BODY=$(echo "$RESPONSE" | sed -n '2,$p')

if [ "$STATUS" != "200" ]; then
  fail "Login" "HTTP $STATUS — $BODY"
  exit 1
fi
TOKEN=$(extract_json "$BODY" "['access_token']")
if [ -z "$TOKEN" ]; then
  fail "Login" "No access_token in response"
  exit 1
fi
ok "Logged in"
AUTH=(-H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json")
echo ""

# ---- Create Categories ----
echo -e "${YELLOW}[Categories]${NC}"

create_cat() {
  local name="$1" type="$2"
  local RESP STATUS BODY ID
  RESP=$(req POST "${API}/categories/" "${AUTH[@]}" \
    -d "{\"name\": \"${name}\", \"type\": \"${type}\"}")
  STATUS=$(echo "$RESP" | head -1)
  BODY=$(echo "$RESP" | sed -n '2,$p')
  ID=$(extract_json "$BODY" "['id']")
  if [ "$STATUS" = "201" ] && [ -n "$ID" ]; then
    ok "Created category '${name}' (id=${ID})" >&2
    echo "$ID"
  else
    # Try to find existing category by name
    local ALL_RESP ALL_BODY
    ALL_RESP=$(req GET "${API}/categories/" "${AUTH[@]}")
    ALL_BODY=$(echo "$ALL_RESP" | sed -n '2,$p')
    ID=$(echo "$ALL_BODY" | python3 -c "
import sys, json
cats = json.load(sys.stdin)
match = next((c['id'] for c in cats if c['name'] == '${name}' and c['type'] == '${type}'), None)
print(match if match is not None else '')
" 2>/dev/null)
    if [ -n "$ID" ]; then
      info "Category '${name}' already exists (id=${ID})" >&2
      echo "$ID"
    else
      fail "Category '${name}'" "HTTP $STATUS" >&2
      echo ""
    fi
  fi
}

GROCERIES_ID=$(create_cat "Groceries" "expense")
DINING_ID=$(create_cat "Dining Out" "expense")
UTILITIES_ID=$(create_cat "Utilities" "expense")
TRANSPORT_ID=$(create_cat "Transport" "expense")
ENTERTAINMENT_ID=$(create_cat "Entertainment" "expense")
SHOPPING_ID=$(create_cat "Shopping" "expense")
HEALTHCARE_ID=$(create_cat "Healthcare" "expense")
RENT_ID=$(create_cat "Rent" "expense")
SALARY_ID=$(create_cat "Salary" "income")
FREELANCE_ID=$(create_cat "Freelance" "income")
echo ""

# Validate we have the IDs we need
for VAR in GROCERIES_ID DINING_ID UTILITIES_ID TRANSPORT_ID ENTERTAINMENT_ID SHOPPING_ID HEALTHCARE_ID RENT_ID SALARY_ID FREELANCE_ID; do
  if [ -z "${!VAR}" ]; then
    fail "Missing category ID for ${VAR}" "Cannot continue"
    exit 1
  fi
done

# ---- Create Transactions (6 months) ----
# Months: Sep 2025 → Feb 2026 (current)
# Budget for Feb 2026:
#   Rent          $1500 → actual $1500 (exact, green)
#   Groceries      $300 → actual ~$252 (under, green)
#   Dining Out     $150 → actual ~$195 (over,  red)
#   Utilities      $150 → actual ~$118 (under, green)
#   Transport      $100 → actual  ~$72 (under, green)
#   Entertainment   $60 → actual  ~$85 (over,  red)
#   Shopping       $200 → actual ~$260 (over,  red)
#   Healthcare     $100 → actual  ~$45 (under, green)

echo -e "${YELLOW}[Transactions — 6 months]${NC}"

post_txn() {
  local amount="$1" date="$2" desc="$3" type="$4" cat_id="$5"
  local RESP STATUS BODY ID
  RESP=$(req POST "${API}/transactions/" "${AUTH[@]}" \
    -d "{\"amount\": ${amount}, \"transaction_date\": \"${date}\", \"description\": \"${desc}\", \"transaction_type\": \"${type}\", \"category_id\": ${cat_id}}")
  STATUS=$(echo "$RESP" | head -1)
  BODY=$(echo "$RESP" | sed -n '2,$p')
  ID=$(extract_json "$BODY" "['id']")
  if [ "$STATUS" = "201" ] && [ -n "$ID" ]; then
    ok "${date}  ${type}  \$${amount}  ${desc}"
  else
    fail "${date} ${desc}" "HTTP $STATUS — $BODY"
  fi
}

# September 2025
post_txn 4200.00 "2025-09-01" "September salary"      "income"  "$SALARY_ID"
post_txn 500.00  "2025-09-01" "Freelance project"     "income"  "$FREELANCE_ID"
post_txn 1500.00 "2025-09-01" "Rent"                  "expense" "$RENT_ID"
post_txn 280.00  "2025-09-06" "Grocery run"           "expense" "$GROCERIES_ID"
post_txn 45.00   "2025-09-08" "Dinner out"            "expense" "$DINING_ID"
post_txn 115.00  "2025-09-10" "Electric bill"         "expense" "$UTILITIES_ID"
post_txn 60.00   "2025-09-12" "Bus pass"              "expense" "$TRANSPORT_ID"
post_txn 35.00   "2025-09-20" "Movie tickets"         "expense" "$ENTERTAINMENT_ID"
post_txn 85.00   "2025-09-21" "Clothing"              "expense" "$SHOPPING_ID"
post_txn 190.00  "2025-09-22" "Grocery restock"       "expense" "$GROCERIES_ID"
post_txn 88.00   "2025-09-28" "Restaurant dinner"     "expense" "$DINING_ID"
post_txn 60.00   "2025-09-29" "Dentist visit"         "expense" "$HEALTHCARE_ID"

# October 2025
post_txn 4200.00 "2025-10-01" "October salary"        "income"  "$SALARY_ID"
post_txn 1500.00 "2025-10-01" "Rent"                  "expense" "$RENT_ID"
post_txn 310.00  "2025-10-04" "Weekly groceries"      "expense" "$GROCERIES_ID"
post_txn 72.00   "2025-10-09" "Lunch with friends"    "expense" "$DINING_ID"
post_txn 120.00  "2025-10-11" "Internet + electric"   "expense" "$UTILITIES_ID"
post_txn 75.00   "2025-10-14" "Rideshare rides"       "expense" "$TRANSPORT_ID"
post_txn 55.00   "2025-10-19" "Concert ticket"        "expense" "$ENTERTAINMENT_ID"
post_txn 140.00  "2025-10-22" "Fall wardrobe"         "expense" "$SHOPPING_ID"
post_txn 175.00  "2025-10-25" "Grocery run"           "expense" "$GROCERIES_ID"
post_txn 110.00  "2025-10-30" "Takeout week"          "expense" "$DINING_ID"

# November 2025
post_txn 4200.00 "2025-11-01" "November salary"       "income"  "$SALARY_ID"
post_txn 750.00  "2025-11-01" "Freelance project"     "income"  "$FREELANCE_ID"
post_txn 1500.00 "2025-11-01" "Rent"                  "expense" "$RENT_ID"
post_txn 340.00  "2025-11-03" "Thanksgiving groceries" "expense" "$GROCERIES_ID"
post_txn 130.00  "2025-11-07" "Holiday dining"        "expense" "$DINING_ID"
post_txn 105.00  "2025-11-10" "Electric bill"         "expense" "$UTILITIES_ID"
post_txn 85.00   "2025-11-13" "Fuel + transit"        "expense" "$TRANSPORT_ID"
post_txn 70.00   "2025-11-20" "Streaming + games"     "expense" "$ENTERTAINMENT_ID"
post_txn 220.00  "2025-11-23" "Black Friday shopping" "expense" "$SHOPPING_ID"
post_txn 145.00  "2025-11-25" "Grocery restock"       "expense" "$GROCERIES_ID"
post_txn 35.00   "2025-11-27" "Pharmacy"              "expense" "$HEALTHCARE_ID"

# December 2025
post_txn 4800.00 "2025-12-01" "December salary + bonus" "income" "$SALARY_ID"
post_txn 1500.00 "2025-12-01" "Rent"                  "expense" "$RENT_ID"
post_txn 420.00  "2025-12-05" "Holiday groceries"     "expense" "$GROCERIES_ID"
post_txn 210.00  "2025-12-12" "Holiday dinners"       "expense" "$DINING_ID"
post_txn 130.00  "2025-12-14" "Utilities"             "expense" "$UTILITIES_ID"
post_txn 90.00   "2025-12-16" "Rideshare + fuel"      "expense" "$TRANSPORT_ID"
post_txn 120.00  "2025-12-20" "Holiday events"        "expense" "$ENTERTAINMENT_ID"
post_txn 380.00  "2025-12-20" "Holiday gifts"         "expense" "$SHOPPING_ID"
post_txn 180.00  "2025-12-28" "Post-holiday groceries" "expense" "$GROCERIES_ID"

# January 2026
post_txn 4200.00 "2026-01-01" "January salary"        "income"  "$SALARY_ID"
post_txn 1500.00 "2026-01-01" "Rent"                  "expense" "$RENT_ID"
post_txn 290.00  "2026-01-05" "Weekly groceries"      "expense" "$GROCERIES_ID"
post_txn 95.00   "2026-01-09" "Lunch spots"           "expense" "$DINING_ID"
post_txn 118.00  "2026-01-12" "Electric bill"         "expense" "$UTILITIES_ID"
post_txn 68.00   "2026-01-15" "Bus pass"              "expense" "$TRANSPORT_ID"
post_txn 42.00   "2026-01-18" "Streaming services"    "expense" "$ENTERTAINMENT_ID"
post_txn 95.00   "2026-01-20" "Winter sale shopping"  "expense" "$SHOPPING_ID"
post_txn 165.00  "2026-01-24" "Grocery run"           "expense" "$GROCERIES_ID"
post_txn 115.00  "2026-01-29" "Restaurant week"       "expense" "$DINING_ID"
post_txn 120.00  "2026-01-30" "Doctor visit + meds"   "expense" "$HEALTHCARE_ID"

# February 2026 — matches budgets below
# Rent          $1500 → $1500 (exact, green)
# Groceries      $300 → $252  (under, green)
# Dining Out     $150 → $195  (over,  red)
# Utilities      $150 → $118  (under, green)
# Transport      $100 → $72   (under, green)
# Entertainment   $60 → $85   (over,  red)
# Shopping       $200 → $260  (over,  red)
# Healthcare     $100 → $45   (under, green)
post_txn 4200.00 "2026-02-01" "February salary"       "income"  "$SALARY_ID"
post_txn 1500.00 "2026-02-01" "Rent"                  "expense" "$RENT_ID"
post_txn 162.00  "2026-02-03" "Grocery run"           "expense" "$GROCERIES_ID"
post_txn 90.00   "2026-02-07" "Date night dinner"     "expense" "$DINING_ID"
post_txn 118.00  "2026-02-10" "Electric + internet"   "expense" "$UTILITIES_ID"
post_txn 72.00   "2026-02-11" "Transit + rideshare"   "expense" "$TRANSPORT_ID"
post_txn 85.00   "2026-02-14" "Valentine events"      "expense" "$ENTERTAINMENT_ID"
post_txn 90.00   "2026-02-17" "Grocery restock"       "expense" "$GROCERIES_ID"
post_txn 105.00  "2026-02-21" "Work lunches"          "expense" "$DINING_ID"
post_txn 160.00  "2026-02-22" "Clothing haul"         "expense" "$SHOPPING_ID"
post_txn 100.00  "2026-02-24" "Valentine shopping"    "expense" "$SHOPPING_ID"
post_txn 45.00   "2026-02-25" "Pharmacy"              "expense" "$HEALTHCARE_ID"
post_txn 300.00  "2026-02-26" "Freelance payment"     "income"  "$FREELANCE_ID"
echo ""

# ---- Create Budgets for February 2026 ----
echo -e "${YELLOW}[Budgets — February 2026]${NC}"

post_budget() {
  local cat_id="$1" amount="$2" name="$3"
  local RESP STATUS BODY
  RESP=$(req POST "${API}/budgets/" "${AUTH[@]}" \
    -d "{\"year\": 2026, \"month\": 2, \"category_id\": ${cat_id}, \"amount\": ${amount}}")
  STATUS=$(echo "$RESP" | head -1)
  BODY=$(echo "$RESP" | sed -n '2,$p')
  if [ "$STATUS" = "201" ] || [ "$STATUS" = "200" ]; then
    ok "Budget: ${name} = \$${amount}"
  else
    fail "Budget ${name}" "HTTP $STATUS — $BODY"
  fi
}

post_budget "$RENT_ID"          1500.00 "Rent"
post_budget "$GROCERIES_ID"     300.00  "Groceries"
post_budget "$DINING_ID"        150.00  "Dining Out"
post_budget "$UTILITIES_ID"     150.00  "Utilities"
post_budget "$TRANSPORT_ID"     100.00  "Transport"
post_budget "$ENTERTAINMENT_ID"  60.00  "Entertainment"
post_budget "$SHOPPING_ID"      200.00  "Shopping"
post_budget "$HEALTHCARE_ID"    100.00  "Healthcare"
echo ""

echo "============================================="
echo -e "  ${GREEN}Seed complete!${NC}"
echo "  Open http://localhost:5173/analytics to view charts."
echo "============================================="
echo ""
