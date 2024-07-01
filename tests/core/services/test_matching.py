from ephios.core.models import Qualification, QualificationCategory
from ephios.core.services.matching import Position, match_participants_to_positions
from ephios.core.signup.participants import PlaceholderParticipant


def test_match_participants_to_positions(qualifications):
    # create 3 participants
    ann = PlaceholderParticipant("Ann", {qualifications.nfs}, None, None)
    ben = PlaceholderParticipant("Ben", {qualifications.rs, qualifications.ce}, None, None)
    leader = Position("Führer", True, {qualifications.nfs}, [])
    driver = Position("Fahrer", True, {qualifications.rs, qualifications.c}, [])

    assert match_participants_to_positions([], []).pairings == set()
    assert match_participants_to_positions([ben], []).pairings == set()
    assert match_participants_to_positions([], [driver]).pairings == set()
    assert match_participants_to_positions([ben], [driver]).pairings == {(ben, driver)}
    assert match_participants_to_positions([ann], [driver]).pairings == set()
    assert match_participants_to_positions([ben, ann], [driver]).pairings == {(ben, driver)}
    assert match_participants_to_positions([ann, ben], [driver]).pairings == {(ben, driver)}
    assert match_participants_to_positions([ben], [driver, leader]).pairings == {(ben, driver)}
    assert match_participants_to_positions([ann, ben], [driver, leader]).pairings == {
        (ben, driver),
        (ann, leader),
    }


def test_maximise_number_of_matches_in_adverse_case():
    """
    Test that the matching algorithm maximizes the number of matches even if that means qualificaitons aren't
    utilized in the best way possible.
    For this, we create an adverse szenario:

    Positions: A, B, C, D
    Participants:
        - W (prefers B, qualifies for A+B)
        - X (prefers C, qualifies for B+C)
        - Y (prefers D, qualifies for C+D)
        - Z (prefers nothing, qualifies for D)

    Here, the preferring should not overweigh so that Z does not get matched.
    """
    category = QualificationCategory.objects.create(title="Test")
    q_a = Qualification.objects.create(title="A", category=category)
    q_b = Qualification.objects.create(title="B", category=category)
    q_c = Qualification.objects.create(title="C", category=category)
    q_d = Qualification.objects.create(title="D", category=category)

    w = PlaceholderParticipant("W", {q_a, q_b}, None, None)
    x = PlaceholderParticipant("X", {q_b, q_c}, None, None)
    y = PlaceholderParticipant("Y", {q_c, q_d}, None, None)
    z = PlaceholderParticipant("Z", {q_d}, None, None)

    positions = [
        Position("A", False, {q_a}, []),
        Position("B", False, {q_b}, [w]),
        Position("C", False, {q_c}, [x]),
        Position("D", False, {q_d}, [y]),
    ]
    participants = [w, x, y, z]

    matching = match_participants_to_positions(participants, positions)
    assert len(matching.pairings) == 4
