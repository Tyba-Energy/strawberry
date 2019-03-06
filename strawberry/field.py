from typing import get_type_hints

from graphql import GraphQLField

from .constants import IS_STRAWBERRY_FIELD, IS_STRAWBERRY_INPUT
from .exceptions import MissingArgumentsAnnotationsError, MissingReturnAnnotationError
from .type_converter import get_graphql_type_for_annotation
from .utils.inspect import get_func_args


def field(wrap):
    setattr(wrap, IS_STRAWBERRY_FIELD, True)
    annotations = get_type_hints(wrap)

    name = wrap.__name__

    if "return" not in annotations:
        raise MissingReturnAnnotationError(name)

    field_type = get_graphql_type_for_annotation(annotations["return"], name)

    function_arguments = set(get_func_args(wrap)) - {"self", "info"}

    arguments_annotations = {
        key: value
        for key, value in annotations.items()
        if key not in ["info", "return"]
    }

    annotated_function_arguments = set(arguments_annotations.keys())
    arguments_missing_annotations = function_arguments - annotated_function_arguments

    if len(arguments_missing_annotations) > 0:
        raise MissingArgumentsAnnotationsError(name, arguments_missing_annotations)

    arguments = {
        name: get_graphql_type_for_annotation(annotation, name)
        for name, annotation in arguments_annotations.items()
    }

    def convert_args(args):
        converted_args = {}

        for key, value in args.items():
            if getattr(arguments_annotations[key], IS_STRAWBERRY_INPUT):
                # TODO: recursive
                converted_args[key] = arguments_annotations[key](**value)
            else:
                converted_args[key] = value

        return converted_args

    def resolver(source, info, **args):
        # TODO: convert args to input types
        args = convert_args(args)

        return wrap(source, info, **args)

    wrap.field = GraphQLField(field_type, args=arguments, resolve=resolver)
    return wrap
