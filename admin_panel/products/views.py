import base64
from django.shortcuts import render, redirect, get_object_or_404
from django.core.files.base import ContentFile
from django.contrib import messages
from django.views.decorators.cache import cache_control
from django.db.models import Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from admin_panel.decorators import admin_required
from .models import Product, ProductImage
from admin_panel.category.models import Category


@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@admin_required
def admin_products_view(request):
    products_list = Product.objects.filter(is_deleted=False)

    # Get query parameters
    search = request.GET.get('search', '').strip()
    category_id = request.GET.get('category', '').strip()
    sort_by = request.GET.get('sort', 'newest').strip()

    # Search filter
    if search:
        products_list = products_list.filter(
            Q(name__icontains=search) | Q(description__icontains=search)
        )

    # Category filter
    if category_id:
        products_list = products_list.filter(category_id=category_id)

    # Sorting
    if sort_by == 'oldest':
        products_list = products_list.order_by('created_at')
    elif sort_by == 'name_asc':
        products_list = products_list.order_by('name')
    elif sort_by == 'name_desc':
        products_list = products_list.order_by('-name')
    else:  # newest
        products_list = products_list.order_by('-created_at')

    # Pagination: 10 items per page
    paginator = Paginator(products_list, 10)
    page_number = request.GET.get('page', 1)
    try:
        products = paginator.page(page_number)
    except PageNotAnInteger:
        products = paginator.page(1)
    except EmptyPage:
        products = paginator.page(paginator.num_pages)

    categories = Category.objects.filter(is_deleted=False, is_active=True)

    return render(request, 'admin_panel/products/products.html', {
        "products": products,
        "categories": categories,
        "search": search,
        "category_id": category_id,
        "sort_by": sort_by,
        "admin_name": request.user.fullname
    })


@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@admin_required
def admin_product_add_view(request):
    if request.method == "POST":
        name = request.POST.get("name")
        description = request.POST.get("description")
        price = request.POST.get("price")
        stock = request.POST.get("stock")
        category_id = request.POST.get("category")

        category = get_object_or_404(Category, id=category_id)

        is_active = "is_active" in request.POST

        product = Product.objects.create(
            name=name,
            description=description,
            price=price,
            stock=stock,
            category=category,
            is_active=is_active
        )

        cropped_images_data = request.POST.getlist("cropped_images")

        if len(cropped_images_data) < 3:
            messages.error(request, "You must upload at least 3 images.")
            product.delete()
            return redirect('admin_product_add')

        for i, img_str in enumerate(cropped_images_data):
            if img_str.startswith("data:image"):
                format, imgstr = img_str.split(";base64,")
                ext = format.split('/')[-1]
                image_file = ContentFile(base64.b64decode(imgstr), name=f"{product.id}_image_{i}.{ext}")
                ProductImage.objects.create(product=product, image=image_file)

        messages.success(request, "Product added successfully!")
        return redirect("admin_products")
            
    categories = Category.objects.filter(is_active=True)
    return render(request, "admin_panel/products/add_product.html", {
        "categories": categories,
        "admin_name": request.user.fullname
    })


@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@admin_required
def admin_product_edit_view(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_deleted=False)
    if request.method == "POST":
        product.name = request.POST.get("name")
        product.description = request.POST.get("description")
        product.price = request.POST.get("price")
        product.stock = request.POST.get("stock")
        category_id = request.POST.get("category")
        product.category = get_object_or_404(Category, id=category_id)
        product.is_active = "is_active" in request.POST
        product.save()

        # Handle updating or adding new images if any are uploaded
        cropped_images_data = request.POST.getlist("cropped_images")
        if cropped_images_data:
            # Delete old images if they uploaded a new set
            product.images.all().delete()
            for i, img_str in enumerate(cropped_images_data):
                if img_str.startswith("data:image"):
                    format, imgstr = img_str.split(";base64,")
                    ext = format.split('/')[-1]
                    image_file = ContentFile(base64.b64decode(imgstr), name=f"{product.id}_image_{i}.{ext}")
                    ProductImage.objects.create(product=product, image=image_file)

        messages.success(request, "Product updated successfully!")
        return redirect("admin_products")

    categories = Category.objects.filter(is_active=True)
    return render(request, "admin_panel/products/edit_product.html", {
        "product": product,
        "categories": categories,
        "admin_name": request.user.fullname
    })


@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@admin_required
def admin_product_delete_view(request, product_id):
    if request.method == "POST":
        product = get_object_or_404(Product, id=product_id)
        product.is_deleted = True
        product.save()
        messages.success(request, "Product deleted successfully!")
    return redirect("admin_products")