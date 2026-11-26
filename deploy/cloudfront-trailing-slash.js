/**
 * CloudFront Function — viewer-request
 * Runtime: cloudfront-js-2.0
 *
 * The app is built with `trailingSlash: true`, so Next.js emits
 * `out/<route>/index.html`. S3 serves those at `/<route>/` but returns
 * 403/404 for `/<route>` (no trailing slash). This function 301-redirects
 * extension-less, slash-less URIs to their trailing-slash form while
 * preserving the query string (detail pages use ?jobId= / ?companyId=).
 *
 * Associate with: default cache behavior → Viewer request → this function.
 */
function handler(event) {
  var request = event.request;
  var uri = request.uri;
  var lastSegment = uri.substring(uri.lastIndexOf('/') + 1);

  // Pass through: already a directory URL, the root, or a real file
  // (anything whose last segment contains a dot, e.g. .html, .txt, .js)
  if (uri === '/' || uri.endsWith('/') || lastSegment.indexOf('.') !== -1) {
    return request;
  }

  // Rebuild the query string — CloudFront Functions expose it as an object
  // of { value } or { multiValue: [{ value }, ...] } entries.
  var pairs = [];
  for (var key in request.querystring) {
    var entry = request.querystring[key];
    if (entry.multiValue) {
      for (var i = 0; i < entry.multiValue.length; i++) {
        pairs.push(key + '=' + entry.multiValue[i].value);
      }
    } else {
      pairs.push(key + '=' + entry.value);
    }
  }
  var qs = pairs.length ? '?' + pairs.join('&') : '';

  var host = request.headers.host ? request.headers.host.value : '';

  return {
    statusCode: 301,
    statusDescription: 'Moved Permanently',
    headers: {
      location: { value: 'https://' + host + uri + '/' + qs }
    }
  };
}
