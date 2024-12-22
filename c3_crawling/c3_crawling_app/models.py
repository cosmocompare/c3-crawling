from django.db import models

class Ranking(models.Model):
    id = models.AutoField(primary_key=True)
    brand = models.CharField(max_length=100)
    cosmetic_name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    oy_price = models.DecimalField(max_digits=10, decimal_places=2)
    zz_price = models.DecimalField(max_digits=10, decimal_places=2)
    cosmetic_url = models.URLField()
    image_url = models.URLField()

    class Meta:
        db_table = 'ranking'

    def __str__(self):
        return self.cosmetic_name

# Create your models here.
