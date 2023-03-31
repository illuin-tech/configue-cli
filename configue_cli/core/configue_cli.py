import logging
import logging.config
from pathlib import Path
from typing import Callable, List, Optional, Tuple, Type, TypeVar, Union

from .dict_config import DictConfig, ListMergeMode
from .dumper import ConfigueDumper
from .loader import load_from_config, load_from_path
from .render import render

CLI_DESCRIPTION = """\
configue-cli: a configue extension that adds the ability to dynamically configure your application via the command line.
"""
PARAMETERS_DOCSTRING = """\
Parameters key-value pairs in dotted notation: module.param1=value1 module.submodule.param2=value2
"""
CONFIG_PATHS_DOCSTRING = (
    "Path to a YAML file containing a configuration; multiple configurations can be specified with "
    "additional -c/--config flags, they will be merged in the order they are provided."
)
OUTPUT_DOCSTRING = "Path to an output YAML file used to save the final configuration."
DRY_RUN_DOCSTRING = "Print the final configuration but do not run the command."
PRETTY_PRINT_DOCTRING = "Enable/disable pretty printing."
TREE_DEPTH_DOCSTRING = "Only print the first levels of the configuration tree."

CLI_DOCSTRING = f"""\
{CLI_DESCRIPTION}

Args:
    parameters: {PARAMETERS_DOCSTRING}
    config_paths: {CONFIG_PATHS_DOCSTRING}
    output: {OUTPUT_DOCSTRING}
    dry_run: {DRY_RUN_DOCSTRING}
    pretty_print: {PRETTY_PRINT_DOCTRING}
    tree_depth: {TREE_DEPTH_DOCSTRING}
"""

InjectedT = TypeVar("InjectedT")
ReturnedT = TypeVar("ReturnedT")


def inject_from_cli(  # pylint: disable=too-many-locals
    *,
    inner_function: Callable[[Union[InjectedT, DictConfig]], ReturnedT],
    parameters: Optional[Tuple[str, ...]] = None,
    config_paths: Optional[List[str]] = None,
    output: Optional[Path] = None,
    dry_run: bool = False,
    pretty_print: bool = True,
    target_type: Optional[Type[InjectedT]] = None,
    tree_depth: Optional[int] = None,
    logging_config_path: Optional[str] = None,
    yaml_merge_mode: ListMergeMode = ListMergeMode.EXTEND,
    cli_merge_mode: ListMergeMode = ListMergeMode.REPLACE,
) -> Optional[ReturnedT]:
    base_config = DictConfig({})

    # Step 1: Load configurations from YAML files
    yaml_configs = []
    _config_paths = config_paths or []
    for config_path in _config_paths:
        yaml_configs.append(load_from_path(config_path, instantiate=False))
    base_config.merge(*yaml_configs, mode=yaml_merge_mode)

    # Step 2: Append a configuration generated from command line arguments (if any)
    cli_configs = []
    _parameters = parameters or tuple[str]()
    if len(_parameters) > 0:
        cli_configs.append(DictConfig.from_dotlist(_parameters))
    base_config.merge(*cli_configs, mode=cli_merge_mode)

    # Step 3: Deduce remaining arguments by recursively traversing the dataclasses
    # We skip this step if the arguments are injected in an unstructured config
    if target_type is None:
        config = base_config
    else:
        config = DictConfig.from_type(target_type, initial_config=base_config)  # type: ignore[arg-type]
        config.pop("()")
        config.merge(base_config, mode=ListMergeMode.REPLACE)

    # Step 4: Load the logging configuration (if any)
    if logging_config_path is None:
        logging_config = DictConfig({})
    elif logging_config_path in config:
        logging_config = DictConfig(config.pop(logging_config_path))
        logging.captureWarnings(True)
        logging.config.dictConfig(load_from_config(logging_config, instantiate=True))
        logging_config = DictConfig({logging_config_path: logging_config})
    else:
        logging.warning(f"`{logging_config_path}` was not found in the config, skip logging configuration")
        logging_config = DictConfig({})

    if dry_run:
        config.merge(logging_config, mode=ListMergeMode.REPLACE)
        render(
            config,
            title="Configuration helper",
            throw_on_missing_value=False,
            pretty_print=pretty_print,
            depth=tree_depth,
        )
        return None

    # Step 5: Create the final object
    injected_object: Union[InjectedT, DictConfig] = (
        target_type(**load_from_config(config, instantiate=True))
        if target_type is not None
        else DictConfig(**load_from_config(config, instantiate=True))
    )
    config.merge(logging_config, mode=ListMergeMode.REPLACE)

    if output:
        with open(output, "w", encoding="utf-8") as writer:
            writer.write(ConfigueDumper.from_config(config))

    render(
        config,
        title="Configuration",
        throw_on_missing_value=True,
        pretty_print=pretty_print,
        depth=tree_depth,
    )

    return inner_function(injected_object)
