from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib import messages
from django.urls import reverse, reverse_lazy
from django.views.generic import ListView, DetailView, CreateView
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST
from django.db.models import Count

from .models import Course, Lesson, Student
from .forms import CourseForm, LessonForm, CourseEnrollmentForm, UserUpdateForm

# DRF imports
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import CourseSerializer


@login_required
@require_POST
def toggle_completion(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    student = Student.objects.filter(email=request.user.email).first()

    if student:
        if lesson in student.completed_lessons.all():
            student.completed_lessons.remove(lesson)
            messages.info(request, f"Marked '{lesson.title}' as incomplete.")
        else:
            student.completed_lessons.add(lesson)
            messages.success(request, f"Marked '{lesson.title}' as complete.")

    return redirect('course_detail', pk=lesson.course.id)


# User Registration
def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Registration successful!")
            return redirect('/')
    else:
        form = UserCreationForm()
    return render(request, 'courses/register.html', {'form': form})


# User Login
def user_login(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, "Login successful!")
            return redirect('/')
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()
    return render(request, 'courses/login.html', {'form': form})


# User Logout
def user_logout(request):
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect('/')


# Profile Update
@login_required
def profile(request):
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('profile')
    else:
        form = UserUpdateForm(instance=request.user)
    return render(request, 'courses/profile.html', {'form': form})


# Course List (CBV)
@method_decorator(login_required, name='dispatch')
class CourseListView(ListView):
    model = Course
    template_name = 'courses/course_list.html'
    context_object_name = 'courses'


# Course Detail (CBV)
class CourseDetailView(DetailView):
    model = Course
    template_name = 'courses/course_detail.html'
    context_object_name = 'course'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = self.get_object()
        student = Student.objects.filter(email=self.request.user.email).first()

        completed_lesson_ids = (
            student.completed_lessons.filter(course=course).values_list('id', flat=True) if student else []
        )

        context['lessons'] = course.lessons.all()
        context['student'] = student
        context['completed_lesson_ids'] = completed_lesson_ids

        total_lessons = course.lessons.count()
        completed_lessons = len(completed_lesson_ids)

        context['progress_percentage'] = (completed_lessons / total_lessons) * 100 if total_lessons > 0 else 0

        return context


# Course Create (CBV)
class CourseCreateView(CreateView):
    model = Course
    fields = ['title', 'description', 'duration', 'thumbnail']
    template_name = 'courses/course_form.html'
    success_url = reverse_lazy('course_list')


# Course Update
@login_required
def course_update(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    if request.method == "POST":
        form = CourseForm(request.POST, request.FILES, instance=course)
        if form.is_valid():
            form.save()
            messages.success(request, "Course updated successfully!")
            return redirect('course_list')
    else:
        form = CourseForm(instance=course)
    return render(request, 'courses/course_form.html', {'form': form})


# Course Delete
@login_required
def course_delete(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    if request.method == "POST":
        course.delete()
        messages.success(request, "Course deleted successfully!")
        return redirect('course_list')
    return render(request, 'courses/course_confirm_delete.html', {'course': course})


# Lesson Create
@login_required
def lesson_create(request):
    if request.method == "POST":
        form = LessonForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Lesson created successfully!")
            return redirect('course_list')
    else:
        form = LessonForm()
    return render(request, 'courses/lesson_form.html', {'form': form})


# Lesson Update
@login_required
def lesson_update(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    if request.method == "POST":
        form = LessonForm(request.POST, instance=lesson)
        if form.is_valid():
            form.save()
            messages.success(request, "Lesson updated successfully!")
            return redirect('course_list')
    else:
        form = LessonForm(instance=lesson)
    return render(request, 'courses/lesson_form.html', {'form': form})


# Lesson Delete
@login_required
def lesson_delete(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    if request.method == "POST":
        lesson.delete()
        messages.success(request, "Lesson deleted successfully!")
        return redirect('course_list')
    return render(request, 'courses/lesson_confirm_delete.html', {'lesson': lesson})


# Enroll Student (HTML View)
@login_required
def enroll_student(request):
    if request.method == 'POST':
        form = CourseEnrollmentForm(request.POST)
        if form.is_valid():
            student_name = form.cleaned_data['student_name']
            student_email = form.cleaned_data['student_email']
            course = form.cleaned_data['course']

            student, created = Student.objects.get_or_create(email=student_email, defaults={'name': student_name})

            if not created and student.name != student_name:
                student.name = student_name
                student.save()

            was_already_enrolled = student.enrolled_courses.filter(id=course.id).exists()

            if was_already_enrolled:
                messages.warning(request, f"{student_name} is already enrolled in {course.title}.")
            else:
                student.enrolled_courses.add(course)
                messages.success(request, f"{student_name} has been successfully enrolled in {course.title}.")

            redirect_url = f"{reverse('enrollment_success', args=[student.email, course.id])}?was_already_enrolled={'true' if was_already_enrolled else 'false'}"
            return redirect(redirect_url)
    else:
        form = CourseEnrollmentForm()

    return render(request, 'courses/enroll_student.html', {'form': form})


# Enrollment Success
@login_required
def enrollment_success(request, student_email, course_id):
    student = get_object_or_404(Student, email=student_email)
    course = get_object_or_404(Course, id=course_id)
    was_already_enrolled = request.GET.get('was_already_enrolled', 'false') == 'true'

    return render(request, 'courses/enrollment_success.html', {
        'student': student,
        'course': course,
        'was_already_enrolled': was_already_enrolled
    })


# View Enrolled Students
@login_required
def view_enrolled_students(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    students = course.students.all()
    return render(request, 'courses/view_enrolled_students.html', {'course': course, 'students': students})


# -----------------------
# ✅ API VIEWS (DRF)
# -----------------------

class CourseListAPI(APIView):
    def get(self, request):
        courses = Course.objects.all()
        serializer = CourseSerializer(courses, many=True)
        return Response(serializer.data)


class CourseDetailAPI(APIView):
    def get(self, request, pk):
        try:
            course = Course.objects.get(pk=pk)
        except Course.DoesNotExist:
            return Response({'error': 'Course not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = CourseSerializer(course)
        return Response(serializer.data)


class EnrollStudentAPI(APIView):
    def post(self, request):
        student_email = request.data.get('email')
        course_id = request.data.get('course_id')

        if not student_email or not course_id:
            return Response({'error': 'Email and course_id are required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            return Response({'error': 'Course not found.'}, status=status.HTTP_404_NOT_FOUND)

        student, created = Student.objects.get_or_create(email=student_email)

        if course in student.enrolled_courses.all():
            return Response({'message': f'{student.email} is already enrolled in {course.title}.'}, status=status.HTTP_200_OK)

        student.enrolled_courses.add(course)

        return Response({'message': f'{student.email} has been enrolled in {course.title}.'}, status=status.HTTP_201_CREATED)
