import pytest

from ephios.plugins.questionnaires.models import Question, Questionnaire, SavedAnswer


@pytest.fixture
def plain_shift(event):
    return event.shifts.first()


@pytest.fixture
def optional_text_question():
    return Question.objects.create(
        name="Optional Text Question",
        question_text="Optional Text Question Text?",
        required=False,
        type=Question.Type.TEXT,
        use_saved_answers=True,
    )


@pytest.fixture
def required_text_question():
    return Question.objects.create(
        name="Required Text Question",
        question_text="Required Text Question Text?",
        required=True,
        type=Question.Type.TEXT,
        use_saved_answers=True,
    )


@pytest.fixture
def optional_choice_question():
    return Question.objects.create(
        name="Optional Single Choice Question",
        question_text="Optional Single Choice Question Text?",
        required=False,
        type=Question.Type.SINGLE,
        choices=["Choice #1", "Choice #2", "Choice #3"],
    )


@pytest.fixture
def required_choice_question():
    return Question.objects.create(
        name="Required Single Choice Question",
        question_text="Required Single Choice Question Text?",
        required=True,
        type=Question.Type.SINGLE,
        choices=["Choice #1", "Choice #2", "Choice #3"],
    )


@pytest.fixture
def shift_with_optional_text_question(plain_shift, optional_text_question):
    questionnaire = Questionnaire.objects.create(shift=plain_shift)
    questionnaire.questions.add(optional_text_question)
    questionnaire.save()

    return plain_shift, optional_text_question


@pytest.fixture
def shift_with_required_text_question(plain_shift, required_text_question):
    questionnaire = Questionnaire.objects.create(shift=plain_shift)
    questionnaire.questions.add(required_text_question)
    questionnaire.save()

    return plain_shift, required_text_question


@pytest.fixture
def shift_with_text_questions(plain_shift, optional_text_question, required_text_question):
    questionnaire = Questionnaire.objects.create(shift=plain_shift)
    questionnaire.questions.add(optional_text_question, required_text_question)
    questionnaire.save()

    return plain_shift, optional_text_question, required_text_question


@pytest.fixture
def shift_with_required_choice_question(plain_shift, required_choice_question):
    questionnaire = Questionnaire.objects.create(shift=plain_shift)
    questionnaire.questions.add(required_choice_question)
    questionnaire.save()

    return plain_shift, required_choice_question


@pytest.fixture
def saved_optional_text_answer(optional_text_question, volunteer):
    return SavedAnswer.objects.create(
        user=volunteer,
        question=optional_text_question,
        answer="Optional answer from volunteer",
    )


@pytest.fixture
def saved_required_text_answer(required_text_question, volunteer):
    return SavedAnswer.objects.create(
        user=volunteer,
        question=required_text_question,
        answer="Required answer from volunteer",
    )
