from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import Post, Comment, Like, Following
from .serializers import PostSerializer, CommentSerializer
from .factories.post_factory import PostFactory
from .singletons.logger_singleton import LoggerSingleton
from .singletons.config_manager import ConfigManager
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from functools import wraps
from django.contrib.auth.models import Group
from django.core.cache import cache
import hashlib
import json

# Initialize singletons
logger = LoggerSingleton().get_logger()
config = ConfigManager()

# ========== RBAC HELPER FUNCTIONS (MUST BE AT TOP) ==========
def is_admin(user):
    return user.is_superuser or user.groups.filter(name='admin').exists()

def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=401)
        if not is_admin(request.user):
            return Response({'error': 'Admin privileges required'}, status=403)
        return view_func(request, *args, **kwargs)
    return wrapper

def check_post_privacy(view_func):
    @wraps(view_func)
    def wrapper(request, post_id, *args, **kwargs):
        try:
            post = Post.objects.get(id=post_id)
        except Post.DoesNotExist:
            return Response({'error': 'Post not found'}, status=404)
        
        if not post.can_view(request.user):
            return Response({'error': 'Post not found'}, status=404)
        
        request.post = post
        return view_func(request, post_id, *args, **kwargs)
    return wrapper

# ========== AUTHENTICATION ENDPOINTS ==========

@csrf_exempt
@api_view(['POST'])
def register_view(request):
    try:
        username = request.data.get('username')
        email = request.data.get('email')
        password = request.data.get('password')
        
        if not username or not email or not password:
            return Response({'error': 'All fields are required'}, status=400)
        
        if User.objects.filter(username=username).exists():
            return Response({'error': 'Username already exists'}, status=400)
        
        if User.objects.filter(email=email).exists():
            return Response({'error': 'Email already exists'}, status=400)
        
        user = User.objects.create_user(username=username, email=email, password=password)
        logger.info(f"New user registered: {username}")
        
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email
            },
            'message': 'User registered successfully'
        }, status=201)
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        return Response({'error': str(e)}, status=500)

@csrf_exempt
@api_view(['POST'])
def login_view(request):
    try:
        username = request.data.get('username')
        password = request.data.get('password')
        
        user = authenticate(username=username, password=password)
        
        if user is not None:
            logger.info(f"User logged in: {username}")
            refresh = RefreshToken.for_user(user)
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email
                },
                'message': 'Authentication successful'
            }, status=200)
        else:
            logger.warning(f"Failed login attempt for: {username}")
            return Response({'error': 'Invalid credentials'}, status=401)
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return Response({'error': str(e)}, status=500)

# ========== USER ENDPOINTS ==========

@csrf_exempt
@api_view(['GET'])
def get_users(request):
    try:
        users = User.objects.all().values('id', 'username', 'email')
        return Response(list(users), status=200)
    except Exception as e:
        logger.error(f"Get users error: {str(e)}")
        return Response({'error': str(e)}, status=500)

# ========== POST ENDPOINTS ==========

@csrf_exempt
@api_view(['GET'])
def get_posts(request):
    try:
        page = request.GET.get('page', 1)
        page_size = min(max(int(request.GET.get('page_size', 20)), 1), 100)
        
        # Privacy filtering
        if not request.user.is_authenticated:
            posts = Post.objects.filter(privacy='public')
        else:
            posts = Post.objects.filter(
                Q(privacy='public') | Q(author=request.user)
            )
        
        # Optimization + sorting
        posts = posts.select_related('author').prefetch_related('comments', 'likes').order_by('-created_at')
        
        # Paginate
        paginator = Paginator(posts, page_size)
        try:
            paginated_posts = paginator.page(page)
        except (PageNotAnInteger, EmptyPage):
            paginated_posts = paginator.page(1)
        
        serializer = PostSerializer(paginated_posts, many=True)
        return Response({
            'page': paginated_posts.number,
            'page_size': page_size,
            'total_pages': paginator.num_pages,
            'total_posts': paginator.count,
            'posts': serializer.data
        }, status=200)
    except Exception as e:
        logger.error(f"Get posts error: {str(e)}")
        return Response({'error': str(e)}, status=500)

