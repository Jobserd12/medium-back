from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView # type: ignore
from api import views
from rest_framework.routers import DefaultRouter

# Create a router for the new PostViewSet
router = DefaultRouter()
router.register(r'posts/manage', views.PostViewSet, basename='post-manage')

urlpatterns = [
    # Existing authentication and user routes
    path('user/token/', views.MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('user/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('user/register/', views.RegisterView.as_view(), name='auth_register'),
    path('user/profile/<str:username>/', views.ProfileView.as_view(), name='user_profile'),
    path('follow-toggle/<int:user_id>/', views.FollowToggleView.as_view(), name='follow-user'),

    # Existing post-related routes
    path('post/category/list/', views.CategoryListAPIView.as_view()),
    path('post/category/posts/<category_slug>/', views.PostCategoryListAPIView.as_view()),
    path('post/lists/', views.PostListAPIView.as_view()),
    path('post/list-popular/', views.PopularPostsAPIView.as_view()),
    path('post/detail/<slug>/', views.PostDetailAPIView.as_view()),
    path('post/increment-view/<slug>/', views.IncrementPostView.as_view()),
    path('post/search/', views.SearchPostsView.as_view()),
    path('post/like-post/', views.LikePostAPIView.as_view()),
    path('post/comment-post/', views.PostCommentAPIView.as_view()),
    path('post/bookmark-post/', views.BookmarkPostAPIView.as_view()),

    # New routes for post management
    path('posts/autosave/', views.PostViewSet.as_view({'post': 'autosave_post'}), name='post-autosave'),
    path('posts/update-status/<slug>/', views.PostViewSet.as_view({'patch': 'update_post_status'}), name='post-update-status'),

    # Existing dashboard routes
    path('author/dashboard/stats/<user_id>/', views.DashboardStats.as_view()),
    path('author/dashboard/post-list/<user_id>/', views.DashboardPostLists.as_view()),
    path('author/dashboard/comment-list/', views.DashboardCommentLists.as_view()),
    path('author/dashboard/noti-list/<user_id>/', views.DashboardNotificationLists.as_view()),
    path('notifications/<int:pk>/', views.NotificationDeleteAPIView.as_view(), name='notification-delete'),
    path('author/dashboard/noti-mark-seen/', views.DashboardMarkNotiSeenAPIView.as_view()),
    path('author/dashboard/reply-comment/', views.DashboardPostCommentAPIView.as_view()),
    
    # Include the router URLs for additional post management endpoints
    path('', include(router.urls)),
]