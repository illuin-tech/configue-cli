# Configue CLI

A [configue](https://github.com/illuin-tech/configue) extension that adds the ability to dynamically configure your application via the command line.

Configue CLI overlaps in functionality with [Hydra](https://hydra.cc/) but without all the unnecessary boilerplate and with the benefit of being compatible with `configue`.

### Table of contents

- [Installation](#installation)
- [Quick start](#quick-start)
  - [Integration in a click CLI](#integration-in-a-click-cli)
  - [Integration in a Fire CLI](#integration-in-a-fire-cli)
- [Inspection of the configuration state](#inspection-of-the-configuration-state)
- [Configuration from the command line](#configuration-from-the-command-line)
- [Configuration with YAML files](#configuration-with-yaml-files)
- [Exporting the final configuration](#exporting-the-final-configuration)
- [Configuring the logging](#configuring-the-logging)
- [Unstructured configuration](#unstructured-configuration)

## Installation

To install the library from ILLUIN's Nexus, use

```shell
pip install configue-cli
```

To develop locally, clone the repository and use

```shell
pip install -r requirements-dev.txt
```

## Quick start

With `configue-cli`, configurations are defined with structured and arbitrarily nested Python objects (both native dataclasses and `attr` dataclasses are supported and can be nested).

```python
import dataclasses
import attrs


@dataclasses.dataclass
class DatasetConfig:
    name: str
    n_samples: int = 10_000


@dataclasses.dataclass
class OptimizerConfig:
    learning_rate: float = 0.001
    weight_decay: float = 1e-2


@attrs.define
class ModelConfig:
    name: str
    batch_size: int = 12
    optimizer: OptimizerConfig = attrs.Factory(
        lambda self: OptimizerConfig(learning_rate=0.001 * self.batch_size), takes_self=True
    )


@dataclasses.dataclass
class ExperimentConfig:
    model: ModelConfig
    dataset: DatasetConfig
```

These objects are injected at configuration time in your application entrypoint by the `inject_from_cli` decorator. `configue-cli` is compatible with `click` and `fire` CLI applications.

### Integration in a click CLI

To use `configue-cli` in a [click](https://github.com/pallets/click) command line application, simply wrap the entrypoint with the `configue_cli.click.inject_from_cli` decorator and provide a target type to be injected.

```python
import click
from configue_cli.click import inject_from_cli

@click.command()
@inject_from_cli(ExperimentConfig)
def main(config: ExperimentConfig) -> None:
    print("Passed configuration: ", config)


if __name__ == "__main__":
    main()
```

To display a help message, use the following:

```shell
python main.py --help
```

### Integration in a Fire CLI

Alternatively, `configue-cli` can be integrated in a [Fire](https://github.com/google/python-fire) CLI:

```python
import fire
from configue_cli.fire import inject_from_cli

@inject_from_cli(ExperimentConfig)
def main(config: ExperimentConfig) -> None:
    print("Passed configuration: ", config)


if __name__ == "__main__":
    fire.Fire(main)
```

To display a help message, use the following:

```shell
python main.py -h
```

## Inspection of the configuration state

To visually inspect your application configuration state, use the following command:

```shell
$ python main.py --dry-run

╭─ Configuration helper ────────────────────────────────╮
│                                                       │
│  model                                                │
│  ├── (): __main__.ModelConfig                         │
│  ├── name: Missing                                    │
│  ├── batch_size: 12                                   │
│  └── optimizer                                        │
│      ├── (): __main__.OptimizerConfig                 │
│      ├── learning_rate: 0.012                         │
│      └── weight_decay: 0.01                           │
│                                                       │
│  dataset                                              │
│  ├── (): __main__.DatasetConfig                       │
│  ├── name: Missing                                    │
│  └── n_samples: 10000                                 │
│                                                       │
╰───────────────────────────────────────────────────────╯
```

This is useful to quickly identify which parameters are not yet defined (those marked with a `Missing`) and which values are used in the other parameters without inspecting the code.

## Configuration from the command line

Parameters can be specified from the command line using dotted notation.

```shell
$ python main.py model.name=camembert-base dataset.name=fquad model.batch_size=48

╭─ Configuration ───────────────────────────────────────────────────────────────────────────╮
│                                                                                           │
│  model                                                                                    │
│  ├── (): __main__.ModelConfig                                                             │
│  ├── name: camembert-base                                                                 │
│  ├── batch_size: 48                                                                       │
│  └── optimizer                                                                            │
│      ├── (): __main__.OptimizerConfig                                                     │
│      ├── learning_rate: 0.048                                                             │
│      └── weight_decay: 0.01                                                               │
│                                                                                           │
│  dataset                                                                                  │
│  ├── (): __main__.DatasetConfig                                                           │
│  ├── name: fquad                                                                          │
│  └── n_samples: 10000                                                                     │
│                                                                                           │
╰───────────────────────────────────────────────────────────────────────────────────────────╯
Passed configuration: ExperimentConfig(model=ModelConfig(name='camembert-base', batch_size=48, optimizer=OptimizerConfig(learning_rate=0.048, weight_decay=0.01)), dataset=DatasetConfig(name='fquad', n_samples=10000))
```

Any missing required parameter at configuration time will result in an exception:

```shell
$ python main.py model.batch_size=3

Traceback (most recent call last):
  ...
configue_cli.core.exceptions.MissingMandatoryValue: Missing mandatory value: dataset.name
```

## Configuration with YAML files

Any parameter can be overridden using a `configue` compliant YAML file. Suppose the model is configured in the following `model.yml` file:

```yaml
model:
  (): __main__.ModelConfig
  name: camembert-large
  batch_size: 72
  optimizer:
    (): __main__.OptimizerConfig
    learning_rate: 0.01
    weight_decay: 0.0
```

This configuration file can be loaded from the CLI using the `-c` flag:

```shell
$ python main.py -c model.yml --dry-run

╭─ Configuration helper ────────────────────────────────────╮
│                                                           │
│  model                                                    │
│  ├── (): __main__.ModelConfig                             │
│  ├── name: camembert-large                                │
│  ├── batch_size: 72                                       │
│  └── optimizer                                            │
│      ├── (): __main__.OptimizerConfig                     │
│      ├── learning_rate: 0.01                              │
│      └── weight_decay: 0.0                                │
│                                                           │
│  dataset                                                  │
│  ├── (): __main__.DatasetConfig                           │
│  ├── name: Missing                                        │
│  └── n_samples: 10000                                     │
│                                                           │
╰───────────────────────────────────────────────────────────╯
```

Multiple configuration files can be used simultaneously, the final configuration is assembled by merging all files in the order they are provided. For instance, let's suppose we have the following `large_batch.yml` file:

```yaml
model:
  batch_size: 512
```

This file can be merged into our previous configuration using the following:

```shell
$ python main.py -c model.yml -c large_batch.yml --dry-run 

╭─ Configuration helper ────────────────────────────────────╮
│                                                           │
│  model                                                    │
│  ├── (): __main__.ModelConfig                             │
│  ├── name: camembert-large                                │
│  ├── batch_size: 512                                      │
│  └── optimizer                                            │
│      ├── (): __main__.OptimizerConfig                     │
│      ├── learning_rate: 0.01                              │
│      └── weight_decay: 0.0                                │
│                                                           │
│  dataset                                                  │
│  ├── (): __main__.DatasetConfig                           │
│  ├── name: Missing                                        │
│  └── n_samples: 10000                                     │
│                                                           │
╰───────────────────────────────────────────────────────────╯
```

> If you are using Fire, the same flag cannot be passed multiple times in the same command. To pass a list of multiple paths, it is therefore necessary to use:
>
> ```shell
> $ python main.py -c "[\"model.yml\", \"large_batch.yml\"]" --dry-run
> ```

Parameters specified with the command line take precedence over the ones specified in YAML files:

```shell
$ python main.py model.batch_size=32 -c model.yml -c large_batch.yml --dry-run

╭─ Configuration helper ────────────────────────────────────╮
│                                                           │
│  model                                                    │
│  ├── (): __main__.ModelConfig                             │
│  ├── name: camembert-large                                │
│  ├── batch_size: 32                                       │
│  └── optimizer                                            │
│      ├── (): __main__.OptimizerConfig                     │
│      ├── learning_rate: 0.01                              │
│      └── weight_decay: 0.0                                │
│                                                           │
│  dataset                                                  │
│  ├── (): __main__.DatasetConfig                           │
│  ├── name: Missing                                        │
│  └── n_samples: 10000                                     │
│                                                           │
╰───────────────────────────────────────────────────────────╯
```

This feature encourages a modular configuration pattern where different subparts of the application (the model and the dataset in this example) are configured in separate YAML files and are dynamically assembled at configuration time. Different variations of these subparts can easily be assembled. All arguments can be overridden using the command line without having to edit the config files.

## Exporting the final configuration

To ease reproducibility, the final configuration used for the run can be exported by using the `-o` flag and specifying an output YAML file:

```shell
$ python main.py dataset.name=hello-world -c model.yml -c large_batch.yml -o output.yml

╭─ Configuration ───────────────────────────────────────────╮
│                                                           │
│  model                                                    │
│  ├── (): __main__.ModelConfig                             │
│  ├── name: camembert-large                                │
│  ├── batch_size: 512                                      │
│  └── optimizer                                            │
│      ├── (): __main__.OptimizerConfig                     │
│      ├── learning_rate: 0.01                              │
│      └── weight_decay: 0.0                                │
│                                                           │
│  dataset                                                  │
│  ├── (): __main__.DatasetConfig                           │
│  ├── name: hello-world                                    │
│  └── n_samples: 10000                                     │
│                                                           │
╰───────────────────────────────────────────────────────────╯
Passed configuration ExperimentConfig(model=ModelConfig(name='camembert-large', batch_size=512, optimizer=OptimizerConfig(learning_rate=0.01, weight_decay=0.0)), dataset=DatasetConfig(name='hello-world', n_samples=10000))

$ cat output.yml
model:
  (): __main__.ModelConfig
  name: camembert-large
  batch_size: 512
  optimizer:
    (): __main__.OptimizerConfig
    learning_rate: 0.01
    weight_decay: 0.0
dataset:
  (): __main__.DatasetConfig
  name: hello-world
  n_samples: 10000
```

## Configuring the logging

To load a [logging configuration](https://docs.python.org/3/library/logging.config.html) located under the `"logging"` key in your final configuration, use the following:

```python
@click.command()
@inject_from_cli(ExperimentConfig, logging_config_path="logging")
def main(config: ExperimentConfig) -> None:
    ...
```

## Unstructured configuration

It is possible to use the `inject_from_cli` decorator without specifying a target type:

```python
@click.command()
@inject_from_cli()
def main(config: configue_cli.core.dict_config.DictConfig) -> None:
    ...
```

In that case, the wrapped entrypoint will be passed a `configue_cli.core.dict_config.DictConfig` object upon injection.
