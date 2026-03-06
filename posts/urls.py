from django.urls import path
from .views import (
    register_view, login_view, get_users,
    get_posts, create_post,
    create_text_post, create_image_post, create_video_post, create_link_post,
    get_comments, create_comment,
    like_post, unlike_post,
    get_post_comments, add_comment_to_post, delete_comment,
    news_feed  # Add this import
)

urlpatterns = [
    # Authentication
    path('register/', register_view, name='register'),
    path('login/', login_view, name='login'),
    
    # Users
    path('users/', get_users, name='users'),
    
    # News Feed
    path('feed/', news_feed, name='news_feed'),
    
    # Posts - Factory Pattern endpoints
    path('posts/', get_posts, name='posts'),
    path('posts/create/', create_post, name='create_post'),
    path('posts/create/text/', create_text_post, name='create_text_post'),
    path('posts/create/image/', create_image_post, name='create_image_post'),
    path('posts/create/video/', create_video_post, name='create_video_post'),
    path('posts/create/link/', create_link_post, name='create_link_post'),
    
    # Likes
    path('posts/<int:post_id>/like/', like_post, name='like_post'),
    path('posts/<int:post_id>/unlike/', unlike_post, name='unlike_post'),
    
    # Comments
    path('comments/', get_comments, name='comments'),
    path('comments/create/', create_comment, name='create_comment'),
    path('posts/<int:post_id>/comments/', get_post_comments, name='get_post_comments'),
    path('posts/<int:post_id>/comments/add/', add_comment_to_post, name='add_comment_to_post'),
    path('comments/<int:comment_id>/delete/', delete_comment, name='delete_comment'),
]