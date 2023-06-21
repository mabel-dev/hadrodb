class Field:
    def __init__(self, name, ftype, nullable=True):
        self.name = name
        self.ftype = ftype
        self.nullable = nullable


class Index:
    def __init__(self, name, fields):
        self.name = name
        self.fields = fields


class TableSchema:
    def __init__(self, fields=None, primary_key=None, indexes=None):
        self._fields = {}
        self.primary_key = primary_key
        self.indexes = indexes or []

        if fields is not None:
            for name, field in fields.items():
                self.add_field(name, field["type"], field.get("nullable", True))

    def add_field(self, name_or_field, field_type=None, nullable=True):
        if isinstance(name_or_field, Field):
            name = name_or_field.name
            field = name_or_field
        else:
            name = name_or_field
            field = Field(name, field_type, nullable)
        self._fields[name] = field

    def remove_field(self, name):
        if name in self._fields:
            del self._fields[name]

    def field(self, i):
        if isinstance(i, int):
            return self._fields[list(self._fields.keys())[i]]
        else:
            return self._fields[i]

    @property
    def num_fields(self):
        return len(self._fields)

    @property
    def names(self):
        return list(self._fields.keys())

    @property
    def types(self):
        return [field["type"] for field in self._fields.values()]

    def to_dict(self):
        return {
            "fields": {
                name: {"type": field["type"], "nullable": field["nullable"]}
                for name, field in self._fields.items()
            },
            "primaryKey": self.primary_key,
            "indexes": [index.to_dict() for index in self.indexes],
        }

    def validate(self, data):
        if not isinstance(data, dict):
            return False

        # Check that all required fields are present
        for field_name, field in self._fields.items():
            if not field["nullable"] and field_name not in data:
                return False

        # Check that all fields have the correct type
        for field_name, field in self._fields.items():
            if field_name in data and not isinstance(data[field_name], field["type"]):
                return False

        return True
