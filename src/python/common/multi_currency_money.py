"""
MultiCurrencyMoney - Multi-currency money class

Core design:
  - Internally uses int to store the smallest currency unit value (e.g.: cents for CNY, yen for JPY), field name ``cent``
  - Objects are **mutable**, providing two styles: ``add``/``add_to``
  - Supports ISO 4217 currency codes (CNY) and numeric codes (156)
  - Default rounding mode: banker's rounding (ROUND_HALF_EVEN)
  - Validates currency consistency before operations, raises ValueError on mismatch
  - Provides ``of(minor_units, currency)`` factory method (construct from smallest unit)
"""

from __future__ import annotations

import re
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation
from typing import Any, Union

try:
    from pydantic import GetCoreSchemaHandler
    from pydantic_core import CoreSchema, core_schema
    _HAS_PYDANTIC = True
except ImportError:  # pragma: no cover
    _HAS_PYDANTIC = False

# ---------------------------------------------------------------------------
# Rounding mode constants
# ---------------------------------------------------------------------------
ROUND_UP = "ROUND_UP"
ROUND_DOWN = "ROUND_DOWN"
ROUND_CEILING = "ROUND_CEILING"
ROUND_FLOOR = "ROUND_FLOOR"
ROUND_HALF_UP = "ROUND_HALF_UP"
ROUND_HALF_DOWN = "ROUND_HALF_DOWN"
ROUND_HALF_EVEN_NAME = "ROUND_HALF_EVEN"
ROUND_UNNECESSARY = "ROUND_UNNECESSARY"

_PYTHON_ROUNDING_MAP = {
    ROUND_UP: "ROUND_UP",
    ROUND_DOWN: "ROUND_DOWN",
    ROUND_CEILING: "ROUND_CEILING",
    ROUND_FLOOR: "ROUND_FLOOR",
    ROUND_HALF_UP: "ROUND_HALF_UP",
    ROUND_HALF_DOWN: "ROUND_HALF_DOWN",
    ROUND_HALF_EVEN_NAME: "ROUND_HALF_EVEN",
    ROUND_UNNECESSARY: "ROUND_UNNECESSARY",
}

# Default rounding mode: banker's rounding
DEFAULT_ROUNDING_MODE = ROUND_HALF_EVEN_NAME

# Default currency code
DEFAULT_CURRENCY_CODE = "CNY"

# Only digits 0-9, '.', '+', '-' are allowed
_DIGITS_PATTERN: re.Pattern = re.compile(r"^[+-]?[0-9.]+$")

# Major/minor unit conversion table: index = fraction digits, value = centFactor
_CENT_FACTORS = [1, 10, 100, 1000, 10000, 100000]


# ---------------------------------------------------------------------------
# Currency enumeration (compact version)
# currency_code: ISO 4217 alphabetic code (CNY, USD, ...)
# currency_value: ISO 4217 numeric code (156, 840, ...)
# fraction_digits: number of fraction digits for the currency
# ---------------------------------------------------------------------------
class _CurrencyInfo:
    """Internal currency info."""

    __slots__ = ("currency_code", "currency_value", "fraction_digits")

    def __init__(self, code: str, value: str, digits: int) -> None:
        self.currency_code = code
        self.currency_value = value
        self.fraction_digits = digits

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, _CurrencyInfo):
            return False
        return self.currency_code == other.currency_code

    def __hash__(self) -> int:
        return hash(self.currency_code)

    def __repr__(self) -> str:
        return self.currency_code


_CURRENCY_TABLE: dict[str, _CurrencyInfo] = {}
_CURRENCY_VALUE_TABLE: dict[str, _CurrencyInfo] = {}


def _register(code: str, value: str, digits: int) -> None:
    info = _CurrencyInfo(code, value, digits)
    _CURRENCY_TABLE[code] = info
    _CURRENCY_VALUE_TABLE[value] = info


