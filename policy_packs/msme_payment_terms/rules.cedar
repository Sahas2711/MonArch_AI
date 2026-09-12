// Rule 1: payment cycle exceeding the MSME Act 45-day limit
permit (
  principal,
  action == Action::"flag",
  resource
) when {
  resource.paymentDays > 45
};

// Rule 2: missing statutory penalty-interest entitlement
permit (
  principal,
  action == Action::"flag",
  resource
) when {
  resource.hasPenaltyInterestClause == false
};

// Rule 3: one-sided cancellation terms
permit (
  principal,
  action == Action::"flag",
  resource
) when {
  resource.hasUnilateralCancellation == true
};
