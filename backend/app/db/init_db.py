from sqlalchemy.orm import Session

from app import crud, schemas
from app.core.logger_init import setup_logging

logger = setup_logging()


PREDEFINED_CATEGORIES = [
    {
        "name": "Groceries",
        "type": "expense",
        "description": "Supermarket and grocery store purchases",
        "icon": "🛒",
        "color": "#4CAF50"
    },
    {
        "name": "Dining",
        "type": "expense",
        "description": "Restaurants and eating out",
        "icon": "🍽️",
        "color": "#FF6B6B"
    },
    {
        "name": "Transportation",
        "type": "expense",
        "description": "All transportation costs",
        "icon": "🚗",
        "color": "#3498DB"
    },
    {
        "name": "Housing",
        "type": "expense",
        "description": "Home-related expenses",
        "icon": "🏠",
        "color": "#9C27B0"
    },
    {
        "name": "Utilities",
        "type": "expense",
        "description": "Electric, water, gas, internet",
        "icon": "💡",
        "color": "#F39C12"
    },
    {
        "name": "Entertainment",
        "type": "expense",
        "description": "Leisure and fun activities",
        "icon": "🎮",
        "color": "#E91E63"
    },
    {
        "name": "Shopping",
        "type": "expense",
        "description": "General shopping",
        "icon": "🛍️",
        "color": "#FF9800"
    },
    {
        "name": "Health & Fitness",
        "type": "expense",
        "description": "Medical and wellness",
        "icon": "🏥",
        "color": "#00BCD4"
    },
    {
        "name": "Personal Care",
        "type": "expense",
        "description": "Personal grooming and care",
        "icon": "💇",
        "color": "#CDDC39"
    },
    {
        "name": "Education",
        "type": "expense",
        "description": "Learning and development",
        "icon": "📚",
        "color": "#607D8B"
    },
    {
        "name": "Travel",
        "type": "expense",
        "description": "Trips and vacations",
        "icon": "✈️",
        "color": "#009688"
    },
    {
        "name": "Insurance",
        "type": "expense",
        "description": "All insurance premiums",
        "icon": "🛡️",
        "color": "#795548"
    },
    {
        "name": "Pets",
        "type": "expense",
        "description": "Pet care and supplies",
        "icon": "🐾",
        "color": "#8BC34A"
    },
    {
        "name": "Miscellaneous",
        "type": "expense",
        "description": "Other expenses",
        "icon": "📦",
        "color": "#9E9E9E"
    },
    {
        "name": "Salary",
        "type": "income",
        "description": "Regular employment income",
        "icon": "💰",
        "color": "#2ECC71"
    },
    {
        "name": "Freelance",
        "type": "income",
        "description": "Freelance and contract work",
        "icon": "💼",
        "color": "#1ABC9C"
    },
    {
        "name": "Investment",
        "type": "income",
        "description": "Dividends, interest, capital gains",
        "icon": "📈",
        "color": "#27AE60"
    },
    {
        "name": "Side Hustle",
        "type": "income",
        "description": "Additional income sources",
        "icon": "🚀",
        "color": "#16A085"
    },
    {
        "name": "Gift/Bonus",
        "type": "income",
        "description": "Gifts and bonuses",
        "icon": "🎁",
        "color": "#52BE80"
    },
    {
        "name": "Refund",
        "type": "income",
        "description": "Refunds and reimbursements",
        "icon": "↩️",
        "color": "#58D68D"
    }
]


def init_db(db: Session) -> None:
    logger.info("Starting database initialization...")

    existing_categories = crud.category.get_system_categories(db, limit=1000)
    if existing_categories:
        logger.info(f"Found {len(existing_categories)} existing system categories. Skipping initialization.")
        return

    logger.info("No system categories found. Creating predefined categories...")

    for cat_data in PREDEFINED_CATEGORIES:
        try:
            category_in = schemas.CategoryCreate(**cat_data)
            category = crud.category.create(db, obj_in=category_in, user_id=None)
            logger.info(f"Created system category: {cat_data['name']} (ID: {category.id})")
        except Exception as e:
            logger.error(f"Error creating category '{cat_data['name']}': {e!s}")

    logger.info("Database initialization completed!")
