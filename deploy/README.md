# RoleCraft — S3 + CloudFront deploy guide

The frontend is a static export: `npm run build` produces `out/` (all routes
prerendered, `trailingSlash: true` → `out/<route>/index.html`). Deploy `out/`
to S3 behind CloudFront.

## 1. Build

```bash
npm ci
NEXT_PUBLIC_API_URL=https://<api-host> \
NEXT_PUBLIC_WS_URL=wss://<api-host> \
npm run build        # → out/
```

`NEXT_PUBLIC_API_URL` is **required** in production builds (build fails if
unset or localhost). `API_PROXY_TARGET` no longer exists — do not set it.

## 2. S3 bucket

```bash
aws s3 mb s3://rolecraft-frontend
aws s3 sync out/ s3://rolecraft-frontend/ --delete
```

Block all public access (CloudFront OAC is the only reader).

## 3. CloudFront distribution

- Origin: the S3 bucket, **Origin access control (OAC)** — not OAI, not public.
- Default root object: `index.html`.
- Viewer protocol policy: redirect HTTP → HTTPS.
- ACM certificate for your domain (us-east-1 for CloudFront).

Bucket policy must allow `cloudfront.amazonaws.com` `s3:GetObject` scoped to
the distribution's `AWS:SourceArn`.

## 4. Trailing-slash redirect (required)

`trailingSlash: true` means URLs are `/path/`; bare `/path` 404s on S3.

```bash
aws cloudfront create-function \
  --name rolecraft-trailing-slash \
  --function-config Comment="Redirect /path -> /path/ preserving querystring",Runtime=cloudfront-js-2.0 \
  --function-code fileb://deploy/cloudfront-trailing-slash.js

aws cloudfront publish-function --name rolecraft-trailing-slash
```

Then associate it: distribution → Behaviors → default behavior →
**Viewer request** → Function type *CloudFront Functions* →
`rolecraft-trailing-slash`.

(Console equivalent: CloudFront → Functions → Create function → paste
`deploy/cloudfront-trailing-slash.js` → Publish → attach to behavior.)

## 5. Security headers (required)

The old `next.config.ts` `headers()` no longer applies — headers must come
from a **Response headers policy** on the same default behavior.

```bash
# Edit deploy/response-headers-policy.json first: replace API_HOST with the
# real API domain (e.g. rolecraft-api.onrender.com or the future ALB domain).
sed 's/API_HOST/rolecraft-api.onrender.com/g' deploy/response-headers-policy.json > /tmp/policy.json

aws cloudfront create-response-headers-policy \
  --response-headers-policy-config file:///tmp/policy.json
```

Attach the returned policy ID to the default cache behavior
(**Response headers policy** field). Note the CSP `connect-src` already lists
`https://API_HOST` and `wss://API_HOST` — update it whenever the API domain
changes.

## 6. Error responses (recommended)

Custom error responses on the distribution:

| HTTP code | Response page path | Response code |
|---|---|---|
| 403   | `/404.html` | 404 |
| 404   | `/404.html` | 404 |

(S3 returns 403 for missing keys when OAC is used — this mapping makes it a
proper 404 page.)

## 7. Backend env

`CORS_ORIGINS` on the API must include the CloudFront domain(s), comma-separated,
no wildcard (production guard rejects `*`):

```bash
CORS_ORIGINS=https://app.example.com,https://<dist-id>.cloudfront.net
```

Also keep `FRONTEND_URL` pointed at the CloudFront/custom domain for email links.

## Route reference (dynamic → static query-param)

| URL | Page |
|---|---|
| `/jobs/detail?jobId=<id>` | Job detail |
| `/companies/profile?companyId=<id>` | Public company profile |
| `/company/jobs/applications?jobId=<id>` | Company: applications for a job |

All other routes are plain paths (`/jobs`, `/dashboard`, `/signin`, …).