@csrf_exempt
@api_view(['POST'])
def create_post(request):
    try:
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=401)
        
        post_type = request.data.get('post_type', 'text')
        title = request.data.get('title', '')
        content = request.data.get('content', '')
        metadata = request.data.get('metadata', {})
        privacy = request.data.get('privacy', 'public')  # NEW: privacy field
        
        try:
            post = PostFactory.create_post(
                author=request.user,
                post_type=post_type,
                title=title,
                content=content,
                metadata=metadata
            )
            # Set privacy after creation
            if privacy in ['public', 'private']:
                post.privacy = privacy
                post.save()
            
            logger.info(f"Post created by {request.user.username}: {post.id}")
            serializer = PostSerializer(post)
            return Response(serializer.data, status=201)
        except ValueError as e:
            logger.warning(f"Invalid post creation: {str(e)}")
            return Response({'error': str(e)}, status=400)
    except Exception as e:
        logger.error(f"Create post error: {str(e)}")
        return Response({'error': str(e)}, status=500)
    

# Factory shortcut endpoints (simplified - no changes needed for RBAC)
@csrf_exempt
@api_view(['POST'])
def create_text_post(request):
    try:
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=401)
        
        content = request.data.get('content')
        title = request.data.get('title', '')
        
        if not content:
            return Response({'error': 'Content is required'}, status=400)
        
        post = PostFactory.create_text_post(
            author=request.user,
            content=content,
            title=title
        )
        
        # Set privacy if provided
        privacy = request.data.get('privacy', 'public')
        if privacy in ['public', 'private']:
            post.privacy = privacy
            post.save()
        
        logger.info(f"Text post created by {request.user.username}: {post.id}")
        serializer = PostSerializer(post)
        return Response(serializer.data, status=201)
    except Exception as e:
        logger.error(f"Create text post error: {str(e)}")
        return Response({'error': str(e)}, status=500)

@csrf_exempt
@api_view(['POST'])
def create_image_post(request):
    try:
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=401)
        
        image_url = request.data.get('image_url')
        file_size = request.data.get('file_size')
        title = request.data.get('title', '')
        description = request.data.get('description', '')
        
        if not image_url or not file_size:
            return Response({'error': 'image_url and file_size are required'}, status=400)
        
        post = PostFactory.create_image_post(
            author=request.user,
            image_url=image_url,
            file_size=file_size,
            title=title,
            description=description
        )
        
        # Set privacy
        privacy = request.data.get('privacy', 'public')
        if privacy in ['public', 'private']:
            post.privacy = privacy
            post.save()
        
        logger.info(f"Image post created by {request.user.username}: {post.id}")
        serializer = PostSerializer(post)
        return Response(serializer.data, status=201)
    except ValueError as e:
        logger.warning(f"Invalid image post: {str(e)}")
        return Response({'error': str(e)}, status=400)
    except Exception as e:
        logger.error(f"Create image post error: {str(e)}")
        return Response({'error': str(e)}, status=500)

@csrf_exempt
@api_view(['POST'])
def create_video_post(request):
    try:
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=401)
        
        video_url = request.data.get('video_url')
        duration = request.data.get('duration')
        title = request.data.get('title', '')
        description = request.data.get('description', '')
        
        if not video_url or not duration:
            return Response({'error': 'video_url and duration are required'}, status=400)
        
        post = PostFactory.create_video_post(
            author=request.user,
            video_url=video_url,
            duration=duration,
            title=title,
            description=description
        )
        
        # Set privacy
        privacy = request.data.get('privacy', 'public')
        if privacy in ['public', 'private']:
            post.privacy = privacy
            post.save()
        
        logger.info(f"Video post created by {request.user.username}: {post.id}")
        serializer = PostSerializer(post)
        return Response(serializer.data, status=201)
    except ValueError as e:
        logger.warning(f"Invalid video post: {str(e)}")
        return Response({'error': str(e)}, status=400)
    except Exception as e:
        logger.error(f"Create video post error: {str(e)}")
        return Response({'error': str(e)}, status=500)

