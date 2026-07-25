# UniPrep Phase 1 Implementation Checklist

## BACKEND IMPLEMENTATION STATUS

### 1. CustomUser Model & Role System
- ✅ TextChoices for roles implemented
- ✅ STUDENT, TEACHER, DEPARTMENT_HEAD, SYSTEM_ADMIN roles exist
- ✅ department FK added
- ✅ Role helper methods exist (is_student, is_teacher, is_department_head, is_system_admin)

### 2. Database Models
- ✅ Department model with id, name, code, description, created_at
- ✅ Course model with department FK
- ✅ TeacherCourseAssignment model with teacher FK, course FK, assigned_at
- ✅ StudentProfile model exists with user, student_id, department, program, year_of_study
- ✅ Question model with status workflow (draft, submitted, approved, rejected, archived)
- ✅ Review tracking (reviewed_by, reviewed_at, rejection_reason, submitted_at)

### 3. Serializers
- ✅ DepartmentSerializer
- ✅ CourseSerializer with department_name
- ✅ TeacherCourseAssignmentSerializer with teacher_username and course_name
- ✅ QuestionSerializer with approval workflow fields
- ✅ RejectQuestionSerializer for rejection reason

### 4. Permissions
- ✅ IsTeacherRole permission
- ✅ IsDepartmentHeadRole permission
- ✅ IsAdminOrReadOnly permission
- ⚠️ NEED: Explicit permission for question approval (restrict to department heads only)
- ⚠️ NEED: Permission to restrict teachers to their assigned courses

### 5. Views & APIs
- ✅ DepartmentViewSet
- ✅ CourseViewSet  
- ✅ TeacherCourseAssignmentViewSet
- ✅ QuestionViewSet with role-based access
- ✅ Question approval endpoint (approve_question)
- ✅ Question rejection endpoint (reject_question)
- ✅ Submit for approval endpoint (submit_question_for_approval)
- ✅ Pending approvals endpoint (pending_question_approvals)
- ✅ My assigned courses endpoint (my_assigned_courses)
- ⚠️ NEED: Dashboard summary endpoint for totals

### 6. Data Migration Strategy
- ✅ Migration 0002_institutional_roles created
- ✅ Migration 0003_customuser_department created  
- ✅ Migration 0006_department_teacher_assignments
- ✅ Migration 0007_question_approval_workflow with backfill logic
- ⚠️ NEED: Verify all existing admin users migrated to DEPARTMENT_HEAD

### 7. Access Control
- ✅ Teachers can only create draft questions
- ✅ Teachers can only edit their own draft questions
- ✅ Only department heads can approve/reject questions in their department
- ✅ System admins CANNOT approve questions academically
- ✅ Students only see approved questions
- ⚠️ NEED: Verify teachers can only access their assigned courses

### 8. Role Responsibilities Implementation
- ✅ SYSTEM_ADMIN: Can manage users, departments, assign teachers/department heads
- ✅ DEPARTMENT_HEAD: Can approve/reject questions, view department analytics
- ✅ TEACHER: Can create questions, submit for approval, manage assigned courses
- ✅ STUDENT: Can take exams, view analytics, use study tools

---

## FRONTEND IMPLEMENTATION STATUS

### 1. Authentication Context
- ⚠️ NEED: Verify AuthContext handles all 4 roles
- ⚠️ NEED: Verify role-based UI conditionals

### 2. Sidebar Navigation
- ⚠️ NEED: Student sidebar with Dashboard, Exams, Results, Materials, Focus
- ⚠️ NEED: Teacher sidebar with Dashboard, My Courses, Question Bank, Materials, Analytics
- ⚠️ NEED: Department Head sidebar with Dashboard, Academic Structure, Question Approval, Exam Bank, Analytics, Blueprint Settings
- ⚠️ NEED: System Admin sidebar with Dashboard, Users, Departments, System Settings

### 3. Protected Routes
- ⚠️ NEED: Update ProtectedRoute logic to support all 4 roles
- ⚠️ NEED: Add role-based route guards

### 4. Components Needed
- ⚠️ NEED: Teacher Dashboard component
- ⚠️ NEED: Teacher My Courses component
- ⚠️ NEED: Question Bank component (for teachers)
- ⚠️ NEED: Department Head Dashboard
- ⚠️ NEED: Question Approval Queue component
- ⚠️ NEED: Academic Structure component
- ⚠️ NEED: System Admin Dashboard
- ⚠️ NEED: Users Management component
- ⚠️ NEED: Departments Management component

### 5. Updated Pages
- ⚠️ NEED: Update Dashboard to show role-specific metrics
- ⚠️ NEED: Update Analytics to show department/teacher scope

---

## MISSING IMPLEMENTATIONS

### Backend
1. **Dashboard Summary Endpoint** - totals for teachers, students, departments, courses per dept
2. **Verify Permission Enforcement** - ensure teachers can only access assigned courses
3. **Bulk Approve Extracted Questions** - ensure department heads only can approve
4. **Admin APIs** - for assigning teachers to courses (verify access control)

### Frontend
1. **Conditional Sidebar** - render different menus based on role
2. **Teacher Pages** - My Courses, Question Bank
3. **Department Head Pages** - Question Approval, Academic Structure, Blueprint Settings
4. **System Admin Pages** - Users Management, Departments, System Settings
5. **Protected Routes** - update ProtectedRoute component for all roles
6. **Role-based UI** - conditionally show/hide features

---

## ACTION ITEMS (PRIORITY ORDER)

### MUST DO (Blocking):
1. Verify data migration - all existing admin users → DEPARTMENT_HEAD
2. Implement Dashboard Summary Endpoint (backend)
3. Update Frontend ProtectedRoute for all roles
4. Implement Conditional Sidebar based on role
5. Create Teacher Pages (My Courses, Question Bank)
6. Create Department Head Pages (Question Approval)
7. Create System Admin Pages (Users, Departments)

### SHOULD DO (High Priority):
1. Add role-based UI elements to existing components
2. Update Navbar to show current user role
3. Add loading/error states to new components
4. Test all role transitions

### NICE TO HAVE (Future):
1. Add department filtering to analytics
2. Add teacher performance metrics
3. Add audit logging for approvals
