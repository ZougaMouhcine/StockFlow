from django.db import models


class Category(models.Model):
	name = models.CharField(max_length=120, unique=True, verbose_name="Nom")
	description = models.TextField(blank=True, verbose_name="Description")
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['name']
		verbose_name = "Catégorie"
		verbose_name_plural = "Catégories"

	def __str__(self):
		return self.name


class Product(models.Model):
	STATUS_CHOICES = [
		('available', 'Disponible'),
		('low', 'Stock faible'),
		('out', 'Rupture'),
	]

	name = models.CharField(max_length=150, verbose_name="Nom du produit")
	description = models.TextField(blank=True, verbose_name="Description")
	price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Prix")
	stock = models.PositiveIntegerField(default=0, verbose_name="Quantité en stock")
	photo = models.ImageField(upload_to='products/', blank=True, null=True)
	category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['name']
		verbose_name = "Produit"
		verbose_name_plural = "Produits"

	def __str__(self):
		return self.name

	@property
	def stock_status(self):
		if self.stock == 0:
			return 'out'
		if self.stock <= 5:
			return 'low'
		return 'available'