@csrf_exempt
@api_view(['POST'])
def create_link_post(request):
    try:
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=401)
        
        url = request.data.get('url')
        title = request.data.get('title', '')
        description = request.data.get('description', '')
        
        if not url:
            return Response({'error': 'url is required'}, status=400)
        
        post = PostFactory.create_link_post(
            author=request.user,
            url=url,
            title=title,
            description=description
        )
        
        # Set privacy
        privacy = request.data.get('privacy', 'public')
        if privacy in ['public', 'private']:
            post.privacy = privacy
            post.save()
        
        logger.info(f"Link post created by {request.user.username}: {post.id}")
        serializer = PostSerializer(post)
        return Response(serializer.data, status=201)
    except ValueError as e:
        logger.warning(f"Invalid link post: {str(e)}")
        return Response({'error': str(e)}, status=400)
    except Exception as e:
        logger.error(f"Create link post error: {str(e)}")
        return Response({'error': str(e)}, status=500)

# ========== LIKE ENDPOINTS ==========

@csrf_exempt
@api_view(['POST'])
def like_post(request, post_id):
    try:
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=401)
        
        try:
            post = Post.objects.get(id=post_id)
            # Check if user can view the post before allowing like
            if not post.can_view(request.user):
                return Response({'error': 'Post not found'}, status=404)
        except Post.DoesNotExist:
            logger.warning(f"Like failed: Post {post_id} not found")
            return Response({'error': 'Post not found'}, status=404)
        
        like, created = Like.objects.get_or_create(
            user=request.user,
            post=post
        )
        
        if not created:
            logger.info(f"User {request.user.username} already liked post {post_id}")
            return Response({
                'message': 'You already liked this post',
                'like_count': post.like_count
            }, status=200)
        
        logger.info(f"User {request.user.username} liked post {post_id}")
        return Response({
            'message': 'Post liked successfully',
            'like_count': post.like_count
        }, status=201)
        
    except Exception as e:
        logger.error(f"Like post error: {str(e)}")
        return Response({'error': str(e)}, status=500)

@csrf_exempt
@api_view(['DELETE'])
def unlike_post(request, post_id):
    try:
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=401)
        
        try:
            post = Post.objects.get(id=post_id)
            if not post.can_view(request.user):
                return Response({'error': 'Post not found'}, status=404)
        except Post.DoesNotExist:
            return Response({'error': 'Post not found'}, status=404)
        
        deleted_count, _ = Like.objects.filter(
            user=request.user,
            post=post
        ).delete()
        
        if deleted_count == 0:
            return Response({
                'message': 'You have not liked this post',
                'like_count': post.like_count
            }, status=200)
        
        logger.info(f"User {request.user.username} unliked post {post_id}")
        return Response({
            'message': 'Post unliked successfully',
            'like_count': post.like_count
        }, status=200)
        
    except Exception as e:
        logger.error(f"Unlike post error: {str(e)}")
        return Response({'error': str(e)}, status=500)

# ========== COMMENT ENDPOINTS ==========

@csrf_exempt
@api_view(['GET'])
def get_comments(request):
    try:
        page = request.GET.get('page', 1)
        page_size = min(max(int(request.GET.get('page_size', 50)), 1), 200)
        
        # Optimization: preload authors
        comments = Comment.objects.select_related('author', 'post').order_by('-created_at')
        
        paginator = Paginator(comments, page_size)
        try:
            paginated_comments = paginator.page(page)
        except (PageNotAnInteger, EmptyPage):
            paginated_comments = paginator.page(1)
        
        serializer = CommentSerializer(paginated_comments, many=True)
        return Response({
            'page': paginated_comments.number,
            'page_size': page_size,
            'total_pages': paginator.num_pages,
            'total_comments': paginator.count,
            'comments': serializer.data
        }, status=200)
    except Exception as e:
        logger.error(f"Get comments error: {str(e)}")
        return Response({'error': str(e)}, status=500)

@csrf_exempt
@api_view(['POST'])
def create_comment(request):
    try:
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=401)
        
        text = request.data.get('text')
        post_id = request.data.get('post')
        
        if not text or not post_id:
            return Response({'error': 'Text and post ID are required'}, status=400)
        
        try:
            post = Post.objects.get(id=post_id)
            if not post.can_view(request.user):
                return Response({'error': 'Post not found'}, status=404)
        except Post.DoesNotExist:
            logger.warning(f"Comment creation failed: Post {post_id} not found")
            return Response({'error': 'Post not found'}, status=404)
        
        comment = Comment.objects.create(text=text, author=request.user, post=post)
        logger.info(f"Comment created by {request.user.username} on post {post_id}")
        serializer = CommentSerializer(comment)
        return Response(serializer.data, status=201)
    except Exception as e:
        logger.error(f"Create comment error: {str(e)}")
        return Response({'error': str(e)}, status=500)

