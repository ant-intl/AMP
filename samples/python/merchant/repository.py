from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from common.sqlite_store import SqliteModel, SqliteRepo
from common.multi_currency_money import MultiCurrencyMoney

from .models import Product, Order


# ---------------------------------------------------------------------------
# SQLite path configuration
# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)

# DB file placed in project .data/ directory to keep it out of source tree
_project_root = Path(__file__).resolve().parents[3]
_data_dir = _project_root / ".data"
_data_dir.mkdir(exist_ok=True)

MERCHANT_STORE_PATH = os.environ.get(
    "MERCHANT_STORE_PATH",
    str(_data_dir / "merchant.db"),
)


# ---------------------------------------------------------------------------
# ProductModel
# ---------------------------------------------------------------------------


class ProductModel(SqliteModel):
    """Product table model."""

    def __init__(
        self,
        product_id: str = "",
        name: str = "",
        description: str = "",
        currency: str = "USD",
        price: int = 0,
        stock: int = 0,
        image_url: str = "",
    ) -> None:
        self.product_id = product_id
        self.name = name
        self.description = description
        self.currency = currency
        self.price = price
        self.stock = stock
        self.image_url = image_url

    @property
    def table_name(self) -> str:
        return "product"

    @property
    def pk_column(self) -> str:
        return "product_id"

    @classmethod
    def columns(cls) -> list[tuple[str, str]]:
        return [
            ("product_id", "TEXT PRIMARY KEY"),
            ("name", "TEXT NOT NULL"),
            ("description", "TEXT DEFAULT ''"),
            ("currency", "TEXT NOT NULL DEFAULT 'USD'"),
            ("price", "INTEGER NOT NULL DEFAULT 0"),
            ("stock", "INTEGER NOT NULL DEFAULT 999"),
            ("image_url", "TEXT DEFAULT ''"),
        ]

    def to_row(self) -> dict[str, Any]:
        return {
            "product_id": self.product_id,
            "name": self.name,
            "description": self.description,
            "currency": self.currency,
            "price": self.price,
            "stock": self.stock,
            "image_url": self.image_url,
        }

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "ProductModel":
        return cls(
            product_id=row["product_id"],
            name=row["name"],
            description=row.get("description", ""),
            currency=row.get("currency", "USD"),
            price=row.get("price", 0),
            stock=row.get("stock", 0),
            image_url=row.get("image_url", ""),
        )

    def to_domain(self) -> Product:
        """Convert to domain Product."""
        return Product(
            id=self.product_id,
            name=self.name,
            description=self.description,
            price=MultiCurrencyMoney.of(self.price, self.currency),
            stock=self.stock,
            image_url=self.image_url,
        )


# ---------------------------------------------------------------------------
# CheckoutModel
# ---------------------------------------------------------------------------


class CheckoutModel(SqliteModel):
    """Checkout table model."""

    def __init__(
        self,
        checkout_id: str = "",
        items_json: str = "[]",
        total_amount: int = 0,
        currency: str = "USD",
        merchant_id: str = "",
        created_at: str = "",
    ) -> None:
        self.checkout_id = checkout_id
        self.items_json = items_json
        self.total_amount = total_amount
        self.currency = currency
        self.merchant_id = merchant_id
        self.created_at = created_at

    @property
    def table_name(self) -> str:
        return "checkout"

    @property
    def pk_column(self) -> str:
        return "checkout_id"

    @classmethod
    def columns(cls) -> list[tuple[str, str]]:
        return [
            ("checkout_id", "TEXT PRIMARY KEY"),
            ("items_json", "TEXT NOT NULL"),
            ("total_amount", "INTEGER NOT NULL DEFAULT 0"),
            ("currency", "TEXT NOT NULL DEFAULT 'USD'"),
            ("merchant_id", "TEXT NOT NULL"),
            ("created_at", "TEXT NOT NULL"),
        ]

    def to_row(self) -> dict[str, Any]:
        return {
            "checkout_id": self.checkout_id,
            "items_json": self.items_json,
            "total_amount": self.total_amount,
            "currency": self.currency,
            "merchant_id": self.merchant_id,
            "created_at": self.created_at,
        }

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "CheckoutModel":
        return cls(
            checkout_id=row["checkout_id"],
            items_json=row.get("items_json", "[]"),
            total_amount=row.get("total_amount", 0),
            currency=row.get("currency", "USD"),
            merchant_id=row.get("merchant_id", ""),
            created_at=row.get("created_at", ""),
        )


