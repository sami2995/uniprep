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
    if not answer_text:
        return ""

    for letter, option_text in options.items():
        option_text_clean = clean_text(option_text).lower()
        if not option_text_clean:
            continue

        if answer_text == option_text_clean:
            return letter

        if answer_text in option_text_clean:
            return letter

        if option_text_clean in answer_text:
            return letter

    return ""


def extract_global_answer_key(text):
    """
    Extract answer keys and explanations from document-level tables or sections
    (e.g., Answer Key tables or '1. Answer B: explanation' sections at the end).
    """
    key = {}
    explanations = {}

    # 1. Answer key table format: '1 B' or '1. B'
    for num, ans in re.findall(r"^\s*(\d{1,3})\.?\s+([A-Da-d])\s*$", text, re.MULTILINE):
        key[int(num)] = ans.upper()

    # 2. Explanations section format: '1. Answer B: explanation text...'
    for num, ans, exp in re.findall(r"^\s*(\d{1,3})\.\s*Answer\s*([A-Da-d])\s*:\s*(.*)", text, re.MULTILINE):
        key[int(num)] = ans.upper()
        explanations[int(num)] = clean_text(exp)

    return key, explanations


# ---------------------------------------------------------------------------
# Linear Boundary-based Question Parser (Zero Backtracking / O(n) Execution)
# ---------------------------------------------------------------------------

_RAW_BOUNDARY = re.compile(
    r"^\s*(\d{1,3})\.?[\s\xa0]+",
    re.MULTILINE
)

# Robust Answer Token pattern matching all Ethiopian Exit Exam formats:
# - ANSWER: A / Answer: B / Ans: C / ANS: D
# - Ans. A / Ans. a. / Ans A
# - The correct answer is X
# - Correct answer: X
_ANS_TOKEN = re.compile(
    r"[\s\xa0]+(?i:Answer\s*:?|Ans\s*\.?|The\s+correct\s+answer\s+is|Correct\s+answer\s*:?)\s*"
)


