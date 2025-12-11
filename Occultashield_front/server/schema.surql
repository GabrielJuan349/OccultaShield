-- ============================================================================
-- OccultaShield - SurrealDB Schema Completo para surreal-better-auth
-- Incluye: Core tables + Extensiones futuras (2FA, Organizations, etc.)
-- Ejecutar: surreal import --conn http://localhost:8000 --ns occultashield --db main --user root --pass root schema.surql
-- ============================================================================

-- ============================================================================
-- TABLAS CORE DE BETTER-AUTH (REQUERIDAS)
-- ============================================================================

-- ============================================================================
-- TABLA: user
-- Almacena información de los usuarios registrados
-- ============================================================================
DEFINE TABLE user SCHEMAFULL;

-- Campos principales (requeridos por better-auth)
DEFINE FIELD email ON user TYPE string ASSERT string::is::email($value);
DEFINE FIELD emailVerified ON user TYPE bool DEFAULT false;
DEFINE FIELD name ON user TYPE string;
DEFINE FIELD image ON user TYPE option<string>;

-- Campo de rol personalizado (extensión de OccultaShield)
DEFINE FIELD role ON user TYPE string DEFAULT 'user';

-- Timestamps (requeridos por better-auth)
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

-- Campos requeridos por better-auth
DEFINE FIELD userId ON session TYPE record<user>;
DEFINE FIELD token ON session TYPE string;
DEFINE FIELD expiresAt ON session TYPE datetime;

-- Campos opcionales de better-auth
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

-- Campos requeridos por better-auth
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
-- Almacena tokens de verificación (email, password reset, magic links, etc.)
-- ============================================================================
DEFINE TABLE verification SCHEMAFULL;

-- Campos requeridos por better-auth
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
-- TABLAS PARA PLUGINS FUTUROS
-- ============================================================================

-- ============================================================================
-- TABLA: twoFactor (Plugin: twoFactor)
-- Almacena configuración de 2FA para usuarios
-- Relación: twoFactor -> user (one-to-one)
-- ============================================================================
DEFINE TABLE twoFactor SCHEMAFULL;

-- Foreign Key: referencia al usuario
DEFINE FIELD userId ON twoFactor TYPE record<user>;

-- Secreto TOTP (Time-based One-Time Password)
DEFINE FIELD secret ON twoFactor TYPE string;

-- Códigos de respaldo (para recuperación)
DEFINE FIELD backupCodes ON twoFactor TYPE option<array<string>>;

-- Estado de activación
DEFINE FIELD enabled ON twoFactor TYPE bool DEFAULT false;

-- Timestamps
DEFINE FIELD createdAt ON twoFactor TYPE datetime DEFAULT time::now();
DEFINE FIELD updatedAt ON twoFactor TYPE datetime DEFAULT time::now();

-- Índices
DEFINE INDEX twoFactor_userId_idx ON twoFactor FIELDS userId UNIQUE;

-- ============================================================================
-- TABLA: organization (Plugin: organization)
-- Almacena organizaciones/equipos
-- ============================================================================
DEFINE TABLE organization SCHEMAFULL;

-- Campos principales
DEFINE FIELD name ON organization TYPE string;
DEFINE FIELD slug ON organization TYPE string;
DEFINE FIELD logo ON organization TYPE option<string>;

-- Metadatos adicionales (JSON flexible)
DEFINE FIELD metadata ON organization TYPE option<object> DEFAULT {};

-- Timestamps
DEFINE FIELD createdAt ON organization TYPE datetime DEFAULT time::now();
DEFINE FIELD updatedAt ON organization TYPE datetime DEFAULT time::now();

-- Índices
DEFINE INDEX organization_slug_idx ON organization FIELDS slug UNIQUE;

-- ============================================================================
-- TABLA: member (Plugin: organization)
-- Almacena miembros de organizaciones con sus roles
-- Relación: member -> user (many-to-one)
-- Relación: member -> organization (many-to-one)
-- ============================================================================
DEFINE TABLE member SCHEMAFULL;

-- Foreign Keys
DEFINE FIELD userId ON member TYPE record<user>;
DEFINE FIELD organizationId ON member TYPE record<organization>;

-- Rol del miembro en la organización
DEFINE FIELD role ON member TYPE string DEFAULT 'member'; -- 'owner', 'admin', 'member'

-- Timestamps
DEFINE FIELD createdAt ON member TYPE datetime DEFAULT time::now();
DEFINE FIELD updatedAt ON member TYPE datetime DEFAULT time::now();

