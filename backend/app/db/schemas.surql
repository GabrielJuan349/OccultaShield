-- ============================================================================
-- OccultaShield - Merged SurrealDB Schema
-- Includes: Service Authentication (Better-Auth) & Application Domain (Videos/GDPR)
-- ============================================================================

-- ============================================================================
-- 1. AUTHENTICATION & ORGANIZATION (Better-Auth)
-- ============================================================================

-- TABLE: user
DEFINE TABLE user SCHEMAFULL;
DEFINE FIELD email ON user TYPE string ASSERT string::is::email($value);
DEFINE FIELD emailVerified ON user TYPE bool DEFAULT false;
DEFINE FIELD name ON user TYPE string;
DEFINE FIELD image ON user TYPE option<string>;
DEFINE FIELD role ON user TYPE string DEFAULT 'user';
DEFINE FIELD createdAt ON user TYPE datetime DEFAULT time::now();
DEFINE FIELD updatedAt ON user TYPE datetime DEFAULT time::now();
DEFINE INDEX user_email_idx ON user FIELDS email UNIQUE;

-- TABLE: session
DEFINE TABLE session SCHEMAFULL;
DEFINE FIELD userId ON session TYPE record<user>;
DEFINE FIELD token ON session TYPE string;
DEFINE FIELD expiresAt ON session TYPE datetime;
DEFINE FIELD ipAddress ON session TYPE option<string>;
DEFINE FIELD userAgent ON session TYPE option<string>;
DEFINE FIELD createdAt ON session TYPE datetime DEFAULT time::now();
DEFINE FIELD updatedAt ON session TYPE datetime DEFAULT time::now();
DEFINE INDEX session_token_idx ON session FIELDS token UNIQUE;
DEFINE INDEX session_userId_idx ON session FIELDS userId;

-- TABLE: account
DEFINE TABLE account SCHEMAFULL;
DEFINE FIELD userId ON account TYPE record<user>;
DEFINE FIELD accountId ON account TYPE string;
DEFINE FIELD providerId ON account TYPE string;
DEFINE FIELD password ON account TYPE option<string>;
DEFINE FIELD accessToken ON account TYPE option<string>;
DEFINE FIELD refreshToken ON account TYPE option<string>;
DEFINE FIELD accessTokenExpiresAt ON account TYPE option<datetime>;
DEFINE FIELD refreshTokenExpiresAt ON account TYPE option<datetime>;
DEFINE FIELD scope ON account TYPE option<string>;
DEFINE FIELD idToken ON account TYPE option<string>;
DEFINE FIELD createdAt ON account TYPE datetime DEFAULT time::now();
DEFINE FIELD updatedAt ON account TYPE datetime DEFAULT time::now();
DEFINE INDEX account_provider_idx ON account FIELDS providerId, accountId UNIQUE;
DEFINE INDEX account_userId_idx ON account FIELDS userId;

-- TABLE: verification (Auth Tokens)
DEFINE TABLE verification SCHEMAFULL;
DEFINE FIELD identifier ON verification TYPE string;
DEFINE FIELD value ON verification TYPE string;
DEFINE FIELD expiresAt ON verification TYPE datetime;
DEFINE FIELD createdAt ON verification TYPE datetime DEFAULT time::now();
DEFINE FIELD updatedAt ON verification TYPE datetime DEFAULT time::now();
DEFINE INDEX verification_identifier_idx ON verification FIELDS identifier;
DEFINE INDEX verification_value_idx ON verification FIELDS value UNIQUE;

-- TABLE: twoFactor
DEFINE TABLE twoFactor SCHEMAFULL;
DEFINE FIELD userId ON twoFactor TYPE record<user>;
DEFINE FIELD secret ON twoFactor TYPE string;
DEFINE FIELD backupCodes ON twoFactor TYPE option<array<string>>;
DEFINE FIELD enabled ON twoFactor TYPE bool DEFAULT false;
DEFINE FIELD createdAt ON twoFactor TYPE datetime DEFAULT time::now();
DEFINE FIELD updatedAt ON twoFactor TYPE datetime DEFAULT time::now();
DEFINE INDEX twoFactor_userId_idx ON twoFactor FIELDS userId UNIQUE;

