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
-- Relación: session -> user (many-to-one)
-- ============================================================================
DEFINE TABLE session SCHEMAFULL;

-- Foreign Key: referencia al usuario (record link)
DEFINE FIELD userId ON session TYPE record<user>;
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
-- Relación: account -> user (many-to-one)
-- ============================================================================
DEFINE TABLE account SCHEMAFULL;

-- Foreign Key: referencia al usuario (record link)
DEFINE FIELD userId ON account TYPE record<user>;
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
-- TABLA: processing_log
-- Almacena el historial de archivos procesados para estadísticas
-- Relación: processing_log -> user (many-to-one)
-- ============================================================================
DEFINE TABLE processing_log SCHEMAFULL;

-- Foreign Key: referencia al usuario (record link)
DEFINE FIELD userId ON processing_log TYPE record<user>;
DEFINE FIELD action ON processing_log TYPE string; -- 'upload', 'clean', 'download'
DEFINE FIELD fileName ON processing_log TYPE string;
DEFINE FIELD fileSize ON processing_log TYPE number;
DEFINE FIELD status ON processing_log TYPE string; -- 'success', 'error'
DEFINE FIELD metadata ON processing_log TYPE option<object> DEFAULT {};
DEFINE FIELD createdAt ON processing_log TYPE datetime DEFAULT time::now();

-- Índices para búsquedas rápidas
DEFINE INDEX log_userId_idx ON processing_log FIELDS userId;
DEFINE INDEX log_action_idx ON processing_log FIELDS action;
DEFINE INDEX log_createdAt_idx ON processing_log FIELDS createdAt;

-- ============================================================================
-- QUERIES DE EJEMPLO CON RECORD LINKS
-- Las relaciones se navegan automáticamente
-- ============================================================================

-- Obtener sesiones con datos del usuario (el record link se resuelve automáticamente):
-- SELECT *, userId.* AS user FROM session;

-- Obtener cuentas con nombre del usuario:
-- SELECT *, userId.name AS userName, userId.email AS userEmail FROM account;

-- Obtener logs con información del usuario:
-- SELECT *, userId.name AS userName FROM processing_log ORDER BY createdAt DESC;

-- Estadísticas de procesamiento por usuario:
-- SELECT userId, userId.name AS userName, count() as total, action FROM processing_log GROUP BY userId, action;

-- Obtener todas las sesiones de un usuario específico:
-- SELECT * FROM session WHERE userId = user:some_user_id;

-- ============================================================================
-- QUERIES DE LIMPIEZA (Ejecutar periódicamente via cron/tarea programada)
-- ============================================================================

-- Limpiar sesiones expiradas:
-- DELETE session WHERE expiresAt < time::now();

-- Limpiar verificaciones expiradas:
-- DELETE verification WHERE expiresAt < time::now();

