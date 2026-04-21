from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import CategoryForm, ProductForm
from .models import Category, Product


def is_superadmin(user):
	return user.is_authenticated and (
		user.is_superuser or
		user.groups.filter(name='superadmin').exists()
	)


def can_manage_products(user):
	return user.is_authenticated and (
		user.is_superuser or
		user.groups.filter(name__in=['superadmin', 'admin']).exists()
	)


@login_required
@require_POST
def app_logout(request):
	logout(request)
	messages.success(request, 'Vous êtes déconnecté.')
	return redirect('/admin/login/')


def admin_logout_compat(request):
	logout(request)
	messages.success(request, 'Vous êtes déconnecté.')
	return redirect('/admin/login/')


@login_required
def product_list(request):
	query = request.GET.get('q', '')
	category_id = request.GET.get('category', '')
	sort = request.GET.get('sort', 'name')

	products = Product.objects.select_related('category').all()

	if query:
		products = products.filter(Q(name__icontains=query) | Q(description__icontains=query))

	if category_id:
		products = products.filter(category_id=category_id)

	if sort in ['name', '-name', 'price', '-price']:
		products = products.order_by(sort)

	paginator = Paginator(products, 6)
	page_obj = paginator.get_page(request.GET.get('page'))

	context = {
		'page_obj': page_obj,
		'categories': Category.objects.all(),
		'query': query,
		'category_id': category_id,
		'sort': sort,
		'is_superadmin': is_superadmin(request.user),
		'can_manage': can_manage_products(request.user),
	}
	return render(request, 'inventory/product_list.html', context)


@login_required
def product_detail(request, pk):
	product = get_object_or_404(Product, pk=pk)
	context = {
		'product': product,
		'is_superadmin': is_superadmin(request.user),
		'can_manage': can_manage_products(request.user),
	}
	return render(request, 'inventory/product_detail.html', context)


@login_required
@user_passes_test(can_manage_products)
def product_create(request):
	form = ProductForm(request.POST or None, request.FILES or None)
	if form.is_valid():
		form.save()
		messages.success(request, 'Produit ajouté avec succès.')
		return redirect('product_list')

	context = {
		'form': form,
		'title': 'Ajouter un produit',
		'product': None,
		'is_superadmin': is_superadmin(request.user),
		'can_manage': can_manage_products(request.user),
	}
	return render(request, 'inventory/product_form.html', context)


@login_required
@user_passes_test(can_manage_products)
def product_update(request, pk):
	product = get_object_or_404(Product, pk=pk)
	form = ProductForm(request.POST or None, request.FILES or None, instance=product)
	if form.is_valid():
		form.save()
		messages.success(request, 'Produit modifié avec succès.')
		return redirect('product_list')

	context = {
		'form': form,
		'title': 'Modifier le produit',
		'product': product,
		'is_superadmin': is_superadmin(request.user),
		'can_manage': can_manage_products(request.user),
	}
	return render(request, 'inventory/product_form.html', context)


@login_required
@user_passes_test(can_manage_products)
def product_delete(request, pk):
	product = get_object_or_404(Product, pk=pk)
	if request.method == 'POST':
		product.delete()
		messages.warning(request, 'Produit supprimé.')
		return redirect('product_list')

	context = {
		'product': product,
		'is_superadmin': is_superadmin(request.user),
		'can_manage': can_manage_products(request.user),
	}
	return render(request, 'inventory/product_confirm_delete.html', context)


@login_required
@user_passes_test(is_superadmin)
def category_list(request):
	context = {
		'categories': Category.objects.all(),
		'is_superadmin': is_superadmin(request.user),
		'can_manage': can_manage_products(request.user),
	}
	return render(request, 'inventory/category_list.html', context)


@login_required
@user_passes_test(is_superadmin)
def category_create(request):
	form = CategoryForm(request.POST or None)
	if form.is_valid():
		form.save()
		messages.success(request, 'Catégorie ajoutée avec succès.')
		return redirect('category_list')

	context = {
		'form': form,
		'title': 'Ajouter une catégorie',
		'is_superadmin': is_superadmin(request.user),
		'can_manage': can_manage_products(request.user),
	}
	return render(request, 'inventory/category_form.html', context)


@login_required
@user_passes_test(is_superadmin)
def category_update(request, pk):
	category = get_object_or_404(Category, pk=pk)
	form = CategoryForm(request.POST or None, instance=category)
	if form.is_valid():
		form.save()
		messages.success(request, 'Catégorie modifiée avec succès.')
		return redirect('category_list')

	context = {
		'form': form,
		'title': 'Modifier la catégorie',
		'category': category,
		'is_superadmin': is_superadmin(request.user),
		'can_manage': can_manage_products(request.user),
	}
	return render(request, 'inventory/category_form.html', context)


@login_required
@user_passes_test(is_superadmin)
def category_delete(request, pk):
	category = get_object_or_404(Category, pk=pk)
	if request.method == 'POST':
		category.delete()
		messages.warning(request, 'Catégorie supprimée.')
		return redirect('category_list')

	context = {
		'category': category,
		'is_superadmin': is_superadmin(request.user),
		'can_manage': can_manage_products(request.user),
	}
	return render(request, 'inventory/category_confirm_delete.html', context)
