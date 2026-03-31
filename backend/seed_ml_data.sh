#!/usr/bin/env bash
# =============================================================================
# ML Training Data Seed Script
# Adds ~200 varied transactions across all categories to improve classifier
# benchmarking (TF-IDF vocabulary diversity + class balance).
# Designed to be run AFTER seed_data.sh — does not re-seed budgets or categories.
# Usage: ./seed_ml_data.sh [BASE_URL] [EMAIL] [PASSWORD]
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
read_env() {
    grep -E "^${1}=" "${SCRIPT_DIR}/.env" 2>/dev/null | head -1 | cut -d'=' -f2- | sed 's/[[:space:]]*#.*//' | xargs
}

BASE_URL="${1:-http://localhost:8000}"
API="${BASE_URL}/api/v1"
EMAIL="${2:-$(read_env FIRST_SUPERUSER_EMAIL)}"
PASSWORD="${3:-$(read_env FIRST_SUPERUSER_PASSWORD)}"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

if [ -z "$EMAIL" ] || [ -z "$PASSWORD" ]; then
  echo "Error: no credentials found. Set FIRST_SUPERUSER_EMAIL/FIRST_SUPERUSER_PASSWORD in .env"
  echo "       or pass as arguments: ./seed_ml_data.sh [URL] [EMAIL] [PASSWORD]"
  exit 1
fi

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
echo "  ML Training Data Seed"
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

# ---- Resolve category IDs from existing categories ----
echo -e "${YELLOW}[Resolving category IDs]${NC}"
ALL_RESP=$(req GET "${API}/categories/" "${AUTH[@]}")
ALL_BODY=$(echo "$ALL_RESP" | sed -n '2,$p')

resolve_cat() {
  local name="$1" type="$2"
  echo "$ALL_BODY" | python3 -c "
import sys, json
cats = json.load(sys.stdin)
match = next((c['id'] for c in cats if c['name'] == '${name}' and c['type'] == '${type}'), None)
print(match if match is not None else '')
" 2>/dev/null
}

GROCERIES_ID=$(resolve_cat "Groceries" "expense")
DINING_ID=$(resolve_cat "Dining" "expense")
UTILITIES_ID=$(resolve_cat "Utilities" "expense")
TRANSPORT_ID=$(resolve_cat "Transportation" "expense")
ENTERTAINMENT_ID=$(resolve_cat "Entertainment" "expense")
SHOPPING_ID=$(resolve_cat "Shopping" "expense")
HEALTHCARE_ID=$(resolve_cat "Health & Fitness" "expense")
RENT_ID=$(resolve_cat "Housing" "expense")
SALARY_ID=$(resolve_cat "Salary" "income")
FREELANCE_ID=$(resolve_cat "Freelance" "income")

for VAR in GROCERIES_ID DINING_ID UTILITIES_ID TRANSPORT_ID ENTERTAINMENT_ID SHOPPING_ID HEALTHCARE_ID RENT_ID SALARY_ID FREELANCE_ID; do
  if [ -z "${!VAR}" ]; then
    fail "Could not resolve category ID for ${VAR}" "Run seed_data.sh first"
    exit 1
  fi
  info "${VAR} = ${!VAR}"
done
echo ""

# ---- Post transactions ----
post_txn() {
  local amount="$1" date="$2" desc="$3" type="$4" cat_id="$5"
  local RESP STATUS BODY ID
  RESP=$(req POST "${API}/transactions/" "${AUTH[@]}" \
    -d "{\"amount\": ${amount}, \"transaction_date\": \"${date}\", \"description\": \"${desc}\", \"transaction_type\": \"${type}\", \"category_id\": ${cat_id}}")
  STATUS=$(echo "$RESP" | head -1)
  BODY=$(echo "$RESP" | sed -n '2,$p')
  ID=$(extract_json "$BODY" "['id']")
  if [ "$STATUS" = "201" ] && [ -n "$ID" ]; then
    ok "${date}  \$${amount}  ${desc}"
  else
    fail "${date} ${desc}" "HTTP $STATUS — $BODY"
  fi
}

