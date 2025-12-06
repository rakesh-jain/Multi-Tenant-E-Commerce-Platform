
# Multi-Tenant E-Commerce Platform

A Django-based multi-tenant e-commerce platform where multiple vendors can host their stores on a shared infrastructure with isolated data.

## Features

- **Multi-tenancy**: Each vendor has completely isolated data
- **Role-based access control**: Store Owner, Staff, and Customer roles
- **JWT Authentication**: Secure token-based authentication with tenant context
- **Complete e-commerce functionality**: Products, Orders, Customers management
- **RESTful API**: Fully documented API endpoints

## Tech Stack

- **Backend**: Django 4.2, Django REST Framework
- **Database**: PostgreSQL with django-tenants for multi-tenancy
- **Authentication**: JWT with custom tenant-aware authentication
- **Container**: Docker & Docker Compose

## Setup Instructions

### Prerequisites
- Python 3.11+
- MySQL 2.2+
- Docker & Docker Compose (optional)

### Local Development

1. **Clone the repository**
```bash
git clone <repository-url>
cd multi-tenant-ecommerce
```

1. Set up environment variables

```bash
cp .env.example .env
# Edit .env with your configuration
```

1. Install dependencies

```bash
cd backend
pip install -r requirements.txt
```

1. Run database migrations

```bash
python manage.py migrate_schemas --shared
```

1. Create a superuser for shared schema

```bash
python manage.py create_tenant_superuser
```

1. Run the development server

```bash
python manage.py runserver
```

Using Docker

```bash
docker-compose up --build
```

API Endpoints

Authentication

· POST /api/auth/register/ - Register a new tenant/vendor
· POST /api/auth/login/ - Login and get JWT token
· GET /api/auth/profile/ - Get user profile

Products

· GET /api/products/ - List products (all roles)
· POST /api/products/ - Create product (store owner/staff)
· GET /api/products/{id}/ - Get product details (all roles)
· PUT /api/products/{id}/ - Update product (store owner/staff)
· DELETE /api/products/{id}/ - Delete product (store owner)

Orders

· GET /api/orders/ - List orders
· Store owners/staff: All orders
· Customers: Their own orders
· POST /api/orders/ - Create order (customers only)
· GET /api/orders/{id}/ - Get order details
· PUT /api/orders/{id}/ - Update order status (store owner/staff)

Categories

· GET /api/categories/ - List categories
· POST /api/categories/ - Create category (store owner/staff)

Multi-Tenancy Implementation

The platform uses django-tenants library to implement multi-tenancy at the database schema level. Each tenant gets its own MySQL schema with completely isolated data.

Key Implementation Details:

1. Tenant Identification:
· Domain-based tenant identification (subdomain.example.com)
· JWT tokens include tenant ID for API requests
2. Data Isolation:
· Each tenant has separate database schema
· All models are tenant-aware through foreign key relationships
· Automatic schema switching based on request domain
3. Shared vs Tenant Apps:
· Shared apps: Vendors app (stores tenant information)
· Tenant apps: Users, Products, Orders (tenant-specific data)
4. Middleware:
· TenantMainMiddleware automatically switches schemas based on domain
· Custom JWT authentication extracts tenant from token for API requests

Role-Based Access Control

1. Store Owner: Full access to all data within their tenant
2. Staff: Limited access (products and orders management)
3. Customer: Can view products and manage their own orders

Permissions are checked at both view level and object level, ensuring users can only access data belonging to their tenant.


Testing

```bash
# Run tests
python manage.py test

# Test specific app
python manage.py test users --settings=ecommerce.test_settings
```
