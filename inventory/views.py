from decimal import Decimal
import re
import unicodedata

from rapidfuzz import fuzz

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import F, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import CategoryForm, CheckoutForm, LoginForm, ProductForm, SignUpForm
from .models import Category, Order, OrderItem, Product
from .notifications import send_admin_whatsapp_notification


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


ORDER_STATUS_FLOW = {
	'pending': ['confirmed', 'cancelled'],
	'confirmed': ['shipped', 'cancelled'],
	'shipped': ['delivered'],
	'delivered': [],
	'cancelled': [],
}

ORDER_STATUS_STEPS = [
	('pending', 'En attente'),
	('confirmed', 'Confirmée'),
	('shipped', 'En livraison'),
	('delivered', 'Livrée'),
]


def _get_allowed_statuses(order):
	return ORDER_STATUS_FLOW.get(order.status, [])


@login_required
@require_POST
def app_logout(request):
	logout(request)
	messages.success(request, 'Vous êtes déconnecté.')
	return redirect('product_list')


def admin_logout_compat(request):
	logout(request)
	messages.success(request, 'Vous êtes déconnecté.')
	return redirect('/admin/login/')


def _get_cart(request):
	cart = request.session.get('cart', {})
	if not isinstance(cart, dict):
		cart = {}
	return cart


def _save_cart(request, cart):
	request.session['cart'] = cart
	request.session.modified = True


def _parse_quantity(value):
	try:
		quantity = int(value)
	except (TypeError, ValueError):
		return None
	return quantity


def _get_safe_next_url(request):
	next_url = request.POST.get('next') or request.GET.get('next')
	if not next_url:
		return None
	if url_has_allowed_host_and_scheme(
		next_url,
		allowed_hosts={request.get_host()},
		require_https=request.is_secure(),
	):
		return next_url
	return None


def _deny_cart_for_admin(request):
	if can_manage_products(request.user):
		messages.info(request, "Le panier est désactive pour les comptes administrateurs.")
		return True
	return False


SEARCH_SYNONYMS = {
	'chargeur': ['charger', 'power adapter', 'adapter', 'adaptor', 'alimentation', 'power supply'],
	'charger': ['chargeur', 'power adapter', 'adapter', 'adaptor', 'alimentation', 'power supply'],
	'adaptateur': ['adapter', 'adaptor'],
	'adapter': ['adaptateur', 'adaptor'],
	'adaptor': ['adaptateur', 'adapter'],
	'cable': ['cord', 'wire', 'lead'],
	'clavier': ['keyboard'],
	'keyboard': ['clavier'],
	'souris': ['mouse'],
	'mouse': ['souris'],
	'casque': ['headset', 'headphones'],
	'headphones': ['casque', 'headset'],
	'ecouteurs': ['earbuds', 'earphones', 'headphones'],
	'earbuds': ['ecouteurs', 'earphones'],
	'ecran': ['monitor', 'screen', 'display'],
	'monitor': ['ecran', 'screen', 'display'],
	'portable': ['laptop', 'notebook'],
	'laptop': ['portable', 'notebook'],
	'ordinateur': ['computer', 'pc'],
	'computer': ['ordinateur', 'pc'],
}

NON_WORD_RE = re.compile(r"[^\w\s-]", re.UNICODE)
MULTISPACE_RE = re.compile(r"\s+")


def _normalize_search_text(text):
	if not text:
		return ''
	text = unicodedata.normalize('NFKD', str(text))
	text = ''.join(ch for ch in text if not unicodedata.combining(ch))
	text = text.lower()
	text = NON_WORD_RE.sub(' ', text)
	text = MULTISPACE_RE.sub(' ', text).strip()
	return text


def _expand_query_terms(query):
	base = _normalize_search_text(query)
	if not base:
		return []
	terms = {base}
	for token in base.split():
		terms.add(token)
		for synonym in SEARCH_SYNONYMS.get(token, []):
			normalized = _normalize_search_text(synonym)
			if normalized:
				terms.add(normalized)
	return list(terms)


def _score_product(query_terms, product):
	corpus = ' '.join(
		part for part in [product.name, product.description, product.category.name]
		if part
	)
	corpus = _normalize_search_text(corpus)
	if not corpus:
		return 0, False
	corpus_tokens = corpus.split()
	best_score = 0
	has_exact_match = False
	for term in query_terms:
		if not term:
			continue
		if term in corpus:
			has_exact_match = True
			best_score = max(best_score, 100)
			continue
		score = fuzz.WRatio(term, corpus)
		if corpus_tokens:
			token_score = max((fuzz.WRatio(term, token) for token in corpus_tokens), default=0)
			score = max(score, token_score)
		best_score = max(best_score, score)
	return best_score, has_exact_match


def _build_cart_items(cart):
	if not cart:
		return [], Decimal('0.00')

	product_ids = [int(product_id) for product_id in cart.keys()]
	products = Product.objects.filter(id__in=product_ids).select_related('category')
	items = []
	total = Decimal('0.00')

	for product in products:
		quantity = _parse_quantity(cart.get(str(product.id))) or 0
		if quantity <= 0:
			continue
		line_total = product.price * quantity
		items.append({
			'product': product,
			'quantity': quantity,
			'line_total': line_total,
		})
		total += line_total

	return items, total


