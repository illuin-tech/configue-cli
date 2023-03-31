from pathlib import Path
from typing import Callable, List, Literal, Optional, Tuple, Type, TypeVar, Union, overload

try:  # pragma: no cover
    import click
except ImportError as exc:  # pragma: no cover
    raise ImportError("click is not installed, use `pip install click`") from exc

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
    ...  # pragma: no cover


@overload
def inject_from_cli(
    target_type: Literal[None] = None,
    *,
    logging_config_path: Optional[str] = None,
    yaml_merge_mode: ListMergeMode = ListMergeMode.EXTEND,
    cli_merge_mode: ListMergeMode = ListMergeMode.REPLACE,
) -> Callable[[Callable[[DictConfig], ReturnedT]], Callable[..., Optional[ReturnedT]]]:
    ...  # pragma: no cover


def inject_from_cli(
    target_type: Optional[Type[InjectedT]] = None,
    *,
    logging_config_path: Optional[str] = None,
    yaml_merge_mode: ListMergeMode = ListMergeMode.EXTEND,
    cli_merge_mode: ListMergeMode = ListMergeMode.REPLACE,
) -> Callable[[Callable[[Union[InjectedT, DictConfig]], ReturnedT]], Callable[..., Optional[ReturnedT]]]:
    def cli(inner_function: Callable[[Union[InjectedT, DictConfig]], ReturnedT]) -> Callable[..., Optional[ReturnedT]]:
        @click.argument("parameters", nargs=-1, type=str, required=False)
        @click.option(
            "-c",
            "--config",
            "config_paths",
            default=[],
            multiple=True,
            type=click.Path(exists=True),
            help=configue_cli.CONFIG_PATHS_DOCSTRING,
        )
        @click.option(
            "-d",
            "--dry-run",
            "dry_run",
            default=False,
            is_flag=True,
            help=configue_cli.DRY_RUN_DOCSTRING,
        )
        @click.option(
            "--pretty/--no-pretty",
            "pretty_print",
            default=True,
            help=configue_cli.PRETTY_PRINT_DOCTRING,
        )
        @click.option(
            "-L",
            "--level",
            "tree_depth",
            default=None,
            type=int,
            help=configue_cli.TREE_DEPTH_DOCSTRING,
        )
        @click.option(
            "-o",
            "--output",
            "output",
            default=None,
            type=click.Path(writable=True),
            help=configue_cli.OUTPUT_DOCSTRING,
        )
        def wrapped(
            parameters: Tuple[str],
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

        # click auto-documents the arguments so we only pass the CLI description
        wrapped.__doc__ = configue_cli.CLI_DESCRIPTION
        wrapped.__name__ = inner_function.__name__
        return wrapped

    return cli
