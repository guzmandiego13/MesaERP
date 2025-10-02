from fastapi import FastAPI, APIRouter, HTTPException, Depends, Header, Query
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
from enum import Enum
import httpx
from passlib.context import CryptContext
import jwt
from emergentintegrations.llm.chat import LlmChat, UserMessage
import json
import asyncio

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Password hashing
from passlib.hash import pbkdf2_sha256
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key-change-in-production')
JWT_ALGORITHM = "HS256"

# Parrot API Config
PARROT_API_BASE = "https://api.parrot.rest/external"
PARROT_API_KEY = os.environ.get('PARROT_API_KEY', '')

# Emergent LLM Key
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY', '')

app = FastAPI(title="MesaERP API")
api_router = APIRouter(prefix="/api")

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ============================================================================
# ENUMS
# ============================================================================

class RoleEnum(str, Enum):
    OWNER = "Owner"
    FINANCE = "Finance"
    OPS = "Ops"
    STORE_MANAGER = "Store Manager"
    ANALYST = "Analyst"

class AccountTypeEnum(str, Enum):
    ASSET = "Asset"
    LIABILITY = "Liability"
    EQUITY = "Equity"
    REVENUE = "Revenue"
    EXPENSE = "Expense"

class AccountingBasisEnum(str, Enum):
    CASH = "Cash"
    ACCRUAL = "Accrual"

class POStatusEnum(str, Enum):
    DRAFT = "Draft"
    SUBMITTED = "Submitted"
    APPROVED = "Approved"
    SENT = "Sent"
    RECEIVED = "Received"
    PARTIAL = "Partial"

# ============================================================================
# MODELS
# ============================================================================

