from django.urls import path
from .views import user_list_create, post_list_create, comment_list_create

urlpatterns = [
    path('users/', user_list_create, name='user-list-create'),
    path('posts/', post_list_create, name='post-list-create'),
    path('comments/', comment_list_create, name='comment-list-create'),
]