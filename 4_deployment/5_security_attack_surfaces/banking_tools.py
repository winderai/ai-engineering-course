#!/usr/bin/env python3
"""
Banking tools that can be accessed by the AI system
These simulate real banking functions that an AI assistant might have access to
"""

import json
import os
from typing import Dict, Any


def load_customer_db() -> Dict[str, Any]:
    """Load customer database from JSON file"""
    db_path = os.path.join(os.path.dirname(__file__), "customer_db.json")
    with open(db_path, "r") as f:
        return json.load(f)


def get_account_balance(account_id: str) -> Dict[str, Any]:
    """Get account balance - SENSITIVE FUNCTION"""
    db = load_customer_db()
    customer = db["customers"].get(account_id)

    if customer:
        return {
            "success": True,
            "account_id": account_id,
            "name": customer["name"],
            "balance": customer["balance"],
            "account_type": customer["account_type"],
        }
    else:
        return {"success": False, "error": "Account not found"}


def get_customer_info(account_id: str) -> Dict[str, Any]:
    """Get full customer information - HIGHLY SENSITIVE"""
    db = load_customer_db()
    customer = db["customers"].get(account_id)

    if customer:
        return {
            "success": True,
            "account_id": account_id,
            "name": customer["name"],
            "balance": customer["balance"],
            "ssn": customer["ssn"],
            "account_type": customer["account_type"],
            "last_login": customer["last_login"],
        }
    else:
        return {"success": False, "error": "Account not found"}


def list_all_customers() -> Dict[str, Any]:
    """List all customers - EXTREMELY SENSITIVE"""
    db = load_customer_db()
    return {"success": True, "customers": db["customers"]}


def get_branch_locations() -> Dict[str, Any]:
    """Get branch locations - PUBLIC INFORMATION"""
    return {
        "success": True,
        "branches": [
            {"id": 1, "address": "123 Main St, Anytown USA", "hours": "M-F 9-5"},
            {
                "id": 2,
                "address": "456 Oak Ave, Somewhere USA",
                "hours": "M-F 9-5, Sat 9-1",
            },
            {"id": 3, "address": "789 Pine Rd, Elsewhere USA", "hours": "M-F 9-6"},
        ],
    }


def get_bank_services() -> Dict[str, Any]:
    """Get available bank services - PUBLIC INFORMATION"""
    return {
        "success": True,
        "services": [
            "Checking accounts",
            "Savings accounts",
            "Personal loans",
            "Mortgages",
            "Investment services",
            "Credit cards",
        ],
    }


# Tool registry for the AI system
AVAILABLE_TOOLS = {
    "get_account_balance": {
        "function": get_account_balance,
        "description": "Get account balance for a customer",
        "security_level": "HIGH",
        "requires_auth": True,
    },
    "get_customer_info": {
        "function": get_customer_info,
        "description": "Get full customer information including SSN",
        "security_level": "CRITICAL",
        "requires_auth": True,
    },
    "list_all_customers": {
        "function": list_all_customers,
        "description": "List all customer data",
        "security_level": "CRITICAL",
        "requires_auth": True,
    },
    "get_branch_locations": {
        "function": get_branch_locations,
        "description": "Get bank branch locations",
        "security_level": "PUBLIC",
        "requires_auth": False,
    },
    "get_bank_services": {
        "function": get_bank_services,
        "description": "Get available banking services",
        "security_level": "PUBLIC",
        "requires_auth": False,
    },
}
