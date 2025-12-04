-- ============================================================================
-- OccultaShield - SurrealDB Schema for Better-Auth
-- Ejecutar con: surreal import --conn http://localhost:8000 --ns occultashield --db main schema.surql
-- ============================================================================

-- ============================================================================
-- TABLA: user
-- Almacena información de los usuarios registrados
-- ============================================================================
DEFINE TABLE user SCHEMAFULL;

-- Campos principales
DEFINE FIELD email ON user TYPE string ASSERT string::is::email($value);
DEFINE FIELD emailVerified ON user TYPE bool DEFAULT false;
DEFINE FIELD name ON user TYPE string;
DEFINE FIELD image ON user TYPE option<string>;

-- Campo de rol personalizado
DEFINE FIELD role ON user TYPE string DEFAULT 'user';

-- Timestamps
DEFINE FIELD createdAt ON user TYPE datetime DEFAULT time::now();
DEFINE FIELD updatedAt ON user TYPE datetime DEFAULT time::now();

-- Índices
DEFINE INDEX user_email_idx ON user FIELDS email UNIQUE;

-- ============================================================================
-- TABLA: session
-- Almacena las sesiones activas de los usuarios
-- ============================================================================
DEFINE TABLE session SCHEMAFULL;

-- Campos principales
DEFINE FIELD userId ON session TYPE string;
DEFINE FIELD token ON session TYPE string;
DEFINE FIELD expiresAt ON session TYPE datetime;

-- Información adicional de la sesión
DEFINE FIELD ipAddress ON session TYPE option<string>;
DEFINE FIELD userAgent ON session TYPE option<string>;

-- Timestamps
DEFINE FIELD createdAt ON session TYPE datetime DEFAULT time::now();
DEFINE FIELD updatedAt ON session TYPE datetime DEFAULT time::now();

-- Índices
DEFINE INDEX session_token_idx ON session FIELDS token UNIQUE;
DEFINE INDEX session_userId_idx ON session FIELDS userId;

-- ============================================================================
-- TABLA: account
-- Almacena las cuentas vinculadas (providers como email, google, github, etc.)
-- ============================================================================
DEFINE TABLE account SCHEMAFULL;

-- Campos principales
DEFINE FIELD userId ON account TYPE string;
DEFINE FIELD accountId ON account TYPE string;
DEFINE FIELD providerId ON account TYPE string;

-- Credenciales (para email/password)
DEFINE FIELD password ON account TYPE option<string>;

-- Tokens OAuth (para providers externos)
DEFINE FIELD accessToken ON account TYPE option<string>;
DEFINE FIELD refreshToken ON account TYPE option<string>;
DEFINE FIELD accessTokenExpiresAt ON account TYPE option<datetime>;
DEFINE FIELD refreshTokenExpiresAt ON account TYPE option<datetime>;
DEFINE FIELD scope ON account TYPE option<string>;
DEFINE FIELD idToken ON account TYPE option<string>;

-- Timestamps
DEFINE FIELD createdAt ON account TYPE datetime DEFAULT time::now();
DEFINE FIELD updatedAt ON account TYPE datetime DEFAULT time::now();

-- Índices
DEFINE INDEX account_provider_idx ON account FIELDS providerId, accountId UNIQUE;
DEFINE INDEX account_userId_idx ON account FIELDS userId;

-- ============================================================================
-- TABLA: verification
-- Almacena tokens de verificación (email, password reset, etc.)
-- ============================================================================
DEFINE TABLE verification SCHEMAFULL;

-- Campos principales
DEFINE FIELD identifier ON verification TYPE string;
DEFINE FIELD value ON verification TYPE string;
DEFINE FIELD expiresAt ON verification TYPE datetime;

-- Timestamps
DEFINE FIELD createdAt ON verification TYPE datetime DEFAULT time::now();
DEFINE FIELD updatedAt ON verification TYPE datetime DEFAULT time::now();

-- Índices
DEFINE INDEX verification_identifier_idx ON verification FIELDS identifier;
DEFINE INDEX verification_value_idx ON verification FIELDS value UNIQUE;

-- ============================================================================
-- EVENTOS (Opcional - para limpieza automática)
-- ============================================================================

-- Evento para limpiar sesiones expiradas (ejecutar periódicamente)
-- DELETE session WHERE expiresAt < time::now();

-- Evento para limpiar verificaciones expiradas
-- DELETE verification WHERE expiresAt < time::now();

-- ============================================================================
-- TABLA: processing_log
-- Almacena el historial de archivos procesados para estadísticas
-- ============================================================================
DEFINE TABLE processing_log SCHEMAFULL;

DEFINE FIELD userId ON processing_log TYPE string; -- ID del usuario (opcional si es anónimo)
DEFINE FIELD action ON processing_log TYPE string; -- 'upload', 'clean', 'download'
DEFINE FIELD fileName ON processing_log TYPE string;
DEFINE FIELD fileSize ON processing_log TYPE number;
DEFINE FIELD status ON processing_log TYPE string; -- 'success', 'error'
DEFINE FIELD metadata ON processing_log TYPE object;
DEFINE FIELD createdAt ON processing_log TYPE datetime DEFAULT time::now();

DEFINE INDEX log_userId_idx ON processing_log FIELDS userId;
DEFINE INDEX log_action_idx ON processing_log FIELDS action;