def signup(request):
	if request.user.is_authenticated:
		return redirect('product_list')

	form = SignUpForm(request.POST or None)
	if form.is_valid():
		user = form.save()
		login(request, user)
		messages.success(request, 'Votre compte a été créé avec succès.')
		return redirect('product_list')

	return render(request, 'inventory/signup.html', {'form': form})


def login_view(request):
	if request.user.is_authenticated:
		return redirect('product_list')

	next_url = _get_safe_next_url(request)
	form = LoginForm(request, data=request.POST or None)
	if form.is_valid():
		user = form.get_user()
		login(request, user)
		messages.success(request, 'Bienvenue, vous êtes connecté.')
		return redirect(next_url or 'product_list')

	return render(request, 'inventory/login.html', {'form': form, 'next_url': next_url})


def product_list(request):
	query = request.GET.get('q', '').strip()
	category_id = request.GET.get('category', '')
	sort_param = request.GET.get('sort')
	if query and not sort_param:
		sort = 'relevance'
	else:
		sort = sort_param or 'name'

	products = Product.objects.select_related('category').all()

	if query:
		query_terms = _expand_query_terms(query)
		scored = []
		if query_terms:
			for product in products:
				score, has_exact_match = _score_product(query_terms, product)
				if has_exact_match or score >= 85:
					scored.append((product, score))
		if not scored:
			fallback = products.filter(
				Q(name__icontains=query)
				| Q(description__icontains=query)
				| Q(category__name__icontains=query)
			)
			scored = [(product, 100) for product in fallback]

		if sort == 'relevance':
			scored.sort(key=lambda item: (item[1], item[0].name.lower()), reverse=True)
		elif sort == 'name':
			scored.sort(key=lambda item: item[0].name.lower())
		elif sort == '-name':
			scored.sort(key=lambda item: item[0].name.lower(), reverse=True)
		elif sort == 'price':
			scored.sort(key=lambda item: item[0].price)
		elif sort == '-price':
			scored.sort(key=lambda item: item[0].price, reverse=True)

		products = [item[0] for item in scored]

	if category_id:
		products = products.filter(category_id=category_id)

	if not query and sort in ['name', '-name', 'price', '-price']:
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
	next_url = _get_safe_next_url(request)
	if request.method == 'POST':
		product.delete()
		messages.warning(request, 'Produit supprimé.')
		return redirect(next_url or 'product_list')

	context = {
		'product': product,
		'next_url': next_url,
		'is_superadmin': is_superadmin(request.user),
		'can_manage': can_manage_products(request.user),
	}
	return render(request, 'inventory/product_confirm_delete.html', context)


@login_required
@user_passes_test(can_manage_products)
def category_list(request):
	context = {
		'categories': Category.objects.all(),
		'is_superadmin': is_superadmin(request.user),
		'can_manage': can_manage_products(request.user),
	}
	return render(request, 'inventory/category_list.html', context)


@login_required
@user_passes_test(can_manage_products)
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
@user_passes_test(can_manage_products)
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
@user_passes_test(can_manage_products)
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


@login_required
@user_passes_test(can_manage_products)
def admin_dashboard(request):
	context = {
		'product_count': Product.objects.count(),
		'category_count': Category.objects.count(),
		'order_count': Order.objects.count(),
		'pending_order_count': Order.objects.filter(status='pending').count(),
		'recent_orders': Order.objects.select_related('user').order_by('-created_at')[:5],
		'is_superadmin': is_superadmin(request.user),
		'can_manage': can_manage_products(request.user),
	}
	return render(request, 'inventory/admin_dashboard.html', context)


@login_required
def cart_detail(request):
	if _deny_cart_for_admin(request):
		return redirect('product_list')
	cart = _get_cart(request)
	items, total = _build_cart_items(cart)
	context = {
		'items': items,
		'total': total,
		'is_superadmin': is_superadmin(request.user),
		'can_manage': can_manage_products(request.user),
	}
	return render(request, 'inventory/cart.html', context)


@login_required
@require_POST
def cart_add(request, pk):
	if _deny_cart_for_admin(request):
		return redirect('product_list')
	product = get_object_or_404(Product, pk=pk)
	quantity = _parse_quantity(request.POST.get('quantity', 1))
	if quantity is None or quantity <= 0:
		messages.error(request, 'Quantité invalide.')
		return redirect('product_detail', pk=pk)

	if product.stock <= 0:
		messages.error(request, 'Ce produit est en rupture de stock.')
		return redirect('product_detail', pk=pk)

	cart = _get_cart(request)
	current_qty = _parse_quantity(cart.get(str(product.id), 0)) or 0
	if current_qty + quantity > product.stock:
		messages.error(request, 'Stock insuffisant pour la quantité demandée.')
		return redirect('product_detail', pk=pk)

	cart[str(product.id)] = current_qty + quantity
	_save_cart(request, cart)
	messages.success(request, 'Produit ajouté au panier.')
	next_url = request.POST.get('next')
	return redirect(next_url or 'cart_detail')


