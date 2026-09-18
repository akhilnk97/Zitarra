from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Q
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import datetime, timedelta

from common.decorators import admin_required
from common.services import is_ajax
from .models import ProductOffer
from admin_panel.products.models import Product


@admin_required
def admin_offers_list_view(request):
    search_query = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '').strip()
    sort_by = request.GET.get('sort', 'newest').strip()
    page_num = request.GET.get('page', '1').strip()

    offers_qs = ProductOffer.objects.all()

    if search_query:
        offers_qs = offers_qs.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    today = timezone.now().date()

    if status_filter == 'ACTIVE':
        offers_qs = offers_qs.filter(is_active=True).filter(
            Q(start_date__isnull=True) | Q(start_date__lte=today)
        ).filter(
            Q(end_date__isnull=True) | Q(end_date__gte=today)
        )
    elif status_filter == 'SCHEDULED':
        offers_qs = offers_qs.filter(is_active=True, start_date__gt=today)
    elif status_filter == 'DISABLED':
        offers_qs = offers_qs.filter(is_active=False)
    elif status_filter == 'EXPIRED':
        offers_qs = offers_qs.filter(end_date__lt=today, is_active=True)

    if sort_by == 'name_asc':
        offers_qs = offers_qs.order_by('name')
    elif sort_by == 'name_desc':
        offers_qs = offers_qs.order_by('-name')
    elif sort_by == 'discount_desc':
        offers_qs = offers_qs.order_by('-discount_percentage')
    elif sort_by == 'discount_asc':
        offers_qs = offers_qs.order_by('discount_percentage')
    elif sort_by == 'oldest':
        offers_qs = offers_qs.order_by('created_at')
    else:
        offers_qs = offers_qs.order_by('-created_at')

    # Metrics
    total_offers = ProductOffer.objects.count()
    active_offers = ProductOffer.objects.filter(is_active=True).filter(
        Q(start_date__isnull=True) | Q(start_date__lte=today)
    ).filter(
        Q(end_date__isnull=True) | Q(end_date__gte=today)
    ).count()

    expiring_soon = ProductOffer.objects.filter(
        is_active=True,
        end_date__gte=today,
        end_date__lte=today + timedelta(days=7)
    ).count()

    all_products = Product.objects.filter(is_deleted=False, is_active=True).order_by('name')

    paginator = Paginator(offers_qs, 8)
    page_obj = paginator.get_page(page_num)

    context = {
        'admin_name': getattr(request.user, 'fullname', None) or getattr(request.user, 'username', 'Admin'),
        'offers': page_obj.object_list,
        'page_obj': page_obj,
        'paginator': paginator,
        'search_query': search_query,
        'status_filter': status_filter,
        'sort_by': sort_by,
        'total_offers': total_offers,
        'active_offers': active_offers,
        'expiring_soon': expiring_soon,
        'all_products': all_products,
        'today': today,
        'today_str': today.strftime('%Y-%m-%d'),
    }
    return render(request, 'admin_panel/offers/offers.html', context)


@admin_required
def admin_add_offer_view(request):
    if request.method != 'POST':
        return redirect('admin_offers')

    name = request.POST.get('name', '').strip()
    description = request.POST.get('description', '').strip()
    discount_str = request.POST.get('discount_percentage', '').strip()
    start_date_str = request.POST.get('start_date', '').strip()
    end_date_str = request.POST.get('end_date', '').strip()
    is_active = request.POST.get('is_active') == 'on' or 'is_active' in request.POST
    product_ids = request.POST.getlist('products')

    # 1. Offer Name Validation
    if not name:
        messages.error(request, "Offer name is required.")
        return redirect('admin_offers')

    if len(name) < 3 or len(name) > 100:
        messages.error(request, "Offer name must be between 3 and 100 characters.")
        return redirect('admin_offers')

    import re
    if not re.match(r'^[a-zA-Z0-9_\-\s%]+$', name):
        messages.error(request, "Offer name can only contain letters, numbers, spaces, underscores, and hyphens.")
        return redirect('admin_offers')

    if ProductOffer.objects.filter(name__iexact=name).exists():
        messages.error(request, f"An offer named '{name}' already exists.")
        return redirect('admin_offers')

    # 2. Discount Validation
    try:
        discount = int(discount_str)
        if discount < 1 or discount > 99:
            raise ValueError
    except (ValueError, TypeError):
        messages.error(request, "Discount percentage must be an integer between 1% and 99%.")
        return redirect('admin_offers')

    # 3. Dates Validation (No Past Dates)
    today = timezone.now().date()
    start_date = None
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            if start_date < today:
                messages.error(request, "Start date cannot be in the past.")
                return redirect('admin_offers')
        except ValueError:
            messages.error(request, "Invalid start date format.")
            return redirect('admin_offers')

    end_date = None
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            if end_date < today:
                messages.error(request, "Expiry date cannot be in the past.")
                return redirect('admin_offers')
        except ValueError:
            messages.error(request, "Invalid expiry date format.")
            return redirect('admin_offers')

    if start_date and end_date and end_date < start_date:
        messages.error(request, "Expiry date cannot be earlier than start date.")
        return redirect('admin_offers')

    # 4. Description Validation
    if len(description) > 500:
        messages.error(request, "Description cannot exceed 500 characters.")
        return redirect('admin_offers')

    with transaction.atomic():
        offer = ProductOffer.objects.create(
            name=name,
            description=description,
            discount_percentage=discount,
            start_date=start_date,
            end_date=end_date,
            is_active=is_active
        )
        if product_ids:
            Product.objects.filter(id__in=product_ids).update(product_offer=offer)

    messages.success(request, f"Product Offer '{offer.name}' created successfully!")
    return redirect('admin_offers')


