from itertools import count
from django.db.models import Count, F
from django.shortcuts import render
from django.http import JsonResponse
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.db.models import Sum
from django.db import transaction

from rest_framework import status
from rest_framework.decorators import api_view, APIView
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.pagination import PageNumberPagination
from rest_framework.exceptions import NotFound

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from datetime import datetime

import json
import random

from api import serializer as api_serializer
from api import models as api_models

class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = api_serializer.MyTokenObtainPairSerializer


class RegisterView(generics.CreateAPIView): 
    queryset = api_models.User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = api_serializer.RegisterSerializer



class ProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = (AllowAny,)
    serializer_class = api_serializer.ProfileSerializer

    def get_object(self):
        username = self.kwargs['username']
        user = api_models.User.objects.get(username=username)
        profile = api_models.Profile.objects.get(user=user)
        return profile

    def retrieve(self, request, *args, **kwargs):
        profile = self.get_object()
        serializer = self.get_serializer(profile)

        # Obtener los datos de seguidores y seguidos
        follow_serializer = api_serializer.FollowSerializer(profile.user)

        # Combinar los datos del perfil y los datos de seguidores/seguidos
        data = serializer.data
        data.update({
            "followers_count": follow_serializer.data['followers_count'],
            "following_count": follow_serializer.data['following_count'],
            "followers": follow_serializer.data['followers'],
            "following": follow_serializer.data['following']
        })
        return Response(data)

 
class UserFollowView(generics.RetrieveAPIView): 
    permission_classes = (IsAuthenticated,) 
    serializer_class = api_serializer.FollowSerializer 
    
    def get_object(self): 
        user_id = self.kwargs['user_id'] 
        user = api_models.User.objects.get(id=user_id) 
        return user
    

