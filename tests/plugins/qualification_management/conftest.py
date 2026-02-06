import pytest

from ephios.core.models import Qualification, QualificationCategory, QualificationGrant
from ephios.plugins.qualification_management.importing import (
    DeserializedQualification,
    QualificationChangeManager,
)

SANH_UUID = "b1faab38-2e7c-4507-b753-06d1e653412d"
NOTSAN_UUID = "d114125b-7cf4-49e2-8908-f93e2f95dfb8"


@pytest.fixture
def deserialized_qualifications():
    b = DeserializedQualification({
        "uuid": "247fab6a-8784-4976-a406-985fe47dc683",
        "title": "Deutsches Rettungsschwimmabzeichen Bronze",
        "abbreviation": "DRSA Bronze",
        "includes": [],
        "included_by": ["ef95a854-2eeb-431c-a795-bc291b341d49"],
        "category": {
            "uuid": "cd10e68f-41fe-4ca0-a624-3ab3eb85bd08",
            "title": "Wasserrettung Allgemein",
        },
    })
    s = DeserializedQualification({
        "uuid": "ef95a854-2eeb-431c-a795-bc291b341d49",
        "title": "Deutsches Rettungsschwimmabzeichen Silber",
        "abbreviation": "DRSA Silber",
        "includes": ["247fab6a-8784-4976-a406-985fe47dc683"],
        "included_by": ["b601a18b-cee8-4037-af33-dd7aabeac295"],
        "category": {
            "uuid": "cd10e68f-41fe-4ca0-a624-3ab3eb85bd08",
            "title": "Wasserrettung Allgemein",
        },
    })
    g = DeserializedQualification({
        "uuid": "b601a18b-cee8-4037-af33-dd7aabeac295",
        "title": "Deutsches Rettungsschwimmabzeichen Gold",
        "abbreviation": "DRSA Gold",
        "includes": ["ef95a854-2eeb-431c-a795-bc291b341d49"],
        "included_by": [],
        "category": {
            "uuid": "cd10e68f-41fe-4ca0-a624-3ab3eb85bd08",
            "title": "Wasserrettung Allgemein",
        },
    })
    return b, s, g


@pytest.fixture
def saved_deserialized_qualifications(deserialized_qualifications):
    QualificationChangeManager().add_deserialized_qualifications_to_db(
        *deserialized_qualifications
    ).commit()
    return deserialized_qualifications


@pytest.fixture
def qualification_grant(saved_deserialized_qualifications, volunteer):
    return QualificationGrant.objects.create(
        user=volunteer,
        qualification=Qualification.objects.create(
            title="custom",
            is_imported=False,
            abbreviation="cstm",
            uuid="5543ce30-5593-48b7-aa01-78d4cc54bf22",
            category=QualificationCategory.objects.get(),
        ),
    )
