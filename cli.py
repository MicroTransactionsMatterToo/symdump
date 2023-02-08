import cmd
from unicodedata import name
import symdump
import os
import ntpath

from pygments import highlight
from pygments.lexers import get_lexer_for_filename
from pygments.lexers.c_cpp import CFamilyLexer
from pygments.formatters import Terminal256Formatter

from symdump.symbols import DefinitionSymbol


class SymDumpShell(cmd.Cmd):
    def __init__(self, symfile: str | None = None) -> None:
        self.symfile = None
        self.symobj = None
        if symfile is not None:
            self.symfile = open(symfile, "rb")
            self.symobj = symdump.SymFile(self.symfile)
            self.symobj.map_types()
            self.symobj.create_files()
        super().__init__()

    def do_sourcefiles(self, arg):
        """Lists source file names"""
        self.columnize(
            list(self.symobj.source_files.keys()), os.get_terminal_size().columns
        )
        return None

    def do_functions(self, arg):
        """Lists function, filtered by provided string"""
        function_names = self.symobj.functions.keys()
        matches = [x for x in function_names if arg in x]
        self.columnize(matches, os.get_terminal_size().columns)

    def do_printsource(self, arg):
        """Prints the source of the specified source file"""
        file_names = self.symobj.source_files.keys()
        matches = [x for x in file_names if arg in x]
        if len(matches) > 1 and self.symobj.source_files.get(arg) is None:
            print("Multiple matching files found, they are:")
            self.columnize(matches, os.get_terminal_size().columns)
            return
        elif len(matches) == 0:
            print("No matching files found")
            return
        else:
            file_name = ntpath.basename(matches[0])
            print(
                highlight(
                    str(self.symobj.source_files[matches[0]]),
                    get_lexer_for_filename(file_name),
                    Terminal256Formatter(),
                )
            )
            return

    def do_printfunction(self, arg):
        """Prints the source of the specified function"""
        function_names = self.symobj.functions.keys()
        matches = [x for x in function_names if arg in x]
        if len(matches) > 1 and self.symobj.functions.get(arg) is None:
            print("Multiple matching functions found, they are:")
            self.columnize(matches, os.get_terminal_size().columns)
            return
        elif len(matches) == 0:
            print("No matching functions found")
            return
        elif self.symobj.functions.get(arg) is not None:
            print(
                highlight(
                    str(self.symobj.functions[arg]),
                    CFamilyLexer(),
                    Terminal256Formatter(),
                )
            )
        else:
            print(
                highlight(
                    str(self.symobj.functions[matches[0]]),
                    CFamilyLexer(),
                    Terminal256Formatter(),
                )
            )
            return

    def do_printsymbol(self, arg):
        """Prints the source code for a given symbol name"""
        symbols = []
        name_list = []
        for symbol in self.symobj.symbols:
            if symbol.name in name_list or symbol.name is None:
                next
            else:
                symbols.append(symbol)
                name_list.append(symbol.name)
        matches = [(x, x.name) for x in symbols if arg in x.name]
        if len(matches) > 1 and [x for x in matches if x[1] == arg] == []:
            print("Multiple matching symbols found, they are:")
            self.columnize([x[1] for x in matches], os.get_terminal_size().columns)
            return
        elif len(matches) == 0:
            print("No matching symbols found")
            return
        elif [x for x in matches if x[1] == arg] != []:
            match = [x for x in matches if x[1] == arg][0]
            print(highlight(str(match[0]), CFamilyLexer(), Terminal256Formatter()))
        else:
            print(highlight(str(matches[0][0]), CFamilyLexer(), Terminal256Formatter()))
            return
