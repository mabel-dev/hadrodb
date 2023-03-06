# strings have a max length of 65535
# ints have a minimum value of -9,223,372,036,854,775,808 and a maximum value of 9,223,372,036,854,775,807 (inclusive)
# floats are IEEE754

import struct


def table_to_tuples(table):
    # Get the schema and columns from the table
    schema = table.schema
    columns = [table.column(i) for i in schema.names]
    # Create a list of tuples from the columns
    rows = [tuple(col[i].as_py() for col in columns) for i in range(table.num_rows)]
    return rows


def check_dict_schema(input_dict, schema):
    for key, schema_info in schema.items():
        expected_type = schema_info["type"]
        is_nullable = schema_info.get("nullable", False)
        if key not in input_dict:
            if is_nullable:
                continue  # nullable field
            else:
                return False
        if input_dict[key] is not None and not isinstance(input_dict[key], expected_type):
            return False
    return True


TYPE_DICT = {
    "BOOLEAN": (">?", struct.calcsize(">?")),
    "FLOAT": (">d", struct.calcsize(">d")),
    "INTEGER": (">q", struct.calcsize(">q")),
}


def check_tuple_schema(data, schema):
    if len(schema) != len(data):
        raise ValueError("Tuple does not match schema: schema and data have different lengths")

    for i, (key, schema_info) in enumerate(schema.items()):
        expected_type = schema_info["type"]
        is_nullable = schema_info.get("nullable", False)
        if data[i] is None:
            if not is_nullable:
                raise ValueError(
                    f"Tuple does not match schema: field '{key}' is not nullable but has value None"
                )
        else:
            if not isinstance(data[i], expected_type):
                raise ValueError(
                    f"Tuple does not match schema: field '{key}' has type {type(data[i])}, expected {expected_type}"
                )


class Row(tuple):
    __slots__ = ()
    _fields = []

    def __new__(cls, data):
        # if cls._schema:
        #    check_tuple_schema(data, cls._schema)
        return super().__new__(cls, data)

    @property
    def as_dict(self):
        return {k: v for k, v in zip(self._fields, self)}

    def __repr__(self):
        return f"Row{super().__repr__()}"

    def __str__(self):
        return str(self.as_dict)

    def __setattr__(self, name, value):
        raise AttributeError("can't set attribute")

    def __delattr__(self, name):
        raise AttributeError("can't delete attribute")

    @classmethod
    def from_bytes(cls, data: bytes) -> tuple:
        fields = []
        offset = 0
        for field_name, field_type in cls._schema.items():
            nullable = field_type["nullable"]
            if nullable:
                has_value = struct.unpack_from(">B", data, offset)[0]
                offset += struct.calcsize(">B")
                if not has_value:
                    fields.append(None)
                    continue
            if field_type["type"] == "VARCHAR":
                str_len = struct.unpack_from(">H", data, offset)[0]
                offset += struct.calcsize(">H")
                str_bytes = struct.unpack_from(f">{str_len}s", data, offset)[0]
                offset += struct.calcsize(f">{str_len}s")
                fields.append(str_bytes.decode("utf-8"))
            elif field_type["type"] in TYPE_DICT:
                form, size = TYPE_DICT[field_type["type"]]
                fields.append(struct.unpack_from(form, data, offset)[0])
                offset += size
            else:
                raise ValueError(f"Invalid field type: {field_type['type']}")
        return cls(fields)

    def to_bytes(self) -> bytes:
        values = []
        for i, (field_name, field_type) in enumerate(self._schema.items()):
            value = self[i]
            if value is None and field_type["nullable"]:
                values.append(struct.pack(">B", 0))
            else:
                if field_type["nullable"]:
                    values.append(struct.pack(">B", 1))
                if field_type["type"] == "VARCHAR":
                    value_bytes = value.encode("utf-8")
                    values.append(
                        struct.pack(f">H{len(value_bytes)}s", len(value_bytes), value_bytes)
                    )
                elif field_type["type"] in TYPE_DICT:
                    form, size = TYPE_DICT[field_type["type"]]
                    values.append(struct.pack(form, value))
                else:
                    raise ValueError(f"Invalid field type: {field_type['type']}")
        return b"".join(values)

    @classmethod
    def create_class(cls, schema):
        row_class = type(
            "RowClass", (Row,), {"_fields": [field for field in schema], "_schema": schema}
        )
        return row_class
