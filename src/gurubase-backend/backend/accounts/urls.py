from django.urls import path
from accounts import views as accounts_views

urlpatterns = [
    path('auth0-user-login/', accounts_views.auth0_user_login, name='auth0_user_login'),
]