@admin_required
def admin_edit_offer_view(request, offer_id):
    offer = get_object_or_404(ProductOffer, id=offer_id)

    if request.method != 'POST':
        return redirect('admin_offers')

    name = request.POST.get('name', '').strip()
    description = request.POST.get('description', '').strip()
    discount_str = request.POST.get('discount_percentage', '').strip()
    start_date_str = request.POST.get('start_date', '').strip()
    end_date_str = request.POST.get('end_date', '').strip()
    is_active = request.POST.get('is_active') == 'on' or 'is_active' in request.POST
    product_ids = [int(p) for p in request.POST.getlist('products') if p.isdigit()]

    # 1. Name Validation
    if not name:
        messages.error(request, "Offer name is required.")
        return redirect('admin_offers')

    if len(name) < 3 or len(name) > 100:
        messages.error(request, "Offer name must be between 3 and 100 characters.")
        return redirect('admin_offers')

    import re
    if not re.match(r'^[a-zA-Z0-9_\-\s%]+$', name):
        messages.error(request, "Offer name can only contain letters, numbers, spaces, underscores, and hyphens.")
        return redirect('admin_offers')

    if ProductOffer.objects.filter(name__iexact=name).exclude(id=offer.id).exists():
        messages.error(request, f"Another offer named '{name}' already exists.")
        return redirect('admin_offers')

    # 2. Discount Validation
    try:
        discount = int(discount_str)
        if discount < 1 or discount > 99:
            raise ValueError
    except (ValueError, TypeError):
        messages.error(request, "Discount percentage must be an integer between 1% and 99%.")
        return redirect('admin_offers')

    # 3. Dates Validation
    today = timezone.now().date()
    start_date = None
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            if start_date != offer.start_date and start_date < today:
                messages.error(request, "Start date cannot be in the past.")
                return redirect('admin_offers')
        except ValueError:
            messages.error(request, "Invalid start date format.")
            return redirect('admin_offers')

    end_date = None
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            if end_date < today:
                messages.error(request, "Expiry date cannot be in the past.")
                return redirect('admin_offers')
        except ValueError:
            messages.error(request, "Invalid expiry date format.")
            return redirect('admin_offers')

    if start_date and end_date and end_date < start_date:
        messages.error(request, "Expiry date cannot be earlier than start date.")
        return redirect('admin_offers')

    # 4. Description Validation
    if len(description) > 500:
        messages.error(request, "Description cannot exceed 500 characters.")
        return redirect('admin_offers')

    with transaction.atomic():
        offer.name = name
        offer.description = description
        offer.discount_percentage = discount
        offer.start_date = start_date
        offer.end_date = end_date
        offer.is_active = is_active
        offer.save()

        # Sync assigned products
        # Unlink products that were previously assigned to this offer but now deselected
        Product.objects.filter(product_offer=offer).exclude(id__in=product_ids).update(product_offer=None)
        # Link newly selected products
        if product_ids:
            Product.objects.filter(id__in=product_ids).update(product_offer=offer)

    messages.success(request, f"Product Offer '{offer.name}' updated successfully!")
    return redirect('admin_offers')


@admin_required
def admin_toggle_offer_view(request, offer_id):
    if request.method != 'POST':
        return redirect('admin_offers')

    offer = get_object_or_404(ProductOffer, id=offer_id)
    offer.is_active = not offer.is_active
    offer.save()

    status_str = "activated" if offer.is_active else "disabled"
    msg = f"Offer '{offer.name}' {status_str}."

    if is_ajax(request):
        return JsonResponse({
            'status': 'success',
            'is_active': offer.is_active,
            'status_code': offer.status_code,
            'message': msg
        })

    messages.success(request, msg)
    return redirect('admin_offers')


@admin_required
def admin_delete_offer_view(request, offer_id):
    if request.method != 'POST':
        return redirect('admin_offers')

    offer = get_object_or_404(ProductOffer, id=offer_id)
    offer_name = offer.name

    with transaction.atomic():
        # Clear FK from products explicitly (SET_NULL does this, but good practice)
        Product.objects.filter(product_offer=offer).update(product_offer=None)
        offer.delete()

    messages.success(request, f"Product Offer '{offer_name}' was permanently deleted.")
    return redirect('admin_offers')
