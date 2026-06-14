import re

from exit_exams.models import Question, Topic


# More specific phrases should have higher weights.
# This is a defense-ready prototype classifier.
TOPIC_KEYWORDS = {
    "Computer Programming": {
        "c programming": 5,
        "c++": 5,
        "printf": 5,
        "scanf": 5,
        "pointer": 4,
        "variable": 2,
        "function": 2,
        "loop": 2,
        "array": 1,
        "identifier": 3,
        "programming language": 3,
    },

    "Object-Oriented Programming": {
        "object oriented": 5,
        "inheritance": 5,
        "polymorphism": 5,
        "encapsulation": 5,
        "abstraction": 4,
        "method overriding": 5,
        "method overloading": 5,
        "constructor": 4,
        "subclass": 4,
        "superclass": 4,
        "class": 1,
        "object": 1,
    },

    "Data Structures & Algorithms": {
        "linked list": 5,
        "binary search": 5,
        "bubble sort": 5,
        "selection sort": 5,
        "insertion sort": 5,
        "data structure": 5,
        "stack": 4,
        "queue": 4,
        "tree": 3,
        "graph": 2,
        "sorting": 3,
        "searching": 2,
        "lifo": 5,
        "fifo": 5,
    },

    "Design & Analysis of Algorithms": {
        "dynamic programming": 5,
        "divide and conquer": 5,
        "time complexity": 5,
        "space complexity": 5,
        "big o": 5,
        "asymptotic": 5,
        "recurrence relation": 5,
        "algorithm analysis": 5,
        "greedy algorithm": 5,
        "lower bound": 4,
        "complexity": 2,
        "algorithm": 1,
        "best case": 5,
"worst case": 5,
"average case": 5,
"running time": 5,
"input size": 4,
"algorithm performance": 5,
    },

    "Software Engineering": {
        "software engineering": 5,
        "software development life cycle": 5,
        "sdlc": 5,
        "waterfall": 5,
        "agile": 5,
        "software requirement": 5,
        "functional requirement": 5,
        "non functional requirement": 5,
        "software quality": 5,
        "use case": 4,
        "uml": 4,
        "maintainability": 4,
        "software testing": 4,
        "class diagram": 5,
"solid diamond": 5,
"composition relationship": 5,
"aggregation relationship": 5,
"software modeling": 4,
    },

    "Web Programming": {
        "web programming": 5,
        "html": 5,
        "css": 5,
        "javascript": 5,
        "php": 5,
        "$_get": 5,
        "$_post": 5,
        "web page": 4,
        "web browser": 4,
        "client side": 4,
        "server side scripting": 5,
        "cookie": 3,
        "session": 2,
        "web form": 4,
        "dynamic web page": 5,
"input element": 5,
"label element": 5,
"for attribute": 5,
"list style type": 5,
"navigation element": 4,
"nav element": 4,
"html form": 5,
    },

    "Database Systems": {
        "database": 4,
        "dbms": 5,
        "sql": 5,
        "normalization": 5,
        "primary key": 5,
        "foreign key": 5,
        "candidate key": 5,
        "super key": 5,
        "weak entity": 5,
        "entity relationship": 5,
        "acid property": 5,
        "database transaction": 5,
        "query optimization": 5,
        "distributed database": 5,
        "two phase locking": 5,
        "ddl": 4,
        "dml": 4,
    },

    "Data Communication & Computer Networking": {
        "computer network": 5,
        "data communication": 5,
        "tcp": 5,
        "udp": 5,
        "osi model": 5,
        "ip address": 5,
        "subnet": 5,
        "routing": 4,
        "dns": 4,
        "dhcp": 4,
        "ftp": 4,
        "smtp": 4,
        "transport layer": 5,
        "network layer": 5,
        "data link layer": 5,
        "circuit switching": 5,
        "packet switching": 5,
    },

    "Computer Security": {
        "computer security": 5,
        "confidentiality": 5,
        "integrity": 4,
        "availability": 4,
        "digital signature": 5,
        "encryption": 5,
        "decryption": 5,
        "cryptography": 5,
        "firewall": 5,
        "intrusion detection": 5,
        "access control": 5,
        "malware": 5,
        "vulnerability": 5,
        "security attack": 5,
        "authentication": 4,
    },

    "Network & System Administration": {
        "system administration": 5,
        "network administration": 5,
        "linux administration": 5,
        "user account": 4,
        "password aging": 5,
        "file permission": 5,
        "chmod": 5,
        "chown": 5,
        "chgrp": 5,
        "passwd": 5,
        "shadow file": 5,
        "disk quota": 5,
        "ldap": 5,
        "system administrator": 5,
    },

    "Introduction to AI": {
        "artificial intelligence": 5,
        "machine learning": 5,
        "expert system": 5,
        "knowledge representation": 5,
        "heuristic search": 5,
        "informed search": 5,
        "uninformed search": 5,
        "a star search": 5,
        "breadth first search": 3,
        "depth first search": 3,
        "minimax": 5,
        "neural network": 5,
        "intelligent agent": 5,
        "knowledge base": 4,
        "biological intelligence": 5,
"intelligent behavior": 5,
"cognitive modeling": 5,
"thinking humanly": 5,
"acting humanly": 5,
"thinking rationally": 5,
"acting rationally": 5,
    },

    "Computer Organization & Architecture": {
        "computer architecture": 5,
        "computer organization": 5,
        "instruction cycle": 5,
        "fetch decode execute": 5,
        "cpu": 4,
        "processor": 3,
        "register": 3,
        "cache memory": 5,
        "main memory": 4,
        "dma": 5,
        "system bus": 5,
        "input output device": 4,
        "instruction set": 5,
        "pipeline": 4,
        "processor bus": 5,
"combinational circuit": 5,
"sequential circuit": 5,
"logic circuit": 4,
"control unit": 4,
"arithmetic logic unit": 5,
    },

    "Operating Systems": {
        "operating system": 5,
        "process scheduling": 5,
        "cpu scheduling": 5,
        "deadlock": 5,
        "memory management": 5,
        "virtual memory": 5,
        "page replacement": 5,
        "semaphore": 5,
        "mutual exclusion": 5,
        "process": 2,
        "thread": 3,
        "file system": 4,
        "time sharing": 4,
        "resource allocation": 4,
    },

    "Automata & Complexity Theory": {
        "finite automata": 5,
        "deterministic finite automata": 5,
        "nondeterministic finite automata": 5,
        "dfa": 5,
        "nfa": 5,
        "pushdown automata": 5,
        "pda": 5,
        "turing machine": 5,
        "regular language": 5,
        "context free language": 5,
        "context sensitive language": 5,
        "formal language": 5,
        "formal grammar": 5,
        "recursive language": 5,
        "recursively enumerable": 5,
        "p versus np": 5,
        "np complete": 5,
    },

    "Compiler Design": {
        "compiler design": 5,
        "compiler": 4,
        "lexical analyzer": 5,
        "lexical analysis": 5,
        "syntax analysis": 5,
        "semantic analysis": 5,
        "parser": 4,
        "parse tree": 5,
        "syntax tree": 5,
        "syntax directed translation": 5,
        "intermediate code": 5,
        "three address code": 5,
        "code generation": 5,
        "symbol table": 4,
        "token": 3,
    },
}


