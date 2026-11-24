# EduSaaS CRM - API Documentation

## Base URL
```
Development: http://localhost:8000/api/v1
Swagger UI:  http://localhost:8000/docs
ReDoc:       http://localhost:8000/redoc
```

## Authentication
All protected endpoints require:
```
Authorization: Bearer <access_token>
```

## Response Envelopes

### Success
```json
{
  "success": true,
  "data": { ... },
  "message": "Operation successful"
}
```

### Paginated
```json
{
  "success": true,
  "data": [ ... ],
  "pagination": { "total": 100, "page": 1, "size": 20, "pages": 5 }
}
```

### Error
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable message",
    "details": [{ "field": "email", "message": "Invalid email" }]
  }
}
```

## Implemented Endpoints (Phase 0)

### Health
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/health` | None | Basic health check |
| GET | `/api/v1/health/detailed` | None | Health + dependency status |

---
*Additional endpoints documented here as modules are implemented.*
