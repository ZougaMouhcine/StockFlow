def cart_summary(request):
    cart = request.session.get('cart', {})
    if not isinstance(cart, dict):
        cart = {}
    try:
        cart_count = sum(int(quantity) for quantity in cart.values())
    except (TypeError, ValueError):
        cart_count = 0
    return {
        'cart_count': cart_count,
    }
