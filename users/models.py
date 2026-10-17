from django.db import models
from django.contrib.auth.models import AbstractUser

class Country(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class User(AbstractUser):
    country = models.ForeignKey(Country, on_delete=models.CASCADE, null=True, blank=True)
#    sdt
    # phone = models.CharField(max_length=20, null=True, blank=True)

    def __str__(self):
        return self.username