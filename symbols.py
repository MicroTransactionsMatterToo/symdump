"""
All the types of symbol supported are present here
"""

__all__ = ["SourceLineSymbol", "SetOverlaySymbol", "OverlaySymbol", "FunctionSymbol", "ArraySymbol", "DefinitionSymbol",
           "SourceLineBeginSymbol", "SymbolEntry"]

import io
import struct
import re
from typing import List, Tuple, Dict, Union

from symdump.utils import *
import symdump

_PRIMITIVE_TYPES: List[str] = [
    'null',
    'void',
    'char',
    'short',
    'int',
    'long',
    'float',
    'double',
    'struct',
    'uniondef',
    'enum',
    'enummember',
    'uchar',
    'ushort',
    'uint',
    'ulong'
]

_SYMBOL_TYPES = {
    -1: "EndFunction",
    0:  "Null",
    1:  "AutoVar",
    2:  "External", 
    3:  "Static",
    4:  "Register",
    5:  "ExternalDefinition",
    6:  "Label",
    7:  "UndefinedLabel",
    8:  "StructMember",
    9:  "Argument",
    10: "Struct",
    11: "UnionMember",
    12: "Union",
    13: "Typedef",
    14: "UndefinedStatic",
    15: "Enum",
    16: "EnumMember",
    17: "RegParam",
    18: "Bitfield",
    19: "AutoArgument",
    20: "LastEntry",
    30: "MangledName",
    100: "Block",
    101: "Function",
    102: "EndOfStruct",
    103: "Filename",
    104: "Line",
    105: "Alias",
    106: "Hidden"
}

_REGISTERS = [
    "zero",
    "at",
    "v0",
    "v1",
    "a0",
    "a1",
    "a2",
    "a3",
    "t0",
    "t1",
    "t2",
    "t3",
    "t4",
    "t5",
    "t6",
    "t7",
    "s0",
    "s1",
    "s2",
    "s3",
    "s4",
    "s5",
    "s6",
    "s7",
    "t8",
    "t9",
    "k0",
    "k1",
    "gp",
    "sp",
    "fp",
    "ra"
]

_TYPE_MODIFIERS: List[Tuple[str, str]] = [
    ("none", ""),
    ("pointer", "*{}"),
    ("func_return", "({})"),
    ("array", "[{}]")
]


class SymbolABC:
    _TYPE_MAPPING: Dict[int, str] = {}

    @classmethod
    def add_type_mapping(cls, type_id: int, name: str) -> None:
        cls._TYPE_MAPPING[type_id] = name

    @classmethod
    def map_type(cls, type_id: int) -> str: return cls._TYPE_MAPPING[type_id]


class OverlaySymbol(SymbolABC):
    def __init__(self, file_input: io.BytesIO):
        self.length, self.id = struct.unpack("<ii", file_input.read(8))

    def __repr__(self):
        return f"<Overlay(id:{self.id},len:{self.length})>"


class SetOverlaySymbol(SymbolABC):
    def __init__(self, file_input: io.BytesIO):
        pass


class BlockSymbol(SymbolABC):
    def __init__(self, file_input: io.BytesIO):
        self.line = int.from_bytes(file_input.read(4), 'little')

    def __repr__(self):
        return f"<Block @ {self.line}>"

    def __str__(self):
        return "{"


class BlockEndSymbol(BlockSymbol):
    def __repr__(self):
        return "<BlockEnd>"
    def __str__(self):
        return "};"


class ArraySymbol(SymbolABC):
    def __init__(self, file_input: io.BytesIO):
        self.cls = struct.unpack("<h", file_input.read(2))[0]
        self._type_modifier = struct.unpack("<H", file_input.read(2))[0]
        self.type_modifiers = [_TYPE_MODIFIERS[(self._type_modifier >> (x * 2 + 4)) & 3] for x in range(0, 6)]
        self.cls_name = _PRIMITIVE_TYPES[self._type_modifier & 0x0F]
        self.length, self.n_dims = struct.unpack("<ih", file_input.read(6))
        self.dims = []
        for i in range(0, self.n_dims):
            dim = struct.unpack("<I", file_input.read(4))[0]
            self.dims.append(dim)
        self.tag = read_pascal_string(file_input).decode('ASCII')
        self.name = read_pascal_string(file_input).decode('ASCII')

    @property
    def type_name(self):
        return _PRIMITIVE_TYPES[self.cls & 0x0F]
    
    @property
    def is_fake(self):
        return re.match(r"\.\d+fake", self.tag) is not None

    def __str__(self):
        if not self.is_fake:
            p1 = f"{self.cls_name} {self.tag if self.tag is not None else ''} {self.name}"
        else:
            actual_type = symdump.SymFile().type_definitions[self.tag]
            p1 = str(actual_type)
        p1 += "".join([f"[{x}]" for x in self.dims]) + ";"
        return p1

    def __repr__(self):
        return "<Array {name}[{type_name}<{modifiers}>]{dims} tag:{tag}".format(
            name=self.name,
            type_name=self.type_name,
            modifiers=",".join([x[0] for x in self.type_modifiers]),
            dims="[" + ",".join([str(x) for x in self.dims]) + "]",
            tag=self.tag
        )

    def get_arg_string(self):
        return str(self)

