from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .forms import *

app_name = 'myapp'

urlpatterns =[
    path('', views.home, name='home'),
    path('contact/', views.contact, name='contact'),
    path('signup/', views.signup, name ='signup'),
    path('login/', auth_views.LoginView.as_view(template_name='login.html', authentication_form =LoginForm), name="login"),
]