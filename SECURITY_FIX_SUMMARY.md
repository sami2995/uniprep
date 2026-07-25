# Question Approval Workflow - Security Fix Summary

## Problem
The old PDF approval path (`approve_extracted_question` and `reject_extracted_question`) could still let system admins academically approve/reject questions, bypassing the role-based access control.

## Solution
Added explicit system admin checks to all four question approval/rejection endpoints:

### 1. Main Workflow (Already Fixed)
- ✅ `approve_question()` - Denies system admins before department head check
- ✅ `reject_question()` - Denies system admins before department head check

### 2. PDF Import Workflow (Newly Fixed)
- ✅ `approve_extracted_question()` - Now explicitly denies system admins
- ✅ `reject_extracted_question()` - Now explicitly denies system admins

## Security Model

**Question Status Workflow:**
```
DRAFT → SUBMITTED → APPROVED
  ↓                    ↓
  └────→ REJECTED      └→ is_active=True

Only teachers can create/edit draft questions
Only department heads can approve/reject submitted questions
System admins have NO academic approval authority
```

**Role Permissions:**
- **Student**: Can view only APPROVED questions
- **Teacher**: Can create/edit own DRAFT questions, submit for approval
- **Department Head**: Can approve/reject SUBMITTED questions in their department
- **System Admin**: Can view all questions but CANNOT approve/reject any

## Key Code Changes

### Before (PDF Approval - Vulnerable)
```python
def approve_extracted_question(request, extracted_question_id):
    user = request.user
    
    if not is_department_head_user(user):  # This alone doesn't block system_admins!
        return Response({"detail": "Only department heads..."}, status=403)
```

### After (PDF Approval - Secured)
```python
def approve_extracted_question(request, extracted_question_id):
    user = request.user
    
    if is_system_admin_user(user):
        return Response(
            {"detail": "System admins cannot academically approve questions."},
            status=403
        )
    
    if not is_department_head_user(user):
        return Response({"detail": "Only department heads..."}, status=403)
```

## Affected Endpoints

1. **Main Workflow**
   - POST `/api/questions/<id>/approve/` - Protected ✅
   - POST `/api/questions/<id>/reject/` - Protected ✅

2. **PDF Import Workflow**
   - POST `/api/extracted-questions/<id>/approve/` - Protected ✅
   - POST `/api/extracted-questions/<id>/reject/` - Protected ✅

## Additional Safeguards

- QuestionViewSet's `perform_update()` is restricted to teachers editing their own draft questions
- The `status` field is read-only in the serializer
- Questions can only change status through dedicated approval/rejection endpoints

## Testing

Comprehensive test suite created in `exit_exams/test_approval_workflow.py`:
- System admins are denied approval/rejection on both workflows
- Department heads can approve/reject in their department
- Teachers can only edit their own draft questions
- All status transitions are validated

## Files Modified

1. `exit_exams/views.py`:
   - `approve_extracted_question()` - Added system admin check
   - `reject_extracted_question()` - Added system admin check

2. `exit_exams/test_approval_workflow.py` - New comprehensive test suite
