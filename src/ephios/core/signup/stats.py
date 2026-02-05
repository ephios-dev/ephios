import dataclasses
from typing import Optional

from django.utils.functional import classproperty


@dataclasses.dataclass(frozen=True)
class SignupStats:
    """
    SignupStats store counts about "fullness" of personnel structures.
    They can be combined using the `add`-operation.

    `requested_count` and `confirmed_count` store the amount of
    requested and confirmed participants respectively.

    Considering only confirmed participations, `missing` counts the
    number of open positions that are required in the shift, while
    `free` counts the number of open positions including those not required.
    If there is no imposed maximum on the number of participations,
    `free` will be None.
    `min_count` and `max_count` store the minimum and maximum number
    of participants (None meaning no min specified/infinite maximum).

    We store missing and free separate from min and max to allow for
    correct composition. If for example there are two shifts, one
    with 3 confirmed for a min of 2, and another with
    1 confirmed and a min of 2, just adding the numbers would give you
    4 confirmed for a min of 4. While that is true, the fact that
    someone is missing was lost.

    When showing something like "5/5 people found", the
    latter number should commonly be max, as min might be misleading
    as mentioned above. Also, using `max_count` might
    give you wrong results if the shift contains an unqualified
    participant and still has an open position.
    Use the dynamic `full_count` instead. If you instead want
    the minimum number of participants required so all missing spots
    are filled, use the dynamic `required_count`. Displaying `free`
    and `missing` might be more understandable though.
    """

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

    @property
    def full_count(self):
        """
        Returns the maximum number of participants so the object is considered full.
        This can be different from `max_count`, if e.g. someone dispatched an
        unqualified volunteer, so there is still an open spot.
        """
        if self.free is None:
            return None
        return self.confirmed_count + self.free

    @property
    def required_count(self):
        """
        Returns the minimum number of participants needed so every
        required position in the object could be accounted for.
        """
        return self.confirmed_count + self.missing

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
