from django.contrib import admin
from .models import (
    Category, Course, Lesson, Video, Resource, 
    Enrollment, LessonProgress, Review, SearchHistory
)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'created_at']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']

class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 1
    fields = ['title', 'order', 'duration', 'is_free']

class ResourceInline(admin.TabularInline):
    model = Resource
    extra = 1

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'level', 'price', 'students_count', 'rating', 'is_published']
    list_filter = ['category', 'level', 'is_published']
    search_fields = ['title', 'description']
    prepopulated_fields = {'slug': ('title',)}
    inlines = [LessonInline]
    readonly_fields = ['students_count', 'rating']

@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'order', 'duration', 'is_free']
    list_filter = ['course', 'is_free']
    search_fields = ['title']
    inlines = [ResourceInline]

@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ['title', 'lesson', 'duration', 'views_count']

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ['user', 'course', 'enrolled_at', 'progress', 'is_completed']
    list_filter = ['course', 'is_completed']

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['user', 'course', 'rating', 'created_at']
    list_filter = ['course', 'rating']

@admin.register(SearchHistory)
class SearchHistoryAdmin(admin.ModelAdmin):
    list_display = ['user', 'query', 'searched_at']
    list_filter = ['user']