# =============================================================================
# GROCERIES  (~22 varied descriptions)
# Mix of merchant names, generic descriptions, and non-keyword phrasing
# =============================================================================
echo -e "${YELLOW}[Groceries — 22 transactions]${NC}"
post_txn 68.50  "2025-09-03" "Whole Foods haul"                  "expense" "$GROCERIES_ID"
post_txn 112.30 "2025-09-14" "Trader Joe's weekly shop"          "expense" "$GROCERIES_ID"
post_txn 94.75  "2025-09-19" "Aldi grocery run"                  "expense" "$GROCERIES_ID"
post_txn 210.00 "2025-10-02" "Costco bulk order"                 "expense" "$GROCERIES_ID"
post_txn 55.40  "2025-10-17" "Safeway fresh produce"             "expense" "$GROCERIES_ID"
post_txn 78.90  "2025-10-23" "Walmart supercenter food items"    "expense" "$GROCERIES_ID"
post_txn 43.20  "2025-11-04" "Farmers market produce"            "expense" "$GROCERIES_ID"
post_txn 130.60 "2025-11-16" "Kroger pickup order"               "expense" "$GROCERIES_ID"
post_txn 62.15  "2025-11-28" "Organic produce delivery"          "expense" "$GROCERIES_ID"
post_txn 88.00  "2025-12-02" "Meal prep ingredients"             "expense" "$GROCERIES_ID"
post_txn 145.50 "2025-12-07" "Holiday baking supplies"           "expense" "$GROCERIES_ID"
post_txn 54.30  "2025-12-18" "Publix run"                        "expense" "$GROCERIES_ID"
post_txn 97.80  "2026-01-03" "Fresh vegetables and proteins"     "expense" "$GROCERIES_ID"
post_txn 63.45  "2026-01-11" "Supermarket delivery fee"          "expense" "$GROCERIES_ID"
post_txn 119.00 "2026-01-19" "Pantry restock"                    "expense" "$GROCERIES_ID"
post_txn 72.60  "2026-01-27" "Weekly food shopping"              "expense" "$GROCERIES_ID"
post_txn 46.90  "2026-02-04" "Morning market run"                "expense" "$GROCERIES_ID"
post_txn 89.20  "2026-02-09" "Instacart grocery delivery"        "expense" "$GROCERIES_ID"
post_txn 105.75 "2026-02-14" "Bulk dry goods purchase"           "expense" "$GROCERIES_ID"
post_txn 57.30  "2026-02-18" "Deli and bakery items"             "expense" "$GROCERIES_ID"
post_txn 81.00  "2026-02-22" "H-E-B weekly shop"                 "expense" "$GROCERIES_ID"
post_txn 38.50  "2026-02-27" "Late night grocery stop"           "expense" "$GROCERIES_ID"
echo ""

# =============================================================================
# DINING  (~22 varied descriptions)
# =============================================================================
echo -e "${YELLOW}[Dining — 22 transactions]${NC}"
post_txn 14.50  "2025-09-04" "Chipotle burrito bowl"             "expense" "$DINING_ID"
post_txn 6.75   "2025-09-09" "Starbucks morning coffee"          "expense" "$DINING_ID"
post_txn 32.40  "2025-09-15" "Sushi restaurant with coworkers"   "expense" "$DINING_ID"
post_txn 11.80  "2025-09-23" "McDonald's drive-thru"             "expense" "$DINING_ID"
post_txn 48.20  "2025-10-05" "Italian dinner downtown"           "expense" "$DINING_ID"
post_txn 22.60  "2025-10-12" "Thai takeout order"                "expense" "$DINING_ID"
post_txn 38.90  "2025-10-18" "Brunch with friends"               "expense" "$DINING_ID"
post_txn 17.30  "2025-10-26" "Taco spot for lunch"               "expense" "$DINING_ID"
post_txn 55.00  "2025-11-08" "Birthday dinner celebration"       "expense" "$DINING_ID"
post_txn 9.50   "2025-11-12" "Coffee and pastry"                 "expense" "$DINING_ID"
post_txn 26.75  "2025-11-19" "Ramen bar visit"                   "expense" "$DINING_ID"
post_txn 41.30  "2025-12-04" "DoorDash order"                    "expense" "$DINING_ID"
post_txn 18.90  "2025-12-09" "Sandwich shop for lunch"           "expense" "$DINING_ID"
post_txn 63.50  "2025-12-22" "Holiday work team dinner"          "expense" "$DINING_ID"
post_txn 29.40  "2025-12-30" "New Year Eve appetizers"           "expense" "$DINING_ID"
post_txn 12.60  "2026-01-07" "Uber Eats delivery"                "expense" "$DINING_ID"
post_txn 47.80  "2026-01-14" "GrubHub Chinese food"              "expense" "$DINING_ID"
post_txn 8.25   "2026-01-22" "Food truck lunch"                  "expense" "$DINING_ID"
post_txn 34.00  "2026-01-31" "Happy hour with colleagues"        "expense" "$DINING_ID"
post_txn 72.10  "2026-02-08" "Valentine dinner reservation"      "expense" "$DINING_ID"
post_txn 15.40  "2026-02-15" "Breakfast diner"                   "expense" "$DINING_ID"
post_txn 23.80  "2026-02-25" "Burger joint quick bite"           "expense" "$DINING_ID"
echo ""

