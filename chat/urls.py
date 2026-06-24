from django.urls import path
from .views import *


app_name = 'chat'

urlpatterns = [
    path('', inbox, name='inbox'),
    path('<int:pk>/', detail, name='detail'),
    path('new/<int:item_pk>/', new_conversation, name='new'),
]