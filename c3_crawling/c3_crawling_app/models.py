from django.db import models

class Ranking(models.Model):
    brand = models.CharField(max_length=255)
    cosmetic_name = models.CharField(max_length=255)
    price = models.CharField(max_length=255, null=True, blank=True)
    oy_price = models.CharField(max_length=255)
    zz_price = models.CharField(max_length=255, null=True, blank=True)
    cosmetic_url = models.TextField()  # URL이 길 수 있으므로 TextField 사용
    image_url = models.TextField()  # URL이 길 수 있으므로 TextField 사용

    class Meta:
        db_table = 'ranking'

    def __str__(self):
        return f"{self.brand} - {self.cosmetic_name}"