# =============================================================================
# TRANSPORTATION  (~20 varied descriptions)
# =============================================================================
echo -e "${YELLOW}[Transportation — 20 transactions]${NC}"
post_txn 18.40  "2025-09-05" "Lyft to airport"                   "expense" "$TRANSPORT_ID"
post_txn 52.00  "2025-09-11" "Shell gas station fill-up"         "expense" "$TRANSPORT_ID"
post_txn 12.50  "2025-09-17" "Metro card top-up"                 "expense" "$TRANSPORT_ID"
post_txn 89.00  "2025-10-03" "Amtrak weekend ticket"             "expense" "$TRANSPORT_ID"
post_txn 27.30  "2025-10-08" "Parking garage downtown"           "expense" "$TRANSPORT_ID"
post_txn 14.80  "2025-10-15" "Uber surge ride"                   "expense" "$TRANSPORT_ID"
post_txn 45.00  "2025-10-20" "Monthly transit pass"              "expense" "$TRANSPORT_ID"
post_txn 38.60  "2025-11-06" "Highway toll charges"              "expense" "$TRANSPORT_ID"
post_txn 22.10  "2025-11-14" "Bike share annual membership"      "expense" "$TRANSPORT_ID"
post_txn 67.90  "2025-11-21" "Car oil change"                    "expense" "$TRANSPORT_ID"
post_txn 48.50  "2025-12-03" "Rideshare rides this week"         "expense" "$TRANSPORT_ID"
post_txn 110.00 "2025-12-10" "Rental car weekend"                "expense" "$TRANSPORT_ID"
post_txn 31.20  "2025-12-17" "Ferry ticket"                      "expense" "$TRANSPORT_ID"
post_txn 19.60  "2025-12-26" "Zipcar hourly rental"              "expense" "$TRANSPORT_ID"
post_txn 55.00  "2026-01-06" "Gas and highway tolls"             "expense" "$TRANSPORT_ID"
post_txn 24.40  "2026-01-13" "Subway and bus fare"               "expense" "$TRANSPORT_ID"
post_txn 40.00  "2026-01-21" "Lyft rides this week"              "expense" "$TRANSPORT_ID"
post_txn 76.50  "2026-01-28" "Tire rotation and service"         "expense" "$TRANSPORT_ID"
post_txn 16.80  "2026-02-06" "Commuter rail ticket"              "expense" "$TRANSPORT_ID"
post_txn 29.90  "2026-02-20" "Parking and tolls"                 "expense" "$TRANSPORT_ID"
echo ""

