import dataclasses
from typing import Optional

from django.utils.functional import classproperty


@dataclasses.dataclass(frozen=True)
class SignupStats:
    requested_count: int
    confirmed_count: int
    missing: int
    free: Optional[int]  # None means infinite free
    min_count: Optional[int]  # None means no min specified
    max_count: Optional[int]  # None means infinite max

    @classproperty
    def ZERO(cls):  # pylint: disable=no-self-argument
        return SignupStats(
            requested_count=0,
            confirmed_count=0,
            missing=0,
            free=0,
            min_count=None,
            max_count=0,
        )

    @classmethod
    def reduce(cls, stats_list):
        return sum(stats_list, cls.ZERO)

    def replace(self, **kwargs):
        return dataclasses.replace(self, **kwargs)

    def has_free(self):
        return self.free is None or self.free > 0

    def __add__(self, other: "SignupStats"):
        free = self.free + other.free if self.free is not None and other.free is not None else None
        missing = self.missing + other.missing
        min_count = (
            (self.min_count or 0) + (other.min_count or 0)
            if self.min_count is not None or other.min_count is not None
            else None
        )
        max_count = (
            self.max_count + other.max_count
            if self.max_count is not None and other.max_count is not None
            else None
        )
        return SignupStats(
            requested_count=self.requested_count + other.requested_count,
            confirmed_count=self.confirmed_count + other.confirmed_count,
            missing=missing,
            free=free,
            min_count=min_count,
            max_count=max_count,
        )
