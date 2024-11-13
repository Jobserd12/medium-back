from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView # type: ignore
from api import views 

urlpatterns = [
    path('user/token/', views.MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('user/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('user/register/', views.RegisterView.as_view(), name='auth_register'),
    path('user/profile/<user_id>/', views.ProfileView.as_view(), name='user_profile'),
    path('follow/<int:user_id>/', views.FollowUserView.as_view(), name='follow-user'), 
    path('unfollow/<int:user_id>/', views.UnfollowUserView.as_view(), name='unfollow-user'),
                                                                                        
    # Post Endpoints
    #!! Mejorar ruta
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
    
    # Dashboard APIS
    path('author/dashboard/stats/<user_id>/', views.DashboardStats.as_view()),
    path('author/dashboard/post-list/<user_id>/', views.DashboardPostLists.as_view()),
    path('author/dashboard/comment-list/', views.DashboardCommentLists.as_view()),
    
    path('author/dashboard/noti-list/<user_id>/', views.DashboardNotificationLists.as_view()),
    
    path('notifications/<int:pk>/', views.NotificationDeleteAPIView.as_view(), name='notification-delete'),

    path('author/dashboard/noti-mark-seen/', views.DashboardMarkNotiSeenAPIView.as_view()),
    path('author/dashboard/reply-comment/', views.DashboardPostCommentAPIView.as_view()),
    
    path('author/dashboard/post-create/', views.DashboardPostCreateAPIView.as_view()),
    path('author/dashboard/post-detail/<user_id>/<post_id>/', views.DashboardPostEditAPIView.as_view()),

]