class FollowToggleView(generics.GenericAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = api_serializer.FollowSerializer

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        follower = request.user
        target_user_id = self.kwargs.get('user_id')

        # Validar que no se siga a sí mismo
        if str(follower.id) == str(target_user_id):
            return Response({
                "error": "No puedes seguirte a ti mismo"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Obtener usuario objetivo
        following = get_object_or_404(api_models.User, id=target_user_id)

        try:
            # Existe la relación de seguimiento?
            follow_relation = api_models.Follow.objects.select_for_update().get(
                follower=follower,
                following=following
            )
            # Eliminar (unfollow)
            follow_relation.delete()
            return Response({
                "message": f"Dejaste de seguir a {following.username}",
                "is_following": False
            }, status=status.HTTP_200_OK)
            
        except api_models.Follow.DoesNotExist:
            # Si no existe, crear nueva relación (follow)
            api_models.Follow.objects.create(
                follower=follower,
                following=following
            )
            return Response({
                "message": f"Ahora sigues a {following.username}",
                "is_following": True
            }, status=status.HTTP_201_CREATED)


# class FollowUserView(generics.CreateAPIView):
#     permission_classes = (IsAuthenticated,) 
#     serializer_class = api_serializer.FollowSerializer

#     def post(self, request, *args, **kwargs):
#         user_id = self.kwargs['user_id']
#         follower = request.user
#         try:
#             following = api_models.User.objects.get(id=user_id)
#         except api_models.User.DoesNotExist:
#             return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        
#         if api_models.Follow.objects.filter(follower=follower, following=following).exists():
#             return Response({"message": "You are already following this user"}, status=status.HTTP_400_BAD_REQUEST)
        
#         follow = api_models.Follow.objects.create(follower=follower, following=following)
#         return Response({"message": "Followed successfully"}, status=status.HTTP_201_CREATED)


# class UnfollowUserView(generics.DestroyAPIView):
#     permission_classes = (IsAuthenticated,) 
#     serializer_class = api_serializer.FollowSerializer

#     def delete(self, request, *args, **kwargs):
#         user_id = self.kwargs['user_id']
#         follower = request.user
#         try:
#             following = api_models.User.objects.get(id=user_id)
#         except api_models.User.DoesNotExist:
#             return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        
#         try:
#             follow = api_models.Follow.objects.get(follower=follower, following=following)
#         except api_models.Follow.DoesNotExist:
#             return Response({"error": "You are not following this user"}, status=status.HTTP_400_BAD_REQUEST)
        
#         follow.delete()
#         return Response({"message": "Unfollowed successfully"}, status=status.HTTP_200_OK)
   

# def generate_numeric_otp(length=7):
#         # Generate a random 7-digit OTP
#         otp = ''.join([str(random.randint(0, 9)) for _ in range(length)])
#         return otp


# class PasswordEmailVerify(generics.RetrieveAPIView):
#     permission_classes = (AllowAny,)
#     serializer_class = api_serializer.UserSerializer
    
#     def get_object(self):
#         email = self.kwargs['email']
#         user = api_models.User.objects.get(email=email)
        
#         if user:
#             user.otp = generate_numeric_otp()
#             uidb64 = user.pk
            
#              # Generate a token and include it in the reset link sent via email
#             refresh = RefreshToken.for_user(user)
#             reset_token = str(refresh.access_token)

#             # Store the reset_token in the user model for later verification
#             user.reset_token = reset_token
#             user.save()

#             link = f"http://localhost:5173/create-new-password?otp={user.otp}&uidb64={uidb64}&reset_token={reset_token}"
            
#             merge_data = {
#                 'link': link, 
#                 'username': user.username, 
#             }
#             subject = f"Password Reset Request"
#             text_body = render_to_string("email/password_reset.txt", merge_data)
#             html_body = render_to_string("email/password_reset.html", merge_data)
            
#             msg = EmailMultiAlternatives(
#                 subject=subject, from_email=settings.FROM_EMAIL,
#                 to=[user.email], body=text_body
#             )
#             msg.attach_alternative(html_body, "text/html")
#             msg.send()
#         return user
    

# class PasswordChangeView(generics.CreateAPIView):
#     permission_classes = (AllowAny,)
#     serializer_class = api_serializer.UserSerializer
    
#     def create(self, request, *args, **kwargs):
#         payload = request.data
        
#         otp = payload['otp']
#         uidb64 = payload['uidb64']
#         password = payload['password']

        

#         user = api_models.User.objects.get(id=uidb64, otp=otp)
#         if user:
#             user.set_password(password)
#             user.otp = ""
#             user.save()
            
#             return Response( {"message": "Password Changed Successfully"}, status=status.HTTP_201_CREATED)
#         else:
#             return Response( {"message": "An Error Occured"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ######################## Post APIs ########################
        
class CategoryListAPIView(generics.ListAPIView):
    serializer_class = api_serializer.CategorySerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return api_models.Category.objects.all()

class PostPagination(PageNumberPagination):
    page_size = 9  
    page_size_query_param = 'page_size'
    max_page_size = 20  

class PostCategoryListAPIView(generics.ListAPIView):
    serializer_class = api_serializer.PostSerializer
    permission_classes = [AllowAny]
    pagination_class = PostPagination 

    def get_queryset(self):
        category_slug = self.kwargs['category_slug'] 
        try:
            category = api_models.Category.objects.get(slug=category_slug)
        except api_models.category.DoesNotExist:
            raise NotFound()
        return api_models.Post.objects.filter(category=category, status="Active")
    

class SearchPostsView(generics.ListAPIView):
    serializer_class = api_serializer.PostSerializer
    permission_classes = [AllowAny]
    pagination_class = PostPagination

    def get_queryset(self):
        query = self.request.GET.get('query', '')
        if query:
            return api_models.Post.objects.filter(title__icontains=query, status="Active").order_by('-date')
        return api_models.Post.objects.none()

    
class PostListAPIView(generics.ListAPIView):
    serializer_class = api_serializer.PostSerializer
    permission_classes = [AllowAny]
    pagination_class = PostPagination 

    def get_queryset(self):
        return api_models.Post.objects.all()
    

class PopularPostsAPIView(generics.ListAPIView):
    serializer_class = api_serializer.PostSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return api_models.Post.objects.annotate(
            popularity_score = (
                Count('likes') * 0.5 + 
                F('view') * 0.3 + 
                Count('bookmark') * 0.2
            )
        ).order_by('-popularity_score')[:6]


class PostDetailAPIView(generics.RetrieveAPIView):
    serializer_class = api_serializer.PostSerializer
    permission_classes = [AllowAny]

    def get_object(self):
        slug = self.kwargs['slug']
        post = api_models.Post.objects.get(slug=slug, status="Active")
        return post


class IncrementPostView(generics.UpdateAPIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        slug = self.kwargs['slug']
        try:
            post = api_models.Post.objects.get(slug=slug, status="Active")
            post.view += 1
            post.save()
            return Response({'status': 'view counted'}, status=status.HTTP_200_OK)
        except api_models.Post.DoesNotExist:
            return Response({'error': 'Post not found'}, status=status.HTTP_404_NOT_FOUND)

class LikePostAPIView(APIView):
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'user_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                'post_id': openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
    )
    
    def post(self, request):
        user_id = request.data.get('user_id')
        post_id = request.data.get('post_id')

        try:
            user = api_models.User.objects.get(id=user_id)
            post = api_models.Post.objects.get(id=post_id)

            # Si el usuario ya dio like al post
            if user in post.likes.all():
                post.likes.remove(user)
                return Response({"message": "Post Disliked"}, status=status.HTTP_200_OK)
            else:
                post.likes.add(user)

                # Crear notificación para el autor
                api_models.Notification.objects.create(
                    user=post.user,
                    post=post,
                    type="Like",
                    actor=user,
                )
                return Response({"message": "Post Liked"}, status=status.HTTP_201_CREATED)

        except api_models.User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        except api_models.Post.DoesNotExist:
            return Response({"error": "Post not found"}, status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PostCommentAPIView(APIView):
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'post_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                'name': openapi.Schema(type=openapi.TYPE_STRING),
                'email': openapi.Schema(type=openapi.TYPE_STRING),
                'comment': openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
    )
    
    def post(self, request):
        post_id = request.data['post_id']
        name = request.data['name']
        email = request.data['email']
        comment = request.data['comment']
        user_id = request.data['user_id']

        user = api_models.User.objects.get(id=user_id)
        post = api_models.Post.objects.get(id=post_id)

        # Create Comment
        api_models.Comment.objects.create(
            post=post,
            name=name,
            email=email,
            comment=comment,
        )

        # Notification
        api_models.Notification.objects.create(
            user=post.user,
            post=post,
            type="Comment",
            actor=user,
        )

        return Response({"message": "Commented Sent"}, status=status.HTTP_201_CREATED)
 
 
 
class BookmarkPostAPIView(APIView):
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'user_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                'post_id': openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
    )
    
    def post(self, request):
        user_id = request.data.get('user_id')
        post_id = request.data.get('post_id')

        try:
            user = api_models.User.objects.get(id=user_id)
            post = api_models.Post.objects.get(id=post_id)

            bookmark = api_models.Bookmark.objects.filter(post=post, user=user).first()
            if bookmark:
                # Eliminar el post de los marcados
                bookmark.delete()
                return Response({"message": "Post Un-Bookmarked"}, status=status.HTTP_200_OK)
            else:
                api_models.Bookmark.objects.create(
                    user=user,
                    post=post
                )

                # Crear notificación
                api_models.Notification.objects.create(
                    user=post.user,
                    post=post,
                    type="Bookmark",
                    actor=user,
                )
                return Response({"message": "Post Bookmarked"}, status=status.HTTP_201_CREATED)

        except api_models.User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        except api_models.Post.DoesNotExist:
            return Response({"error": "Post not found"}, status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ######################## Author Dashboard APIs ########################

class DashboardStats(generics.ListAPIView):
    serializer_class = api_serializer.AuthorStats
    permission_classes = [AllowAny]


    def get_queryset(self):
        user_id = self.kwargs['user_id']
        user = api_models.User.objects.get(id=user_id)

        views = api_models.Post.objects.filter(user=user).aggregate(view=Sum("view"))['view']
        posts = api_models.Post.objects.filter(user=user).count()
        bookmarks = api_models.Bookmark.objects.filter(post__user=user).count()
        
        posts_queryset = api_models.Post.objects.filter(user=user)
        total_likes = sum(post.likes.count() for post in posts_queryset)

        return [{
            "views": views,
            "posts": posts,
            "likes": total_likes,
            "bookmarks": bookmarks,
        }]
    
    def list(self, request, *args, **kwargs):
        querset = self.get_queryset()
        serializer = self.get_serializer(querset, many=True)
        return Response(serializer.data)


class DashboardPostLists(generics.ListAPIView):
    serializer_class = api_serializer.PostSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        user_id = self.kwargs['user_id']
        user = api_models.User.objects.get(id=user_id)

        return api_models.Post.objects.filter(user=user).order_by("-id")


class DashboardCommentLists(generics.ListAPIView):
    serializer_class = api_serializer.CommentSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return api_models.Comment.objects.all()



class DashboardNotificationLists(generics.ListAPIView):
    serializer_class = api_serializer.NotificationSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        user_id = self.kwargs['user_id']
        user = api_models.User.objects.get(id=user_id)

        return api_models.Notification.objects.filter(user=user)


class DashboardMarkNotiSeenAPIView(APIView):
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'noti_id': openapi.Schema(type=openapi.TYPE_INTEGER),
            },
        ),
    )
    
    def post(self, request):
        noti_id = request.data['noti_id']
        noti = api_models.Notification.objects.get(id=noti_id)

        noti.seen = True
        noti.save()

        return Response({"message": "Noti Marked As Seen"}, status=status.HTTP_200_OK)


