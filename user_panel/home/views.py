from django.shortcuts import render
from common.decorators import user_member_required
from admin_panel.products.models import Product


def get_new_products():
    available_brands = ['Fender', 'Casio', 'Roland', 'Yamaha', 'Kadence', 'Zitarra']
    products = list(Product.objects.filter(is_active=True, is_deleted=False).order_by('-created_at')[:4])
    for product in products:
        first_word = product.name.split()[0].title()
        product.brand_name = product.brand if product.brand else (first_word if first_word in available_brands else "Zitarra")
    return products

def landing_view(request):
    new_products = get_new_products()
    return render(request, "user/panel/landing.html", {
        "new_products": new_products
    })

@user_member_required
def home_view(request):
    show_modal = request.session.pop('show_google_login_modal', False)
    login_type = request.session.pop('google_login_type', 'welcome')
    new_products = get_new_products()
    return render(request, "user/panel/home.html", {
        "show_google_login_modal": show_modal,
        "google_login_type": login_type,
        "new_products": new_products
    })

def custom_404_view(request, exception=None):
    if request.path.startswith('/admin-panel/'):
        context = {}
        if request.user.is_authenticated and request.user.is_staff:
            context["admin_name"] = request.user.fullname
        return render(request, "admin_panel/404.html", context, status=404)
    return render(request, "404.html", status=404)
