import networkx as nx
import symdump

class SympdumpSorter():
    def __init__(self) -> None:
        self.graph = nx.DiGraph()
        
        sortable_definitions = [x for x in symdump.SymFile().type_definitions.values() if type(x) is not symdump.symbols.ArraySymbol and not x.is_fake]
        for definition in sortable_definitions:
            self.graph.add_node(definition)
            if definition.children is not None:
                for child in definition.children:
                    if type(child.symbol) is symdump.symbols.ArraySymbol:
                        if child.symbol.tag is not None \
                            and symdump.SymFile().type_definitions.get(child.symbol.tag) is not None \
                            and not child.symbol.is_fake \
                            and child.symbol.tag != type_def.name \
                            and ('pointer', '*{}') not in child.symbol.type_modifiers:
                            self.graph.add_edge(symdump.SymFile().type_definitions[child.symbol.tag], definition)

        self.sorted_graph = nx.topological_sort(self.graph)