class FunctionEndSymbol(SymbolABC):
    def __init__(self, file_input: io.BytesIO):
        self.line = struct.unpack("<i", file_input.read(4))[0]


class FunctionSymbol(SymbolABC):
    def __init__(self, file_input: io.BytesIO):
        self.fp, self.fsize, self.retreg, self.mask, self.maskoffs, self.line = struct.unpack("<hihIii",
                                                                                              file_input.read(20))
        self.file = read_pascal_string(file_input).decode('ASCII')
        """The file this function was located in"""        
        self.name = read_pascal_string(file_input).decode('ASCII')
        """Name of the function"""
        self._complete = False
        self.children: List[SymbolEntry] = []
        self.children += [SymbolEntry(file_input)]
        while self.children[-1].type & 0x7F != 14:
            self.children += [SymbolEntry(file_input)]
        self.end = FunctionEndSymbol(file_input)


    def __str__(self):
        indent_amount = 0
        curr_line = 0
        func_def = symdump.SymFile().type_definitions[self.name]
        return_type = str(func_def.type_name)
        arg_strings = ", ".join([str(x)[:-1] for x in self.args])  # Remove the ; from the normal string represetatoin
        blocks = io.StringIO()
        for symbol in [sym for sym in self.children if sym not in self.args]:
            if type(symbol.symbol) is BlockSymbol:
                blocks.write(('\t' * indent_amount) + '{\n')
                indent_amount += 1
            elif type(symbol.symbol) is BlockEndSymbol:
                blocks.write(('\t' * indent_amount) + '}\n')
                indent_amount -= 1
            elif type(symbol) is not None:
                symbol_lines = str(symbol.symbol).splitlines(True)
                symbol_lines = [('\t' * indent_amount) + x + '\n' for x in symbol_lines]
                blocks.writelines(symbol_lines)
        blocks.seek(0)
        out = """{return_type} {func_name}({args}) {{
    {blocks}
}}""".format(
    return_type = return_type,
    func_name = self.name,
    args=arg_strings,
    blocks="".join(blocks.readlines()[:-1])
    )
        return out





    def __repr__(self):
        return "<Function {name}(fp:{fp},fsize:{fsize},retreg:{retreg},mask:0x{mask:x},maskoffs:0x{maskoffs:x})@{file}:{line}".format(
            name=self.name,
            fp=self.fp,
            fsize=self.fsize,
            retreg=self.retreg,
            mask=self.mask,
            maskoffs=self.maskoffs & 0xFFFFFFFF,
            file=self.file,
            line=self.line
        )

    @property
    def defs(self):
        return [x for x in self.children if type(x) is DefinitionSymbol]
    
    @property
    def blocks(self):
        return [x for x in self.children if type(x.symbol) in [BlockSymbol, BlockEndSymbol]]

    @property
    def args(self):
        return [x for x in self.children if x.cls_name in ['RegParam', 'Argument']]

class DefinitionSymbol(SymbolABC):
    def __init__(self, file_input: io.BytesIO):
        self.cls, self._type, self.sz = struct.unpack("<hHi", file_input.read(8))
        self.type_modifiers = [_TYPE_MODIFIERS[(self._type >> (x * 2 + 4)) & 3] for x in range(0, 6)]
        self.name = read_pascal_string(file_input).decode('ASCII')

        self.cls_name = _SYMBOL_TYPES.get(self.cls)
        self.type_name = _PRIMITIVE_TYPES[self._type & 0x0F]
        self.children: List[SymbolEntry] = None

        if self.cls == 10 or self.cls == 15 or self.cls == 12:
            self.children = []
            while True:
                n_definition = SymbolEntry(file_input)
                if n_definition.symbol.cls == 102:
                    break
                else:
                    self.children += [n_definition]
        else:
            pass


    def __hash__(self):
        return hash((self.cls, self.sz, self._type, self.name, self.children))

    def __str__(self):
        modstring = "{}"
        realmods = [x[1] for x in self.type_modifiers if x != ('pointer', '*{}')]
        pointers = self.type_modifiers.count(('pointer', '*{}'))
        for modifier in realmods:
            modstring = modstring.format(modifier)
        
        definitions = ""
        if 'func_return' not in [y[0] for y in self.type_modifiers] and self.children is not None:
            definitions = " {\n"
            for definition in self.children:
                if not definition.symbol.is_fake:
                    definitions += "\t" + str(definition.symbol) + "\n"
                else:
                    definitions += '\n'.join(['\t' + x for x in str.splitlines(str(symdump.SymFile().definitions[definition.symbol.tag]))])[0:-1] + " " + definition.symbol.name + ";\n"
            definitions = definitions[0:-1]
            definitions += "\n}"
        
        decl = ''
        if 'pointer' in [y[0] for y in self.type_modifiers] and 'func_return' in [y[0] for y in self.type_modifiers]:
            decl = f"{self.type_name} ({'*' * pointers}{self.name}){modstring} "
        else:
            decl = f"{self.type_name}{'*'*pointers} {self.name}{modstring}"
        if not self.is_function:
            decl += definitions
        decl += ";"
        return decl
        


    def __repr__(self):
        return "<Definition {name}[{type_name}<{modifiers}>](cls:{cls},sz:{sz},defs:{defs})".format(
            type_name=self.type_name,
            modifiers=",".join([x[0] for x in self.type_modifiers]),
            cls=self.cls,
            sz=self.sz,
            name=self.name,
            defs=f"<List sz={len(self.children)}>" if self.children is not None else None
        )


    @property
    def is_fake(self):
        return re.match(r"^\.\d+fake$", self.name) is not None

    @property
    def is_function(self):
        return ('func_return', '({})') in self.type_modifiers


