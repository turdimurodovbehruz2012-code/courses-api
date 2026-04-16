from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q, Count, Avg
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import (
    Category, Course, Lesson, Video, Resource, 
    Enrollment, LessonProgress, Review, SearchHistory
)
from .serializers import (
    CategorySerializer, CourseListSerializer, CourseDetailSerializer,
    LessonSerializer, VideoSerializer, ResourceSerializer,
    EnrollmentSerializer, LessonProgressSerializer, ReviewSerializer,
    SearchHistorySerializer
)

class StandardPagination(PageNumberPagination):
    page_size = 12
    page_size_query_param = 'page_size'
    max_page_size = 100

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'
    
    @action(detail=True, methods=['get'])
    def courses(self, request, slug=None):
        category = self.get_object()
        courses = category.courses.filter(is_published=True)
        serializer = CourseListSerializer(courses, many=True, context={'request': request})
        return Response(serializer.data)

class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.filter(is_published=True)
    permission_classes = [AllowAny]
    lookup_field = 'slug'
    pagination_class = StandardPagination
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by category
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category__slug=category)
        
        # Filter by level
        level = self.request.query_params.get('level')
        if level:
            queryset = queryset.filter(level=level)
        
        # Filter by price
        price_type = self.request.query_params.get('price')
        if price_type == 'free':
            queryset = queryset.filter(price=0)
        elif price_type == 'paid':
            queryset = queryset.filter(price__gt=0)
        
        # Search
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(short_description__icontains=search)
            )
            # Save search history for authenticated users
            if self.request.user.is_authenticated and search:
                SearchHistory.objects.create(user=self.request.user, query=search)
        
        # Ordering
        ordering = self.request.query_params.get('ordering', '-created_at')
        if ordering in ['price', '-price', 'rating', '-rating', 'created_at', '-created_at', 'students_count', '-students_count']:
            queryset = queryset.order_by(ordering)
        else:
            queryset = queryset.order_by('-created_at')
        
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'list':
            return CourseListSerializer
        return CourseDetailSerializer
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def enroll(self, request, slug=None):
        course = self.get_object()
        user = request.user
        
        enrollment, created = Enrollment.objects.get_or_create(user=user, course=course)
        
        if created:
            course.students_count += 1
            course.save()
            return Response({'message': f'"{course.title}" kursiga muvaffaqiyatli yozildingiz'}, status=status.HTTP_201_CREATED)
        else:
            return Response({'message': 'Siz allaqachon ushbu kursga yozilgansiz'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def add_review(self, request, slug=None):
        course = self.get_object()
        user = request.user
        
        rating = request.data.get('rating')
        comment = request.data.get('comment')
        
        if not rating or not comment:
            return Response({'error': 'Rating va comment majburiy'}, status=status.HTTP_400_BAD_REQUEST)
        
        review, created = Review.objects.get_or_create(
            course=course, user=user,
            defaults={'rating': rating, 'comment': comment}
        )
        
        if not created:
            review.rating = rating
            review.comment = comment
            review.save()
        
        # Update course rating
        avg_rating = course.reviews.aggregate(Avg('rating'))['rating__avg']
        course.rating = round(avg_rating, 1) if avg_rating else 0
        course.save()
        
        serializer = ReviewSerializer(review, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['get'])
    def lessons(self, request, slug=None):
        course = self.get_object()
        lessons = course.lessons.all()
        serializer = LessonSerializer(lessons, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def my_progress(self, request, slug=None):
        course = self.get_object()
        user = request.user
        
        enrollment = Enrollment.objects.filter(user=user, course=course).first()
        
        if not enrollment:
            return Response({'error': 'Siz bu kursga yozilmagansiz'}, status=status.HTTP_404_NOT_FOUND)
        
        progress = enrollment.lesson_progress.all()
        serializer = LessonProgressSerializer(progress, many=True)
        
        return Response({
            'total_lessons': course.lessons.count(),
            'completed_lessons': progress.filter(is_completed=True).count(),
            'progress_percentage': (progress.filter(is_completed=True).count() / course.lessons.count() * 100) if course.lessons.count() > 0 else 0,
            'lessons_progress': serializer.data
        })

class LessonViewSet(viewsets.ModelViewSet):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        course_slug = self.request.query_params.get('course')
        if course_slug:
            course = get_object_or_404(Course, slug=course_slug)
            queryset = queryset.filter(course=course)
        return queryset
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def mark_complete(self, request, pk=None):
        lesson = self.get_object()
        user = request.user
        
        enrollment = Enrollment.objects.filter(user=user, course=lesson.course).first()
        
        if not enrollment:
            return Response({'error': 'Siz bu kursga yozilmagansiz'}, status=status.HTTP_403_FORBIDDEN)
        
        progress, created = LessonProgress.objects.get_or_create(
            enrollment=enrollment, lesson=lesson
        )
        
        if not progress.is_completed:
            progress.is_completed = True
            progress.completed_at = timezone.now()
            progress.save()
            
            # Update enrollment progress
            completed_count = enrollment.lesson_progress.filter(is_completed=True).count()
            enrollment.progress = completed_count
            enrollment.is_completed = completed_count == enrollment.course.lessons.count()
            
            if enrollment.is_completed:
                enrollment.completed_at = timezone.now()
            
            enrollment.save()
            
            return Response({'message': 'Dars muvaffaqiyatli tugatildi'})
        
        return Response({'message': 'Dars allaqachon tugatilgan'})
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def update_position(self, request, pk=None):
        lesson = self.get_object()
        user = request.user
        position = request.data.get('position', 0)
        
        enrollment = Enrollment.objects.filter(user=user, course=lesson.course).first()
        
        if not enrollment:
            return Response({'error': 'Siz bu kursga yozilmagansiz'}, status=status.HTTP_403_FORBIDDEN)
        
        progress, created = LessonProgress.objects.get_or_create(
            enrollment=enrollment, lesson=lesson
        )
        
        progress.last_position = position
        progress.save()
        
        return Response({'message': 'Video pozitsiyasi saqlandi', 'position': position})

class VideoViewSet(viewsets.ModelViewSet):
    queryset = Video.objects.all()
    serializer_class = VideoSerializer
    permission_classes = [AllowAny]
    
    @action(detail=True, methods=['post'])
    def increment_view(self, request, pk=None):
        video = self.get_object()
        video.views_count += 1
        video.save()
        return Response({'views_count': video.views_count})

class EnrollmentViewSet(viewsets.ModelViewSet):
    queryset = Enrollment.objects.all()
    serializer_class = EnrollmentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Enrollment.objects.filter(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def my_courses(self, request):
        enrollments = request.user.enrollments.all()
        serializer = self.get_serializer(enrollments, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def update_progress(self, request, pk=None):
        enrollment = self.get_object()
        progress = request.data.get('progress')
        
        if progress is not None:
            enrollment.progress = progress
            enrollment.is_completed = progress >= enrollment.course.lessons.count()
            if enrollment.is_completed and not enrollment.completed_at:
                enrollment.completed_at = timezone.now()
            enrollment.save()
        
        serializer = self.get_serializer(enrollment)
        return Response(serializer.data)

class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        course_id = self.request.query_params.get('course')
        if course_id:
            queryset = queryset.filter(course_id=course_id)
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class SearchViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        query = request.query_params.get('q', '')
        
        if not query:
            return Response({'error': 'Iltimos, qidiruv so\'zini kiriting'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Search in courses
        courses = Course.objects.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(short_description__icontains=query),
            is_published=True
        )
        
        # Search in categories
        categories = Category.objects.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query)
        )
        
        course_serializer = CourseListSerializer(courses, many=True, context={'request': request})
        category_serializer = CategorySerializer(categories, many=True)
        
        # Save search history for authenticated users
        if request.user.is_authenticated and query:
            SearchHistory.objects.create(user=request.user, query=query)
        
        return Response({
            'query': query,
            'courses': course_serializer.data,
            'categories': category_serializer.data,
            'total_courses': courses.count(),
            'total_categories': categories.count()
        })
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def history(self, request):
        history = request.user.search_history.all()[:20]
        serializer = SearchHistorySerializer(history, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['delete'], permission_classes=[IsAuthenticated])
    def clear_history(self, request):
        request.user.search_history.all().delete()
        return Response({'message': 'Qidiruv tarixi tozalandi'})

class StatisticsViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=['get'])
    def home(self, request):
        # Featured courses (most popular)
        featured_courses = Course.objects.filter(is_published=True).order_by('-students_count')[:8]
        
        # New courses
        new_courses = Course.objects.filter(is_published=True).order_by('-created_at')[:8]
        
        # Top rated courses
        top_rated = Course.objects.filter(is_published=True, rating__gt=0).order_by('-rating')[:8]
        
        # Categories with counts
        categories = Category.objects.annotate(
            courses_count=Count('courses', filter=Q(courses__is_published=True))
        ).filter(courses_count__gt=0)[:10]
        
        # Statistics
        total_courses = Course.objects.filter(is_published=True).count()
        total_students = Course.objects.aggregate(total=Count('enrollments'))['total'] or 0
        total_categories = Category.objects.count()
        total_lessons = Lesson.objects.filter(course__is_published=True).count()
        
        return Response({
            'featured_courses': CourseListSerializer(featured_courses, many=True, context={'request': request}).data,
            'new_courses': CourseListSerializer(new_courses, many=True, context={'request': request}).data,
            'top_rated_courses': CourseListSerializer(top_rated, many=True, context={'request': request}).data,
            'categories': CategorySerializer(categories, many=True).data,
            'statistics': {
                'total_courses': total_courses,
                'total_students': total_students,
                'total_categories': total_categories,
                'total_lessons': total_lessons,
            }
        })

@api_view(['GET'])
def home_api(request):
    return Response({
        'message': 'Kurslar API platformasiga xush kelibsiz!',
        'version': '1.0.0',
        'endpoints': {
            'categories': '/api/categories/',
            'courses': '/api/courses/',
            'lessons': '/api/lessons/',
            'videos': '/api/videos/',
            'enrollments': '/api/enrollments/',
            'reviews': '/api/reviews/',
            'search': '/api/search/search/',
            'statistics': '/api/statistics/home/',
        },
        'admin_panel': 'http://127.0.0.1:8000/admin/'
    })

@api_view(['GET'])
def get_video_by_lesson(request, lesson_id):
    try:
        video = Video.objects.get(lesson_id=lesson_id)
        serializer = VideoSerializer(video)
        return Response(serializer.data)
    except Video.DoesNotExist:
        return Response({'error': 'Video topilmadi'}, status=status.HTTP_404_NOT_FOUND)