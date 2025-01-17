import uuid
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, Group, Permission
from django.db import models

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, name=None, auth_provider=None, is_email_confirmed=False):
        if not email:
            raise ValueError('Users must have an email address')

        user = self.model(
            email=self.normalize_email(email),
            name=name,
            is_email_confirmed=is_email_confirmed,
        )
        if auth_provider:
            user.auth_provider = auth_provider

        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()  # Sets a password that will never validate
            
        user.save(using=self._db)
        return user

    def create_auth0_user(self, auth0_id, email, name, picture, full_request, auth_provider, is_email_confirmed):
        user = self.create_user(
            email,
            password=None,
            name=name,
            auth_provider=auth_provider,
            is_email_confirmed=is_email_confirmed,
        )
        user.auth0_id = auth0_id
        user.picture = picture
        user.full_request = full_request
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, name=None):
        user = self.create_user(
            email,
            password=password,
            name=name,
            is_email_confirmed=True,
        )
        user.is_admin = True
        user.save(using=self._db)
        return user

class User(AbstractBaseUser):
    class AuthProviders(models.TextChoices):
        EMAIL = 'email'
        GOOGLE = 'google'
        GITHUB = 'github'

    id = models.UUIDField(default=uuid.uuid4, primary_key=True, editable=False)
    auth0_id = models.CharField(max_length=250, null=True, blank=True)
    full_request = models.JSONField(default=dict, blank=True, null=True)
    picture = models.URLField(max_length=2000, default='', blank=True, null=True)
    email = models.EmailField(
        verbose_name='email address',
        max_length=255,
        unique=True,
    )
    groups = models.ManyToManyField(
      Group,
      verbose_name='groups',
      blank=True,
      help_text='The groups this user belongs to. A user can belong to multiple groups.',
      related_name='users',
      related_query_name='user'
    )
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    name = models.CharField(max_length=250, null=False, blank=False)
    is_email_confirmed = models.BooleanField(default=False)
    auth_provider = models.CharField(
        max_length=50, 
        blank=False,
        null=False,
        choices=AuthProviders.choices, 
        default=AuthProviders.EMAIL
    )

    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)
    last_login = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    def __str__(self):
        return self.email

    def has_perm(self, perm, obj=None):
        if self.is_admin:
            return True
        
        if Permission.objects.filter(
            group__user=self,
            codename=perm.split('.')[1],
            content_type__app_label=perm.split('.')[0]
        ).exists():
            return True

    def has_module_perms(self, app_label):
        return True

    @property
    def is_staff(self):
        return self.is_admin

    @property
    def is_superuser(self):
        return self.is_admin
