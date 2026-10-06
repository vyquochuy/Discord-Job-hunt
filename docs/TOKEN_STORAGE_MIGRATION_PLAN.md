# JWT Token Storage Migration Plan (SEC-06)

## Objective
Migrate the storage of Access and Refresh tokens from `localStorage` to `HttpOnly`, `Secure`, `SameSite=Strict` (or `Lax`) cookies. This migration addresses the vulnerability **SEC-06: Browser localStorage Token Storage Exposing Refresh Tokens**, neutralizing the risk of token theft via Cross-Site Scripting (XSS).

## Current State Analysis
1. **Frontend**: Tokens are saved using `localStorage.setItem('jh_access_token', token)` in `frontend/js/api/client.js` and `frontend/legacy/js/api/client.js`.
2. **Backend**: Tokens are extracted from the `Authorization: Bearer <token>` header in `backend/app/core/security.py` via `get_current_user` / `get_current_user_optional`.
3. **API Integration**: Currently, JavaScript manually reads `localStorage` and attaches the token to the header for every outgoing HTTP request.

## Migration Steps

### Phase 1: Dual-Mode Backend Support & Cookie Issuance
Modify authentication endpoints to issue tokens as cookies in addition to the JSON response body to maintain backward compatibility during rollout.
- **Login/Refresh Endpoints (`backend/app/api/v1/endpoints/auth.py`)**: Add `set_cookie` directives to the `Response` object.
  ```python
  response.set_cookie(
      key="access_token",
      value=f"Bearer {access_token}",
      httponly=True,
      secure=True,  # Set based on environment (HTTPS)
      samesite="lax",
      max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
  )
  response.set_cookie(
      key="refresh_token",
      value=refresh_token,
      httponly=True,
      secure=True,
      samesite="lax",
      max_age=REFRESH_TOKEN_EXPIRE_DAYS * 86400,
  )
  ```
- **Logout Endpoint**: Ensure `response.delete_cookie(key="access_token")` and `response.delete_cookie(key="refresh_token")` are called.

### Phase 2: Frontend Client Update
Modify the `ApiClient` class in `frontend/js/api/client.js` to stop using `localStorage`.
- Ensure all `fetch` requests include `credentials: "include"` (or `"same-origin"` depending on deployment).
- Remove `setTokens`, `getToken`, and `localStorage.setItem` logic.
- Clear `localStorage` tokens upon logout or initial migration detection.

### Phase 3: Mitigating CSRF (Crucial Requirement)
Since tokens will now be automatically sent by the browser via cookies, the application becomes susceptible to Cross-Site Request Forgery (CSRF).
1. Implement a **Double Submit Cookie** pattern or a synchronized CSRF token.
2. The backend issues a non-HttpOnly `csrf_token` cookie.
3. The frontend reads the `csrf_token` and attaches it as an `X-CSRF-Token` header.
4. The backend verifies that the header matches the `csrf_token` cookie for all state-changing operations (`POST`, `PUT`, `DELETE`).

## Rollout Strategy
1. **Backward Compatibility**: During the transition, backend accepts tokens from *both* `Authorization` headers and `access_token` cookies.
2. **Frontend Deployment**: Deploy the updated frontend configured with `credentials: 'include'`.
3. **Deprecation**: After all active clients are updated, strictly enforce cookie-based auth and deprecate manual localStorage token passing.
