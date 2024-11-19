from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models.signals import post_save
from django.utils.html import mark_safe
from django.utils.text import slugify

from shortuuid.django_fields import ShortUUIDField
import shortuuid

class User(AbstractUser):
    username = models.CharField(unique=True, max_length=100)
    email = models.EmailField(unique=True) 
    full_name = models.CharField(max_length=100, null=True, blank=True)
    otp = models.CharField(max_length=100, null=True, blank=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email
    
    def save(self, *args, **kwargs):
        email_username, mobile = self.email.split("@")
        if self.full_name == "" or self.full_name == None:
            self.full_name = email_username
        if self.username == "" or self.username == None:
            self.username = email_username  
    
        super(User, self).save(*args, **kwargs)


class Follow(models.Model):
    follower = models.ForeignKey(User, related_name="following", on_delete=models.CASCADE)
    following = models.ForeignKey(User, related_name="followers", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('follower', 'following')

    def __str__(self):
        return f"{self.follower} follows {self.following}"




class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    image = models.FileField(upload_to="image", default="default/default-user.jpg", null=True, blank=True)
    full_name = models.CharField(max_length=100, null=True, blank=True)
    bio = models.TextField(null=True, blank=True)
    about = models.TextField(null=True, blank=True)
    author = models.BooleanField(default=False)
    country = models.CharField(max_length=100, null=True, blank=True)
    facebook = models.CharField(max_length=100, null=True, blank=True)
    twitter = models.CharField(max_length=100, null=True, blank=True)
    instagram = models.CharField(max_length=100, null=True, blank=True)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.full_name:
            return str(self.full_name)
        else:
            return str(self.user.full_name)
    

    def save(self, *args, **kwargs):
        if self.full_name == "" or self.full_name == None:
            self.full_name = self.user.full_name
        super(Profile, self).save(*args, **kwargs)

    def thumbnail(self):
        return mark_safe('<img src="/media/%s" width="50" height="50" object-fit:"cover" style="border-radius: 30px; object-fit: cover;" />' % (self.image))
    


# Función que crea un perfil de usuario cuando se crea un nuevo usuario.
def create_user_profile(sender, instance, created, **kwargs):
    if created: 
        Profile.objects.create(user=instance) 

# Función que guarda el perfil de usuario cuando se guarda un usuario existente.
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save() 

# Conecta las señales post_save para crear o guardar un perfil de usuario
post_save.connect(create_user_profile, sender=User)
post_save.connect(save_user_profile, sender=User)




class Category(models.Model):  
    name = models.CharField(max_length=100)  
    slug = models.SlugField(unique=True, null=True, blank=True) 

    def __str__(self):  
        return self.name

    class Meta:
        verbose_name_plural = "Category" 

    def save(self, *args, **kwargs):  # Sobreescribe el método save
        if not self.slug: # Si no hay slug, genera uno a partir del título
            self.slug = slugify(self.name)
        super(Category, self).save(*args, **kwargs)  # Llama al método save original para guardar la instancia

    def post_count(self): 
        return Post.objects.filter(category=self).count()  


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class PostContentBlock(models.Model):
    """
    Modelo para almacenar bloques de contenido de manera flexible
    Permite manejar texto, imágenes, videos y otros tipos de contenido
    """
    BLOCK_TYPES = (
        ('text', 'Text'),
        ('image', 'Image'),
        ('video', 'Video'),
        ('heading', 'Heading'),
        ('quote', 'Quote'),
        ('code', 'Code')
    )

    post = models.ForeignKey('Post', related_name='content_blocks', on_delete=models.CASCADE)
    block_type = models.CharField(max_length=20, choices=BLOCK_TYPES)
    order = models.PositiveIntegerField(default=0)
    
    # Campos para diferentes tipos de contenido
    text_content = models.TextField(null=True, blank=True)
    text_style = models.JSONField(null=True, blank=True)  # Para estilos de texto
    
    # Para imágenes
    image = models.ImageField(
        upload_to='post_images/', 
        null=True, 
        blank=True,
        validators=[FileExtensionValidator(['png', 'jpg', 'jpeg', 'gif', 'webp'])]
    )
    image_caption = models.CharField(max_length=200, null=True, blank=True)
    
    # Para videos
    video_url = models.URLField(null=True, blank=True)
    video_platform = models.CharField(max_length=20, choices=[
        ('youtube', 'YouTube'),
        ('vimeo', 'Vimeo'),
        ('custom', 'Custom Embed')
    ], null=True, blank=True)

    def clean(self):
        # Validaciones específicas según el tipo de bloque
        if self.block_type == 'text' and not self.text_content:
            raise ValidationError('Text content is required for text blocks')
        
        if self.block_type == 'image' and not self.image:
            raise ValidationError('Image is required for image blocks')
        
        if self.block_type == 'video' and not self.video_url:
            raise ValidationError('Video URL is required for video blocks')

    def __str__(self):
        return f"{self.post.title} - {self.block_type} Block"


class Post(models.Model):
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived')
    )

    # Relaciones principales
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    category = models.ForeignKey(
        Category, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='posts'
    )
    tags = models.ManyToManyField(Tag, related_name='posts', blank=True)

    # Campos básicos
    title = models.CharField(max_length=200)
    short_description = models.TextField(max_length=500, null=True, blank=True)
    
    # Imagen representativa
    featured_image = models.ImageField(
        upload_to='featured_images/', 
        null=True, 
        blank=True,
        validators=[FileExtensionValidator(['png', 'jpg', 'jpeg', 'gif', 'webp'])]
    )

    # Metadatos y estado
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='draft'
    )
    
    # SEO y URL
    slug = models.SlugField(unique=True, max_length=255)
    
    # Métricas
    views_count = models.PositiveIntegerField(default=0)
    likes_count = models.PositiveIntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        # Generar slug único
        if not self.slug:
            base_slug = slugify(self.title)
            unique_slug = base_slug
            counter = 1
            while Post.objects.filter(slug=unique_slug).exists():
                unique_slug = f"{base_slug}-{shortuuid.uuid()[:4]}"
                counter += 1
            self.slug = unique_slug

        # Establecer fecha de publicación si cambia a estado publicado
        if self.status == 'published' and not self.published_at:
            self.published_at = timezone.now()

        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Posts"


