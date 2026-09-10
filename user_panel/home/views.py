from django.shortcuts import render, redirect
from django.contrib import messages
from common.decorators import user_member_required
from admin_panel.products.models import Product
from admin_panel.banners.models import Banner
from django.db.models import F, Q
from django.utils import timezone


def get_new_products():
    available_brands = ['Fender', 'Casio', 'Roland', 'Yamaha', 'Kadence', 'Zitarra']
    products = list(Product.objects.filter(is_active=True, is_deleted=False).order_by('-created_at')[:4])
    for product in products:
        first_word = product.name.split()[0].title()
        product.brand_name = product.brand if product.brand else (first_word if first_word in available_brands else "Zitarra")
    return products

def get_active_banners():
    now = timezone.now()
    active_q = Q(is_deleted=False, status='PUBLISHED') & (Q(end_date__isnull=True) | Q(end_date__gte=now))
    hero_banners = list(Banner.objects.filter(active_q, display_mode='HERO_SLIDER').order_by('priority', '-created_at'))
    promo_strips = list(Banner.objects.filter(active_q, display_mode='PROMO_STRIP').order_by('priority', '-created_at'))

    # Record real impressions atomically whenever banners are served
    displayed_ids = [b.id for b in hero_banners + promo_strips]
    if displayed_ids:
        Banner.objects.filter(id__in=displayed_ids).update(impressions_count=F('impressions_count') + 1)

    return hero_banners, promo_strips

def landing_view(request):
    new_products = get_new_products()
    hero_banners, promo_strips = get_active_banners()
    return render(request, "user/panel/landing.html", {
        "new_products": new_products,
        "hero_banners": hero_banners,
        "promo_strips": promo_strips,
    })

@user_member_required
def home_view(request):
    show_modal = request.session.pop('show_google_login_modal', False)
    login_type = request.session.pop('google_login_type', 'welcome')
    new_products = get_new_products()
    hero_banners, promo_strips = get_active_banners()
    return render(request, "user/panel/home.html", {
        "show_google_login_modal": show_modal,
        "google_login_type": login_type,
        "new_products": new_products,
        "hero_banners": hero_banners,
        "promo_strips": promo_strips,
    })


def about_view(request):
    now = timezone.now()
    active_q = Q(is_deleted=False, status='PUBLISHED', display_mode='PROMO_STRIP') & (Q(end_date__isnull=True) | Q(end_date__gte=now))
    promo_strips = list(Banner.objects.filter(active_q).order_by('priority', '-created_at'))
    if promo_strips:
        Banner.objects.filter(id__in=[b.id for b in promo_strips]).update(impressions_count=F('impressions_count') + 1)
    return render(request, "user/panel/about.html", {
        "promo_strips": promo_strips,
    })


def contact_view(request):
    now = timezone.now()
    active_q = Q(is_deleted=False, status='PUBLISHED', display_mode='PROMO_STRIP') & (Q(end_date__isnull=True) | Q(end_date__gte=now))
    promo_strips = list(Banner.objects.filter(active_q).order_by('priority', '-created_at'))
    if promo_strips:
        Banner.objects.filter(id__in=[b.id for b in promo_strips]).update(impressions_count=F('impressions_count') + 1)
    if request.method == 'POST':
        messages.success(request, "INQUIRY SUBMITTED SUCCESSFULLY. OUR CONCIERGE TEAM WILL BE IN TOUCH SHORTLY.")
        return redirect('contact')

    return render(request, "user/panel/contact.html", {
        "promo_strips": promo_strips,
    })


def custom_404_view(request, exception=None):
    if request.path.startswith('/admin-panel/'):
        context = {}
        if request.user.is_authenticated and request.user.is_staff:
            context["admin_name"] = request.user.fullname
        return render(request, "admin_panel/404.html", context, status=404)
    return render(request, "404.html", status=404)
