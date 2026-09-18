from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Min, Max
import math
from django.views.decorators.cache import cache_control
from common.decorators import user_not_blocked
from admin_panel.products.models import Product, ProductReview
from admin_panel.category.models import Category
from admin_panel.banners.models import ShopShowcase

from django.contrib import messages
from user_panel.wishlist.models import WishlistItem
from common.services import get_eligible_coupons




@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@user_not_blocked
def shop_view(request):

    products_list = Product.objects.filter(
        is_deleted=False,
        is_active=True,
        category__is_deleted=False, 
        category__is_active=True
    )

    # Determine maximum price of available products dynamically
    max_db_price = products_list.aggregate(Max('price'))['price__max']
    if max_db_price is not None:
        max_slider_val = max(10000, int(math.ceil(max_db_price)))
    else:
        max_slider_val = 10000

    search_query = request.GET.get('search', '').strip()
    category_id = request.GET.get('category', '').strip()
    sort_by = request.GET.get('sort', '').strip()
    selected_brands = request.GET.get('brand', '').strip()
    min_price = request.GET.get('min_price', '').strip()
    max_price = request.GET.get('max_price', '').strip()

    if search_query:
        products_list = products_list.filter(
            Q(name__icontains=search_query) | Q(description__icontains=search_query)
        )
        
    if category_id:
        if category_id.isdigit():
            products_list = products_list.filter(category_id=int(category_id))
        else:
            products_list = products_list.filter(category__name__iexact=category_id)


    selected_brands_list = [b.strip() for b in selected_brands.split(',') if b.strip()]
    if selected_brands_list:
        brand_queries = Q()
        for b in selected_brands_list:
            brand_queries |= Q(brand__iexact=b)
        products_list = products_list.filter(brand_queries)

    has_price_filter = False
    if min_price:
        try:
            min_val = float(min_price)
            if min_val > 0:
                products_list = products_list.filter(price__gte=min_val)
                has_price_filter = True
        except ValueError:
            min_price = ''

    if max_price:
        try:
            max_val = float(max_price)
            if max_val < max_slider_val:
                products_list = products_list.filter(price__lte=max_val)
                has_price_filter = True
        except ValueError:
            max_price = ''

        
    if sort_by == 'price_asc':
        products_list = products_list.order_by('price')
    elif sort_by == 'price_desc':
        products_list = products_list.order_by('-price')
    elif sort_by == 'name_asc':
        products_list = products_list.order_by('name')
    elif sort_by == 'name_desc':
        products_list = products_list.order_by('-name')
    else:
        products_list = products_list.order_by('-created_at')
        
    # Fetch distinct active brands dynamically
    available_brands = list(
        Product.objects.filter(is_active=True, is_deleted=False)
        .exclude(brand__isnull=True)
        .exclude(brand__exact='')
        .values_list('brand', flat=True)
        .distinct()
    )

    paginator = Paginator(products_list, 12)
    page_number = request.GET.get('page', 1)
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    for product in page_obj:
        active_vars = product.variants.filter(is_active=True, is_deleted=False)
        primary_var = active_vars.first()
        base_price = primary_var.price if (primary_var and primary_var.price) else product.price
        product.primary_variant_id = primary_var.id if primary_var else ""
        product.display_base_price = base_price
        eff = product.get_effective_discount()
        product.has_discount = eff['has_discount']
        product.discount_percent = eff['discount_percentage']
        product.offer_type = eff['offer_type']
        product.offer_name = eff['offer_name']
        product.discounted_price = product.get_discounted_price(base_price)

    categories = Category.objects.filter(is_deleted=False, is_active=True)

    user_wishlist_product_ids = set()
    if request.user.is_authenticated:
        from user_panel.wishlist.models import WishlistItem
        user_wishlist_product_ids = set(
            WishlistItem.objects.filter(wishlist__user=request.user)
            .values_list('product_id', flat=True)
        )

    filter_applied = bool(category_id or selected_brands or has_price_filter)

    showcases = {
        s.slot: s for s in ShopShowcase.objects.filter(is_active=True, product__is_deleted=False, product__is_active=True).select_related('product')
    }
    hero_left_showcase = showcases.get('HERO_LEFT')
    hero_right_showcase = showcases.get('HERO_RIGHT')
    grid_spotlight_showcase = showcases.get('GRID_SPOTLIGHT')
    sidebar_promo_showcase = showcases.get('SIDEBAR_PROMO')

    for sc in [hero_left_showcase, hero_right_showcase, grid_spotlight_showcase, sidebar_promo_showcase]:
        if sc and sc.product:
            eff = sc.product.get_effective_discount()
            sc.product.has_discount = eff['has_discount']
            sc.product.discounted_price = sc.product.get_discounted_price()

    fender_product = hero_left_showcase.product if hero_left_showcase else Product.objects.filter(
        Q(name__icontains='Stratocaster') | Q(name__icontains='Fender Player'),
        is_deleted=False, is_active=True
    ).first()

    casio_product = hero_right_showcase.product if hero_right_showcase else Product.objects.filter(
        Q(name__icontains='Casio') | Q(name__icontains='Privia'),
        is_deleted=False, is_active=True
    ).first()

    vox_product = grid_spotlight_showcase.product if grid_spotlight_showcase else Product.objects.filter(
        Q(name__icontains='VOX') | Q(name__icontains='AC30'),
        is_deleted=False, is_active=True
    ).first()
    if vox_product and not hasattr(vox_product, 'discounted_price'):
        eff_vox = vox_product.get_effective_discount()
        vox_product.has_discount = eff_vox['has_discount']
        vox_product.discounted_price = vox_product.get_discounted_price()

    context = {
        "page_obj": page_obj,
        "categories": categories,
        "brands": available_brands,
        "search_query": search_query,
        "category_id": category_id,
        "selected_brand": selected_brands,
        "selected_brands_list": selected_brands_list,
        "min_price": min_price or 0,
        "max_price": max_price or max_slider_val,
        "has_price_filter": has_price_filter,
        "max_slider_val": max_slider_val,
        "filter_applied": filter_applied,
        "sort_by": sort_by,
        "user_wishlist_product_ids": user_wishlist_product_ids,
        "fender_product": fender_product,
        "casio_product": casio_product,
        "vox_product": vox_product,
        "hero_left_showcase": hero_left_showcase,
        "hero_right_showcase": hero_right_showcase,
        "grid_spotlight_showcase": grid_spotlight_showcase,
        "sidebar_promo_showcase": sidebar_promo_showcase,
    }

    return render(request, "user/shop/shop.html", context)



