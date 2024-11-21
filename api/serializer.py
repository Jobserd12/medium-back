from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from api import models as api_models

# Serializador personalizado que hereda de TokenObtainPairSerializer
class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        # Obtiene el token por el metodo get_token de la clase padre
        token = super().get_token(user)

        token['full_name'] = user.full_name
        token['email'] = user.email
        token['username'] = user.username
        # try:
        #     token['vendor_id'] = user.vendor.id
        # except:
        #     token['vendor_id'] = 0

        # ...

        # Return the token with custom claims
        return token



class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = api_models.User
        fields = ('full_name', 'email',  'password', 'password2')

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})

        return attrs

    def create(self, validated_data):
        user = api_models.User.objects.create(
            full_name=validated_data['full_name'],
            email=validated_data['email'],
        )
        email_username, mobile = user.email.split('@')
        user.username = email_username

        user.set_password(validated_data['password'])
        user.save()

        return user

class UserSerializer(serializers.ModelSerializer):

    class Meta:
        model = api_models.User
        fields = '__all__'

class ProfileSerializer(serializers.ModelSerializer):

    class Meta:
        model = api_models.Profile
        fields = '__all__'

    # def to_representation(self, instance):
    #     response = super().to_representation(instance)
    #     response['user'] = UserSerializer(instance.user).data
    #     return response

# class PasswordResetSerializer(serializers.Serializer):
#     email = serializers.EmailField()


class FollowSerializer(serializers.ModelSerializer):
    followers_count = serializers.IntegerField(source='followers.count', read_only=True)
    following_count = serializers.IntegerField(source='following.count', read_only=True)
    followers = serializers.SerializerMethodField()
    following = serializers.SerializerMethodField()

    class Meta:
        model = api_models.User
        fields = ['id', 'username', 'email', 'full_name', 'followers_count', 'following_count', 'followers', 'following']

    def get_followers(self, obj):
        return [follower.follower.username for follower in obj.followers.all()]

    def get_following(self, obj):
        return [follow.following.username for follow in obj.following.all()]

    

class CategorySerializer(serializers.ModelSerializer):
    post_count = serializers.SerializerMethodField()

    def get_post_count(self, category):
            return category.posts.count()
        
    class Meta:
        model = api_models.Category
        fields = ['id', 'name', 'slug', 'post_count']


# class CategorySerializer(serializers.ModelSerializer):
#     post_count = serializers.SerializerMethodField()

#     def get_post_count(self, category):
#         return category.posts.count()
    
#     class Meta:
#         model = api_models.Category
#         fields = [
#             "id",
#             "title",
#             "image",
#             "slug",
#             "post_count",
#         ]

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = api_models.Tag
        fields = ['id', 'name', 'slug']

class PostContentBlockSerializer(serializers.ModelSerializer):
    block_type = serializers.ChoiceField(
        choices=api_models.PostContentBlock.BLOCK_TYPES, 
        required=True,
        default='text'  # Valor por defecto si no se proporciona
    )
    order = serializers.IntegerField(default=0)

    class Meta:
        model = api_models.PostContentBlock
        fields = [
            'id',
            'block_type',
            'order',
            'text_content',
            'text_style',
            'image',
            'image_caption',
            'video_url',
            'video_platform'
        ]
        extra_kwargs = {
            'text_content': {'required': False},
            'image': {'required': False},
            'video_url': {'required': False}
        }

    def validate(self, data):
        # Validaciones específicas según el tipo de bloque
        block_type = data.get('block_type')
        
        if block_type == 'text' and not data.get('text_content'):
            data['text_content'] = ''
        
        if block_type == 'image' and not data.get('image'):
            raise serializers.ValidationError("Image is required for image blocks")
        
        if block_type == 'video' and not data.get('video_url'):
            raise serializers.ValidationError("Video URL is required for video blocks")
        
        return data

