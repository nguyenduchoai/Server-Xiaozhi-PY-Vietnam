/**
 * Feature Flags Configuration
 * 
 * Controls incremental rollout of Semi UI migration.
 * Can be toggled for testing and gradual deployment.
 */

export const FEATURE_FLAGS = {
  ENABLE_SEMI_UI: true,
  ENABLE_SEMI_WRAPPERS: true,
  ENABLE_NEW_THEME: true,
  ENABLE_DARK_MODE: true,
} as const

export const ROLLOUT_CONFIG = {
  SEMI_UI_PERCENTAGE: 100,
  NEW_THEME_PERCENTAGE: 50,
  FEATURE_FLAGS_ENABLED: 1,
} as const

export type FeatureKey = keyof typeof FEATURE_FLAGS

export function isFeatureEnabled(feature: FeatureKey): boolean {
  return FEATURE_FLAGS[feature]
}

export function setFeature(feature: FeatureKey, enabled: boolean): void {
  (FEATURE_FLAGS as Record<string, boolean>)[feature] = enabled
}

export function getRolloutPercentage(feature: keyof typeof ROLLOUT_CONFIG): number {
  return ROLLOUT_CONFIG[feature] as number
}