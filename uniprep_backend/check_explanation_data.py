import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "uniprep_backend.settings")
django.setup()

from exit_exams.models import Question, Topic, Course

# ── 1. EXPLANATION FIELD POPULATION ─────────────────────────────────────────
print("=" * 60)
print("CHECK 1: Explanation field population")
print("=" * 60)

approved_qs = Question.objects.filter(status="approved", is_active=True)
total_approved = approved_qs.count()
with_explanation = approved_qs.exclude(explanation="").count()
empty_explanation = approved_qs.filter(explanation="").count()
pct = round((with_explanation / total_approved * 100), 1) if total_approved else 0

print(f"Total approved questions: {total_approved}")
print(f"With non-empty explanation: {with_explanation} ({pct}%)")
print(f"With empty explanation: {empty_explanation} ({100-pct}%)")

# Per-topic breakdown for first 5 topics that have approved questions
print()
print("Per-topic breakdown (first 10 topics with approved questions):")
print(f"{'Topic':<45} {'Total':>6} {'With Expl':>10} {'%':>6}")
print("-" * 72)

from django.db.models import Count, Q

topic_stats = (
    Topic.objects.annotate(
        total_q=Count("questions", filter=Q(questions__status="approved", questions__is_active=True)),
        expl_q=Count("questions", filter=Q(questions__status="approved", questions__is_active=True) & ~Q(questions__explanation="")),
    )
    .filter(total_q__gt=0)
    .order_by("-total_q")[:10]
)

for t in topic_stats:
    pct_t = round(t.expl_q / t.total_q * 100, 1) if t.total_q else 0
    print(f"{t.name[:45]:<45} {t.total_q:>6} {t.expl_q:>10} {pct_t:>5}%")

# ── 2. SAMPLE QUESTIONS + EXPLANATIONS ──────────────────────────────────────
print()
print("=" * 60)
print("CHECK 3: Sample questions from a real topic")
print("=" * 60)

# Pick the first topic that has approved questions
sample_topic = Topic.objects.annotate(
    total_q=Count("questions", filter=Q(questions__status="approved", questions__is_active=True))
).filter(total_q__gt=0).order_by("-total_q").first()

print(f"Sample topic: {sample_topic.name}")
print(f"Domain: {sample_topic.domain.name}")
print()

sample_qs = Question.objects.filter(
    topic=sample_topic, status="approved", is_active=True
).prefetch_related("choices")[:3]

def safe_print(s):
    print(str(s).encode("ascii", errors="replace").decode("ascii"))

for i, q in enumerate(sample_qs, 1):
    correct_choice = q.choices.filter(is_correct=True).first()
    safe_print(f"--- Question {i} ---")
    safe_print(f"Q: {q.text}")
    safe_print(f"Correct answer: {correct_choice.text if correct_choice else '[no correct choice]'}")
    expl = q.explanation[:400] if q.explanation else "[EMPTY]"
    safe_print(f"Explanation: {expl}")
    safe_print("")
