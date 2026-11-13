from django.urls import path
from .views import *


app_name = 'chat'

urlpatterns = [
    path('', inbox, name='inbox'),
    path('sync/', sync, name='sync'),
    path('new/<int:item_pk>/', new_conversation, name='new'),
    path('<int:pk>/', detail, name='detail'),
    path('<int:pk>/send/', send, name='send'),
]