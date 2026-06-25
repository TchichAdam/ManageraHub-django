"""Candidate Skills quiz — interview & soft-skills questions.

Questions are stored here (not in the database) so the quiz can be edited
without a migration. Each question has a unique ``id``, the prompt text, a list
of answer ``options`` and the index of the correct option.
"""

QUIZ_TITLE = "Candidate Skills"
QUIZ_SUBTITLE = "Interview & Soft Skills Quiz"

QUIZ_QUESTIONS = [
    {
        "id": "q1",
        "text": "During an interview, what is the best way to answer a behavioural question (e.g. \"Tell me about a challenge you faced\")?",
        "options": [
            "Give a short yes/no answer",
            "Use the STAR method: Situation, Task, Action, Result",
            "Talk about your hobbies instead",
            "Say you have never faced a challenge",
        ],
        "answer": 1,
    },
    {
        "id": "q2",
        "text": "What should you research before a job interview?",
        "options": [
            "Nothing, stay spontaneous",
            "Only the salary",
            "The company, the role, and recent news about them",
            "The interviewer's personal social media",
        ],
        "answer": 2,
    },
    {
        "id": "q3",
        "text": "Which is the strongest example of good teamwork?",
        "options": [
            "Doing all the work yourself to be sure it is right",
            "Sharing tasks, communicating progress, and helping blocked teammates",
            "Waiting for instructions before acting",
            "Avoiding feedback to prevent conflict",
        ],
        "answer": 1,
    },
    {
        "id": "q4",
        "text": "How should you handle constructive criticism from a manager?",
        "options": [
            "Defend yourself immediately",
            "Ignore it",
            "Listen, ask clarifying questions, and act on it",
            "Quit the task",
        ],
        "answer": 2,
    },
    {
        "id": "q5",
        "text": "What is the most professional way to follow up after an interview?",
        "options": [
            "Send a short, polite thank-you message within a day or two",
            "Call every hour until you get an answer",
            "Do nothing and wait silently",
            "Message the interviewer on personal social media",
        ],
        "answer": 0,
    },
    {
        "id": "q6",
        "text": "You are given a deadline you think is too tight. The best first step is to:",
        "options": [
            "Miss the deadline without saying anything",
            "Communicate early, explain the constraints, and propose a plan",
            "Accept silently and hope it works out",
            "Blame a teammate in advance",
        ],
        "answer": 1,
    },
    {
        "id": "q7",
        "text": "Which soft skill is most important when requirements keep changing on a project?",
        "options": [
            "Rigidity",
            "Adaptability",
            "Perfectionism",
            "Avoidance",
        ],
        "answer": 1,
    },
    {
        "id": "q8",
        "text": "A good CV / cover letter should mainly:",
        "options": [
            "List every task you ever did with no focus",
            "Be tailored to the role and highlight relevant achievements",
            "Be as long as possible",
            "Use the same generic text for every company",
        ],
        "answer": 1,
    },
]


def score_quiz(post_data):
    """Score submitted answers. Returns ``(score, total, reviewed_questions)``.

    ``reviewed_questions`` is a list of dicts describing each question with the
    selected option index, the correct option index, and whether it was right.
    """
    score = 0
    reviewed = []
    for question in QUIZ_QUESTIONS:
        raw = post_data.get(question["id"])
        try:
            selected = int(raw)
        except (TypeError, ValueError):
            selected = None
        is_correct = selected == question["answer"]
        if is_correct:
            score += 1
        reviewed.append(
            {
                "id": question["id"],
                "text": question["text"],
                "options": question["options"],
                "selected": selected,
                "answer": question["answer"],
                "is_correct": is_correct,
            }
        )
    return score, len(QUIZ_QUESTIONS), reviewed
