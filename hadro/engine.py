"""

Typical usage example:

    disk: DiskStorage = DiskStore(file_name="books.db")
    disk.set(key="othello", value="shakespeare")
    author: str = disk.get("othello")
    # it also supports dictionary style API too:
    disk["hamlet"] = "shakespeare"
"""
import io
import os.path
import struct
import typing
from collections import namedtuple

from hadro.config import WRITE_CONSISTENCY
from hadro.config import ConsistencyMode
from orso import logging
from orso.row import Row

logging.set_log_name("MESOS")
logger = logging.get_logger()
logger.setLevel(5)

DELETED_FLAG: int = 1

RecordHeader = namedtuple("RecordHeader", ["flags", "size"])


# DiskStorage is a Log-Structured Hash Table as described in the BitCask paper. We
# keep appending the data to a file, like a log. DiskStorage maintains an in-memory
# hash table called KeyDir, which keeps the row's location on the disk.
#
# The idea is simple yet brilliant:
#   - Write the record to the disk
#   - Update the internal hash table to point to that byte offset
#   - Whenever we get a read request, check the internal hash table for the address,
#       fetch that and return
#
# KeyDir does not store values, only their locations.
#
# The above approach solves a lot of problems:
#   - Writes are insanely fast since you are just appending to the file
#   - Reads are insanely fast since you do only one disk seek. In B-Tree backed
#       storage, there could be 2-3 disk seeks
#
# However, there are drawbacks too:
#   - We need to maintain an in-memory hash table KeyDir. A database with a large
#       number of keys would require more RAM
#   - Since we need to build the KeyDir at initialisation, it will affect the startup
#       time too
#   - Deleted keys need to be purged from the file to reduce the file size
#
# Read the paper for more details: https://riak.com/assets/bitcask-intro.pdf


class HadroDB:
    """
    Implements the KV store on the disk

    Args:
        file_name (str): name of the file where all the data will be written. Just
            passing the file name will save the data in the current directory. You may
            pass the full file location too.

    Attributes:
        file_name (str): name of the file where all the data will be written. Just
            passing the file name will save the data in the current directory. You may
            pass the full file location too.
        file (typing.BinaryIO): file object pointing the file_name
        write_position (int): current cursor position in the file where the data can be
            written
        key_dir (dict[str, KeyEntry]): is a map of key and KeyEntry being the value.
            KeyEntry contains the position of the byte offset in the file where the
            value exists. key_dir map acts as in-memory index to fetch the values
            quickly from the disk
    """

    def __init__(self, collection: typing.Union[str, None] = None):
        logger.warning("HadroDB is experimental and not recommended for use.")
        self.collection: str = collection
        self.file_name: str = collection + "/00000000.data"
        self._schema_file: str = collection + "/00000000.schema"
        self.write_position: int = 0
        self.key_dir: dict[bytes, Row] = {}

        if collection is None:
            raise ValueError("HadroDB requires a collection name")
        # if the collection exists, it must be a folder, not a file
        if os.path.exists(collection):
            if not os.path.isdir(collection):
                raise ValueError("Collection must be a folder")
            # if the file exists already, then we will load the key_dir
        #            self._init_key_dir()
        else:
            os.makedirs(collection, exist_ok=True)

        #        if os.path.exists(self._schema_file):
        #            load the schema

        # we open the file in `a+b` mode:
        # a - says the writes are append only. `a+` means we want append and read
        # b - says that we are operating the file in binary mode (as opposed to the
        #     default string mode)
        self.file: typing.BinaryIO = open(self.file_name, "a+b")
        self.fileno = self.file.fileno()

        schema = {
            "id": {"type": "SMALLINT", "nullable": False},
            "planetId": {"type": "SMALLINT", "nullable": False},
            "name": {"type": "VARCHAR", "nullable": False},
            "gm": {"type": "FLOAT", "nullable": False},
            "radius": {"type": "FLOAT", "nullable": False},
            "density": {"type": "FLOAT", "nullable": True},
            "magnitude": {"type": "FLOAT", "nullable": True},
            "albedo": {"type": "FLOAT", "nullable": True},
        }

        self.rows = Row.create_class(schema)

    def append(self, record) -> None:
        if isinstance(record, dict):
            _record = record.values()
        else:
            _record = record

        record = self.rows(_record)
        # test it matches the schema

        bytes_to_write = record.to_bytes()
        self._write(bytes_to_write)

        # update indices index
        #

        self.write_position += len(bytes_to_write)

    def scan(self, columns=None, predicates=None):
        block_size: int = 8 * 1024 * 1024  # read 1Mb at a time
        self.file.seek(0, 0)

        # TODO: read file header

        buffer = io.BufferedReader(self.file, block_size)  # type: ignore

        header_bytes = buffer.read(5)
        flags, size = struct.unpack(">BI", header_bytes)
        block_start = 5  # start of the current block

        while size > 0:
            if block_start + size > block_size:
                # The current record spans multiple blocks, so read the rest of it in the next block
                remaining_size = size - (block_size - block_start)
                data_bytes = bytearray(
                    buffer.read(block_size - block_start)
                )  # read the remaining bytes in the current block
                while remaining_size > 0:
                    # Read the remaining bytes in subsequent blocks
                    block_bytes = buffer.read(min(remaining_size, block_size))
                    data_bytes += block_bytes
                    remaining_size -= len(block_bytes)
                    block_start = len(block_bytes)
            else:
                # The current record fits in the current block, so just read it
                data_bytes = bytearray(buffer.read(size))
                block_start += size

            if flags & DELETED_FLAG == 0:
                yield self.rows.from_bytes(data_bytes)

            # Read the size of the next record
            header_bytes = buffer.read(5)
            if len(header_bytes) == 0:
                break
            flags, size = struct.unpack(">BI", header_bytes)
            block_start += 5  # add the size of the size field to the start of the next block

    def _write(self, data: bytes) -> None:
        # saving stuff to a file reliably is hard!
        # if you would like to explore and learn more, then
        # start from here: https://danluu.com/file-consistency/
        # and read this too: https://lwn.net/Articles/457667/
        os.write(self.fileno, data)

        if WRITE_CONSISTENCY == ConsistencyMode.AGGRESSIVE:
            # calling fsync after every write is important, this assures that our writes
            # are actually persisted to the disk
            os.fsync(self.fileno)

    def close(self) -> None:
        # before we close the file, we need to safely write the contents in the buffers
        # to the disk. Check documentation of DiskStorage._write() to understand
        # following the operations
        self.file.flush()
        os.fsync(self.fileno)
        self.file.close()
