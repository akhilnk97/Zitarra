from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from datetime import datetime

from common.decorators import admin_required
from .models import Category


@admin_required
def admin_category_view(request):
    search_query = request.GET.get("search", "").strip()
    page_number = request.GET.get("page", "1").strip()
    sort_val = request.GET.get("sort", "latest").strip()

    categories = Category.objects.filter(is_deleted=False).order_by("-id")

    if search_query:
        categories = categories.filter(name__icontains=search_query)

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

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        description = request.POST.get("description", "").strip()
        discount_str = request.POST.get("discount", "0").strip()
        expiry_date_str = request.POST.get("expiry_date", "").strip()
        is_active = "is_active" in request.POST
        image = request.FILES.get("image")

        if not name:
            messages.error(request, "Category name is required.")
            return render(request, "admin_panel/category/add_category.html", {"admin_name": request.user.fullname})

        if Category.objects.filter(name__iexact=name, is_deleted=False).exists():
            messages.error(request, f"A category named '{name}' already exists.")
            return render(request, "admin_panel/category/add_category.html", {"admin_name": request.user.fullname})

        if len(description) > 500:
            messages.error(request, "Category description cannot exceed 500 characters.")
            return render(request, "admin_panel/category/add_category.html", {"admin_name": request.user.fullname})

        try:
            discount = int(discount_str) if discount_str else 0
            if discount < 0 or discount > 100:
                raise ValueError
        except ValueError:
            messages.error(request, "Discount must be a number between 0 and 100.")
            return render(request, "admin_panel/category/add_category.html", {"admin_name": request.user.fullname})

        expiry_date = None
        if expiry_date_str:
            try:
                expiry_date = datetime.strptime(expiry_date_str, "%d-%m-%Y").date()
            except ValueError:
                messages.error(request, "Expiry date must be in DD-MM-YYYY format.")
                return render(request, "admin_panel/category/add_category.html", {"admin_name": request.user.fullname})

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

    return render(request, "admin_panel/category/add_category.html", {"admin_name": request.user.fullname})


@admin_required
def admin_edit_category_view(request, category_id):

    category = get_object_or_404(Category, id=category_id, is_deleted=False)

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        description = request.POST.get("description", "").strip()
        discount_str = request.POST.get("discount", "0").strip()
        expiry_date_str = request.POST.get("expiry_date", "").strip()
        is_active = "is_active" in request.POST
        image = request.FILES.get("image")

        if not name:
            messages.error(request, "Category name is required.")
            return render(request, "admin_panel/category/edit_category.html", {"admin_name": request.user.fullname, "category": category})
            
        if Category.objects.filter(name__iexact=name, is_deleted=False).exclude(id=category.id).exists():
            messages.error(request, f"A category named '{name}' already exists.")
            return render(request, "admin_panel/category/edit_category.html", {"admin_name": request.user.fullname, "category": category})

        if len(description) > 500:
            messages.error(request, "Category description cannot exceed 500 characters.")
            return render(request, "admin_panel/category/edit_category.html", {"admin_name": request.user.fullname, "category": category})
    
        try:
            discount = int(discount_str) if discount_str else 0
            if discount < 0 or discount > 100:
                raise ValueError
        except ValueError:
            messages.error(request, "Discount must be a number between 0 and 100.")
            return render(request, "admin_panel/category/edit_category.html", {"admin_name": request.user.fullname, "category": category})

        expiry_date = None
        if expiry_date_str:
            try:
                expiry_date = datetime.strptime(expiry_date_str, "%d-%m-%Y").date()
            except ValueError:
                messages.error(request, "Expiry date must be in DD-MM-YYYY format.")
                return render(request, "admin_panel/category/edit_category.html", {"admin_name": request.user.fullname, "category": category})
    
        
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
        

    
        
        
            
        
        
        

            
