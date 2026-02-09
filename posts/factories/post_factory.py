from ..models import Post

class PostFactory:
    @staticmethod
    def create_post(author, post_type, content='', title='', metadata=None):
        """
        Factory method to create posts with validation
        """
        if metadata is None:
            metadata = {}
        
        # Validate post type
        allowed_types = dict(Post.POST_TYPES).keys()
        if post_type not in allowed_types:
            raise ValueError(f"Invalid post type. Must be one of: {', '.join(allowed_types)}")
        
        # Type-specific validation
        if post_type == 'image':
            if 'file_size' not in metadata:
                raise ValueError("Image posts require 'file_size' in metadata")
            if 'image_url' not in metadata:
                raise ValueError("Image posts require 'image_url' in metadata")
        
        if post_type == 'video':
            if 'duration' not in metadata:
                raise ValueError("Video posts require 'duration' in metadata")
            if 'video_url' not in metadata:
                raise ValueError("Video posts require 'video_url' in metadata")
        
        if post_type == 'link':
            if 'url' not in metadata:
                raise ValueError("Link posts require 'url' in metadata")
        
        # Create and return the post
        post = Post.objects.create(
            author=author,
            post_type=post_type,
            content=content,
            title=title,
            metadata=metadata
        )
        
        return post

    @staticmethod
    def create_text_post(author, content, title=''):
        """Shortcut for creating text posts"""
        return PostFactory.create_post(
            author=author,
            post_type='text',
            content=content,
            title=title
        )

    @staticmethod
    def create_image_post(author, image_url, file_size, title='', description=''):
        """Shortcut for creating image posts"""
        return PostFactory.create_post(
            author=author,
            post_type='image',
            content=description,
            title=title,
            metadata={
                'image_url': image_url,
                'file_size': file_size
            }
        )

    @staticmethod
    def create_video_post(author, video_url, duration, title='', description=''):
        """Shortcut for creating video posts"""
        return PostFactory.create_post(
            author=author,
            post_type='video',
            content=description,
            title=title,
            metadata={
                'video_url': video_url,
                'duration': duration
            }
        )

    @staticmethod
    def create_link_post(author, url, title='', description=''):
        """Shortcut for creating link posts"""
        return PostFactory.create_post(
            author=author,
            post_type='link',
            content=description,
            title=title,
            metadata={'url': url}
        )