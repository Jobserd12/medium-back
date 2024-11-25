from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView # type: ignore
from api import views 

urlpatterns = [
    path('user/token/', views.MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('user/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('user/register/', views.RegisterView.as_view(), name='auth_register'),
    path('user/profile/<str:username>/', views.ProfileView.as_view(), name='user_profile'),
    path('follow-toggle/<int:user_id>/', views.FollowToggleView.as_view(), name='follow-user'), 
                                    
    # Post Endpoints
    path('post/category/list/', views.CategoryListAPIView.as_view()),
    path('post/category/posts/<category_slug>/', views.PostCategoryListAPIView.as_view()),
    path('post/lists/', views.PostListAPIView.as_view()),
    path('post/list-popular/', views.PopularPostsAPIView.as_view()),
    path('post/detail/<slug>/', views.PostDetailAPIView.as_view()),
    path('post/increment-view/<slug>/', views.IncrementPostView.as_view()),
    path('post/search/', views.SearchPostsView.as_view()),

    path('admin/posts/<str:username>/', views.PostsList.as_view()), 
    path('admin/post/like-post/', views.LikePostAPIView.as_view()),
    path('admin/post/bookmark-post/', views.BookmarkPostAPIView.as_view()),
    path('admin/stats/<user_id>/', views.DashboardStats.as_view()),
    path('admin/comment-list/', views.DashboardCommentLists.as_view()),
    path('admin/noti-list/<user_id>/', views.DashboardNotificationLists.as_view()),
    path('admin/notifications/<int:pk>/', views.NotificationDeleteAPIView.as_view(), name='notification-delete'),
    path('admin/noti-mark-seen/', views.DashboardMarkNotiSeenAPIView.as_view()),
    
    path('admin/post/comments/', views.CommentViewSet.as_view(), name='comments'),
    path('admin/post/reply-comments/', views.CommentReplyViewSet.as_view()),

    path('admin/post-create/', views.DashboardPostCreateAPIView.as_view()),
    path('admin/post-detail/<user_id>/<post_id>/', views.DashboardPostEditAPIView.as_view()),

]
