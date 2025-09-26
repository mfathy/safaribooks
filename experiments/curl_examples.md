# O'Reilly Books API - cURL Examples

## Updated API Endpoints
The parser now uses API v2 with limit=100 for better performance:

```
https://learning.oreilly.com/api/v2/search/
```

## cURL Examples for Testing

### 1. Programming Languages Topic (100 books per page)
```bash
curl -X GET "https://learning.oreilly.com/api/v2/search/?topic=programming-languages&page=1&limit=100" \
  -H "Accept: application/json"
```

### 2. Programming Languages Topic (Page 2)
```bash
curl -X GET "https://learning.oreilly.com/api/v2/search/?topic=programming-languages&page=2&limit=100" \
  -H "Accept: application/json"
```

### 3. Data Science Topic (100 books per page)
```bash
curl -X GET "https://learning.oreilly.com/api/v2/search/?topic=data-science&page=1&limit=100" \
  -H "Accept: application/json"
```

### 4. Software Development Topic (100 books per page)
```bash
curl -X GET "https://learning.oreilly.com/api/v2/search/?topic=software-development&page=1&limit=100" \
  -H "Accept: application/json"
```

### 5. Python Search (100 books per page)
```bash
curl -X GET "https://learning.oreilly.com/api/v2/search/?q=python&page=1&limit=100" \
  -H "Accept: application/json"
```

### 6. JavaScript Search (100 books per page)
```bash
curl -X GET "https://learning.oreilly.com/api/v2/search/?q=javascript&page=1&limit=100" \
  -H "Accept: application/json"
```

### 7. Query Search with Topic Filter
```bash
curl -X GET "https://learning.oreilly.com/api/v2/search/?q=python&topic=programming-languages&page=1&limit=100" \
  -H "Accept: application/json"
```

## Postman Collection

### Environment Variables
Create these variables in Postman:
- `base_url`: `https://learning.oreilly.com/api/v2/search/`

### Request Examples

#### 1. Get Programming Languages Books (100 per page)
- **Method**: GET
- **URL**: `{{base_url}}?topic=programming-languages&page=1&limit=100`
- **Headers**:
  - `Accept`: `application/json`

#### 2. Get Programming Languages Books (Page 2)
- **Method**: GET
- **URL**: `{{base_url}}?topic=programming-languages&page=2&limit=100`
- **Headers**:
  - `Accept`: `application/json`

#### 3. Search for Python Books (100 per page)
- **Method**: GET
- **URL**: `{{base_url}}?q=python&page=1&limit=100`
- **Headers**:
  - `Accept`: `application/json`

## Expected Response Format

```json
{
  "results": [
    {
      "id": "https://www.safaribooksonline.com/api/v1/book/9781098166298/",
      "archive_id": "9781098166298",
      "isbn": "9781098166304",
      "title": "AI Engineering",
      "authors": [
        {
          "name": "Chip Huyen"
        }
      ],
      "issued": "2024-12-04",
      "created_time": "2023-04-04T10:21:26.053Z"
    }
  ],
  "count": 61118,
  "next": "https://learning.oreilly.com/api/v1/search/?topic=programming-languages&page=2",
  "previous": null
}
```

## Key Parameters

- `topic`: Topic slug (e.g., `programming-languages`, `data-science`, `software-development`)
- `q`: Search query (e.g., `python`, `javascript`, `machine learning`)
- `page`: Page number (starts from 1)
- `limit`: Page size (default: 10, max: 100 results per page)

## Available Topics

Based on the original parser, these topics are available:
- `programming-languages`
- `software-development`
- `web-mobile`
- `data-science`
- `business`
- `career-development`
- `security`
- `cloud-computing`
- `artificial-intelligence`
- `devops`

## Testing Tips

1. **Start with Page 1**: Always test page 1 first to ensure the endpoint works
2. **Check Response Headers**: Look for rate limiting headers
3. **Test Pagination**: Try page 2, 3, etc. to see how many pages are available
4. **Test Different Topics**: Try different topic slugs to see which ones work
5. **Test Query Search**: Use the `q` parameter for keyword searches

## Rate Limiting

The API appears to have some rate limiting. If you get errors:
- Add delays between requests (0.5-1 second)
- Use proper User-Agent headers
- Don't make too many requests too quickly