# Register common currencies
_register("CNY", "156", 2)
_register("USD", "840", 2)
_register("EUR", "978", 2)
_register("GBP", "826", 2)
_register("HKD", "344", 2)
_register("JPY", "392", 0)
_register("KRW", "410", 0)


def _get_currency_info(currency_code: str) -> _CurrencyInfo:
    """Look up currency info by alphabetic or numeric code."""
    code = currency_code.upper()
    info = _CURRENCY_TABLE.get(code)
    if info is not None:
        return info
    info = _CURRENCY_VALUE_TABLE.get(currency_code)
    if info is not None:
        return info
    raise ValueError(f"Unsupported currency: {currency_code}")


def _get_fraction_digits(currency_code: str) -> int:
    """Return the number of fraction digits for the currency (defaults to 2 for unknown)."""
    try:
        return _get_currency_info(currency_code).fraction_digits
    except ValueError:
        return 2


def _get_cent_factor(currency_code: str) -> int:
    """Return the major/minor unit conversion factor."""
    digits = _get_fraction_digits(currency_code)
    if digits < len(_CENT_FACTORS):
        return _CENT_FACTORS[digits]
    return 10 ** digits


def _to_python_rounding(rounding_mode: str) -> str:
    """Convert module rounding constant to Decimal module rounding constant name."""
    mapped = _PYTHON_ROUNDING_MAP.get(rounding_mode)
    if mapped is None:
        raise ValueError(f"Unsupported rounding mode: {rounding_mode}")
    return mapped


def _create_big_decimal(amount: str) -> Decimal:
    """Safely create a Decimal, disallowing scientific notation and illegal characters."""
    if not _DIGITS_PATTERN.match(amount):
        raise ValueError(
            f"Amount string only allows digits, decimal point, and sign, got: '{amount}'"
        )
    try:
        return Decimal(amount)
    except InvalidOperation as e:
        raise ValueError(f"Cannot parse '{amount}' as a valid amount: {e}") from e


