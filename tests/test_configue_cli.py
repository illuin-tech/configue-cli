# mypy: disable-error-code=no-untyped-def
import dataclasses
import logging
import tempfile
import textwrap
from logging import Handler, LogRecord
from typing import List, Type
from unittest import TestCase

import attrs
import click
from click.testing import CliRunner

from configue_cli.click import inject_from_cli
from configue_cli.core.dict_config import DictConfig
from configue_cli.core.exceptions import MissingMandatoryValue


class CustomType:
    def __init__(self, arg: int = 1) -> None:
        self._arg = arg

    def __repr__(self) -> str:
        return f"CustomType(args={self._arg})"


class CustomHandler(Handler):
    def __init__(self, arg):
        Handler.__init__(self)
        self.arg = arg

    def emit(self, record: LogRecord) -> None:
        pass


@attrs.define
class AttrsSubConfig:
    param_1: int
    param_2: int = 3
    param_3: int = attrs.Factory(lambda: 4)
    param_4: int = attrs.Factory(lambda self: self.param_3 + 2, takes_self=True)  # type: ignore[call-overload]
    param_5: List[str] = attrs.field(factory=lambda: ["hello", "world"])
    param_6: CustomType = attrs.Factory(CustomType)
    non_init: int = attrs.field(init=False)


@dataclasses.dataclass
class DataclassSubConfig:
    custom_type: Type[CustomType]
    custom_object: CustomType
    param_1: int
    param_2: int = 1
    param_3: int = dataclasses.field(default_factory=lambda: 2)
    param_4: List[str] = dataclasses.field(default_factory=lambda: ["hello", "world"])
    param_5: CustomType = dataclasses.field(default_factory=CustomType)
    non_init: int = dataclasses.field(init=False)


@dataclasses.dataclass
class DataclassConfig:
    dataclass_sub_config: DataclassSubConfig
    attrs_sub_config: AttrsSubConfig
    param_1: int
    param_2: int = 1
    param_3: int = dataclasses.field(default_factory=lambda: 2)


@attrs.define
class AttrsConfig:
    attrs_sub_config: AttrsSubConfig
    dataclass_sub_config: DataclassSubConfig
    param_1: int
    param_2: int = 3
    param_3: int = attrs.field(factory=lambda: 4)
    param_4: int = attrs.Factory(lambda self: self.param_3 + 2, takes_self=True)  # type: ignore[call-overload]


@attrs.define
class MainConfig:
    param_1: int
    dataclass_config_1: DataclassConfig
    attrs_config_1: AttrsConfig
    dataclass_config_2: DataclassConfig = attrs.Factory(
        lambda self: DataclassConfig(
            param_1=self.param_1,
            dataclass_sub_config=self.dataclass_config_1,
            attrs_sub_config=self.attrs_config_1,
        ),
        takes_self=True,
    )
    attrs_config_2: AttrsConfig = attrs.Factory(
        lambda self: AttrsConfig(
            param_1=self.param_1,
            dataclass_sub_config=self.dataclass_config_1,
            attrs_sub_config=self.attrs_config_1,
        ),
        takes_self=True,
    )


