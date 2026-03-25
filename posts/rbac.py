# posts/rbac.py
from functools import wraps
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import Group

def is_admin(user):
    return user.is_superuser or user.groups.filter(name='admin').exists()

def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
        if not is_admin(request.user):
            return Response({'error': 'Admin privileges required', 'required_role': 'admin'}, 
                          status=status.HTTP_403_FORBIDDEN)
        return view_func(request, *args, **kwargs)
    return wrapper

def check_post_privacy(view_func):
    @wraps(view_func)
    def wrapper(request, post_id, *args, **kwargs):
        from .models import Post
        try:
            post = Post.objects.get(id=post_id)
        except Post.DoesNotExist:
            return Response({'error': 'Post not found'}, status=status.HTTP_404_NOT_FOUND)
        if not post.can_view(request.user):
            return Response({'error': 'Post not found'}, status=status.HTTP_404_NOT_FOUND)
        request.post = post
        return view_func(request, post_id, *args, **kwargs)
    return wrapper