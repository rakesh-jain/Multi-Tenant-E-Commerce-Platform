
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
### **Authentication**
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/auth/register/` | Register new tenant/vendor | No |
| POST | `/api/auth/login/` | Login & get JWT token | No |
| GET | `/api/auth/profile/` | Get user profile | Yes |

### **Products**
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/products/` | List products (all roles) | Yes |
| POST | `/api/products/` | Create product | Owner/Staff |
| GET | `/api/products/{id}/` | Get product details | Yes |
| PUT | `/api/products/{id}/` | Update product | Owner/Staff |
| DELETE | `/api/products/{id}/` | Delete product | Owner |

### **Orders**
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/orders/` | List orders (owner: all, customer: own) | Yes |
| POST | `/api/orders/` | Create order | Customer |
| GET | `/api/orders/{id}/` | Get order details | Yes |
| PUT | `/api/orders/{id}/` | Update order status | Owner/Staff |

### **Customers**
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/customers/profiles/` | List customer profiles | Owner/Staff |
| GET | `/api/customers/profiles/{id}/` | Get customer profile | Yes |
| PUT | `/api/customers/profiles/{id}/` | Update customer profile | Owner/Staff |
| GET | `/api/customers/profiles/{id}/stats/` | Customer statistics | Yes |
| POST | `/api/customers/profiles/{id}/update_loyalty_points/` | Update loyalty points | Owner/Staff |
| POST | `/api/customers/addresses/` | Create shipping address | Customer |
| GET | `/api/customers/addresses/` | List addresses | Customer |
| DELETE | `/api/customers/addresses/{id}/` | Delete address | Customer |

### **Categories**
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/categories/` | List categories | Yes |
| POST | `/api/categories/` | Create category | Owner/Staff |

### **Tenants (Multi-Tenant)**
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/tenants/public/` | Public tenant discovery | No |
| GET | `/api/tenants/my/` | My tenants | Yes |
| POST | `/api/tenants/{id}/add_member/` | Add tenant member | Owner |
| GET | `/api/tenants/{id}/members/` | List tenant members | Owner |
| GET | `/api/tenants/{id}/stats/` | Tenant statistics | Owner |

### **Customer Features**
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/customers/wishlist/` | Add to wishlist | Customer |
| GET | `/api/customers/wishlist/` | List wishlist | Customer |
| POST | `/api/customers/reviews/` | Create review | Customer |
| GET | `/api/customers/reviews/` | List reviews | Yes |


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

