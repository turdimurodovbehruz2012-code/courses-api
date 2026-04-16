from rest_framework import serializers
from .models import (
    Category, Course, Lesson, Video, Resource, 
    Enrollment, LessonProgress, Review, SearchHistory
)
from django.contrib.auth.models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'date_joined']

class CategorySerializer(serializers.ModelSerializer):
    courses_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'icon', 'description', 'courses_count', 'created_at']
    
    def get_courses_count(self, obj):
        return obj.courses.filter(is_published=True).count()

class VideoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Video
        fields = ['id', 'title', 'video_url', 'video_file', 'iframe_code', 'duration', 'views_count']

class ResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resource
        fields = ['id', 'title', 'resource_type', 'file', 'link']

class LessonSerializer(serializers.ModelSerializer):
    video = VideoSerializer(read_only=True)
    resources = ResourceSerializer(many=True, read_only=True)
    
    class Meta:
        model = Lesson
        fields = ['id', 'title', 'order', 'duration', 'is_free', 'video', 'resources', 'created_at']

class CourseListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    author_name = serializers.CharField(source='author.username', read_only=True)
    
    class Meta:
        model = Course
        fields = ['id', 'title', 'slug', 'short_description', 'image', 'level', 
                 'price', 'duration', 'students_count', 'rating', 'category_name', 
                 'author_name', 'created_at']

class CourseDetailSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    author = UserSerializer(read_only=True)
    lessons = LessonSerializer(many=True, read_only=True)
    reviews = serializers.SerializerMethodField()
    enrollment_status = serializers.SerializerMethodField()
    progress = serializers.SerializerMethodField()
    
    class Meta:
        model = Course
        fields = ['id', 'title', 'slug', 'description', 'short_description', 'image', 
                 'level', 'price', 'duration', 'students_count', 'rating', 'category', 
                 'author', 'lessons', 'reviews', 'enrollment_status', 'progress', 
                 'is_published', 'created_at', 'updated_at']
    
    def get_reviews(self, obj):
        reviews = obj.reviews.all()[:5]
        return ReviewSerializer(reviews, many=True).data
    
    def get_enrollment_status(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Enrollment.objects.filter(user=request.user, course=obj).exists()
        return False
    
    def get_progress(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            enrollment = Enrollment.objects.filter(user=request.user, course=obj).first()
            if enrollment:
                return enrollment.progress
        return 0

class EnrollmentSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source='course.title', read_only=True)
    course_image = serializers.ImageField(source='course.image', read_only=True)
    progress_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = Enrollment
        fields = ['id', 'course', 'course_title', 'course_image', 'enrolled_at', 
                 'completed_at', 'progress', 'progress_percentage', 'is_completed']
    
    def get_progress_percentage(self, obj):
        if obj.course.lessons.count() > 0:
            return (obj.progress / obj.course.lessons.count()) * 100
        return 0

class LessonProgressSerializer(serializers.ModelSerializer):
    lesson_title = serializers.CharField(source='lesson.title', read_only=True)
    
    class Meta:
        model = LessonProgress
        fields = ['id', 'lesson', 'lesson_title', 'is_completed', 'completed_at', 'last_position']

class ReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = Review
        fields = ['id', 'user', 'user_name', 'rating', 'comment', 'created_at', 'updated_at']
        read_only_fields = ['user', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

class SearchHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SearchHistory
        fields = ['id', 'query', 'searched_at']