def product_detail_view(request, product_id):
    try:
        product = Product.objects.get(
            id=product_id,
            is_deleted=False,
            is_active=True,
            category__is_deleted=False,
            category__is_active=True
        )
    except Product.DoesNotExist:
        messages.error(request, "The requested product is currently unavailable.")
        return redirect("shop")
    


    category = product.category
    eff = product.get_effective_discount()
    has_discount = eff['has_discount']
    discount_pct = eff['discount_percentage']
    offer_type = eff['offer_type']
    offer_name = eff['offer_name']

    # Fetch active variants
    variants = product.variants.filter(is_active=True, is_deleted=False)

    # Determine initial item to feature on page load (prefer in-stock variant)
    if variants.exists():
        first_available = variants.filter(stock__gt=0).first() or variants.first()
    else:
        first_available = product

    # Initial price defaults to first_available variant if available, otherwise product
    primary_item = first_available
    display_base_price = float(primary_item.price) if (primary_item and getattr(primary_item, 'price', None)) else float(product.price)

    if has_discount:
        discount_price = display_base_price - (display_base_price * discount_pct / 100)
    else:
        discount_price = display_base_price

    for var in variants:
        v_price = float(var.price) if var.price else float(product.price)
        var.display_price = v_price
        if has_discount:
            var.display_discounted = v_price - (v_price * discount_pct / 100)
        else:
            var.display_discounted = v_price

    related_products = Product.objects.filter(
        category=category,
        is_active=True, 
        is_deleted=False
    ).exclude(id=product.id)[:4]



    highlights_list = []
    if product.highlights:
        highlights_list = [line.strip() for line in product.highlights.splitlines() if line.strip()]
    if not highlights_list:
        highlights_list = [
            "Professional luthier setup and calibration.",
            "Selected premium wood & custom hardware.",
            "12-Month hardware warranty included.",
            "Custom thermo-foamed protective packaging.",
            "30-Day hassle-free return window.",
            "100% authentic certificate included."
        ]

    is_in_wishlist = False
    if request.user.is_authenticated:
        is_in_wishlist = WishlistItem.objects.filter(wishlist__user=request.user, product=product).exists()

    active_coupons = get_eligible_coupons(user=request.user, limit=3)

    # Fetch product reviews and calculate rating stats
    reviews = product.reviews.all().order_by('-created_at')
    total_reviews = reviews.count()
    avg_rating = product.average_rating

    rating_counts = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
    for r in reviews:
        if r.rating in rating_counts:
            rating_counts[r.rating] += 1

    rating_breakdown = []
    for star in [5, 4, 3, 2, 1]:
        count = rating_counts[star]
        pct = round((count / total_reviews * 100), 1) if total_reviews > 0 else 0
        rating_breakdown.append({
            'star': star,
            'count': count,
            'pct': pct,
        })

    context = {
        "product": product,
        "variants": variants,
        "first_available": first_available,
        "has_discount": has_discount,
        "discount_pct": discount_pct,
        "product_price": display_base_price,
        "discounted_price": discount_price,
        "related_products": related_products,
        "highlights_list": highlights_list,
        "is_in_wishlist": is_in_wishlist,
        "active_coupons": active_coupons,
        "reviews": reviews,
        "total_reviews": total_reviews,
        "avg_rating": avg_rating,
        "rating_breakdown": rating_breakdown,
    }
    
    return render(request, "user/shop/product_detail.html", context)


@cache_control(no_cache=True, no_store=True, must_revalidate=True)
def post_review_view(request, product_id):
    if request.method == "POST":
        product = get_object_or_404(Product, id=product_id)
        
        reviewer_name = request.POST.get('reviewer_name', '').strip()
        if request.user.is_authenticated and not reviewer_name:
            user_full = getattr(request.user, 'fullname', '') or getattr(request.user, 'username', '')
            reviewer_name = user_full if user_full else "Verified Customer"

        if not reviewer_name:
            reviewer_name = "Verified Customer"

        try:
            rating = int(request.POST.get('rating', 5))
            if rating < 1 or rating > 5:
                rating = 5
        except (ValueError, TypeError):
            rating = 5

        title = request.POST.get('title', '').strip()
        comment = request.POST.get('comment', '').strip()
        image = request.FILES.get('image')
        video = request.FILES.get('video')

        if not title or not comment:
            messages.error(request, "Please provide both a review headline and detailed review text.")
            return redirect(f"/shop/product/{product_id}/#reviews-section")

        ProductReview.objects.create(
            product=product,
            user=request.user if request.user.is_authenticated else None,
            reviewer_name=reviewer_name,
            rating=rating,
            title=title,
            comment=comment,
            image=image,
            video=video,
            is_verified_buyer=True
        )

        messages.success(request, "Thank you! Your review and rating have been posted successfully.")
        return redirect(f"/shop/product/{product_id}/#reviews-section")
    
    return redirect("shop")

