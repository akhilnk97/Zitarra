import base64
from django.shortcuts import render, redirect, get_object_or_404
from django.core.files.base import ContentFile
from django.contrib import messages
from django.db import transaction, models
from django.db.models import Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from common.decorators import admin_required
from common.services import save_base64_image
from .models import Product, ProductImage, ProductVariant, VariantImage
from admin_panel.category.models import Category


@admin_required
def admin_products_view(request):
    products_list = Product.objects.filter(is_deleted=False)

    search = request.GET.get('search', '').strip()
    category_id = request.GET.get('category', '').strip()
    sort_by = request.GET.get('sort', 'newest').strip()

    if search:
        products_list = products_list.filter(
            Q(name__icontains=search) | Q(description__icontains=search)
        )

    if category_id:
        products_list = products_list.filter(category_id=category_id)

    if sort_by == 'oldest':
        products_list = products_list.order_by('created_at')
    elif sort_by == 'name_asc':
        products_list = products_list.order_by('name')
    elif sort_by == 'name_desc':
        products_list = products_list.order_by('-name')
    else:  
        products_list = products_list.order_by('-created_at')

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


@admin_required
def admin_product_add_view(request):
    if request.method == "POST":
        category_id = request.POST.get("category")
        category = get_object_or_404(Category, id=category_id)
        
        # VALIDATE MAIN PRODUCT IMAGES (Before creating anything in DB)
        cropped_images_data = request.POST.getlist("cropped_images")
        if len(cropped_images_data) < 3 or len(cropped_images_data) > 5:
            messages.error(request, "YOU MUST UPLOAD AND CROP AT LEAST 3 IMAGES.")
            return redirect('admin_product_add')

        # VALIDATE VARIANTS (Before creating anything in DB)
        parsed_variants = []
        variant_indices_str = request.POST.get("variant_indices", "")
        if variant_indices_str:
            variant_indices = []
            for idx in variant_indices_str.split(","):
                idx = idx.strip()

                if idx.isdigit():
                    variant_indices.append(int(idx))
            
            for idx in variant_indices:
                v_name = request.POST.get(f"variant_name_{idx}", "").strip()
                v_color = request.POST.get(f"variant_color_{idx}", "").strip()
                v_price = request.POST.get(f"variant_price_{idx}", "").strip()
                v_stock = request.POST.get(f"variant_stock_{idx}", "").strip()
                v_image_data = request.POST.getlist(f"variant_images_{idx}")

                if v_name and v_color and v_stock:
                    is_base64 = len(v_image_data) > 0
                    img_list = v_image_data if is_base64 else request.FILES.getlist(f"variant_image_{idx}")

                    if len(img_list) < 3 or len(img_list) > 5:
                        messages.error(request, f"VARIANT '{v_name.upper()}': YOU MUST UPLOAD AND CROP AT LEAST 3 IMAGES.")
                        return redirect('admin_product_add')

                    try:
                        v_stock = int(v_stock)
                        if v_stock < 0:
                            v_stock = 0
                    except ValueError:
                        v_stock = 0    

                    try:
                        v_price = float(v_price) if v_price and float(v_price) > 0 else None
                    except ValueError:
                        v_price = None

                    parsed_variants.append({
                        "name": v_name,
                        "color_code": v_color,
                        "price": v_price,
                        "stock": v_stock,
                        "img_list": img_list,
                        "is_base64": is_base64
                    })  
        with transaction.atomic():
            product = Product.objects.create(
                name=request.POST.get("name"),
                description=request.POST.get("description"),
                price=request.POST.get("price"),
                stock=request.POST.get("stock"),
                category=category,
                is_active="is_active" in request.POST,
                highlights=request.POST.get("highlights", "").strip(),
                brand=request.POST.get("brand", "").strip(),
                offer=request.POST.get("offer", "").strip()
            )

            # Save Main Product Images using save_base64_image
            for i, img_str in enumerate(cropped_images_data):
                image_file = save_base64_image(img_str, f"{product.id}_image_{i}")
                if image_file:
                    ProductImage.objects.create(product=product, image=image_file)
            
            # Save Product Variants & Variant Images
            for v_data in parsed_variants:
                variant = ProductVariant.objects.create(
                    product=product,
                    name=v_data["name"],
                    color_code=v_data["color_code"],
                    price=v_data["price"],
                    stock=v_data["stock"]
                )

                for i, img in enumerate(v_data["img_list"]):
                    if v_data["is_base64"]:
                        image_file = save_base64_image(img, f"variant_{variant.id}_image_{i}")
                    else:
                        image_file = img
                    if image_file:
                        VariantImage.objects.create(variant=variant, image=image_file)

        messages.success(request, "Product added successfully!")
        return redirect('admin_products')  
    
    categories = Category.objects.filter(is_deleted=False, is_active=True)
    return render(request, 'admin_panel/products/add_product.html', {
        'categories': categories,
        'admin_name': request.user.fullname
    })