# ---------------------------------------------------------------------------
# OrderModel
# ---------------------------------------------------------------------------


class OrderModel(SqliteModel):
    """Order table model (table name: order_record to avoid SQL reserved word)."""

    def __init__(
        self,
        order_id: str = "",
        checkout_id: str = "",
        payment_token: str = "",
        status: str = "",
        acquirer_transaction_id: str = "",
        created_at: str = "",
    ) -> None:
        self.order_id = order_id
        self.checkout_id = checkout_id
        self.payment_token = payment_token
        self.status = status
        self.acquirer_transaction_id = acquirer_transaction_id
        self.created_at = created_at

    @property
    def table_name(self) -> str:
        return "order_record"

    @property
    def pk_column(self) -> str:
        return "order_id"

    @classmethod
    def columns(cls) -> list[tuple[str, str]]:
        return [
            ("order_id", "TEXT PRIMARY KEY"),
            ("checkout_id", "TEXT NOT NULL"),
            ("payment_token", "TEXT NOT NULL"),
            ("status", "TEXT NOT NULL"),
            ("acquirer_transaction_id", "TEXT DEFAULT ''"),
            ("created_at", "TEXT NOT NULL"),
        ]

    def to_row(self) -> dict[str, Any]:
        return {
            "order_id": self.order_id,
            "checkout_id": self.checkout_id,
            "payment_token": self.payment_token,
            "status": self.status,
            "acquirer_transaction_id": self.acquirer_transaction_id,
            "created_at": self.created_at,
        }

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "OrderModel":
        return cls(
            order_id=row["order_id"],
            checkout_id=row.get("checkout_id", ""),
            payment_token=row.get("payment_token", ""),
            status=row.get("status", ""),
            acquirer_transaction_id=row.get("acquirer_transaction_id", ""),
            created_at=row.get("created_at", ""),
        )

    def to_domain(self) -> Order:
        """Convert to domain Order."""
        return Order(
            order_id=self.order_id,
            checkout_id=self.checkout_id,
            payment_token=self.payment_token,
            status=self.status,
            acquirer_transaction_id=self.acquirer_transaction_id,
            created_at=self.created_at,
        )


# ---------------------------------------------------------------------------
# Repo instances (module-level singletons, initialized lazily via init_db)
# ---------------------------------------------------------------------------

product_repo: SqliteRepo[ProductModel] | None = None
checkout_repo: SqliteRepo[CheckoutModel] | None = None
order_repo: SqliteRepo[OrderModel] | None = None


# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

