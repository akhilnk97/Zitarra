from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import datetime

from common.decorators import admin_required
from user_panel.coupons.models import Coupon
from admin_panel.category.models import Category
from admin_panel.products.models import Product


@admin_required
def admin_coupons_list_view(request):
    search_query = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '').strip()
    sort_by = request.GET.get('sort', 'newest').strip()
    page_num = request.GET.get('page', '1').strip()

    coupons_qs = Coupon.objects.all()

    if search_query:
        coupons_qs = coupons_qs.filter(
            Q(code__icontains=search_query) |
            Q(campaign_name__icontains=search_query)
        )

    now = timezone.now()
    if status_filter == 'ACTIVE':
        coupons_qs = coupons_qs.filter(is_active=True).filter(
            Q(valid_from__isnull=True) | Q(valid_from__lte=now)
        ).filter(
            Q(valid_to__isnull=True) | Q(valid_to__gte=now)
        )
    elif status_filter == 'SCHEDULED':
        coupons_qs = coupons_qs.filter(is_active=True, valid_from__gt=now)
    elif status_filter == 'DISABLED':
        coupons_qs = coupons_qs.filter(is_active=False)
    elif status_filter == 'EXPIRED':
        coupons_qs = coupons_qs.filter(Q(valid_to__lt=now) | Q(is_active=False))

    
    if sort_by == 'code_asc':
        coupons_qs = coupons_qs.order_by('code')
    elif sort_by == 'code_desc':
        coupons_qs = coupons_qs.order_by('-code')
    elif sort_by == 'expiry_asc':
        coupons_qs = coupons_qs.order_by('valid_to')
    elif sort_by == 'discount_desc':
        coupons_qs = coupons_qs.order_by('-discount_value')
    elif sort_by == 'min_purchase_asc':
        coupons_qs = coupons_qs.order_by('min_purchase')
    else:
        coupons_qs = coupons_qs.order_by('-created_at')


    categories = Category.objects.filter(is_deleted=False, is_active=True).order_by('name')
    products = Product.objects.filter(is_deleted=False, is_active=True).order_by('name')

    paginator = Paginator(coupons_qs, 7)
    page_obj = paginator.get_page(page_num)

    context = {
        'coupons': page_obj.object_list,
        'page_obj': page_obj,
        'paginator': paginator,
        'search_query': search_query,
        'status_filter': status_filter,
        'sort_by': sort_by,
        'total_coupons': coupons_qs.count(),
        'all_categories': categories,
        'all_products': products,
    }
    return render(request, 'admin_panel/coupons/coupons.html', context)


@admin_required
def admin_add_coupon_view(request):
    if request.method == 'POST':
        code = request.POST.get('code', '').strip().upper()
        campaign_name = request.POST.get('campaign_name', '').strip()
        offer_type = request.POST.get('offer_type', 'GENERAL').strip()
        discount_type = request.POST.get('discount_type', 'PERCENTAGE').strip()
        discount_value = request.POST.get('discount_value', '0').strip()
        min_purchase = request.POST.get('min_purchase', '0').strip()
        max_discount = request.POST.get('max_discount', '').strip()
        usage_limit = request.POST.get('usage_limit', '').strip()
        usage_limit_per_user = request.POST.get('usage_limit_per_user', '1').strip()
        valid_from = request.POST.get('valid_from', '').strip()
        valid_to = request.POST.get('valid_to', '').strip()
        is_active = request.POST.get('is_active') == 'on' or request.POST.get('is_active') == 'true' or 'is_active' in request.POST
        is_first_order_only = request.POST.get('is_first_order_only') == 'on' or request.POST.get('is_first_order_only') == 'true'

        category_ids = request.POST.getlist('applicable_categories')
        product_ids = request.POST.getlist('applicable_products')

        if not code:
            messages.error(request, "Coupon code is required.")
            return redirect('admin_coupons')

        if Coupon.objects.filter(code__iexact=code).exists():
            messages.error(request, f"Coupon code '{code}' already exists.")
            return redirect('admin_coupons')

        if valid_from and valid_to:
            dt_from = datetime.fromisoformat(valid_from)
            dt_to = datetime.fromisoformat(valid_to)
            if dt_to < dt_from:
                messages.error(request, "Expiry Date cannot be earlier than Start Date.")
                return redirect('admin_coupons')

        try:
            coupon = Coupon(
                code=code,
                campaign_name=campaign_name,
                offer_type=offer_type,
                discount_type=discount_type,
                discount_value=Decimal(discount_value) if discount_value else Decimal('0.00'),
                min_purchase=Decimal(min_purchase) if min_purchase else Decimal('0.00'),
                max_discount=Decimal(max_discount) if max_discount else None,
                usage_limit=int(usage_limit) if (usage_limit and int(usage_limit) > 0) else None,
                usage_limit_per_user=int(usage_limit_per_user) if (usage_limit_per_user and int(usage_limit_per_user) > 0) else None,
                is_first_order_only=is_first_order_only,
                is_active=is_active,
            )
            if valid_from:
                coupon.valid_from = datetime.fromisoformat(valid_from)
            if valid_to:
                coupon.valid_to = datetime.fromisoformat(valid_to)

            coupon.save()

            if offer_type == 'CATEGORY_SPECIFIC':
                coupon.applicable_categories.set(category_ids)
            elif offer_type == 'PRODUCT_SPECIFIC':
                coupon.applicable_products.set(product_ids)

            messages.success(request, f"Coupon '{code}' created successfully.")
        except Exception as e:
            messages.error(request, f"Failed to create coupon: {str(e)}")

    return redirect('admin_coupons')


