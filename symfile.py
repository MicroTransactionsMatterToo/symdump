"""
Provides the entry point to a PSX symbol file
"""
import io
import struct
from typing import List, Dict

from symdump.symbols import SymbolEntry
from symdump.source_file import SourceFile
import symdump.symbols as syms

class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

class SymFile(metaclass=Singleton):
    def __init__(self, input: io.BytesIO):
        self.input = input
        self.source_files: Dict[str, List[SourceFile]] = {}

        # Seek to start of file just in case
        self.input.seek(0)

        # Read header
        self.magic, self.version, self.target = struct.unpack("<3sBB3x", self.input.read(8))

        if self.magic != b'MND':
            raise ValueError("Magic number incorrect, expected {}, got {}".format(
                b"MND",
                self.magic
            ))
        self.symbols: List[SymbolEntry] = []
        self.type_definitions: Dict[str, syms.DefinitionSymbol] = {}
        for entry in self:
            self.symbols.append(entry)

    def __next__(self) -> SymbolEntry:
        if self.input.read(1):
            self.input.seek(-1, 1)
            return SymbolEntry(self.input)
        else:
            raise StopIteration

    def __iter__(self):
        return self

    @property
    def definitions(self):
        return [entry for entry in self.symbols if type(entry.symbol) is syms.DefinitionSymbol]

    @property
    def sourcelines(self):
        return [entry for entry in self.symbols if type(entry.symbol) is syms.SourceLineBeginSymbol or type(entry.symbol) is syms.SourceLineSymbol]

    @property
    def functions(self):
        return {func.name:func for func in self.symbols if type(func.symbol) is syms.FunctionSymbol}

    def map_types(self):
        type_defs = [x.symbol for x in self.symbols if type(x.symbol) in [syms.DefinitionSymbol, syms.ArraySymbol]]
        for item in type_defs:
            if self.type_definitions.get(item.name) is not None:
                pass
            else:
                self.type_definitions[item.name] = item




    def create_files(self):
        """Generates `SourceFile` objects for each identifiable source file identified via the SourceLineBegin symbol
        """        
        curr_file = None
        for entry in self.symbols:
            # print(entry)
            symbol = entry.symbol
            if type(entry.symbol) is syms.SourceLineBeginSymbol:
                if not self.source_files.get(symbol.file) and symbol.file is not None:  # Some SourceLineBeginSymbols don't actually have a filename attached to them or whatever reason
                    self.source_files[symbol.file] = SourceFile(symbol.file)
                    self.source_files[symbol.file].set_line(symbol.line[0])
                    print("Current File Changed, object was: ", entry)
                    curr_file = symbol.file
            elif entry.symbol is None:  # Some symbol entries are just a label, and don't actually have any other data attached to them. We ignore these when generating source files
                pass
            else:
                if curr_file is not None:
                    self.source_files[curr_file].add_symbol(entry)