def normalize(value):
    value = value or ""
    value = value.lower()

    # Normalize common symbols and spellings.
    value = value.replace("a*", "a star")
    value = value.replace("object-oriented", "object oriented")
    value = value.replace("non-functional", "non functional")
    value = value.replace("time-sharing", "time sharing")
    value = value.replace("&", " and ")

    # Keep characters useful for programming terms.
    value = re.sub(r"[^a-z0-9+#$_\s]", " ", value)
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def phrase_exists(text, phrase):
    """
    Match a keyword as a complete phrase instead of an arbitrary substring.

    Example:
    'class' will match 'class method',
    but it will not match 'classification'.
    """

    phrase = normalize(phrase)

    if not phrase:
        return False

    pattern = r"(?<![a-z0-9_])" + re.escape(phrase) + r"(?![a-z0-9_])"

    return re.search(pattern, text) is not None


def build_search_text(
    question_text="",
    option_a="",
    option_b="",
    option_c="",
    option_d=""
):
    return normalize(
        " ".join([
            question_text or "",
            option_a or "",
            option_b or "",
            option_c or "",
            option_d or "",
        ])
    )


def get_question_search_text(extracted_question):
    return build_search_text(
        question_text=extracted_question.question_text,
        option_a=extracted_question.option_a,
        option_b=extracted_question.option_b,
        option_c=extracted_question.option_c,
        option_d=extracted_question.option_d,
    )


