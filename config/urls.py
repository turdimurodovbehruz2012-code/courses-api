from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from courses import views

router = DefaultRouter()
router.register(r'categories', views.CategoryViewSet)
router.register(r'courses', views.CourseViewSet)
router.register(r'lessons', views.LessonViewSet)
router.register(r'videos', views.VideoViewSet)
router.register(r'enrollments', views.EnrollmentViewSet)
router.register(r'reviews', views.ReviewViewSet)
router.register(r'search', views.SearchViewSet, basename='search')
router.register(r'statistics', views.StatisticsViewSet, basename='statistics')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api/home/', views.home_api, name='home'),
    path('api/video/lesson/<int:lesson_id>/', views.get_video_by_lesson, name='video-by-lesson'),
    path('api-auth/', include('rest_framework.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)