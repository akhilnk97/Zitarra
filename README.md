# ZITARRA — Mastercraft Musical Instruments & Accessories

**Zitarra** is a full-featured, enterprise-grade e-commerce platform built specifically for handcrafted musical instruments, boutique acoustic & electric guitars, classical Indian string & percussion instruments, and premium musician accessories.

Designed with clean software engineering patterns, Zitarra pairs a fast, responsive, and visually stunning storefront with a comprehensive administration command center for full catalog, order fulfillment, discount, and inventory control.

---

## Table of Contents

- [Core Architectural Highlights](#core-architectural-highlights)
- [Feature Matrix](#feature-matrix)
  - [Customer Storefront](#customer-storefront)
  - [Admin Command Center](#admin-command-center)
- [Technology Stack](#technology-stack)
- [Detailed Project Structure](#detailed-project-structure)
- [Installation & Setup Guide](#installation--setup-guide)
  - [1. Prerequisites](#1-prerequisites)
  - [2. Clone Repository](#2-clone-repository)
  - [3. Virtual Environment Setup](#3-virtual-environment-setup)
  - [4. Install Dependencies](#4-install-dependencies)
  - [5. PostgreSQL Database Setup](#5-postgresql-database-setup)
  - [6. Environment Configuration (.env)](#6-environment-configuration-env)
  - [7. Apply Database Migrations](#7-apply-database-migrations)
  - [8. Create Administrative Superuser](#8-create-administrative-superuser)
  - [9. Start Development Server](#9-start-development-server)
- [External Services Setup](#external-services-setup)
  - [Razorpay Gateway](#razorpay-gateway)
  - [Google OAuth 2.0](#google-oauth-20)
  - [SMTP Email / OTP Service](#smtp-email--otp-service)
- [Application Endpoints](#application-endpoints)

---

## Core Architectural Highlights

- **Master Product & Variant Hierarchy**:
  - Implements industry-standard multi-variant architecture (e.g. Amazon / Nike).
  - The parent `Product` model represents the core instrument specification.
  - The child `ProductVariant` model captures purchasable finishes, hex color codes, independent SKUs, color-specific image galleries (3 to 5 cropped images), and dedicated stock quantities.
- **Strict Variant-Level Stock Enforcement**:
  - Out-of-stock items and depleted variants are blocked from checkout and disabled dynamically on the Product Detail Page (PDP), Cart, and Wishlist.
- **Universal Inventory & Ledger Synchronization**:
  - Real-time stock decrement occurs simultaneously across all payment methods (**Razorpay**, **COD**, and **Digital Wallet**).
  - Database row locks (`select_for_update()`) inside atomic transactions prevent race conditions and inventory overselling under high concurrency.
- **Automated Stock Restoration & Refunds**:
  - Order cancellations and returned items immediately restore inventory levels (`variant.stock += quantity`) and issue ledger-backed refunds to the user's digital wallet.
- **Universal Case-Insensitive Search**:
  - Search queries across User and Admin panels operate case-insensitively (`__icontains`) with intelligent multi-word token matching across names, descriptions, categories, brands, and order numbers.
- **Strict Data Sanitization**:
  - Real-time client and backend validations prevent irregular spacing, consecutive spaces, and illegal special characters across all customer and administrative forms.

---

## Feature Matrix

### Customer Storefront

1. **Authentication & Security**:
   - Email/password authentication with time-limited OTP verification.
   - Google Social OAuth 2.0 single sign-on via `django-allauth`.
   - Forgot/reset password recovery workflow with OTP authorization.
   - Account status tracking (Active, Blocked, Soft-deleted).
2. **Catalog & Interactive PDP**:
   - Comprehensive instrument catalog with case-insensitive search, category filtering, multi-brand selection, price range dual-slider, and multiple sorting rules.
   - Dynamic variant switcher with live hex swatch indicators, stock counters, and image gallery updates.
   - High-resolution image zoom and multi-angle viewing.
3. **Cart & Wishlist**:
   - Real-time stock validation preventing over-limit quantities.
   - Dedicated variant SKU and color preview in cart items.
   - Instant wishlist management with one-click migration to cart.
4. **Checkout & Multi-Payment Options**:
   - Address Book with **Auto City/State Detection** via Postal Pincode API (`api.postalpincode.in`).
   - Multiple payment rails:
     - **Razorpay Online Gateway** (Cards, UPI, NetBanking, Wallets).
     - **Zitarra Digital Wallet** (instant one-click debit).
     - **Cash on Delivery (COD)** with minimum/maximum threshold safety limits.
   - Interactive Coupon application with minimum spend requirements and user quotas.
   - Payment failure recovery page with active coupon retention and one-click payment retry.
5. **Orders, Invoices & Returns**:
   - Step-by-step order tracking timeline (Pending, Confirmed, Shipped, Delivered, Cancelled, Returned).
   - Instant automated wallet refund upon user or admin cancellation.
   - Delivered item return request system with defect proof image uploads.
   - Clean, professional, downloadable PDF tax invoices generated via `ReportLab`.

### Admin Command Center

1. **Analytical Dashboard**:
   - Real-time sales metrics, revenue charts, order counts, pending returns, and inventory status.
   - Top 10 Best-Selling Products, Top Categories, and Top Brands analytics.
2. **Product & Variant Suite**:
   - Multi-image cropping with **Cropper.js** (enforcing 3 to 5 images per variant).
   - Color picker with finish name suggestions, SKU auto-assignment, and stock management.
3. **Categories & Brands**:
   - Full CRUD management with active/inactive toggles, image uploads, and category-level discount campaigns with expiry limits.
4. **Coupon & Offer Engine**:
   - Category and Product promotional offers with automated discount calculations.
   - Custom discount coupons with percentage/flat reductions, usage limits, and validity dates.
5. **Order Fulfillment & Returns**:
   - Centralized order fulfillment with status updates (Confirmed, Shipped, Delivered, Cancelled).
   - Customer return inspection workflow: Approve, Schedule Pickup, Complete & Refund, or Reject with notes.
6. **Sales Reporting**:
   - Filterable sales performance reports by daily, weekly, monthly, or custom date ranges.
   - Instant export to **PDF** and **Microsoft Excel (.xlsx)**.

---

## Technology Stack

| Layer | Technology |
|---|---|
| **Backend Framework** | Python 3.11+, Django 5.x / 6.x |
| **Relational Database** | PostgreSQL 14+ with `psycopg3` driver |
| **Authentication** | Django Auth, Django Allauth (Google OAuth 2.0) |
| **Payment Gateway** | Razorpay Python SDK & Razorpay Checkout.js |
| **Image Processing** | Pillow (PIL), Cropper.js |
| **Document Generation** | ReportLab (PDF Invoices & Reports), OpenPyXL (Excel Reports) |
| **Frontend & Styling** | HTML5, Vanilla CSS3, Tailwind CSS, Modern JavaScript (ES6+) |
| **External APIs** | Postal Pincode API (`api.postalpincode.in`) |

---

## Detailed Project Structure

```
Zitarra/
├── admin_panel/                  # Administrative management backoffice
│   ├── authentication/           # Admin login, session security & decorators
│   ├── banners/                  # Promotional hero banner management
│   ├── brands/                   # Instrument brand registry & status control
│   ├── category/                 # Product category taxonomy & category discounts
│   ├── coupons/                  # Coupon creation, limits & campaign management
│   ├── dashboard/                # Analytics, revenue charts & top performers
│   ├── offers/                   # Product-level & category-level promotional offers
│   ├── orders/                   # Order fulfillment pipeline & shipment status
│   ├── products/                 # Master products & color variant management
│   ├── returns/                  # Return request inspection & approval workflow
│   ├── sales/                    # Sales reporting, date filtering, PDF & Excel export
│   └── users/                    # Customer account management & block controls
│
├── user_panel/                   # Customer-facing storefront modules
│   ├── authentication/           # Registration, login, OTP verification & social auth
│   ├── banners/                  # Storefront banner endpoints
│   ├── cart/                     # Shopping cart with real-time stock sync
│   ├── coupons/                  # Customer coupon application & discount validation
│   ├── home/                     # Homepage, landing page & 404 error views
│   ├── orders/                   # Checkout, Razorpay callback, invoices & order history
│   ├── profiles/                 # User profile, password management & address book
│   ├── returns/                  # Return request filing & proof upload
│   ├── shop/                     # Product catalog, search, filters, sorting & PDP
│   ├── wallet/                   # Digital wallet balance, top-up & transaction ledger
│   └── wishlist/                 # Customer wishlist & cart migration
│
├── common/                       # Shared platform utilities & services
│   ├── decorators.py             # Role-based access control (@admin_required, @user_member_required)
│   ├── services.py               # Validation suite, OTP dispatch, mailer, order math
│   └── utils.py                  # Formatters, slug generators & helpers
│
├── config/                       # Core Django project configuration
│   ├── settings.py               # Main application settings, DB, Auth, Razorpay configs
│   ├── urls.py                   # Master URL routing table
│   ├── wsgi.py                   # WSGI deployment entrypoint
│   └── asgi.py                   # ASGI entrypoint
│
├── templates/                    # Server-rendered HTML templates
│   ├── admin_panel/              # Administrative templates (Dashboard, Products, Orders, etc.)
│   └── user/                     # Customer storefront templates (Home, Shop, Checkout, etc.)
│
├── static/                       # Static assets (CSS, JS, brand logos, icons)
├── media/                        # User-uploaded files (Product images, cropped variants, return proofs)
├── manage.py                     # Django administrative CLI
├── requirements.txt              # Production Python package dependencies
├── .env.example                  # Environment variables template
└── README.md                     # Project documentation
```

---

## Installation & Setup Guide

Follow these instructions to configure and run Zitarra locally.

### 1. Prerequisites

Ensure the following tools are installed on your machine:
- **Python 3.11** or higher: `python --version`
- **PostgreSQL 14** or higher: `psql --version`
- **Git**: `git --version`

---

### 2. Clone Repository

```bash
git clone https://github.com/your-username/Zitarra.git
cd Zitarra
```

---

### 3. Virtual Environment Setup

Create and activate an isolated Python virtual environment:

**On Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**On Windows (Command Prompt):**
```cmd
python -m venv venv
venv\Scripts\activate.bat
```

**On macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

---

### 4. Install Dependencies

Upgrade pip and install all required project packages:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

### 5. PostgreSQL Database Setup

Log in to your local PostgreSQL server and create a dedicated database:

```bash
psql -U postgres
```

Inside the PostgreSQL prompt:
```sql
CREATE DATABASE zitarra_db;
CREATE USER zitarra_user WITH PASSWORD 'your_secure_password';
ALTER ROLE zitarra_user SET client_encoding TO 'utf8';
ALTER ROLE zitarra_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE zitarra_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE zitarra_db TO zitarra_user;
\q
```

---

### 6. Environment Configuration (.env)

Copy the sample environment file to create your active `.env`:

**Windows:**
```cmd
copy .env.example .env
```

**macOS / Linux:**
```bash
cp .env.example .env
```

Open `.env` in your text editor and fill in your local credentials:

```ini
# Django Core
DEBUG=True
SECRET_KEY=your-custom-django-secret-key-change-in-production

# PostgreSQL Database Configuration
DB_NAME=zitarra_db
DB_USER=postgres
DB_PASSWORD=your_postgres_password
DB_HOST=localhost
DB_PORT=5432

# Razorpay Payment Gateway Credentials
RAZORPAY_KEY_ID=rzp_test_your_key_id
RAZORPAY_KEY_SECRET=your_razorpay_key_secret

# Email SMTP Configuration (Gmail or custom SMTP for OTPs)
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_app_specific_password

# Google OAuth Social Authentication (Optional)
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

---

### 7. Apply Database Migrations

Apply all schema migrations to create the database tables:

```bash
python manage.py makemigrations
python manage.py migrate
```

---

### 8. Create Administrative Superuser

Create an administrative account to access both the custom Admin Command Center and the default Django admin:

```bash
python manage.py createsuperuser
```

Provide your desired username, email, full name, and password when prompted.

---

### 9. Start Development Server

Launch the Django local development server:

```bash
python manage.py runserver
```

Once started, open your browser and navigate to:
- **Customer Storefront**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Admin Command Center**: [http://127.0.0.1:8000/admin-panel/](http://127.0.0.1:8000/admin-panel/)
- **Django Default Admin**: [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)

---

## External Services Setup

### Razorpay Gateway
1. Sign up for a [Razorpay Dashboard](https://dashboard.razorpay.com/) account.
2. Navigate to **Settings > API Keys** and generate **Test Keys**.
3. Copy `Key Id` and `Key Secret` into `.env` under `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET`.

### Google OAuth 2.0
1. Create a project in the [Google Cloud Console](https://console.cloud.google.com/).
2. Configure your **OAuth Consent Screen**.
3. Under **Credentials**, create an **OAuth 2.0 Client ID** (Web application).
4. Add Authorized redirect URI:
   `http://127.0.0.1:8000/accounts/google/login/callback/`
5. Set `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` in `.env`.

### SMTP Email / OTP Service
For sending registration verification OTPs and order notifications via Gmail:
1. Enable **2-Step Verification** on your Google account.
2. Navigate to **Security > App passwords**.
3. Generate a 16-character App Password.
4. Set `EMAIL_HOST_USER` to your Gmail address and `EMAIL_HOST_PASSWORD` to the 16-character App Password in `.env`.

---

## Application Endpoints

| Route | Function |
|---|---|
| `/` | Storefront Homepage & Curated Showcase |
| `/shop/` | Instrument Catalog, Search & Filtering |
| `/shop/<product-slug>/` | Interactive Product Detail Page (PDP) & Variant Switcher |
| `/cart/` | Customer Shopping Cart & Inventory Checks |
| `/wishlist/` | User Wishlist |
| `/checkout/` | Checkout, Address Selector & Payment Gateways |
| `/checkout/payment-failed/` | Payment Failure Recovery & Retry Screen |
| `/profile/` | Customer Account, Order History & Address Book |
| `/wallet/` | Digital Wallet Ledger & Fund Top-Up |
| `/admin-panel/` | Administrative Backoffice & Analytics Dashboard |
| `/admin-panel/products/` | Product & Multi-Variant Catalog Management |
| `/admin-panel/orders/` | Order Fulfillment & Shipment Tracking |
| `/admin-panel/returns/` | Customer Return Request Inspection |
| `/admin-panel/coupons/` | Discount Coupon Campaign Engine |
| `/admin-panel/offers/` | Category & Product Promotional Offers |
| `/admin-panel/sales/` | Sales Performance Reports (PDF / Excel) |

---

