import re
from pypdf import PdfReader


def extract_text_from_pdf(file_path):
    reader = PdfReader(file_path)
    full_text = ""

    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        full_text += f"\n\n--- Page {page_number} ---\n{text}"

    return full_text


def is_scanned_or_empty_pdf(text):
    return len(text.strip()) < 200


def clean_text(value):
    value = value or ""
    value = value.strip()
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def normalize_text(text):
    text = text.replace("\r", "\n")

    # Remove our extraction page markers
    text = re.sub(
        r"\n?--- Page \d+ ---\n?",
        "\n",
        text
    )

    # Remove lines like: 1 | P a g e
    text = re.sub(
        r"^\s*\d+\s*\|\s*P\s*a\s*g\s*e\s*$",
        "",
        text,
        flags=re.MULTILINE | re.IGNORECASE
    )

    # Remove Moodle-like inserted text: Question 2Answer
    text = re.sub(
        r"\bQuestion\s+\d+\s*Answer\b",
        " ",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)

    return text.strip()


def infer_answer_letter(answer_text, options):
    """
    If answer appears as text instead of letter, infer the option letter.
    Example:
    Ans . A* search
    """

    answer_text = clean_text(answer_text).lower()

    for letter, option_text in options.items():
        option_text_clean = clean_text(option_text).lower()

        if answer_text == option_text_clean:
            return letter

        if answer_text in option_text_clean:
            return letter

        if option_text_clean in answer_text:
            return letter

    return ""


def parse_mcq_questions(text):
    """
    Robust parser for Ethiopian Exit Exam PDF styles like:

    1 Question text
    A. a.
    Option A text
    B. b.
    Option B text
    C. c.
    Option C text
    D. d.
    Option D text
    Ans. a. Correct answer text

    Supports:
    - question numbers without dot
    - A. a. / B. b. format
    - page breaks inside questions
    - Ans. a. and Ans . answer text
    """

    text = normalize_text(text)

    # Format A (Moodle export): doubled option letters ("A. a.\n<text>"),
    # "Ans." answer token. Kept exactly as before; only the question-number
    # and final lookahead got the optional-dot / explicit \xa0 tweak (both
    # are supersets, so bare-digit Moodle files still match identically).
    moodle_pattern = re.compile(
        r"""
        (?m)^\s*(?P<number>\d{1,3})\.?[\s\xa0]+
        (?P<question>.*?)
        \s+A\.\s*a\.\s*(?P<a>.*?)
        \s+B\.\s*b\.\s*(?P<b>.*?)
        \s+C\.\s*c\.\s*(?P<c>.*?)
        \s+D\.\s*d\.\s*(?P<d>.*?)
        \s+(?:Ans\s*\.|ans\s*\.)\s*
        (?:(?P<answer>[a-dA-D])\.?\s*)?
        (?P<answer_text>.*?)
        (?=^\s*\d{1,3}\.?[\s\xa0]+|\bQuestion number\s+100\b|\Z)
        """,
        re.DOTALL | re.VERBOSE,
    )

# Format B (Ministry-style real exam): inline single-letter options
    # ("A. <text>"), "The correct answer is X." answer token. Mirrors the
    # Moodle pattern but with the doubled-letter step dropped and an extra
    # answer-token alternative added. Answer letter is inferred via the
    # existing infer_answer_letter() when only answer text is captured.
    # The question-text token is *tempered* so it cannot cross a following
    # question-number line. This prevents numbered sub-lists inside an
    # explanation (e.g. "1. Set of states ... 2. ... 5. ...") from being
    # mistaken for a new question starter, which would otherwise create a
    # phantom match that swallows a later real question's option block.
    ministry_boundary = r"(?!^\s*\d{1,3}\.?[\s\xa0]+)"
    ministry_pattern = re.compile(
        r"""
        (?m)^\s*(?P<number>\d{1,3})\.?[\s\xa0]+
        (?P<question>(?:""" + ministry_boundary + r""".)*?)
        [\s\xa0]+A\.\s+(?P<a>.*?)
        [\s\xa0]+B\.\s+(?P<b>.*?)
        [\s\xa0]+C\.\s+(?P<c>.*?)
        [\s\xa0]+D\.\s+(?P<d>.*?)
        [\s\xa0]+(?i:Ans\s*\.|The\s+correct\s+answer\s+is|Correct\s+answer\s*:?)\s*
        (?:(?P<answer>[a-dA-D])\.?\s*)?
        (?P<answer_text>.*?)
        (?=^\s*\d{1,3}\.?[\s\xa0]+|\bQuestion number\s+100\b|\Z)
        """,
        re.DOTALL | re.VERBOSE,
    )

    def _collect(pattern, found, questions):
        for match in pattern.finditer(text):
            number = int(match.group("number"))

            if number in found:
                continue

            options = {
                "A": clean_text(match.group("a")),
                "B": clean_text(match.group("b")),
                "C": clean_text(match.group("c")),
                "D": clean_text(match.group("d")),
            }

            answer = match.group("answer")
            answer_text = clean_text(match.group("answer_text"))

            if answer:
                correct_answer = answer.upper()
            else:
                correct_answer = infer_answer_letter(answer_text, options)

            questions.append({
                "question_number": number,
                "question_text": clean_text(match.group("question")),
                "option_a": options["A"],
                "option_b": options["B"],
                "option_c": options["C"],
                "option_d": options["D"],
                "correct_answer": correct_answer,
                "explanation": answer_text,
            })
            found.add(number)

    questions = []
    found = set()

    # Moodle format tried first and takes precedence; Ministry format fills
    # in any question numbers Moodle missed (tried in order, as required).
    _collect(moodle_pattern, found, questions)
    _collect(ministry_pattern, found, questions)

    questions.sort(key=lambda q: q["question_number"])

    return questions


def extract_answer_key(text):
    """
    Kept for compatibility with the old process view.
    The new parse_mcq_questions already extracts correct_answer.
    """

    text = normalize_text(text)

    answer_key = {}

    matches = re.findall(
        r"""
        ^\s*(\d{1,3})
        .*?
        (?i:Ans\s*\.|\bThe\s+correct\s+answer\s+is\b|\bCorrect\s+answer\s*:?)
        \s*
        ([A-Da-d])
        """,
        text,
        flags=re.DOTALL | re.MULTILINE | re.VERBOSE,
    )

    for number, answer in matches:
        answer_key[int(number)] = answer.upper()

    return answer_key