-- TABLE: organization
DEFINE TABLE organization SCHEMAFULL;
DEFINE FIELD name ON organization TYPE string;
DEFINE FIELD slug ON organization TYPE string;
DEFINE FIELD logo ON organization TYPE option<string>;
DEFINE FIELD metadata ON organization TYPE option<object> DEFAULT {};
DEFINE FIELD createdAt ON organization TYPE datetime DEFAULT time::now();
DEFINE FIELD updatedAt ON organization TYPE datetime DEFAULT time::now();
DEFINE INDEX organization_slug_idx ON organization FIELDS slug UNIQUE;

-- TABLE: member
DEFINE TABLE member SCHEMAFULL;
DEFINE FIELD userId ON member TYPE record<user>;
DEFINE FIELD organizationId ON member TYPE record<organization>;
DEFINE FIELD role ON member TYPE string DEFAULT 'member';
DEFINE FIELD createdAt ON member TYPE datetime DEFAULT time::now();
DEFINE FIELD updatedAt ON member TYPE datetime DEFAULT time::now();
DEFINE INDEX member_user_org_idx ON member FIELDS userId, organizationId UNIQUE;
DEFINE INDEX member_org_idx ON member FIELDS organizationId;

-- TABLE: invitation
DEFINE TABLE invitation SCHEMAFULL;
DEFINE FIELD email ON invitation TYPE string ASSERT string::is::email($value);
DEFINE FIELD organizationId ON invitation TYPE record<organization>;
DEFINE FIELD inviterId ON invitation TYPE record<user>;
DEFINE FIELD role ON invitation TYPE string DEFAULT 'member';
DEFINE FIELD token ON invitation TYPE string;
DEFINE FIELD expiresAt ON invitation TYPE datetime;
DEFINE FIELD status ON invitation TYPE string DEFAULT 'pending';
DEFINE FIELD createdAt ON invitation TYPE datetime DEFAULT time::now();
DEFINE FIELD updatedAt ON invitation TYPE datetime DEFAULT time::now();
DEFINE INDEX invitation_token_idx ON invitation FIELDS token UNIQUE;
DEFINE INDEX invitation_org_idx ON invitation FIELDS organizationId;
DEFINE INDEX invitation_email_idx ON invitation FIELDS email;

-- TABLE: processing_log (Extension)
DEFINE TABLE processing_log SCHEMAFULL;
DEFINE FIELD userId ON processing_log TYPE record<user>;
DEFINE FIELD action ON processing_log TYPE string;
DEFINE FIELD fileName ON processing_log TYPE string;
DEFINE FIELD fileSize ON processing_log TYPE number;
DEFINE FIELD status ON processing_log TYPE string;
DEFINE FIELD metadata ON processing_log TYPE option<object> DEFAULT {};
DEFINE FIELD createdAt ON processing_log TYPE datetime DEFAULT time::now();
DEFINE INDEX log_userId_idx ON processing_log FIELDS userId;
DEFINE INDEX log_action_idx ON processing_log FIELDS action;
DEFINE INDEX log_createdAt_idx ON processing_log FIELDS createdAt;

-- EVENTS: Cleanup
DEFINE EVENT session_cleanup ON TABLE session WHEN $event = "CREATE" OR $event = "UPDATE" THEN {
    DELETE session WHERE expiresAt < time::now();
};
DEFINE EVENT verification_cleanup ON TABLE verification WHEN $event = "CREATE" OR $event = "UPDATE" THEN {
    DELETE verification WHERE expiresAt < time::now();
};
DEFINE EVENT invitation_cleanup ON TABLE invitation WHEN $event = "CREATE" OR $event = "UPDATE" THEN {
    DELETE invitation WHERE expiresAt < time::now() AND status = 'pending';
};

