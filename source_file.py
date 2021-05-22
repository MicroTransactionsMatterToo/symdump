import symdump.symbols
from typing import List, Dict
import os

class SourceFile:
    """Abstraction of a source file generated using symbols.

    Args:
        filename (str): Filename of source file, typically derived from a `SourceLineBeginSymbol`
    """
    def __init__(self, filename: str=''):
        self.filename = filename
        self.basename = self.filename.split("\\")[-1]
        self.symbols: List[symdump.symbols.SymbolEntry] = []
        self.lines: Dict[int, List[symdump.symbols.SymbolEntry]] = {}
        self.header_lines: Dict[int, List[symdump.symbols.SymbolEntry]] = {}
        self.text_lines: List[str] = [f'#include "{self.basename[:-1]}H"\n']
        self.header_text_lines: List[str] = []
        self.curr_line: int = 0
        self.curr_header_line: int = 0
    
    def add_symbol(self, symbol: symdump.symbols.SymbolEntry):
        if type(symbol.symbol) is symdump.symbols.SourceLineSymbol:
            if symbol.symbol.dir_type == 6:
                self.curr_line = symbol.symbol.value
            elif symbol.symbol.dir_type == 0:
                self.curr_line += symbol.symbol.value
        elif type(symbol.symbol) is symdump.symbols.SourceLineBeginSymbol:
            raise Exception("SourceLineBegin symbol passed to SourceFile")
        else:
            if type(symbol.symbol) is symdump.symbols.FunctionSymbol or (symbol.symbol.cls_name != "Typedef" and ('func_return', '({})') not in symbol.symbol.type_modifiers):
                if self.lines.get(self.curr_line) is None:
                    self.lines[self.curr_line] = [symbol]
                else:
                    self.lines[self.curr_line].append(symbol)
                self.curr_line += 1
            else:
                if self.header_lines.get(self.curr_header_line) is None:
                    self.header_lines[self.curr_header_line] = [symbol]
                else:
                    self.header_lines[self.curr_header_line].append(symbol)
                self.curr_header_line += 1

    
    def set_line(self, line_num):
        self.curr_line = line_num
    
    def write_file(self):
        if len(self.lines.keys()) >= 1:
            for i, _ in self.lines.items():
                if self.lines.get(i) is not None:
                    for entry in self.lines[i]:
                        self.text_lines.append(str(entry.symbol) + '\n' if entry.symbol is not None else '')
                else:
                    pass
        if len(self.header_lines.keys()) >= 1:
            for i, _ in self.header_lines.items():
                if self.header_lines.get(i) is not None:
                    for entry in self.header_lines[i]:
                        if entry.symbol.cls_name == 'Typedef' and not entry.symbol.is_function:
                            self.header_text_lines.append("typedef " + str(entry.symbol) + '\n' if entry.symbol is not None else '')
                        else:
                            self.header_text_lines.append(str(entry.symbol) + '\n' if entry.symbol is not None else '')
                            
                else:
                    pass
        self.write_out()
    
    def write_out(self, output_dir="output"):
        split_path = self.filename.upper().split("\\")[1:]  # Remove the first part of the path. Likely not ideal in every circumstance, but removes the C: part of windows paths
        os.makedirs(os.path.join(os.getcwd(), output_dir, *split_path[:-1]), exist_ok=True)
        output_file = os.path.join(os.getcwd(), output_dir, *split_path)
        output_header = output_file[:-1] + 'H'
        with open(output_file, "w") as f:
            f.writelines(self.text_lines)
            f.close()
        with open(output_header, "w") as f:
            f.writelines(self.header_text_lines)
            f.close()


            

