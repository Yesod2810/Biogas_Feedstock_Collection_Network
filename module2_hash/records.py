"""Author: Thanh Dat Nguyen
Student ID: 23857030
Date: 25/09/2026
Purpose: Immutable complete farm records; no dictionary is used as an ID index.
"""

from manual_structures import LinkedList, manual_all, manual_any, manual_contains, manual_count


from dataclasses import dataclass
from math import isfinite

REQUIRED_COLUMNS = ("Id", "Name", "Species", "Lat", "Lng", "Street Num", "Street",
                    "Suburb", "State", "Postcode", "Country")
ID_CHARACTERS = "0123456789abcdefghijklmnopqrstuvwxyz"


class RecordValidationError(ValueError):
    """A farm record or FarmID is invalid."""


def validate_id(farm_id):
    """The supplied website IDs are exactly five lowercase ASCII letters/digits."""
    if (not isinstance(farm_id, str) or len(farm_id) != 5
            or manual_any(not manual_contains(ID_CHARACTERS, character) for character in farm_id)):
        raise RecordValidationError(
            "Invalid FarmID: {!r}. Use exactly five lowercase letters/digits.".format(farm_id))
    return farm_id


def numerical_coordinate(value, limit, label):
    """Accept numerical CSV text or a number; reject booleans and non-finite values."""
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise RecordValidationError("Invalid {}: {!r}.".format(label, value))
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise RecordValidationError("Invalid {}: {!r}.".format(label, value)) from error
    if not isfinite(number) or not -limit <= number <= limit:
        raise RecordValidationError("Invalid {}: {!r}.".format(label, value))
    return number


@dataclass(frozen=True)
class FarmRecord:
    """All eleven Section 3.2 fields plus the remaining source CSV columns.

    Textual address fields may be blank where the source is blank. The ID is
    never converted to a number, trimmed, lowercased or replaced. Coordinates
    are numerical values; extra source fields are retained as immutable pairs.
    """

    farm_id: str
    name: str
    species: str
    lat: float
    lng: float
    street_num: str
    street: str
    suburb: str
    state: str
    postcode: str
    country: str
    extra_fields: tuple = ()

    def __post_init__(self):
        validate_id(self.farm_id)
        for label, value in (("Name", self.name), ("Species", self.species)):
            if not isinstance(value, str) or not value.strip():
                raise RecordValidationError("{} must not be blank.".format(label))
        for value in (self.street_num, self.street, self.suburb, self.state,
                      self.postcode, self.country):
            if not isinstance(value, str):
                raise RecordValidationError("Address fields must be strings; source blanks are allowed.")
        object.__setattr__(self, "lat", numerical_coordinate(self.lat, 90, "latitude"))
        object.__setattr__(self, "lng", numerical_coordinate(self.lng, 180, "longitude"))
        if (not isinstance(self.extra_fields, tuple)
                or manual_any(not isinstance(pair, tuple) or len(pair) != 2
                       or not manual_all(isinstance(item, str) for item in pair)
                       for pair in self.extra_fields)):
            raise RecordValidationError("Extra fields must be an immutable tuple of text pairs.")
        labels = LinkedList((pair[0] for pair in self.extra_fields))
        if manual_any(manual_contains(REQUIRED_COLUMNS, label) or manual_count(labels, label) > 1 for label in labels):
            raise RecordValidationError("Extra fields must not duplicate a column.")

    def fields(self):
        """Return every mandatory field and all additional original source fields."""
        values = (self.farm_id, self.name, self.species, self.lat, self.lng,
                  self.street_num, self.street, self.suburb, self.state,
                  self.postcode, self.country)
        return tuple(zip(REQUIRED_COLUMNS, values)) + self.extra_fields

    @classmethod
    def from_csv_row(cls, header, row):
        """Build a record from positional CSV fields, preserving all extra columns."""
        if len(header) != len(row):
            raise RecordValidationError("CSV row has the wrong number of fields.")
        if manual_any(manual_count(header, column) != 1 for column in header):
            raise RecordValidationError("CSV header contains duplicate columns.")
        missing = LinkedList((column for column in REQUIRED_COLUMNS if not manual_contains(header, column)))
        if missing:
            raise RecordValidationError("Missing CSV columns: {}.".format(", ".join(missing)))
        # Explicit linear header lookup instead of an automatic index lookup.
        values = LinkedList()
        for column in REQUIRED_COLUMNS:
            position = 0
            while position < len(header) and header[position] != column:
                position += 1
            if position == len(header):
                raise RecordValidationError("Missing CSV column: {}.".format(column))
            values.append(row[position])
        extras = tuple((column, value) for column, value in zip(header, row)
                       if not manual_contains(REQUIRED_COLUMNS, column))
        return cls(*values, extra_fields=extras)


def record_text(record):
    return "\n".join("{}: {}".format(label, value if value != "" else "[source blank]")
                     for label, value in record.fields())
