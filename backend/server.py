from fastapi import FastAPI, APIRouter, HTTPException, Depends, Header, Query, File, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
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
import base64
import shutil
import csv
import io
from decimal import Decimal, InvalidOperation

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

class Company(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    name: str
    parent_company_id: Optional[str] = None  # For subsidiaries
    industry: str
    accounting_basis: AccountingBasisEnum = AccountingBasisEnum.ACCRUAL
    tax_id: Optional[str] = None
    is_active: bool = True
    deleted_at: Optional[datetime] = None  # For soft delete
    backup_data: Optional[dict] = None  # Store backup of related data
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class BusinessUnit(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    company_id: str
    parent_subsidiary_id: Optional[str] = None  # Links to parent subsidiary for consolidation
    name: str
    code: str  # e.g., "BU-001"
    description: Optional[str] = None
    manager_name: Optional[str] = None
    consolidation_enabled: bool = True  # Whether to roll up to parent subsidiary
    is_active: bool = True
    deleted_at: Optional[datetime] = None  # For soft delete
    backup_data: Optional[dict] = None  # Store backup of related data
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Location(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    company_id: str
    business_unit_id: Optional[str] = None
    name: str
    address: str
    timezone: str = "America/New_York"
    lat: Optional[float] = None
    lng: Optional[float] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserPermissions(BaseModel):
    # Dashboard & Reporting
    view_dashboard: bool = True
    view_reports: bool = False
    export_data: bool = False
    
    # Financial Management
    view_finances: bool = False
    manage_accounts_ledger: bool = False
    create_journal_entries: bool = False
    approve_journal_entries: bool = False
    
    # Company & Business Units
    manage_information: bool = False
    manage_companies: bool = False
    manage_business_units: bool = False
    
    # User Management
    view_users: bool = False
    manage_users: bool = False
    
    # Settings & Configuration
    manage_settings: bool = False
    manage_api_keys: bool = False
    manage_branding: bool = False
    
    # Inventory & Operations
    view_inventory: bool = False
    manage_inventory: bool = False
    manage_procurement: bool = False
    
    # Administrative
    full_access: bool = False

class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    email: EmailStr
    password_hash: str
    name: str
    role: RoleEnum
    permissions: Optional[UserPermissions] = None
    location_ids: List[str] = []  # Empty means access to all locations
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class CompanyBranding(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    company_id: str
    logo_url: Optional[str] = None
    primary_color: str = "#3b82f6"  # Default blue
    secondary_color: str = "#8b5cf6"  # Default purple
    accent_color: str = "#10b981"  # Default green
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class APIKey(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    company_id: str
    name: str
    service_type: str  # "parrot_pos", "stripe", "plaid", etc.
    api_key: str
    api_secret: Optional[str] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_used: Optional[datetime] = None

class Account(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    company_id: str  # Each company has its own chart of accounts
    code: str
    name: str
    account_type: AccountTypeEnum
    parent_id: Optional[str] = None
    is_active: bool = True

class JournalEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    company_id: str
    business_unit_id: Optional[str] = None  # For BU-level tracking
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
    company_id: str
    business_unit_id: Optional[str] = None
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
    company_name: Optional[str] = None  # First company name

class CreateCompanyRequest(BaseModel):
    name: str
    industry: str
    parent_company_id: Optional[str] = None
    tax_id: Optional[str] = None
    accounting_basis: AccountingBasisEnum = AccountingBasisEnum.ACCRUAL

class CreateBusinessUnitRequest(BaseModel):
    company_id: str
    name: str
    code: str
    description: Optional[str] = None
    manager_name: Optional[str] = None
    parent_subsidiary_id: Optional[str] = None  # Optional manual assignment
    consolidation_enabled: Optional[bool] = True

class CreateUserRequest(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: RoleEnum
    permissions: UserPermissions

class UpdateBrandingRequest(BaseModel):
    logo_url: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    accent_color: Optional[str] = None

class CreateAPIKeyRequest(BaseModel):
    name: str
    service_type: str
    api_key: str
    api_secret: Optional[str] = None

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
# CSV IMPORT MODELS
# ============================================================================

class AccountTemplate(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    company_id: str
    account_name: str
    description: str
    account_type: str  # Asset, Liability, Equity, Revenue, Expense
    account_code: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class BankStatement(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    company_id: str
    business_unit_id: Optional[str] = None
    upload_filename: str
    upload_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    total_transactions: int
    categorized_transactions: int = 0
    status: str = "uploaded"  # uploaded, categorizing, completed
    
class BankTransaction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    company_id: str
    business_unit_id: Optional[str] = None
    bank_statement_id: str
    transaction_date: datetime
    description: str
    amount: float
    transaction_type: str  # "debit" or "credit" 
    account_id: Optional[str] = None  # For categorization
    category: Optional[str] = None
    notes: Optional[str] = None
    is_categorized: bool = False
    journal_entry_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class CashFlow(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    company_id: str
    business_unit_id: Optional[str] = None
    invoice_id: Optional[str] = None
    accrual_date: datetime
    cashflow_date: datetime
    account_id: str
    supplier_name: Optional[str] = None
    description: str
    payment_method: str  # cash, check, credit_card, wire_transfer, etc.
    amount: float
    expense_type: str  # "expense_pl" or "capitalize_bs"
    journal_entry_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class BankTransactionCategorization(BaseModel):
    transaction_id: str
    account_id: str
    category: Optional[str] = None
    notes: Optional[str] = None

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
    """Create initial tenant, admin user, company, business units, locations, and COA"""
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
    
    # Create first company
    company_name = request.company_name or request.name
    company = Company(
        tenant_id=tenant.id,
        name=company_name,
        industry=request.industry
    )
    await db.companies.insert_one(company.dict())
    
    # Create default business units
    business_units = [
        BusinessUnit(
            tenant_id=tenant.id,
            company_id=company.id,
            name="Operations",
            code="BU-OPS",
            description="Main operational unit"
        ),
        BusinessUnit(
            tenant_id=tenant.id,
            company_id=company.id,
            name="Sales",
            code="BU-SALES",
            description="Sales and marketing"
        )
    ]
    for bu in business_units:
        await db.business_units.insert_one(bu.dict())
    
    # Create sample locations
    locations = [
        Location(
            tenant_id=tenant.id,
            company_id=company.id,
            business_unit_id=business_units[0].id,
            name="Main Store",
            address="123 Main St"
        ),
        Location(
            tenant_id=tenant.id,
            company_id=company.id,
            business_unit_id=business_units[0].id,
            name="Downtown Branch",
            address="456 Downtown Ave"
        ),
        Location(
            tenant_id=tenant.id,
            company_id=company.id,
            business_unit_id=business_units[1].id,
            name="Airport Location",
            address="789 Airport Rd"
        )
    ]
    for loc in locations:
        await db.locations.insert_one(loc.dict())
    
    # Create chart of accounts
    coa_template = get_coa_template(request.industry)
    for acc in coa_template:
        account = Account(
            tenant_id=tenant.id,
            company_id=company.id,
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
                    # Get first company for this tenant
                    company = await db.companies.find_one({"tenant_id": tenant_id})
                    if not company:
                        continue  # Skip if no company found
                    
                    # Get first business unit for this company
                    business_unit = await db.business_units.find_one({
                        "tenant_id": tenant_id, 
                        "company_id": company["id"]
                    })
                    
                    location = Location(
                        tenant_id=tenant_id,
                        company_id=company["id"],
                        business_unit_id=business_unit["id"] if business_unit else None,
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
                        company_id=location.get("company_id", ""),
                        business_unit_id=location.get("business_unit_id"),
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
                    await post_sale_to_ledger(tenant_id, sale.company_id, sale.business_unit_id, location["id"], sale)
                    
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

async def post_sale_to_ledger(tenant_id: str, company_id: str, business_unit_id: Optional[str], location_id: str, sale: POSSale):
    """Post POS sale to general ledger"""
    # Find accounts for this company
    cash_account = await db.accounts.find_one({"tenant_id": tenant_id, "company_id": company_id, "code": "1000"})
    revenue_account = await db.accounts.find_one({"tenant_id": tenant_id, "company_id": company_id, "code": "4000"})
    tax_account = await db.accounts.find_one({"tenant_id": tenant_id, "company_id": company_id, "code": "2100"})
    
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
        company_id=company_id,
        business_unit_id=business_unit_id,
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
async def get_accounts(
    company_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get accounts, optionally filtered by company"""
    query = {"tenant_id": current_user["tenant_id"]}
    if company_id:
        query["company_id"] = company_id
    
    accounts = await db.accounts.find(query).to_list(1000)
    return accounts

class CreateAccountRequest(BaseModel):
    company_id: str
    code: str
    name: str
    account_type: AccountTypeEnum
    parent_id: Optional[str] = None

@api_router.post("/finance/accounts")
async def create_account(
    request: CreateAccountRequest,
    current_user: dict = Depends(get_current_user)
):
    """Create a new account"""
    tenant_id = current_user["tenant_id"]
    
    # Check if code already exists in this company
    existing = await db.accounts.find_one({
        "tenant_id": tenant_id,
        "company_id": request.company_id,
        "code": request.code
    })
    if existing:
        raise HTTPException(status_code=400, detail="Account code already exists in this company")
    
    account = Account(
        tenant_id=tenant_id,
        company_id=request.company_id,
        code=request.code,
        name=request.name,
        account_type=request.account_type,
        parent_id=request.parent_id
    )
    await db.accounts.insert_one(account.dict())
    return account

class UpdateAccountRequest(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    account_type: Optional[AccountTypeEnum] = None
    is_active: Optional[bool] = None

@api_router.put("/finance/accounts/{account_id}")
async def update_account(
    account_id: str,
    request: UpdateAccountRequest,
    current_user: dict = Depends(get_current_user)
):
    """Update an existing account"""
    tenant_id = current_user["tenant_id"]
    code = request.code
    name = request.name
    account_type = request.account_type
    is_active = request.is_active
    
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

class CreateJournalEntryRequest(BaseModel):
    company_id: str
    business_unit_id: Optional[str] = None
    entry_date: str
    description: str
    lines: List[Dict[str, Any]]
    reference: Optional[str] = None

@api_router.post("/finance/journal-entries")
async def create_journal_entry(
    request: CreateJournalEntryRequest,
    current_user: dict = Depends(get_current_user)
):
    """Create a manual journal entry"""
    tenant_id = current_user["tenant_id"]
    
    # Validate lines balance (debits = credits)
    total_debits = sum(line.get("debit", 0) for line in request.lines)
    total_credits = sum(line.get("credit", 0) for line in request.lines)
    
    if abs(total_debits - total_credits) > 0.01:
        raise HTTPException(
            status_code=400, 
            detail=f"Journal entry is not balanced. Debits: {total_debits}, Credits: {total_credits}"
        )
    
    # Verify all accounts exist and belong to the same company
    for line in request.lines:
        account = await db.accounts.find_one({
            "id": line["account_id"],
            "tenant_id": tenant_id,
            "company_id": request.company_id
        })
        if not account:
            raise HTTPException(status_code=404, detail=f"Account {line['account_id']} not found in this company")
    
    je = JournalEntry(
        tenant_id=tenant_id,
        company_id=request.company_id,
        business_unit_id=request.business_unit_id,
        entry_date=datetime.fromisoformat(request.entry_date),
        description=request.description,
        reference=request.reference,
        is_posted=True,
        lines=request.lines
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
    company_id: Optional[str] = None,
    business_unit_id: Optional[str] = None,
    location_id: Optional[str] = None,
    consolidated: bool = False,  # For parent company consolidated view
    current_user: dict = Depends(get_current_user)
):
    """Generate P&L statement with company/business unit filtering"""
    tenant_id = current_user["tenant_id"]
    start = datetime.fromisoformat(start_date)
    end = datetime.fromisoformat(end_date)
    
    # Build company filter
    company_ids = []
    if company_id:
        company_ids.append(company_id)
        
        # If consolidated, include all subsidiaries
        if consolidated:
            subsidiaries = await db.companies.find({
                "tenant_id": tenant_id,
                "parent_company_id": company_id
            }).to_list(1000)
            company_ids.extend([sub["id"] for sub in subsidiaries])
    
    # Get all accounts for the relevant companies
    account_query = {"tenant_id": tenant_id}
    if company_ids:
        account_query["company_id"] = {"$in": company_ids} if len(company_ids) > 1 else company_ids[0]
    
    accounts = await db.accounts.find(account_query).to_list(1000)
    account_map = {acc["id"]: acc for acc in accounts}
    
    # Get journal entries in date range
    query = {
        "tenant_id": tenant_id,
        "entry_date": {"$gte": start, "$lte": end},
        "is_posted": True
    }
    if company_ids:
        query["company_id"] = {"$in": company_ids} if len(company_ids) > 1 else company_ids[0]
    if business_unit_id:
        query["business_unit_id"] = business_unit_id
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
# COMPANY MANAGEMENT
# ============================================================================

@api_router.get("/companies")
async def get_companies(current_user: dict = Depends(get_current_user)):
    """Get all active companies for the tenant (excludes soft-deleted)"""
    companies = await db.companies.find({
        "tenant_id": current_user["tenant_id"],
        "deleted_at": None  # Exclude soft-deleted companies
    }).to_list(1000)
    
    # Enrich with subsidiary count
    for company in companies:
        company.pop("_id", None)  # Remove MongoDB _id
        subsidiary_count = await db.companies.count_documents({
            "tenant_id": current_user["tenant_id"],
            "parent_company_id": company["id"],
            "deleted_at": None  # Exclude soft-deleted subsidiaries
        })
        company["subsidiary_count"] = subsidiary_count
        
        # Get parent company name if it's a subsidiary
        if company.get("parent_company_id"):
            parent = await db.companies.find_one({"id": company["parent_company_id"]})
            company["parent_company_name"] = parent["name"] if parent else None
    
    return companies

@api_router.post("/companies")
async def create_company(
    request: CreateCompanyRequest,
    current_user: dict = Depends(get_current_user)
):
    """Create a new company or subsidiary"""
    tenant_id = current_user["tenant_id"]
    
    # Verify parent company if specified
    if request.parent_company_id:
        parent = await db.companies.find_one({
            "id": request.parent_company_id,
            "tenant_id": tenant_id
        })
        if not parent:
            raise HTTPException(status_code=404, detail="Parent company not found")
    
    company = Company(
        tenant_id=tenant_id,
        name=request.name,
        industry=request.industry,
        parent_company_id=request.parent_company_id,
        tax_id=request.tax_id,
        accounting_basis=request.accounting_basis
    )
    
    company_dict = company.dict()
    await db.companies.insert_one(company_dict)
    
    # Create default chart of accounts for new company
    coa_template = get_coa_template(request.industry)
    for acc in coa_template:
        account = Account(
            tenant_id=tenant_id,
            company_id=company.id,
            code=acc["code"],
            name=acc["name"],
            account_type=AccountTypeEnum(acc["type"])
        )
        await db.accounts.insert_one(account.dict())
    
    company_dict.pop("_id", None)
    return company_dict

class UpdateCompanyRequest(BaseModel):
    name: Optional[str] = None
    industry: Optional[str] = None
    tax_id: Optional[str] = None
    accounting_basis: Optional[AccountingBasisEnum] = None
    is_active: Optional[bool] = None

@api_router.put("/companies/{company_id}")
async def update_company(
    company_id: str,
    request: UpdateCompanyRequest,
    current_user: dict = Depends(get_current_user)
):
    """Update company details"""
    tenant_id = current_user["tenant_id"]
    
    update_data = {}
    if request.name:
        update_data["name"] = request.name
    if request.industry:
        update_data["industry"] = request.industry
    if request.tax_id is not None:
        update_data["tax_id"] = request.tax_id
    if request.accounting_basis:
        update_data["accounting_basis"] = request.accounting_basis
    if request.is_active is not None:
        update_data["is_active"] = request.is_active
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    result = await db.companies.update_one(
        {"id": company_id, "tenant_id": tenant_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Company not found")
    
    company = await db.companies.find_one({"id": company_id, "tenant_id": tenant_id})
    if company:
        company.pop("_id", None)
    return company

@api_router.delete("/companies/{company_id}")
async def delete_company(
    company_id: str,
    current_user: dict = Depends(get_current_user)
):
    """DEPRECATED: Use soft-delete endpoint instead. Hard delete a company and all associated data"""
    tenant_id = current_user["tenant_id"]
    
    # Check if company has subsidiaries
    subsidiaries = await db.companies.count_documents({
        "tenant_id": tenant_id,
        "parent_company_id": company_id
    })
    
    if subsidiaries > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete company with {subsidiaries} subsidiaries. Delete subsidiaries first."
        )
    
    # Delete associated data
    await db.business_units.delete_many({"company_id": company_id})
    await db.locations.delete_many({"company_id": company_id})
    await db.accounts.delete_many({"company_id": company_id})
    await db.journal_entries.delete_many({"company_id": company_id})
    await db.api_keys.delete_many({"company_id": company_id})
    await db.company_branding.delete_many({"company_id": company_id})
    
    # Delete the company
    result = await db.companies.delete_one({"id": company_id, "tenant_id": tenant_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Company not found")
    
    return {"success": True, "message": "Company and associated data deleted"}

@api_router.post("/companies/{company_id}/soft-delete")
async def soft_delete_company(
    company_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Soft delete a company with backup for 6 months"""
    tenant_id = current_user["tenant_id"]
    
    # Get the company
    company = await db.companies.find_one({"id": company_id, "tenant_id": tenant_id})
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    if company.get("deleted_at"):
        raise HTTPException(status_code=400, detail="Company is already deleted")
    
    # Check if company has subsidiaries
    subsidiaries = await db.companies.count_documents({
        "tenant_id": tenant_id,
        "parent_company_id": company_id,
        "deleted_at": None
    })
    
    if subsidiaries > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete company with {subsidiaries} active subsidiaries. Delete subsidiaries first."
        )
    
    # Create backup data
    backup_data = {
        "business_units": [],
        "locations": [],
        "accounts": [],
        "api_keys": [],
        "branding": [],
        "journal_entries": []
    }
    
    # Collect related data for backup
    backup_data["business_units"] = await db.business_units.find({"company_id": company_id}).to_list(None)
    backup_data["locations"] = await db.locations.find({"company_id": company_id}).to_list(None)
    backup_data["accounts"] = await db.accounts.find({"company_id": company_id}).to_list(None)
    backup_data["api_keys"] = await db.api_keys.find({"company_id": company_id}).to_list(None)
    backup_data["branding"] = await db.company_branding.find({"company_id": company_id}).to_list(None)
    backup_data["journal_entries"] = await db.journal_entries.find({"company_id": company_id}).to_list(None)
    
    # Remove MongoDB ObjectIds from backup data
    for collection_data in backup_data.values():
        for item in collection_data:
            item.pop("_id", None)
    
    # Soft delete the company
    delete_time = datetime.now(timezone.utc)
    result = await db.companies.update_one(
        {"id": company_id, "tenant_id": tenant_id},
        {
            "$set": {
                "deleted_at": delete_time,
                "backup_data": backup_data,
                "is_active": False
            }
        }
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Deactivate related data (but keep it for potential restoration)
    await db.business_units.update_many({"company_id": company_id}, {"$set": {"is_active": False}})
    await db.locations.update_many({"company_id": company_id}, {"$set": {"is_active": False}})
    await db.accounts.update_many({"company_id": company_id}, {"$set": {"is_active": False}})
    await db.api_keys.update_many({"company_id": company_id}, {"$set": {"is_active": False}})
    
    return {
        "success": True, 
        "message": "Company soft deleted successfully. Data backed up for 6 months.",
        "deleted_at": delete_time,
        "restoration_deadline": delete_time.replace(month=delete_time.month + 6) if delete_time.month <= 6 else delete_time.replace(year=delete_time.year + 1, month=delete_time.month - 6)
    }

@api_router.post("/companies/{company_id}/restore")
async def restore_company(
    company_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Restore a soft-deleted company"""
    tenant_id = current_user["tenant_id"]
    
    # Get the deleted company
    company = await db.companies.find_one({"id": company_id, "tenant_id": tenant_id})
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    if not company.get("deleted_at"):
        raise HTTPException(status_code=400, detail="Company is not deleted")
    
    # Check if restoration deadline has passed (6 months)
    delete_time = company["deleted_at"]
    # Ensure delete_time is timezone-aware
    if delete_time.tzinfo is None:
        delete_time = delete_time.replace(tzinfo=timezone.utc)
    
    restoration_deadline = delete_time.replace(month=delete_time.month + 6) if delete_time.month <= 6 else delete_time.replace(year=delete_time.year + 1, month=delete_time.month - 6)
    
    if datetime.now(timezone.utc) > restoration_deadline:
        raise HTTPException(status_code=400, detail="Restoration deadline has passed. Company data may have been permanently deleted.")
    
    # Restore the company
    await db.companies.update_one(
        {"id": company_id, "tenant_id": tenant_id},
        {
            "$set": {"is_active": True},
            "$unset": {"deleted_at": "", "backup_data": ""}
        }
    )
    
    # Reactivate related data
    await db.business_units.update_many({"company_id": company_id}, {"$set": {"is_active": True}})
    await db.locations.update_many({"company_id": company_id}, {"$set": {"is_active": True}})
    await db.accounts.update_many({"company_id": company_id}, {"$set": {"is_active": True}})
    await db.api_keys.update_many({"company_id": company_id}, {"$set": {"is_active": True}})
    
    return {"success": True, "message": "Company restored successfully"}

@api_router.get("/companies/deleted")
async def get_deleted_companies(
    current_user: dict = Depends(get_current_user)
):
    """Get all soft-deleted companies that can be restored"""
    tenant_id = current_user["tenant_id"]
    
    # Get deleted companies that are still within restoration period
    six_months_ago = datetime.now(timezone.utc) - timedelta(days=180)
    
    deleted_companies = await db.companies.find({
        "tenant_id": tenant_id,
        "deleted_at": {"$exists": True, "$gte": six_months_ago}
    }).to_list(None)
    
    # Clean up and add restoration info
    for company in deleted_companies:
        company.pop("_id", None)
        company.pop("backup_data", None)  # Don't send backup data in list
        
        # Add restoration deadline
        delete_time = company["deleted_at"]
        # Ensure delete_time is timezone-aware
        if delete_time.tzinfo is None:
            delete_time = delete_time.replace(tzinfo=timezone.utc)
        
        restoration_deadline = delete_time.replace(month=delete_time.month + 6) if delete_time.month <= 6 else delete_time.replace(year=delete_time.year + 1, month=delete_time.month - 6)
        company["restoration_deadline"] = restoration_deadline
        
        # Add days remaining
        days_remaining = (restoration_deadline - datetime.now(timezone.utc)).days
        company["days_remaining"] = max(0, days_remaining)
    
    return deleted_companies

# ============================================================================
# BUSINESS UNIT MANAGEMENT
# ============================================================================

@api_router.get("/business-units")
async def get_business_units(
    company_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get business units, optionally filtered by company (excludes soft-deleted)"""
    query = {
        "tenant_id": current_user["tenant_id"],
        "deleted_at": None  # Exclude soft-deleted business units
    }
    if company_id:
        query["company_id"] = company_id
    
    business_units = await db.business_units.find(query).to_list(1000)
    
    # Enrich with company name and parent subsidiary info
    for bu in business_units:
        bu.pop("_id", None)  # Remove MongoDB _id
        
        # Get company name
        company = await db.companies.find_one({"id": bu["company_id"]})
        bu["company_name"] = company["name"] if company else None
        
        # Get parent subsidiary name if linked
        if bu.get("parent_subsidiary_id"):
            parent_subsidiary = await db.companies.find_one({"id": bu["parent_subsidiary_id"]})
            bu["parent_subsidiary_name"] = parent_subsidiary["name"] if parent_subsidiary else None
        else:
            bu["parent_subsidiary_name"] = None
    
    return business_units

@api_router.post("/business-units")
async def create_business_unit(
    request: CreateBusinessUnitRequest,
    current_user: dict = Depends(get_current_user)
):
    """Create a new business unit"""
    tenant_id = current_user["tenant_id"]
    
    # Verify company exists
    company = await db.companies.find_one({
        "id": request.company_id,
        "tenant_id": tenant_id
    })
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Check if code already exists
    existing = await db.business_units.find_one({
        "tenant_id": tenant_id,
        "company_id": request.company_id,
        "code": request.code
    })
    if existing:
        raise HTTPException(status_code=400, detail="Business unit code already exists")
    
    # Determine parent subsidiary for consolidation
    parent_subsidiary_id = request.parent_subsidiary_id
    if not parent_subsidiary_id and company.get("parent_company_id"):
        # If the company is a subsidiary, it rolls up to itself by default
        parent_subsidiary_id = request.company_id
    
    # Validate parent_subsidiary_id if provided
    if parent_subsidiary_id:
        parent_subsidiary = await db.companies.find_one({
            "id": parent_subsidiary_id,
            "tenant_id": tenant_id
        })
        if not parent_subsidiary:
            raise HTTPException(status_code=404, detail="Parent subsidiary not found")
    
    business_unit = BusinessUnit(
        tenant_id=tenant_id,
        company_id=request.company_id,
        parent_subsidiary_id=parent_subsidiary_id,
        name=request.name,
        code=request.code,
        description=request.description,
        manager_name=request.manager_name,
        consolidation_enabled=request.consolidation_enabled
    )
    
    bu_dict = business_unit.dict()
    await db.business_units.insert_one(bu_dict)
    bu_dict.pop("_id", None)
    
    return bu_dict

class UpdateBusinessUnitRequest(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    manager_name: Optional[str] = None
    parent_subsidiary_id: Optional[str] = None
    consolidation_enabled: Optional[bool] = None
    is_active: Optional[bool] = None

@api_router.put("/business-units/{bu_id}")
async def update_business_unit(
    bu_id: str,
    request: UpdateBusinessUnitRequest,
    current_user: dict = Depends(get_current_user)
):
    """Update business unit details"""
    tenant_id = current_user["tenant_id"]
    
    # Get existing BU
    existing_bu = await db.business_units.find_one({"id": bu_id, "tenant_id": tenant_id})
    if not existing_bu:
        raise HTTPException(status_code=404, detail="Business unit not found")
    
    update_data = {}
    if request.name:
        update_data["name"] = request.name
    if request.code:
        # Check if new code conflicts with another BU
        conflict = await db.business_units.find_one({
            "tenant_id": tenant_id,
            "company_id": existing_bu["company_id"],
            "code": request.code,
            "id": {"$ne": bu_id}
        })
        if conflict:
            raise HTTPException(status_code=400, detail="Business unit code already exists")
        update_data["code"] = request.code
    if request.description is not None:
        update_data["description"] = request.description
    if request.manager_name is not None:
        update_data["manager_name"] = request.manager_name
    if request.parent_subsidiary_id is not None:
        # Validate parent_subsidiary_id if provided
        if request.parent_subsidiary_id:
            parent_subsidiary = await db.companies.find_one({
                "id": request.parent_subsidiary_id,
                "tenant_id": tenant_id
            })
            if not parent_subsidiary:
                raise HTTPException(status_code=404, detail="Parent subsidiary not found")
        update_data["parent_subsidiary_id"] = request.parent_subsidiary_id
    if request.consolidation_enabled is not None:
        update_data["consolidation_enabled"] = request.consolidation_enabled
    if request.is_active is not None:
        update_data["is_active"] = request.is_active
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    result = await db.business_units.update_one(
        {"id": bu_id, "tenant_id": tenant_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Business unit not found")
    
    bu = await db.business_units.find_one({"id": bu_id, "tenant_id": tenant_id})
    if bu:
        bu.pop("_id", None)
    return bu

@api_router.delete("/business-units/{bu_id}")
async def delete_business_unit(
    bu_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a business unit"""
    tenant_id = current_user["tenant_id"]
    
    # Check if BU has locations
    locations = await db.locations.count_documents({
        "tenant_id": tenant_id,
        "business_unit_id": bu_id
    })
    
    if locations > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete business unit with {locations} locations. Reassign locations first."
        )
    
    # Delete journal entries associated with this BU
    await db.journal_entries.delete_many({"business_unit_id": bu_id})
    
    # Delete the business unit
    result = await db.business_units.delete_one({"id": bu_id, "tenant_id": tenant_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Business unit not found")
    
    return {"success": True, "message": "Business unit deleted"}

@api_router.post("/business-units/{bu_id}/soft-delete")
async def soft_delete_business_unit(
    bu_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Soft delete a business unit with backup for 6 months"""
    tenant_id = current_user["tenant_id"]
    
    # Get the business unit
    business_unit = await db.business_units.find_one({"id": bu_id, "tenant_id": tenant_id})
    if not business_unit:
        raise HTTPException(status_code=404, detail="Business unit not found")
    
    if business_unit.get("deleted_at"):
        raise HTTPException(status_code=400, detail="Business unit is already deleted")
    
    # Check if BU has locations
    locations = await db.locations.count_documents({
        "tenant_id": tenant_id,
        "business_unit_id": bu_id
    })
    
    if locations > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete business unit with {locations} locations. Reassign locations first."
        )
    
    # Create backup data
    backup_data = {
        "locations": [],
        "journal_entries": []
    }
    
    # Collect related data for backup
    backup_data["locations"] = await db.locations.find({"business_unit_id": bu_id}).to_list(None)
    backup_data["journal_entries"] = await db.journal_entries.find({"business_unit_id": bu_id}).to_list(None)
    
    # Remove MongoDB ObjectIds from backup data
    for collection_data in backup_data.values():
        for item in collection_data:
            item.pop("_id", None)
    
    # Soft delete the business unit
    delete_time = datetime.now(timezone.utc)
    result = await db.business_units.update_one(
        {"id": bu_id, "tenant_id": tenant_id},
        {
            "$set": {
                "deleted_at": delete_time,
                "backup_data": backup_data,
                "is_active": False
            }
        }
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Business unit not found")
    
    # Deactivate related data (but keep it for potential restoration)
    await db.locations.update_many({"business_unit_id": bu_id}, {"$set": {"is_active": False}})
    
    return {
        "success": True, 
        "message": "Business unit soft deleted successfully. Data backed up for 6 months.",
        "deleted_at": delete_time,
        "restoration_deadline": delete_time.replace(month=delete_time.month + 6) if delete_time.month <= 6 else delete_time.replace(year=delete_time.year + 1, month=delete_time.month - 6)
    }

@api_router.post("/business-units/{bu_id}/restore")
async def restore_business_unit(
    bu_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Restore a soft-deleted business unit"""
    tenant_id = current_user["tenant_id"]
    
    # Get the deleted business unit
    business_unit = await db.business_units.find_one({"id": bu_id, "tenant_id": tenant_id})
    if not business_unit:
        raise HTTPException(status_code=404, detail="Business unit not found")
    
    if not business_unit.get("deleted_at"):
        raise HTTPException(status_code=400, detail="Business unit is not deleted")
    
    # Check if restoration deadline has passed (6 months)
    delete_time = business_unit["deleted_at"]
    # Ensure delete_time is timezone-aware
    if delete_time.tzinfo is None:
        delete_time = delete_time.replace(tzinfo=timezone.utc)
    
    restoration_deadline = delete_time.replace(month=delete_time.month + 6) if delete_time.month <= 6 else delete_time.replace(year=delete_time.year + 1, month=delete_time.month - 6)
    
    if datetime.now(timezone.utc) > restoration_deadline:
        raise HTTPException(status_code=400, detail="Restoration deadline has passed. Business unit data may have been permanently deleted.")
    
    # Restore the business unit
    await db.business_units.update_one(
        {"id": bu_id, "tenant_id": tenant_id},
        {
            "$set": {"is_active": True},
            "$unset": {"deleted_at": "", "backup_data": ""}
        }
    )
    
    # Reactivate related data
    await db.locations.update_many({"business_unit_id": bu_id}, {"$set": {"is_active": True}})
    
    return {"success": True, "message": "Business unit restored successfully"}

@api_router.get("/business-units/deleted")
async def get_deleted_business_units(
    current_user: dict = Depends(get_current_user)
):
    """Get all soft-deleted business units that can be restored"""
    tenant_id = current_user["tenant_id"]
    
    # Get deleted business units that are still within restoration period
    six_months_ago = datetime.now(timezone.utc) - timedelta(days=180)
    
    deleted_bus = await db.business_units.find({
        "tenant_id": tenant_id,
        "deleted_at": {"$exists": True, "$gte": six_months_ago}
    }).to_list(None)
    
    # Clean up and add restoration info
    for bu in deleted_bus:
        bu.pop("_id", None)
        bu.pop("backup_data", None)  # Don't send backup data in list
        
        # Add restoration deadline
        delete_time = bu["deleted_at"]
        # Ensure delete_time is timezone-aware
        if delete_time.tzinfo is None:
            delete_time = delete_time.replace(tzinfo=timezone.utc)
        
        restoration_deadline = delete_time.replace(month=delete_time.month + 6) if delete_time.month <= 6 else delete_time.replace(year=delete_time.year + 1, month=delete_time.month - 6)
        bu["restoration_deadline"] = restoration_deadline
        
        # Add days remaining
        days_remaining = (restoration_deadline - datetime.now(timezone.utc)).days
        bu["days_remaining"] = max(0, days_remaining)
        
        # Get company name
        company = await db.companies.find_one({"id": bu["company_id"]})
        bu["company_name"] = company["name"] if company else None
    
    return deleted_bus

@api_router.get("/business-units/{bu_id}/consolidation")
async def get_business_unit_consolidation(
    bu_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get consolidation data for a business unit and its relationship to parent subsidiary"""
    tenant_id = current_user["tenant_id"]
    
    # Get the business unit
    business_unit = await db.business_units.find_one({"id": bu_id, "tenant_id": tenant_id})
    if not business_unit:
        raise HTTPException(status_code=404, detail="Business unit not found")
    
    # Build date filter if provided
    date_filter = {}
    if start_date:
        date_filter["$gte"] = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
    if end_date:
        date_filter["$lte"] = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
    
    query = {
        "tenant_id": tenant_id,
        "business_unit_id": bu_id
    }
    if date_filter:
        query["entry_date"] = date_filter
    
    # Get journal entries for this business unit
    journal_entries = await db.journal_entries.find(query).to_list(None)
    
    # Calculate totals
    total_debits = 0
    total_credits = 0
    entries_count = len(journal_entries)
    
    for entry in journal_entries:
        entry.pop("_id", None)
        for line in entry.get("lines", []):
            total_debits += line.get("debit", 0)
            total_credits += line.get("credit", 0)
    
    # Get parent subsidiary info if linked
    parent_subsidiary_info = None
    if business_unit.get("parent_subsidiary_id"):
        parent_subsidiary = await db.companies.find_one({
            "id": business_unit["parent_subsidiary_id"],
            "tenant_id": tenant_id
        })
        if parent_subsidiary:
            parent_subsidiary.pop("_id", None)
            parent_subsidiary_info = parent_subsidiary
    
    # Get company info
    company = await db.companies.find_one({
        "id": business_unit["company_id"],
        "tenant_id": tenant_id
    })
    if company:
        company.pop("_id", None)
    
    business_unit.pop("_id", None)
    
    return {
        "business_unit": business_unit,
        "company": company,
        "parent_subsidiary": parent_subsidiary_info,
        "consolidation_summary": {
            "total_debits": total_debits,
            "total_credits": total_credits,
            "net_balance": total_debits - total_credits,
            "entries_count": entries_count,
            "consolidation_enabled": business_unit.get("consolidation_enabled", True)
        },
        "journal_entries": journal_entries,
        "date_range": {
            "start_date": start_date,
            "end_date": end_date
        }
    }

@api_router.get("/companies/{company_id}/consolidated-report")
async def get_consolidated_report(
    company_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get consolidated financial report for a subsidiary company from all its business units"""
    tenant_id = current_user["tenant_id"]
    
    # Get the company
    company = await db.companies.find_one({"id": company_id, "tenant_id": tenant_id})
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Build date filter if provided
    date_filter = {}
    if start_date:
        date_filter["$gte"] = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
    if end_date:
        date_filter["$lte"] = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
    
    # Get all business units that consolidate to this company
    business_units = await db.business_units.find({
        "tenant_id": tenant_id,
        "parent_subsidiary_id": company_id,
        "consolidation_enabled": True,
        "is_active": True
    }).to_list(None)
    
    # Get direct business units of this company
    direct_business_units = await db.business_units.find({
        "tenant_id": tenant_id,
        "company_id": company_id,
        "consolidation_enabled": True,
        "is_active": True
    }).to_list(None)
    
    # Combine all business units
    all_business_units = business_units + direct_business_units
    
    consolidated_data = {
        "company": company,
        "consolidation_period": {
            "start_date": start_date,
            "end_date": end_date
        },
        "business_units_summary": [],
        "consolidated_totals": {
            "total_debits": 0,
            "total_credits": 0,
            "net_balance": 0,
            "total_entries": 0
        },
        "all_journal_entries": []
    }
    
    company.pop("_id", None)
    
    for bu in all_business_units:
        bu.pop("_id", None)
        
        # Get journal entries for this business unit
        query = {
            "tenant_id": tenant_id,
            "business_unit_id": bu["id"]
        }
        if date_filter:
            query["entry_date"] = date_filter
        
        bu_entries = await db.journal_entries.find(query).to_list(None)
        
        # Calculate BU totals
        bu_debits = 0
        bu_credits = 0
        
        for entry in bu_entries:
            entry.pop("_id", None)
            for line in entry.get("lines", []):
                bu_debits += line.get("debit", 0)
                bu_credits += line.get("credit", 0)
        
        bu_summary = {
            "business_unit": bu,
            "totals": {
                "debits": bu_debits,
                "credits": bu_credits,
                "net_balance": bu_debits - bu_credits,
                "entries_count": len(bu_entries)
            }
        }
        
        consolidated_data["business_units_summary"].append(bu_summary)
        consolidated_data["consolidated_totals"]["total_debits"] += bu_debits
        consolidated_data["consolidated_totals"]["total_credits"] += bu_credits
        consolidated_data["consolidated_totals"]["total_entries"] += len(bu_entries)
        consolidated_data["all_journal_entries"].extend(bu_entries)
    
    consolidated_data["consolidated_totals"]["net_balance"] = (
        consolidated_data["consolidated_totals"]["total_debits"] - 
        consolidated_data["consolidated_totals"]["total_credits"]
    )
    
    return consolidated_data

@api_router.post("/business-units/{bu_id}/set-consolidation")
async def set_business_unit_consolidation(
    bu_id: str,
    parent_subsidiary_id: Optional[str] = None,
    consolidation_enabled: bool = True,
    current_user: dict = Depends(get_current_user)
):
    """Update business unit consolidation settings"""
    tenant_id = current_user["tenant_id"]
    
    # Get the business unit
    business_unit = await db.business_units.find_one({"id": bu_id, "tenant_id": tenant_id})
    if not business_unit:
        raise HTTPException(status_code=404, detail="Business unit not found")
    
    update_data = {
        "consolidation_enabled": consolidation_enabled
    }
    
    # Validate parent_subsidiary_id if provided
    if parent_subsidiary_id is not None:
        if parent_subsidiary_id:
            parent_subsidiary = await db.companies.find_one({
                "id": parent_subsidiary_id,
                "tenant_id": tenant_id
            })
            if not parent_subsidiary:
                raise HTTPException(status_code=404, detail="Parent subsidiary not found")
        update_data["parent_subsidiary_id"] = parent_subsidiary_id
    
    # Update the business unit
    result = await db.business_units.update_one(
        {"id": bu_id, "tenant_id": tenant_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Business unit not found")
    
    # Return updated business unit
    updated_bu = await db.business_units.find_one({"id": bu_id, "tenant_id": tenant_id})
    if updated_bu:
        updated_bu.pop("_id", None)
    
    return {
        "success": True,
        "message": "Consolidation settings updated",
        "business_unit": updated_bu
    }

# ============================================================================
# LOCATIONS
# ============================================================================

@api_router.get("/locations")
async def get_locations(
    company_id: Optional[str] = None,
    business_unit_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get locations, optionally filtered by company or business unit"""
    query = {"tenant_id": current_user["tenant_id"]}
    if company_id:
        query["company_id"] = company_id
    if business_unit_id:
        query["business_unit_id"] = business_unit_id
    
    locations = await db.locations.find(query).to_list(1000)
    
    # Enrich with company and BU names
    for loc in locations:
        loc.pop("_id", None)  # Remove MongoDB _id
        company = await db.companies.find_one({"id": loc["company_id"]})
        loc["company_name"] = company["name"] if company else None
        
        if loc.get("business_unit_id"):
            bu = await db.business_units.find_one({"id": loc["business_unit_id"]})
            loc["business_unit_name"] = bu["name"] if bu else None
    
    return locations

# ============================================================================
# USER MANAGEMENT
# ============================================================================

@api_router.get("/users")
async def get_users(current_user: dict = Depends(get_current_user)):
    """Get all users in the tenant"""
    users = await db.users.find({"tenant_id": current_user["tenant_id"]}).to_list(1000)
    # Remove password hashes and MongoDB _id from response
    for user in users:
        user.pop("password_hash", None)
        user.pop("_id", None)
    return users

@api_router.post("/users")
async def create_user(
    request: CreateUserRequest,
    current_user: dict = Depends(get_current_user)
):
    """Create a new user (admin only)"""
    tenant_id = current_user["tenant_id"]
    
    # Check if email already exists
    existing = await db.users.find_one({"email": request.email, "tenant_id": tenant_id})
    if existing:
        raise HTTPException(status_code=400, detail="User with this email already exists")
    
    user = User(
        tenant_id=tenant_id,
        email=request.email,
        password_hash=pwd_context.hash(request.password),
        name=request.name,
        role=request.role,
        permissions=request.permissions
    )
    
    user_dict = user.dict()
    await db.users.insert_one(user_dict)
    
    # Remove password hash and _id from response
    user_dict.pop("password_hash", None)
    user_dict.pop("_id", None)
    return user_dict

class UpdateUserRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[RoleEnum] = None
    permissions: Optional[UserPermissions] = None
    location_ids: Optional[List[str]] = None
    is_active: Optional[bool] = None

@api_router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    request: UpdateUserRequest,
    current_user: dict = Depends(get_current_user)
):
    """Update user details, permissions, or status"""
    tenant_id = current_user["tenant_id"]
    
    # Check if user exists
    existing_user = await db.users.find_one({"id": user_id, "tenant_id": tenant_id})
    if not existing_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    update_data = {}
    
    # Check email uniqueness if updating email
    if request.email and request.email != existing_user["email"]:
        email_exists = await db.users.find_one({
            "email": request.email,
            "tenant_id": tenant_id,
            "id": {"$ne": user_id}
        })
        if email_exists:
            raise HTTPException(status_code=400, detail="Email already in use")
        update_data["email"] = request.email
    
    if request.name:
        update_data["name"] = request.name
    if request.role:
        update_data["role"] = request.role
    if request.permissions:
        update_data["permissions"] = request.permissions.dict()
    if request.location_ids is not None:
        update_data["location_ids"] = request.location_ids
    if request.is_active is not None:
        update_data["is_active"] = request.is_active
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    result = await db.users.update_one(
        {"id": user_id, "tenant_id": current_user["tenant_id"]},
        {"$set": update_data}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"success": True}

@api_router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a user"""
    if user_id == current_user["id"]:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    result = await db.users.delete_one({"id": user_id, "tenant_id": current_user["tenant_id"]})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"success": True}

# ============================================================================
# BRANDING MANAGEMENT
# ============================================================================

# Create uploads directory if it doesn't exist
UPLOAD_DIR = Path("/app/backend/uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

@api_router.post("/upload-logo/{company_id}")
async def upload_logo(
    company_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload company logo"""
    # Validate file type
    if not file.content_type in ["image/jpeg", "image/jpg", "image/png"]:
        raise HTTPException(status_code=400, detail="Only JPG and PNG files are allowed")
    
    # Generate unique filename
    file_extension = file.filename.split(".")[-1]
    unique_filename = f"{company_id}_{uuid.uuid4()}.{file_extension}"
    file_path = UPLOAD_DIR / unique_filename
    
    # Save file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Generate URL (relative path)
    logo_url = f"/api/uploads/{unique_filename}"
    
    # Update branding with new logo URL
    await db.company_branding.update_one(
        {"company_id": company_id},
        {"$set": {"logo_url": logo_url, "updated_at": datetime.now(timezone.utc)}},
        upsert=True
    )
    
    return {"logo_url": logo_url}

@api_router.get("/uploads/{filename}")
async def get_uploaded_file(filename: str):
    """Serve uploaded files"""
    file_path = UPLOAD_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)

@api_router.get("/branding/{company_id}")
async def get_branding(
    company_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get branding for a company"""
    branding = await db.company_branding.find_one({
        "company_id": company_id
    })
    
    if not branding:
        # Return defaults
        return {
            "company_id": company_id,
            "logo_url": None,
            "primary_color": "#3b82f6",
            "secondary_color": "#8b5cf6",
            "accent_color": "#10b981"
        }
    
    branding.pop("_id", None)  # Remove MongoDB _id
    return branding

@api_router.put("/branding/{company_id}")
async def update_branding(
    company_id: str,
    request: UpdateBrandingRequest,
    current_user: dict = Depends(get_current_user)
):
    """Update company branding"""
    update_data = {"company_id": company_id}
    if request.logo_url is not None:
        update_data["logo_url"] = request.logo_url
    if request.primary_color:
        update_data["primary_color"] = request.primary_color
    if request.secondary_color:
        update_data["secondary_color"] = request.secondary_color
    if request.accent_color:
        update_data["accent_color"] = request.accent_color
    
    update_data["updated_at"] = datetime.now(timezone.utc)
    
    # Upsert
    await db.company_branding.update_one(
        {"company_id": company_id},
        {"$set": update_data},
        upsert=True
    )
    
    branding = await db.company_branding.find_one({"company_id": company_id})
    if branding:
        branding.pop("_id", None)
    return branding

# ============================================================================
# API KEY MANAGEMENT
# ============================================================================

@api_router.get("/api-keys/{company_id}")
async def get_api_keys(
    company_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get all API keys for a company"""
    keys = await db.api_keys.find({"company_id": company_id}).to_list(1000)
    
    # Mask API keys in response (show only last 4 chars)
    for key in keys:
        key.pop("_id", None)  # Remove MongoDB _id
        if len(key["api_key"]) > 4:
            key["api_key_masked"] = "*" * (len(key["api_key"]) - 4) + key["api_key"][-4:]
        else:
            key["api_key_masked"] = "****"
        key.pop("api_key", None)
        key.pop("api_secret", None)
    
    return keys

@api_router.post("/api-keys/{company_id}")
async def create_api_key(
    company_id: str,
    request: CreateAPIKeyRequest,
    current_user: dict = Depends(get_current_user)
):
    """Add a new API key"""
    api_key = APIKey(
        company_id=company_id,
        name=request.name,
        service_type=request.service_type,
        api_key=request.api_key,
        api_secret=request.api_secret
    )
    
    api_key_dict = api_key.dict()
    await db.api_keys.insert_one(api_key_dict)
    
    # Return masked version
    api_key_dict.pop("_id", None)
    if len(request.api_key) > 4:
        api_key_dict["api_key_masked"] = "*" * (len(request.api_key) - 4) + request.api_key[-4:]
    else:
        api_key_dict["api_key_masked"] = "****"
    api_key_dict.pop("api_key", None)
    api_key_dict.pop("api_secret", None)
    
    return api_key_dict

@api_router.delete("/api-keys/{key_id}")
async def delete_api_key(
    key_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete an API key"""
    result = await db.api_keys.delete_one({"id": key_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="API key not found")
    
    return {"success": True}

@api_router.patch("/api-keys/{key_id}/toggle")
async def toggle_api_key(
    key_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Toggle API key active status"""
    key = await db.api_keys.find_one({"id": key_id})
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    new_status = not key.get("is_active", True)
    await db.api_keys.update_one(
        {"id": key_id},
        {"$set": {"is_active": new_status}}
    )
    
    return {"success": True, "is_active": new_status}

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

# ============================================================================
# CSV IMPORT & TEMPLATE ENDPOINTS
# ============================================================================

@api_router.get("/templates/accounts/download")
async def download_accounts_template(
    current_user: dict = Depends(get_current_user)
):
    """Download accounts template CSV"""
    # Create CSV content
    csv_content = "account_name,description,account_type,account_code\n"
    csv_content += "Cash,Main business checking account,Asset,1000\n"
    csv_content += "Accounts Receivable,Money owed by customers,Asset,1200\n"
    csv_content += "Inventory,Products in stock,Asset,1300\n"
    csv_content += "Accounts Payable,Money owed to suppliers,Liability,2000\n"
    csv_content += "Sales Revenue,Income from sales,Revenue,4000\n"
    csv_content += "Cost of Goods Sold,Direct costs of products sold,Expense,5000\n"
    csv_content += "Office Supplies,General office supplies expense,Expense,6100\n"
    csv_content += "Utilities,Electricity and other utilities,Expense,6200\n"
    
    # Create file-like object
    csv_buffer = io.StringIO(csv_content)
    
    return StreamingResponse(
        io.BytesIO(csv_content.encode()),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=accounts_template.csv"}
    )

@api_router.post("/accounts/upload-template")
async def upload_accounts_template(
    company_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload accounts template CSV and create accounts"""
    tenant_id = current_user["tenant_id"]
    
    # Validate file type
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")
    
    try:
        # Read and parse CSV
        contents = await file.read()
        csv_data = contents.decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(csv_data))
        
        created_accounts = []
        errors = []
        
        for row_num, row in enumerate(csv_reader, start=2):
            try:
                # Validate required fields
                if not row.get('account_name') or not row.get('account_type'):
                    errors.append(f"Row {row_num}: Missing required fields (account_name, account_type)")
                    continue
                
                # Check if account already exists
                existing_account = await db.accounts.find_one({
                    "tenant_id": tenant_id,
                    "company_id": company_id,
                    "name": row['account_name']
                })
                
                if existing_account:
                    errors.append(f"Row {row_num}: Account '{row['account_name']}' already exists")
                    continue
                
                # Create account
                account = {
                    "id": str(uuid.uuid4()),
                    "tenant_id": tenant_id,
                    "company_id": company_id,
                    "code": row.get('account_code', ''),
                    "name": row['account_name'],
                    "account_type": row['account_type'],
                    "description": row.get('description', ''),
                    "balance": 0.0,
                    "is_active": True,
                    "created_at": datetime.now(timezone.utc)
                }
                
                await db.accounts.insert_one(account)
                account.pop("_id", None)
                created_accounts.append(account)
                
            except Exception as e:
                errors.append(f"Row {row_num}: {str(e)}")
        
        return {
            "success": True,
            "created_accounts": len(created_accounts),
            "accounts": created_accounts,
            "errors": errors
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process CSV: {str(e)}")

@api_router.get("/templates/cashflows/download")
async def download_cashflows_template(
    current_user: dict = Depends(get_current_user)
):
    """Download cash flows template CSV"""
    csv_content = "invoice_id,accrual_date,cashflow_date,account_name,supplier_name,description,payment_method,amount,expense_type\n"
    csv_content += "INV-001,2024-01-15,2024-01-15,Office Supplies,Staples,Office supplies purchase,cash,150.50,expense_pl\n"
    csv_content += "INV-002,2024-01-16,2024-01-20,Equipment,Dell,Computer purchase,check,2500.00,capitalize_bs\n"
    csv_content += ",2024-01-17,2024-01-17,Utilities,Electric Company,Monthly electricity,cash,85.00,expense_pl\n"
    
    return StreamingResponse(
        io.BytesIO(csv_content.encode()),
        media_type="text/csv", 
        headers={"Content-Disposition": "attachment; filename=cashflows_template.csv"}
    )

@api_router.post("/cashflows/upload-template")
async def upload_cashflows_template(
    company_id: str,
    business_unit_id: Optional[str] = None,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload cash flows template CSV and create journal entries"""
    tenant_id = current_user["tenant_id"]
    
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")
    
    try:
        contents = await file.read()
        csv_data = contents.decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(csv_data))
        
        created_cashflows = []
        created_journal_entries = []
        errors = []
        
        for row_num, row in enumerate(csv_reader, start=2):
            try:
                # Validate required fields
                required_fields = ['accrual_date', 'cashflow_date', 'account_name', 'description', 'amount', 'expense_type']
                missing_fields = [field for field in required_fields if not row.get(field)]
                
                if missing_fields:
                    errors.append(f"Row {row_num}: Missing required fields: {', '.join(missing_fields)}")
                    continue
                
                # Find account by name
                account = await db.accounts.find_one({
                    "tenant_id": tenant_id,
                    "company_id": company_id,
                    "name": row['account_name']
                })
                
                if not account:
                    errors.append(f"Row {row_num}: Account '{row['account_name']}' not found")
                    continue
                
                # Parse dates and amount
                try:
                    accrual_date = datetime.fromisoformat(row['accrual_date']).replace(tzinfo=timezone.utc)
                    cashflow_date = datetime.fromisoformat(row['cashflow_date']).replace(tzinfo=timezone.utc)
                    amount = float(row['amount'])
                except (ValueError, InvalidOperation) as e:
                    errors.append(f"Row {row_num}: Invalid date or amount format: {str(e)}")
                    continue
                
                # Create cash flow record
                cashflow = CashFlow(
                    tenant_id=tenant_id,
                    company_id=company_id,
                    business_unit_id=business_unit_id,
                    invoice_id=row.get('invoice_id'),
                    accrual_date=accrual_date,
                    cashflow_date=cashflow_date,
                    account_id=account["id"],
                    supplier_name=row.get('supplier_name'),
                    description=row['description'],
                    payment_method=row.get('payment_method', 'cash'),
                    amount=amount,
                    expense_type=row['expense_type']
                )
                
                # Get cash account for journal entry
                cash_account = await db.accounts.find_one({
                    "tenant_id": tenant_id,
                    "company_id": company_id,
                    "account_type": "Asset",
                    "name": {"$regex": "cash", "$options": "i"}
                })
                
                if not cash_account:
                    errors.append(f"Row {row_num}: No cash account found for journal entry")
                    continue
                
                # Create journal entry
                journal_entry = {
                    "id": str(uuid.uuid4()),
                    "tenant_id": tenant_id,
                    "company_id": company_id,
                    "business_unit_id": business_unit_id,
                    "entry_date": cashflow_date,
                    "description": f"Cash flow: {row['description']}",
                    "reference": row.get('invoice_id', f"CF-{cashflow.id[:8]}"),
                    "is_posted": True,
                    "lines": [],
                    "created_at": datetime.now(timezone.utc)
                }
                
                # Determine journal entry lines based on expense type
                if row['expense_type'] == 'expense_pl':
                    # Debit expense account, credit cash
                    journal_entry["lines"] = [
                        {
                            "account_id": account["id"],
                            "debit": amount,
                            "credit": 0,
                            "memo": f"Expense: {row['description']}"
                        },
                        {
                            "account_id": cash_account["id"],
                            "debit": 0,
                            "credit": amount,
                            "memo": f"Cash payment: {row['description']}"
                        }
                    ]
                elif row['expense_type'] == 'capitalize_bs':
                    # Debit asset account, credit cash
                    journal_entry["lines"] = [
                        {
                            "account_id": account["id"],
                            "debit": amount,
                            "credit": 0,
                            "memo": f"Asset purchase: {row['description']}"
                        },
                        {
                            "account_id": cash_account["id"],
                            "debit": 0,
                            "credit": amount,
                            "memo": f"Cash payment: {row['description']}"
                        }
                    ]
                else:
                    errors.append(f"Row {row_num}: Invalid expense_type. Must be 'expense_pl' or 'capitalize_bs'")
                    continue
                
                # Save cash flow and journal entry
                cashflow_dict = cashflow.dict()
                await db.cashflows.insert_one(cashflow_dict)
                
                await db.journal_entries.insert_one(journal_entry)
                
                # Link journal entry to cash flow
                await db.cashflows.update_one(
                    {"id": cashflow.id},
                    {"$set": {"journal_entry_id": journal_entry["id"]}}
                )
                
                cashflow_dict.pop("_id", None)
                journal_entry.pop("_id", None)
                
                created_cashflows.append(cashflow_dict)
                created_journal_entries.append(journal_entry)
                
            except Exception as e:
                errors.append(f"Row {row_num}: {str(e)}")
        
        return {
            "success": True,
            "created_cashflows": len(created_cashflows),
            "created_journal_entries": len(created_journal_entries),
            "cashflows": created_cashflows,
            "journal_entries": created_journal_entries,
            "errors": errors
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process CSV: {str(e)}")

@api_router.post("/bank-statements/upload")
async def upload_bank_statement(
    company_id: str,
    business_unit_id: Optional[str] = None,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload bank statement CSV for categorization"""
    tenant_id = current_user["tenant_id"]
    
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")
    
    try:
        contents = await file.read()
        csv_data = contents.decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(csv_data))
        
        # Create bank statement record
        bank_statement = BankStatement(
            tenant_id=tenant_id,
            company_id=company_id,
            business_unit_id=business_unit_id,
            upload_filename=file.filename,
            total_transactions=0
        )
        
        transactions = []
        errors = []
        
        for row_num, row in enumerate(csv_reader, start=2):
            try:
                # Expected columns: date, description, amount, type (or auto-detect from amount sign)
                if not all(key in row for key in ['date', 'description', 'amount']):
                    errors.append(f"Row {row_num}: Missing required columns (date, description, amount)")
                    continue
                
                # Parse transaction
                try:
                    transaction_date = datetime.fromisoformat(row['date']).replace(tzinfo=timezone.utc)
                    amount = float(row['amount'])
                    
                    # Determine transaction type
                    transaction_type = row.get('type', '').lower()
                    if not transaction_type:
                        transaction_type = 'credit' if amount > 0 else 'debit'
                        amount = abs(amount)  # Make amount positive
                    
                except (ValueError, InvalidOperation) as e:
                    errors.append(f"Row {row_num}: Invalid date or amount: {str(e)}")
                    continue
                
                transaction = BankTransaction(
                    tenant_id=tenant_id,
                    company_id=company_id,
                    business_unit_id=business_unit_id,
                    bank_statement_id=bank_statement.id,
                    transaction_date=transaction_date,
                    description=row['description'],
                    amount=amount,
                    transaction_type=transaction_type
                )
                
                transactions.append(transaction.dict())
                
            except Exception as e:
                errors.append(f"Row {row_num}: {str(e)}")
        
        # Update total transactions count
        bank_statement.total_transactions = len(transactions)
        
        # Save bank statement and transactions
        bank_statement_dict = bank_statement.dict()
        await db.bank_statements.insert_one(bank_statement_dict)
        
        if transactions:
            await db.bank_transactions.insert_many(transactions)
        
        bank_statement_dict.pop("_id", None)
        for transaction in transactions:
            transaction.pop("_id", None)
        
        return {
            "success": True,
            "bank_statement": bank_statement_dict,
            "transactions_count": len(transactions),
            "transactions": transactions[:10],  # Return first 10 for preview
            "errors": errors
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process bank statement: {str(e)}")

@api_router.get("/bank-statements")
async def get_bank_statements(
    company_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get uploaded bank statements"""
    query = {"tenant_id": current_user["tenant_id"]}
    if company_id:
        query["company_id"] = company_id
    
    statements = await db.bank_statements.find(query).to_list(100)
    
    for statement in statements:
        statement.pop("_id", None)
    
    return statements

@api_router.get("/bank-statements/{statement_id}/transactions")
async def get_bank_transactions(
    statement_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get transactions for a bank statement"""
    tenant_id = current_user["tenant_id"]
    
    transactions = await db.bank_transactions.find({
        "tenant_id": tenant_id,
        "bank_statement_id": statement_id
    }).to_list(1000)
    
    for transaction in transactions:
        transaction.pop("_id", None)
        
        # Add account info if categorized
        if transaction.get("account_id"):
            account = await db.accounts.find_one({"id": transaction["account_id"]})
            if account:
                transaction["account_name"] = account["name"]
    
    return transactions

@api_router.post("/bank-transactions/categorize")
async def categorize_bank_transactions(
    categorizations: List[BankTransactionCategorization],
    current_user: dict = Depends(get_current_user)
):
    """Categorize multiple bank transactions"""
    tenant_id = current_user["tenant_id"]
    updated_count = 0
    
    for cat in categorizations:
        result = await db.bank_transactions.update_one(
            {
                "id": cat.transaction_id,
                "tenant_id": tenant_id
            },
            {
                "$set": {
                    "account_id": cat.account_id,
                    "category": cat.category,
                    "notes": cat.notes,
                    "is_categorized": True
                }
            }
        )
        
        if result.modified_count > 0:
            updated_count += 1
    
    return {
        "success": True,
        "updated_transactions": updated_count
    }

@api_router.post("/bank-transactions/{statement_id}/create-journal-entries")
async def create_journal_entries_from_bank_transactions(
    statement_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Create journal entries from categorized bank transactions"""
    tenant_id = current_user["tenant_id"]
    
    # Get categorized transactions
    transactions = await db.bank_transactions.find({
        "tenant_id": tenant_id,
        "bank_statement_id": statement_id,
        "is_categorized": True,
        "journal_entry_id": None  # Only uncategorized transactions
    }).to_list(1000)
    
    if not transactions:
        raise HTTPException(status_code=400, detail="No categorized transactions found")
    
    # Get cash account
    cash_account = await db.accounts.find_one({
        "tenant_id": tenant_id,
        "company_id": transactions[0]["company_id"],
        "account_type": "Asset",
        "name": {"$regex": "cash", "$options": "i"}
    })
    
    if not cash_account:
        raise HTTPException(status_code=400, detail="No cash account found")
    
    created_entries = []
    
    for transaction in transactions:
        # Get account info
        account = await db.accounts.find_one({"id": transaction["account_id"]})
        if not account:
            continue
        
        # Create journal entry
        journal_entry = {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "company_id": transaction["company_id"],
            "business_unit_id": transaction.get("business_unit_id"),
            "entry_date": transaction["transaction_date"],
            "description": f"Bank: {transaction['description']}",
            "reference": f"BANK-{transaction['id'][:8]}",
            "is_posted": True,
            "lines": [],
            "created_at": datetime.now(timezone.utc)
        }
        
        # Determine journal entry lines based on transaction type
        if transaction["transaction_type"] == "credit":
            # Money coming in (debit cash, credit account)
            journal_entry["lines"] = [
                {
                    "account_id": cash_account["id"],
                    "debit": transaction["amount"],
                    "credit": 0,
                    "memo": f"Bank deposit: {transaction['description']}"
                },
                {
                    "account_id": account["id"],
                    "debit": 0,
                    "credit": transaction["amount"],
                    "memo": f"Revenue: {transaction['description']}"
                }
            ]
        else:  # debit
            # Money going out (debit account, credit cash)
            journal_entry["lines"] = [
                {
                    "account_id": account["id"],
                    "debit": transaction["amount"],
                    "credit": 0,
                    "memo": f"Expense: {transaction['description']}"
                },
                {
                    "account_id": cash_account["id"],
                    "debit": 0,
                    "credit": transaction["amount"],
                    "memo": f"Bank payment: {transaction['description']}"
                }
            ]
        
        # Save journal entry
        await db.journal_entries.insert_one(journal_entry)
        
        # Link back to transaction
        await db.bank_transactions.update_one(
            {"id": transaction["id"]},
            {"$set": {"journal_entry_id": journal_entry["id"]}}
        )
        
        journal_entry.pop("_id", None)
        created_entries.append(journal_entry)
    
    return {
        "success": True,
        "created_entries": len(created_entries),
        "journal_entries": created_entries
    }

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
