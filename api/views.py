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

from rest_framework.permissions import IsAuthenticatedOrReadOnly
from django.contrib.auth import get_user_model
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
    
    def patch(self, request, *args, **kwargs):
        profile = self.get_object()
        mutable_data = request.data.copy()


        if 'image' in mutable_data:
            if mutable_data['image'] in [None, '', 'null', 'undefined']:
                # Si la imagen es null, vacía o undefined, establecer la imagen por defecto
                profile.image = 'default/default-user.webp'
                profile.save()
                del mutable_data['image']
            elif isinstance(mutable_data['image'], str) and mutable_data['image'].startswith('http'):
                # Si es una URL existente, mantener la imagen actual
                del mutable_data['image']
    
        # Actualizar el perfil
        serializer = self.get_serializer(profile, data=mutable_data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(serializer.data)
 
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
            
            api_models.Notification.objects.create(
                user=following, 
                type="Follow",
                actor=follower,  
                post=None 
            )

            return Response({
                "message": f"Ahora sigues a {following.username}",
                "is_following": True
            }, status=status.HTTP_201_CREATED)


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
        return api_models.Post.objects.filter(category=category, status="Published")
    

class SearchPostsView(generics.ListAPIView):
    serializer_class = api_serializer.PostSerializer
    permission_classes = [AllowAny]
    pagination_class = PostPagination

    def get_queryset(self):
        query = self.request.GET.get('query', '')
        if query:
            return api_models.Post.objects.filter(title__icontains=query, status="Published").order_by('-date')
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
    queryset = api_models.Post.objects.all()
    lookup_field = 'slug'

    def get_object(self):
        try:
            slug = self.kwargs['slug']
            return api_models.Post.objects.get(
                slug=slug,
                status="Published"
            )
        except api_models.Post.DoesNotExist:
            raise Http404("Post no encontrado")


class IncrementPostView(generics.UpdateAPIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        slug = self.kwargs['slug']
        try:
            post = api_models.Post.objects.get(slug=slug, status="Published")
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
                return Response(status=status.HTTP_200_OK)
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



class CommentViewSet(APIView):
    permission_classes = [IsAuthenticated, ]
    
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'post_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                'content': openapi.Schema(type=openapi.TYPE_STRING),
            },
            required=['post_id', 'content']
        ),
        responses={201: api_serializer.CommentSerializer()}
    )
   

    def post(self, request):
        """Crear un nuevo comentario principal"""
        try:
            # Obtener el post al que pertenece el comentario
            post = get_object_or_404(api_models.Post, id=request.data['post_id'])
            
            # Crear el comentario principal
            comment = api_models.Comment.objects.create(
                post=post,
                author=request.user,
                content=request.data['content']
            )
            
            serializer = api_serializer.CommentSerializer(comment, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'post_id',
                openapi.IN_QUERY,
                description="ID del post",
                type=openapi.TYPE_INTEGER,
                required=True
            )
        ],
        responses={200: api_serializer.CommentSerializer(many=True)}
    )
    
    def get(self, request):
        """Obtener todas las respuestas de un comentario"""
        comment_id = request.query_params.get('comment_id')
        if not comment_id:
            return Response(
                {"error": "comment_id es requerido"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        parent_comment = get_object_or_404(api_models.Comment, id=comment_id)
        # Usar comment_replies en lugar de replies
        replies = parent_comment.comment_replies.all()
        
        serializer = api_serializer.CommentSerializer(
            replies, 
            many=True, 
            context={'request': request}
        )
        return Response(serializer.data)
    

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'comment_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                'content': openapi.Schema(type=openapi.TYPE_STRING),
            },
            required=['comment_id', 'content']
        ),
        responses={200: api_serializer.CommentSerializer()}
    )
    def put(self, request):
        """Actualizar un comentario"""
        try:
            comment = get_object_or_404(
                api_models.Comment, 
                id=request.data['comment_id']
            )
            
            comment.content = request.data['content']
            comment.save()
            
            serializer = api_serializer.CommentSerializer(
                comment, 
                context={'request': request}
            )
            return Response(serializer.data)
            
        except Exception as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'comment_id',
                openapi.IN_QUERY,
                description="ID del comentario a eliminar",
                type=openapi.TYPE_INTEGER,
                required=True
            )
        ]
    )

    def delete(self, request):
        """Eliminar un comentario y todas sus respuestas relacionadas de forma permanente"""
        try:
            comment_id = request.query_params.get('comment_id')
            if not comment_id:
                return Response(
                    {"error": "comment_id es requerido"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Obtener el comentario original
            comment = get_object_or_404(api_models.Comment, id=comment_id)

            # Eliminar en una única transacción
            with transaction.atomic():
                # 1. Primero eliminar todas las respuestas relacionadas y sus historiales
                replies = comment.replies.all()
                for reply in replies:
                    # Asegurarnos de eliminar cualquier relación primero
                    reply.replies.clear()  
                    # Eliminar la respuesta completamente
                    api_models.Comment.objects.filter(id=reply.id).delete()

                # 2. Eliminar el comentario principal completamente
                api_models.Comment.objects.filter(id=comment_id).delete()

            return Response(
                {"message": "Comentario y respuestas relacionadas eliminados exitosamente"},
                status=status.HTTP_204_NO_CONTENT
            )

        except Exception as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )


class CommentReplyViewSet(APIView):
    permission_classes = [IsAuthenticated, ]
    
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'comment_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                'content': openapi.Schema(type=openapi.TYPE_STRING),
            },
            required=['comment_id', 'content']
        ),
        responses={201: api_serializer.CommentSerializer()}
    )
    
    def post(self, request):
        """Crear una nueva respuesta a un comentario"""
        try:
            parent_comment = get_object_or_404(
                api_models.Comment, 
                id=request.data['comment_id']
            )
            
            reply = api_models.Comment.objects.create(
                post=parent_comment.post,  
                author=request.user,
                content=request.data['content']
            )
            
            parent_comment.replies.add(reply)
            
            api_models.Notification.objects.create(
                user=parent_comment.author,  
                post=parent_comment.post,
                type="Comment", 
                actor=request.user,
            )
            
            serializer = api_serializer.CommentSerializer(reply, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'post_id',
                openapi.IN_QUERY,
                description="ID del post",
                type=openapi.TYPE_INTEGER,
                required=True
            )
        ],
        responses={200: api_serializer.CommentSerializer(many=True)}
    )

    def get(self, request):
        """Obtener todas las respuestas de un comentario"""
        comment_id = request.query_params.get('comment_id')
        if not comment_id:
            return Response(
                {"error": "comment_id es requerido"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        parent_comment = get_object_or_404(api_models.Comment, id=comment_id)
        replies = parent_comment.replies.all()
        
        serializer = api_serializer.CommentSerializer(
            replies, 
            many=True, 
            context={'request': request}
        )
        return Response(serializer.data)

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'reply_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                'content': openapi.Schema(type=openapi.TYPE_STRING),
            },
            required=['reply_id', 'content']
        ),
        responses={200: api_serializer.CommentSerializer()}
    )
    def put(self, request):
        """Actualizar una respuesta"""
        try:
            reply = get_object_or_404(
                api_models.Comment, 
                id=request.data['reply_id']
            )
            
            # Verificar que sea una respuesta y no un comentario principal
            parent_comments = reply.comment_replies.all()
            if not parent_comments.exists():
                return Response(
                    {"error": "El comentario especificado no es una respuesta"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            reply.content = request.data['content']
            reply.save()
            
            serializer = api_serializer.CommentSerializer(
                reply, 
                context={'request': request}
            )
            return Response(serializer.data)
            
        except Exception as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'reply_id',
                openapi.IN_QUERY,
                description="ID de la respuesta a eliminar",
                type=openapi.TYPE_INTEGER,
                required=True
            )
        ]
    )
    def delete(self, request):
        """Eliminar una respuesta"""
        try:
            reply_id = request.query_params.get('reply_id')
            if not reply_id:
                return Response(
                    {"error": "reply_id es requerido"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            reply = get_object_or_404(api_models.Comment, id=reply_id)
            
            parent_comments = reply.comment_replies.all()
            if not parent_comments.exists():
                return Response(
                    {"error": "El comentario especificado no es una respuesta"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            
            reply.delete()
            return Response(
                {"message": "Respuesta eliminada exitosamente"},
                status=status.HTTP_204_NO_CONTENT
            )
            
        except Exception as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        


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
                return Response(status=status.HTTP_200_OK)
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


class PostsList(generics.ListAPIView):
    serializer_class = api_serializer.PostSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        username = self.kwargs['username']
        user = api_models.User.objects.get(username=username)

        if user:
            return api_models.Post.objects.filter(user=user).order_by("-id")
            
        if self.request.user.is_authenticated:
            return api_models.Post.objects.filter(user=self.request.user).order_by("-id")
            
        return api_models.Post.objects.none()


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
        try:
            noti = api_models.Notification.objects.get(id=noti_id)
            noti.seen = not noti.seen
            noti.save()

            if noti.seen: 
                message = "Marked as read" 
            else: message = "Marked as unread" 
            return Response({"message": message},status=status.HTTP_200_OK) 
        except api_models.Notification.DoesNotExist: 
            return Response({"error": "Notification not found"}, status=status.HTTP_404_NOT_FOUND)


from django.shortcuts import get_object_or_404

class NotificationDeleteAPIView(APIView):    
    def delete(self, request, pk):
        notification = get_object_or_404(api_models.Notification, pk=pk)
        notification.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class DashboardPostCreateAPIView(generics.CreateAPIView):
    serializer_class = api_serializer.PostSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        try:
            # Obtener datos del request
            user_id = request.data.get('user_id')
            category_id = request.data.get('category')
            
            # Verificar que existan usuario y categoría
            try:
                user = api_models.User.objects.get(id=user_id)
                category = api_models.Category.objects.get(id=category_id)
            except api_models.User.DoesNotExist:
                return Response({"error": "Usuario no encontrado"}, status=status.HTTP_404_NOT_FOUND)
            except api_models.Category.DoesNotExist:
                return Response({"error": "Categoría no encontrada"}, status=status.HTTP_404_NOT_FOUND)
            
            # Crear el diccionario de datos para el serializer
            post_data = {
                'user': user.id,
                'title': request.data.get('title'),
                'image': request.data.get('image'),
                'preview': request.data.get('preview'),
                'content': request.data.get('content'),
                'tags': request.data.get('tags'),
                'category': category.id,
                'status': request.data.get('post_status')
            }
            
            # Usar el serializer para validar y crear el post
            serializer = self.get_serializer(data=post_data)
            serializer.is_valid(raise_exception=True)
            post = serializer.save()
            
            return Response({
                "message": "Post Created Successfully",
                "post": {
                    "id": post.id,
                    "slug": post.slug,
                    "title": post.title
                }
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)



# Views.py
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
        
        # Obtener datos del request
        title = request.data.get('title')
        image = request.data.get('image')
        preview = request.data.get('preview')  # Cambiado de 'description' a 'preview'
        content = request.data.get('content')  # Agregado el campo content
        tags = request.data.get('tags')
        category_id = request.data.get('category')
        post_status = request.data.get('post_status')

        try:
            category = api_models.Category.objects.get(id=category_id)
            
            # Actualizar los campos
            post_instance.title = title
            if image != "undefined":
                post_instance.image = image
            post_instance.preview = preview  # Cambiado de description a preview
            post_instance.content = content  # Agregado el content
            post_instance.tags = tags
            post_instance.category = category
            post_instance.status = post_status
            
            post_instance.save()
            
            return Response({
                "message": "Post Updated Successfully",
                "post": {
                    "id": post_instance.id,
                    "title": post_instance.title,
                    "preview": post_instance.preview,
                    "content": post_instance.content,
                    "image": post_instance.image.url if post_instance.image else None
                }
            }, status=status.HTTP_200_OK)
            
        except api_models.Category.DoesNotExist:
            return Response(
                {"error": "Category not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )