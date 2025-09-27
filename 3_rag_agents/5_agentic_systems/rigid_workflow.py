#!/usr/bin/env python3
"""
Rigid workflow example - shows brittleness of hard-coded logic
"""

def process_email(email):
    """Brittle email processing with hard-coded rules"""

    if "urgent" in email.lower():
        if "payment" in email.lower():
            if "overdue" in email.lower():
                return "escalate_to_finance"
            else:
                return "process_payment"
        elif "delivery" in email.lower():
            return "check_shipping_status"
        else:
            return "general_urgent"
    elif "complaint" in email.lower():
        if "product" in email.lower():
            return "forward_to_quality"
        elif "service" in email.lower():
            return "forward_to_support"
        else:
            return "general_complaint"
    else:
        return "inbox"

# Test cases that break the rigid system
test_emails = [
    "URGENT: Payment is past due and we need immediate action",
    "Customer complaint about delayed shipment and poor service quality",
    "Important: New regulations require compliance update",  # Breaks - no handler
    "Emergency: System down, customers can't place orders"    # Breaks - no handler
]

if __name__ == "__main__":
    print("Rigid Workflow Demo\n" + "="*20)

    for email in test_emails:
        result = process_email(email)
        print(f"Email: {email[:50]}...")
        print(f"Action: {result}\n")

        if result in ["inbox", "general_urgent", "general_complaint"]:
            print("⚠️  FALLBACK USED - May miss important actions\n")