def score_topic_parts(
    question_text,
    options_text,
    weighted_keywords
):
    """
    The question stem is more reliable than answer options.

    Stem keyword weight: x3
    Option keyword weight: x1
    """

    score = 0
    matched_keywords = []

    for keyword, weight in weighted_keywords.items():
        if phrase_exists(question_text, keyword):
            score += weight * 3
            matched_keywords.append({
                "keyword": keyword,
                "source": "question",
            })

        elif phrase_exists(options_text, keyword):
            score += weight
            matched_keywords.append({
                "keyword": keyword,
                "source": "options",
            })

    return score, matched_keywords


def classify_topic_from_parts(
    question_text,
    options_text,
    course
):
    """
    Classify using the question stem as the primary evidence
    and answer options as secondary evidence.
    """

    question_text = normalize(question_text)
    options_text = normalize(options_text)

    ranked_results = []

    for topic_name, weighted_keywords in TOPIC_KEYWORDS.items():
        score, matched_keywords = score_topic_parts(
            question_text=question_text,
            options_text=options_text,
            weighted_keywords=weighted_keywords,
        )

        ranked_results.append({
            "topic_name": topic_name,
            "score": score,
            "matched_keywords": matched_keywords,
        })

    ranked_results.sort(
        key=lambda result: result["score"],
        reverse=True
    )

    best_result = ranked_results[0]
    second_result = ranked_results[1]

    best_score = best_result["score"]
    second_score = second_result["score"]

    if best_score == 0:
        return {
            "topic": None,
            "score": 0,
            "confidence": 0,
            "matched_topic_name": "",
            "matched_keywords": [],
            "reason": "no_keyword_match",
        }

    # Prevent weak generic matches from being accepted.
    minimum_score = 5

    if best_score < minimum_score:
        return {
            "topic": None,
            "score": best_score,
            "confidence": 0,
            "matched_topic_name": best_result["topic_name"],
            "matched_keywords": best_result["matched_keywords"],
            "reason": "low_score",
        }

    score_difference = best_score - second_score

    # Reject exact or very close results.
    if score_difference < 3:
        return {
            "topic": None,
            "score": best_score,
            "confidence": 0,
            "matched_topic_name": best_result["topic_name"],
            "matched_keywords": best_result["matched_keywords"],
            "reason": "ambiguous_match",
        }

    confidence = round(
        score_difference / best_score,
        2
    )

    topic = Topic.objects.filter(
        domain__course=course,
        name__iexact=best_result["topic_name"]
    ).select_related("domain").first()

    if not topic:
        return {
            "topic": None,
            "score": best_score,
            "confidence": confidence,
            "matched_topic_name": best_result["topic_name"],
            "matched_keywords": best_result["matched_keywords"],
            "reason": "topic_not_found_in_database",
        }

    return {
        "topic": topic,
        "score": best_score,
        "confidence": confidence,
        "matched_topic_name": best_result["topic_name"],
        "matched_keywords": best_result["matched_keywords"],
        "reason": "classified",
    }


def classify_topic_from_text(text, course):
    """
    Compatibility wrapper for places that only provide one text value.
    """

    return classify_topic_from_parts(
        question_text=text,
        options_text="",
        course=course,
    )


