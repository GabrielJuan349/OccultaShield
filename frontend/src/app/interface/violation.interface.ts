/**
 * Violation and GDPR detection interfaces
 * Used by: VideoService, ReviewPage, ViolationCard component
 */

// === Severity Levels ===

export type SeverityLevel = 'none' | 'low' | 'medium' | 'high' | 'critical';

// === Modification Actions ===

export type ModificationType = 'no_modify' | 'pixelate' | 'mask' | 'blur';

// === Backend Response Types ===

/**
 * ViolationCard from backend API
 * Represents a GDPR verification result
 */
export interface ViolationCard {
  verification_id: string;
  detection_id: string;
  is_violation: boolean;
  severity: SeverityLevel;
  violated_articles: string[];
  description: string;
  fine_text: string;
  recommended_action: string;
  confidence: number;
  capture_image_url: string;
  thumbnail_url?: string;
  detection_type: string;
  duration_seconds?: number;
  first_frame?: number;
  last_frame?: number;
  timestamp?: string;
  track_id?: number | string;
  frames_analyzed?: number;
  frames_with_violation?: number;
}

// === UI Display Types ===

/**
 * Violation model for UI display
 * Used in ReviewPage component
 */
export interface Violation {
  id: string;
  articleTitle: string;
  articleSubtitle: string;
  description: string;
  fineText: string;
  imageUrl: string;
  selectedOption: ModificationType;
  framesAnalyzed?: number;
  confidence?: number;
  recommendedAction?: ModificationType;
  isViolation?: boolean;
  severity?: SeverityLevel;
}

// === User Decision Types ===

export interface UserDecision {
  verification_id: string;
  action: ModificationType;
  confirmed_violation: boolean;
}

export interface UserDecisionBatch {
  decisions: UserDecision[];
}
