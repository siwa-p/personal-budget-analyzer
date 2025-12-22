from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.session import engine, get_db
from app.db.base import Base, Users, Categories, Transactions, Bills
from pydantic import BaseModel
from datetime import date
# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
    
@app.get("/")
async def root():
    return {
        "message": "Welcome to Personal Budget Analyzer API",
        "version": settings.VERSION,
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION
    }

class TransactionCreate(BaseModel):
    user_id: int
    category_id: int
    amount: float
    description: str
    transaction_date: date
    bill_id: int
    transaction_type: str
    account_name: str

class CategoriesCreate(BaseModel):
    name: str
    type: str
    
    
@app.get("/users")
async def get_all_users(db: Session = Depends(get_db)):
    users = db.query(Users).all()
    return {
        "count": len(users),
        "users": [
            {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "balance": user.balance
            }
            for user in users
        ]
    }
    
@app.get("/categories")
async def get_all_categories(db: Session = Depends(get_db)):
    categories = db.query(Categories).all()
    return {
        "count": len(categories),
        "categories": [
            {
                "id": cat.id,
                "name": cat.name,
                "type": cat.type,
                "user_id": cat.user_id
            }
            for cat in categories
        ]
    }
    
@app.get("/categories/user/{user_id}")
async def get_categories_by_user(user_id: int | None = None, db: Session = Depends(get_db)):
    # Get both system categories (user_id=NULL) and user's custom categories
    if user_id is not None:
        categories = db.query(Categories).filter(
            (Categories.user_id == None) | (Categories.user_id == user_id)
        ).all()
    else:
        # If no user_id provided, return all categories
        categories = db.query(Categories).all()
    return {
        "count": len(categories),
        "categories": [
            {
                "id": cat.id,
                "name": cat.name,
                "type": cat.type,
                "user_id": cat.user_id
            }
            for cat in categories
        ]
    }

@app.post("/categories/create/{user_id}")
async def create_category(user_id: int, category: CategoriesCreate, db: Session = Depends(get_db)):
    # Verify user exists
    user = db.query(Users).filter_by(id=user_id).first()
    if not user:
        return {"error": "User not found"}, 404

    new_category = Categories(
        name=category.name,
        type=category.type,
        user_id=user_id
    )
    db.add(new_category)
    db.commit()
    db.refresh(new_category)
    return {
        "message": "Category created successfully",
        "category": {
            "id": new_category.id,
            "name": new_category.name,
            "type": new_category.type,
            "user_id": new_category.user_id
        }
    }
    
@app.post("/categories/{category_id}/update/{user_id}")
async def update_category(category_id: int, user_id: int, category: CategoriesCreate, db: Session = Depends(get_db)):
    existing_category = db.query(Categories).filter_by(id=category_id).first()
    if not existing_category:
        return {"error": "Category not found"}, 404

    # Only allow users to update their own categories
    if existing_category.user_id != user_id:
        return {"error": "You can only update your own categories"}, 403

    # Don't allow updating system categories (user_id is None)
    if existing_category.user_id is None:
        return {"error": "Cannot update system categories"}, 403

    existing_category.name = category.name
    existing_category.type = category.type
    # user_id stays the same - don't allow changing ownership

    db.commit()
    db.refresh(existing_category)
    return {
        "message": "Category updated successfully",
        "category": {
            "id": existing_category.id,
            "name": existing_category.name,
            "type": existing_category.type,
            "user_id": existing_category.user_id
        }
    }
    

@app.get("/test/bills")
async def get_all_bills(db: Session = Depends(get_db)):
    bills = db.query(Bills).all()
    return {
        "count": len(bills),
        "bills": [
            {
                "id": bill.id,
                "user_id": bill.user_id,
                "title": bill.title,
                "amount": bill.amount,
                "due_date": bill.due_date,
                "recurrence": bill.recurrence,
                "last_paid_date": bill.last_paid_date
            }
            for bill in bills
        ]
    }

