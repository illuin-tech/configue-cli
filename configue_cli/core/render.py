import itertools
from numbers import Number
from typing import Any, Dict, List, Optional

from rich import box
from rich.console import Console, Group, NewLine
from rich.panel import Panel
from rich.style import Style
from rich.text import Text
from rich.tree import Tree

from .dict_config import DictConfig
from .exceptions import MissingMandatoryValueError
from .missing import MISSING, MissingType

DEFAULT_STYLE = Style(color="green")
CONSTRUCTOR_STYLE = Style(color="blue", bold=True)
MISSING_VALUE_STYLE = Style(color="red", italic=True)
NONE_VALUE_STYLE = Style(color="cyan")
BOOL_VALUE_STYLE = Style(color="cyan")
NUMBER_VALUE_STYLE = Style(color="magenta")
STRING_VALUE_STYLE = Style(color="yellow")


def value2style(value: Any) -> Style:
    if value is None:
        return NONE_VALUE_STYLE
    if isinstance(value, bool):
        return BOOL_VALUE_STYLE
    if isinstance(value, Number):
        return NUMBER_VALUE_STYLE
    if isinstance(value, str):
        return STRING_VALUE_STYLE
    return DEFAULT_STYLE


class Parser:
    def __init__(self, throw_on_missing_value: bool = True) -> None:
        self.throw_on_missing_value = throw_on_missing_value

    def _parse_list(self, obj: List, depth: Optional[int] = None, prefix_key: str = "") -> List[Tree]:
        trees: List[Tree] = []
        for index, item in enumerate(obj):
            tree = Tree("", hide_root=True)
            dotted_key_name = str(index) if prefix_key == "" else f"{prefix_key}.{index}"
            for sub_tree in self._parse(
                item,
                depth=None if depth is None else depth - 1,
                prefix_key=dotted_key_name,
            ):
                tree.add(sub_tree)
            trees.append(tree)
        return trees

    def _parse_dict(self, obj: Dict, depth: Optional[int] = None, prefix_key: str = "") -> List[Tree]:
        trees: List[Tree] = []
        for key, value in obj.items():
            dotted_key_name = str(key) if prefix_key == "" else f"{prefix_key}.{str(key)}"
            if isinstance(value, MissingType):
                if self.throw_on_missing_value:
                    raise MissingMandatoryValueError(f"Missing mandatory value: {dotted_key_name}")
                tree = Tree(Text(str(key) + ": ") + Text(str(MISSING), style=MISSING_VALUE_STYLE))
            elif key == "()":
                tree = Tree(Text(f"(): {value}", style=CONSTRUCTOR_STYLE))
            elif isinstance(value, dict):
                sub_tree = Tree(Text(str(key), style=Style(bold=True)))
                for sub_sub_tree in self._parse(
                    value,
                    depth=None if depth is None else depth - 1,
                    prefix_key=dotted_key_name,
                ):
                    sub_tree.add(sub_sub_tree)
                tree = sub_tree
            elif isinstance(value, list):
                sub_tree = Tree(Text(str(key), style=Style(bold=True)))
                for sub_sub_tree in self._parse(
                    value,
                    depth=None if depth is None else depth - 1,
                    prefix_key=dotted_key_name,
                ):
                    sub_tree.add(sub_sub_tree)
                tree = sub_tree

            else:
                tree = Tree(Text(str(key) + ": ") + Text(repr(value), style=value2style(value)))
            trees.append(tree)
        return trees

    def _parse(self, obj: Any, depth: Optional[int] = None, prefix_key: str = "") -> List[Tree]:
        if depth == 0:
            return []
        if isinstance(obj, list):
            return self._parse_list(obj, depth, prefix_key)
        if isinstance(obj, dict):
            return self._parse_dict(obj, depth, prefix_key)
        return [Tree(Text(repr(obj), style=value2style(obj)))]

    def parse(self, config: DictConfig, depth: Optional[int] = None) -> List[Tree]:
        return self._parse(config, depth)


def render(
    config: DictConfig,
    title: str,
    throw_on_missing_value: bool = True,
    pretty_print: bool = True,
    depth: Optional[int] = None,
) -> None:
    if not pretty_print:
        for tree in Parser(throw_on_missing_value).parse(config, depth):
            Console().print(tree)
        return

    panel = Panel(
        Group(
            *itertools.chain.from_iterable(  # type: ignore[arg-type]
                zip(
                    Parser(throw_on_missing_value).parse(config, depth),
                    itertools.repeat(NewLine()),
                )
            )
        ),
        border_style="dim",
        title=title,
        title_align="left",
        box=box.ROUNDED,
        padding=(1, 2, 0, 2),
    )
    Console().print(panel, new_line_start=True)