# ---------------------------------------------------------------------------
# MultiCurrencyMoney
# ---------------------------------------------------------------------------
class MultiCurrencyMoney:
    """
    Multi-currency money class.

    **Mutable object**: operations ``add``/``subtract``/``multiply``/``divide`` return new objects,
    while ``add_to``/``subtract_from``/``multiply_by``/``divide_by`` modify in place.

    Internally uses ``int`` to store the smallest currency unit value (``cent``), e.g.:
    - CNY/USD: cents (cent = yuan * 100)
    - JPY/KRW: yen (cent = yen * 1)

    Examples
    --------
    >>> m = MultiCurrencyMoney.of(10000, "CNY")   # 100.00 CNY (10000 cents)
    >>> m2 = MultiCurrencyMoney.of(5050, "CNY")    # 50.50 CNY
    >>> m.add(m2)                                   # 150.50 CNY (new object)
    >>> m.add_to(m2)                                # accumulate in place
    """

    __slots__ = ("_cent", "_currency_info")

    # ------------------------------------------------------------------
    # Constructor
    # ------------------------------------------------------------------
    def __init__(
            self,
            yuan: Union[int, float, str, Decimal, None] = None,
            cent_part: int = 0,
            currency_code: str | None = None,
            rounding_mode: str = DEFAULT_ROUNDING_MODE,
    ) -> None:
        """
        Constructor, supports various parameter combinations.

        Parameters
        ----------
        yuan : int | float | str | Decimal | None
            Amount (in major unit), can be:
            - int/str/Decimal: amount in major units
            - None: zero amount
        cent_part : int
            Minor unit part (only meaningful when yuan is int).
            e.g. ``MultiCurrencyMoney(100, 50, "CNY")`` = 100 yuan 50 cents = 100.50 CNY.
        currency_code : str | None
            Currency code (ISO 4217 alphabetic or numeric code). Defaults to CNY when None.
        rounding_mode : str
            Rounding mode, defaults to ROUND_HALF_EVEN (banker's rounding).
        """
        # Resolve currency
        code = currency_code if currency_code is not None else DEFAULT_CURRENCY_CODE
        info = _get_currency_info(code)
        object.__setattr__(self, "_currency_info", info)

        fraction_digits = info.fraction_digits
        cent_factor = _get_cent_factor(info.currency_code)

        if yuan is None:
            # Zero value
            object.__setattr__(self, "_cent", 0)

        elif isinstance(yuan, (int, float)) and cent_part != 0 and not isinstance(yuan, bool):
            # MultiCurrencyMoney(yuan, cent, currency) form
            # Check cent overflow
            if cent_part >= cent_factor:
                raise OverflowError(
                    f"Overflow of cent, cent({cent_part}) >= centFactor({cent_factor})"
                )
            object.__setattr__(
                self, "_cent", int(yuan) * cent_factor + (cent_part % cent_factor)
            )

        elif isinstance(yuan, float):
            # float constructor (@Deprecated usage)
            object.__setattr__(
                self, "_cent", round(yuan * cent_factor)
            )

        elif isinstance(yuan, str):
            # String constructor
            bd = _create_big_decimal(yuan)
            scaled = bd.scaleb(fraction_digits)
            py_rounding = _to_python_rounding(rounding_mode)
            object.__setattr__(
                self, "_cent", int(scaled.quantize(Decimal(1), rounding=py_rounding))
            )

        elif isinstance(yuan, Decimal):
            # BigDecimal constructor
            scaled = yuan.scaleb(fraction_digits)
            py_rounding = _to_python_rounding(rounding_mode)
            object.__setattr__(
                self, "_cent", int(scaled.quantize(Decimal(1), rounding=py_rounding))
            )

        elif isinstance(yuan, int):
            # int constructor (no cent_part or cent_part == 0)
            object.__setattr__(self, "_cent", yuan * cent_factor)

        else:
            raise TypeError(f"Unsupported amount type: {type(yuan).__name__}")

    # ------------------------------------------------------------------
    # Factory methods
    # ------------------------------------------------------------------
    @classmethod
    def of(cls, minor_units: Union[int, str], currency_code: str) -> "MultiCurrencyMoney":
        """
        Construct an amount object from the smallest currency unit.

        Parameters
        ----------
        minor_units : int | str
            Value in the smallest currency unit (e.g.: cents for CNY, yen for JPY)
        currency_code : str
            Currency code (e.g. CNY, USD, JPY)

        Examples
        --------
        >>> MultiCurrencyMoney.of(10000, "CNY")   # 100.00 CNY
        >>> MultiCurrencyMoney.of(1500, "JPY")     # 1500 JPY

        Raises
        ------
        ValueError
            If ``minor_units`` is negative. Constructing money from an external
            (untrusted) minor-unit value must never yield a negative amount —
            this defends downstream logic (e.g. budget deduction) against
            negative-amount attacks. Zero is allowed. Internal arithmetic that
            can legitimately produce negatives (subtract/__neg__) does not use
            this factory.
        """
        info = _get_currency_info(currency_code)
        cent = int(minor_units)
        if cent < 0:
            raise ValueError(f"minor_units must be non-negative, got: {cent}")
        money = cls.__new__(cls)
        object.__setattr__(money, "_currency_info", info)
        object.__setattr__(money, "_cent", cent)
        return money

    @classmethod
    def zero(cls, currency_code: str) -> "MultiCurrencyMoney":
        """Construct a zero-value amount object."""
        return cls.of(0, currency_code)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------
    @property
    def cent(self) -> int:
        """
        Value in the smallest currency unit (prefer fetch_minor_units).
        """
        return self._cent

    def get_cent(self) -> int:
        """Get value in the smallest currency unit (@Deprecated)."""
        return self._cent

    def set_cent(self, value: int) -> None:
        """Set value in the smallest currency unit."""
        object.__setattr__(self, "_cent", int(value))

    def fetch_minor_units(self) -> int:
        """Get value in the smallest currency unit (recommended)."""
        return self._cent

    def get_amount(self) -> Decimal:
        """
        Get the amount value (in major unit).

        Returns
        -------
        Decimal
            Amount in major unit. e.g. cent=10050, CNY -> Decimal("100.50")
        """
        fraction_digits = self._currency_info.fraction_digits
        return Decimal(self._cent).scaleb(-fraction_digits)

    def fetch_amount_str(self) -> str:
        """Get amount as string (in major unit)."""
        return str(self.get_amount())

    @property
    def currency_code(self) -> str:
        """Currency code (ISO 4217 alphabetic code, e.g. CNY)."""
        return self._currency_info.currency_code

    @property
    def currency_value(self) -> str:
        """Currency numeric code (e.g. 156, 840)."""
        return self._currency_info.currency_value

    def get_currency_code(self) -> str:
        """Get currency code."""
        return self._currency_info.currency_code

    def get_currency_value(self) -> str:
        """Get currency numeric code."""
        return self._currency_info.currency_value

    def get_cent_factor(self) -> int:
        """Get major/minor unit conversion factor."""
        return _get_cent_factor(self._currency_info.currency_code)

    # ------------------------------------------------------------------
    # Currency setters
    # ------------------------------------------------------------------
    def set_currency(self, currency_code: str) -> None:
        """
        Set currency (@Deprecated, risk of financial loss).
        """
        info = _get_currency_info(currency_code)
        object.__setattr__(self, "_currency_info", info)

    def set_currency_value(self, currency_value: str) -> None:
        """
        Set currency numeric code (@Deprecated, risk of financial loss).
        """
        info = _CURRENCY_VALUE_TABLE.get(currency_value)
        if info is None:
            # Compatibility: might be an alphabetic code
            info = _CURRENCY_TABLE.get(currency_value.upper())
        if info is None:
            raise ValueError(f"Unsupported currency numeric or alphabetic code: {currency_value}")
        object.__setattr__(self, "_currency_info", info)

    # ------------------------------------------------------------------
    # Comparison
    # ------------------------------------------------------------------
    def _assert_same_currency(self, other: "MultiCurrencyMoney") -> None:
        """Assert two money objects have the same currency, raises ValueError otherwise."""
        if self._currency_info != other._currency_info:
            raise ValueError("Money math currency mismatch.")

    def equals(self, other: object) -> bool:
        """Check equality."""
        if not isinstance(other, MultiCurrencyMoney):
            return False
        return self._currency_info == other._currency_info and self._cent == other._cent

    def compare_to(self, other: "MultiCurrencyMoney") -> int:
        """
        Compare two money objects.

        Returns
        -------
        -1 : less than
         0 : equal
         1 : greater than
        """
        self._assert_same_currency(other)
        if self._cent < other._cent:
            return -1
        elif self._cent == other._cent:
            return 0
        else:
            return 1

    def greater_than(self, other: "MultiCurrencyMoney") -> bool:
        """Check if greater than."""
        return self.compare_to(other) > 0

    # ------------------------------------------------------------------
    # Money arithmetic
    # ------------------------------------------------------------------
    def _new_money_with_same_currency(self, cent: int) -> "MultiCurrencyMoney":
        """Create a new money object with the same currency and specified minor unit value."""
        money = MultiCurrencyMoney.__new__(MultiCurrencyMoney)
        object.__setattr__(money, "_currency_info", self._currency_info)
        object.__setattr__(money, "_cent", cent)
        return money

    # ---- Addition ----

    def add(self, other: "MultiCurrencyMoney") -> "MultiCurrencyMoney":
        """
        Money addition, returns a new object.

        Raises ValueError if currencies differ.
        """
        self._assert_same_currency(other)
        return self._new_money_with_same_currency(self._cent + other._cent)

    def add_to(self, other: "MultiCurrencyMoney") -> "MultiCurrencyMoney":
        """
        Money accumulation, modifies in place and returns self.
        """
        self._assert_same_currency(other)
        object.__setattr__(self, "_cent", self._cent + other._cent)
        return self

    # ---- Subtraction ----

    def subtract(self, other: "MultiCurrencyMoney") -> "MultiCurrencyMoney":
        """
        Money subtraction, returns a new object.
        """
        self._assert_same_currency(other)
        return self._new_money_with_same_currency(self._cent - other._cent)

    def subtract_from(self, other: "MultiCurrencyMoney") -> "MultiCurrencyMoney":
        """
        Money deduction, modifies in place and returns self.
        """
        self._assert_same_currency(other)
        object.__setattr__(self, "_cent", self._cent - other._cent)
        return self

    # ---- Multiplication ----

    def multiply(self, val: Union[int, str, Decimal]) -> "MultiCurrencyMoney":
        """
        Money multiplication (int uses direct arithmetic, Decimal/str uses default rounding), returns a new object.
        """
        if isinstance(val, int) and not isinstance(val, bool):
            return self._new_money_with_same_currency(self._cent * val)
        # BigDecimal path
        bd = Decimal(str(val)) if not isinstance(val, Decimal) else val
        new_cent = Decimal(self._cent) * bd
        py_rounding = _to_python_rounding(DEFAULT_ROUNDING_MODE)
        rounded = int(new_cent.quantize(Decimal(1), rounding=py_rounding))
        return self._new_money_with_same_currency(rounded)

    def multiply_with_rounding(
            self, val: Union[str, Decimal], rounding_mode: str
    ) -> "MultiCurrencyMoney":
        """
        Money multiplication (with specified rounding mode), returns a new object.
        """
        bd = Decimal(str(val)) if not isinstance(val, Decimal) else val
        new_cent = Decimal(self._cent) * bd
        py_rounding = _to_python_rounding(rounding_mode)
        rounded = int(new_cent.quantize(Decimal(1), rounding=py_rounding))
        return self._new_money_with_same_currency(rounded)

    def multiply_by(self, val: Union[int, str, Decimal]) -> "MultiCurrencyMoney":
        """
        Money multiplication in place, modifies and returns self.
        """
        if isinstance(val, int) and not isinstance(val, bool):
            object.__setattr__(self, "_cent", self._cent * val)
            return self
        bd = Decimal(str(val)) if not isinstance(val, Decimal) else val
        new_cent = Decimal(self._cent) * bd
        py_rounding = _to_python_rounding(DEFAULT_ROUNDING_MODE)
        object.__setattr__(
            self, "_cent", int(new_cent.quantize(Decimal(1), rounding=py_rounding))
        )
        return self

    # ---- Division ----

    def divide(self, val: Union[int, str, Decimal]) -> "MultiCurrencyMoney":
        """
        Money division (default rounding), returns a new object.
        """
        bd = Decimal(str(val)) if not isinstance(val, (int, Decimal)) else Decimal(val)
        new_cent = Decimal(self._cent) / bd
        py_rounding = _to_python_rounding(DEFAULT_ROUNDING_MODE)
        rounded = int(new_cent.quantize(Decimal(1), rounding=py_rounding))
        return self._new_money_with_same_currency(rounded)

    def divide_with_rounding(
            self, val: Union[str, Decimal], rounding_mode: str
    ) -> "MultiCurrencyMoney":
        """
        Money division (with specified rounding mode), returns a new object.
        """
        bd = Decimal(str(val)) if not isinstance(val, Decimal) else val
        new_cent = Decimal(self._cent) / bd
        py_rounding = _to_python_rounding(rounding_mode)
        rounded = int(new_cent.quantize(Decimal(1), rounding=py_rounding))
        return self._new_money_with_same_currency(rounded)

    def divide_by(self, val: Union[int, str, Decimal]) -> "MultiCurrencyMoney":
        """
        Money division in place, modifies and returns self.
        """
        bd = Decimal(str(val)) if not isinstance(val, (int, Decimal)) else Decimal(val)
        new_cent = Decimal(self._cent) / bd
        py_rounding = _to_python_rounding(DEFAULT_ROUNDING_MODE)
        object.__setattr__(
            self, "_cent", int(new_cent.quantize(Decimal(1), rounding=py_rounding))
        )
        return self

    # ------------------------------------------------------------------
    # Python magic methods
    # ------------------------------------------------------------------
    def __eq__(self, other: object) -> bool:
        return self.equals(other)

    def __hash__(self) -> int:
        return hash((self._cent, self._currency_info.currency_code))

    def __lt__(self, other: "MultiCurrencyMoney") -> bool:
        return self.compare_to(other) < 0

    def __le__(self, other: "MultiCurrencyMoney") -> bool:
        return self.compare_to(other) <= 0

    def __gt__(self, other: "MultiCurrencyMoney") -> bool:
        return self.compare_to(other) > 0

    def __ge__(self, other: "MultiCurrencyMoney") -> bool:
        return self.compare_to(other) >= 0

    def __add__(self, other: "MultiCurrencyMoney") -> "MultiCurrencyMoney":
        return self.add(other)

    def __sub__(self, other: "MultiCurrencyMoney") -> "MultiCurrencyMoney":
        return self.subtract(other)

    def __mul__(self, val: Union[int, str, Decimal]) -> "MultiCurrencyMoney":
        return self.multiply(val)

    def __truediv__(self, val: Union[int, str, Decimal]) -> "MultiCurrencyMoney":
        return self.divide(val)

    def __neg__(self) -> "MultiCurrencyMoney":
        return self._new_money_with_same_currency(-self._cent)

    def __abs__(self) -> "MultiCurrencyMoney":
        return self._new_money_with_same_currency(abs(self._cent))

    def __repr__(self) -> str:
        return (
            f"MultiCurrencyMoney [cent={self._cent}, "
            f"currency={self._currency_info.currency_code}, "
            f"currencyValue={self._currency_info.currency_value}]"
        )

    def __str__(self) -> str:
        return f"{self.fetch_amount_str()} {self._currency_info.currency_code}"

    # ------------------------------------------------------------------
    # Pydantic v2 integration
    # ------------------------------------------------------------------
    if _HAS_PYDANTIC:
        @classmethod
        def __get_pydantic_core_schema__(
                cls, source_type: Any, handler: GetCoreSchemaHandler
        ) -> CoreSchema:
            return core_schema.no_info_plain_validator_function(
                cls._pydantic_validate,
                serialization=core_schema.plain_serializer_function_ser_schema(
                    cls._pydantic_serialize,
                    info_arg=False,
                    when_used="always",
                ),
            )

        @classmethod
        def _pydantic_validate(cls, v: Any) -> "MultiCurrencyMoney":
            """Validate and construct from dict or existing instance."""
            if isinstance(v, cls):
                return v
            if isinstance(v, dict):
                if "cent" in v and "currency" in v:
                    return cls.of(v["cent"], v["currency"])
                if "value" in v and "currency" in v:
                    return cls(v["value"], currency_code=v["currency"])
                if "amount" in v and "currency" in v:
                    return cls(str(v["amount"]), currency_code=v["currency"])
            raise ValueError(
                f"Cannot parse {v} as MultiCurrencyMoney, "
                f"expected dict with 'cent'+'currency' or 'value'+'currency'"
            )

        @classmethod
        def _pydantic_serialize(cls, v: "MultiCurrencyMoney") -> dict:
            """Serialize to dict for JSON output."""
            if v is None:
                return None
            return {"cent": v.fetch_minor_units(), "currency": v.currency_code}

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------
    def to_dict(self) -> dict:
        """
        Serialize to dict format.

        Returns
        -------
        dict
            {"value": "100.50", "currency": "CNY"}
        """
        return {
            "value": self.fetch_amount_str(),
            "currency": self._currency_info.currency_code,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MultiCurrencyMoney":
        """
        Deserialize from dict.

        Expected format::

            {"value": "100.50", "currency": "CNY"}
        """
        if "value" not in data or "currency" not in data:
            raise ValueError(
                f"Deserialization failed: missing 'value' or 'currency' field, got: {data}"
            )
        return cls(data["value"], currency_code=data["currency"])