@admin_required
def admin_product_edit_view(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_deleted=False)
    if request.method == "POST":
        category_id = request.POST.get("category")
        category = get_object_or_404(Category, id=category_id)

        # VALIDATE NEW IMAGES FIRST (If uploaded)
        cropped_images_data = request.POST.getlist("cropped_images")
        if cropped_images_data:
            if len(cropped_images_data) < 3 or len(cropped_images_data) > 5:
                messages.error(request, "YOU MUST UPLOAD AND CROP AT LEAST 3 IMAGES.")
                return redirect('admin_product_edit', product_id=product.id)

        with transaction.atomic():
            product.name = request.POST.get("name")
            product.description = request.POST.get("description")
            product.price = request.POST.get("price")
            product.stock = request.POST.get("stock")
            product.category = category
            product.is_active = "is_active" in request.POST
            product.highlights = request.POST.get("highlights", "").strip()
            product.brand = request.POST.get("brand", "").strip()
            product.offer = request.POST.get("offer", "").strip()
            product.save()

            # Handle updating or adding new images if any are uploaded
            if cropped_images_data:
                # Delete old images only when new set is valid and saving
                product.images.all().delete()
                for i, img_str in enumerate(cropped_images_data):
                    image_file = save_base64_image(img_str, f"{product.id}_image_{i}")
                    if image_file:
                        ProductImage.objects.create(product=product, image=image_file)

        messages.success(request, "Product updated successfully!")
        return redirect("admin_products")

    categories = Category.objects.filter(is_active=True)
    return render(request, "admin_panel/products/edit_product.html", {
        "product": product,
        "categories": categories,
        "admin_name": request.user.fullname
    })


@admin_required
def admin_product_delete_view(request, product_id):
    if request.method == "POST":
        product = get_object_or_404(Product, id=product_id)
        product.is_deleted = True
        product.save()
        messages.success(request, "Product deleted successfully!")
    return redirect("admin_products")


@admin_required
def admin_product_variants_view(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_deleted=False)
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        color_code = request.POST.get("color_code", "").strip()
        price = request.POST.get("price", "").strip()
        stock = request.POST.get("stock", "").strip()

        if not name or not color_code or not stock:
            messages.error(request, "Please fill in all required fields.")
            return redirect('admin_product_variants', product_id=product.id)

        try:
            stock = int(stock)
            if stock < 0:
                raise ValueError()
        except ValueError:
            messages.error(request, "Stock must be a non-negative integer.")
            return redirect('admin_product_variants', product_id=product.id)

        if price:
            try:
                price = float(price)
                if price <= 0:
                    raise ValueError()
            except ValueError:
                messages.error(request, "Price must be a positive number.")
                return redirect('admin_product_variants', product_id=product.id)
        else:
            price = None

        # EXTRACT IMAGES (Base64 cropped strings or standard files)
        variant_images_data = request.POST.getlist("images")
        is_base64 = len(variant_images_data) > 0
        img_list = variant_images_data if is_base64 else request.FILES.getlist("images")

        if len(img_list) < 3 or len(img_list) > 5:
            messages.error(request, "YOU MUST UPLOAD AND CROP AT LEAST 3 IMAGES.")
            return redirect('admin_product_variants', product_id=product.id)

        with transaction.atomic():
            variant = ProductVariant.objects.create(
                product=product,
                name=name,
                color_code=color_code,
                price=price,
                stock=stock
            )

            for i, img in enumerate(img_list):
                if is_base64:
                    image_file = save_base64_image(img, f"variant_{variant.id}_image_{i}")
                else:
                    image_file = img

                if image_file:
                    VariantImage.objects.create(variant=variant, image=image_file)

        messages.success(request, "Product variant added successfully!")
        return redirect('admin_product_variants', product_id=product.id)

    variants = product.variants.filter(is_deleted=False)
    return render(request, "admin_panel/products/variants.html", {
        "product": product,
        "variants": variants,
        "admin_name": request.user.fullname
    })


@admin_required
def admin_variant_delete_view(request, variant_id):
    if request.method == "POST":
        variant = get_object_or_404(ProductVariant, id=variant_id, is_deleted=False)
        variant.is_deleted = True
        variant.save()
        messages.success(request, "Product variant deleted successfully!")
        return redirect('admin_product_variants', product_id=variant.product.id)
    return redirect('admin_products')


@admin_required
def admin_variant_toggle_view(request, variant_id):
    if request.method == "POST":
        variant = get_object_or_404(ProductVariant, id=variant_id, is_deleted=False)
        variant.is_active = not variant.is_active
        variant.save()
        status_str = "enabled" if variant.is_active else "disabled"
        messages.success(request, f"Product variant '{variant.name}' has been {status_str} successfully!")
        return redirect('admin_product_variants', product_id=variant.product.id)
    return redirect('admin_products')


@admin_required
def admin_variant_add_select_view(request):
    if request.method == "POST":
        product_id = request.POST.get("product_id")
        if product_id:
            return redirect('admin_product_variants', product_id=product_id)
    products = Product.objects.filter(is_deleted=False).order_by('name')
    return render(request, "admin_panel/products/select_product_for_variant.html", {
        "products": products,
        "admin_name": request.user.fullname
    })