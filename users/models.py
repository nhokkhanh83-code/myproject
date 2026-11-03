from django.db import models
from django.contrib.auth.models import AbstractUser

class Country(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name
# 1. Model Category
class Category(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

# 2. Model Brand
class Brand(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name
    
class User(AbstractUser):
    country = models.ForeignKey(Country, on_delete=models.CASCADE, null=True, blank=True)
    address = models.CharField(max_length=255, null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)

    def __str__(self):
        return self.username



class Product(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE)
    status = models.IntegerField(default=0)
    sale = models.IntegerField(default=0, null=True, blank=True) 
    company = models.CharField(max_length=255, null=True, blank=True)
    detail = models.TextField(null=True, blank=True)
    images = models.TextField(default='[]')
   
   
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    class Meta:
        db_table = "product"

    def __str__(self):
        return self.name

class History(models.Model):

    email = models.EmailField(max_length=255)
    phone = models.CharField(max_length=50, blank=True, null=True)
    name = models.CharField(max_length=255)
    id_user = models.IntegerField()
    price = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True) 

    class Meta:
        db_table = 'history' 

    def __str__(self):
        return f"{self.name} - {self.email} - ${self.price}"

    # Proxy model để đưa User vào menu quản lý của App Users
class UserAccount(User):
    class Meta:
        proxy = True
        verbose_name = 'User'
        verbose_name_plural = 'Users'