@csrf_exempt
@api_view(['GET'])
def get_post_comments(request, post_id):
    try:
        try:
            post = Post.objects.get(id=post_id)
            if not post.can_view(request.user):
                return Response({'error': 'Post not found'}, status=404)
        except Post.DoesNotExist:
            return Response({'error': 'Post not found'}, status=404)
        
        page_size = config.get_setting('DEFAULT_PAGE_SIZE')
        comments = Comment.objects.filter(post=post).order_by('-created_at')[:page_size]
        serializer = CommentSerializer(comments, many=True)
        
        return Response({
            'post_id': post_id,
            'comment_count': post.comment_count,
            'comments': serializer.data
        }, status=200)
        
    except Exception as e:
        logger.error(f"Get post comments error: {str(e)}")
        return Response({'error': str(e)}, status=500)

@csrf_exempt
@api_view(['POST'])
def add_comment_to_post(request, post_id):
    try:
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=401)
        
        try:
            post = Post.objects.get(id=post_id)
            if not post.can_view(request.user):
                return Response({'error': 'Post not found'}, status=404)
        except Post.DoesNotExist:
            logger.warning(f"Comment failed: Post {post_id} not found")
            return Response({'error': 'Post not found'}, status=404)
        
        text = request.data.get('text')
        
        if not text or text.strip() == '':
            return Response({'error': 'Comment text is required'}, status=400)
        
        if len(text) > 1000:
            return Response({'error': 'Comment text cannot exceed 1000 characters'}, status=400)
        
        comment = Comment.objects.create(
            text=text.strip(),
            author=request.user,
            post=post
        )
        
        logger.info(f"User {request.user.username} commented on post {post_id}")
        serializer = CommentSerializer(comment)
        
        return Response({
            'message': 'Comment added successfully',
            'comment': serializer.data,
            'comment_count': post.comment_count
        }, status=201)
        
    except Exception as e:
        logger.error(f"Add comment error: {str(e)}")
        return Response({'error': str(e)}, status=500)

@csrf_exempt
@api_view(['DELETE'])
def delete_comment(request, comment_id):
    """Delete comment (author or admin only)"""
    try:
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=401)
        
        comment = Comment.objects.get(id=comment_id)
        
        # Check permissions: author OR admin
        if comment.author != request.user and not is_admin(request.user):
            return Response({
                'error': 'You can only delete your own comments',
                'required': 'comment author or admin'
            }, status=403)
        
        comment.delete()
        logger.info(f"User {request.user.username} deleted comment {comment_id}")
        return Response({'message': 'Comment deleted successfully'}, status=200)
        
    except Comment.DoesNotExist:
        return Response({'error': 'Comment not found'}, status=404)
    except Exception as e:
        logger.error(f"Delete comment error: {str(e)}")
        return Response({'error': str(e)}, status=500)

# ========== NEWS FEED ENDPOINT ==========

