from django.conf import settings
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


class Order(models.Model):
	STATUS_CHOICES = [
		('pending', 'En attente'),
		('confirmed', 'Confirmee'),
		('shipped', 'Expediee'),
		('delivered', 'Livree'),
		('cancelled', 'Annulee'),
	]

	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
	full_name = models.CharField(max_length=160, verbose_name='Nom complet')
	email = models.EmailField(verbose_name='Email')
	phone = models.CharField(max_length=30, verbose_name='Telephone')
	address = models.CharField(max_length=240, verbose_name='Adresse')
	city = models.CharField(max_length=120, verbose_name='Ville')
	notes = models.TextField(blank=True, verbose_name='Notes')
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
	total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['-created_at']
		verbose_name = 'Commande'
		verbose_name_plural = 'Commandes'

	def __str__(self):
		return f"Commande {self.pk}"


class OrderItem(models.Model):
	order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
	product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='order_items')
	quantity = models.PositiveIntegerField(default=1)
	unit_price = models.DecimalField(max_digits=10, decimal_places=2)

	class Meta:
		ordering = ['id']
		verbose_name = 'Article'
		verbose_name_plural = 'Articles'

	def __str__(self):
		return f"{self.product} x {self.quantity}"

	@property
	def line_total(self):
		return self.unit_price * self.quantity
