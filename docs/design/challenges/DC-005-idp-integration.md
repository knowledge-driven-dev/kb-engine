# DC-005: Integración IdP

---
id: DC-005
status: open
priority: alta
created: 2025-01-16
updated: 2025-01-16
owner: TBD
adrs: []
---

## 1. Contexto

El sistema requiere autenticación y autorización con roles provenientes de un Identity Provider (IdP) externo. Los roles determinan el acceso a documentos, chunks y nodos del grafo.

### Requisitos ya definidos

- **Roles externos**: Provenientes del IdP (no gestionados internamente)
- **RBAC**: Control de acceso basado en roles a nivel documento y proyecto
- **Tenancy**: Un despliegue por dominio/proyecto (aislamiento)
- **Futuro**: Rol Knowledge Manager con permisos especiales

### Contexto Técnico

- Backend en Python (FastAPI probable)
- Múltiples clientes potenciales (MCP, UI de curación, API directa)
- Claims necesarios: usuario, roles, dominio/proyecto

## 2. Requisitos y Restricciones

### 2.1 Requisitos Funcionales

- [ ] RF1: Autenticar usuarios mediante tokens del IdP
- [ ] RF2: Extraer roles y claims del token
- [ ] RF3: Validar tokens en cada request (o sesión)
- [ ] RF4: Soportar múltiples IdPs (OAuth2/OIDC estándar)
- [ ] RF5: Mapear claims del IdP a permisos internos
- [ ] RF6: Soportar refresh tokens para sesiones largas

### 2.2 Requisitos No Funcionales

- [ ] RNF1: Validación de token no debe añadir latencia significativa
- [ ] RNF2: Cache de tokens/claims para rendimiento
- [ ] RNF3: Manejo seguro de tokens (no logging, encriptación)

### 2.3 Restricciones

- Debe ser agnóstico del IdP (OAuth2/OIDC estándar)
- No gestionar usuarios/roles internamente (solo consumir del IdP)
- Compatible con despliegue cloud-agnóstico

## 3. Opciones Consideradas

### Opción A: Validación Directa de JWT

**Descripción**: Validar JWT directamente en el backend usando la clave pública del IdP.

```python
from jose import jwt

def validate_token(token: str) -> Claims:
    # Obtener JWKS del IdP
    jwks = get_jwks(IDP_JWKS_URL)

    # Validar y decodificar
    claims = jwt.decode(
        token,
        jwks,
        algorithms=["RS256"],
        audience=CLIENT_ID
    )
    return claims

@app.middleware("http")
async def auth_middleware(request, call_next):
    token = request.headers.get("Authorization")
    claims = validate_token(token)
    request.state.user = claims
    return await call_next(request)
```

**Pros**:
- Simple y directo
- Sin dependencias externas adicionales
- Bajo overhead (validación local)

**Contras**:
- Cache de JWKS manual
- No soporta revocación inmediata de tokens
- Configuración por cada IdP

**Esfuerzo estimado**: Bajo

---

### Opción B: API Gateway con Autenticación

**Descripción**: Delegar autenticación a un API Gateway (Kong, AWS API Gateway, etc.).

```
Cliente → API Gateway (valida token) → Backend (recibe claims en headers)
```

**Pros**:
- Separación de concerns
- Gateway maneja cache, rate limiting, etc.
- Backend más simple

**Contras**:
- Dependencia de infraestructura específica
- Menos control sobre validación
- Añade componente a mantener

**Esfuerzo estimado**: Medio (setup infra)

---

### Opción C: Librería de Autenticación (Authlib/FastAPI-Security)

**Descripción**: Usar librería especializada que abstrae la complejidad de OAuth2/OIDC.

```python
from authlib.integrations.starlette_client import OAuth
from fastapi_security import FastAPISecurity

oauth = OAuth()
oauth.register(
    name='idp',
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    server_metadata_url=f'{IDP_URL}/.well-known/openid-configuration'
)

security = FastAPISecurity()

@app.get("/protected")
async def protected(user: User = Depends(security.authenticated)):
    return {"user": user.id, "roles": user.roles}
```

**Pros**:
- Abstrae complejidad de OIDC
- Soporta múltiples IdPs fácilmente
- Manejo automático de refresh, JWKS, etc.

**Contras**:
- Dependencia adicional
- Menos control sobre el flujo
- Curva de aprendizaje de la librería

**Esfuerzo estimado**: Medio

---

### Opción D: Sidecar de Autenticación (OAuth2 Proxy)

**Descripción**: Usar un sidecar/proxy que maneja toda la autenticación.

```
Cliente → OAuth2 Proxy → Backend (usuario ya autenticado)
```

**Pros**:
- Backend completamente desacoplado de auth
- Funciona con cualquier IdP compatible
- Patrón probado en Kubernetes

**Contras**:
- Componente adicional de infraestructura
- Menos flexible para lógica custom
- Overhead de latencia (hop adicional)

**Esfuerzo estimado**: Medio (setup infra)

## 4. Análisis Comparativo

| Criterio | Peso | JWT Directo | API Gateway | Librería | Sidecar |
|----------|------|-------------|-------------|----------|---------|
| Simplicidad backend | 2 | ⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| Agnóstico de IdP | 3 | ⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| Rendimiento | 2 | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| Flexibilidad | 2 | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐ |
| Cloud agnóstico | 3 | ⭐⭐⭐ | ⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| Mantenibilidad | 2 | ⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| **Total ponderado** | | 35 | 29 | 39 | 33 |

## 5. Preguntas Abiertas

- [ ] ¿Qué IdPs específicos se usarán? (Azure AD, Keycloak, Auth0, Okta?)
- [ ] ¿El IdP puede incluir claims custom (dominio, proyecto)?
- [ ] ¿Se necesita soportar múltiples IdPs simultáneamente?
- [ ] ¿Qué flujo OAuth2 usar? (Authorization Code, Client Credentials?)
- [ ] ¿Cómo manejar service-to-service auth (MCP → Backend)?

## 6. Decisión

> **Estado**: Pendiente

**Opción seleccionada**: -

**Justificación**: -

**ADRs generados**: -

## 7. Referencias

- [OAuth 2.0](https://oauth.net/2/)
- [OpenID Connect](https://openid.net/connect/)
- [Authlib](https://docs.authlib.org/en/latest/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [OAuth2 Proxy](https://oauth2-proxy.github.io/oauth2-proxy/)