@admin_required
def admin_edit_coupon_view(request, coupon_id):
    coupon = get_object_or_404(Coupon, id=coupon_id)
    if request.method == 'POST':
        code = request.POST.get('code', '').strip().upper()
        campaign_name = request.POST.get('campaign_name', '').strip()
        offer_type = request.POST.get('offer_type', 'GENERAL').strip()
        discount_type = request.POST.get('discount_type', 'PERCENTAGE').strip()
        discount_value = request.POST.get('discount_value', '0').strip()
        min_purchase = request.POST.get('min_purchase', '0').strip()
        max_discount = request.POST.get('max_discount', '').strip()
        usage_limit = request.POST.get('usage_limit', '').strip()
        usage_limit_per_user = request.POST.get('usage_limit_per_user', '').strip()
        valid_from = request.POST.get('valid_from', '').strip()
        valid_to = request.POST.get('valid_to', '').strip()
        is_active = request.POST.get('is_active') == 'on' or request.POST.get('is_active') == 'true' or 'is_active' in request.POST
        is_first_order_only = request.POST.get('is_first_order_only') == 'on' or request.POST.get('is_first_order_only') == 'true'

        category_ids = request.POST.getlist('applicable_categories')
        product_ids = request.POST.getlist('applicable_products')

        if not code:
            messages.error(request, "Coupon code is required.")
            return redirect('admin_coupons')

        if Coupon.objects.filter(code__iexact=code).exclude(id=coupon.id).exists():
            messages.error(request, f"Coupon code '{code}' already exists.")
            return redirect('admin_coupons')

        if valid_from and valid_to:
            dt_from = datetime.fromisoformat(valid_from)
            dt_to = datetime.fromisoformat(valid_to)
            if dt_to < dt_from:
                messages.error(request, "Expiry Date cannot be earlier than Start Date.")
                return redirect('admin_coupons')

        try:
            coupon.code = code
            coupon.campaign_name = campaign_name
            coupon.offer_type = offer_type
            coupon.discount_type = discount_type
            coupon.discount_value = Decimal(discount_value) if discount_value else Decimal('0.00')
            coupon.min_purchase = Decimal(min_purchase) if min_purchase else Decimal('0.00')
            coupon.max_discount = Decimal(max_discount) if max_discount else None
            coupon.usage_limit = int(usage_limit) if (usage_limit and int(usage_limit) > 0) else None
            coupon.usage_limit_per_user = int(usage_limit_per_user) if (usage_limit_per_user and int(usage_limit_per_user) > 0) else None
            coupon.is_first_order_only = is_first_order_only
            coupon.is_active = is_active

            coupon.valid_from = datetime.fromisoformat(valid_from) if valid_from else None
            coupon.valid_to = datetime.fromisoformat(valid_to) if valid_to else None

            coupon.save()

            if offer_type == 'CATEGORY_SPECIFIC':
                coupon.applicable_categories.set(category_ids)
                coupon.applicable_products.clear()
            elif offer_type == 'PRODUCT_SPECIFIC':
                coupon.applicable_products.set(product_ids)
                coupon.applicable_categories.clear()
            else:
                coupon.applicable_categories.clear()
                coupon.applicable_products.clear()

            messages.success(request, f"Coupon '{code}' updated successfully.")
        except Exception as e:
            messages.error(request, f"Failed to update coupon: {str(e)}")

    return redirect('admin_coupons')


@admin_required
def admin_delete_coupon_view(request, coupon_id):
    coupon = get_object_or_404(Coupon, id=coupon_id)
    if request.method == 'POST':
        code = coupon.code
        coupon.delete()
        messages.success(request, f"Coupon '{code}' deleted successfully.")
    return redirect('admin_coupons')


@admin_required
def admin_toggle_coupon_status_view(request, coupon_id):
    coupon = get_object_or_404(Coupon, id=coupon_id)
    coupon.is_active = not coupon.is_active
    coupon.save(update_fields=['is_active'])
    status_str = 'activated' if coupon.is_active else 'disabled'
    messages.success(request, f"Coupon '{coupon.code}' {status_str}.")
    return redirect('admin_coupons')
