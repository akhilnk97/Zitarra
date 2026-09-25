from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.utils import timezone
from django.db.models import Q
from datetime import datetime

from common.decorators import admin_required
from common.services import is_valid_image_file
from .models import Category
import re


@admin_required
def admin_category_view(request):
    search_query = request.GET.get("search", "").strip()
    page_number = request.GET.get("page", "1").strip()
    sort_val = request.GET.get("sort", "latest").strip()

    categories = Category.objects.filter(is_deleted=False).order_by("-id")

    if search_query:
        words = search_query.split()
        q_obj = Q(name__icontains=search_query) | Q(description__icontains=search_query)
        if len(words) > 1:
            multi_q = Q()
            for w in words:
                multi_q &= (Q(name__icontains=w) | Q(description__icontains=w))
            q_obj |= multi_q
        categories = categories.filter(q_obj).distinct()

    if sort_val == "oldest":
        categories = categories.order_by("id")
    elif sort_val == "name_az":
        categories = categories.order_by("name")
    elif sort_val == "name_za":
        categories = categories.order_by("-name")
    else:
        categories = categories.order_by("-id")

    total_categories = Category.objects.filter(is_deleted=False).count()
    active_categories = Category.objects.filter(is_deleted=False, is_active=True).count()

    paginator = Paginator(categories, 7)
    page_obj = paginator.get_page(page_number)

    context = {
        "admin_name": request.user.fullname,
        "categories": page_obj,
        "search_query": search_query,
        "total_categories": total_categories,
        "active_categories": active_categories,
    }
    return render(request, "admin_panel/category/category.html", context)


@admin_required
def admin_add_category_view(request):
    today = timezone.now().date()
    today_str = today.strftime("%Y-%m-%d")

    if request.method == "POST":
        raw_name = request.POST.get("name", "")
        name = raw_name.strip()
        description = request.POST.get("description", "").strip()
        discount_str = request.POST.get("discount", "0").strip()
        expiry_date_str = request.POST.get("expiry_date", "").strip()
        is_active = "is_active" in request.POST
        image = request.FILES.get("image")

        if not name:
            messages.error(request, "Category name is required.")
            return render(request, "admin_panel/category/add_category.html", {"admin_name": request.user.fullname, "today_str": today_str})

        if raw_name.startswith(" ") or raw_name.endswith(" "):
            messages.error(request, "Category name cannot start or end with a space.")
            return render(request, "admin_panel/category/add_category.html", {"admin_name": request.user.fullname, "today_str": today_str})

        if "  " in raw_name:
            messages.error(request, "Category name cannot contain consecutive spaces.")
            return render(request, "admin_panel/category/add_category.html", {"admin_name": request.user.fullname, "today_str": today_str})

        if len(name) < 2 or len(name) > 100:
            messages.error(request, "Category name must be between 2 and 100 characters.")
            return render(request, "admin_panel/category/add_category.html", {"admin_name": request.user.fullname, "today_str": today_str})

        if not re.match(r'^[A-Za-z0-9]+([ \-&][A-Za-z0-9]+)*$', name):
            messages.error(request, "Category name can only contain letters, numbers, single spaces, hyphens, and &.")
            return render(request, "admin_panel/category/add_category.html", {"admin_name": request.user.fullname, "today_str": today_str})

        if Category.objects.filter(name__iexact=name, is_deleted=False).exists():
            messages.error(request, f"A category named '{name}' already exists.")
            return render(request, "admin_panel/category/add_category.html", {"admin_name": request.user.fullname, "today_str": today_str})

        if len(description) > 500:
            messages.error(request, "Category description cannot exceed 500 characters.")
            return render(request, "admin_panel/category/add_category.html", {"admin_name": request.user.fullname, "today_str": today_str})

        try:
            discount = int(discount_str) if discount_str else 0
            if discount < 0 or discount > 90:
                raise ValueError
        except ValueError:
            messages.error(request, "Discount must be an integer between 0% and 90%.")
            return render(request, "admin_panel/category/add_category.html", {"admin_name": request.user.fullname, "today_str": today_str})

        if image:
            if image.size > 5 * 1024 * 1024:
                messages.error(request, "Category image file size cannot exceed 5MB.")
                return render(request, "admin_panel/category/add_category.html", {"admin_name": request.user.fullname, "today_str": today_str})
            if not is_valid_image_file(image):
                messages.error(request, "Invalid image format. Allowed formats: JPG, PNG, WEBP, AVIF.")
                return render(request, "admin_panel/category/add_category.html", {"admin_name": request.user.fullname, "today_str": today_str})

        expiry_date = None
        if expiry_date_str:
            for fmt in ("%Y-%m-%d", "%d-%m-%Y"):
                try:
                    expiry_date = datetime.strptime(expiry_date_str, fmt).date()
                    break
                except ValueError:
                    continue
            if not expiry_date:
                messages.error(request, "Campaign expiry date must be a valid date.")
                return render(request, "admin_panel/category/add_category.html", {"admin_name": request.user.fullname, "today_str": today_str})

            if expiry_date < today:
                messages.error(request, "Campaign expiry date cannot be in the past.")
                return render(request, "admin_panel/category/add_category.html", {"admin_name": request.user.fullname, "today_str": today_str})

        Category.objects.create(
            name=name,
            description=description,
            discount=discount,
            expiry_date=expiry_date,
            is_active=is_active,
            image=image,
        )
        messages.success(request, f"Category '{name}' created successfully.")
        return redirect("admin_category")

    return render(request, "admin_panel/category/add_category.html", {"admin_name": request.user.fullname, "today_str": today_str})