# =============================================================================
# UTILITIES  (~18 varied descriptions)
# =============================================================================
echo -e "${YELLOW}[Utilities — 18 transactions]${NC}"
post_txn 89.00  "2025-09-02" "Comcast internet bill"             "expense" "$UTILITIES_ID"
post_txn 143.50 "2025-09-13" "Electric company monthly payment"  "expense" "$UTILITIES_ID"
post_txn 72.30  "2025-10-02" "AT&T phone plan"                   "expense" "$UTILITIES_ID"
post_txn 38.60  "2025-10-10" "Water utility bill"                "expense" "$UTILITIES_ID"
post_txn 97.80  "2025-10-16" "Verizon wireless monthly"          "expense" "$UTILITIES_ID"
post_txn 55.40  "2025-11-02" "Natural gas bill"                  "expense" "$UTILITIES_ID"
post_txn 119.00 "2025-11-09" "Home internet service"             "expense" "$UTILITIES_ID"
post_txn 84.20  "2025-11-18" "T-Mobile monthly plan"             "expense" "$UTILITIES_ID"
post_txn 47.10  "2025-12-02" "Trash and recycling pickup"        "expense" "$UTILITIES_ID"
post_txn 162.40 "2025-12-13" "Winter electricity usage"          "expense" "$UTILITIES_ID"
post_txn 66.90  "2025-12-19" "Cell phone plan renewal"           "expense" "$UTILITIES_ID"
post_txn 91.50  "2026-01-02" "Xfinity internet and cable"        "expense" "$UTILITIES_ID"
post_txn 43.70  "2026-01-10" "Sewage and water services"         "expense" "$UTILITIES_ID"
post_txn 108.30 "2026-01-17" "Power bill high usage month"       "expense" "$UTILITIES_ID"
post_txn 78.60  "2026-01-25" "Broadband subscription"            "expense" "$UTILITIES_ID"
post_txn 52.00  "2026-02-02" "Gas heating bill"                  "expense" "$UTILITIES_ID"
post_txn 95.40  "2026-02-12" "Electric and internet bundle"      "expense" "$UTILITIES_ID"
post_txn 69.80  "2026-02-23" "Monthly phone bill"                "expense" "$UTILITIES_ID"
echo ""

# =============================================================================
# ENTERTAINMENT  (~20 varied descriptions)
# =============================================================================
echo -e "${YELLOW}[Entertainment — 20 transactions]${NC}"
post_txn 15.99  "2025-09-07" "Netflix monthly subscription"      "expense" "$ENTERTAINMENT_ID"
post_txn 9.99   "2025-09-16" "Spotify premium"                   "expense" "$ENTERTAINMENT_ID"
post_txn 24.00  "2025-09-25" "Movie theater tickets"             "expense" "$ENTERTAINMENT_ID"
post_txn 18.49  "2025-10-01" "Hulu with ads plan"                "expense" "$ENTERTAINMENT_ID"
post_txn 59.99  "2025-10-13" "Video game purchase"               "expense" "$ENTERTAINMENT_ID"
post_txn 35.00  "2025-10-21" "Bowling night with friends"        "expense" "$ENTERTAINMENT_ID"
post_txn 13.99  "2025-11-01" "Disney Plus renewal"               "expense" "$ENTERTAINMENT_ID"
post_txn 85.00  "2025-11-15" "Concert venue tickets"             "expense" "$ENTERTAINMENT_ID"
post_txn 12.99  "2025-11-24" "Xbox Game Pass monthly"            "expense" "$ENTERTAINMENT_ID"
post_txn 42.00  "2025-12-06" "Museum admission"                  "expense" "$ENTERTAINMENT_ID"
post_txn 28.50  "2025-12-11" "Comedy club show"                  "expense" "$ENTERTAINMENT_ID"
post_txn 75.00  "2025-12-23" "NYE event tickets"                 "expense" "$ENTERTAINMENT_ID"
post_txn 8.99   "2026-01-04" "Twitch subscription"               "expense" "$ENTERTAINMENT_ID"
post_txn 32.00  "2026-01-10" "Escape room activity"              "expense" "$ENTERTAINMENT_ID"
post_txn 19.99  "2026-01-16" "Steam game bundle"                 "expense" "$ENTERTAINMENT_ID"
post_txn 50.00  "2026-01-23" "Sports event tickets"              "expense" "$ENTERTAINMENT_ID"
post_txn 14.99  "2026-02-01" "Paramount Plus streaming"          "expense" "$ENTERTAINMENT_ID"
post_txn 46.00  "2026-02-11" "Mini golf and arcade"              "expense" "$ENTERTAINMENT_ID"
post_txn 22.50  "2026-02-19" "Board game cafe evening"           "expense" "$ENTERTAINMENT_ID"
post_txn 67.00  "2026-02-28" "Ticketmaster live show"            "expense" "$ENTERTAINMENT_ID"
echo ""

