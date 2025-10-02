#!/usr/bin/env python3
"""
Integration test for business unit consolidation with journal entries
Tests the full consolidation workflow with actual financial data
"""

import requests
import json
from datetime import datetime, timezone

# Configuration
BASE_URL = "https://erp-dashboard-31.preview.emergentagent.com/api"
TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "password123"

class ConsolidationIntegrationTester:
    def __init__(self):
        self.session = requests.Session()
        self.token = None
        self.tenant_id = None
        
    def login(self):
        """Login and get authentication token"""
        try:
            response = self.session.post(f"{BASE_URL}/auth/login", json={
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD
            })
            
            if response.status_code == 200:
                data = response.json()
                self.token = data["token"]
                self.tenant_id = data["tenant"]["id"]
                self.session.headers.update({"Authorization": f"Bearer {self.token}"})
                print("✅ Successfully authenticated")
                return True
            else:
                print(f"❌ Login failed with status {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Login error: {str(e)}")
            return False
    
    def test_consolidation_with_journal_entries(self):
        """Test full consolidation workflow with journal entries"""
        print("\n🧪 Testing Business Unit Consolidation with Journal Entries")
        print("-" * 60)
        
        try:
            # 1. Create a parent subsidiary company
            print("1. Creating parent subsidiary company...")
            subsidiary_data = {
                "name": "Parent Subsidiary Corp",
                "industry": "restaurant"
            }
            response = self.session.post(f"{BASE_URL}/companies", json=subsidiary_data)
            if response.status_code != 200:
                print("❌ Failed to create parent subsidiary")
                return False
            
            parent_subsidiary = response.json()
            parent_subsidiary_id = parent_subsidiary["id"]
            print(f"✅ Created parent subsidiary: {parent_subsidiary['name']}")
            
            # 2. Get an existing company to create business units under
            response = self.session.get(f"{BASE_URL}/companies")
            if response.status_code != 200:
                print("❌ Failed to get companies")
                return False
            
            companies = response.json()
            if not companies:
                print("❌ No companies found")
                return False
            
            main_company_id = companies[0]["id"]
            print(f"✅ Using main company: {companies[0]['name']}")
            
            # 3. Create business units with consolidation settings
            print("2. Creating business units with consolidation...")
            bu_data_list = [
                {
                    "company_id": main_company_id,
                    "name": "Operations BU",
                    "code": "BU-OPS-CONSOL",
                    "description": "Operations business unit for consolidation",
                    "parent_subsidiary_id": parent_subsidiary_id,
                    "consolidation_enabled": True
                },
                {
                    "company_id": main_company_id,
                    "name": "Sales BU",
                    "code": "BU-SALES-CONSOL",
                    "description": "Sales business unit for consolidation",
                    "parent_subsidiary_id": parent_subsidiary_id,
                    "consolidation_enabled": True
                }
            ]
            
            created_bus = []
            for bu_data in bu_data_list:
                response = self.session.post(f"{BASE_URL}/business-units", json=bu_data)
                if response.status_code == 200:
                    bu = response.json()
                    created_bus.append(bu)
                    print(f"✅ Created BU: {bu['name']} (consolidates to parent subsidiary)")
                else:
                    print(f"❌ Failed to create BU: {bu_data['name']}")
                    return False
            
            # 4. Create accounts for journal entries (workaround for accounts endpoint issue)
            print("3. Creating test accounts...")
            
            # Create cash account
            cash_account_data = {
                "company_id": main_company_id,
                "code": "1000",
                "name": "Cash",
                "account_type": "Asset"
            }
            response = self.session.post(f"{BASE_URL}/finance/accounts", json=cash_account_data)
            if response.status_code == 200:
                cash_account = response.json()
                print("✅ Created Cash account")
            elif response.status_code == 400 and "already exists" in response.text:
                # Account already exists, create a unique one
                cash_account_data["code"] = "1001"
                cash_account_data["name"] = "Cash Test"
                response = self.session.post(f"{BASE_URL}/finance/accounts", json=cash_account_data)
                if response.status_code == 200:
                    cash_account = response.json()
                    print("✅ Created Cash Test account")
                else:
                    print("❌ Failed to create cash account")
                    return False
            else:
                print("❌ Failed to create cash account")
                return False
            
            # Create revenue account
            revenue_account_data = {
                "company_id": main_company_id,
                "code": "4000",
                "name": "Revenue",
                "account_type": "Revenue"
            }
            response = self.session.post(f"{BASE_URL}/finance/accounts", json=revenue_account_data)
            if response.status_code == 200:
                revenue_account = response.json()
                print("✅ Created Revenue account")
            elif response.status_code == 400 and "already exists" in response.text:
                # Account already exists, create a unique one
                revenue_account_data["code"] = "4001"
                revenue_account_data["name"] = "Revenue Test"
                response = self.session.post(f"{BASE_URL}/finance/accounts", json=revenue_account_data)
                if response.status_code == 200:
                    revenue_account = response.json()
                    print("✅ Created Revenue Test account")
                else:
                    print("❌ Failed to create revenue account")
                    return False
            else:
                print("❌ Failed to create revenue account")
                return False
            
            # 5. Create journal entries for each business unit
            print("4. Creating journal entries for business units...")
            entry_date = datetime.now(timezone.utc).isoformat()
            
            for i, bu in enumerate(created_bus):
                amount = 1000 + (i * 500)  # Different amounts for each BU
                
                je_data = {
                    "company_id": main_company_id,
                    "business_unit_id": bu["id"],
                    "entry_date": entry_date,
                    "description": f"Test revenue entry for {bu['name']}",
                    "reference": f"TEST-{bu['code']}-001",
                    "lines": [
                        {
                            "account_id": cash_account["id"],
                            "debit": amount,
                            "credit": 0,
                            "memo": f"Cash from {bu['name']}"
                        },
                        {
                            "account_id": revenue_account["id"],
                            "debit": 0,
                            "credit": amount,
                            "memo": f"Revenue from {bu['name']}"
                        }
                    ]
                }
                
                response = self.session.post(f"{BASE_URL}/finance/journal-entries", json=je_data)
                if response.status_code == 200:
                    print(f"✅ Created journal entry for {bu['name']}: ${amount}")
                else:
                    print(f"❌ Failed to create journal entry for {bu['name']}")
                    return False
            
            # 6. Test individual BU consolidation data
            print("5. Testing individual BU consolidation data...")
            for bu in created_bus:
                response = self.session.get(f"{BASE_URL}/business-units/{bu['id']}/consolidation")
                if response.status_code == 200:
                    data = response.json()
                    summary = data["consolidation_summary"]
                    print(f"✅ {bu['name']} consolidation: ${summary['total_debits']} debits, ${summary['total_credits']} credits, {summary['entries_count']} entries")
                    
                    # Verify parent subsidiary info
                    if data.get("parent_subsidiary") and data["parent_subsidiary"]["id"] == parent_subsidiary_id:
                        print(f"   ✅ Correctly linked to parent subsidiary: {data['parent_subsidiary']['name']}")
                    else:
                        print(f"   ❌ Parent subsidiary link incorrect")
                        return False
                else:
                    print(f"❌ Failed to get consolidation data for {bu['name']}")
                    return False
            
            # 7. Test consolidated report for parent subsidiary
            print("6. Testing consolidated report for parent subsidiary...")
            response = self.session.get(f"{BASE_URL}/companies/{parent_subsidiary_id}/consolidated-report")
            if response.status_code == 200:
                data = response.json()
                totals = data["consolidated_totals"]
                bu_summaries = data["business_units_summary"]
                
                print(f"✅ Consolidated report generated:")
                print(f"   Total debits: ${totals['total_debits']}")
                print(f"   Total credits: ${totals['total_credits']}")
                print(f"   Net balance: ${totals['net_balance']}")
                print(f"   Total entries: {totals['total_entries']}")
                print(f"   Business units included: {len(bu_summaries)}")
                
                # Verify all created BUs are included
                included_bu_ids = [summary["business_unit"]["id"] for summary in bu_summaries]
                expected_bu_ids = [bu["id"] for bu in created_bus]
                
                if set(included_bu_ids) >= set(expected_bu_ids):
                    print("   ✅ All business units correctly included in consolidation")
                else:
                    print("   ❌ Some business units missing from consolidation")
                    return False
            else:
                print(f"❌ Failed to get consolidated report")
                return False
            
            # 8. Test date filtering
            print("7. Testing date filtering in consolidation...")
            today = datetime.now(timezone.utc).date().isoformat()
            response = self.session.get(f"{BASE_URL}/companies/{parent_subsidiary_id}/consolidated-report", 
                                      params={"start_date": f"{today}T00:00:00Z", "end_date": f"{today}T23:59:59Z"})
            if response.status_code == 200:
                data = response.json()
                if data["consolidation_period"]["start_date"] and data["consolidation_period"]["end_date"]:
                    print("✅ Date filtering works correctly")
                else:
                    print("❌ Date filtering not working")
                    return False
            else:
                print("❌ Failed to test date filtering")
                return False
            
            # 9. Test disabling consolidation
            print("8. Testing consolidation disable/enable...")
            test_bu = created_bus[0]
            
            # Disable consolidation
            response = self.session.post(f"{BASE_URL}/business-units/{test_bu['id']}/set-consolidation", 
                                       params={"consolidation_enabled": False})
            if response.status_code == 200:
                print(f"✅ Disabled consolidation for {test_bu['name']}")
                
                # Check consolidated report excludes disabled BU
                response = self.session.get(f"{BASE_URL}/companies/{parent_subsidiary_id}/consolidated-report")
                if response.status_code == 200:
                    data = response.json()
                    included_bu_ids = [summary["business_unit"]["id"] for summary in data["business_units_summary"]]
                    
                    if test_bu["id"] not in included_bu_ids:
                        print("   ✅ Disabled BU correctly excluded from consolidation")
                    else:
                        print("   ❌ Disabled BU still included in consolidation")
                        return False
                else:
                    print("   ❌ Failed to verify exclusion")
                    return False
            else:
                print(f"❌ Failed to disable consolidation")
                return False
            
            # Clean up
            print("9. Cleaning up test data...")
            for bu in created_bus:
                self.session.delete(f"{BASE_URL}/business-units/{bu['id']}")
            self.session.delete(f"{BASE_URL}/companies/{parent_subsidiary_id}")
            print("✅ Cleanup completed")
            
            print("\n🎉 All consolidation integration tests passed!")
            return True
            
        except Exception as e:
            print(f"❌ Integration test error: {str(e)}")
            return False

def main():
    tester = ConsolidationIntegrationTester()
    
    if not tester.login():
        print("❌ Authentication failed - cannot proceed with integration tests")
        return False
    
    success = tester.test_consolidation_with_journal_entries()
    
    if success:
        print("\n✅ Business Unit Consolidation Integration Test: PASSED")
    else:
        print("\n❌ Business Unit Consolidation Integration Test: FAILED")
    
    return success

if __name__ == "__main__":
    main()