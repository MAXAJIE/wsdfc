/**
 * Frontend display labels for semantic tags (enums from backend).
 * Maps internal enum keys to user-friendly display text.
 */

export const PPP_LABELS: Record<string, string> = {
  // Positive Property Preferences (required features)
  "needs_security": "24h Security",
  "needs_gated": "Gated Community",
  "needs_near_mrt": "Near MRT",
  "needs_near_lrt": "Near LRT",
  "needs_near_highway": "Close to Highway",
  "needs_high_floor": "High Floor",
  "needs_south_facing": "South Facing",
  "needs_natural_light": "Natural Light",
  "needs_balcony": "Balcony",
  "needs_pool": "Swimming Pool",
  "needs_gym": "Gym",
  "needs_parking": "Parking",
  "needs_covered_parking": "Covered Parking",
  "needs_lift": "Lift/Elevator",
  "needs_near_school": "Near School",
  "needs_near_mall": "Near Mall",
  "needs_near_hospital": "Near Hospital",
  "pet_friendly": "Pet Friendly",
  "furnished": "Furnished",
  "new_building": "New Building",
  // Generic/catchall
  "modern_style": "Modern Style",
  "double_storey": "Double Storey",
  "johor_bahru": "Johor Bahru",
  "kuala_lumpur": "Kuala Lumpur",
  "penang": "Penang",
  "iskandar_puteri": "Iskandar Puteri",
};

export const NPP_LABELS: Record<string, string> = {
  // Negative Property Preferences (exclusions)
  "west_facing": "West Facing",
  "east_facing": "East Facing",
  "no_natural_light": "No Natural Light",
  "no_balcony": "No Balcony",
  "high_floor": "High Floor",
  "low_floor": "Low Floor",
  "top_floor": "Top Floor",
  "ground_floor": "Ground Floor",
  "far_from_mrt": "Far from MRT",
  "far_from_bus": "Far from Bus",
  "far_from_highway": "Far from Highway",
  "no_pool": "No Swimming Pool",
  "no_gym": "No Gym",
  "no_security": "No Security",
  "no_parking": "No Parking",
  "no_visitor_parking": "No Visitor Parking",
  "frequent_lift_issues": "Frequent Lift Issues",
  "far_from_school": "Far from School",
  "far_from_hospital": "Far from Hospital",
  "far_from_mall": "Far from Mall",
  "near_industrial": "Near Industrial Area",
  "noise_area": "Noisy Area",
  "near_cemetery": "Near Cemetery",
  "near_power_lines": "Near Power Lines",
  "near_mosque": "Near Mosque",
  "open_kitchen": "Open Kitchen",
  "no_storage": "No Storage",
  "small_unit": "Small Unit",
  "high_tenant_mix": "Mixed Tenants",
  "no_dog": "No Dogs",
  "no_noise": "No Noise Tolerance",
};

/**
 * Get display label for a tag. Falls back to formatted tag name if not in mapping.
 */
export function getTagLabel(tag: string, polarity: "pos" | "neg" = "neg"): string {
  const mapping = polarity === "pos" ? PPP_LABELS : NPP_LABELS;
  if (tag in mapping) {
    return mapping[tag];
  }
  // Fallback: convert snake_case to Title Case
  return tag
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

