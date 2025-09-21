# API Reference

## Authentication

All API requests require an API key sent in the `X-API-Key` header.

## Base URL

```
https://api.insurance-claims.example.com/v1
```

## Endpoints

### Submit Claim

```http
POST /claims
```

**Request Body**

```json
{
  "policy_number": "string",
  "claim_amount": 0,
  "incident_date": "2025-09-21",
  "incident_details": "string",
  "documents": [
    {
      "type": "string",
      "url": "string"
    }
  ]
}
```

**Response**

```json
{
  "claim_id": "string",
  "status": "string",
  "estimated_processing_time": 0,
  "links": {
    "self": "string",
    "status": "string"
  }
}
```

### Get Claim Status

```http
GET /claims/{claim_id}
```

**Response**

```json
{
  "claim_id": "string",
  "status": "string",
  "current_stage": "string",
  "created_at": "2025-09-21T14:30:00Z",
  "updated_at": "2025-09-21T14:35:00Z",
  "result": {
    "approved_amount": 0,
    "rejection_reason": "string",
    "requires_additional_info": true
  }
}
```

## Error Handling

Standard HTTP status codes are used:

- `200 OK` - Request successful
- `400 Bad Request` - Invalid request format
- `401 Unauthorized` - Invalid or missing API key
- `404 Not Found` - Resource not found
- `429 Too Many Requests` - Rate limit exceeded
- `500 Internal Server Error` - Server error

## Rate Limiting

- 100 requests per minute per API key
- `X-RateLimit-Limit` header shows the limit
- `X-RateLimit-Remaining` shows remaining requests
- `X-RateLimit-Reset` shows when the limit resets