from django.shortcuts import get_object_or_404

class NotificationDeleteAPIView(APIView):    
    def delete(self, request, pk):
        notification = get_object_or_404(api_models.Notification, pk=pk)
        notification.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)



class DashboardPostCommentAPIView(APIView):
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'comment_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                'reply': openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
    )
    
    #!! ESTA REEMPLAZANDO LOS COMENTAREOS POR EL ACTUAL
    #!! Se rompe al no encontrar el id del comentareo
    
    def post(self, request):
        comment_id = request.data['comment_id']
        reply = request.data['reply']

        comment = api_models.Comment.objects.get(id=comment_id)
        comment.reply = reply
        comment.save()

        return Response({"message": "Comment Response Sent"}, status=status.HTTP_201_CREATED)
    


class DashboardPostCreateAPIView(generics.CreateAPIView):
    serializer_class = api_serializer.PostSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        user_id = request.data.get('user_id')
        title = request.data.get('title')
        image = request.data.get('image')
        description = request.data.get('description')
        tags = request.data.get('tags')
        category_id = request.data.get('category')
        post_status = request.data.get('post_status')

        #!! Agregar excepciones en caso de el usuario o la categoria no exista
        user = api_models.User.objects.get(id=user_id)
        category = api_models.Category.objects.get(id=category_id)

        post = api_models.Post.objects.create(
            user=user,
            title=title,
            image=image,
            description=description,
            tags=tags,
            category=category,
            status=post_status
        )

        return Response({"message": "Post Created Successfully"}, status=status.HTTP_201_CREATED)



class DashboardPostEditAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = api_serializer.PostSerializer
    permission_classes = [AllowAny]

    def get_object(self):
        user_id = self.kwargs['user_id']
        post_id = self.kwargs['post_id']
        user = api_models.User.objects.get(id=user_id)
        return api_models.Post.objects.get(user=user, id=post_id)

    def update(self, request, *args, **kwargs):
        post_instance = self.get_object()

        title = request.data.get('title')
        image = request.data.get('image')
        description = request.data.get('description')
        tags = request.data.get('tags')
        category_id = request.data.get('category')
        post_status = request.data.get('post_status')

        category = api_models.Category.objects.get(id=category_id)

        post_instance.title = title
        if image != "undefined":
            post_instance.image = image
        post_instance.description = description
        post_instance.tags = tags
        post_instance.category = category
        post_instance.status = post_status
        post_instance.save()

        return Response({"message": "Post Updated Successfully"}, status=status.HTTP_200_OK)


# {
#     "title": "New post",
#     "image": "",
#     "description": "lorem",
#     "tags": "tags, here",
#     "category_id": 1,
#     "post_status": "Active"
# }