import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "uniprep_backend.settings")
django.setup()

from exit_exams.models import Question, Topic
from django.db.models import Count, Q

def safe(s, limit=300):
    return str(s)[:limit].encode("ascii", errors="replace").decode("ascii")

# Get ALL approved questions for the top topic and check explanation depth
sample_topic = Topic.objects.annotate(
    total_q=Count("questions", filter=Q(questions__status="approved", questions__is_active=True))
).filter(total_q__gt=0).order_by("-total_q").first()

print(f"Topic: {sample_topic.name}")
qs = Question.objects.filter(
    topic=sample_topic, status="approved", is_active=True
).prefetch_related("choices")

# Check how many explanations are just a repeat of the correct answer (trivial)
trivial = 0
rich = 0
empty = 0
examples_rich = []
examples_trivial = []

for q in qs:
    correct = q.choices.filter(is_correct=True).first()
    expl = q.explanation.strip()
    if not expl:
        empty += 1
    elif correct and expl.lower() == correct.text.strip().lower():
        trivial += 1
        if len(examples_trivial) < 2:
            examples_trivial.append((q.text, correct.text, expl))
    else:
        rich += 1
        if len(examples_rich) < 3:
            examples_rich.append((q.text, correct.text if correct else "N/A", expl))

print(f"\nOf {qs.count()} approved questions in this topic:")
print(f"  Rich explanations (distinct from correct answer): {rich}")
print(f"  Trivial explanations (= just correct answer text): {trivial}")
print(f"  Empty explanations: {empty}")

print("\n--- RICH explanation examples ---")
for i, (q_text, ans, expl) in enumerate(examples_rich, 1):
    print(f"\n[{i}] Q: {safe(q_text)}")
    print(f"    Correct: {safe(ans)}")
    print(f"    Explanation: {safe(expl)}")

print("\n--- TRIVIAL explanation examples ---")
for i, (q_text, ans, expl) in enumerate(examples_trivial, 1):
    print(f"\n[{i}] Q: {safe(q_text)}")
    print(f"    Correct: {safe(ans)}")
    print(f"    Explanation: {safe(expl)}")
