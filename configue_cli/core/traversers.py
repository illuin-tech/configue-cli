import dataclasses
from typing import Any, ClassVar, Dict, Optional, Protocol, Tuple, Type, Union

import attr

from .exceptions import UnsupportedDataclassType
from .missing import MISSING


class NativeDataclassInstance(Protocol):
    __dataclass_fields__: ClassVar[dict[str, dataclasses.Field[Any]]]


DataclassInstance = Union[NativeDataclassInstance, attr.AttrsInstance]


class NativeDataclassTraverser:
    @staticmethod
    def traverse_instance(
        instance: NativeDataclassInstance,
        initial_config: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Dict[str, Any], NativeDataclassInstance]:
        config: Dict[str, Any] = {"()": instance.__class__.__module__ + "." + instance.__class__.__qualname__}
        partially_init_instance = instance.__class__.__new__(instance.__class__)
        initial_config = initial_config or {}

        for field in dataclasses.fields(instance.__class__):
            if not field.init:
                continue
            sub_instance = getattr(instance, field.name)
            sub_config, partially_init_subinstance = Traverser.traverse_instance(
                sub_instance, initial_config=initial_config.get(field.name, None)
            )
            setattr(partially_init_instance, field.name, partially_init_subinstance)
            config[field.name] = sub_config
        return config, instance

    @staticmethod
    def traverse_type(
        type_: Type[NativeDataclassInstance],
        initial_config: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Dict[str, Any], NativeDataclassInstance]:
        config: Dict[str, Any] = {"()": type_.__module__ + "." + type_.__qualname__}
        partially_init_instance = type_.__new__(type_)
        initial_config = initial_config or {}

        for field in dataclasses.fields(type_):
            if not field.init:
                continue
            if not isinstance(field.default, dataclasses._MISSING_TYPE):  # pylint: disable=protected-access
                sub_instance_type = field.default
                try:
                    sub_config, partially_init_subinstance = Traverser.traverse_type(
                        sub_instance_type, initial_config=initial_config.get(field.name, None)
                    )
                    setattr(partially_init_instance, field.name, partially_init_subinstance)
                except UnsupportedDataclassType:
                    sub_config = initial_config.get(field.name, sub_instance_type)
                    setattr(partially_init_instance, field.name, sub_config)

            elif not isinstance(field.default_factory, dataclasses._MISSING_TYPE):  # pylint: disable=protected-access
                sub_instance = field.default_factory()
                sub_config, partially_init_subinstance = Traverser.traverse_instance(
                    sub_instance, initial_config=initial_config.get(field.name, None)
                )
                setattr(partially_init_instance, field.name, partially_init_subinstance)

            else:
                sub_instance_type = field.type
                try:
                    sub_config, partially_init_subinstance = Traverser.traverse_type(
                        sub_instance_type, initial_config=initial_config.get(field.name, None)
                    )
                    setattr(partially_init_instance, field.name, partially_init_subinstance)
                except UnsupportedDataclassType:
                    sub_config = initial_config.get(field.name, MISSING)
                    try:
                        setattr(partially_init_instance, field.name, sub_config)
                    except TypeError:
                        # a converter can raise an issue here so we bypass it
                        pass

            config[field.name] = sub_config

        return config, partially_init_instance


