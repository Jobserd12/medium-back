from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models.signals import post_save
from django.utils.html import mark_safe
from django.utils.text import slugify

from django.utils.html import strip_tags
from django.utils import timezone
from shortuuid.django_fields import ShortUUIDField
import shortuuid

class User(AbstractUser):
    username = models.CharField(unique=True, max_length=100)
    email = models.EmailField(unique=True) 
    full_name = models.CharField(max_length=100, null=True, blank=True)
    otp = models.CharField(max_length=100, null=True, blank=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        db_table = 'user' 

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
        db_table = 'follow'

    def __str__(self):
        return f"{self.follower} follows {self.following}"



class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    image = models.FileField(upload_to="image", default="default/default-user.webp", null=True, blank=True)
    full_name = models.CharField(max_length=100, null=True, blank=True)
    bio = models.TextField(max_length=160, null=True, blank=True, default="This user prefers to keep an air of mystery about them.") 
    country = models.CharField(max_length=100, null=True, blank=True)
    facebook = models.CharField(max_length=100, null=True, blank=True)
    twitter = models.CharField(max_length=100, null=True, blank=True)
    instagram = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        if self.full_name:
            return str(self.full_name)
        else:
            return str(self.user.full_name)
    
    class Meta:
        db_table = 'profile' 

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
        verbose_name_plural = "Categories" 
        db_table = 'category' 

    def save(self, *args, **kwargs): 
        if self.slug == "" or self.slug == None: 
            self.slug = slugify(self.name)
        super(Category, self).save(*args, **kwargs)  

    def post_count(self): 
        return Post.objects.filter(category=self).count()  


class Post(models.Model):
    STATUS = ( 
        ("Published", "Published"), 
        ("Draft", "Draft"),
        ("Disabled", "Disabled"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=100) 
    image = models.FileField(upload_to="image", default="default/default-image-post.webp", null=True, blank=True)
    preview = models.TextField(null=True, blank=True, max_length=200) 
    content = models.TextField(null=False, blank=False)
    tags = models.CharField(max_length=100)  
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='posts')
    status = models.CharField(max_length=100, choices=STATUS, default="Active")
    view = models.IntegerField(default=0)
    likes = models.ManyToManyField(User, blank=True, related_name="likes_user")
    slug = models.SlugField(unique=True, null=True, blank=True)
    date = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return self.title
    
    class Meta:
        db_table = 'post' 
        verbose_name_plural = "Post"

    def save(self, *args, **kwargs):
        if not self.slug:  # Cambiado para mayor claridad
            self.slug = slugify(self.title) + "-" + shortuuid.uuid()[:2]
        if not self.preview: 
            self.preview = strip_tags(self.content)[:200]
        super().save(*args, **kwargs)

    def comments(self):
        return Comment.objects.filter(post=self).order_by("-id")


class Comment(models.Model):
    post = models.ForeignKey('Post', on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='authored_comments', null=True, blank=True)
    content = models.CharField(max_length=500, null=True, blank=True)  # Agregar null=True temporalmente
    replies = models.ManyToManyField('self', symmetrical=False, blank=True, related_name='comment_replies')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'comment'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Comment {self.author.username} en {self.post.title}"


class Bookmark(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.post.title} - {self.user.username}"
    
    class Meta:
        db_table = 'bookmark' 
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
        db_table = 'notification' 
    
    def __str__(self):
        if self.post:
            return f"{self.type} - {self.post.title}"
        else:
            return "Notification"
        
        
        