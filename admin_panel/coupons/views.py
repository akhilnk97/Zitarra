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
import re


@admin_required
def admin_coupons_list_view(request):
    search_query = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '').strip()
    sort_by = request.GET.get('sort', 'newest').strip()
    page_num = request.GET.get('page', '1').strip()

    coupons_qs = Coupon.objects.all()

    if search_query:
        words = search_query.split()
        q_obj = Q(code__icontains=search_query) | Q(campaign_name__icontains=search_query)
        if len(words) > 1:
            multi_q = Q()
            for w in words:
                multi_q &= (Q(code__icontains=w) | Q(campaign_name__icontains=w))
            q_obj |= multi_q
        coupons_qs = coupons_qs.filter(q_obj).distinct()

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
        discount_value_str = request.POST.get('discount_value', '').strip()
        min_purchase_str = request.POST.get('min_purchase', '0').strip()
        max_discount_str = request.POST.get('max_discount', '').strip()
        usage_limit_str = request.POST.get('usage_limit', '').strip()
        usage_limit_per_user_str = request.POST.get('usage_limit_per_user', '1').strip()
        valid_from = request.POST.get('valid_from', '').strip()
        valid_to = request.POST.get('valid_to', '').strip()
        is_active = request.POST.get('is_active') == 'on' or request.POST.get('is_active') == 'true' or 'is_active' in request.POST
        is_first_order_only = request.POST.get('is_first_order_only') == 'on' or request.POST.get('is_first_order_only') == 'true'

        category_ids = request.POST.getlist('applicable_categories')
        product_ids = request.POST.getlist('applicable_products')

        # 1. Code Validation
        raw_code = request.POST.get('code', '')
        if not code:
            messages.error(request, "Coupon code is required.")
            return redirect('admin_coupons')

        if ' ' in raw_code:
            messages.error(request, "Coupon code cannot contain spaces.")
            return redirect('admin_coupons')

        if len(code) < 3 or len(code) > 30:
            messages.error(request, "Coupon code must be between 3 and 30 characters.")
            return redirect('admin_coupons')

        if not re.match(r'^[A-Z0-9_-]+$', code):
            messages.error(request, "Coupon code can only contain uppercase letters, numbers, hyphens, and underscores without spaces.")
            return redirect('admin_coupons')

        if Coupon.objects.filter(code__iexact=code).exists():
            messages.error(request, f"Coupon code '{code}' already exists.")
            return redirect('admin_coupons')

        # 2. Campaign Name Validation
        raw_campaign = request.POST.get('campaign_name', '')
        if raw_campaign:
            if raw_campaign.startswith(' ') or raw_campaign.endswith(' '):
                messages.error(request, "Campaign name cannot start or end with a space.")
                return redirect('admin_coupons')
            if '  ' in raw_campaign:
                messages.error(request, "Campaign name cannot contain consecutive spaces.")
                return redirect('admin_coupons')
            if len(campaign_name) < 3:
                messages.error(request, "Campaign name must be at least 3 characters.")
                return redirect('admin_coupons')
            if len(campaign_name) > 100:
                messages.error(request, "Campaign name cannot exceed 100 characters.")
                return redirect('admin_coupons')
            if re.search(r'[<>{}]', campaign_name):
                messages.error(request, "Campaign name cannot contain special characters like < > { }.")
                return redirect('admin_coupons')

        if offer_type == 'CATEGORY_SPECIFIC' and not category_ids:
            messages.error(request, "Please select at least one applicable category for category-specific coupons.")
            return redirect('admin_coupons')

        if offer_type == 'PRODUCT_SPECIFIC' and not product_ids:
            messages.error(request, "Please select at least one applicable product for product-specific coupons.")
            return redirect('admin_coupons')

        try:
            discount_val = Decimal(discount_value_str)
        except Exception:
            messages.error(request, "Valid discount value is required.")
            return redirect('admin_coupons')

        if discount_type == 'PERCENTAGE':
            if discount_val < 1 or discount_val > 99:
                messages.error(request, "Percentage discount must be between 1% and 99%.")
                return redirect('admin_coupons')
        elif discount_type == 'FIXED':
            if discount_val <= Decimal('0.00'):
                messages.error(request, "Fixed discount amount must be greater than ₹0.00.")
                return redirect('admin_coupons')
        else:
            discount_type = 'PERCENTAGE'

        try:
            min_purchase = Decimal(min_purchase_str) if min_purchase_str else Decimal('0.00')
            if min_purchase < Decimal('0.00'):
                raise ValueError
        except Exception:
            messages.error(request, "Minimum purchase amount must be a positive number or zero.")
            return redirect('admin_coupons')

        if discount_type == 'FIXED' and min_purchase > Decimal('0.00') and discount_val > min_purchase:
            messages.error(request, f"Fixed discount (₹{discount_val}) cannot exceed the minimum subtotal (₹{min_purchase}).")
            return redirect('admin_coupons')

        usage_limit = None
        if usage_limit_str:
            try:
                usage_limit = int(usage_limit_str)
                if usage_limit < 1:
                    messages.error(request, "Global usage limit must be at least 1.")
                    return redirect('admin_coupons')
            except ValueError:
                messages.error(request, "Global usage limit must be an integer.")
                return redirect('admin_coupons')

        usage_limit_per_user = None
        if usage_limit_per_user_str:
            try:
                usage_limit_per_user = int(usage_limit_per_user_str)
                if usage_limit_per_user < 1:
                    messages.error(request, "Usage limit per user must be at least 1.")
                    return redirect('admin_coupons')
                if usage_limit is not None and usage_limit_per_user > usage_limit:
                    messages.error(request, "Usage limit per user cannot exceed global usage limit.")
                    return redirect('admin_coupons')
            except ValueError:
                messages.error(request, "Usage limit per user must be an integer.")
                return redirect('admin_coupons')

        dt_from = None
        dt_to = None
        now = timezone.now()
        if valid_from:
            try:
                dt_from = datetime.fromisoformat(valid_from)
            except Exception:
                messages.error(request, "Invalid start date format.")
                return redirect('admin_coupons')

        if valid_to:
            try:
                dt_to = datetime.fromisoformat(valid_to)
            except Exception:
                messages.error(request, "Invalid expiry date format.")
                return redirect('admin_coupons')

        if dt_from and dt_to and dt_to < dt_from:
            messages.error(request, "Expiry Date cannot be earlier than Start Date.")
            return redirect('admin_coupons')

        try:
            coupon = Coupon(
                code=code,
                campaign_name=campaign_name,
                offer_type=offer_type,
                discount_type=discount_type,
                discount_value=discount_val,
                min_purchase=min_purchase,
                max_discount=Decimal(max_discount_str) if max_discount_str else None,
                usage_limit=usage_limit,
                usage_limit_per_user=usage_limit_per_user,
                is_first_order_only=is_first_order_only,
                is_active=is_active,
                valid_from=dt_from,
                valid_to=dt_to,
            )

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
        discount_value_str = request.POST.get('discount_value', '').strip()
        min_purchase_str = request.POST.get('min_purchase', '0').strip()
        max_discount_str = request.POST.get('max_discount', '').strip()
        usage_limit_str = request.POST.get('usage_limit', '').strip()
        usage_limit_per_user_str = request.POST.get('usage_limit_per_user', '').strip()
        valid_from = request.POST.get('valid_from', '').strip()
        valid_to = request.POST.get('valid_to', '').strip()
        is_active = request.POST.get('is_active') == 'on' or request.POST.get('is_active') == 'true' or 'is_active' in request.POST
        is_first_order_only = request.POST.get('is_first_order_only') == 'on' or request.POST.get('is_first_order_only') == 'true'

        category_ids = request.POST.getlist('applicable_categories')
        product_ids = request.POST.getlist('applicable_products')

        raw_code = request.POST.get('code', '')
        if not code:
            messages.error(request, "Coupon code is required.")
            return redirect('admin_coupons')

        if ' ' in raw_code:
            messages.error(request, "Coupon code cannot contain spaces.")
            return redirect('admin_coupons')

        if len(code) < 3 or len(code) > 30:
            messages.error(request, "Coupon code must be between 3 and 30 characters.")
            return redirect('admin_coupons')

        if not re.match(r'^[A-Z0-9_-]+$', code):
            messages.error(request, "Coupon code can only contain uppercase letters, numbers, hyphens, and underscores without spaces.")
            return redirect('admin_coupons')

        if Coupon.objects.filter(code__iexact=code).exclude(id=coupon.id).exists():
            messages.error(request, f"Coupon code '{code}' already exists.")
            return redirect('admin_coupons')

        raw_campaign = request.POST.get('campaign_name', '')
        if raw_campaign:
            if raw_campaign.startswith(' ') or raw_campaign.endswith(' '):
                messages.error(request, "Campaign name cannot start or end with a space.")
                return redirect('admin_coupons')
            if '  ' in raw_campaign:
                messages.error(request, "Campaign name cannot contain consecutive spaces.")
                return redirect('admin_coupons')
            if len(campaign_name) < 3:
                messages.error(request, "Campaign name must be at least 3 characters.")
                return redirect('admin_coupons')
            if len(campaign_name) > 100:
                messages.error(request, "Campaign name cannot exceed 100 characters.")
                return redirect('admin_coupons')
            if re.search(r'[<>{}]', campaign_name):
                messages.error(request, "Campaign name cannot contain special characters like < > { }.")
                return redirect('admin_coupons')

        if offer_type == 'CATEGORY_SPECIFIC' and not category_ids:
            messages.error(request, "Please select at least one applicable category for category-specific coupons.")
            return redirect('admin_coupons')

        if offer_type == 'PRODUCT_SPECIFIC' and not product_ids:
            messages.error(request, "Please select at least one applicable product for product-specific coupons.")
            return redirect('admin_coupons')

        try:
            discount_val = Decimal(discount_value_str)
        except Exception:
            messages.error(request, "Valid discount value is required.")
            return redirect('admin_coupons')

        if discount_type == 'PERCENTAGE':
            if discount_val < 1 or discount_val > 99:
                messages.error(request, "Percentage discount must be between 1% and 99%.")
                return redirect('admin_coupons')
        elif discount_type == 'FIXED':
            if discount_val <= Decimal('0.00'):
                messages.error(request, "Fixed discount amount must be greater than ₹0.00.")
                return redirect('admin_coupons')
        else:
            discount_type = 'PERCENTAGE'

        try:
            min_purchase = Decimal(min_purchase_str) if min_purchase_str else Decimal('0.00')
            if min_purchase < Decimal('0.00'):
                raise ValueError
        except Exception:
            messages.error(request, "Minimum purchase amount must be a positive number or zero.")
            return redirect('admin_coupons')

        if discount_type == 'FIXED' and min_purchase > Decimal('0.00') and discount_val > min_purchase:
            messages.error(request, f"Fixed discount (₹{discount_val}) cannot exceed the minimum subtotal (₹{min_purchase}).")
            return redirect('admin_coupons')

        usage_limit = None
        if usage_limit_str:
            try:
                usage_limit = int(usage_limit_str)
                if usage_limit < 1:
                    messages.error(request, "Global usage limit must be at least 1.")
                    return redirect('admin_coupons')
            except ValueError:
                messages.error(request, "Global usage limit must be an integer.")
                return redirect('admin_coupons')

        usage_limit_per_user = None
        if usage_limit_per_user_str:
            try:
                usage_limit_per_user = int(usage_limit_per_user_str)
                if usage_limit_per_user < 1:
                    messages.error(request, "Usage limit per user must be at least 1.")
                    return redirect('admin_coupons')
                if usage_limit is not None and usage_limit_per_user > usage_limit:
                    messages.error(request, "Usage limit per user cannot exceed global usage limit.")
                    return redirect('admin_coupons')
            except ValueError:
                messages.error(request, "Usage limit per user must be an integer.")
                return redirect('admin_coupons')

        dt_from = None
        dt_to = None
        if valid_from:
            try:
                dt_from = datetime.fromisoformat(valid_from)
            except Exception:
                messages.error(request, "Invalid start date format.")
                return redirect('admin_coupons')

        if valid_to:
            try:
                dt_to = datetime.fromisoformat(valid_to)
            except Exception:
                messages.error(request, "Invalid expiry date format.")
                return redirect('admin_coupons')

        if dt_from and dt_to and dt_to < dt_from:
            messages.error(request, "Expiry Date cannot be earlier than Start Date.")
            return redirect('admin_coupons')

        try:
            coupon.code = code
            coupon.campaign_name = campaign_name
            coupon.offer_type = offer_type
            coupon.discount_type = discount_type
            coupon.discount_value = discount_val
            coupon.min_purchase = min_purchase
            coupon.max_discount = Decimal(max_discount_str) if max_discount_str else None
            coupon.usage_limit = usage_limit
            coupon.usage_limit_per_user = usage_limit_per_user
            coupon.is_first_order_only = is_first_order_only
            coupon.is_active = is_active
            coupon.valid_from = dt_from
            coupon.valid_to = dt_to
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
