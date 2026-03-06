from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import Post, Comment, Like
from .serializers import PostSerializer, CommentSerializer
from .factories.post_factory import PostFactory
from .singletons.logger_singleton import LoggerSingleton
from .singletons.config_manager import ConfigManager

# Initialize singletons
logger = LoggerSingleton().get_logger()
config = ConfigManager()

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
        
        # Log registration
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
            # Log successful login
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
            # Log failed login attempt
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
        # Use singleton config for pagination
        page_size = config.get_setting('DEFAULT_PAGE_SIZE')
        posts = Post.objects.all()[:page_size]
        serializer = PostSerializer(posts, many=True)
        return Response(serializer.data, status=200)
    except Exception as e:
        logger.error(f"Get posts error: {str(e)}")
        return Response({'error': str(e)}, status=500)

@csrf_exempt
@api_view(['POST'])
def create_post(request):
    try:
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=401)
        
        # Use Factory Pattern to create post
        post_type = request.data.get('post_type', 'text')
        title = request.data.get('title', '')
        content = request.data.get('content', '')
        metadata = request.data.get('metadata', {})
        
        try:
            post = PostFactory.create_post(
                author=request.user,
                post_type=post_type,
                title=title,
                content=content,
                metadata=metadata
            )
            
            logger.info(f"Post created by {request.user.username}: {post.id}")
            serializer = PostSerializer(post)
            return Response(serializer.data, status=201)
        except ValueError as e:
            logger.warning(f"Invalid post creation: {str(e)}")
            return Response({'error': str(e)}, status=400)
    except Exception as e:
        logger.error(f"Create post error: {str(e)}")
        return Response({'error': str(e)}, status=500)

# Factory shortcut endpoints
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
        
        logger.info(f"Link post created by {request.user.username}: {post.id}")
        serializer = PostSerializer(post)
        return Response(serializer.data, status=201)
    except ValueError as e:
        logger.warning(f"Invalid link post: {str(e)}")
        return Response({'error': str(e)}, status=400)
    except Exception as e:
        logger.error(f"Create link post error: {str(e)}")
        return Response({'error': str(e)}, status=500)

# ========== COMMENT ENDPOINTS ==========

@csrf_exempt
@api_view(['GET'])
def get_comments(request):
    try:
        comments = Comment.objects.all()
        serializer = CommentSerializer(comments, many=True)
        return Response(serializer.data, status=200)
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
    
    # ========== LIKE ENDPOINTS ==========

@csrf_exempt
@api_view(['POST'])
def like_post(request, post_id):
    """
    Like a post
    """
    try:
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=401)
        
        try:
            post = Post.objects.get(id=post_id)
        except Post.DoesNotExist:
            logger.warning(f"Like failed: Post {post_id} not found")
            return Response({'error': 'Post not found'}, status=404)
        
        # Check if user already liked this post
        like, created = Like.objects.get_or_create(
            user=request.user,
            post=post
        )
        
        if not created:
            # User already liked this post
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
    """
    Unlike a post
    """
    try:
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=401)
        
        try:
            post = Post.objects.get(id=post_id)
        except Post.DoesNotExist:
            return Response({'error': 'Post not found'}, status=404)
        
        # Delete the like if it exists
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
def get_post_comments(request, post_id):
    """
    Get all comments for a specific post
    """
    try:
        try:
            post = Post.objects.get(id=post_id)
        except Post.DoesNotExist:
            return Response({'error': 'Post not found'}, status=404)
        
        # Get comments with pagination (optional)
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
    """
    Add a comment to a specific post
    """
    try:
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=401)
        
        try:
            post = Post.objects.get(id=post_id)
        except Post.DoesNotExist:
            logger.warning(f"Comment failed: Post {post_id} not found")
            return Response({'error': 'Post not found'}, status=404)
        
        text = request.data.get('text')
        
        if not text or text.strip() == '':
            return Response({'error': 'Comment text is required'}, status=400)
        
        if len(text) > 1000:
            return Response({'error': 'Comment text cannot exceed 1000 characters'}, status=400)
        
        # Create comment
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
    """
    Delete a comment (only by author or admin)
    """
    try:
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=401)
        
        try:
            comment = Comment.objects.get(id=comment_id)
        except Comment.DoesNotExist:
            return Response({'error': 'Comment not found'}, status=404)
        
        # Check if user is the author
        if comment.author != request.user:
            return Response({'error': 'You can only delete your own comments'}, status=403)
        
        comment.delete()
        logger.info(f"User {request.user.username} deleted comment {comment_id}")
        
        return Response({
            'message': 'Comment deleted successfully'
        }, status=200)
        
    except Exception as e:
        logger.error(f"Delete comment error: {str(e)}")
        return Response({'error': str(e)}, status=500)