def _parse_single_block(block_text, number, global_key, global_exp):
    """
    Linearly extract MCQ options and answer from a single bounded block_text.
    Supports inline answers ('Ans. B', 'ANSWER: A'), standalone option blocks without inline answer
    tokens (extracting answers from document-level answer key/explanations), and doubled/single option letters.
    """
    # 1. Try Moodle format: doubled option letters ("A. a.")
    moodle_a = re.search(r"\s+A\.\s*a\.\s*", block_text)
    if moodle_a:
        q_text = block_text[:moodle_a.start()]
        rest = block_text[moodle_a.end():]
        b_m = re.search(r"\s+B\.\s*b\.\s*", rest)
        if b_m:
            opt_a = rest[:b_m.start()]
            rest = rest[b_m.end():]
            c_m = re.search(r"\s+C\.\s*c\.\s*", rest)
            if c_m:
                opt_b = rest[:c_m.start()]
                rest = rest[c_m.end():]
                d_m = re.search(r"\s+D\.\s*d\.\s*", rest)
                if d_m:
                    opt_c = rest[:d_m.start()]
                    rest = rest[d_m.end():]
                    ans_m = _ANS_TOKEN.search(rest)
                    if ans_m:
                        opt_d = rest[:ans_m.start()]
                        ans_rest = rest[ans_m.end():].lstrip()
                        ans_match = re.match(
                            r"^(?:([a-dA-D])[\s\.\:]*)?(.*)",
                            ans_rest,
                            re.DOTALL
                        )
                        ans_letter = (ans_match.group(1) or "").upper() if ans_match else ""
                        ans_text = (
                            clean_text(ans_match.group(2))
                            if ans_match
                            else clean_text(ans_rest)
                        )
                    else:
                        opt_d = rest
                        ans_letter = global_key.get(number, "")
                        ans_text = global_exp.get(number, "")

                    opts = {
                        "A": clean_text(opt_a),
                        "B": clean_text(opt_b),
                        "C": clean_text(opt_c),
                        "D": clean_text(opt_d),
                    }
                    if all(opts.values()):
                        if not ans_letter:
                            ans_letter = infer_answer_letter(ans_text, opts)
                        return {
                            "question_number": number,
                            "question_text": clean_text(q_text),
                            "option_a": opts["A"],
                            "option_b": opts["B"],
                            "option_c": opts["C"],
                            "option_d": opts["D"],
                            "correct_answer": ans_letter,
                            "explanation": ans_text,
                        }

    # 2. Try Ministry format: single-letter options ("A. ")
    min_a = re.search(r"[\s\xa0]+A\.\s+", block_text)
    if min_a:
        q_text = block_text[:min_a.start()]
        rest = block_text[min_a.end():]
        min_b = re.search(r"[\s\xa0]+B\.\s+", rest)
        if min_b:
            opt_a = rest[:min_b.start()]
            rest = rest[min_b.end():]
            min_c = re.search(r"[\s\xa0]+C\.\s+", rest)
            if min_c:
                opt_b = rest[:min_c.start()]
                rest = rest[min_c.end():]
                min_d = re.search(r"[\s\xa0]+D\.\s+", rest)
                if min_d:
                    opt_c = rest[:min_d.start()]
                    rest = rest[min_d.end():]
                    ans_m = _ANS_TOKEN.search(rest)
                    if ans_m:
                        opt_d = rest[:ans_m.start()]
                        ans_rest = rest[ans_m.end():].lstrip()
                        ans_match = re.match(
                            r"^(?:([a-dA-D])[\s\.\:]*)?(.*)",
                            ans_rest,
                            re.DOTALL
                        )
                        ans_letter = (ans_match.group(1) or "").upper() if ans_match else ""
                        ans_text = (
                            clean_text(ans_match.group(2))
                            if ans_match
                            else clean_text(ans_rest)
                        )
                    else:
                        opt_d = rest
                        ans_letter = global_key.get(number, "")
                        ans_text = global_exp.get(number, "")

                    opts = {
                        "A": clean_text(opt_a),
                        "B": clean_text(opt_b),
                        "C": clean_text(opt_c),
                        "D": clean_text(opt_d),
                    }
                    if all(opts.values()):
                        if not ans_letter:
                            ans_letter = infer_answer_letter(ans_text, opts)
                        return {
                            "question_number": number,
                            "question_text": clean_text(q_text),
                            "option_a": opts["A"],
                            "option_b": opts["B"],
                            "option_c": opts["C"],
                            "option_d": opts["D"],
                            "correct_answer": ans_letter,
                            "explanation": ans_text,
                        }

    return None


def parse_mcq_questions(text):
    """
    Robust linear parser for Ethiopian Exit Exam PDF styles.

    Uses a two-step boundary-based approach:
    1. Extract document-level answer key tables / explanations if present.
    2. Find all potential question-number boundaries via simple O(n) regex.
    3. Filter out false boundaries (e.g., numbers inside answer explanations).
    4. Slice text into per-question blocks and parse each linearly.
    """

    text = normalize_text(text)
    global_key, global_exp = extract_global_answer_key(text)

    raw_boundaries = list(_RAW_BOUNDARY.finditer(text))

    if not raw_boundaries:
        return []

    # Filter boundaries: a valid question boundary MUST contain option A before the next boundary
    boundaries = []
    for i, b in enumerate(raw_boundaries):
        next_pos = (
            raw_boundaries[i + 1].start()
            if i + 1 < len(raw_boundaries)
            else len(text)
        )
        snippet = text[b.end():next_pos]
        if re.search(r"\s+A\.\s*a\.\s*", snippet) or re.search(r"[\s\xa0]+A\.\s+", snippet):
            boundaries.append(b)

    questions = []
    found = set()

    for i, b in enumerate(boundaries):
        number = int(b.group(1))
        if number in found:
            continue

        b_start = b.end()
        b_end = (
            boundaries[i + 1].start()
            if i + 1 < len(boundaries)
            else len(text)
        )
        block = text[b_start:b_end]

        res = _parse_single_block(block, number, global_key, global_exp)
        if res:
            questions.append(res)
            found.add(number)

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