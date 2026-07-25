import os, sys
os.environ['DJANGO_SETTINGS_MODULE'] = 'uniprep_backend.settings'
import django
django.setup()

from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory
from analytics.views import student_dashboard

User = get_user_model()

students = User.objects.filter(role='student')
if students.exists():
    student = students.first()
    print(f"Testing student_dashboard for: {student.username}")
    factory = APIRequestFactory()
    request = factory.get('/api/analytics/dashboard/')
    from rest_framework.test import force_authenticate
    force_authenticate(request, user=student)
    try:
        response = student_dashboard(request)
        print(f"Status: {response.status_code}")
        if response.status_code != 200:
            print(f"Response: {response.data}")
        else:
            print("SUCCESS - dashboard data returned OK")
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
else:
    print("No student users found.")
