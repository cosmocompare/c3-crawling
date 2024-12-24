from django.db import models

class Ranking(models.Model):
    brand = models.CharField(max_length=255)
    cosmetic_name = models.CharField(max_length=255)
    price = models.CharField(max_length=255)
    sale_price = models.CharField(max_length=255)
    cosmetic_url = models.TextField()  # URL이 길 수 있으므로 TextField 사용
    image_url = models.TextField()  # URL이 길 수 있으므로 TextField 사용

    class Meta:
        db_table = 'ranking'

    def __str__(self):
        return f"{self.brand} - {self.cosmetic_name}"


class Oycosmetic(models.Model):
    category = models.CharField(max_length=255)
    brand = models.CharField(max_length=255)
    cosmetic_name = models.CharField(max_length=255)
    price = models.CharField(max_length=255)
    sale_price_price = models.CharField(max_length=255)
    cosmetic_url = models.TextField()  # URL이 길 수 있으므로 TextField 사용
    image_url = models.TextField()  # URL이 길 수 있으므로 TextField 사용
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'oycosmetic'

    def __str__(self):
        return f"{self.brand} - {self.cosmetic_name}"
    
class Zzcosmetic(models.Model):
    category = models.CharField(max_length=255)
    brand = models.CharField(max_length=255)
    cosmetic_name = models.CharField(max_length=255)
    price = models.CharField(max_length=255)
    sale_price = models.CharField(max_length=255)
    cosmetic_url = models.TextField()
    image_url = models.TextField()
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)

    class Meta:
        db_table = 'zzcosmetic'

    def __str__(self):
        return f"{self.brand} - {self.cosmetic_name}"