#!/usr/bin/env python3
"""Test the semantic tag normalization logic"""

from llm_client import LLMClient
from positive_enum import PPP_ENUM_FULL
from npp_enum import NPP_ENUM_FULL

client = LLMClient()

# Test case 1: 'carpark' and 'securities' -> enum keys
print("=" * 60)
print("Test 1: Positive tags normalization")
print("=" * 60)
tags = ['carpark', 'securities']
result = client._normalize_tags_to_enum(tags, PPP_ENUM_FULL)
print(f"Input:  {tags}")
print(f"Output: {result}")
print(f"Expected: ['needs_parking', 'needs_security']")
print(f"✓ PASS" if result == ['needs_parking', 'needs_security'] else "✗ FAIL")

# Test case 2: negative tags
print("\n" + "=" * 60)
print("Test 2: Negative tags normalization")
print("=" * 60)
tags = ['no_dog', 'no_noise']
result = client._normalize_tags_to_enum(tags, NPP_ENUM_FULL)
print(f"Input:  {tags}")
print(f"Output: {result}")
print(f"Expected: ['no_dog', 'no_noise']")
print(f"✓ PASS" if result == ['no_dog', 'no_noise'] else "✗ FAIL")

# Test case 3: mixed synonyms
print("\n" + "=" * 60)
print("Test 3: Mixed synonyms and direct enum keys")
print("=" * 60)
tags = ['carpark', 'security', 'needs_gym']
result = client._normalize_tags_to_enum(tags, PPP_ENUM_FULL)
print(f"Input:  {tags}")
print(f"Output: {result}")
expected = ['needs_parking', 'needs_security', 'needs_gym']
print(f"Expected: {expected}")
print(f"✓ PASS" if result == expected else "✗ FAIL")

# Test case 4: space-separated synonyms
print("\n" + "=" * 60)
print("Test 4: Space-separated synonyms")
print("=" * 60)
tags = ['car park', '24h security', 'high floor']
result = client._normalize_tags_to_enum(tags, PPP_ENUM_FULL)
print(f"Input:  {tags}")
print(f"Output: {result}")
expected = ['needs_parking', 'needs_security', 'needs_high_floor']
print(f"Expected: {expected}")
print(f"✓ PASS" if result == expected else "✗ FAIL")

print("\n" + "=" * 60)
print("All tests completed!")
print("=" * 60)