@login_required
@require_POST
def cart_update(request, pk):
	if _deny_cart_for_admin(request):
		return redirect('product_list')
	product = get_object_or_404(Product, pk=pk)
	quantity = _parse_quantity(request.POST.get('quantity'))
	if quantity is None or quantity < 0:
		messages.error(request, 'Quantité invalide.')
		return redirect('cart_detail')

	cart = _get_cart(request)
	if quantity == 0:
		cart.pop(str(product.id), None)
		_save_cart(request, cart)
		messages.info(request, 'Produit retiré du panier.')
		return redirect('cart_detail')

	if quantity > product.stock:
		messages.error(request, 'Stock insuffisant pour la quantité demandée.')
		return redirect('cart_detail')

	cart[str(product.id)] = quantity
	_save_cart(request, cart)
	messages.success(request, 'Panier mis à jour.')
	return redirect('cart_detail')


@login_required
@require_POST
def cart_remove(request, pk):
	if _deny_cart_for_admin(request):
		return redirect('product_list')
	cart = _get_cart(request)
	if str(pk) in cart:
		cart.pop(str(pk), None)
		_save_cart(request, cart)
		messages.info(request, 'Produit retiré du panier.')
	return redirect('cart_detail')


@login_required
def checkout(request):
	if _deny_cart_for_admin(request):
		return redirect('product_list')
	cart = _get_cart(request)
	items, total = _build_cart_items(cart)
	if not items:
		messages.info(request, 'Votre panier est vide.')
		return redirect('product_list')

	initial = {
		'full_name': f"{request.user.first_name} {request.user.last_name}".strip(),
		'email': request.user.email,
	}
	form = CheckoutForm(request.POST or None, initial=initial)

	if form.is_valid():
		for item in items:
			if item['quantity'] > item['product'].stock:
				messages.error(request, f"Stock insuffisant pour {item['product'].name}.")
				return redirect('cart_detail')

		order = Order.objects.create(
			user=request.user,
			full_name=form.cleaned_data['full_name'],
			email=form.cleaned_data['email'],
			phone=form.cleaned_data['phone'],
			address=form.cleaned_data['address'],
			city=form.cleaned_data['city'],
			notes=form.cleaned_data['notes'],
			total_amount=total,
		)

		for item in items:
			OrderItem.objects.create(
				order=order,
				product=item['product'],
				quantity=item['quantity'],
				unit_price=item['product'].price,
			)
			Product.objects.filter(pk=item['product'].pk).update(stock=F('stock') - item['quantity'])

		send_admin_whatsapp_notification(order, items)

		_save_cart(request, {})
		messages.success(request, 'Commande validée !')
		return redirect('order_detail', pk=order.pk)

	context = {
		'form': form,
		'items': items,
		'total': total,
		'is_superadmin': is_superadmin(request.user),
		'can_manage': can_manage_products(request.user),
	}
	return render(request, 'inventory/checkout.html', context)


@login_required
def order_list(request):
	if can_manage_products(request.user):
		orders = Order.objects.select_related('user').prefetch_related('items', 'items__product').order_by('-created_at')
		for order in orders:
			order.allowed_statuses = _get_allowed_statuses(order)
	else:
		orders = Order.objects.filter(user=request.user).prefetch_related('items', 'items__product').order_by('-created_at')
	context = {
		'orders': orders,
		'is_superadmin': is_superadmin(request.user),
		'can_manage': can_manage_products(request.user),
	}
	return render(request, 'inventory/order_list.html', context)


@login_required
def order_detail(request, pk):
	if can_manage_products(request.user):
		order = get_object_or_404(Order, pk=pk)
	else:
		order = get_object_or_404(Order, pk=pk, user=request.user)
	status_steps = []
	current_index = None
	for index, (key, label) in enumerate(ORDER_STATUS_STEPS):
		if order.status == key:
			current_index = index
		status_steps.append({
			'key': key,
			'label': label,
		})
	context = {
		'order': order,
		'items': order.items.select_related('product'),
		'allowed_statuses': _get_allowed_statuses(order) if can_manage_products(request.user) else [],
		'status_steps': status_steps,
		'current_status_index': current_index,
		'is_superadmin': is_superadmin(request.user),
		'can_manage': can_manage_products(request.user),
	}
	return render(request, 'inventory/order_detail.html', context)


@login_required
@user_passes_test(can_manage_products)
@require_POST
def order_update_status(request, pk):
	order = get_object_or_404(Order, pk=pk)
	new_status = request.POST.get('status')
	allowed = _get_allowed_statuses(order)
	if not new_status or new_status not in allowed:
		messages.error(request, "Changement de statut non autorisé.")
		return redirect('order_detail', pk=pk)

	order.status = new_status
	order.save(update_fields=['status'])
	messages.success(request, "Statut de la commande mis à jour.")
	return redirect('order_detail', pk=pk)