# =============================================================================
# SHOPPING  (~20 varied descriptions)
# =============================================================================
echo -e "${YELLOW}[Shopping — 20 transactions]${NC}"
post_txn 87.30  "2025-09-06" "Amazon Prime order"                "expense" "$SHOPPING_ID"
post_txn 145.00 "2025-09-18" "Nike shoes purchase"               "expense" "$SHOPPING_ID"
post_txn 62.50  "2025-09-27" "Target home run"                   "expense" "$SHOPPING_ID"
post_txn 210.00 "2025-10-07" "Fall wardrobe at Zara"             "expense" "$SHOPPING_ID"
post_txn 38.90  "2025-10-16" "eBay secondhand item"              "expense" "$SHOPPING_ID"
post_txn 129.00 "2025-10-24" "Best Buy gadget purchase"          "expense" "$SHOPPING_ID"
post_txn 74.40  "2025-11-05" "H&M seasonal clothing"             "expense" "$SHOPPING_ID"
post_txn 320.00 "2025-11-29" "Cyber Monday online shopping"      "expense" "$SHOPPING_ID"
post_txn 55.80  "2025-12-01" "Craft supplies for holiday gifts"  "expense" "$SHOPPING_ID"
post_txn 198.00 "2025-12-15" "IKEA home goods"                   "expense" "$SHOPPING_ID"
post_txn 92.60  "2025-12-21" "Department store gifts"            "expense" "$SHOPPING_ID"
post_txn 43.20  "2025-12-27" "Post-Christmas sale items"         "expense" "$SHOPPING_ID"
post_txn 168.00 "2026-01-08" "Apple Store accessory"             "expense" "$SHOPPING_ID"
post_txn 57.90  "2026-01-12" "Home decor purchase"               "expense" "$SHOPPING_ID"
post_txn 79.50  "2026-01-20" "Outdoor gear for hiking"           "expense" "$SHOPPING_ID"
post_txn 34.70  "2026-01-26" "Bookstore haul"                    "expense" "$SHOPPING_ID"
post_txn 115.00 "2026-02-03" "Online fashion order"              "expense" "$SHOPPING_ID"
post_txn 88.40  "2026-02-13" "Valentine apparel gift"            "expense" "$SHOPPING_ID"
post_txn 47.60  "2026-02-20" "Etsy handmade purchase"            "expense" "$SHOPPING_ID"
post_txn 136.00 "2026-02-26" "Wardrobe refresh"                  "expense" "$SHOPPING_ID"
echo ""

# =============================================================================
# HEALTH & FITNESS  (~18 varied descriptions)
# =============================================================================
echo -e "${YELLOW}[Health & Fitness — 18 transactions]${NC}"
post_txn 25.00  "2025-09-10" "CVS pharmacy run"                  "expense" "$HEALTHCARE_ID"
post_txn 40.00  "2025-09-24" "Gym membership monthly"            "expense" "$HEALTHCARE_ID"
post_txn 180.00 "2025-10-06" "Doctor copay and lab work"         "expense" "$HEALTHCARE_ID"
post_txn 55.00  "2025-10-22" "Dental cleaning visit"             "expense" "$HEALTHCARE_ID"
post_txn 32.80  "2025-11-03" "Walgreens prescription pickup"     "expense" "$HEALTHCARE_ID"
post_txn 75.00  "2025-11-11" "Yoga class monthly pass"           "expense" "$HEALTHCARE_ID"
post_txn 200.00 "2025-11-22" "Vision exam and new glasses"       "expense" "$HEALTHCARE_ID"
post_txn 90.00  "2025-12-08" "Physical therapy session"          "expense" "$HEALTHCARE_ID"
post_txn 145.00 "2025-12-16" "Urgent care visit"                 "expense" "$HEALTHCARE_ID"
post_txn 28.50  "2025-12-24" "Vitamin supplements order"         "expense" "$HEALTHCARE_ID"
post_txn 120.00 "2026-01-05" "Mental health therapy session"     "expense" "$HEALTHCARE_ID"
post_txn 65.00  "2026-01-16" "Chiropractic adjustment"           "expense" "$HEALTHCARE_ID"
post_txn 38.00  "2026-01-23" "Allergy medication CVS"            "expense" "$HEALTHCARE_ID"
post_txn 250.00 "2026-01-30" "Specialist referral visit"         "expense" "$HEALTHCARE_ID"
post_txn 44.00  "2026-02-05" "Massage therapy"                   "expense" "$HEALTHCARE_ID"
post_txn 18.99  "2026-02-16" "Protein powder and supplements"    "expense" "$HEALTHCARE_ID"
post_txn 95.00  "2026-02-21" "Annual physical exam"              "expense" "$HEALTHCARE_ID"
post_txn 60.00  "2026-02-28" "Fitness class drop-in"             "expense" "$HEALTHCARE_ID"
echo ""

