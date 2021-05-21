import symdump.symbols
from typing import List, Dict

class SourceFile:
    """Abstraction of a source file generated using symbols.

    Args:
        filename (str): Filename of source file, typically derived from a `SourceLineBeginSymbol`
    """
    def __init__(self, filename: str=''):
        self.filename = filename
        self.symbols: List[symdump.symbols.SymbolEntry] = []
        self.lines: Dict[int, List[symdump.symbols.SymbolEntry]] = {}
        self.text_lines: List[str] = []
        self.curr_line: int = 0
    
    def add_symbol(self, symbol: symdump.symbols.SymbolEntry):
        if type(symbol.symbol) is symdump.symbols.SourceLineSymbol:
            if symbol.symbol.dir_type == 6:
                self.curr_line = symbol.symbol.value
            elif symbol.symbol.dir_type == 0:
                self.curr_line += symbol.symbol.value
        elif type(symbol.symbol) is symdump.symbols.SourceLineBeginSymbol:
            raise Exception("SourceLineBegin symbol passed to SourceFile")
        else:
            if self.lines.get(self.curr_line) is None:
                self.lines[self.curr_line] = [symbol]
            else:
                self.lines[self.curr_line].append(symbol)
            self.curr_line += 1
    
    def set_line(self, line_num):
        self.curr_line = line_num
    
    def write_file(self):
        for i in range(0, max(self.lines.keys())):
            if self.lines.get(i) is not None:
                for entry in self.lines[i]:
                    self.text_lines.append(str(entry.symbol) if entry.symbol is not None else '')
            else:
                self.text_lines.append('\n')
            