def calculate_bloom_scores(question_text, options_text=""):
    """
    Produce scores for the project's four Bloom levels.

    This is a rule-assisted prediction. The academic reviewer can
    correct the predicted level before final approval.
    """

    text = normalize(question_text)

    scores = {
        Question.BloomLevel.KNOWLEDGE: 0,
        Question.BloomLevel.COMPREHENSION: 0,
        Question.BloomLevel.APPLICATION: 0,
        Question.BloomLevel.ANALYSIS: 0,
    }

    knowledge_patterns = {
        "define": 6,
        "what is": 4,
        "identify": 5,
        "list": 5,
        "name": 5,
        "stands for": 6,
        "how many": 6,
        "which keyword": 6,
        "which command is": 5,
        "which of the following is": 3,
        "which one of the following is": 3,
        "first step": 4,
        "primary role": 4,
    }

    comprehension_patterns = {
        "explain": 6,
        "describe": 6,
        "why": 6,
        "purpose of": 5,
        "meaning of": 5,
        "feature of": 5,
        "characteristic of": 5,
        "which statement": 4,
        "what does": 5,
        "difference between": 5,
        "differentiate": 5,
        "best defines": 4,
        "indicates": 4,
        "concept": 2,
        "principle": 2,
    }

    application_patterns = {
        "calculate": 8,
        "compute": 8,
        "solve": 8,
        "apply": 7,
        "implement": 7,
        "execute": 7,
        "what is the output": 9,
        "what will be the output": 9,
        "determine the output": 9,
        "find the output": 9,
        "output of the following": 9,
        "program segment": 7,
        "code segment": 7,
        "code fragment": 7,
        "following code": 7,
        "following program": 7,
        "use the following": 5,
        "given the following": 5,
        "which command would": 6,
        "subnet address": 7,
        "network address": 7,
    }

    analysis_patterns = {
        "analyze": 9,
        "compare": 9,
        "contrast": 9,
        "evaluate": 9,
        "justify": 9,
        "recommend": 8,
        "diagnose": 8,
        "which is the best": 8,
        "which is most appropriate": 8,
        "most suitable": 8,
        "best solution": 8,
        "trade off": 8,
        "examine": 7,
        "infer": 7,
        "design a": 8,
        "design an": 8,
        "design the": 8,
    }

    pattern_groups = {
        Question.BloomLevel.KNOWLEDGE: knowledge_patterns,
        Question.BloomLevel.COMPREHENSION: comprehension_patterns,
        Question.BloomLevel.APPLICATION: application_patterns,
        Question.BloomLevel.ANALYSIS: analysis_patterns,
    }

    for level, patterns in pattern_groups.items():
        for pattern, weight in patterns.items():
            if phrase_exists(text, pattern):
                scores[level] += weight

    scenario_patterns = [
        "assume that",
        "assume",
        "suppose that",
        "suppose",
        "given that",
        "consider the following",
        "consider a",
        "a developer proposes",
        "an administrator",
        "a company has",
        "a system has",
    ]

    has_scenario = any(
        phrase_exists(text, pattern)
        for pattern in scenario_patterns
    )

    if has_scenario:
        scores[Question.BloomLevel.APPLICATION] += 5

    decision_patterns = [
        "best",
        "most appropriate",
        "most suitable",
        "should be used",
        "should the",
        "recommend",
        "why",
        "solution",
    ]

    has_decision = any(
        phrase_exists(text, pattern)
        for pattern in decision_patterns
    )

    if has_scenario and has_decision:
        scores[Question.BloomLevel.ANALYSIS] += 7

    # Negative MCQs normally test understanding rather than analysis.
    if " not " in f" {text} ":
        scores[Question.BloomLevel.COMPREHENSION] += 2

    return scores


def classify_bloom_level(question_text, options_text=""):
    """
    Return one of the project's four Bloom levels.

    Evaluate and Create are represented under Analysis in the
    current four-level prototype.
    """

    scores = calculate_bloom_scores(
        question_text=question_text,
        options_text=options_text,
    )

    highest_score = max(scores.values())

    if highest_score == 0:
        return Question.BloomLevel.COMPREHENSION

    # Higher-order levels win when scores are tied.
    priority = [
        Question.BloomLevel.ANALYSIS,
        Question.BloomLevel.APPLICATION,
        Question.BloomLevel.COMPREHENSION,
        Question.BloomLevel.KNOWLEDGE,
    ]

    for level in priority:
        if scores[level] == highest_score:
            return level

    return Question.BloomLevel.COMPREHENSION


def classify_extracted_question(extracted_question):
    course = extracted_question.exam_import.course

    options_text = " ".join([
        extracted_question.option_a or "",
        extracted_question.option_b or "",
        extracted_question.option_c or "",
        extracted_question.option_d or "",
    ])

    topic_result = classify_topic_from_parts(
        question_text=extracted_question.question_text,
        options_text=options_text,
        course=course,
    )

    topic_result["bloom_level"] = classify_bloom_level(
        question_text=extracted_question.question_text,
        options_text=options_text,
    )

    return topic_result