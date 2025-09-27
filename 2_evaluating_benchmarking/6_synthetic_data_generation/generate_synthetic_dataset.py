#!/usr/bin/env python3
import json
from litellm import completion

def generate_email_via_llm(category, characteristics):
    """Generate synthetic email using LiteLLM"""
    
    prompt = f"""Write a complete customer email to a brewery. This should be {characteristics[0]}.

Context: Customer is {characteristics[1]} and {characteristics[2]}.

Write the ACTUAL EMAIL that a customer would send, starting with a greeting and ending with a sign-off.
Use realistic fake names, dates, order numbers, and beer names. DO NOT USE PLACEHOLDERS.
Make it sound natural and conversational.

Category hint (don't mention in email): {category}

Write only the email text itself:"""

    try:
        response = completion(
            model="ollama/qwen3:1.7b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=200,
            extra_body={"think": False, "options": {"num_predict": 200, "temperature": 0.7}}
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error generating email: {e}")
        return None

def create_test_dataset():
    """Create synthetic dataset for Promptfoo evaluation"""
    
    test_cases = []
    
    # Define scenarios for each category
    scenarios = {
        "URGENT_ISSUE": [
            ["an urgent email about contaminated beer batch", "found mold in bottles purchased yesterday", "needs immediate response for health concerns"],
            ["an urgent email about a delivery truck accident", "driver reporting collision with brewery vehicle", "needs insurance information immediately"],
            ["an urgent email about refrigeration failure", "walk-in cooler stopped working overnight", "risk of losing entire inventory"],
            ["an urgent email about water main break", "flooding in the brewery basement", "needs emergency shutdown procedures"],
            ["an urgent email about failed health inspection", "inspector found critical violations", "brewery at risk of closure"]
        ],
        "SUPPLY_ORDER": [
            ["an email ordering hops and malt", "running low on Cascade hops", "needs 50kg by next week"],
            ["an email requesting bottle shipment", "need 5000 brown bottles", "monthly standing order"],
            ["an email about keg rental order", "local bar needing 20 kegs", "for weekend festival"],
            ["an email ordering cleaning supplies", "need sanitizer and caustic cleaner", "quarterly bulk order"],
            ["an email about CO2 tank delivery", "running low on carbonation supplies", "needs refill within 3 days"]
        ],
        "SCHEDULE": [
            ["an email requesting brewery tour booking", "group of 15 people", "available next Saturday afternoon"],
            ["an email about delivery schedule change", "restaurant needing earlier delivery", "lunch rush requirements"],
            ["an email scheduling equipment maintenance", "bottling line service due", "proposing next Tuesday morning"],
            ["an email about staff shift coverage", "employee calling in sick", "needs replacement for tonight"],
            ["an email booking private event space", "corporate happy hour event", "checking availability for next month"]
        ],
        "CUSTOMER": [
            ["an email complimenting the IPA", "best beer they've ever tasted", "wants to leave a 5-star review"],
            ["an email asking about gluten-free options", "customer with celiac disease", "looking for safe alternatives"],
            ["an email requesting loyalty program info", "frequent customer", "interested in membership benefits"],
            ["an email about missing order items", "received only half the order", "politely asking for resolution"],
            ["an email inquiring about gift cards", "wants to buy for Christmas presents", "asking about bulk discounts"]
        ],
        "MAINTENANCE": [
            ["an email about broken tap handle", "bar staff reporting issue", "needs replacement parts"],
            ["an email scheduling fermenter cleaning", "routine maintenance due", "coordinating downtime"],
            ["an email about bottling line calibration", "bottles under-filling", "technician availability check"],
            ["an email reporting HVAC issues", "temperature control problems", "affecting fermentation room"],
            ["an email about forklift repair needed", "hydraulic system leaking", "safety concern for warehouse"]
        ],
        "OTHER": [
            ["an email from local newspaper", "wanting to write brewery feature", "requesting interview with owner"],
            ["an email about lost and found item", "customer left jacket last night", "describing the item"],
            ["an email from brewery association", "annual membership renewal", "invoice attached"],
            ["an email about neighborhood noise complaint", "resident living nearby", "late night delivery disturbances"],
            ["an email from job applicant", "interested in brewer position", "attaching resume and references"]
        ]
    }
    
    for category, scenario_list in scenarios.items():
        for characteristics in scenario_list:
            print(f"Generating {category}: {characteristics[0]}...")
            
            email = generate_email_via_llm(category, characteristics)
            if email:
                test_case = {
                    "vars": {
                        "email": email
                    },
                    "assert": [
                        {
                            "type": "contains",
                            "value": category
                        }
                    ]
                }
                test_cases.append(test_case)
    
    return test_cases

if __name__ == "__main__":
    print("Generating synthetic email dataset...")
    dataset = create_test_dataset()
    
    # Save as JSON for use with Promptfoo
    with open("2_evaluating_benchmarking/6_synthetic_data_generation/synthetic_emails.json", "w") as f:
        json.dump(dataset, f, indent=2)
    
    print(f"Generated {len(dataset)} test cases")
    print("Saved to 2_evaluating_benchmarking/6_synthetic_data_generation/synthetic_emails.json")