class PostSerializer(serializers.ModelSerializer):
    content_blocks = PostContentBlockSerializer(many=True, required=False)
    category = CategorySerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    
    class Meta:
        model = api_models.Post
        fields = [
            'id', 
            'title', 
            'short_description', 
            'featured_image', 
            'status', 
            'slug', 
            'views_count', 
            'likes_count', 
            'created_at', 
            'updated_at', 
            'published_at', 
            'user', 
            'category', 
            'tags',
            'content_blocks'
        ]
        read_only_fields = ['slug', 'views_count', 'likes_count', 'created_at', 'updated_at', 'published_at']

    def create(self, validated_data):
        # Extraer bloques de contenido del contexto
        content_blocks_data = self.context.get('content_blocks', [])
        
        # Si no hay bloques de contenido, crear uno predeterminado
        if not content_blocks_data:
            content_blocks_data = [{
                'block_type': 'text',
                'text_content': validated_data.get('content', ''),
                'order': 0
            }]
        
        # Eliminar 'content' de los datos validados si existe
        validated_data.pop('content', None)
        
        # Crear el post
        post = super().create(validated_data)
        
        # Crear bloques de contenido
        for block_data in content_blocks_data:
            block_data['post'] = post
            # Usar el serializador para crear y validar cada bloque
            block_serializer = PostContentBlockSerializer(data=block_data)
            block_serializer.is_valid(raise_exception=True)
            block_serializer.save()
        
        return post

    def update(self, instance, validated_data):
        # Lógica similar para la actualización
        content_blocks_data = self.context.get('content_blocks', [])
        
        # Actualizar campos del post
        instance.title = validated_data.get('title', instance.title)
        # ... otros campos ...

        # Eliminar bloques de contenido existentes
        instance.content_blocks.all().delete()
        
        # Crear nuevos bloques de contenido
        for block_data in content_blocks_data:
            block_data['post'] = instance
            block_serializer = PostContentBlockSerializer(data=block_data)
            block_serializer.is_valid(raise_exception=True)
            block_serializer.save()
        
        return instance

# class CategorySerializer(serializers.ModelSerializer):
#     post_count = serializers.SerializerMethodField()

#     def get_post_count(self, category):
#         return category.posts.count()
    
#     class Meta:
#         model = api_models.Category
#         fields = [
#             "id",
#             "title",
#             "image",
#             "slug",
#             "post_count",
#         ]

    # def __init__(self, *args, **kwargs):
    #     super(CategorySerializer, self).__init__(*args, **kwargs)
    #     request = self.context.get('request')
    #     if request and request.method == 'POST':
    #         self.Meta.depth = 0
    #     else:
    #         self.Meta.depth = 3


class CommentSerializer(serializers.ModelSerializer):
    user_profile = ProfileSerializer(source='post.user.profile') 

    class Meta:
        model = api_models.Comment
        fields = ['id', 'name', 'comment', 'user_profile', 'date', 'reply'] 

    def __init__(self, *args, **kwargs):
        super(CommentSerializer, self).__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and request.method == 'POST':
            self.Meta.depth = 0
        else:
            self.Meta.depth = 0


class BookmarkSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = api_models.Bookmark
        fields = "__all__"


    def __init__(self, *args, **kwargs):
        super(BookmarkSerializer, self).__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and request.method == 'POST':
            self.Meta.depth = 0
        else:
            self.Meta.depth = 2
    

# class PostSerializer(serializers.ModelSerializer):
#     comments = CommentSerializer(many=True)
#     bookmarks = BookmarkSerializer(many=True, source='bookmark_set')

#     class Meta:
#         model = api_models.Post
#         fields = "__all__"

#     def __init__(self, *args, **kwargs):
#         super(PostSerializer, self).__init__(*args, **kwargs)
#         request = self.context.get('request')
#         if request and request.method == 'POST':
#             self.Meta.depth = 0
#         else:
#             self.Meta.depth = 3


class NotificationSerializer(serializers.ModelSerializer):  
    actor_username = serializers.CharField(source='actor.username', read_only=True) 
    actor_profile = serializers.ImageField(source='actor.profile.image', read_only=True) 

    class Meta:
        model = api_models.Notification
        exclude = ['user', "actor"] 
        
    def __init__(self, *args, **kwargs):
        super(NotificationSerializer, self).__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and request.method == 'POST':
            self.Meta.depth = 0
        else:
            self.Meta.depth = 1


class AuthorStats(serializers.Serializer):
    views = serializers.IntegerField(default=0)
    posts = serializers.IntegerField(default=0)
    likes = serializers.IntegerField(default=0)
    bookmarks = serializers.IntegerField(default=0)