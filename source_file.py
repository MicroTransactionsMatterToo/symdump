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
        self.include_files: Dict[str, symdump.symbols.SymbolEntry] = {}
        self.__file_symbol_count = 0
        self.text_lines: List[str] = [f'#include "{self.basename[:-1]}H"\n']
        self.header_text_lines: List[str] = []
        self.lines_written: bool = False
        self.curr_line: int = 0
        self.curr_header_line: int = 0

    def __str__(self) -> str:
        self.write_lines()
        return "".join(self.text_lines)
    
    def add_symbol(self, symbol: symdump.symbols.SymbolEntry):
        # if self.__file_symbol_count > 1:
        #     if type(symbol.symbol) is symdump.symbols.DefinitionSymbol and symbol.type_name == 'null':
        #         self.include_files[symbol.symbol.name] = symbol
        #     return
        if type(symbol.symbol) is symdump.symbols.SourceLineSymbol:
            if symbol.symbol.dir_type == 6:
                self.curr_line = symbol.symbol.value
            elif symbol.symbol.dir_type == 0:
                self.curr_line += symbol.symbol.value
        elif type(symbol.symbol) is symdump.symbols.SourceLineBeginSymbol:
            raise Exception("SourceLineBegin symbol passed to SourceFile")
        else:
            # if symbol.type_name == 'null':
            #     self.include_files[symbol.symbol.name] = symbol
            #     self.__file_symbol_count += 1
            if type(symbol.symbol) is symdump.symbols.DefinitionSymbol and symbol.symbol.cls_name == "Filename":
                if self.lines.get(self.curr_line) is None:
                    self.lines[self.curr_line] = [symbol]
                else:
                    self.lines[self.curr_line].append(symbol)
                self.curr_line += 1
                if self.header_lines.get(self.curr_header_line) is None:
                    self.header_lines[self.curr_header_line] = [symbol]
                else:
                    self.header_lines[self.curr_header_line].append(symbol)
                self.curr_header_line += 1
            elif type(symbol.symbol) is symdump.symbols.FunctionSymbol or (symbol.symbol.cls_name != "Typedef" and ('func_return', '({})') not in symbol.symbol.type_modifiers):
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
        self.symbols.append(symbol)

    
    def set_line(self, line_num):
        self.curr_line = line_num

    def write_lines(self):
        source_obj_name = self.basename[:-1].lower() + 'o'
        curr_obj_file = self.basename[:-1].lower() + 'o'
        if self.lines_written:
            return
        if len(self.lines.keys()) >= 1:
            for i, _ in self.lines.items():
                if self.lines.get(i) is not None:
                    for entry in self.lines[i]:
                        if entry.symbol.is_fake:
                            pass
                        elif type(entry.symbol) is symdump.symbols.DefinitionSymbol and entry.symbol.cls_name == "Filename":
                            curr_obj_file = entry.symbol.name
                        elif curr_obj_file != source_obj_name:
                            pass
                        else:
                            self.text_lines.append(str(entry.symbol) + '\n' if entry.symbol is not None else '')
                else:
                    pass
        source_obj_name = self.basename[:-1].lower() + 'o'
        curr_obj_file = self.basename[:-1].lower() + 'o'
        if len(self.header_lines.keys()) >= 1:
            for i, _ in self.header_lines.items():
                if self.header_lines.get(i) is not None:
                    for entry in self.header_lines[i]:
                        if entry.symbol.is_fake:
                            pass
                        elif type(entry.symbol) is symdump.symbols.DefinitionSymbol and entry.symbol.cls_name == "Filename":
                            curr_obj_file = entry.symbol.name
                        elif curr_obj_file != source_obj_name:
                            pass
                        elif entry.symbol.cls_name == 'Typedef' and not entry.symbol.is_function:
                            self.header_text_lines.append("typedef " + str(entry.symbol) + '\n' if entry.symbol is not None else '')
                        else:
                            self.header_text_lines.append(str(entry.symbol) + '\n' if entry.symbol is not None else '')
                                
                else:
                    pass
        self.lines_written = True

    def write_file(self):
        if self.lines_written:
            self.write_out()
            return
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
        self.lines_written = True
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


            