@app.post("/transactions/create")
async def create_transaction(transaction: TransactionCreate, db: Session = Depends(get_db)):
    new_transaction = Transactions(
        user_id=transaction.user_id,
        category_id=transaction.category_id,
        amount=transaction.amount,
        description=transaction.description,
        transaction_date=transaction.transaction_date,
        bill_id=transaction.bill_id,
        transaction_type=transaction.transaction_type,
        account_name=transaction.account_name
    )
    db.add(new_transaction)
    db.commit()
    db.refresh(new_transaction)
    return {
        "message": "Transaction created successfully",
        "transaction": {
            "id": new_transaction.id,
            "user_id": new_transaction.user_id,
            "category_id": new_transaction.category_id,
            "amount": new_transaction.amount,
            "description": new_transaction.description,
            "transaction_date": new_transaction.transaction_date,
            "bill_id": new_transaction.bill_id,
            "transaction_type": new_transaction.transaction_type,
            "account_name": new_transaction.account_name
        }
    }

@app.get("/transactions")
async def get_all_transactions(
    page_number: int = 1,
    page_size: int = 10,
    user_id: int | None = None,
    category_id: int | None = None,
    transaction_type: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db)
):
    # Start building the query
    query = db.query(Transactions)

    # Apply filters
    if user_id is not None:
        query = query.filter(Transactions.user_id == user_id)
    if category_id is not None:
        query = query.filter(Transactions.category_id == category_id)
    if transaction_type is not None:
        query = query.filter(Transactions.transaction_type == transaction_type)
    if start_date is not None:
        query = query.filter(Transactions.transaction_date >= start_date)
    if end_date is not None:
        query = query.filter(Transactions.transaction_date <= end_date)
    total = query.count()
    # Calculate pagination metadata
    total_pages = (total + page_size - 1) // page_size  # Ceiling division
    # Apply sorting and pagination
    offset = (page_number - 1) * page_size
    transactions = query.order_by(Transactions.transaction_date.desc()).offset(offset).limit(page_size).all()
    return {
        "total": total,
        "page": page_number,
        "page_size": page_size,
        "total_pages": total_pages,
        "transactions": [
            {
                "id": transaction.id,
                "user_id": transaction.user_id,
                "category_id": transaction.category_id,
                "amount": transaction.amount,
                "description": transaction.description,
                "transaction_date": transaction.transaction_date,
                "bill_id": transaction.bill_id,
                "transaction_type": transaction.transaction_type,
                "account_name": transaction.account_name
            }
            for transaction in transactions
        ]
    }
    
@app.post("/transactions/{transaction_id}/update")
async def update_transaction(transaction_id: int, transaction: TransactionCreate, db: Session = Depends(get_db)):
    existing_transaction = db.query(Transactions).filter_by(id=transaction_id).first()
    if not existing_transaction:
        return {"error": "Transaction not found"}

    existing_transaction.user_id = transaction.user_id
    existing_transaction.category_id = transaction.category_id
    existing_transaction.amount = transaction.amount
    existing_transaction.description = transaction.description
    existing_transaction.transaction_date = transaction.transaction_date
    existing_transaction.bill_id = transaction.bill_id
    existing_transaction.transaction_type = transaction.transaction_type
    existing_transaction.account_name = transaction.account_name

    db.commit()
    db.refresh(existing_transaction)
    return {
        "message": "Transaction updated successfully",
        "transaction": {
            "id": existing_transaction.id,
            "user_id": existing_transaction.user_id,
            "category_id": existing_transaction.category_id,
            "amount": existing_transaction.amount,
            "description": existing_transaction.description,
            "transaction_date": existing_transaction.transaction_date,
            "bill_id": existing_transaction.bill_id,
            "transaction_type": existing_transaction.transaction_type,
            "account_name": existing_transaction.account_name
        }
    }

@app.post("/transactions/{transaction_id}/delete")
def delete_transaction(transaction_id: int, db: Session = Depends(get_db)):
    existing_transaction =db.query(Transactions).filter_by(id=transaction_id).first()
    if not existing_transaction:
        return {"error": "Transaction not found"}
    db.delete(existing_transaction)
    db.commit()
    return {"message": "Transaction deleted successfully"}
    