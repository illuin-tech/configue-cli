from pathlib import Path
from typing import Callable, List, Literal, Optional, Type, TypeVar, Union, overload

from .core import configue_cli
from .core.dict_config import DictConfig, ListMergeMode

__all__ = ["inject_from_cli"]

InjectedT = TypeVar("InjectedT")
ReturnedT = TypeVar("ReturnedT")


@overload
def inject_from_cli(
    target_type: Type[InjectedT],
    *,
    logging_config_path: Optional[str] = None,
    yaml_merge_mode: ListMergeMode = ListMergeMode.EXTEND,
    cli_merge_mode: ListMergeMode = ListMergeMode.REPLACE,
) -> Callable[[Callable[[InjectedT], ReturnedT]], Callable[..., Optional[ReturnedT]]]:
    ...


@overload
def inject_from_cli(
    target_type: Literal[None] = None,
    *,
    logging_config_path: Optional[str] = None,
    yaml_merge_mode: ListMergeMode = ListMergeMode.EXTEND,
    cli_merge_mode: ListMergeMode = ListMergeMode.REPLACE,
) -> Callable[[Callable[[DictConfig], ReturnedT]], Callable[..., Optional[ReturnedT]]]:
    ...


def inject_from_cli(
    target_type: Optional[Type[InjectedT]] = None,
    *,
    logging_config_path: Optional[str] = None,
    yaml_merge_mode: ListMergeMode = ListMergeMode.EXTEND,
    cli_merge_mode: ListMergeMode = ListMergeMode.REPLACE,
) -> Callable[[Callable[[Union[InjectedT, DictConfig]], ReturnedT]], Callable[..., Optional[ReturnedT]]]:
    def cli(inner_function: Callable[[Union[InjectedT, DictConfig]], ReturnedT]) -> Callable[..., Optional[ReturnedT]]:
        def wrapped(
            *parameters: str,
            config_paths: Optional[List[str]] = None,
            output: Optional[Path] = None,
            dry_run: bool = False,
            tree_depth: Optional[int] = None,
            pretty_print: bool = True,
        ) -> Optional[ReturnedT]:
            return configue_cli.inject_from_cli(
                parameters=parameters,
                inner_function=inner_function,
                config_paths=config_paths,
                output=output,
                dry_run=dry_run,
                pretty_print=pretty_print,
                target_type=target_type,
                tree_depth=tree_depth,
                logging_config_path=logging_config_path,
                yaml_merge_mode=yaml_merge_mode,
                cli_merge_mode=cli_merge_mode,
            )

        wrapped.__doc__ = configue_cli.CLI_DOCSTRING
        wrapped.__name__ = inner_function.__name__
        return wrapped

    return cli
