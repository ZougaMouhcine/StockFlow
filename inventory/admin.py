from django.contrib import admin
from .models import Category, Order, OrderItem, Product


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
	list_display = ('name', 'created_at')
	search_fields = ('name',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
	list_display = ('name', 'category', 'price', 'stock', 'created_at')
	search_fields = ('name', 'description')
	list_filter = ('category', 'created_at')


class OrderItemInline(admin.TabularInline):
	model = OrderItem
	extra = 0
	readonly_fields = ('product', 'quantity', 'unit_price')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
	list_display = ('id', 'user', 'status', 'total_amount', 'created_at')
	list_filter = ('status', 'created_at')
	search_fields = ('user__username', 'user__email', 'full_name', 'email')
	inlines = [OrderItemInline]
