from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from common.decorators import admin_required
from common.services import is_valid_image_file
from .models import Brand
import re


@admin_required
def admin_brands_view(request):
    search_query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', 'all').strip()

    brands_qs = Brand.objects.filter(is_deleted=False)

    if search_query:
        words = search_query.split()
        q_obj = Q(name__icontains=search_query) | Q(description__icontains=search_query)
        if len(words) > 1:
            multi_q = Q()
            for w in words:
                multi_q &= (Q(name__icontains=w) | Q(description__icontains=w))
            q_obj |= multi_q
        brands_qs = brands_qs.filter(q_obj).distinct()

    if status_filter and status_filter != 'all':
        brands_qs = brands_qs.filter(status=status_filter)

    all_active_qs = Brand.objects.filter(is_deleted=False)
    total_brands = all_active_qs.count()
    active_brands = all_active_qs.filter(status='ACTIVE').count()
    pending_brands = all_active_qs.filter(status='PENDING').count()
    suspended_brands = all_active_qs.filter(status='SUSPENDED').count()

    paginator = Paginator(brands_qs.order_by('id'), 8)
    page_number = request.GET.get('page', 1)

    try:
        brands_page = paginator.page(page_number)
    except PageNotAnInteger:
        brands_page = paginator.page(1)
    except EmptyPage:
        brands_page = paginator.page(paginator.num_pages)

    context = {
        'admin_name': getattr(request.user, 'fullname', None) or getattr(request.user, 'username', 'Admin'),
        'brands': brands_page,
        'total_brands': total_brands,
        'active_brands': active_brands,
        'pending_brands': pending_brands,
        'suspended_brands': suspended_brands,
        'search_query': search_query,
        'status_filter': status_filter,
    }

    return render(request, 'admin_panel/brands/brands.html', context)


@admin_required
def add_brand_view(request):
    if request.method == 'POST':
        raw_name = request.POST.get('name', '')
        name = raw_name.strip()
        description = request.POST.get('description', '').strip()
        status = request.POST.get('status', 'ACTIVE').strip()
        logo = request.FILES.get('logo')

        if not name:
            messages.error(request, "Brand name is required.")
            return redirect('admin_brands')

        if raw_name.startswith(" ") or raw_name.endswith(" "):
            messages.error(request, "Brand name cannot start or end with a space.")
            return redirect('admin_brands')

        if "  " in raw_name:
            messages.error(request, "Brand name cannot contain consecutive spaces.")
            return redirect('admin_brands')

        if len(name) < 2 or len(name) > 100:
            messages.error(request, "Brand name must be between 2 and 100 characters.")
            return redirect('admin_brands')

        if not re.match(r'^[A-Za-z0-9]+([ \-&][A-Za-z0-9]+)*$', name):
            messages.error(request, "Brand name can only contain letters, numbers, single spaces, hyphens, and &.")
            return redirect('admin_brands')

        if Brand.objects.filter(name__iexact=name, is_deleted=False).exists():
            messages.error(request, f"Brand '{name}' already exists.")
            return redirect('admin_brands')

        if len(description) > 500:
            messages.error(request, "Brand description cannot exceed 500 characters.")
            return redirect('admin_brands')

        if logo:
            if logo.size > 5 * 1024 * 1024:
                messages.error(request, "Logo file size cannot exceed 5MB.")
                return redirect('admin_brands')
            if not is_valid_image_file(logo):
                messages.error(request, "Invalid logo format. Allowed formats: JPG, PNG, WEBP, AVIF.")
                return redirect('admin_brands')

        brand = Brand.objects.create(
            name=name,
            description=description,
            status=status,
        )

        if logo:
            brand.logo = logo
            brand.save()

        messages.success(request, f"Brand '{brand.name}' added successfully!")
        return redirect('admin_brands')

    return redirect('admin_brands')


@admin_required
def edit_brand_view(request, brand_id):
    brand = get_object_or_404(Brand, id=brand_id, is_deleted=False)

    if request.method == 'POST':
        raw_name = request.POST.get('name', '')
        name = raw_name.strip()
        description = request.POST.get('description', '').strip()
        status = request.POST.get('status', 'ACTIVE').strip()
        logo = request.FILES.get('logo')

        if not name:
            messages.error(request, "Brand name is required.")
            return redirect('admin_brands')

        if raw_name.startswith(" ") or raw_name.endswith(" "):
            messages.error(request, "Brand name cannot start or end with a space.")
            return redirect('admin_brands')

        if "  " in raw_name:
            messages.error(request, "Brand name cannot contain consecutive spaces.")
            return redirect('admin_brands')

        if len(name) < 2 or len(name) > 100:
            messages.error(request, "Brand name must be between 2 and 100 characters.")
            return redirect('admin_brands')

        if not re.match(r'^[A-Za-z0-9]+([ \-&][A-Za-z0-9]+)*$', name):
            messages.error(request, "Brand name can only contain letters, numbers, single spaces, hyphens, and &.")
            return redirect('admin_brands')

        if Brand.objects.filter(name__iexact=name, is_deleted=False).exclude(id=brand.id).exists():
            messages.error(request, f"Another brand with name '{name}' already exists.")
            return redirect('admin_brands')

        if len(description) > 500:
            messages.error(request, "Brand description cannot exceed 500 characters.")
            return redirect('admin_brands')

        if logo:
            if logo.size > 5 * 1024 * 1024:
                messages.error(request, "Logo file size cannot exceed 5MB.")
                return redirect('admin_brands')
            if not is_valid_image_file(logo):
                messages.error(request, "Invalid logo format. Allowed formats: JPG, PNG, WEBP, AVIF.")
                return redirect('admin_brands')

        brand.name = name
        brand.description = description
        brand.status = status

        if logo:
            brand.logo = logo

        brand.save()
        messages.success(request, f"Brand '{brand.name}' updated successfully!")
        return redirect('admin_brands')

    return redirect('admin_brands')


@admin_required
def toggle_brand_status_view(request, brand_id):
    brand = get_object_or_404(Brand, id=brand_id, is_deleted=False)
    new_status = request.GET.get('status', '').strip().upper()

    if new_status in ['ACTIVE', 'PENDING', 'SUSPENDED']:
        brand.status = new_status
        brand.save()
        messages.success(request, f"Brand '{brand.name}' status changed to {brand.get_status_display()}.")
    else:
        # Toggle between ACTIVE and SUSPENDED
        if brand.status == 'ACTIVE':
            brand.status = 'SUSPENDED'
        else:
            brand.status = 'ACTIVE'
        brand.save()
        messages.success(request, f"Brand '{brand.name}' status updated to {brand.get_status_display()}.")

    return redirect('admin_brands')


@admin_required
def delete_brand_view(request, brand_id):
    brand = get_object_or_404(Brand, id=brand_id)
    brand.is_deleted = True
    brand.save()
    messages.success(request, f"Brand '{brand.name}' archived successfully.")
    return redirect('admin_brands')