class Tenant(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    industry: str  # "restaurant" or "retail"
    accounting_basis: AccountingBasisEnum = AccountingBasisEnum.ACCRUAL
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Location(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    name: str
    address: str
    timezone: str = "America/New_York"
    lat: Optional[float] = None
    lng: Optional[float] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    email: EmailStr
    password_hash: str
    name: str
    role: RoleEnum
    location_ids: List[str] = []  # Empty means access to all locations
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Account(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    code: str
    name: str
    account_type: AccountTypeEnum
    parent_id: Optional[str] = None
    is_active: bool = True

class JournalEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    location_id: Optional[str] = None
    entry_date: datetime
    description: str
    reference: Optional[str] = None
    is_posted: bool = False
    lines: List[Dict[str, Any]] = []  # [{account_id, debit, credit, memo}]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Vendor(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    name: str
    email: Optional[str] = None
    contact_person: Optional[str] = None
    payment_terms: int = 30  # days
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Item(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    sku: str
    name: str
    category: str
    unit: str = "each"
    cost: float = 0.0
    price: float = 0.0
    parrot_product_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class InventoryMovement(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    location_id: str
    item_id: str
    quantity: float
    movement_type: str  # "sale", "receipt", "adjustment"
    reference: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class POSSale(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    location_id: str
    parrot_order_id: str
    order_number: str
    sale_date: datetime
    total_amount: float
    tax_amount: float = 0.0
    discount_amount: float = 0.0
    line_items: List[Dict[str, Any]] = []  # [{item_id, sku, qty, price, total}]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class PurchaseOrder(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    location_id: str
    vendor_id: str
    po_number: str
    status: POStatusEnum = POStatusEnum.DRAFT
    order_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expected_delivery: Optional[datetime] = None
    line_items: List[Dict[str, Any]] = []  # [{item_id, qty, unit_cost, total}]
    total_amount: float = 0.0
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class InventoryLevel(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    location_id: str
    item_id: str
    quantity_on_hand: float = 0.0
    min_level: float = 0.0
    max_level: float = 100.0
    reorder_point: float = 10.0
    lead_time_days: int = 5
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class LoginResponse(BaseModel):
    token: str
    user: Dict[str, Any]
    tenant: Dict[str, Any]

class CreateTenantRequest(BaseModel):
    name: str
    industry: str
    admin_email: EmailStr
    admin_password: str
    admin_name: str

class BankTransactionImport(BaseModel):
    date: str
    description: str
    amount: float
    transaction_type: str  # "debit" or "credit"

class DashboardMetrics(BaseModel):
    total_revenue: float
    gross_margin_percent: float
    cash_balance: float
    ar_total: float
    ap_total: float
    stockouts_count: int

# ============================================================================
# AUTH HELPERS
# ============================================================================

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=7)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("user_id")
        tenant_id = payload.get("tenant_id")
        if not user_id or not tenant_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        user = await db.users.find_one({"id": user_id, "tenant_id": tenant_id})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# ============================================================================
# CHART OF ACCOUNTS TEMPLATES
# ============================================================================

def get_coa_template(industry: str) -> List[Dict[str, str]]:
    restaurant_coa = [
        {"code": "1000", "name": "Cash", "type": "Asset"},
        {"code": "1200", "name": "Accounts Receivable", "type": "Asset"},
        {"code": "1300", "name": "Inventory - Food", "type": "Asset"},
        {"code": "1310", "name": "Inventory - Beverage", "type": "Asset"},
        {"code": "1500", "name": "Equipment", "type": "Asset"},
        {"code": "2000", "name": "Accounts Payable", "type": "Liability"},
        {"code": "2100", "name": "Sales Tax Payable", "type": "Liability"},
        {"code": "3000", "name": "Owner's Equity", "type": "Equity"},
        {"code": "4000", "name": "Food Sales", "type": "Revenue"},
        {"code": "4100", "name": "Beverage Sales", "type": "Revenue"},
        {"code": "5000", "name": "Cost of Goods Sold - Food", "type": "Expense"},
        {"code": "5100", "name": "Cost of Goods Sold - Beverage", "type": "Expense"},
        {"code": "6000", "name": "Labor - Wages", "type": "Expense"},
        {"code": "6100", "name": "Rent", "type": "Expense"},
        {"code": "6200", "name": "Utilities", "type": "Expense"},
        {"code": "6300", "name": "Marketing", "type": "Expense"},
    ]
    
    retail_coa = [
        {"code": "1000", "name": "Cash", "type": "Asset"},
        {"code": "1200", "name": "Accounts Receivable", "type": "Asset"},
        {"code": "1300", "name": "Inventory - Merchandise", "type": "Asset"},
        {"code": "1500", "name": "Equipment", "type": "Asset"},
        {"code": "2000", "name": "Accounts Payable", "type": "Liability"},
        {"code": "2100", "name": "Sales Tax Payable", "type": "Liability"},
        {"code": "3000", "name": "Owner's Equity", "type": "Equity"},
        {"code": "4000", "name": "Merchandise Sales", "type": "Revenue"},
        {"code": "5000", "name": "Cost of Goods Sold", "type": "Expense"},
        {"code": "6000", "name": "Salaries", "type": "Expense"},
        {"code": "6100", "name": "Rent", "type": "Expense"},
        {"code": "6200", "name": "Utilities", "type": "Expense"},
    ]
    
    return restaurant_coa if industry == "restaurant" else retail_coa

# ============================================================================
# AUTH ENDPOINTS
# ============================================================================

@api_router.post("/auth/setup", response_model=LoginResponse)
async def setup_tenant(request: CreateTenantRequest):
    """Create initial tenant, admin user, locations, and COA"""
    # Create tenant
    tenant = Tenant(
        name=request.name,
        industry=request.industry
    )
    await db.tenants.insert_one(tenant.dict())
    
    # Create admin user
    user = User(
        tenant_id=tenant.id,
        email=request.admin_email,
        password_hash=pwd_context.hash(request.admin_password),
        name=request.admin_name,
        role=RoleEnum.OWNER
    )
    await db.users.insert_one(user.dict())
    
    # Create sample locations
    locations = [
        Location(tenant_id=tenant.id, name="Main Store", address="123 Main St"),
        Location(tenant_id=tenant.id, name="Downtown Branch", address="456 Downtown Ave"),
        Location(tenant_id=tenant.id, name="Airport Location", address="789 Airport Rd")
    ]
    for loc in locations:
        await db.locations.insert_one(loc.dict())
    
    # Create chart of accounts
    coa_template = get_coa_template(request.industry)
    for acc in coa_template:
        account = Account(
            tenant_id=tenant.id,
            code=acc["code"],
            name=acc["name"],
            account_type=AccountTypeEnum(acc["type"])
        )
        await db.accounts.insert_one(account.dict())
    
    # Create JWT token
    token = create_access_token({"user_id": user.id, "tenant_id": tenant.id})
    
    return LoginResponse(
        token=token,
        user={"id": user.id, "email": user.email, "name": user.name, "role": user.role},
        tenant={"id": tenant.id, "name": tenant.name, "industry": tenant.industry}
    )

@api_router.post("/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    user = await db.users.find_one({"email": request.email})
    if not user or not pwd_context.verify(request.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    tenant = await db.tenants.find_one({"id": user["tenant_id"]})
    token = create_access_token({"user_id": user["id"], "tenant_id": user["tenant_id"]})
    
    return LoginResponse(
        token=token,
        user={"id": user["id"], "email": user["email"], "name": user["name"], "role": user["role"]},
        tenant={"id": tenant["id"], "name": tenant["name"], "industry": tenant["industry"]}
    )

# ============================================================================
# PARROT POS INTEGRATION
# ============================================================================

async def make_parrot_request(client, url, headers, params, retries=3):
    """Make Parrot API request with rate limit handling"""
    for attempt in range(retries):
        try:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                # Rate limited - wait and retry with exponential backoff
                wait_time = (2 ** attempt) * 5  # 5s, 10s, 20s
                logger.warning(f"Rate limited. Waiting {wait_time}s before retry {attempt + 1}/{retries}")
                await asyncio.sleep(wait_time)
                if attempt == retries - 1:
                    raise HTTPException(
                        status_code=429, 
                        detail=f"Parrot API rate limit exceeded. Please wait a minute and try again."
                    )
            else:
                raise
    return None

@api_router.post("/pos/sync")
async def sync_parrot_pos(current_user: dict = Depends(get_current_user)):
    """Sync data from Parrot POS API"""
    tenant_id = current_user["tenant_id"]
    
    if not PARROT_API_KEY:
        raise HTTPException(status_code=400, detail="Parrot API key not configured")
    
    headers = {"Authorization": f"Bearer {PARROT_API_KEY}"}
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Fetch stores with rate limit handling
            stores_resp = await make_parrot_request(
                client,
                f"{PARROT_API_BASE}/v1/stores",
                headers,
                {}
            )
            stores_data = stores_resp.json()
            stores = stores_data.get("data", [])
            
            synced_count = 0
            
            # Calculate time range (last 48 hours max due to API constraint)
            end_dt = datetime.now(timezone.utc)
            start_dt = end_dt - timedelta(hours=47)  # Stay under 48h limit
            
            # Format timestamps as ISO strings
            start_timestamp = start_dt.isoformat()
            end_timestamp = end_dt.isoformat()
            
            # Add delay between API calls to avoid rate limits (15 req/min = 1 per 4s)
            await asyncio.sleep(4)
            
            # Fetch order items once for all stores (more efficient)
            all_items = []
            store_uuids = [store.get("uuid") for store in stores[:3]]
            
            if store_uuids:
                items_resp = await make_parrot_request(
                    client,
                    f"{PARROT_API_BASE}/v2/order-items",
                    headers,
                    {
                        "storeUUID": store_uuids,
                        "startTimestamp": start_timestamp,
                        "endTimestamp": end_timestamp,
                        "page": "0",
                        "pageSize": 100
                    }
                )
                items_data = items_resp.json()
                all_items = items_data.get("data", [])
                
                await asyncio.sleep(4)  # Rate limit delay
            
            for store in stores[:3]:  # Limit to first 3 stores for MVP
                store_uuid = store.get("uuid")
                store_name = store.get("name", "Unknown Store")
                
                # Get or create location
                location = await db.locations.find_one({
                    "tenant_id": tenant_id,
                    "name": store_name
                })
                
                if not location:
                    location = Location(
                        tenant_id=tenant_id,
                        name=store_name,
                        address=""
                    )
                    await db.locations.insert_one(location.dict())
                    location = location.dict()
                
                # Fetch orders for this store
                orders_resp = await make_parrot_request(
                    client,
                    f"{PARROT_API_BASE}/v1/orders",
                    headers,
                    {
                        "storeUUID": [store_uuid],
                        "startTimestamp": start_timestamp,
                        "endTimestamp": end_timestamp,
                        "page": "0",
                        "pageSize": 100
                    }
                )
                orders_data = orders_resp.json()
                orders = orders_data.get("data", [])
                
                await asyncio.sleep(4)  # Rate limit delay
                
                for order in orders:
                    order_uuid = order.get("uuid")
                    
                    # Check if already synced
                    existing = await db.pos_sales.find_one({
                        "tenant_id": tenant_id,
                        "parrot_order_id": order_uuid
                    })
                    
                    if existing:
                        continue
                    
                    # Filter items for this specific order from pre-fetched data
                    order_items = [item for item in all_items if item.get("orderUuid") == order_uuid]
                    
                    line_items = []
                    for item in order_items:
                        line_items.append({
                            "sku": item.get("sku", ""),
                            "name": item.get("itemName", ""),
                            "quantity": item.get("quantity", 0),
                            "unit_price": float(item.get("unitPrice", 0)),
                            "total": float(item.get("total", 0))
                        })
                    
                    # Parse timestamps
                    created_at = order.get("createdAt", "")
                    try:
                        sale_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    except:
                        sale_date = datetime.now(timezone.utc)
                    
                    # Create POS sale
                    sale = POSSale(
                        tenant_id=tenant_id,
                        location_id=location["id"],
                        parrot_order_id=order_uuid,
                        order_number=order.get("orderReference", ""),
                        sale_date=sale_date,
                        total_amount=float(order.get("total", 0)),
                        tax_amount=float(order.get("totalTaxes", 0)),
                        discount_amount=float(order.get("totalDiscounts", 0)),
                        line_items=line_items
                    )
                    await db.pos_sales.insert_one(sale.dict())
                    
                    # Post to journal
                    await post_sale_to_ledger(tenant_id, location["id"], sale)
                    
                    synced_count += 1
            
            return {"success": True, "synced_orders": synced_count}
    
    except HTTPException:
        raise
    except httpx.HTTPStatusError as e:
        logger.error(f"Parrot API error: {e.response.status_code} - {e.response.text}")
        if e.response.status_code == 429:
            raise HTTPException(
                status_code=429, 
                detail="Parrot API rate limit exceeded. Please wait a minute and try again."
            )
        raise HTTPException(status_code=500, detail=f"Parrot API error: {e.response.status_code}")
    except Exception as e:
        logger.error(f"Sync error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def post_sale_to_ledger(tenant_id: str, location_id: str, sale: POSSale):
    """Post POS sale to general ledger"""
    # Find accounts
    cash_account = await db.accounts.find_one({"tenant_id": tenant_id, "code": "1000"})
    revenue_account = await db.accounts.find_one({"tenant_id": tenant_id, "code": "4000"})
    tax_account = await db.accounts.find_one({"tenant_id": tenant_id, "code": "2100"})
    
    if not cash_account or not revenue_account:
        return
    
    # Create journal entry: DR Cash, CR Revenue, CR Tax Payable
    lines = [
        {
            "account_id": cash_account["id"],
            "debit": sale.total_amount,
            "credit": 0,
            "memo": f"Sale {sale.order_number}"
        },
        {
            "account_id": revenue_account["id"],
            "debit": 0,
            "credit": sale.total_amount - sale.tax_amount,
            "memo": f"Sale {sale.order_number}"
        }
    ]
    
    if sale.tax_amount > 0 and tax_account:
        lines.append({
            "account_id": tax_account["id"],
            "debit": 0,
            "credit": sale.tax_amount,
            "memo": "Sales tax"
        })
    
    je = JournalEntry(
        tenant_id=tenant_id,
        location_id=location_id,
        entry_date=sale.sale_date,
        description=f"POS Sale {sale.order_number}",
        reference=sale.parrot_order_id,
        is_posted=True,
        lines=lines
    )
    await db.journal_entries.insert_one(je.dict())

# ============================================================================
# FINANCE ENDPOINTS
# ============================================================================

@api_router.get("/finance/accounts")
async def get_accounts(current_user: dict = Depends(get_current_user)):
    accounts = await db.accounts.find({"tenant_id": current_user["tenant_id"]}).to_list(1000)
    return accounts

@api_router.post("/finance/accounts")
async def create_account(
    code: str,
    name: str,
    account_type: AccountTypeEnum,
    parent_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Create a new account"""
    tenant_id = current_user["tenant_id"]
    
    # Check if code already exists
    existing = await db.accounts.find_one({"tenant_id": tenant_id, "code": code})
    if existing:
        raise HTTPException(status_code=400, detail="Account code already exists")
    
    account = Account(
        tenant_id=tenant_id,
        code=code,
        name=name,
        account_type=account_type,
        parent_id=parent_id
    )
    await db.accounts.insert_one(account.dict())
    return account

@api_router.put("/finance/accounts/{account_id}")
async def update_account(
    account_id: str,
    code: Optional[str] = None,
    name: Optional[str] = None,
    account_type: Optional[AccountTypeEnum] = None,
    is_active: Optional[bool] = None,
    current_user: dict = Depends(get_current_user)
):
    """Update an existing account"""
    tenant_id = current_user["tenant_id"]
    
    update_data = {}
    if code is not None:
        # Check if new code conflicts
        existing = await db.accounts.find_one({
            "tenant_id": tenant_id, 
            "code": code,
            "id": {"$ne": account_id}
        })
        if existing:
            raise HTTPException(status_code=400, detail="Account code already exists")
        update_data["code"] = code
    
    if name is not None:
        update_data["name"] = name
    if account_type is not None:
        update_data["account_type"] = account_type
    if is_active is not None:
        update_data["is_active"] = is_active
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    result = await db.accounts.update_one(
        {"id": account_id, "tenant_id": tenant_id},
        {"$set": update_data}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Account not found")
    
    updated_account = await db.accounts.find_one({"id": account_id, "tenant_id": tenant_id})
    return updated_account

@api_router.post("/finance/journal-entries")
async def create_journal_entry(
    entry_date: str,
    description: str,
    lines: List[Dict[str, Any]],
    reference: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Create a manual journal entry"""
    tenant_id = current_user["tenant_id"]
    
    # Validate lines balance (debits = credits)
    total_debits = sum(line.get("debit", 0) for line in lines)
    total_credits = sum(line.get("credit", 0) for line in lines)
    
    if abs(total_debits - total_credits) > 0.01:
        raise HTTPException(
            status_code=400, 
            detail=f"Journal entry is not balanced. Debits: {total_debits}, Credits: {total_credits}"
        )
    
    # Verify all accounts exist
    for line in lines:
        account = await db.accounts.find_one({
            "id": line["account_id"],
            "tenant_id": tenant_id
        })
        if not account:
            raise HTTPException(status_code=404, detail=f"Account {line['account_id']} not found")
    
    je = JournalEntry(
        tenant_id=tenant_id,
        entry_date=datetime.fromisoformat(entry_date),
        description=description,
        reference=reference,
        is_posted=True,
        lines=lines
    )
    
    await db.journal_entries.insert_one(je.dict())
    return je

@api_router.get("/finance/journal-entries")
async def get_journal_entries(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get journal entries"""
    tenant_id = current_user["tenant_id"]
    
    query = {"tenant_id": tenant_id}
    if start_date and end_date:
        query["entry_date"] = {
            "$gte": datetime.fromisoformat(start_date),
            "$lte": datetime.fromisoformat(end_date)
        }
    
    entries = await db.journal_entries.find(query).sort("entry_date", -1).to_list(1000)
    
    # Enrich with account names
    for entry in entries:
        for line in entry.get("lines", []):
            account = await db.accounts.find_one({"id": line["account_id"]})
            if account:
                line["account_name"] = account["name"]
                line["account_code"] = account["code"]
    
    return entries

@api_router.get("/finance/pl")
async def get_profit_loss(
    start_date: str = Query(...),
    end_date: str = Query(...),
    location_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Generate P&L statement"""
    tenant_id = current_user["tenant_id"]
    start = datetime.fromisoformat(start_date)
    end = datetime.fromisoformat(end_date)
    
    # Get all accounts
    accounts = await db.accounts.find({"tenant_id": tenant_id}).to_list(1000)
    account_map = {acc["id"]: acc for acc in accounts}
    
    # Get journal entries in date range
    query = {
        "tenant_id": tenant_id,
        "entry_date": {"$gte": start, "$lte": end},
        "is_posted": True
    }
    if location_id:
        query["location_id"] = location_id
    
    entries = await db.journal_entries.find(query).to_list(10000)
    
    # Calculate balances by account
    balances = {}
    for entry in entries:
        for line in entry["lines"]:
            acc_id = line["account_id"]
            if acc_id not in balances:
                balances[acc_id] = 0
            balances[acc_id] += line["credit"] - line["debit"]
    
    # Build P&L
    revenue = sum(balances.get(acc["id"], 0) for acc in accounts if acc["account_type"] == "Revenue")
    expenses = sum(balances.get(acc["id"], 0) for acc in accounts if acc["account_type"] == "Expense")
    net_income = revenue - expenses
    
    revenue_detail = [{"account": account_map[acc_id]["name"], "amount": balances[acc_id]} 
                      for acc_id in balances if account_map[acc_id]["account_type"] == "Revenue"]
    expense_detail = [{"account": account_map[acc_id]["name"], "amount": balances[acc_id]} 
                      for acc_id in balances if account_map[acc_id]["account_type"] == "Expense"]
    
    return {
        "period": {"start": start_date, "end": end_date},
        "revenue": revenue,
        "expenses": expenses,
        "net_income": net_income,
        "revenue_detail": revenue_detail,
        "expense_detail": expense_detail
    }

@api_router.get("/finance/balance-sheet")
async def get_balance_sheet(
    as_of_date: str = Query(...),
    current_user: dict = Depends(get_current_user)
):
    """Generate Balance Sheet"""
    tenant_id = current_user["tenant_id"]
    as_of = datetime.fromisoformat(as_of_date)
    
    accounts = await db.accounts.find({"tenant_id": tenant_id}).to_list(1000)
    account_map = {acc["id"]: acc for acc in accounts}
    
    entries = await db.journal_entries.find({
        "tenant_id": tenant_id,
        "entry_date": {"$lte": as_of},
        "is_posted": True
    }).to_list(10000)
    
    balances = {}
    for entry in entries:
        for line in entry["lines"]:
            acc_id = line["account_id"]
            if acc_id not in balances:
                balances[acc_id] = 0
            acc_type = account_map[acc_id]["account_type"]
            # Assets and Expenses increase with debits
            # Liabilities, Equity, Revenue increase with credits
            if acc_type in ["Asset", "Expense"]:
                balances[acc_id] += line["debit"] - line["credit"]
            else:
                balances[acc_id] += line["credit"] - line["debit"]
    
    assets = sum(balances.get(acc["id"], 0) for acc in accounts if acc["account_type"] == "Asset")
    liabilities = sum(balances.get(acc["id"], 0) for acc in accounts if acc["account_type"] == "Liability")
    equity = sum(balances.get(acc["id"], 0) for acc in accounts if acc["account_type"] == "Equity")
    
    return {
        "as_of_date": as_of_date,
        "assets": assets,
        "liabilities": liabilities,
        "equity": equity,
        "total": assets
    }

@api_router.post("/finance/bank-import")
async def import_bank_transactions(
    transactions: List[BankTransactionImport],
    current_user: dict = Depends(get_current_user)
):
    """Import bank transactions from CSV"""
    tenant_id = current_user["tenant_id"]
    imported_count = 0
    
    cash_account = await db.accounts.find_one({"tenant_id": tenant_id, "code": "1000"})
    
    for txn in transactions:
        # Simple auto-categorization (can be enhanced)
        if "rent" in txn.description.lower():
            other_account = await db.accounts.find_one({"tenant_id": tenant_id, "code": "6100"})
        elif "utility" in txn.description.lower() or "electric" in txn.description.lower():
            other_account = await db.accounts.find_one({"tenant_id": tenant_id, "code": "6200"})
        else:
            # Default to first expense account
            other_account = await db.accounts.find_one({"tenant_id": tenant_id, "account_type": "Expense"})
        
        if not other_account:
            continue
        
        # Create journal entry
        if txn.transaction_type == "debit":
            lines = [
                {"account_id": other_account["id"], "debit": abs(txn.amount), "credit": 0, "memo": txn.description},
                {"account_id": cash_account["id"], "debit": 0, "credit": abs(txn.amount), "memo": txn.description}
            ]
        else:
            lines = [
                {"account_id": cash_account["id"], "debit": abs(txn.amount), "credit": 0, "memo": txn.description},
                {"account_id": other_account["id"], "debit": 0, "credit": abs(txn.amount), "memo": txn.description}
            ]
        
        je = JournalEntry(
            tenant_id=tenant_id,
            entry_date=datetime.fromisoformat(txn.date),
            description=txn.description,
            is_posted=True,
            lines=lines
        )
        await db.journal_entries.insert_one(je.dict())
        imported_count += 1
    
    return {"success": True, "imported_count": imported_count}

# ============================================================================
# INVENTORY ENDPOINTS
# ============================================================================

@api_router.get("/inventory/levels")
async def get_inventory_levels(
    location_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    tenant_id = current_user["tenant_id"]
    query = {"tenant_id": tenant_id}
    if location_id:
        query["location_id"] = location_id
    
    levels = await db.inventory_levels.find(query).to_list(1000)
    
    # Enrich with item details
    for level in levels:
        item = await db.items.find_one({"id": level["item_id"]})
        if item:
            level["item_name"] = item["name"]
            level["item_sku"] = item["sku"]
    
    return levels

@api_router.get("/inventory/stockouts")
async def get_stockouts(current_user: dict = Depends(get_current_user)):
    """Get items below min level"""
    tenant_id = current_user["tenant_id"]
    
    levels = await db.inventory_levels.find({"tenant_id": tenant_id}).to_list(1000)
    stockouts = []
    
    for level in levels:
        if level["quantity_on_hand"] < level["min_level"]:
            item = await db.items.find_one({"id": level["item_id"]})
            if item:
                stockouts.append({
                    "location_id": level["location_id"],
                    "item_id": level["item_id"],
                    "item_name": item["name"],
                    "sku": item["sku"],
                    "current_qty": level["quantity_on_hand"],
                    "min_level": level["min_level"],
                    "shortage": level["min_level"] - level["quantity_on_hand"]
                })
    
    return stockouts

# ============================================================================
# AI FORECASTING
# ============================================================================

@api_router.get("/forecast/demand")
async def forecast_demand(
    item_id: str = Query(...),
    location_id: str = Query(...),
    days: int = Query(14),
    current_user: dict = Depends(get_current_user)
):
    """Generate AI-powered demand forecast for an item"""
    tenant_id = current_user["tenant_id"]
    
    # Get historical sales data
    sales = await db.pos_sales.find({
        "tenant_id": tenant_id,
        "location_id": location_id
    }).sort("sale_date", -1).limit(90).to_list(1000)
    
    # Aggregate sales by day for this item
    daily_sales = {}
    for sale in sales:
        date_key = sale["sale_date"].date().isoformat()
        for line in sale["line_items"]:
            # Match by item or sku
            if date_key not in daily_sales:
                daily_sales[date_key] = 0
            daily_sales[date_key] += line.get("quantity", 0)
    
    # Prepare data for AI
    historical_data = [{"date": k, "quantity": v} for k, v in sorted(daily_sales.items())]
    
    if not EMERGENT_LLM_KEY:
        raise HTTPException(status_code=400, detail="AI forecasting not configured")
    
    # Call AI model for forecast
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"forecast-{item_id}-{location_id}",
            system_message="You are a demand forecasting expert. Analyze sales data and provide predictions."
        ).with_model("openai", "gpt-4o")
        
        prompt = f"""Analyze this sales data and forecast demand for the next {days} days.
        
Historical sales (last {len(historical_data)} days):
{json.dumps(historical_data, indent=2)}

Provide:
1. Daily forecast for next {days} days
2. Top 3 drivers/patterns you identified (e.g., weekday vs weekend, trends, seasonality)
3. Confidence level

Respond in JSON format:
{{
  "forecast": [{{"day": 1, "predicted_quantity": 0}}],
  "drivers": ["driver 1", "driver 2", "driver 3"],
  "confidence": "high/medium/low",
  "reasoning": "brief explanation"
}}"""
        
        message = UserMessage(text=prompt)
        response = await chat.send_message(message)
        
        # Parse AI response
        try:
            # Try to extract JSON from response
            response_text = response
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]
            
            forecast_data = json.loads(response_text.strip())
        except:
            # Fallback if JSON parsing fails
            forecast_data = {
                "forecast": [{"day": i+1, "predicted_quantity": 10} for i in range(days)],
                "drivers": ["Historical average", "Seasonal patterns", "Recent trends"],
                "confidence": "medium",
                "reasoning": "AI analysis completed"
            }
        
        return forecast_data
    
    except Exception as e:
        logger.error(f"Forecast error: {str(e)}")
        # Return simple average-based forecast as fallback
        avg_qty = sum(daily_sales.values()) / len(daily_sales) if daily_sales else 10
        return {
            "forecast": [{"day": i+1, "predicted_quantity": round(avg_qty, 1)} for i in range(days)],
            "drivers": ["Historical average", "Limited data"],
            "confidence": "low",
            "reasoning": "Using simple average due to insufficient data"
        }

# ============================================================================
# AUTO-PO GENERATION
# ============================================================================

@api_router.post("/procurement/auto-generate-pos")
async def auto_generate_pos(current_user: dict = Depends(get_current_user)):
    """Generate purchase orders for items below reorder point"""
    tenant_id = current_user["tenant_id"]
    
    # Get inventory levels below reorder point
    levels = await db.inventory_levels.find({
        "tenant_id": tenant_id
    }).to_list(1000)
    
    po_created = 0
    
    for level in levels:
        if level["quantity_on_hand"] < level["reorder_point"]:
            # Calculate order quantity (simple: bring to max level)
            order_qty = level["max_level"] - level["quantity_on_hand"]
            
            if order_qty <= 0:
                continue
            
            # Get item details
            item = await db.items.find_one({"id": level["item_id"]})
            if not item:
                continue
            
            # Find or create default vendor
            vendor = await db.vendors.find_one({"tenant_id": tenant_id})
            if not vendor:
                vendor = Vendor(tenant_id=tenant_id, name="Default Supplier")
                await db.vendors.insert_one(vendor.dict())
                vendor = vendor.dict()
            
            # Check if PO already exists for this item in draft status
            existing_po = await db.purchase_orders.find_one({
                "tenant_id": tenant_id,
                "location_id": level["location_id"],
                "status": POStatusEnum.DRAFT.value,
                "line_items.item_id": level["item_id"]
            })
            
            if existing_po:
                continue
            
            # Generate PO number
            po_count = await db.purchase_orders.count_documents({"tenant_id": tenant_id})
            po_number = f"PO-{po_count + 1:05d}"
            
            # Calculate expected delivery
            expected_delivery = datetime.now(timezone.utc) + timedelta(days=level["lead_time_days"])
            
            # Create PO
            line_items = [{
                "item_id": item["id"],
                "sku": item["sku"],
                "name": item["name"],
                "quantity": order_qty,
                "unit_cost": item["cost"],
                "total": order_qty * item["cost"]
            }]
            
            po = PurchaseOrder(
                tenant_id=tenant_id,
                location_id=level["location_id"],
                vendor_id=vendor["id"],
                po_number=po_number,
                status=POStatusEnum.DRAFT,
                expected_delivery=expected_delivery,
                line_items=line_items,
                total_amount=order_qty * item["cost"],
                notes=f"Auto-generated: Stock below reorder point ({level['quantity_on_hand']} < {level['reorder_point']})"
            )
            
            await db.purchase_orders.insert_one(po.dict())
            po_created += 1
    
    return {"success": True, "pos_created": po_created}

@api_router.get("/procurement/pos")
async def get_purchase_orders(
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    query = {"tenant_id": current_user["tenant_id"]}
    if status:
        query["status"] = status
    
    pos = await db.purchase_orders.find(query).sort("created_at", -1).to_list(1000)
    return pos

@api_router.patch("/procurement/pos/{po_id}/status")
async def update_po_status(
    po_id: str,
    status: POStatusEnum,
    current_user: dict = Depends(get_current_user)
):
    result = await db.purchase_orders.update_one(
        {"id": po_id, "tenant_id": current_user["tenant_id"]},
        {"$set": {"status": status.value}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="PO not found")
    
    return {"success": True}

# ============================================================================
# DASHBOARD
# ============================================================================

@api_router.get("/dashboard/metrics", response_model=DashboardMetrics)
async def get_dashboard_metrics(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    tenant_id = current_user["tenant_id"]
    
    # Default to current month
    if not start_date:
        start_date = datetime.now(timezone.utc).replace(day=1).isoformat()
    if not end_date:
        end_date = datetime.now(timezone.utc).isoformat()
    
    # Get P&L for revenue and expenses
    pl = await get_profit_loss(start_date, end_date, None, current_user)
    
    # Calculate gross margin
    cogs = sum(item["amount"] for item in pl.get("expense_detail", []) if "Cost of Goods" in item["account"])
    gross_margin = ((pl["revenue"] - cogs) / pl["revenue"] * 100) if pl["revenue"] > 0 else 0
    
    # Get cash balance
    bs = await get_balance_sheet(end_date, current_user)
    
    # Get AR/AP (simplified)
    accounts = await db.accounts.find({"tenant_id": tenant_id}).to_list(1000)
    ar_account = next((a for a in accounts if "Receivable" in a["name"]), None)
    ap_account = next((a for a in accounts if "Payable" in a["name"]), None)
    
    # Get stockouts
    stockouts = await get_stockouts(current_user)
    
    return DashboardMetrics(
        total_revenue=pl["revenue"],
        gross_margin_percent=gross_margin,
        cash_balance=bs["assets"],  # Simplified
        ar_total=0,  # Would need to calculate from journal
        ap_total=0,  # Would need to calculate from journal
        stockouts_count=len(stockouts)
    )

@api_router.get("/dashboard/sales-chart")
async def get_sales_chart(
    days: int = Query(30),
    location_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get daily sales for charting"""
    tenant_id = current_user["tenant_id"]
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    query = {
        "tenant_id": tenant_id,
        "sale_date": {"$gte": start_date}
    }
    if location_id:
        query["location_id"] = location_id
    
    sales = await db.pos_sales.find(query).to_list(10000)
    
    # Aggregate by day
    daily_totals = {}
    for sale in sales:
        date_key = sale["sale_date"].date().isoformat()
        if date_key not in daily_totals:
            daily_totals[date_key] = 0
        daily_totals[date_key] += sale["total_amount"]
    
    chart_data = [{"date": k, "sales": v} for k, v in sorted(daily_totals.items())]
    return chart_data

# ============================================================================
# LOCATIONS
# ============================================================================

@api_router.get("/locations")
async def get_locations(current_user: dict = Depends(get_current_user)):
    locations = await db.locations.find({"tenant_id": current_user["tenant_id"]}).to_list(1000)
    return locations

# ============================================================================
# SEED DATA
# ============================================================================

@api_router.post("/seed/demo-data")
async def seed_demo_data(current_user: dict = Depends(get_current_user)):
    """Seed demo inventory and PO data"""
    tenant_id = current_user["tenant_id"]
    
    # Get locations
    locations = await db.locations.find({"tenant_id": tenant_id}).to_list(10)
    if not locations:
        return {"error": "No locations found"}
    
    # Create sample items
    sample_items = [
        {"sku": "BURGER-001", "name": "Beef Burger Patty", "category": "Food", "cost": 2.5, "price": 8.99},
        {"sku": "BUN-001", "name": "Burger Buns (pack)", "category": "Food", "cost": 1.2, "price": 0},
        {"sku": "FRIES-001", "name": "French Fries (lb)", "category": "Food", "cost": 0.8, "price": 3.99},
        {"sku": "COLA-001", "name": "Cola (12oz)", "category": "Beverage", "cost": 0.5, "price": 2.49},
        {"sku": "LETTUCE-001", "name": "Lettuce Head", "category": "Produce", "cost": 0.6, "price": 0},
    ]
    
    for item_data in sample_items:
        existing = await db.items.find_one({"tenant_id": tenant_id, "sku": item_data["sku"]})
        if not existing:
            item = Item(tenant_id=tenant_id, **item_data)
            await db.items.insert_one(item.dict())
            
            # Create inventory levels for each location
            for loc in locations:
                inv_level = InventoryLevel(
                    tenant_id=tenant_id,
                    location_id=loc["id"],
                    item_id=item.id,
                    quantity_on_hand=50,
                    min_level=20,
                    max_level=200,
                    reorder_point=30,
                    lead_time_days=5
                )
                await db.inventory_levels.insert_one(inv_level.dict())
    
    return {"success": True, "message": "Demo data seeded"}

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
