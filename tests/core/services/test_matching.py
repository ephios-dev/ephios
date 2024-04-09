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