# class Post(models.Model):
#     STATUS = ( 
#         ("Active", "Active"), 
#         ("Draft", "Draft"),
#         ("Disabled", "Disabled"),
#     )

#     user = models.ForeignKey(User, on_delete=models.CASCADE)
#     profile = models.ForeignKey(Profile, on_delete=models.CASCADE, null=True, blank=True)
#     title = models.CharField(max_length=100)
#     image = models.FileField(upload_to="image", null=True, blank=True)
#     description = models.TextField(null=True, blank=True)
#     tags = models.CharField(max_length=100)
#     category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='posts')
#     status = models.CharField(max_length=100, choices=STATUS, default="Active")
#     view = models.IntegerField(default=0)
#     likes = models.ManyToManyField(User, blank=True, related_name="likes_user")
#     slug = models.SlugField(unique=True, null=True, blank=True)
#     date = models.DateTimeField(auto_now_add=True)
    
#     def __str__(self):
#         return self.title
    
#     class Meta:
#         verbose_name_plural = "Post"

#     def save(self, *args, **kwargs):
#         if self.slug == "" or self.slug == None:
#             self.slug = slugify(self.title) + "-" + shortuuid.uuid()[:2]
#         super(Post, self).save(*args, **kwargs)
    
#     def comments(self):
#         return Comment.objects.filter(post=self).order_by("-id")

    
class UserLike(models.Model):
    """
    Modelo para rastrear likes con más detalle
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'post')

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Actualizar conteo de likes
        self.post.likes_count = self.post.likes.count()
        self.post.save()
        

class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    email = models.CharField(max_length=100)
    comment = models.TextField()
    reply = models.TextField(null=True, blank=True)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.post.title} - {self.name}"
    
    class Meta:
        verbose_name_plural = "Comment"


class Bookmark(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.post.title} - {self.user.username}"
    
    class Meta:
        verbose_name_plural = "Bookmark"


class Notification(models.Model):
    NOTI_TYPE = ( ("Like", "Like"), ("Comment", "Comment"), ("Bookmark", "Bookmark"), ("Follow", "Follow"))
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, null=True, blank=True)
    type = models.CharField(max_length=100, choices=NOTI_TYPE)
    seen = models.BooleanField(default=False)
    date = models.DateTimeField(auto_now_add=True)
    actor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications_actor')

    class Meta:
        verbose_name_plural = "Notification"
    
    def __str__(self):
        if self.post:
            return f"{self.type} - {self.post.title}"
        else:
            return "Notification"
        
        
        