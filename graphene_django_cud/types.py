import datetime
import re

import graphene
from django.utils import timezone
from graphql import GraphQLError
from graphql.language import ast


class TimeDelta(graphene.Scalar):
    """
    TimeDelta is a graphene scalar for rendering and parsing datetime.timedelta objects.
    """

    regex = re.compile(r"(?P<hours>\d+):(?P<minutes>\d+):(?P<seconds>\d+?)?")

    @staticmethod
    def serialize(timedelta: datetime.timedelta):
        hours = timedelta.seconds // 3600
        if timedelta.days > 0:
            hours += timedelta.days * 24
        minutes = (timedelta.seconds // 60) % 60
        seconds = timedelta.seconds % 60

        return_string = f"{str(hours).zfill(2)}:{str(minutes).zfill(2)}"

        if seconds:
            return_string += f":{str(seconds).zfill(2)}"

        return return_string

    @staticmethod
    def parse_literal(node):
        if isinstance(node, ast.StringValue):
            return TimeDelta.parse_value(node.value)

    @staticmethod
    def parse_value(value):
        match = TimeDelta.regex.match(value)

        if not match:
            raise GraphQLError(f"Error parsing TimeDelta node with format {value}.")

        days = 0
        hours = int(match.group("hours"))
        minutes = int(match.group("minutes"))
        seconds = match.group("seconds")

        if hours > 23:
            days = hours // 24
            hours = hours % 24

        if seconds:
            seconds = int(seconds)

        return timezone.timedelta(
            days=days, hours=hours, minutes=minutes, seconds=seconds
        )