-- Índices (un usuario puede estar en múltiples orgs, pero solo una vez por org)
DEFINE INDEX member_user_org_idx ON member FIELDS userId, organizationId UNIQUE;
DEFINE INDEX member_org_idx ON member FIELDS organizationId;

-- ============================================================================
-- TABLA: invitation (Plugin: organization)
-- Almacena invitaciones pendientes a organizaciones
-- Relación: invitation -> organization (many-to-one)
-- Relación: invitation -> user (many-to-one, quien invita)
-- ============================================================================
DEFINE TABLE invitation SCHEMAFULL;

-- Email del invitado
DEFINE FIELD email ON invitation TYPE string ASSERT string::is::email($value);

-- Foreign Keys
DEFINE FIELD organizationId ON invitation TYPE record<organization>;
DEFINE FIELD inviterId ON invitation TYPE record<user>; -- Quien envía la invitación

-- Rol que tendrá el invitado
DEFINE FIELD role ON invitation TYPE string DEFAULT 'member';

-- Token de invitación
DEFINE FIELD token ON invitation TYPE string;

-- Expiración
DEFINE FIELD expiresAt ON invitation TYPE datetime;

-- Estado
DEFINE FIELD status ON invitation TYPE string DEFAULT 'pending'; -- 'pending', 'accepted', 'rejected', 'expired'

-- Timestamps
DEFINE FIELD createdAt ON invitation TYPE datetime DEFAULT time::now();
DEFINE FIELD updatedAt ON invitation TYPE datetime DEFAULT time::now();

-- Índices
DEFINE INDEX invitation_token_idx ON invitation FIELDS token UNIQUE;
DEFINE INDEX invitation_org_idx ON invitation FIELDS organizationId;
DEFINE INDEX invitation_email_idx ON invitation FIELDS email;

-- ============================================================================
-- TABLAS PERSONALIZADAS DE OCCULTASHIELD
-- ============================================================================

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
-- EVENTOS AUTOMÁTICOS (Limpieza automática de datos expirados)
-- ============================================================================

-- Evento para limpiar sesiones expiradas
DEFINE EVENT session_cleanup ON TABLE session WHEN $event = "CREATE" OR $event = "UPDATE" THEN {
    DELETE session WHERE expiresAt < time::now();
};

-- Evento para limpiar verificaciones expiradas
DEFINE EVENT verification_cleanup ON TABLE verification WHEN $event = "CREATE" OR $event = "UPDATE" THEN {
    DELETE verification WHERE expiresAt < time::now();
};

-- Evento para limpiar invitaciones expiradas
DEFINE EVENT invitation_cleanup ON TABLE invitation WHEN $event = "CREATE" OR $event = "UPDATE" THEN {
    DELETE invitation WHERE expiresAt < time::now() AND status = 'pending';
};

-- ============================================================================
-- QUERIES DE EJEMPLO CON RECORD LINKS
-- ============================================================================

-- Obtener sesiones con datos del usuario:
-- SELECT *, userId.* AS user FROM session;

-- Obtener cuentas con nombre del usuario:
-- SELECT *, userId.name AS userName, userId.email AS userEmail FROM account;

-- Obtener logs con información del usuario:
-- SELECT *, userId.name AS userName FROM processing_log ORDER BY createdAt DESC;

-- Estadísticas de procesamiento por usuario:
-- SELECT userId, userId.name AS userName, count() as total, action FROM processing_log GROUP BY userId, action;

-- Obtener todas las sesiones de un usuario específico:
-- SELECT * FROM session WHERE userId = user:some_user_id;

-- Obtener miembros de una organización con datos de usuario:
-- SELECT *, userId.* AS user FROM member WHERE organizationId = organization:some_org_id;

-- Obtener organizaciones de un usuario:
-- SELECT organizationId.* AS organization, role FROM member WHERE userId = user:some_user_id;

-- Verificar si un usuario tiene 2FA habilitado:
-- SELECT * FROM twoFactor WHERE userId = user:some_user_id AND enabled = true;

-- ============================================================================
-- QUERIES DE LIMPIEZA MANUAL (Por si los eventos automáticos fallan)
-- ============================================================================

-- Limpiar sesiones expiradas:
-- DELETE session WHERE expiresAt < time::now();

-- Limpiar verificaciones expiradas:
-- DELETE verification WHERE expiresAt < time::now();

-- Limpiar invitaciones expiradas:
-- DELETE invitation WHERE expiresAt < time::now() AND status = 'pending';

-- Limpiar logs antiguos (ej: más de 90 días):
-- DELETE processing_log WHERE createdAt < time::now() - 90d;