# =============================================================================
# HOUSING  (~12 varied descriptions — rent is already well seeded)
# =============================================================================
echo -e "${YELLOW}[Housing — 12 transactions]${NC}"
post_txn 1500.00 "2025-09-01" "Monthly apartment rent"           "expense" "$RENT_ID"
post_txn 25.00   "2025-09-20" "Renter's insurance premium"       "expense" "$RENT_ID"
post_txn 1500.00 "2025-10-01" "Lease payment October"            "expense" "$RENT_ID"
post_txn 150.00  "2025-10-28" "Plumber service call"             "expense" "$RENT_ID"
post_txn 1500.00 "2025-11-01" "November rent payment"            "expense" "$RENT_ID"
post_txn 85.00   "2025-11-30" "HOA monthly fee"                  "expense" "$RENT_ID"
post_txn 1500.00 "2025-12-01" "December landlord payment"        "expense" "$RENT_ID"
post_txn 200.00  "2025-12-29" "Storage unit rent"                "expense" "$RENT_ID"
post_txn 1500.00 "2026-01-01" "Apartment lease January"          "expense" "$RENT_ID"
post_txn 60.00   "2026-01-18" "Parking spot monthly"             "expense" "$RENT_ID"
post_txn 1500.00 "2026-02-01" "February housing payment"         "expense" "$RENT_ID"
post_txn 320.00  "2026-02-24" "Home repair plumbing"             "expense" "$RENT_ID"
echo ""

# =============================================================================
# INCOME — Salary  (~8 additional entries with varied descriptions)
# =============================================================================
echo -e "${YELLOW}[Salary income — 8 transactions]${NC}"
post_txn 4200.00 "2025-09-15" "Mid-month payroll deposit"        "income"  "$SALARY_ID"
post_txn 4200.00 "2025-10-15" "Bi-weekly paycheck"               "income"  "$SALARY_ID"
post_txn 4200.00 "2025-11-15" "Direct deposit wage"              "income"  "$SALARY_ID"
post_txn 4200.00 "2025-12-15" "Payroll November second half"     "income"  "$SALARY_ID"
post_txn 4200.00 "2026-01-15" "Salary mid-month"                 "income"  "$SALARY_ID"
post_txn 500.00  "2025-10-31" "Performance bonus payout"         "income"  "$SALARY_ID"
post_txn 750.00  "2025-12-31" "Year-end bonus"                   "income"  "$SALARY_ID"
post_txn 4200.00 "2026-02-15" "February paycheck"                "income"  "$SALARY_ID"
echo ""

# =============================================================================
# INCOME — Freelance  (~8 additional entries)
# =============================================================================
echo -e "${YELLOW}[Freelance income — 8 transactions]${NC}"
post_txn 1200.00 "2025-09-12" "Client invoice paid"              "income"  "$FREELANCE_ID"
post_txn 850.00  "2025-10-18" "Consulting contract payment"      "income"  "$FREELANCE_ID"
post_txn 400.00  "2025-11-08" "Side project completion"          "income"  "$FREELANCE_ID"
post_txn 650.00  "2025-12-05" "Freelance web contract"           "income"  "$FREELANCE_ID"
post_txn 300.00  "2025-12-28" "Design work payment"              "income"  "$FREELANCE_ID"
post_txn 950.00  "2026-01-09" "Contract client payment"          "income"  "$FREELANCE_ID"
post_txn 480.00  "2026-01-24" "Part-time consulting gig"         "income"  "$FREELANCE_ID"
post_txn 720.00  "2026-02-19" "Freelance invoice settled"        "income"  "$FREELANCE_ID"
echo ""

echo "============================================="
echo -e "  ${GREEN}ML seed complete!${NC}"
echo "  Added ~148 varied transactions across 10 categories."
echo "  Run the benchmark at: POST /api/v1/analytics/benchmark"
echo "============================================="
echo ""
