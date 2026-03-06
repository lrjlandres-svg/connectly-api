from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Post, Comment, Like

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']

class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username']

class LikeSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    
    class Meta:
        model = Like
        fields = ['id', 'user', 'created_at']

class CommentSerializer(serializers.ModelSerializer):
    author = AuthorSerializer(read_only=True)
    post = serializers.PrimaryKeyRelatedField(queryset=Post.objects.all())

    class Meta:
        model = Comment
        fields = ['id', 'text', 'author', 'post', 'created_at']

    def validate_post(self, value):
        if not Post.objects.filter(id=value.id).exists():
            raise serializers.ValidationError("Post not found.")
        return value
    
    def validate_text(self, value):
        if not value or value.strip() == '':
            raise serializers.ValidationError("Comment text cannot be empty.")
        if len(value) > 1000:
            raise serializers.ValidationError("Comment text cannot exceed 1000 characters.")
        return value

class PostSerializer(serializers.ModelSerializer):
    author = AuthorSerializer(read_only=True)
    comments = CommentSerializer(many=True, read_only=True)
    likes = LikeSerializer(many=True, read_only=True)
    like_count = serializers.SerializerMethodField()
    comment_count = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = ['id', 'title', 'content', 'post_type', 'metadata', 'author', 'created_at', 'comments', 'likes', 'like_count', 'comment_count']
    
    def get_like_count(self, obj):
        return obj.like_count
    
    def get_comment_count(self, obj):
        return obj.comment_count