SEED_PRODUCTS = [
    ProductModel("PROD-002", "Bali Sunrise Trekking Tour", "Guided sunrise hike up Mount Batur with breakfast and hotel pickup", "USD", 4500, 80, "https://mdn.alipayobjects.com/huamei_4ohk3z/afts/img/HEUgTI3KMfIAAAAAQrAAAAgADkeVAQJr/original"),
    ProductModel("PROD-003", "Paris Seine River Cruise", "1-hour evening cruise along the Seine with live commentary and glass of champagne", "USD", 3500, 150, "https://mdn.alipayobjects.com/huamei_4ohk3z/afts/img/ik5NRawbOkoAAAAAQYAAAAgADkeVAQJr/original"),
    ProductModel("PROD-004", "Sydney Harbour Bridge Climb", "3.5-hour guided climb to the summit of Sydney Harbour Bridge with panoramic views", "USD", 19900, 40, "https://mdn.alipayobjects.com/huamei_4ohk3z/afts/img/t_oKQbHSYYgAAAAAQjAAAAgADkeVAQJr/original"),
    ProductModel("PROD-005", "New York Helicopter Tour", "15-minute helicopter flight over Manhattan skyline including Statue of Liberty", "USD", 25000, 30, "https://mdn.alipayobjects.com/huamei_4ohk3z/afts/img/nMqURp_zSJEAAAAAQjAAAAgADkeVAQJr/original"),
    ProductModel("PROD-007", "AirBuds Pro", "Premium wireless earbuds with noise cancellation", "USD", 12999, 100, "https://mdn.alipayobjects.com/huamei_4ohk3z/afts/img/mw0bQonjbWMAAAAAQTAAAAgADkeVAQJr/original"),
    ProductModel("PROD-010", "Shanghai to Paris One-Way Flight", "Departing October 3 at 10:30 AM from Shanghai Pudong (PVG) to Paris Charles de Gaulle (CDG), economy class", "USD", 65000, 30, "https://mdn.alipayobjects.com/huamei_4ohk3z/afts/img/kLFzRY5tPhUAAAAAgBAAAAgADkeVAQJr/original"),
    ProductModel("PROD-011", "Paris Boutique Hotel - 3 Nights", "3-night stay from October 3 to 6 at a boutique hotel in central Paris, breakfast included", "USD", 54000, 20, "https://mdn.alipayobjects.com/huamei_4ohk3z/afts/img/Jc60Qr714n0AAAAAQzAAAAgADkeVAQJr/original"),
    ProductModel("PROD-012", "Shanghai to Bangkok One-Way Flight", "Departing October 8 at 8:15 AM from Shanghai Pudong (PVG) to Bangkok Suvarnabhumi (BKK), economy class", "USD", 32000, 30, "https://mdn.alipayobjects.com/huamei_4ohk3z/afts/img/2HumQYmqAVEAAAAAeZAAAAgADkeVAQJr/original"),
    ProductModel("PROD-013", "Bangkok Skyline Hotel - 3 Nights", "3-night stay from October 8 to 11 at a 5-star hotel in Bangkok with rooftop pool and city skyline views, breakfast included", "USD", 35000, 20, "https://mdn.alipayobjects.com/huamei_4ohk3z/afts/img/ZEbdRYxsiaQAAAAAQZAAAAgADkeVAQJr/original"),
    ProductModel("PROD-014", "Shanghai to Singapore One-Way Flight", "Departing October 1 at 7:00 PM from Shanghai Pudong (PVG) to Singapore Changi (SIN), economy class", "USD", 38800, 30, "https://mdn.alipayobjects.com/huamei_4ohk3z/afts/img/Z63wQLK6fTwAAAAAgBAAAAgADkeVAQJr/original"),
    ProductModel("PROD-015", "Singapore Marina Bay Hotel - 3 Nights", "3-night stay from October 1 to 4 at a 4-star hotel in Singapore with Marina Bay views, breakfast and free WiFi included", "USD", 48000, 20, "https://mdn.alipayobjects.com/huamei_4ohk3z/afts/img/LshdRoT6GbAAAAAAURAAAAgADkeVAQJr/original"),
]


# ---------------------------------------------------------------------------
# init_db — create repos + seed products
# ---------------------------------------------------------------------------