class SourceLineBeginSymbol(SymbolABC):
    def __init__(self, file_input: io.BytesIO):
        self.line = struct.unpack("<I", file_input.read(4))
        self.sl_symbols = []
        self.file = read_pascal_string(file_input).decode('ASCII')

    def __repr__(self):
        return f"<SourceLineBegin(file:{self.file},line:{self.line})>"


class SourceLineSymbol(SymbolABC):
    """
    These symbols are used to indicate what line of the most recently set file we are on
    """

    typenums: List[int] = [0, 2, 4, 6]
    """Associated type numbers for different kinds of source line symbols"""

    sizes: Dict[int, Tuple[Union[None, str], str]] = {
        0: (0, None, "sl_inc"),
        2: (1, "B", "sl_add1"),
        4: (2, "H", "sl_add2"),
        6: (4, "I", "sl_set")
    }

    def __init__(self, file_input: io.BytesIO, dir_type: int):
        self.dir_type = dir_type
        if dir_type != 0:
            self.value = struct.unpack(f"<{self.sizes[dir_type][1]}", file_input.read(self.sizes[dir_type][0]))[0]
        else:
            self.value = 1

    def __add__(self, other):
        return self.value + other

    def __sub__(self, other):
        return self.value - other

    def __repr__(self):
        return "<SourceLine[{sz}]({val})>".format(
            sz=self.sizes[self.dir_type][2],
            val=self.value
        )


# Dispatch dictionary for basic symbols
_TYPE_MAPPING = {
    0: lambda x: SourceLineSymbol(x, 0),
    2: lambda x: SourceLineSymbol(x, 2),
    4: lambda x: SourceLineSymbol(x, 4),
    6: lambda x: SourceLineSymbol(x, 6),
    8: SourceLineBeginSymbol,
    12: FunctionSymbol,
    16: BlockSymbol,
    18: BlockEndSymbol,
    20: DefinitionSymbol,
    22: ArraySymbol,
    24: OverlaySymbol,
    26: SetOverlaySymbol
}


class SymbolEntry:
    """
    Every symbol in the file is preceded by this. Due to the structure of the file, this class essentially acts as a
    wrapper for symbol.

    Structure is like this:
    | Addr (uint) | Symbol Type (uchar) | mx_info (Optional, uchar) | Label (Pascal Style String, char[]) | Symbol Definition (XXX) |
    """

    def __init__(self, file_input: io.BytesIO):
        self.loc = file_input.tell()
        self.value, self.type = struct.unpack("<IB", file_input.read(5))
        self.type_name = _SYMBOL_TYPES.get(self.type)
        self.mx_info: Union[None, int] = None
        self.label: Union[None, str] = None
        self.symbol: Union[None, SourceLineSymbol, SetOverlaySymbol, OverlaySymbol, FunctionSymbol, ArraySymbol, DefinitionSymbol,
           SourceLineBeginSymbol, SymbolEntry] = None
        if self.type == 8:
            self.mx_info = struct.unpack("<B", file_input.read(1))[0]
        if self.type & 0x80 == 0:
            self.label = read_pascal_string(file_input).decode('ASCII')
        if self.type & 0x7F in _TYPE_MAPPING.keys() and self.type & 0x80 != 0:
            self.symbol = _TYPE_MAPPING[self.type & 0x7F](file_input)

    def __repr__(self):
        return "<SymbolEntry(val:0x{:x},loc:{},type:{},label:{},symbol:{}>".format(
            self.value,
            self.loc,
            self.type,
            self.label,
            type(self.symbol).__name__ if self.symbol is not None else None
        )

    def __str__(self):
        return str(self.symbol)

    @property
    def cls_name(self):
        """Attempts to return the class name of the underlying symbol. If not possible returns None
        """
        try:
            return self.symbol.cls_name
        except (NameError, AttributeError) as e:
            return None

    @property
    def name(self):
        try:
            return self.symbol.name
        except (NameError, AttributeError):
            return None
    