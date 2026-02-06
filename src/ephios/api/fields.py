from rest_framework.fields import ChoiceField


class ChoiceDisplayField(ChoiceField):
    def to_representation(self, value):
        return {"value": value, "label": self.choices[value]}