def init_db() -> None:
    """Initialize repos and reconcile the product catalog with SEED_PRODUCTS.

    The catalog is fixed demo data owned by the source tree and is never
    modified at runtime, so it is reconciled on every startup rather than
    seeded only when the table is empty: SEED entries are upserted and rows no
    longer present in SEED are removed. This keeps a pre-existing local
    database in sync after pulling a catalog change. Checkout and order
    history are left untouched.
    """
    global product_repo, checkout_repo, order_repo

    product_repo = SqliteRepo(MERCHANT_STORE_PATH, ProductModel)
    checkout_repo = SqliteRepo(MERCHANT_STORE_PATH, CheckoutModel)
    order_repo = SqliteRepo(MERCHANT_STORE_PATH, OrderModel)

    seed_ids = {p.product_id for p in SEED_PRODUCTS}
    stale_ids = [
        p.product_id for p in product_repo.select_all() if p.product_id not in seed_ids
    ]
    for p in SEED_PRODUCTS:
        product_repo.save(p)
    for product_id in stale_ids:
        product_repo.delete(product_id)

    logger.info(
        "Product catalog reconciled: %d from seed, %d stale removed",
        len(SEED_PRODUCTS),
        len(stale_ids),
    )
    logger.info("Database initialized: %s", MERCHANT_STORE_PATH)


# ---------------------------------------------------------------------------
# ProductRepository — wraps product_repo with search logic
# ---------------------------------------------------------------------------


class ProductRepository:
    """Product data access with keyword search support."""

    def list_all(self) -> list[Product]:
        """Return all products."""
        assert product_repo is not None, "Call init_db() first"
        return [m.to_domain() for m in product_repo.select_all()]

    def find_by_id(self, product_id: str) -> Product | None:
        """Look up product by ID."""
        assert product_repo is not None, "Call init_db() first"
        m = product_repo.get(product_id)
        return m.to_domain() if m else None

    def search(self, keywords: list[str]) -> list[Product]:
        """Search products by keyword (name + description, case-insensitive)."""
        all_products = self.list_all()
        results = []
        for p in all_products:
            text = (p.name + " " + p.description).lower()
            if any(kw in text for kw in keywords):
                results.append(p)
        return results


# ---------------------------------------------------------------------------
# CheckoutRepository — wraps checkout_repo
# ---------------------------------------------------------------------------


class CheckoutRepository:
    """Checkout data access."""

    def save(
        self,
        checkout_id: str,
        items_json: str,
        total_amount: int,
        currency: str,
        merchant_id: str,
        created_at: str,
    ) -> None:
        """Persist a checkout record."""
        assert checkout_repo is not None, "Call init_db() first"
        model = CheckoutModel(
            checkout_id=checkout_id,
            items_json=items_json,
            total_amount=total_amount,
            currency=currency,
            merchant_id=merchant_id,
            created_at=created_at,
        )
        checkout_repo.save(model)

    def find_by_id(self, checkout_id: str) -> dict | None:
        """Look up checkout by ID, returns dict or None."""
        assert checkout_repo is not None, "Call init_db() first"
        m = checkout_repo.get(checkout_id)
        if m is None:
            return None
        return {
            "checkout_id": m.checkout_id,
            "items_json": m.items_json,
            "total_amount": MultiCurrencyMoney.of(m.total_amount, m.currency),
            "merchant_id": m.merchant_id,
            "created_at": m.created_at,
        }


# ---------------------------------------------------------------------------
# OrderRepository — wraps order_repo with find_success_by_checkout_id
# ---------------------------------------------------------------------------


class OrderRepository:
    """Order data access."""

    def save(self, order: Order) -> None:
        """Persist an order record."""
        assert order_repo is not None, "Call init_db() first"
        model = OrderModel(
            order_id=order.order_id,
            checkout_id=order.checkout_id,
            payment_token=order.payment_token,
            status=order.status,
            acquirer_transaction_id=order.acquirer_transaction_id,
            created_at=order.created_at,
        )
        order_repo.save(model)

    def find_success_by_checkout_id(self, checkout_id: str) -> Order | None:
        """Find a successful order for this checkout (idempotency check)."""
        assert order_repo is not None, "Call init_db() first"
        all_orders = order_repo.select_all()
        for m in all_orders:
            if m.checkout_id == checkout_id and m.status == "SUCCESS":
                return m.to_domain()
        return None
