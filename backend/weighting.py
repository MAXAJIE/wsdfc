"""
Mathematical weighting and scoring pipeline.
- Base weight vector (frozen at development time)
- Dynamic multipliers by gender and identity
- Tier 1/2 classification before weighting
"""
from schemas import Property

# Base weight vector (Σ = 1.0)
BASE_WEIGHT_VECTOR = {
    "price_fit_score": 0.30,
    "security_score": 0.25,
    "facilities_score": 0.20,
    "lifestyle_proximity_score": 0.15,
    "maintenance_fee_score": 0.05,  # Negative score: (1 - maintenance)
    "transit_proximity_score": 0.05,
}

# Gender multipliers
GENDER_MULTIPLIERS = {
    "female": {
        "security_score": 1.30,
        "lifestyle_proximity_score": 1.15,
    },
    "male": {},
    "prefer_not_to_say": {},
}

# Identity multipliers
IDENTITY_MULTIPLIERS = {
    "first_time_buyer": {
        "price_fit_score": 1.30,
        "facilities_score": 1.10,
        "maintenance_fee_score": 1.20,
    },
    "investor": {
        "maintenance_fee_score": 1.25,
        "transit_proximity_score": 1.30,
    },
    "upgrader": {
        "facilities_score": 1.20,
        "security_score": 1.15,
    },
}


def apply_dynamic_weights(
    base: dict,
    gender: str,
    identity: str,
) -> dict:
    """
    Apply gender and identity multipliers, then normalize to Σ = 1.0.
    Strict validation: assert final sum = 1.0 (within floating point tolerance).
    """
    adjusted = base.copy()

    # Apply gender multipliers
    for dim, multiplier in GENDER_MULTIPLIERS.get(gender, {}).items():
        adjusted[dim] *= multiplier

    # Apply identity multipliers
    for dim, multiplier in IDENTITY_MULTIPLIERS.get(identity, {}).items():
        adjusted[dim] *= multiplier

    # Normalize
    total = sum(adjusted.values())
    if total <= 0:
        raise ValueError(f"Weight sum is zero, normalization failed: {adjusted}")

    normalized = {k: v / total for k, v in adjusted.items()}

    # Strict validation
    final_sum = sum(normalized.values())
    if abs(final_sum - 1.0) >= 1e-9:
        raise ValueError(
            f"Normalized weights don't sum to 1.0: {final_sum}. Weights: {normalized}"
        )

    return normalized


def compute_weighted_score(
    property: Property,
    weights: dict,
) -> float:
    """
    Compute weighted score for a single property.
    maintenance_fee_score is inverted: (1 - normalized_maintenance_fee)
    """
    return (
        weights["price_fit_score"] * property.price_fit_score +
        weights["security_score"] * property.security_score +
        weights["facilities_score"] * property.facilities_score +
        weights["lifestyle_proximity_score"] * property.lifestyle_proximity_score +
        weights["maintenance_fee_score"] * (1 - property.normalized_maintenance_fee) +
        weights["transit_proximity_score"] * property.transit_proximity_score
    )


def build_top10(
    tier1_pool: list[Property],
    tier2_pool: list[Property],
    weight_vector: dict,
) -> list[tuple[float, Property, str]]:
    """
    Build Top 10 from Tier 1 and Tier 2 pools with smart tier bias.
    
    Returns: list of (score, property, tier) tuples, sorted descending by score.
    
    Algorithm:
    1. Filter properties with None prices to tier 3 (abandoned)
    2. Sort Tier 1 by (score desc, price asc, property_id asc)
    3. If Tier 1 >= 10: return top 10
    4. If best Tier 2 score >= 90% of best Tier 1: re-sort merged list (pure merit)
    5. Otherwise: keep Tier 1 bias, fill from Tier 2
    
    Tiebreaker: lowest price first (value properties ranked higher)
    """
    # Helper: filter properties with valid prices, collect None-price to tier 3
    def has_valid_price(p: Property) -> bool:
        return p.scraped_data.price is not None
    
    # Filter pools, abandoning None prices to tier 3
    tier1_valid = [p for p in tier1_pool if has_valid_price(p)]
    tier2_valid = [p for p in tier2_pool if has_valid_price(p)]
    
    # Compute scores and build tuples with price tiebreaker (ascending = lowest first)
    scored_tier1 = [
        (compute_weighted_score(p, weight_vector), p, "tier_1")
        for p in tier1_valid
    ]
    
    # Sort by score (desc), then by price (asc for value), then by property_id (asc for determinism)
    scored_tier1.sort(
        key=lambda x: (
            -x[0],  # Score descending
            x[1].scraped_data.price,  # Price ascending (lowest first)
            x[1].property_id,  # Property ID ascending (determinism)
        ),
        reverse=False,
    )
    
    if len(scored_tier1) >= 10:
        return scored_tier1[:10]
    
    # Need to fill with Tier 2
    needed = 10 - len(scored_tier1)
    scored_tier2 = [
        (compute_weighted_score(p, weight_vector), p, "tier_2")
        for p in tier2_valid
    ]
    
    scored_tier2.sort(
        key=lambda x: (
            -x[0],  # Score descending
            x[1].scraped_data.price,  # Price ascending
            x[1].property_id,  # Property ID ascending
        ),
        reverse=False,
    )
    
    # Smart Tier 1 bias: only re-sort if best Tier 2 >= 90% of best Tier 1
    top10 = scored_tier1 + scored_tier2[:needed]
    
    if scored_tier2 and len(scored_tier2) > 0:
        best_tier1_score = scored_tier1[0][0] if scored_tier1 else 0.0
        best_tier2_score = scored_tier2[0][0]
        
        # Re-sort to pure merit-based only if Tier 2 is competitive
        if best_tier1_score > 0 and best_tier2_score >= 0.90 * best_tier1_score:
            top10.sort(
                key=lambda x: (
                    -x[0],  # Score descending
                    x[1].scraped_data.price,  # Price ascending
                    x[1].property_id,  # Property ID ascending
                ),
                reverse=False,
            )
            top10 = top10[:10]
    
    return top10