class AttrsDataclassTraverser:
    @staticmethod
    def _update_with_factory_takes_self(
        field: attr.Attribute,
        partially_init_instance: attr.AttrsInstance,
        initial_config: Dict[str, Any],
    ) -> Any:
        try:
            sub_instance = field.default.factory(partially_init_instance)  # type: ignore[union-attr]
            sub_config, partially_init_subinstance = Traverser.traverse_instance(
                sub_instance, initial_config=initial_config.get(field.name, None)
            )
            setattr(partially_init_instance, field.name, partially_init_subinstance)

        except Exception:  # pylint: disable=broad-exception-caught
            sub_config = initial_config.get(field.name, MISSING)
            setattr(partially_init_instance, field.name, sub_config)
        return sub_config

    @staticmethod
    def _update_with_factory_no_takes_self(
        field: attr.Attribute,
        partially_init_instance: attr.AttrsInstance,
        initial_config: Dict[str, Any],
    ) -> Any:
        sub_instance = field.default.factory()  # type: ignore[union-attr]
        sub_config, partially_init_subinstance = Traverser.traverse_instance(
            sub_instance, initial_config=initial_config.get(field.name, None)
        )
        setattr(partially_init_instance, field.name, partially_init_subinstance)
        return sub_config

    @staticmethod
    def traverse_instance(
        instance: attr.AttrsInstance,
        initial_config: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Dict[str, Any], attr.AttrsInstance]:
        config: Dict[str, Any] = {"()": instance.__class__.__module__ + "." + instance.__class__.__qualname__}
        partially_init_instance = instance.__class__.__new__(instance.__class__)
        initial_config = initial_config or {}

        for field in attr.fields(instance.__class__):
            if not field.init:
                continue
            sub_instance = getattr(instance, field.name)
            sub_config, partially_init_subinstance = Traverser.traverse_instance(
                sub_instance, initial_config=initial_config.get(field.name, None)
            )
            setattr(partially_init_instance, field.name, partially_init_subinstance)
            config[field.name] = sub_config
        return config, instance

    @classmethod
    def traverse_type(
        cls,
        type_: Type[attr.AttrsInstance],
        initial_config: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Dict[str, Any], attr.AttrsInstance]:
        config: Dict[str, Any] = {"()": type_.__module__ + "." + type_.__qualname__}
        partially_init_instance = type_.__new__(type_)
        initial_config = initial_config or {}

        for field in attr.fields(type_):
            if not field.init:
                continue
            # pylint: disable=protected-access
            if field.default != attr._make._Nothing.NOTHING:  # type: ignore[attr-defined]
                if isinstance(field.default, attr._make.Factory):  # type: ignore[attr-defined]
                    if field.default.takes_self:
                        sub_config = cls._update_with_factory_takes_self(field, partially_init_instance, initial_config)
                    else:
                        sub_config = cls._update_with_factory_no_takes_self(
                            field, partially_init_instance, initial_config
                        )

                else:
                    sub_config = initial_config.get(field.name, field.default)
                    setattr(partially_init_instance, field.name, sub_config)

            else:
                try:
                    sub_config, partially_init_subinstance = Traverser.traverse_type(
                        field.type, initial_config=initial_config.get(field.name, None)
                    )
                    setattr(partially_init_instance, field.name, partially_init_subinstance)

                except UnsupportedDataclassType:
                    sub_config = initial_config.get(field.name, MISSING)
                    try:
                        setattr(partially_init_instance, field.name, sub_config)
                    except TypeError:
                        # a converter can raise an issue here so we bypass it
                        pass

            config[field.name] = sub_config

        return config, partially_init_instance


class DictTraverser:
    @staticmethod
    def traverse_instance(
        instance: Dict[str, Any],
        initial_config: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Dict[str, Any], Any]:
        config: Dict[str, Any] = {}
        initial_config = initial_config if initial_config is not None else {}
        for key, value in instance.items():
            sub_config, sub_instance = Traverser.traverse_instance(initial_config.get(key, value))
            config[key] = sub_config
            instance[key] = sub_instance
        return config, instance


class Traverser:
    @classmethod
    def traverse_instance(cls, instance: Any, initial_config: Any = None) -> Tuple[Any, Any]:
        if dataclasses.is_dataclass(instance.__class__):
            return NativeDataclassTraverser.traverse_instance(instance, initial_config)
        if attr.has(instance.__class__):
            return AttrsDataclassTraverser.traverse_instance(instance, initial_config)
        if isinstance(instance, dict):
            return DictTraverser.traverse_instance(instance)
        instance = initial_config if initial_config is not None else instance
        return instance, instance

    @classmethod
    def traverse_type(
        cls,
        type_: Type[DataclassInstance],
        initial_config: Any = None,
    ) -> Tuple[Dict[str, Any], DataclassInstance]:
        if dataclasses.is_dataclass(type_):
            return NativeDataclassTraverser.traverse_type(type_, initial_config=initial_config)
        if attr.has(type_):
            return AttrsDataclassTraverser.traverse_type(type_, initial_config=initial_config)
        raise UnsupportedDataclassType(
            f"`type_` should be the type of a native dataclass or `attr` dataclass, not {type_}"
        )
