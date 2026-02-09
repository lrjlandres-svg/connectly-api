from django.urls import path
from .views import (
    register_view, login_view, get_users,
    get_posts, create_post,
    create_text_post, create_image_post, create_video_post, create_link_post,
    get_comments, create_comment
)

urlpatterns = [
    # Authentication
    path('register/', register_view, name='register'),
    path('login/', login_view, name='login'),
    
    # Users
    path('users/', get_users, name='users'),
    
    # Posts - Factory Pattern endpoints
    path('posts/', get_posts, name='posts'),
    path('posts/create/', create_post, name='create_post'),
    path('posts/create/text/', create_text_post, name='create_text_post'),
    path('posts/create/image/', create_image_post, name='create_image_post'),
    path('posts/create/video/', create_video_post, name='create_video_post'),
    path('posts/create/link/', create_link_post, name='create_link_post'),
    
    # Comments
    path('comments/', get_comments, name='comments'),
    path('comments/create/', create_comment, name='create_comment'),
]