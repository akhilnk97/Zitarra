# ZITARRA — Handcrafted Musical Instruments & Premium Gear

![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-5.x%20%2F%206.x-green?logo=django&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14%2B-336791?logo=postgresql&logoColor=white)
![Razorpay](https://img.shields.io/badge/Payments-Razorpay-0C2340?logo=razorpay&logoColor=white)
![TailwindCSS](https://img.shields.io/badge/TailwindCSS-v3-38B2AC?logo=tailwind-css&logoColor=white)

Zitarra is an enterprise-grade e-commerce web platform engineered specifically for handcrafted professional musical instruments, boutique acoustic and electric guitars, traditional Indian percussion, and high-fidelity musician accessories.

Designed with **Django**, **PostgreSQL**, and vanilla JavaScript with tailored Tailwind styling, Zitarra delivers a fast, responsive shopping experience for musicians, paired with a comprehensive administrative command center for store managers.

---

## Table of Contents

1. [Key Architecture & Highlights](#key-architecture--highlights)
2. [Feature Matrix](#feature-matrix)
   - [Storefront & Customer Features](#storefront--customer-features)
   - [Admin Panel & Store Operations](#admin-panel--store-operations)
3. [Technology Stack](#technology-stack)
4. [Prerequisites](#prerequisites)
5. [Step-by-Step Installation & Setup](#step-by-step-installation--setup)
   - [1. Clone the Repository](#1-clone-the-repository)
   - [2. Set Up Virtual Environment](#2-set-up-virtual-environment)
   - [3. Install Python Dependencies](#3-install-python-dependencies)
   - [4. Environment Variables Configuration (.env)](#4-environment-variables-configuration-env)
   - [5. PostgreSQL Database Creation](#5-postgresql-database-creation)
   - [6. Execute Migrations](#6-execute-migrations)
   - [7. Create Administrator / Superuser](#7-create-administrator--superuser)
   - [8. Collect Static Files (Optional for Dev)](#8-collect-static-files-optional-for-dev)
   - [9. Launch the Development Server](#9-launch-the-development-server)
6. [Application Routing & Default Endpoints](#application-routing--default-endpoints)
7. [Comprehensive Project Structure](#comprehensive-project-structure)
   - [Directory Tree](#directory-tree)
   - [Core Apps & Modules Breakdown](#core-apps--modules-breakdown)
8. [Core Architectural Workflows](#core-architectural-workflows)
   - [Multi-Variant Inventory & Atomic Concurrency](#multi-variant-inventory--atomic-concurrency)
   - [Multi-Channel Checkout & Payments](#multi-channel-checkout--payments)
   - [Return Inspection & Automated Wallet Refunds](#return-inspection--automated-wallet-refunds)
   - [Dynamic Frontend & Sliding Toast Feedback](#dynamic-frontend--sliding-toast-feedback)
9. [Troubleshooting & Common Pitfalls](#troubleshooting--common-pitfalls)
10. [License & Contributing](#license--contributing)

---

## Key Architecture & Highlights

- **True Product & Multi-Variant Hierarchy**:
  - Follows production e-commerce specifications (similar to Amazon / Shopify architecture).
  - The `Product` model represents the master parent entity (e.g. *Varanasi Pro Sitar*).
  - The `ProductVariant` model represents purchasable color/finish variations with unique SKUs, color hex swatches, dedicated image galleries, specific prices, and isolated stock quantities.
- **Strict Variant-Level Stock Enforcement**:
  - Stock validation occurs exclusively at the variant level.
  - Zero-stock variants are dynamically flagged as out-of-stock, eliminating accidental over-selling.
- **Universal Inventory Synchronization**:
  - Checkout automatically decrements `variant.stock -= quantity` and synchronizes parent `product.stock` across all payment pathways:
    - **Cash on Delivery (COD)**
    - **Zitarra Digital Wallet**
    - **Razorpay Online Payment Gateway**
- **Concurrency Safety via Database Row Locks**:
  - Employs `select_for_update()` inside `transaction.atomic()` blocks during checkout and cancellation to guarantee zero race conditions and prevent double-spending.
- **Automated Stock Restoration & Wallet Refunds**:
  - Customer and admin order cancellations restore `variant.stock += quantity` and recalibrate parent product totals.
  - Approved return completions automatically restore inventory and credit the customer's wallet ledger with real-time transaction logs.

---

## Feature Matrix

### Storefront & Customer Features

1. **Authentication & Security**:
   - Secure email & password registration with email verification OTP (time-limited expiration).
   - Google Social OAuth 2.0 single sign-on via `django-allauth`.
   - Forgot/reset password with OTP verification.
   - Account status protection (blocked/inactive users immediately barred from authenticated workflows).
2. **Catalog & Interactive PDP (Product Detail Page)**:
   - Dynamic product search, category browsing, brand filtering, price sliders, and multi-parameter sorting (Popularity, Price Low/High, Rating, A-Z/Z-A, New Arrivals).
   - Interactive Color Variant Switcher with hex swatches, reactive SKU and stock counter updates, and dedicated high-resolution multi-image galleries.
   - Dynamic image zoom, pan-on-hover, and thumbnail carousel.
   - Star ratings and customer product reviews.
3. **Cart & Wishlist (AJAX-Enabled)**:
   - Real-time stock availability check (rejects out-of-stock items, prevents over-limit quantities per user).
   - Asynchronous Wishlist add/remove without full-page reloads, featuring instant icon toggles and badge counter synchronization.
   - One-click migration of wishlist items directly into the cart.
4. **Checkout & Multi-Channel Payments**:
   - Multi-address book (Add, edit, delete, set default delivery address with field validations).
   - **Cash on Delivery (COD)** with configurable order amount thresholds (e.g., restricted for high-value orders).
   - **Razorpay Payment Gateway**: Seamless popup modal supporting UPI, Credit/Debit Cards, Net Banking, and Wallets with cryptographic HMAC signature verification.
   - **Zitarra Digital Wallet**: Instant one-click debit checkout from user's internal stored balance.
   - Automated inventory deduction and order status management (`Pending`, `Confirmed`).
5. **Discounts, Coupons & Referral Rewards**:
   - Interactive coupon application at checkout with minimum purchase validation and per-user usage limits.
   - Category-wide discount campaigns and product-level promotional offers with automatic best-discount calculations.
   - Referral program awarding wallet credits to both referrer and referee upon successful order delivery.
6. **Orders, Invoices & Returns**:
   - Order history timeline with detailed step-by-step shipment tracking (`Pending`, `Confirmed`, `Processing`, `Shipped`, `Delivered`, `Cancelled`, `Returned`).
   - Item-level and whole-order cancellation with instant automated wallet refund.
   - Delivered item return request portal with mandatory photo defect/proof upload.
   - Professional, printable PDF invoice generation with tax calculations, coupon allocation, and variant breakdown.

### Admin Panel & Store Operations

1. **Analytical Dashboard**:
   - Real-time revenue analytics, total sales, daily/monthly revenue trends, pending returns counter, and order status breakdown.
   - Top 10 Best-Selling Products, Top Categories, and Top Brands analytics with custom date range filters.
2. **Product & Variant Management**:
   - Interactive multi-image cropping with **Cropper.js** (mandatory 3 to 5 cropped images per variant).
   - Color picker with auto-suggested palette swatches, hex code input, custom finish names, and SKU management.
   - Parent product overview card detailing all associated color variants and aggregated inventory.
3. **Category & Brand Management**:
   - Category creation, description, custom imagery, active toggling, and category-level discount offers with expiry dates.
   - Brand management with status control and catalog association.
4. **Offer & Coupon Engine**:
   - Promotional Offers module supporting category offers and product offers with auto-computed best discount rules.
   - Coupon management with custom code, percentage/flat discounts, minimum spend, expiry date validation, and user quotas.
5. **Order Fulfillment Pipeline**:
   - Complete order list with multi-parameter status filter (`Delivered`, `Confirmed`, `Shipped`, `Cancelled`, `Returned`).
   - Order details view with itemized transitions, expected delivery dates, pickup date scheduling, and customer communication notes.
6. **Return Requests Management**:
   - Centralized review portal for return requests with customer-submitted proof photos.
   - Workflow actions: *Approve Request*, *Schedule Pickup Date*, *Complete Return & Refund*, or *Reject Request* with administrative notes.
7. **Sales Reports**:
   - Filter sales reports by custom date range, daily, weekly, or monthly periods.
   - One-click export to **PDF** (via ReportLab) and **Microsoft Excel (.xlsx)** (via OpenPyXL) formats.

---

## Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Backend Framework** | Python 3.11+, Django 5.x / 6.x | Core Web MVC framework & ORM |
| **Relational Database** | PostgreSQL 14+ | Relational data persistence with ACID guarantees |
| **Database Driver** | `psycopg` (v3) / `psycopg-binary` | Next-generation PostgreSQL adapter for Python |
| **Authentication** | Django Auth & `django-allauth` | Dual backends: Custom email model + Google Social OAuth 2.0 |
| **Payment Processing** | Razorpay Python SDK & Checkout.js | Online payment gateway & webhook/signature validation |
| **Image Processing** | Pillow (PIL) & Cropper.js | Image validation, multi-aspect cropping & variant galleries |
| **Document Generation**| ReportLab & OpenPyXL | Printable PDF invoices, Sales PDF & Excel spreadsheets |
| **Environment Management** | `python-dotenv` | Twelve-Factor application environment variable isolation |
| **Frontend & Styling** | HTML5, Vanilla CSS3, Tailwind CSS | Responsive, mobile-first storefront & admin interface |
| **UI Components** | SweetAlert2, Dynamic Toast, Canvas Confetti | User alerts, micro-animations, celebration effects |

---

## Prerequisites

Before setting up Zitarra, ensure the following software is installed on your local workstation:

1. **Python 3.11+**:
   - Verify with: `python --version` (or `python3 --version` on Unix).
2. **PostgreSQL 14+**:
   - Ensure the PostgreSQL server is running locally (default port `5432`).
   - Verify with: `psql --version`.
3. **Git**:
   - Verify with: `git --version`.
4. **Google Account (Optional)**:
   - For Google OAuth 2.0 single sign-on testing.
5. **Razorpay Test Account (Optional)**:
   - For testing online card/UPI payments in test mode.

---

## Step-by-Step Installation & Setup

### 1. Clone the Repository

Clone the project repository to your local machine and navigate into the root directory:

```bash
git clone https://github.com/akhilnk97/Zitarra.git
cd Zitarra
```

### 2. Set Up Virtual Environment

It is strongly recommended to isolate project dependencies inside a Python virtual environment.

**On Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

*Note for Windows users:* If PowerShell displays an execution policy error, enable script execution for the current session:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
.\venv\Scripts\Activate.ps1
```

**On Windows (Command Prompt `cmd`):**
```cmd
python -m venv venv
venv\Scripts\activate.bat
```

**On Linux / macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Python Dependencies

With your virtual environment active, install all required packages:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

Verify that key dependencies (`Django`, `psycopg`, `pillow`, `razorpay`, `django-allauth`, `reportlab`, `openpyxl`) are successfully installed:
```bash
pip list
```

### 4. Environment Variables Configuration (`.env`)

Zitarra uses `python-dotenv` to load sensitive parameters from a root `.env` file. A sample configuration template is provided in `.env.example`.

Copy `.env.example` to create your active `.env` file:

**On Windows (PowerShell / CMD):**
```powershell
copy .env.example .env
```

**On Linux / macOS:**
```bash
cp .env.example .env
```

Open `.env` in your editor and configure the variables according to your local setup:

```ini
# ==============================================================================
# Zitarra E-Commerce Platform - Environment Configuration
# ==============================================================================

# Django Core Settings
DEBUG=True
SECRET_KEY=django-insecure-your-super-secret-random-key-here-for-local-development

# PostgreSQL Database Configuration
DB_NAME=zitarra_db
DB_USER=postgres
DB_PASSWORD=your_postgres_password
DB_HOST=localhost
DB_PORT=5432

# Razorpay Payment Gateway Credentials (Test Keys)
RAZORPAY_KEY_ID=rzp_test_your_key_id
RAZORPAY_KEY_SECRET=your_razorpay_key_secret

# Email SMTP Configuration (Gmail SMTP for OTP & Email Notifications)
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_16_digit_google_app_password

# Google OAuth 2.0 Social Authentication (Optional)
GOOGLE_CLIENT_ID=your-google-oauth-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-oauth-client-secret
```

#### Detailed Environment Variable Guide:

| Variable | Required | Description | Example / Default |
|---|---|---|---|
| `DEBUG` | **Yes** | Enables Django debug mode for development | `True` |
| `SECRET_KEY` | **Yes** | Cryptographic signing key for sessions/tokens | Long randomized string |
| `DB_NAME` | **Yes** | PostgreSQL database name | `zitarra_db` |
| `DB_USER` | **Yes** | PostgreSQL username | `postgres` |
| `DB_PASSWORD` | **Yes** | PostgreSQL password for user | e.g. `postgres` or `admin` |
| `DB_HOST` | **Yes** | Database host | `localhost` |
| `DB_PORT` | **Yes** | Database connection port | `5432` |
| `RAZORPAY_KEY_ID` | Optional | Key ID from Razorpay Dashboard (Test Mode) | `rzp_test_xxxxxx` |
| `RAZORPAY_KEY_SECRET` | Optional | Key Secret from Razorpay Dashboard | `xxxxxxxxxxxxxx` |
| `EMAIL_HOST_USER` | Optional | Gmail address used to dispatch OTP verification emails | `store@gmail.com` |
| `EMAIL_HOST_PASSWORD` | Optional | 16-character Google App Password (not your Gmail login password) | `xxxx xxxx xxxx xxxx` |
| `GOOGLE_CLIENT_ID` | Optional | Google Cloud Console OAuth 2.0 Client ID | `xxxx.apps.googleusercontent.com` |
| `GOOGLE_CLIENT_SECRET` | Optional | Google Cloud Console OAuth 2.0 Client Secret | `GOCSPX-xxxxxx` |

> [!TIP]
> **Generating a secure Django SECRET_KEY:**
> Run the following one-liner in your terminal to generate a secure secret key:
> ```bash
> python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
> ```

> [!NOTE]
> **Gmail App Password Setup:**
> If testing email OTP functionality, standard Gmail accounts require 2-Step Verification to be enabled. Then navigate to *Google Account > Security > 2-Step Verification > App passwords* and generate an App Password for "Mail".

### 5. PostgreSQL Database Creation

Create the database in your local PostgreSQL instance:

**Using PostgreSQL interactive terminal (`psql`):**
```bash
psql -U postgres
```
Inside the `psql` console, execute:
```sql
CREATE DATABASE zitarra_db;
\q
```

Or via PowerShell / Bash in a single command:
```bash
psql -U postgres -c "CREATE DATABASE zitarra_db;"
```

### 6. Execute Migrations

Generate and apply all database migrations to initialize tables for authentication, products, orders, coupons, returns, wallet, and administrative modules:

```bash
python manage.py makemigrations
python manage.py migrate
```

Verify that all migrations apply with `OK` status.

### 7. Create Administrator / Superuser

Create a superuser account to access both the Django default admin interface and the custom Zitarra Admin Command Center:

```bash
python manage.py createsuperuser
```

Follow the interactive prompts to enter:
- **Email**: `admin@zitarra.com`
- **First Name / Last Name**: Admin User
- **Password**: Secure administrator password

### 8. Collect Static Files (Optional for Dev)

In development (`DEBUG = True`), Django serves static assets directly from the `static/` folder. If you wish to compile and verify all static assets:

```bash
python manage.py collectstatic --noinput
```

### 9. Launch the Development Server

Start the local Django development web server:

```bash
python manage.py runserver
```

Open your browser and navigate to:
```
http://127.0.0.1:8000/
```

You are now running the Zitarra platform!

---

## Application Routing & Default Endpoints

| Portal | URL Path | Description | Access Requirement |
|---|---|---|---|
| **Storefront Home** | `http://127.0.0.1:8000/home/` or `/` | Landing page, hero banners, curated collections | Public |
| **Catalog / Shop** | `http://127.0.0.1:8000/shop/` | Search, filters, sort, product grid | Public |
| **Product Detail** | `http://127.0.0.1:8000/shop/product/<slug>/` | Color variant selector, gallery, reviews, stock | Public |
| **User Sign-in** | `http://127.0.0.1:8000/login/` | Email & password customer sign in | Public / Anonymous |
| **User Registration**| `http://127.0.0.1:8000/register/` | Account registration with OTP email trigger | Public / Anonymous |
| **User OTP Verify** | `http://127.0.0.1:8000/verify-otp/` | OTP input modal with countdown timer | Registered User |
| **Shopping Cart** | `http://127.0.0.1:8000/cart/` | Variant-level quantity, pricing, checkout trigger | Authenticated User |
| **Wishlist** | `http://127.0.0.1:8000/wishlist/` | Saved favorites, one-click add to cart | Authenticated User |
| **Checkout** | `http://127.0.0.1:8000/checkout/` | Address selector, coupons, payment options | Authenticated User |
| **Customer Orders** | `http://127.0.0.1:8000/orders/` | Order history, tracking, cancellation, invoice PDF | Authenticated User |
| **Digital Wallet** | `http://127.0.0.1:8000/wallet/` | Balance ledger, referral earnings, refunds | Authenticated User |
| **Admin Login** | `http://127.0.0.1:8000/admin-panel/login/` | Admin backoffice credential authentication | Staff / Superuser |
| **Admin Dashboard** | `http://127.0.0.1:8000/admin-panel/dashboard/` | KPI cards, sales analytics, top products/brands | Staff / Superuser |
| **Admin Products** | `http://127.0.0.1:8000/admin-panel/products/` | Product catalog, variant image cropper, stock | Staff / Superuser |
| **Admin Orders** | `http://127.0.0.1:8000/admin-panel/orders/` | Order fulfillment, delivery dates, status changes | Staff / Superuser |
| **Admin Returns** | `http://127.0.0.1:8000/admin-panel/returns/` | Defect photo review, pickup schedule, refunds | Staff / Superuser |
| **Admin Sales** | `http://127.0.0.1:8000/admin-panel/sales/` | Custom reports, PDF & Excel export | Staff / Superuser |
| **Django Admin** | `http://127.0.0.1:8000/admin/` | Standard Django low-level administration | Superuser |

---

## Comprehensive Project Structure

### Directory Tree

```
Zitarra/
├── .env.example                     # Environment template for local configuration
├── manage.py                        # Django command-line execution entrypoint
├── requirements.txt                 # Project Python dependencies
├── README.md                        # Primary project documentation
│
├── config/                          # Project configuration root
│   ├── __init__.py                  # Imports default settings
│   ├── urls.py                      # Main URL routing and endpoint dispatcher
│   ├── wsgi.py                      # WSGI server entrypoint
│   └── settings/                    # Modular settings package
│       ├── __init__.py              # Default settings loader (points to local.py)
│       ├── base.py                  # Core settings (apps, middleware, templates, auth, razorpay)
│       ├── local.py                 # Local development database, debug, email SMTP
│       └── production.py            # Hardened production settings (HTTPS, static caching)
│
├── common/                          # Shared utilities across storefront and admin
│   ├── adapters.py                  # Custom django-allauth adapter suppressing redundant alerts
│   ├── decorators.py                # View guards (@admin_required, @user_required, etc.)
│   └── services.py                  # Reusable business logic (stock validation, invoice helpers)
│
├── admin_panel/                     # Administrative backoffice applications
│   ├── authentication/              # Admin login, session validation & logout
│   ├── banners/                     # Homepage promotional hero banner manager
│   ├── brands/                      # Brand creation, active toggling & metadata
│   ├── category/                    # Categories, hierarchical grouping & category offers
│   ├── coupons/                     # Discount coupons, minimum purchase & usage limits
│   ├── dashboard/                   # Revenue KPIs, sales graphs & top selling metrics
│   ├── offers/                      # Product and category discount campaigns
│   ├── orders/                      # Order fulfillment pipeline & status transitions
│   ├── products/                    # Product CRUD, color variants, SKU & Cropper.js images
│   ├── returns/                     # Return inspection portal, photo proof verification
│   ├── sales/                       # Sales reports with PDF & Excel (.xlsx) export
│   └── users/                       # Customer account management (block/unblock/view)
│
├── user_panel/                      # Storefront customer-facing applications
│   ├── authentication/              # Custom User model, registration, login, OTP & OAuth
│   ├── banners/                     # Hero banner presentation queries
│   ├── cart/                        # Cart persistence, quantity updates, stock checks
│   ├── coupons/                     # Checkout coupon validation & discount calculation
│   ├── home/                        # Landing page, featured highlights & custom 404 handler
│   ├── orders/                      # Checkout flow, Razorpay handler, order history & PDF invoices
│   ├── profiles/                    # Customer profile, multi-address book management
│   ├── returns/                     # Return request submission with defect image uploads
│   ├── shop/                        # Catalog browsing, facet filtering, search & PDP switcher
│   ├── wallet/                      # Digital wallet, transaction ledger & referral bonuses
│   └── wishlist/                    # Asynchronous wishlist management with AJAX
│
├── templates/                       # HTML template hierarchy
│   ├── 404.html                     # Custom styled 404 error page
│   ├── emails/                      # HTML email templates (OTP verification, welcome messages)
│   ├── admin_panel/                 # Admin interface templates
│   │   ├── base.html                # Admin dashboard layout, sidebar & navigation
│   │   ├── authentication/          # Admin login view
│   │   ├── banners/                 # Banner creation and list templates
│   │   ├── brands/                  # Brand management templates
│   │   ├── category/                # Category listing & modal forms
│   │   ├── coupons/                 # Coupon creation and quota manager
│   │   ├── dashboard/               # Main dashboard with charts and tables
│   │   ├── offers/                  # Offer management interface
│   │   ├── orders/                  # Order listing and detail management views
│   │   ├── products/                # Product form, variant manager, Cropper.js modals
│   │   ├── returns/                 # Return request approval and photo review modal
│   │   ├── sales/                   # Sales report filter interface
│   │   └── users/                   # Customer table with status toggling
│   └── user/                        # Storefront customer templates
│       ├── base/                    # Customer base layout (head, footer, dynamic toast)
│       ├── partials/                # Reusable header/navbars (navbar_home, navbar_shop)
│       ├── authentication/          # Customer login, register, OTP verification, forgot password
│       ├── cart/                    # Shopping cart table, quantity adjusters, subtotal summary
│       ├── checkout/                # Multi-step checkout, address picker, payment modal
│       ├── orders/                  # Order list, tracking timeline, invoice PDF download
│       ├── profile/                 # Profile editor, address book modal
│       ├── returns/                 # Return filing form with photo upload
│       ├── shop/                    # Shop catalog, filter sidebar, product_detail (PDP)
│       ├── wallet/                  # Wallet balance card, transaction history table
│       └── wishlist/                # Wishlist grid with direct 'Add to Cart' actions
│
├── static/                          # Static assets
│   ├── css/                         # Custom CSS rules, typography, animation keyframes
│   ├── js/                          # Client-side scripts (AJAX wishlist, Cropper.js, image zoom)
│   └── images/                      # Default logos, placeholder assets, background textures
│
└── media/                           # User-generated and dynamic file uploads
    ├── products/                    # Cropped high-resolution product variant images
    ├── categories/                  # Category banner icons and thumbnails
    ├── banners/                     # Storefront hero banners
    ├── returns/                     # Customer-uploaded return defect proof images
    └── invoices/                    # Cached or generated order invoice documents
```

---

### Core Apps & Modules Breakdown

#### 1. Configuration Package (`config/`)
- **`config/settings/base.py`**: Declares all installed apps (split into `admin_panel` and `user_panel`), middleware stack, custom template context processors (`cart_item_count`, `wishlist_item_count`), session parameters (1-week retention), authentication backends, file upload limits (25MB to prevent memory truncation on high-res variant images), and Razorpay keys.
- **`config/settings/local.py`**: Extends `base.py` for local development. Sets `DEBUG = True`, binds the PostgreSQL database engine via environment variables, enables SMTP email credentials, and configures `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`.
- **`config/settings/production.py`**: Production overrides including security headers, SSL redirection, and optimized static asset handling.
- **`config/urls.py`**: Central URL routing combining storefront namespaces, admin panel routes, Django allauth endpoints, media file serving in debug mode, and a catch-all route mapping to `custom_404_view`.

#### 2. User Panel Apps (`user_panel/`)
- **`authentication`**: Defines custom `User` model (app label `'accounts'`) using email as the unique identifier. Handles email OTP registration, login/logout, password reset, and Google OAuth integration.
- **`shop`**: Powerhouse catalog app providing search, category and brand filters, price bounds, multi-parameter ordering, and the interactive Product Detail Page (PDP) with color variant switching.
- **`cart`**: Handles session and database cart management, real-time stock limits, maximum allowed quantities per user, and item price calculations.
- **`wishlist`**: Manages customer wishlists with AJAX support (no full page reload), updating navigation badges and heart icons dynamically.
- **`orders`**: Directs checkout, address selection, payment processing (COD, Wallet, Razorpay modal), order placement, invoice PDF generation (ReportLab), and order cancellations.
- **`wallet`**: Maintains customer digital wallets, tracking credit and debit transactions, automated refunds, and referral bonuses.
- **`returns`**: Enables customers to file return requests for delivered orders with mandatory photo defect uploads.

#### 3. Admin Panel Apps (`admin_panel/`)
- **`dashboard`**: Renders analytical metrics, revenue figures, pending orders, return requests, and best-performing products/brands.
- **`products`**: Full CRUD for master products and child `ProductVariant` entries. Integrates **Cropper.js** for 3–5 multi-angle cropped images per variant.
- **`category` & `brands`**: Manages taxonomy, active visibility states, and category-level discount campaigns.
- **`orders`**: Administrative fulfillment interface allowing staff to view orders, advance delivery stages, schedule pickups, or handle cancellations.
- **`returns`**: Dedicated return review portal displaying customer photo evidence with actions to approve, schedule pickup, complete refund, or reject.
- **`sales`**: Reporting hub generating filtered sales data with one-click export to PDF or Excel format.
- **`coupons` & `offers`**: Configures discount codes, percentage/flat discounts, minimum order constraints, validity dates, and automatic product/category offer calculations.

#### 4. Shared Utilities (`common/`)
- **`decorators.py`**: Clean access-control decorators (`@admin_required`, `@user_required`, `@guest_required`, etc.) to prevent privilege escalation.
- **`adapters.py`**: Custom `NoMessageAccountAdapter` suppressing redundant default Django-allauth messages in favor of custom UI toasts.
- **`services.py`**: Centralized service layer for complex business operations such as variant stock verification, price calculation after coupon discounts, and invoice layout generation.

---

## Core Architectural Workflows

### Multi-Variant Inventory & Atomic Concurrency

```
                        [ Master Product ]
                       (e.g., Dreadnought Guitar)
                                   |
         +-------------------------+-------------------------+
         |                                                   |
 [ ProductVariant A ]                                [ ProductVariant B ]
 Color: Vintage Sunburst                             Color: Natural Gloss
 Hex: #8B4513                                        Hex: #F5DEB3
 Stock: 5 (Tracked strictly)                         Stock: 0 (Out of stock)
 Gallery: 4 Cropped Photos                           Gallery: 4 Cropped Photos
```

When an order is placed:
1. An atomic transaction begins: `with transaction.atomic():`
2. The specific `ProductVariant` is queried using `select_for_update()` to lock the database row against concurrent read-writes.
3. If `variant.stock < ordered_quantity`, the transaction immediately aborts with an out-of-stock error.
4. If available:
   ```python
   variant.stock -= quantity
   variant.save()
   # Synchronize aggregated master product stock
   product.stock = sum(v.stock for v in product.variants.filter(is_active=True))
   product.save()
   ```
5. On cancellation or completed return, the exact inverse operation safely restores variant and product stock.

### Multi-Channel Checkout & Payments

```
                     +----------------------------+
                     |  Checkout Review & Pay     |
                     +--------------+-------------+
                                    |
            +-----------------------+-----------------------+
            |                       |                       |
     [ Cash on Delivery ]     [ Zitarra Wallet ]     [ Razorpay Online ]
            |                       |                       |
  Threshold validation     Checks wallet.balance    Razorpay order created
  Sets status: Confirmed   Deducts balance ledger   Modal checkout popup
  Decrements variant stock Decrements variant stock Verified via HMAC SHA256
```

### Return Inspection & Automated Wallet Refunds

1. **Submission**: Customer submits a return request for a delivered item, providing reason and uploading defect photos (`user_panel/returns/`).
2. **Review**: Admin reviews the request and inspects uploaded photos in the review portal (`admin_panel/returns/`).
3. **Approval**: Admin schedules a courier pickup date.
4. **Completion**: Upon physical receipt and inspection, admin clicks **Complete Return**:
   - Return status transitions to `Completed`.
   - Variant stock is restored: `variant.stock += quantity`.
   - Refund amount is automatically credited to the customer's `Wallet` with a detailed transaction log.

### Dynamic Frontend & Sliding Toast Feedback

- **Asynchronous Wishlist**: Adding/removing items from the wishlist triggers an async `fetch()` request. On receiving `{ success: true, action: 'added' | 'removed', wishlist_count: N }`, the DOM updates without page refresh:
  - Heart icon updates with filled/outline state.
  - Navbar badge (`#nav-wishlist-badge`) dynamically reflects the current count.
  - A right-to-left sliding toast alert slides into view from the right margin and smoothly dismisses after 3 seconds.

---

## Troubleshooting & Common Pitfalls

### 1. PostgreSQL Connection Refused (`connection to server at "localhost", port 5432 failed`)
- Ensure PostgreSQL service is started:
  - **Windows**: Open `services.msc` and ensure `postgresql-x64-<version>` is in the **Running** state.
  - **Linux**: Run `sudo systemctl status postgresql` (start with `sudo systemctl start postgresql`).
- Verify credentials in `.env` match your PostgreSQL superuser (`DB_USER`, `DB_PASSWORD`, `DB_PORT`).

### 2. Missing Database (`database "zitarra_db" does not exist`)
- Create the database in `psql`:
  ```sql
  CREATE DATABASE zitarra_db;
  ```

### 3. Email OTP Not Sending (`SMTPAuthenticationError`)
- Gmail requires a dedicated 16-character **App Password** when 2FA is active. Your regular Google account password will be rejected by Google SMTP.
- Ensure `EMAIL_HOST_USER` and `EMAIL_HOST_PASSWORD` are correctly specified in your `.env`.

### 4. Razorpay Modal Error (`Missing or Invalid Key ID`)
- Ensure `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET` in `.env` contain valid test credentials starting with `rzp_test_`.

### 5. Large Image Upload Failures (`RequestDataTooBig`)
- The project is pre-configured with `DATA_UPLOAD_MAX_MEMORY_SIZE = 26214400` (25MB) in `config/settings/base.py` to allow multi-image cropping with Cropper.js. Ensure your test images do not exceed this threshold.

---

## License & Contributing

- **License**: Developed for proprietary demonstration and production use.
- **Contributions**: Pull requests are welcome! For major changes, please open an issue first to discuss intended enhancements.

---

*Engineered with precision for musicians by the Zitarra Development Team.*