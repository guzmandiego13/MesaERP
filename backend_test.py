#!/usr/bin/env python3
"""
Backend API Testing for Company and Business Unit Edit/Delete Functionality
Tests the PUT and DELETE endpoints for companies and business units
"""

import requests
import json
import sys
from datetime import datetime

# Configuration
BASE_URL = "https://erp-dashboard-31.preview.emergentagent.com/api"
TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "password123"

class BackendTester:
    def __init__(self):
        self.session = requests.Session()
        self.token = None
        self.tenant_id = None
        self.test_company_id = None
        self.test_bu_id = None
        self.results = []
        
    def log_result(self, test_name, success, message, details=None):
        """Log test result"""
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "details": details
        }
        self.results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name} - {message}")
        if details and not success:
            print(f"   Details: {details}")
    
    def login(self):
        """Test login and get authentication token"""
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
                self.log_result("Login", True, "Successfully authenticated")
                return True
            else:
                self.log_result("Login", False, f"Login failed with status {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_result("Login", False, f"Login error: {str(e)}")
            return False
    
    def get_test_data(self):
        """Get existing companies and business units for testing"""
        try:
            # Get companies
            response = self.session.get(f"{BASE_URL}/companies")
            if response.status_code == 200:
                companies = response.json()
                if companies:
                    # Find a company that's not a parent (has no subsidiaries)
                    for company in companies:
                        if company.get("subsidiary_count", 0) == 0:
                            self.test_company_id = company["id"]
                            break
                    if not self.test_company_id and companies:
                        self.test_company_id = companies[0]["id"]
                    
                    self.log_result("Get Test Companies", True, f"Found {len(companies)} companies")
                else:
                    self.log_result("Get Test Companies", False, "No companies found for testing")
                    return False
            else:
                self.log_result("Get Test Companies", False, f"Failed to get companies: {response.status_code}")
                return False
            
            # Get business units
            response = self.session.get(f"{BASE_URL}/business-units")
            if response.status_code == 200:
                business_units = response.json()
                if business_units:
                    self.test_bu_id = business_units[0]["id"]
                    self.log_result("Get Test Business Units", True, f"Found {len(business_units)} business units")
                else:
                    self.log_result("Get Test Business Units", False, "No business units found for testing")
                    return False
            else:
                self.log_result("Get Test Business Units", False, f"Failed to get business units: {response.status_code}")
                return False
            
            return True
        except Exception as e:
            self.log_result("Get Test Data", False, f"Error getting test data: {str(e)}")
            return False
    
    def test_company_update(self):
        """Test company update endpoint"""
        if not self.test_company_id:
            self.log_result("Company Update", False, "No test company ID available")
            return False
        
        try:
            # Test valid update
            update_data = {
                "name": "Updated Test Company",
                "industry": "retail",
                "tax_id": "123-45-6789",
                "accounting_basis": "Accrual"
            }
            
            response = self.session.put(f"{BASE_URL}/companies/{self.test_company_id}", json=update_data)
            
            if response.status_code == 200:
                data = response.json()
                # Check that _id field is not present
                if "_id" in data:
                    self.log_result("Company Update", False, "Response contains MongoDB _id field", data)
                    return False
                
                # Verify updated fields
                success = True
                for key, value in update_data.items():
                    if data.get(key) != value:
                        success = False
                        break
                
                if success:
                    self.log_result("Company Update", True, "Company updated successfully")
                    return True
                else:
                    self.log_result("Company Update", False, "Updated data doesn't match request", data)
                    return False
            else:
                self.log_result("Company Update", False, f"Update failed with status {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_result("Company Update", False, f"Error testing company update: {str(e)}")
            return False
    
    def test_company_update_invalid_id(self):
        """Test company update with invalid ID"""
        try:
            update_data = {"name": "Test Update"}
            response = self.session.put(f"{BASE_URL}/companies/invalid-id", json=update_data)
            
            if response.status_code == 404:
                self.log_result("Company Update Invalid ID", True, "Correctly returned 404 for invalid ID")
                return True
            else:
                self.log_result("Company Update Invalid ID", False, f"Expected 404, got {response.status_code}")
                return False
        except Exception as e:
            self.log_result("Company Update Invalid ID", False, f"Error: {str(e)}")
            return False
    
    def test_business_unit_update(self):
        """Test business unit update endpoint"""
        if not self.test_bu_id:
            self.log_result("Business Unit Update", False, "No test business unit ID available")
            return False
        
        try:
            # Test valid update
            update_data = {
                "name": "Updated Test BU",
                "code": "BU-TEST-UPD",
                "description": "Updated test business unit",
                "manager_name": "John Manager"
            }
            
            response = self.session.put(f"{BASE_URL}/business-units/{self.test_bu_id}", json=update_data)
            
            if response.status_code == 200:
                data = response.json()
                # Check that _id field is not present
                if "_id" in data:
                    self.log_result("Business Unit Update", False, "Response contains MongoDB _id field", data)
                    return False
                
                # Verify updated fields
                success = True
                for key, value in update_data.items():
                    if data.get(key) != value:
                        success = False
                        break
                
                if success:
                    self.log_result("Business Unit Update", True, "Business unit updated successfully")
                    return True
                else:
                    self.log_result("Business Unit Update", False, "Updated data doesn't match request", data)
                    return False
            else:
                self.log_result("Business Unit Update", False, f"Update failed with status {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_result("Business Unit Update", False, f"Error testing business unit update: {str(e)}")
            return False
    
    def test_business_unit_update_invalid_id(self):
        """Test business unit update with invalid ID"""
        try:
            update_data = {"name": "Test Update"}
            response = self.session.put(f"{BASE_URL}/business-units/invalid-id", json=update_data)
            
            if response.status_code == 404:
                self.log_result("Business Unit Update Invalid ID", True, "Correctly returned 404 for invalid ID")
                return True
            else:
                self.log_result("Business Unit Update Invalid ID", False, f"Expected 404, got {response.status_code}")
                return False
        except Exception as e:
            self.log_result("Business Unit Update Invalid ID", False, f"Error: {str(e)}")
            return False
    
    def test_company_delete_with_subsidiaries(self):
        """Test company delete validation when company has subsidiaries"""
        try:
            # First create a parent company
            parent_data = {
                "name": "Parent Company for Delete Test",
                "industry": "restaurant"
            }
            response = self.session.post(f"{BASE_URL}/companies", json=parent_data)
            
            if response.status_code != 200:
                self.log_result("Company Delete with Subsidiaries", False, "Failed to create parent company for test")
                return False
            
            parent_company = response.json()
            parent_id = parent_company["id"]
            
            # Create a subsidiary
            subsidiary_data = {
                "name": "Subsidiary for Delete Test",
                "industry": "restaurant",
                "parent_company_id": parent_id
            }
            response = self.session.post(f"{BASE_URL}/companies", json=subsidiary_data)
            
            if response.status_code != 200:
                self.log_result("Company Delete with Subsidiaries", False, "Failed to create subsidiary for test")
                return False
            
            subsidiary_company = response.json()
            subsidiary_id = subsidiary_company["id"]
            
            # Try to delete parent company (should fail)
            response = self.session.delete(f"{BASE_URL}/companies/{parent_id}")
            
            if response.status_code == 400:
                # Clean up - delete subsidiary first, then parent
                self.session.delete(f"{BASE_URL}/companies/{subsidiary_id}")
                self.session.delete(f"{BASE_URL}/companies/{parent_id}")
                
                self.log_result("Company Delete with Subsidiaries", True, "Correctly prevented deletion of company with subsidiaries")
                return True
            else:
                # Clean up
                self.session.delete(f"{BASE_URL}/companies/{subsidiary_id}")
                self.session.delete(f"{BASE_URL}/companies/{parent_id}")
                
                self.log_result("Company Delete with Subsidiaries", False, f"Expected 400, got {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Company Delete with Subsidiaries", False, f"Error: {str(e)}")
            return False
    
    def test_company_delete_success(self):
        """Test successful company deletion"""
        try:
            # Create a company for deletion
            company_data = {
                "name": "Company for Delete Test",
                "industry": "retail"
            }
            response = self.session.post(f"{BASE_URL}/companies", json=company_data)
            
            if response.status_code != 200:
                self.log_result("Company Delete Success", False, "Failed to create company for delete test")
                return False
            
            company = response.json()
            company_id = company["id"]
            
            # Delete the company
            response = self.session.delete(f"{BASE_URL}/companies/{company_id}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success") == True:
                    self.log_result("Company Delete Success", True, "Company deleted successfully")
                    return True
                else:
                    self.log_result("Company Delete Success", False, "Delete response missing success flag", data)
                    return False
            else:
                self.log_result("Company Delete Success", False, f"Delete failed with status {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_result("Company Delete Success", False, f"Error: {str(e)}")
            return False
    
    def test_business_unit_delete_with_locations(self):
        """Test business unit delete validation when BU has locations"""
        try:
            # Get locations to check if any are associated with our test BU
            response = self.session.get(f"{BASE_URL}/locations")
            if response.status_code != 200:
                self.log_result("Business Unit Delete with Locations", False, "Failed to get locations")
                return False
            
            locations = response.json()
            bu_with_locations = None
            
            # Find a BU that has locations
            for location in locations:
                if location.get("business_unit_id"):
                    bu_with_locations = location["business_unit_id"]
                    break
            
            if not bu_with_locations:
                self.log_result("Business Unit Delete with Locations", True, "No business units with locations found - validation test skipped")
                return True
            
            # Try to delete BU with locations (should fail)
            response = self.session.delete(f"{BASE_URL}/business-units/{bu_with_locations}")
            
            if response.status_code == 400:
                self.log_result("Business Unit Delete with Locations", True, "Correctly prevented deletion of BU with locations")
                return True
            else:
                self.log_result("Business Unit Delete with Locations", False, f"Expected 400, got {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Business Unit Delete with Locations", False, f"Error: {str(e)}")
            return False
    
    def test_business_unit_delete_success(self):
        """Test successful business unit deletion"""
        try:
            # Create a business unit for deletion
            if not self.test_company_id:
                self.log_result("Business Unit Delete Success", False, "No company ID available for BU creation")
                return False
            
            bu_data = {
                "company_id": self.test_company_id,
                "name": "BU for Delete Test",
                "code": "BU-DEL-TEST"
            }
            response = self.session.post(f"{BASE_URL}/business-units", json=bu_data)
            
            if response.status_code != 200:
                self.log_result("Business Unit Delete Success", False, "Failed to create BU for delete test")
                return False
            
            bu = response.json()
            bu_id = bu["id"]
            
            # Delete the business unit
            response = self.session.delete(f"{BASE_URL}/business-units/{bu_id}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success") == True:
                    self.log_result("Business Unit Delete Success", True, "Business unit deleted successfully")
                    return True
                else:
                    self.log_result("Business Unit Delete Success", False, "Delete response missing success flag", data)
                    return False
            else:
                self.log_result("Business Unit Delete Success", False, f"Delete failed with status {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_result("Business Unit Delete Success", False, f"Error: {str(e)}")
            return False
    
    def test_unauthorized_access(self):
        """Test endpoints without authentication"""
        try:
            # Remove auth header temporarily
            original_headers = self.session.headers.copy()
            if "Authorization" in self.session.headers:
                del self.session.headers["Authorization"]
            
            # Test company update without auth
            response = self.session.put(f"{BASE_URL}/companies/test-id", json={"name": "test"})
            
            # Restore headers
            self.session.headers.update(original_headers)
            
            if response.status_code == 401:
                self.log_result("Unauthorized Access", True, "Correctly returned 401 for unauthorized request")
                return True
            else:
                self.log_result("Unauthorized Access", False, f"Expected 401, got {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Unauthorized Access", False, f"Error: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Run all backend tests"""
        print("🚀 Starting Backend API Tests for Company and Business Unit Edit/Delete")
        print("=" * 80)
        
        # Authentication
        if not self.login():
            print("❌ Authentication failed - cannot proceed with tests")
            return False
        
        # Get test data
        if not self.get_test_data():
            print("❌ Failed to get test data - cannot proceed with tests")
            return False
        
        # Run all tests
        tests = [
            self.test_company_update,
            self.test_company_update_invalid_id,
            self.test_business_unit_update,
            self.test_business_unit_update_invalid_id,
            self.test_company_delete_with_subsidiaries,
            self.test_company_delete_success,
            self.test_business_unit_delete_with_locations,
            self.test_business_unit_delete_success,
            self.test_unauthorized_access
        ]
        
        passed = 0
        total = len(tests)
        
        for test in tests:
            if test():
                passed += 1
        
        print("\n" + "=" * 80)
        print(f"📊 Test Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed!")
            return True
        else:
            print(f"⚠️  {total - passed} tests failed")
            return False
    
    def print_summary(self):
        """Print detailed test summary"""
        print("\n📋 Detailed Test Summary:")
        print("-" * 50)
        
        for result in self.results:
            status = "✅" if result["success"] else "❌"
            print(f"{status} {result['test']}: {result['message']}")
            if result.get("details") and not result["success"]:
                print(f"   Details: {result['details']}")

def main():
    tester = BackendTester()
    success = tester.run_all_tests()
    tester.print_summary()
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()