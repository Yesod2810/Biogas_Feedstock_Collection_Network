"""Author: Thanh Dat Nguyen
Student ID: 23857030
Date: 3/10/2026
Purpose: Educational request values and program-calculated immutable priorities.
"""

from manual_structures import manual_any, manual_contains


from dataclasses import dataclass, field
from math import isfinite

from module2_hash.records import FarmRecord


class RequestValidationError(ValueError):
    """A request identifier, quantity or time is invalid."""


def validate_request_id(request_id):
    allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
    if (not isinstance(request_id, str) or not 1 <= len(request_id) <= 32
            or manual_any(not manual_contains(allowed, character) for character in request_id)):
        raise RequestValidationError("RequestID must contain 1-32 ASCII letters/digits, '_' or '-'.")
    return request_id


def finite_number(value, label):
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise RequestValidationError("{} must be a finite number.".format(label))
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise RequestValidationError("{} must be a finite number.".format(label)) from error
    if not isfinite(number):
        raise RequestValidationError("{} must be a finite number.".format(label))
    return number


def feedstock_value(value):
    number = finite_number(value, "EstimatedFeedstock")
    if number <= 0:
        raise RequestValidationError("EstimatedFeedstock must be greater than zero tonnes.")
    return number


def calculate_priority(feedstock, transport_minutes):
    """P = F / (T + 1 minute), strictly increasing in F and decreasing in T.

    F is a positive educational quantity in tonnes, not a production estimate
    from the source website. The one-minute allowance is a modelling constant.
    T=0 is valid and produces P=F. No priority is supplied by an input CSV.
    """
    quantity = feedstock_value(feedstock)
    minutes = finite_number(transport_minutes, "TransportTime")
    if minutes < 0:
        raise RequestValidationError("TransportTime must not be negative.")
    priority = quantity / (minutes + 1.0)
    if not isfinite(priority) or priority <= 0:
        raise RequestValidationError("Calculated priority is outside the supported numeric range.")
    return priority


@dataclass(frozen=True)
class ScheduledRequest:
    request_id: str
    farm: FarmRecord
    feedstock: float
    transport_minutes: float
    path: tuple
    priority: float = field(init=False)

    def __post_init__(self):
        validate_request_id(self.request_id)
        if not isinstance(self.farm, FarmRecord):
            raise RequestValidationError("A scheduled request needs a complete FarmRecord.")
        quantity = feedstock_value(self.feedstock)
        minutes = finite_number(self.transport_minutes, "TransportTime")
        priority = calculate_priority(quantity, minutes)
        if (not isinstance(self.path, tuple) or not self.path
                or self.path[0] != self.farm.farm_id
                or manual_any(not isinstance(item, str) or not item for item in self.path)):
            raise RequestValidationError("The route must start at the request's FarmID.")
        object.__setattr__(self, "feedstock", quantity)
        object.__setattr__(self, "transport_minutes", minutes)
        object.__setattr__(self, "priority", priority)

    @property
    def farm_id(self):
        return self.farm.farm_id


def calculation_text(request):
    return ("PRIORITY {} | FarmID={} | F={:g} tonnes | T={:g} minutes "
            "| P={:g}/({:g}+1)={:.6f} | route={}".format(
                request.request_id, request.farm_id, request.feedstock,
                request.transport_minutes, request.feedstock, request.transport_minutes,
                request.priority, " -> ".join(request.path)))
