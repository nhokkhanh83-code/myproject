from django.db import models
from django.conf import settings
from ckeditor_uploader.fields import RichTextUploadingField

class Blog(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    content = RichTextUploadingField()  # Tích hợp CKEditor có upload ảnh
    image = models.ImageField(upload_to='blogs/', blank=True, null=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title