-- ============================================================================
-- 2. APPLICATION DOMAIN (OccultaShield)
-- ============================================================================

-- TABLE: video
DEFINE TABLE video SCHEMALESS;
DEFINE FIELD user_id ON TABLE video TYPE record<user> ASSERT $value != NONE;
DEFINE FIELD filename ON TABLE video TYPE string ASSERT string::len($value) >= 1;
DEFINE FIELD original_path ON TABLE video TYPE string;
DEFINE FIELD processed_path ON TABLE video TYPE string;
DEFINE FIELD status ON TABLE video TYPE string 
    ASSERT $value INSIDE ['pending', 'processing', 'detected', 'verified', 'editing', 'completed', 'error'] 
    DEFAULT 'pending';
DEFINE FIELD metadata ON TABLE video TYPE object DEFAULT {};
DEFINE FIELD error_message ON TABLE video TYPE string;
DEFINE FIELD processing_started_at ON TABLE video TYPE datetime;
DEFINE FIELD processing_completed_at ON TABLE video TYPE datetime;
DEFINE FIELD created_at ON TABLE video TYPE datetime DEFAULT time::now();
DEFINE FIELD updated_at ON TABLE video TYPE datetime DEFAULT time::now();
DEFINE INDEX idx_video_user ON TABLE video COLUMNS user_id;
DEFINE INDEX idx_video_status ON TABLE video COLUMNS status;
DEFINE INDEX idx_video_created ON TABLE video COLUMNS created_at;

-- TABLE: detection
DEFINE TABLE detection SCHEMALESS;
DEFINE FIELD video_id ON TABLE detection TYPE record<video> ASSERT $value != NONE;
DEFINE FIELD track_id ON TABLE detection TYPE int ASSERT $value >= 0;
DEFINE FIELD detection_type ON TABLE detection TYPE string 
    ASSERT $value INSIDE ['face', 'license_plate', 'person', 'document', 'minor', 'nude_body', 'other'];
DEFINE FIELD first_frame ON TABLE detection TYPE int ASSERT $value >= 0;
DEFINE FIELD last_frame ON TABLE detection TYPE int ASSERT $value >= 0;
DEFINE FIELD duration_seconds ON TABLE detection TYPE float ASSERT $value >= 0;
DEFINE FIELD avg_confidence ON TABLE detection TYPE float DEFAULT 0.0;
DEFINE FIELD max_confidence ON TABLE detection TYPE float DEFAULT 0.0;
DEFINE FIELD bbox_history ON TABLE detection TYPE array DEFAULT [];
DEFINE FIELD captures ON TABLE detection TYPE array DEFAULT [];
DEFINE FIELD storage_path ON TABLE detection TYPE string;
DEFINE FIELD created_at ON TABLE detection TYPE datetime DEFAULT time::now();
DEFINE INDEX idx_detection_video ON TABLE detection COLUMNS video_id;
DEFINE INDEX idx_detection_type ON TABLE detection COLUMNS detection_type;

-- TABLE: gdpr_verification (RENAMED from verification to avoid conflict with auth)
DEFINE TABLE gdpr_verification SCHEMALESS;
DEFINE FIELD detection_id ON TABLE gdpr_verification TYPE record<detection> ASSERT $value != NONE;
DEFINE FIELD capture_index ON TABLE gdpr_verification TYPE int DEFAULT 0;
DEFINE FIELD is_violation ON TABLE gdpr_verification TYPE bool DEFAULT false;
DEFINE FIELD severity ON TABLE gdpr_verification TYPE string 
    ASSERT $value INSIDE ['none', 'low', 'medium', 'high', 'critical'] 
    DEFAULT 'none';