class TestConfigueCLI(TestCase):
    def test_fail_when_missing_required_parameter(self) -> None:
        @click.command()
        @inject_from_cli(MainConfig)
        def main(config) -> None:
            self.assertIsInstance(config, MainConfig)

        runner = CliRunner()
        result = runner.invoke(main, [])
        self.assertEqual(result.exit_code, 1)
        self.assertIsInstance(result.exception, MissingMandatoryValue)
        self.assertEqual(result.exception.args[0], "Missing mandatory value: param_1")  # type: ignore[union-attr]

    def test_dry_run_unstructured(self) -> None:
        @click.command(no_args_is_help=True)
        @inject_from_cli()
        def main(config) -> None:
            self.assertIsInstance(config, DictConfig)

        runner = CliRunner()
        result = runner.invoke(main, ["--dry-run", "--no-pretty"])
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.stdout, "")

    def test_dry_run_attrs(self) -> None:
        @click.command()
        @inject_from_cli(AttrsConfig)
        def main(config) -> None:
            self.assertIsInstance(config, AttrsConfig)

        runner = CliRunner()
        result = runner.invoke(main, ["--dry-run", "--no-pretty"])
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(
            result.stdout,
            textwrap.dedent(
                """\
                attrs_sub_config
                ├── (): tests.test_configue_cli.AttrsSubConfig
                ├── param_1: Missing
                ├── param_2: 3
                ├── param_3: 4
                ├── param_4: 6
                ├── param_5
                │   ├── 'hello'
                │   └── 'world'
                └── param_6: CustomType(args=1)
                dataclass_sub_config
                ├── (): tests.test_configue_cli.DataclassSubConfig
                ├── custom_type: Missing
                ├── custom_object: Missing
                ├── param_1: Missing
                ├── param_2: 1
                ├── param_3: 2
                ├── param_4
                │   ├── 'hello'
                │   └── 'world'
                └── param_5: CustomType(args=1)
                param_1: Missing
                param_2: 3
                param_3: 4
                param_4: 6
                """
            ),
        )

    def test_dry_run_dataclass(self) -> None:
        @click.command()
        @inject_from_cli(DataclassConfig)
        def main(config) -> None:
            self.assertIsInstance(config, DataclassConfig)

        runner = CliRunner()
        result = runner.invoke(main, ["--dry-run", "--no-pretty"])
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(
            result.stdout,
            textwrap.dedent(
                """\
                dataclass_sub_config
                ├── (): tests.test_configue_cli.DataclassSubConfig
                ├── custom_type: Missing
                ├── custom_object: Missing
                ├── param_1: Missing
                ├── param_2: 1
                ├── param_3: 2
                ├── param_4
                │   ├── 'hello'
                │   └── 'world'
                └── param_5: CustomType(args=1)
                attrs_sub_config
                ├── (): tests.test_configue_cli.AttrsSubConfig
                ├── param_1: Missing
                ├── param_2: 3
                ├── param_3: 4
                ├── param_4: 6
                ├── param_5
                │   ├── 'hello'
                │   └── 'world'
                └── param_6: CustomType(args=1)
                param_1: Missing
                param_2: 1
                param_3: 2
                """
            ),
        )

    def test_dry_run_factory_takes_self_correctly_updates(self):
        @click.command()
        @inject_from_cli(AttrsSubConfig)
        def main(config) -> None:
            self.assertIsInstance(config, AttrsSubConfig)

        runner = CliRunner()
        result = runner.invoke(main, ["--dry-run", "--no-pretty", "param_3=10"])
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(
            result.stdout,
            textwrap.dedent(
                """\
                param_1: Missing
                param_2: 3
                param_3: 10
                param_4: 12
                param_5
                ├── 'hello'
                └── 'world'
                param_6: CustomType(args=1)
                """
            ),
        )

    def test_dry_run_deeply_nested_config(self):
        @click.command()
        @inject_from_cli(MainConfig)
        def main(config) -> None:
            self.assertIsInstance(config, MainConfig)

        runner = CliRunner()
        result = runner.invoke(main, ["--dry-run", "--no-pretty"])
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(
            result.stdout,
            textwrap.dedent(
                """\
                param_1: Missing
                dataclass_config_1
                ├── (): tests.test_configue_cli.DataclassConfig
                ├── dataclass_sub_config
                │   ├── (): tests.test_configue_cli.DataclassSubConfig
                │   ├── custom_type: Missing
                │   ├── custom_object: Missing
                │   ├── param_1: Missing
                │   ├── param_2: 1
                │   ├── param_3: 2
                │   ├── param_4
                │   │   ├── 'hello'
                │   │   └── 'world'
                │   └── param_5: CustomType(args=1)
                ├── attrs_sub_config
                │   ├── (): tests.test_configue_cli.AttrsSubConfig
                │   ├── param_1: Missing
                │   ├── param_2: 3
                │   ├── param_3: 4
                │   ├── param_4: 6
                │   ├── param_5
                │   │   ├── 'hello'
                │   │   └── 'world'
                │   └── param_6: CustomType(args=1)
                ├── param_1: Missing
                ├── param_2: 1
                └── param_3: 2
                attrs_config_1
                ├── (): tests.test_configue_cli.AttrsConfig
                ├── attrs_sub_config
                │   ├── (): tests.test_configue_cli.AttrsSubConfig
                │   ├── param_1: Missing
                │   ├── param_2: 3
                │   ├── param_3: 4
                │   ├── param_4: 6
                │   ├── param_5
                │   │   ├── 'hello'
                │   │   └── 'world'
                │   └── param_6: CustomType(args=1)
                ├── dataclass_sub_config
                │   ├── (): tests.test_configue_cli.DataclassSubConfig
                │   ├── custom_type: Missing
                │   ├── custom_object: Missing
                │   ├── param_1: Missing
                │   ├── param_2: 1
                │   ├── param_3: 2
                │   ├── param_4
                │   │   ├── 'hello'
                │   │   └── 'world'
                │   └── param_5: CustomType(args=1)
                ├── param_1: Missing
                ├── param_2: 3
                ├── param_3: 4
                └── param_4: 6
                dataclass_config_2
                ├── (): tests.test_configue_cli.DataclassConfig
                ├── dataclass_sub_config
                │   ├── (): tests.test_configue_cli.DataclassConfig
                │   ├── dataclass_sub_config
                │   │   ├── (): tests.test_configue_cli.DataclassSubConfig
                │   │   ├── custom_type: Missing
                │   │   ├── custom_object: Missing
                │   │   ├── param_1: Missing
                │   │   ├── param_2: 1
                │   │   ├── param_3: 2
                │   │   ├── param_4
                │   │   │   ├── 'hello'
                │   │   │   └── 'world'
                │   │   └── param_5: CustomType(args=1)
                │   ├── attrs_sub_config
                │   │   ├── (): tests.test_configue_cli.AttrsSubConfig
                │   │   ├── param_1: Missing
                │   │   ├── param_2: 3
                │   │   ├── param_3: 4
                │   │   ├── param_4: 6
                │   │   ├── param_5
                │   │   │   ├── 'hello'
                │   │   │   └── 'world'
                │   │   └── param_6: CustomType(args=1)
                │   ├── param_1: Missing
                │   ├── param_2: 1
                │   └── param_3: 2
                ├── attrs_sub_config
                │   ├── (): tests.test_configue_cli.AttrsConfig
                │   ├── attrs_sub_config
                │   │   ├── (): tests.test_configue_cli.AttrsSubConfig
                │   │   ├── param_1: Missing
                │   │   ├── param_2: 3
                │   │   ├── param_3: 4
                │   │   ├── param_4: 6
                │   │   ├── param_5
                │   │   │   ├── 'hello'
                │   │   │   └── 'world'
                │   │   └── param_6: CustomType(args=1)
                │   ├── dataclass_sub_config
                │   │   ├── (): tests.test_configue_cli.DataclassSubConfig
                │   │   ├── custom_type: Missing
                │   │   ├── custom_object: Missing
                │   │   ├── param_1: Missing
                │   │   ├── param_2: 1
                │   │   ├── param_3: 2
                │   │   ├── param_4
                │   │   │   ├── 'hello'
                │   │   │   └── 'world'
                │   │   └── param_5: CustomType(args=1)
                │   ├── param_1: Missing
                │   ├── param_2: 3
                │   ├── param_3: 4
                │   └── param_4: 6
                ├── param_1: Missing
                ├── param_2: 1
                └── param_3: 2
                attrs_config_2
                ├── (): tests.test_configue_cli.AttrsConfig
                ├── attrs_sub_config
                │   ├── (): tests.test_configue_cli.AttrsConfig
                │   ├── attrs_sub_config
                │   │   ├── (): tests.test_configue_cli.AttrsSubConfig
                │   │   ├── param_1: Missing
                │   │   ├── param_2: 3
                │   │   ├── param_3: 4
                │   │   ├── param_4: 6
                │   │   ├── param_5
                │   │   │   ├── 'hello'
                │   │   │   └── 'world'
                │   │   └── param_6: CustomType(args=1)
                │   ├── dataclass_sub_config
                │   │   ├── (): tests.test_configue_cli.DataclassSubConfig
                │   │   ├── custom_type: Missing
                │   │   ├── custom_object: Missing
                │   │   ├── param_1: Missing
                │   │   ├── param_2: 1
                │   │   ├── param_3: 2
                │   │   ├── param_4
                │   │   │   ├── 'hello'
                │   │   │   └── 'world'
                │   │   └── param_5: CustomType(args=1)
                │   ├── param_1: Missing
                │   ├── param_2: 3
                │   ├── param_3: 4
                │   └── param_4: 6
                ├── dataclass_sub_config
                │   ├── (): tests.test_configue_cli.DataclassConfig
                │   ├── dataclass_sub_config
                │   │   ├── (): tests.test_configue_cli.DataclassSubConfig
                │   │   ├── custom_type: Missing
                │   │   ├── custom_object: Missing
                │   │   ├── param_1: Missing
                │   │   ├── param_2: 1
                │   │   ├── param_3: 2
                │   │   ├── param_4
                │   │   │   ├── 'hello'
                │   │   │   └── 'world'
                │   │   └── param_5: CustomType(args=1)
                │   ├── attrs_sub_config
                │   │   ├── (): tests.test_configue_cli.AttrsSubConfig
                │   │   ├── param_1: Missing
                │   │   ├── param_2: 3
                │   │   ├── param_3: 4
                │   │   ├── param_4: 6
                │   │   ├── param_5
                │   │   │   ├── 'hello'
                │   │   │   └── 'world'
                │   │   └── param_6: CustomType(args=1)
                │   ├── param_1: Missing
                │   ├── param_2: 1
                │   └── param_3: 2
                ├── param_1: Missing
                ├── param_2: 3
                ├── param_3: 4
                └── param_4: 6
                """
            ),
        )

    def test_dry_run_unstructured_with_loaded_param_from_cli(self) -> None:
        @click.command(no_args_is_help=True)
        @inject_from_cli()
        def main(config) -> None:
            self.assertIsInstance(config, DictConfig)

        runner = CliRunner()
        result = runner.invoke(main, ["config_a.required_param=1", "--dry-run", "--no-pretty"])
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(
            result.stdout,
            textwrap.dedent(
                """\
                config_a
                └── required_param: 1
                """
            ),
        )

    def test_dry_run_with_loaded_param_from_cli(self) -> None:
        @click.command()
        @inject_from_cli(DataclassConfig)
        def main(config) -> None:
            self.assertIsInstance(config, DataclassConfig)

        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "dataclass_sub_config.param_1=1",
                "dataclass_sub_config.param_4=[hello, hello, world]",
                'dataclass_sub_config.custom_type="!ext tests.test_configue_cli.CustomType"',
                'dataclass_sub_config.custom_object="(): tests.test_configue_cli.CustomType"',
                "--dry-run",
                "--no-pretty",
            ],
        )
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(
            result.stdout,
            textwrap.dedent(
                """\
                dataclass_sub_config
                ├── (): tests.test_configue_cli.DataclassSubConfig
                ├── custom_type: <class 'tests.test_configue_cli.CustomType'>
                ├── custom_object
                │   └── (): tests.test_configue_cli.CustomType
                ├── param_1: 1
                ├── param_2: 1
                ├── param_3: 2
                ├── param_4
                │   ├── 'hello'
                │   ├── 'hello'
                │   └── 'world'
                └── param_5: CustomType(args=1)
                attrs_sub_config
                ├── (): tests.test_configue_cli.AttrsSubConfig
                ├── param_1: Missing
                ├── param_2: 3
                ├── param_3: 4
                ├── param_4: 6
                ├── param_5
                │   ├── 'hello'
                │   └── 'world'
                └── param_6: CustomType(args=1)
                param_1: Missing
                param_2: 1
                param_3: 2
                """
            ),
        )

    def test_dry_run_with_loaded_param_from_files(self) -> None:
        @click.command()
        @inject_from_cli(DataclassConfig)
        def main(config) -> None:
            self.assertIsInstance(config, DataclassConfig)

        runner = CliRunner()
        result = runner.invoke(main, ["-c", "tests/config_1.yml", "--dry-run", "--no-pretty"])
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(
            result.stdout,
            textwrap.dedent(
                """\
                dataclass_sub_config
                ├── (): tests.test_configue_cli.DataclassSubConfig
                ├── custom_type: <class 'tests.test_configue_cli.CustomType'>
                ├── custom_object
                │   └── (): tests.test_configue_cli.CustomType
                ├── param_1: 2
                ├── param_2: 1
                ├── param_3: 2
                ├── param_4
                │   ├── 'hello'
                │   └── 'world'
                └── param_5: CustomType(args=1)
                attrs_sub_config
                ├── (): tests.test_configue_cli.AttrsSubConfig
                ├── param_1: Missing
                ├── param_2: 3
                ├── param_3: 4
                ├── param_4: 6
                ├── param_5
                │   ├── 'hello'
                │   └── 'world'
                └── param_6: CustomType(args=1)
                param_1: 2
                param_2: 1
                param_3: 2
                """
            ),
        )

    def test_dry_run_with_loaded_param_from_files_and_cli(self) -> None:
        @click.command()
        @inject_from_cli(DataclassConfig)
        def main(config) -> None:
            self.assertIsInstance(config, DataclassConfig)

        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "-c",
                "tests/config_1.yml",
                "attrs_sub_config.param_1=1",
                "--dry-run",
                "--no-pretty",
            ],
        )
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(
            result.stdout,
            textwrap.dedent(
                """\
                dataclass_sub_config
                ├── (): tests.test_configue_cli.DataclassSubConfig
                ├── custom_type: <class 'tests.test_configue_cli.CustomType'>
                ├── custom_object
                │   └── (): tests.test_configue_cli.CustomType
                ├── param_1: 2
                ├── param_2: 1
                ├── param_3: 2
                ├── param_4
                │   ├── 'hello'
                │   └── 'world'
                └── param_5: CustomType(args=1)
                attrs_sub_config
                ├── (): tests.test_configue_cli.AttrsSubConfig
                ├── param_1: 1
                ├── param_2: 3
                ├── param_3: 4
                ├── param_4: 6
                ├── param_5
                │   ├── 'hello'
                │   └── 'world'
                └── param_6: CustomType(args=1)
                param_1: 2
                param_2: 1
                param_3: 2
                """
            ),
        )

    def test_load_required_from_cli(self) -> None:
        @click.command()
        @inject_from_cli(DataclassConfig)
        def main(config: DataclassConfig) -> None:
            self.assertIsInstance(config, DataclassConfig)
            self.assertIsInstance(config.dataclass_sub_config, DataclassSubConfig)
            self.assertIsInstance(config.attrs_sub_config, AttrsSubConfig)
            self.assertEqual(config.param_1, 1)
            self.assertEqual(config.param_2, 1)
            self.assertEqual(config.param_3, 2)
            self.assertEqual(config.dataclass_sub_config.custom_type, CustomType)
            self.assertIsInstance(config.dataclass_sub_config.custom_object, CustomType)
            self.assertEqual(config.dataclass_sub_config.param_1, 1)
            self.assertEqual(config.dataclass_sub_config.param_2, 1)
            self.assertEqual(config.dataclass_sub_config.param_3, 2)
            self.assertEqual(config.attrs_sub_config.param_1, 1)
            self.assertEqual(config.attrs_sub_config.param_2, 3)
            self.assertEqual(config.attrs_sub_config.param_3, 4)
            self.assertEqual(config.attrs_sub_config.param_4, 6)

        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "param_1=1",
                "dataclass_sub_config.param_1=1",
                "attrs_sub_config.param_1=1",
                'dataclass_sub_config.custom_type="!ext tests.test_configue_cli.CustomType"',
                'dataclass_sub_config.custom_object="(): tests.test_configue_cli.CustomType"',
            ],
        )
        self.assertEqual(result.exit_code, 0)

    def test_load_from_file_and_cli(self) -> None:
        @click.command()
        @inject_from_cli(DataclassConfig)
        def main(config) -> None:
            self.assertIsInstance(config, DataclassConfig)
            self.assertIsInstance(config.dataclass_sub_config, DataclassSubConfig)
            self.assertIsInstance(config.attrs_sub_config, AttrsSubConfig)
            self.assertEqual(config.param_1, 1)
            self.assertEqual(config.param_2, 1)
            self.assertEqual(config.param_3, 2)
            self.assertEqual(config.dataclass_sub_config.param_1, 2)
            self.assertEqual(config.dataclass_sub_config.param_2, 1)
            self.assertEqual(config.dataclass_sub_config.param_3, 2)
            self.assertEqual(config.attrs_sub_config.param_1, 1)
            self.assertEqual(config.attrs_sub_config.param_2, 3)
            self.assertEqual(config.attrs_sub_config.param_3, 4)
            self.assertEqual(config.attrs_sub_config.param_4, 6)

        runner = CliRunner()
        result = runner.invoke(main, ["-c", "tests/config_1.yml", "param_1=1", "attrs_sub_config.param_1=1"])
        self.assertEqual(result.exit_code, 0)

    def test_load_from_two_files(self) -> None:
        @click.command()
        @inject_from_cli(DataclassConfig)
        def main(config) -> None:
            self.assertIsInstance(config, DataclassConfig)
            self.assertIsInstance(config.dataclass_sub_config, DataclassSubConfig)
            self.assertIsInstance(config.attrs_sub_config, AttrsSubConfig)
            self.assertEqual(config.param_1, 3)
            self.assertEqual(config.param_2, 1)
            self.assertEqual(config.param_3, 2)
            self.assertEqual(config.dataclass_sub_config.param_1, 2)
            self.assertEqual(config.dataclass_sub_config.param_2, 1)
            self.assertEqual(config.dataclass_sub_config.param_3, 2)
            self.assertEqual(config.attrs_sub_config.param_1, 4)
            self.assertEqual(config.attrs_sub_config.param_2, 3)
            self.assertEqual(config.attrs_sub_config.param_3, 4)
            self.assertEqual(config.attrs_sub_config.param_4, 6)

        runner = CliRunner()
        result = runner.invoke(main, ["-c", "tests/config_1.yml", "-c", "tests/config_2.yml"])
        self.assertEqual(result.exit_code, 0)

    def test_save_config(self) -> None:
        @click.command()
        @inject_from_cli(DataclassConfig)
        def main(config) -> None:
            self.assertIsInstance(config, DataclassConfig)

        runner = CliRunner()
        with tempfile.TemporaryDirectory() as temp_dir:
            result = runner.invoke(
                main, ["-c", "tests/config_1.yml", "-c", "tests/config_2.yml", "-o", f"{temp_dir}/output.yml"]
            )
            self.assertEqual(
                open(f"{temp_dir}/output.yml", encoding="utf-8").read(),
                textwrap.dedent(
                    """\
                    dataclass_sub_config:
                      (): tests.test_configue_cli.DataclassSubConfig
                      custom_type: !ext tests.test_configue_cli.CustomType
                      custom_object:
                        (): tests.test_configue_cli.CustomType
                      param_1: 2
                      param_2: 1
                      param_3: 2
                      param_4:
                      - hello
                      - world
                      param_5: !!python/object:tests.test_configue_cli.CustomType
                        _arg: 1
                    attrs_sub_config:
                      (): tests.test_configue_cli.AttrsSubConfig
                      param_1: 4
                      param_2: 3
                      param_3: 4
                      param_4: 6
                      param_5:
                      - hello
                      - world
                      param_6: !!python/object:tests.test_configue_cli.CustomType
                        _arg: 1
                    param_1: 3
                    param_2: 1
                    param_3: 2
                    """
                ),
            )
        self.assertEqual(result.exit_code, 0)

    def test_load_logging_config(self):
        @click.command()
        @inject_from_cli(DataclassConfig, logging_config_path="logging_config")
        def main(config) -> None:
            self.assertIsInstance(config, DataclassConfig)
            logger = logging.getLogger("test.path")
            self.assertEqual(logging.DEBUG, logger.handlers[0].level)
            self.assertEqual(logging.ERROR, logger.handlers[1].level)

        runner = CliRunner()
        result = runner.invoke(
            main, ["-c", "tests/logging.yml", "-c", "tests/config_1.yml", "-c", "tests/config_2.yml"]
        )
        self.assertEqual(result.exit_code, 0)