@admin_required
def admin_edit_category_view(request, category_id):
    category = get_object_or_404(Category, id=category_id, is_deleted=False)
    today = timezone.now().date()
    today_str = today.strftime("%Y-%m-%d")

    if request.method == "POST":
        raw_name = request.POST.get("name", "")
        name = raw_name.strip()
        description = request.POST.get("description", "").strip()
        discount_str = request.POST.get("discount", "0").strip()
        expiry_date_str = request.POST.get("expiry_date", "").strip()
        is_active = "is_active" in request.POST
        image = request.FILES.get("image")

        if not name:
            messages.error(request, "Category name is required.")
            return render(request, "admin_panel/category/edit_category.html", {"admin_name": request.user.fullname, "category": category, "today_str": today_str})

        if raw_name.startswith(" ") or raw_name.endswith(" "):
            messages.error(request, "Category name cannot start or end with a space.")
            return render(request, "admin_panel/category/edit_category.html", {"admin_name": request.user.fullname, "category": category, "today_str": today_str})

        if "  " in raw_name:
            messages.error(request, "Category name cannot contain consecutive spaces.")
            return render(request, "admin_panel/category/edit_category.html", {"admin_name": request.user.fullname, "category": category, "today_str": today_str})

        if len(name) < 2 or len(name) > 100:
            messages.error(request, "Category name must be between 2 and 100 characters.")
            return render(request, "admin_panel/category/edit_category.html", {"admin_name": request.user.fullname, "category": category, "today_str": today_str})
        if not re.match(r'^[A-Za-z0-9]+([ \-&][A-Za-z0-9]+)*$', name):
            messages.error(request, "Category name can only contain letters, numbers, single spaces, hyphens, and &.")
            return render(request, "admin_panel/category/edit_category.html", {"admin_name": request.user.fullname, "category": category, "today_str": today_str})
            
        if Category.objects.filter(name__iexact=name, is_deleted=False).exclude(id=category.id).exists():
            messages.error(request, f"A category named '{name}' already exists.")
            return render(request, "admin_panel/category/edit_category.html", {"admin_name": request.user.fullname, "category": category, "today_str": today_str})

        if len(description) > 500:
            messages.error(request, "Category description cannot exceed 500 characters.")
            return render(request, "admin_panel/category/edit_category.html", {"admin_name": request.user.fullname, "category": category, "today_str": today_str})
    
        try:
            discount = int(discount_str) if discount_str else 0
            if discount < 0 or discount > 90:
                raise ValueError
        except ValueError:
            messages.error(request, "Discount must be an integer between 0% and 90%.")
            return render(request, "admin_panel/category/edit_category.html", {"admin_name": request.user.fullname, "category": category, "today_str": today_str})

        if image:
            if image.size > 5 * 1024 * 1024:
                messages.error(request, "Category image file size cannot exceed 5MB.")
                return render(request, "admin_panel/category/edit_category.html", {"admin_name": request.user.fullname, "category": category, "today_str": today_str})
            if not is_valid_image_file(image):
                messages.error(request, "Invalid image format. Allowed formats: JPG, PNG, WEBP, AVIF.")
                return render(request, "admin_panel/category/edit_category.html", {"admin_name": request.user.fullname, "category": category, "today_str": today_str})

        expiry_date = None
        if expiry_date_str:
            for fmt in ("%Y-%m-%d", "%d-%m-%Y"):
                try:
                    expiry_date = datetime.strptime(expiry_date_str, fmt).date()
                    break
                except ValueError:
                    continue
            if not expiry_date:
                messages.error(request, "Campaign expiry date must be a valid date.")
                return render(request, "admin_panel/category/edit_category.html", {"admin_name": request.user.fullname, "category": category, "today_str": today_str})

            if expiry_date < today and expiry_date != category.expiry_date:
                messages.error(request, "Campaign expiry date cannot be in the past.")
                return render(request, "admin_panel/category/edit_category.html", {"admin_name": request.user.fullname, "category": category, "today_str": today_str})
        
        category.name = name
        category.description = description
        category.discount = discount
        category.expiry_date = expiry_date
        category.is_active = is_active
        if image:
            category.image = image
        category.save()
        messages.success(request, f"Category '{name}' updated successfully.")
        return redirect("admin_category")

    context = {
        "admin_name": request.user.fullname,
        "category": category,
        "today_str": today_str,
    }
    return render(request, "admin_panel/category/edit_category.html", context)


@admin_required
def admin_delete_category_view(request, category_id):

    if request.method == "POST":
        category = get_object_or_404(Category, id=category_id, is_deleted=False)
        category.is_deleted = True
        category.save()
        messages.success(request, f"Category '{category.name}' deleted successfully.")
    else:
        messages.error(request, "Invalid request method.")
    return redirect("admin_category")


@admin_required
def admin_toggle_offer_view(request, category_id):
    if request.method == "POST":
        category = get_object_or_404(Category, id=category_id, is_deleted=False)
        category.is_offer_active = not category.is_offer_active
        category.save()
        status_text = "enabled" if category.is_offer_active else "disabled"
        messages.success(request, f"Offer for category '{category.name}' has been {status_text}.")
    else:
        messages.error(request, "Invalid request method.")
    return redirect("admin_category")
        

    
        
        
            
        
        
        

            