DEFINE FIELD violated_articles ON TABLE gdpr_verification TYPE array DEFAULT [];
DEFINE FIELD detected_personal_data ON TABLE gdpr_verification TYPE array DEFAULT [];
DEFINE FIELD description ON TABLE gdpr_verification TYPE string DEFAULT '';
DEFINE FIELD legal_basis_required ON TABLE gdpr_verification TYPE string;
DEFINE FIELD recommended_action ON TABLE gdpr_verification TYPE string DEFAULT '';
DEFINE FIELD confidence ON TABLE gdpr_verification TYPE float DEFAULT 0.0;
DEFINE FIELD processing_time_ms ON TABLE gdpr_verification TYPE int;
DEFINE FIELD llm_model ON TABLE gdpr_verification TYPE string DEFAULT 'gemma-3-4b';
DEFINE FIELD llm_raw_response ON TABLE gdpr_verification TYPE string;
DEFINE FIELD created_at ON TABLE gdpr_verification TYPE datetime DEFAULT time::now();
DEFINE INDEX idx_verification_detection ON TABLE gdpr_verification COLUMNS detection_id;
DEFINE INDEX idx_verification_violation ON TABLE gdpr_verification COLUMNS is_violation;
DEFINE INDEX idx_verification_severity ON TABLE gdpr_verification COLUMNS severity;

-- TABLE: user_decision
DEFINE TABLE user_decision SCHEMALESS;
DEFINE FIELD verification_id ON TABLE user_decision TYPE record<gdpr_verification> ASSERT $value != NONE;
DEFINE FIELD user_id ON TABLE user_decision TYPE record<user> ASSERT $value != NONE;
DEFINE FIELD action ON TABLE user_decision TYPE string 
    ASSERT $value INSIDE ['no_modify', 'blur', 'pixelate', 'mask'];
DEFINE FIELD confirmed_violation ON TABLE user_decision TYPE bool DEFAULT true;
DEFINE FIELD rejection_reason ON TABLE user_decision TYPE string;
DEFINE FIELD notes ON TABLE user_decision TYPE string;
DEFINE FIELD created_at ON TABLE user_decision TYPE datetime DEFAULT time::now();
DEFINE INDEX idx_decision_verification ON TABLE user_decision COLUMNS verification_id;
DEFINE INDEX idx_decision_user ON TABLE user_decision COLUMNS user_id;

-- TABLE: processing_progress
DEFINE TABLE processing_progress SCHEMALESS;
DEFINE FIELD video_id ON TABLE processing_progress TYPE record<video>;
DEFINE FIELD phase ON TABLE processing_progress TYPE string 
    ASSERT $value INSIDE ['pending', 'detecting', 'tracking', 'verifying', 'saving', 'editing', 'completed', 'error'] 
    DEFAULT 'pending';
DEFINE FIELD current_frame ON TABLE processing_progress TYPE int DEFAULT 0;
DEFINE FIELD total_frames ON TABLE processing_progress TYPE int DEFAULT 0;
DEFINE FIELD percentage ON TABLE processing_progress TYPE int DEFAULT 0;
DEFINE FIELD fps_processing ON TABLE processing_progress TYPE float DEFAULT 0.0;
DEFINE FIELD active_detections ON TABLE processing_progress TYPE int DEFAULT 0;
DEFINE FIELD total_detections ON TABLE processing_progress TYPE int DEFAULT 0;
DEFINE FIELD total_violations ON TABLE processing_progress TYPE int DEFAULT 0;
DEFINE FIELD message ON TABLE processing_progress TYPE string DEFAULT '';
DEFINE FIELD error_code ON TABLE processing_progress TYPE string;
DEFINE FIELD error_message ON TABLE processing_progress TYPE string;
DEFINE FIELD started_at ON TABLE processing_progress TYPE datetime;
DEFINE FIELD updated_at ON TABLE processing_progress TYPE datetime DEFAULT time::now();
DEFINE INDEX idx_progress_video ON TABLE processing_progress COLUMNS video_id UNIQUE;