@csrf_exempt
@api_view(['GET'])
def news_feed(request):
    """
    News feed endpoint with sorting, pagination, and privacy enforcement
    Query parameters:
    - page: page number (default: 1)
    - page_size: items per page (default: 20, max: 100)
    - sort: sort order ('newest', 'oldest') (default: 'newest')
    - filter: filter type ('all', 'following', 'liked') (default: 'all')
    """
    try:
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=401)
        
        # Get and normalize parameters
        page = request.GET.get('page', 1)
        page_size = min(max(int(request.GET.get('page_size', 20)), 1), 100)
        sort = request.GET.get('sort', 'newest')
        filter_type = request.GET.get('filter', 'all')
        
        # Create cache key based on user + parameters
        params = json.dumps({
            'user_id': request.user.id,
            'page': page,
            'page_size': page_size,
            'sort': sort,
            'filter': filter_type
        }, sort_keys=True)
        cache_key = f"news_feed_{hashlib.md5(params.encode()).hexdigest()}"
        
        # Check cache first
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info(f"Cache HIT for user {request.user.username} - {cache_key}")
            return Response(cached_data, status=200)
        
        # Build query with privacy enforcement
        base_query = Post.objects.select_related('author').prefetch_related('comments', 'likes')
        
        if filter_type == 'following':
            following_users = Following.objects.filter(follower=request.user).values_list('following', flat=True)
            posts = base_query.filter(
                Q(author__in=following_users, privacy='public') | 
                Q(author=request.user)
            )
        elif filter_type == 'liked':
            liked_post_ids = Like.objects.filter(user=request.user).values_list('post', flat=True)
            posts = base_query.filter(
                Q(id__in=liked_post_ids, privacy='public') |
                Q(id__in=liked_post_ids, author=request.user)
            )
        else:  # 'all'
            posts = base_query.filter(
                Q(privacy='public') | 
                Q(author=request.user)
            )
        
        # Apply sorting
        posts = posts.order_by('created_at' if sort == 'oldest' else '-created_at')
        
        # Paginate
        paginator = Paginator(posts, page_size)
        try:
            paginated_posts = paginator.page(page)
        except (PageNotAnInteger, EmptyPage):
            paginated_posts = paginator.page(1)
        
        # Serialize
        serializer = PostSerializer(paginated_posts, many=True)
        response_data = {
            'page': paginated_posts.number,
            'page_size': page_size,
            'total_pages': paginator.num_pages,
            'total_posts': paginator.count,
            'filter': filter_type,
            'sort': sort,
            'posts': serializer.data,
            'cache_status': 'MISS'  # For debugging
        }
        
        # Cache the response
        cache.set(cache_key, response_data, timeout=300)
        logger.info(f"Cache SET for user {request.user.username} - {cache_key} (Page {page})")
        
        return Response(response_data, status=200)
        
    except Exception as e:
        logger.error(f"News feed error: {str(e)}")
        return Response({'error': str(e)}, status=500)
# ========== PRIVACY-ENFORCED ENDPOINTS ==========

@check_post_privacy
@csrf_exempt
@api_view(['GET'])
def get_post_detail(request, post_id):
    """Get single post with privacy enforcement"""
    serializer = PostSerializer(request.post)
    return Response(serializer.data, status=200)

@csrf_exempt
@api_view(['DELETE'])
def delete_own_post(request, post_id):
    """User can delete their own post (author or admin)"""
    try:
        post = Post.objects.get(id=post_id)
        
        # Check permissions: author OR admin
        if post.author != request.user and not is_admin(request.user):
            return Response({
                'error': 'You can only delete your own posts',
                'required': 'post author or admin'
            }, status=403)
        
        post_title = post.title or post.content[:30]
        post.delete()
        logger.info(f"User {request.user.username} deleted their post {post_id}")
        return Response({
            'message': f'Your post "{post_title}" has been deleted'
        }, status=200)
    except Post.DoesNotExist:
        return Response({'error': 'Post not found'}, status=404)
    except Exception as e:
        logger.error(f"Delete post error: {str(e)}")
        return Response({'error': str(e)}, status=500)

# ========== ADMIN-ONLY ENDPOINTS ==========

@admin_required
@csrf_exempt
@api_view(['DELETE'])
def admin_delete_post(request, post_id):
    """Admin can delete any post"""
    try:
        post = Post.objects.get(id=post_id)
        post_title = post.title or post.content[:30]
        post.delete()
        logger.info(f"Admin {request.user.username} deleted post {post_id}: '{post_title}'")
        return Response({
            'message': f'Post "{post_title}" deleted successfully by admin'
        }, status=200)
    except Post.DoesNotExist:
        return Response({'error': 'Post not found'}, status=404)
    except Exception as e:
        logger.error(f"Admin delete post error: {str(e)}")
        return Response({'error': str(e)}, status=500)

@admin_required
@csrf_exempt
@api_view(['DELETE'])
def admin_delete_comment(request, comment_id):
    """Admin can delete any comment"""
    try:
        comment = Comment.objects.get(id=comment_id)
        comment.delete()
        logger.info(f"Admin {request.user.username} deleted comment {comment_id}")
        return Response({
            'message': 'Comment deleted successfully by admin'
        }, status=200)
    except Comment.DoesNotExist:
        return Response({'error': 'Comment not found'}, status=404)
    except Exception as e:
        logger.error(f"Admin delete comment error: {str(e)}")
        return Response({'error': str(e)}, status=500)