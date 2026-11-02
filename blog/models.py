from django.db import models
from django.conf import settings
from ckeditor_uploader.fields import RichTextUploadingField
from django.db.models import Avg

class Blog(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    content = RichTextUploadingField() # Tích hợp CKEditor có upload ảnh
    image = models.ImageField(upload_to='blogs/', blank=True, null=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    

    def __str__(self):
        return self.title

    # Hàm tự động tính điểm TBC của bài viết này
    def get_avg_rate(self):
        avg = self.ratings.aggregate(Avg('rate'))['rate__avg']
        return round(avg) if avg is not None else 0

    # Hàm đếm tổng số lượt vote của bài viết này
    def get_vote_count(self):
        return self.ratings.count()

class Rate(models.Model):
    blog = models.ForeignKey(Blog, on_delete=models.CASCADE, related_name='ratings')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    rate = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} rated {self.rate} stars for {self.blog}"
    

class Comment(models.Model):
    cmt = models.TextField()
    blog = models.ForeignKey('Blog', on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    avatar_user = models.CharField(max_length=255, blank=True, null=True)
    name_user = models.CharField(max_length=150)
    level = models.IntegerField(default=0) # 0: cmt cha; >0: ID của cmt cha
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name_user}: {self.cmt[:30]}"