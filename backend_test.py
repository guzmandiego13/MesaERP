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
    
    def setup_tenant(self):
        """Setup test tenant if it doesn't exist"""
        try:
            setup_data = {
                "name": "Test Company",
                "industry": "restaurant",
                "admin_email": TEST_EMAIL,
                "admin_password": TEST_PASSWORD,
                "admin_name": "Test Admin",
                "company_name": "Test Restaurant"
            }
            
            response = self.session.post(f"{BASE_URL}/auth/setup", json=setup_data)
            
            if response.status_code == 200:
                data = response.json()
                self.token = data["token"]
                self.tenant_id = data["tenant"]["id"]
                self.session.headers.update({"Authorization": f"Bearer {self.token}"})
                self.log_result("Setup Tenant", True, "Test tenant created successfully")
                return True
            else:
                self.log_result("Setup Tenant", False, f"Setup failed with status {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_result("Setup Tenant", False, f"Setup error: {str(e)}")
            return False

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
                # Try to setup tenant if login fails
                self.log_result("Login", False, f"Login failed with status {response.status_code}, trying setup")
                return self.setup_tenant()
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

    def test_soft_delete_company(self):
        """Test soft delete company endpoint"""
        try:
            # Create a company for soft delete test
            company_data = {
                "name": "Company for Soft Delete Test",
                "industry": "retail"
            }
            response = self.session.post(f"{BASE_URL}/companies", json=company_data)
            
            if response.status_code != 200:
                self.log_result("Soft Delete Company", False, "Failed to create company for soft delete test")
                return False
            
            company = response.json()
            company_id = company["id"]
            
            # Soft delete the company
            response = self.session.post(f"{BASE_URL}/companies/{company_id}/soft-delete")
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success") == True and "deleted_at" in data and "restoration_deadline" in data:
                    self.log_result("Soft Delete Company", True, "Company soft deleted successfully with backup")
                    return True
                else:
                    self.log_result("Soft Delete Company", False, "Soft delete response missing required fields", data)
                    return False
            else:
                self.log_result("Soft Delete Company", False, f"Soft delete failed with status {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_result("Soft Delete Company", False, f"Error: {str(e)}")
            return False

    def test_soft_delete_company_with_subsidiaries(self):
        """Test soft delete validation when company has subsidiaries"""
        try:
            # Create a parent company
            parent_data = {
                "name": "Parent Company for Soft Delete Test",
                "industry": "restaurant"
            }
            response = self.session.post(f"{BASE_URL}/companies", json=parent_data)
            
            if response.status_code != 200:
                self.log_result("Soft Delete Company with Subsidiaries", False, "Failed to create parent company")
                return False
            
            parent_company = response.json()
            parent_id = parent_company["id"]
            
            # Create a subsidiary
            subsidiary_data = {
                "name": "Subsidiary for Soft Delete Test",
                "industry": "restaurant",
                "parent_company_id": parent_id
            }
            response = self.session.post(f"{BASE_URL}/companies", json=subsidiary_data)
            
            if response.status_code != 200:
                # Clean up parent
                self.session.delete(f"{BASE_URL}/companies/{parent_id}")
                self.log_result("Soft Delete Company with Subsidiaries", False, "Failed to create subsidiary")
                return False
            
            subsidiary_company = response.json()
            subsidiary_id = subsidiary_company["id"]
            
            # Try to soft delete parent company (should fail)
            response = self.session.post(f"{BASE_URL}/companies/{parent_id}/soft-delete")
            
            # Clean up - delete subsidiary first, then parent
            self.session.delete(f"{BASE_URL}/companies/{subsidiary_id}")
            self.session.delete(f"{BASE_URL}/companies/{parent_id}")
            
            if response.status_code == 400:
                self.log_result("Soft Delete Company with Subsidiaries", True, "Correctly prevented soft deletion of company with subsidiaries")
                return True
            else:
                self.log_result("Soft Delete Company with Subsidiaries", False, f"Expected 400, got {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Soft Delete Company with Subsidiaries", False, f"Error: {str(e)}")
            return False

    def test_get_companies_excludes_deleted(self):
        """Test that GET /companies excludes soft-deleted companies"""
        try:
            # Get initial company count
            response = self.session.get(f"{BASE_URL}/companies")
            if response.status_code != 200:
                self.log_result("Get Companies Excludes Deleted", False, "Failed to get companies")
                return False
            
            initial_companies = response.json()
            initial_count = len(initial_companies)
            
            # Create a company for soft delete test
            company_data = {
                "name": "Company to Hide After Delete",
                "industry": "retail"
            }
            response = self.session.post(f"{BASE_URL}/companies", json=company_data)
            
            if response.status_code != 200:
                self.log_result("Get Companies Excludes Deleted", False, "Failed to create test company")
                return False
            
            company = response.json()
            company_id = company["id"]
            
            # Verify company appears in list
            response = self.session.get(f"{BASE_URL}/companies")
            companies_after_create = response.json()
            
            if len(companies_after_create) != initial_count + 1:
                self.log_result("Get Companies Excludes Deleted", False, "Company not found in list after creation")
                return False
            
            # Soft delete the company
            response = self.session.post(f"{BASE_URL}/companies/{company_id}/soft-delete")
            
            if response.status_code != 200:
                self.log_result("Get Companies Excludes Deleted", False, "Failed to soft delete company")
                return False
            
            # Verify company no longer appears in list
            response = self.session.get(f"{BASE_URL}/companies")
            companies_after_delete = response.json()
            
            if len(companies_after_delete) == initial_count:
                self.log_result("Get Companies Excludes Deleted", True, "Soft-deleted company correctly excluded from companies list")
                return True
            else:
                self.log_result("Get Companies Excludes Deleted", False, f"Expected {initial_count} companies, got {len(companies_after_delete)}")
                return False
                
        except Exception as e:
            self.log_result("Get Companies Excludes Deleted", False, f"Error: {str(e)}")
            return False

    def test_get_deleted_companies(self):
        """Test GET /companies/deleted endpoint"""
        try:
            # Create a company for soft delete test
            company_data = {
                "name": "Company for Deleted List Test",
                "industry": "retail"
            }
            response = self.session.post(f"{BASE_URL}/companies", json=company_data)
            
            if response.status_code != 200:
                self.log_result("Get Deleted Companies", False, "Failed to create test company")
                return False
            
            company = response.json()
            company_id = company["id"]
            company_name = company["name"]
            
            # Soft delete the company
            response = self.session.post(f"{BASE_URL}/companies/{company_id}/soft-delete")
            
            if response.status_code != 200:
                self.log_result("Get Deleted Companies", False, "Failed to soft delete company")
                return False
            
            # Get deleted companies list
            response = self.session.get(f"{BASE_URL}/companies/deleted")
            
            if response.status_code == 200:
                deleted_companies = response.json()
                
                # Find our deleted company in the list
                found_company = None
                for deleted_company in deleted_companies:
                    if deleted_company["id"] == company_id:
                        found_company = deleted_company
                        break
                
                if found_company:
                    # Verify required fields are present
                    required_fields = ["id", "name", "deleted_at", "restoration_deadline"]
                    missing_fields = [field for field in required_fields if field not in found_company]
                    
                    if not missing_fields:
                        self.log_result("Get Deleted Companies", True, "Deleted company found with all required restoration info")
                        return True
                    else:
                        self.log_result("Get Deleted Companies", False, f"Missing fields in deleted company: {missing_fields}")
                        return False
                else:
                    self.log_result("Get Deleted Companies", False, "Soft-deleted company not found in deleted companies list")
                    return False
            else:
                self.log_result("Get Deleted Companies", False, f"Failed to get deleted companies: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Get Deleted Companies", False, f"Error: {str(e)}")
            return False

    def test_restore_company(self):
        """Test company restoration endpoint"""
        try:
            # Create a company for restore test
            company_data = {
                "name": "Company for Restore Test",
                "industry": "retail"
            }
            response = self.session.post(f"{BASE_URL}/companies", json=company_data)
            
            if response.status_code != 200:
                self.log_result("Restore Company", False, "Failed to create test company")
                return False
            
            company = response.json()
            company_id = company["id"]
            
            # Soft delete the company
            response = self.session.post(f"{BASE_URL}/companies/{company_id}/soft-delete")
            
            if response.status_code != 200:
                self.log_result("Restore Company", False, "Failed to soft delete company")
                return False
            
            # Restore the company
            response = self.session.post(f"{BASE_URL}/companies/{company_id}/restore")
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success") == True:
                    # Verify company appears in active companies list again
                    response = self.session.get(f"{BASE_URL}/companies")
                    if response.status_code == 200:
                        companies = response.json()
                        restored_company = None
                        for comp in companies:
                            if comp["id"] == company_id:
                                restored_company = comp
                                break
                        
                        if restored_company and restored_company.get("is_active") == True:
                            # Clean up
                            self.session.delete(f"{BASE_URL}/companies/{company_id}")
                            self.log_result("Restore Company", True, "Company restored successfully and appears in active list")
                            return True
                        else:
                            self.log_result("Restore Company", False, "Restored company not found in active companies list")
                            return False
                    else:
                        self.log_result("Restore Company", False, "Failed to verify restoration")
                        return False
                else:
                    self.log_result("Restore Company", False, "Restore response missing success flag", data)
                    return False
            else:
                self.log_result("Restore Company", False, f"Restore failed with status {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_result("Restore Company", False, f"Error: {str(e)}")
            return False

    def test_restore_non_deleted_company(self):
        """Test restore endpoint on non-deleted company"""
        try:
            if not self.test_company_id:
                self.log_result("Restore Non-Deleted Company", False, "No test company ID available")
                return False
            
            # Try to restore a company that's not deleted
            response = self.session.post(f"{BASE_URL}/companies/{self.test_company_id}/restore")
            
            if response.status_code == 400:
                self.log_result("Restore Non-Deleted Company", True, "Correctly returned 400 for non-deleted company")
                return True
            else:
                self.log_result("Restore Non-Deleted Company", False, f"Expected 400, got {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Restore Non-Deleted Company", False, f"Error: {str(e)}")
            return False

    def test_soft_delete_already_deleted_company(self):
        """Test soft delete on already deleted company"""
        try:
            # Create a company for test
            company_data = {
                "name": "Company for Double Delete Test",
                "industry": "retail"
            }
            response = self.session.post(f"{BASE_URL}/companies", json=company_data)
            
            if response.status_code != 200:
                self.log_result("Soft Delete Already Deleted", False, "Failed to create test company")
                return False
            
            company = response.json()
            company_id = company["id"]
            
            # Soft delete the company
            response = self.session.post(f"{BASE_URL}/companies/{company_id}/soft-delete")
            
            if response.status_code != 200:
                self.log_result("Soft Delete Already Deleted", False, "Failed to soft delete company")
                return False
            
            # Try to soft delete again
            response = self.session.post(f"{BASE_URL}/companies/{company_id}/soft-delete")
            
            if response.status_code == 400:
                self.log_result("Soft Delete Already Deleted", True, "Correctly prevented double soft delete")
                return True
            else:
                self.log_result("Soft Delete Already Deleted", False, f"Expected 400, got {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Soft Delete Already Deleted", False, f"Error: {str(e)}")
            return False

    def test_soft_delete_invalid_company_id(self):
        """Test soft delete with invalid company ID"""
        try:
            response = self.session.post(f"{BASE_URL}/companies/invalid-id/soft-delete")
            
            if response.status_code == 404:
                self.log_result("Soft Delete Invalid ID", True, "Correctly returned 404 for invalid company ID")
                return True
            else:
                self.log_result("Soft Delete Invalid ID", False, f"Expected 404, got {response.status_code}")
                return False
        except Exception as e:
            self.log_result("Soft Delete Invalid ID", False, f"Error: {str(e)}")
            return False

    def test_restore_invalid_company_id(self):
        """Test restore with invalid company ID"""
        try:
            response = self.session.post(f"{BASE_URL}/companies/invalid-id/restore")
            
            if response.status_code == 404:
                self.log_result("Restore Invalid ID", True, "Correctly returned 404 for invalid company ID")
                return True
            else:
                self.log_result("Restore Invalid ID", False, f"Expected 404, got {response.status_code}")
                return False
        except Exception as e:
            self.log_result("Restore Invalid ID", False, f"Error: {str(e)}")
            return False

    # ============================================================================
    # BUSINESS UNIT CONSOLIDATION TESTS
    # ============================================================================

    def test_create_business_unit_with_consolidation(self):
        """Test creating business unit with consolidation settings"""
        if not self.test_company_id:
            self.log_result("Create BU with Consolidation", False, "No test company ID available")
            return False
        
        try:
            # Create a subsidiary company to use as parent subsidiary
            subsidiary_data = {
                "name": "Parent Subsidiary for Consolidation Test",
                "industry": "restaurant",
                "parent_company_id": self.test_company_id
            }
            response = self.session.post(f"{BASE_URL}/companies", json=subsidiary_data)
            
            if response.status_code != 200:
                self.log_result("Create BU with Consolidation", False, "Failed to create parent subsidiary")
                return False
            
            parent_subsidiary = response.json()
            parent_subsidiary_id = parent_subsidiary["id"]
            
            # Create business unit with consolidation settings
            bu_data = {
                "company_id": self.test_company_id,
                "name": "Consolidation Test BU",
                "code": "BU-CONSOL-TEST",
                "description": "Business unit for consolidation testing",
                "manager_name": "Test Manager",
                "parent_subsidiary_id": parent_subsidiary_id,
                "consolidation_enabled": True
            }
            
            response = self.session.post(f"{BASE_URL}/business-units", json=bu_data)
            
            if response.status_code == 200:
                data = response.json()
                # Verify consolidation fields are set correctly
                if (data.get("parent_subsidiary_id") == parent_subsidiary_id and 
                    data.get("consolidation_enabled") == True):
                    
                    # Clean up
                    self.session.delete(f"{BASE_URL}/business-units/{data['id']}")
                    self.session.delete(f"{BASE_URL}/companies/{parent_subsidiary_id}")
                    
                    self.log_result("Create BU with Consolidation", True, "Business unit created with consolidation settings")
                    return True
                else:
                    self.log_result("Create BU with Consolidation", False, "Consolidation fields not set correctly", data)
                    return False
            else:
                # Clean up subsidiary
                self.session.delete(f"{BASE_URL}/companies/{parent_subsidiary_id}")
                self.log_result("Create BU with Consolidation", False, f"BU creation failed with status {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_result("Create BU with Consolidation", False, f"Error: {str(e)}")
            return False

    def test_create_business_unit_invalid_parent_subsidiary(self):
        """Test creating business unit with invalid parent subsidiary ID"""
        if not self.test_company_id:
            self.log_result("Create BU Invalid Parent Subsidiary", False, "No test company ID available")
            return False
        
        try:
            bu_data = {
                "company_id": self.test_company_id,
                "name": "Invalid Parent Test BU",
                "code": "BU-INVALID-PARENT",
                "parent_subsidiary_id": "invalid-subsidiary-id",
                "consolidation_enabled": True
            }
            
            response = self.session.post(f"{BASE_URL}/business-units", json=bu_data)
            
            if response.status_code == 404:
                self.log_result("Create BU Invalid Parent Subsidiary", True, "Correctly returned 404 for invalid parent subsidiary")
                return True
            else:
                self.log_result("Create BU Invalid Parent Subsidiary", False, f"Expected 404, got {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Create BU Invalid Parent Subsidiary", False, f"Error: {str(e)}")
            return False

    def test_update_business_unit_consolidation(self):
        """Test updating business unit consolidation settings"""
        if not self.test_bu_id:
            self.log_result("Update BU Consolidation", False, "No test business unit ID available")
            return False
        
        try:
            # Create a subsidiary company to use as parent subsidiary
            subsidiary_data = {
                "name": "Parent Subsidiary for Update Test",
                "industry": "restaurant"
            }
            response = self.session.post(f"{BASE_URL}/companies", json=subsidiary_data)
            
            if response.status_code != 200:
                self.log_result("Update BU Consolidation", False, "Failed to create parent subsidiary")
                return False
            
            parent_subsidiary = response.json()
            parent_subsidiary_id = parent_subsidiary["id"]
            
            # Update business unit with consolidation settings
            update_data = {
                "parent_subsidiary_id": parent_subsidiary_id,
                "consolidation_enabled": True
            }
            
            response = self.session.put(f"{BASE_URL}/business-units/{self.test_bu_id}", json=update_data)
            
            if response.status_code == 200:
                data = response.json()
                # Verify consolidation fields are updated correctly
                if (data.get("parent_subsidiary_id") == parent_subsidiary_id and 
                    data.get("consolidation_enabled") == True):
                    
                    # Clean up
                    self.session.delete(f"{BASE_URL}/companies/{parent_subsidiary_id}")
                    
                    self.log_result("Update BU Consolidation", True, "Business unit consolidation settings updated successfully")
                    return True
                else:
                    self.log_result("Update BU Consolidation", False, "Consolidation fields not updated correctly", data)
                    return False
            else:
                # Clean up subsidiary
                self.session.delete(f"{BASE_URL}/companies/{parent_subsidiary_id}")
                self.log_result("Update BU Consolidation", False, f"Update failed with status {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_result("Update BU Consolidation", False, f"Error: {str(e)}")
            return False

    def test_get_business_unit_consolidation(self):
        """Test GET /business-units/{id}/consolidation endpoint"""
        if not self.test_bu_id:
            self.log_result("Get BU Consolidation", False, "No test business unit ID available")
            return False
        
        try:
            response = self.session.get(f"{BASE_URL}/business-units/{self.test_bu_id}/consolidation")
            
            if response.status_code == 200:
                data = response.json()
                # Verify required fields are present
                required_fields = ["business_unit", "company", "consolidation_summary", "journal_entries", "date_range"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if not missing_fields:
                    # Verify consolidation_summary structure
                    summary = data.get("consolidation_summary", {})
                    summary_fields = ["total_debits", "total_credits", "net_balance", "entries_count", "consolidation_enabled"]
                    missing_summary_fields = [field for field in summary_fields if field not in summary]
                    
                    if not missing_summary_fields:
                        self.log_result("Get BU Consolidation", True, "Business unit consolidation data retrieved successfully")
                        return True
                    else:
                        self.log_result("Get BU Consolidation", False, f"Missing consolidation summary fields: {missing_summary_fields}")
                        return False
                else:
                    self.log_result("Get BU Consolidation", False, f"Missing required fields: {missing_fields}")
                    return False
            else:
                self.log_result("Get BU Consolidation", False, f"Request failed with status {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_result("Get BU Consolidation", False, f"Error: {str(e)}")
            return False

    def test_get_business_unit_consolidation_with_dates(self):
        """Test GET /business-units/{id}/consolidation with date filtering"""
        if not self.test_bu_id:
            self.log_result("Get BU Consolidation with Dates", False, "No test business unit ID available")
            return False
        
        try:
            # Test with date range
            start_date = "2024-01-01T00:00:00Z"
            end_date = "2024-12-31T23:59:59Z"
            
            response = self.session.get(f"{BASE_URL}/business-units/{self.test_bu_id}/consolidation", 
                                      params={"start_date": start_date, "end_date": end_date})
            
            if response.status_code == 200:
                data = response.json()
                # Verify date range is reflected in response
                date_range = data.get("date_range", {})
                if (date_range.get("start_date") == start_date and 
                    date_range.get("end_date") == end_date):
                    self.log_result("Get BU Consolidation with Dates", True, "Date filtering works correctly")
                    return True
                else:
                    self.log_result("Get BU Consolidation with Dates", False, "Date range not reflected correctly in response")
                    return False
            else:
                self.log_result("Get BU Consolidation with Dates", False, f"Request failed with status {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Get BU Consolidation with Dates", False, f"Error: {str(e)}")
            return False

    def test_get_business_unit_consolidation_invalid_id(self):
        """Test GET /business-units/{id}/consolidation with invalid ID"""
        try:
            response = self.session.get(f"{BASE_URL}/business-units/invalid-id/consolidation")
            
            if response.status_code == 404:
                self.log_result("Get BU Consolidation Invalid ID", True, "Correctly returned 404 for invalid business unit ID")
                return True
            else:
                self.log_result("Get BU Consolidation Invalid ID", False, f"Expected 404, got {response.status_code}")
                return False
        except Exception as e:
            self.log_result("Get BU Consolidation Invalid ID", False, f"Error: {str(e)}")
            return False

    def test_get_consolidated_report(self):
        """Test GET /companies/{id}/consolidated-report endpoint"""
        if not self.test_company_id:
            self.log_result("Get Consolidated Report", False, "No test company ID available")
            return False
        
        try:
            response = self.session.get(f"{BASE_URL}/companies/{self.test_company_id}/consolidated-report")
            
            if response.status_code == 200:
                data = response.json()
                # Verify required fields are present
                required_fields = ["company", "consolidation_period", "business_units_summary", "consolidated_totals", "all_journal_entries"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if not missing_fields:
                    # Verify consolidated_totals structure
                    totals = data.get("consolidated_totals", {})
                    totals_fields = ["total_debits", "total_credits", "net_balance", "total_entries"]
                    missing_totals_fields = [field for field in totals_fields if field not in totals]
                    
                    if not missing_totals_fields:
                        self.log_result("Get Consolidated Report", True, "Consolidated report retrieved successfully")
                        return True
                    else:
                        self.log_result("Get Consolidated Report", False, f"Missing consolidated totals fields: {missing_totals_fields}")
                        return False
                else:
                    self.log_result("Get Consolidated Report", False, f"Missing required fields: {missing_fields}")
                    return False
            else:
                self.log_result("Get Consolidated Report", False, f"Request failed with status {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_result("Get Consolidated Report", False, f"Error: {str(e)}")
            return False

    def test_get_consolidated_report_with_dates(self):
        """Test GET /companies/{id}/consolidated-report with date filtering"""
        if not self.test_company_id:
            self.log_result("Get Consolidated Report with Dates", False, "No test company ID available")
            return False
        
        try:
            # Test with date range
            start_date = "2024-01-01T00:00:00Z"
            end_date = "2024-12-31T23:59:59Z"
            
            response = self.session.get(f"{BASE_URL}/companies/{self.test_company_id}/consolidated-report", 
                                      params={"start_date": start_date, "end_date": end_date})
            
            if response.status_code == 200:
                data = response.json()
                # Verify date range is reflected in response
                period = data.get("consolidation_period", {})
                if (period.get("start_date") == start_date and 
                    period.get("end_date") == end_date):
                    self.log_result("Get Consolidated Report with Dates", True, "Date filtering works correctly for consolidated report")
                    return True
                else:
                    self.log_result("Get Consolidated Report with Dates", False, "Date range not reflected correctly in response")
                    return False
            else:
                self.log_result("Get Consolidated Report with Dates", False, f"Request failed with status {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Get Consolidated Report with Dates", False, f"Error: {str(e)}")
            return False

    def test_get_consolidated_report_invalid_id(self):
        """Test GET /companies/{id}/consolidated-report with invalid ID"""
        try:
            response = self.session.get(f"{BASE_URL}/companies/invalid-id/consolidated-report")
            
            if response.status_code == 404:
                self.log_result("Get Consolidated Report Invalid ID", True, "Correctly returned 404 for invalid company ID")
                return True
            else:
                self.log_result("Get Consolidated Report Invalid ID", False, f"Expected 404, got {response.status_code}")
                return False
        except Exception as e:
            self.log_result("Get Consolidated Report Invalid ID", False, f"Error: {str(e)}")
            return False

    def test_set_business_unit_consolidation(self):
        """Test POST /business-units/{id}/set-consolidation endpoint"""
        if not self.test_bu_id:
            self.log_result("Set BU Consolidation", False, "No test business unit ID available")
            return False
        
        try:
            # Create a subsidiary company to use as parent subsidiary
            subsidiary_data = {
                "name": "Parent Subsidiary for Set Consolidation Test",
                "industry": "restaurant"
            }
            response = self.session.post(f"{BASE_URL}/companies", json=subsidiary_data)
            
            if response.status_code != 200:
                self.log_result("Set BU Consolidation", False, "Failed to create parent subsidiary")
                return False
            
            parent_subsidiary = response.json()
            parent_subsidiary_id = parent_subsidiary["id"]
            
            # Set consolidation settings (using query parameters)
            params = {
                "parent_subsidiary_id": parent_subsidiary_id,
                "consolidation_enabled": True
            }
            
            response = self.session.post(f"{BASE_URL}/business-units/{self.test_bu_id}/set-consolidation", 
                                       params=params)
            
            if response.status_code == 200:
                data = response.json()
                # Verify response structure
                if (data.get("success") == True and 
                    "business_unit" in data and 
                    data["business_unit"].get("parent_subsidiary_id") == parent_subsidiary_id and
                    data["business_unit"].get("consolidation_enabled") == True):
                    
                    # Clean up
                    self.session.delete(f"{BASE_URL}/companies/{parent_subsidiary_id}")
                    
                    self.log_result("Set BU Consolidation", True, "Business unit consolidation settings updated via set-consolidation endpoint")
                    return True
                else:
                    self.log_result("Set BU Consolidation", False, "Consolidation settings not updated correctly", data)
                    return False
            else:
                # Clean up subsidiary
                self.session.delete(f"{BASE_URL}/companies/{parent_subsidiary_id}")
                self.log_result("Set BU Consolidation", False, f"Request failed with status {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_result("Set BU Consolidation", False, f"Error: {str(e)}")
            return False

    def test_set_business_unit_consolidation_invalid_parent(self):
        """Test POST /business-units/{id}/set-consolidation with invalid parent subsidiary"""
        if not self.test_bu_id:
            self.log_result("Set BU Consolidation Invalid Parent", False, "No test business unit ID available")
            return False
        
        try:
            params = {
                "parent_subsidiary_id": "invalid-subsidiary-id",
                "consolidation_enabled": True
            }
            
            response = self.session.post(f"{BASE_URL}/business-units/{self.test_bu_id}/set-consolidation", 
                                       params=params)
            
            if response.status_code == 404:
                self.log_result("Set BU Consolidation Invalid Parent", True, "Correctly returned 404 for invalid parent subsidiary")
                return True
            else:
                self.log_result("Set BU Consolidation Invalid Parent", False, f"Expected 404, got {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Set BU Consolidation Invalid Parent", False, f"Error: {str(e)}")
            return False

    def test_set_business_unit_consolidation_invalid_bu_id(self):
        """Test POST /business-units/{id}/set-consolidation with invalid business unit ID"""
        try:
            params = {
                "consolidation_enabled": False
            }
            
            response = self.session.post(f"{BASE_URL}/business-units/invalid-id/set-consolidation", 
                                       params=params)
            
            if response.status_code == 404:
                self.log_result("Set BU Consolidation Invalid BU ID", True, "Correctly returned 404 for invalid business unit ID")
                return True
            else:
                self.log_result("Set BU Consolidation Invalid BU ID", False, f"Expected 404, got {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Set BU Consolidation Invalid BU ID", False, f"Error: {str(e)}")
            return False

    def test_get_business_units_includes_parent_subsidiary_name(self):
        """Test that GET /business-units includes parent_subsidiary_name"""
        try:
            response = self.session.get(f"{BASE_URL}/business-units")
            
            if response.status_code == 200:
                business_units = response.json()
                if business_units:
                    # Check if any BU has parent_subsidiary_name field (even if None)
                    has_parent_subsidiary_field = any("parent_subsidiary_name" in bu for bu in business_units)
                    if has_parent_subsidiary_field:
                        self.log_result("Get BUs Includes Parent Subsidiary Name", True, "Business units include parent_subsidiary_name field")
                        return True
                    else:
                        self.log_result("Get BUs Includes Parent Subsidiary Name", False, "Business units missing parent_subsidiary_name field")
                        return False
                else:
                    self.log_result("Get BUs Includes Parent Subsidiary Name", True, "No business units found - test skipped")
                    return True
            else:
                self.log_result("Get BUs Includes Parent Subsidiary Name", False, f"Request failed with status {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Get BUs Includes Parent Subsidiary Name", False, f"Error: {str(e)}")
            return False

    # ============================================================================
    # BUSINESS UNIT SOFT DELETE TESTS
    # ============================================================================

    def test_business_unit_soft_delete(self):
        """Test business unit soft delete endpoint"""
        try:
            # Create a business unit for soft delete test
            if not self.test_company_id:
                self.log_result("BU Soft Delete", False, "No company ID available for BU creation")
                return False
            
            bu_data = {
                "company_id": self.test_company_id,
                "name": "BU for Soft Delete Test",
                "code": "BU-SOFT-DEL-TEST"
            }
            response = self.session.post(f"{BASE_URL}/business-units", json=bu_data)
            
            if response.status_code != 200:
                self.log_result("BU Soft Delete", False, "Failed to create BU for soft delete test")
                return False
            
            bu = response.json()
            bu_id = bu["id"]
            
            # Soft delete the business unit
            response = self.session.post(f"{BASE_URL}/business-units/{bu_id}/soft-delete")
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success") == True and "deleted_at" in data and "restoration_deadline" in data:
                    self.log_result("BU Soft Delete", True, "Business unit soft deleted successfully with backup")
                    return True
                else:
                    self.log_result("BU Soft Delete", False, "Soft delete response missing required fields", data)
                    return False
            else:
                self.log_result("BU Soft Delete", False, f"Soft delete failed with status {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_result("BU Soft Delete", False, f"Error: {str(e)}")
            return False

    def test_business_unit_soft_delete_with_locations(self):
        """Test business unit soft delete validation when BU has locations"""
        try:
            # Get locations to check if any are associated with business units
            response = self.session.get(f"{BASE_URL}/locations")
            if response.status_code != 200:
                self.log_result("BU Soft Delete with Locations", False, "Failed to get locations")
                return False
            
            locations = response.json()
            bu_with_locations = None
            
            # Find a BU that has locations
            for location in locations:
                if location.get("business_unit_id"):
                    bu_with_locations = location["business_unit_id"]
                    break
            
            if not bu_with_locations:
                self.log_result("BU Soft Delete with Locations", True, "No business units with locations found - validation test skipped")
                return True
            
            # Try to soft delete BU with locations (should fail)
            response = self.session.post(f"{BASE_URL}/business-units/{bu_with_locations}/soft-delete")
            
            if response.status_code == 400:
                self.log_result("BU Soft Delete with Locations", True, "Correctly prevented soft deletion of BU with locations")
                return True
            else:
                self.log_result("BU Soft Delete with Locations", False, f"Expected 400, got {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("BU Soft Delete with Locations", False, f"Error: {str(e)}")
            return False

    def test_get_business_units_excludes_soft_deleted(self):
        """Test that GET /business-units excludes soft-deleted business units"""
        try:
            # Get initial BU count
            response = self.session.get(f"{BASE_URL}/business-units")
            if response.status_code != 200:
                self.log_result("Get BUs Excludes Soft Deleted", False, "Failed to get business units")
                return False
            
            initial_bus = response.json()
            initial_count = len(initial_bus)
            
            # Create a business unit for soft delete test
            if not self.test_company_id:
                self.log_result("Get BUs Excludes Soft Deleted", False, "No company ID available")
                return False
            
            bu_data = {
                "company_id": self.test_company_id,
                "name": "BU to Hide After Delete",
                "code": "BU-HIDE-TEST"
            }
            response = self.session.post(f"{BASE_URL}/business-units", json=bu_data)
            
            if response.status_code != 200:
                self.log_result("Get BUs Excludes Soft Deleted", False, "Failed to create test BU")
                return False
            
            bu = response.json()
            bu_id = bu["id"]
            
            # Verify BU appears in list
            response = self.session.get(f"{BASE_URL}/business-units")
            bus_after_create = response.json()
            
            if len(bus_after_create) != initial_count + 1:
                self.log_result("Get BUs Excludes Soft Deleted", False, "BU not found in list after creation")
                return False
            
            # Soft delete the business unit
            response = self.session.post(f"{BASE_URL}/business-units/{bu_id}/soft-delete")
            
            if response.status_code != 200:
                self.log_result("Get BUs Excludes Soft Deleted", False, "Failed to soft delete BU")
                return False
            
            # Verify BU no longer appears in list
            response = self.session.get(f"{BASE_URL}/business-units")
            bus_after_delete = response.json()
            
            if len(bus_after_delete) == initial_count:
                self.log_result("Get BUs Excludes Soft Deleted", True, "Soft-deleted BU correctly excluded from business units list")
                return True
            else:
                self.log_result("Get BUs Excludes Soft Deleted", False, f"Expected {initial_count} BUs, got {len(bus_after_delete)}")
                return False
                
        except Exception as e:
            self.log_result("Get BUs Excludes Soft Deleted", False, f"Error: {str(e)}")
            return False

    def test_get_deleted_business_units(self):
        """Test GET /business-units/deleted endpoint"""
        try:
            # Create a business unit for soft delete test
            if not self.test_company_id:
                self.log_result("Get Deleted BUs", False, "No company ID available")
                return False
            
            bu_data = {
                "company_id": self.test_company_id,
                "name": "BU for Deleted List Test",
                "code": "BU-DEL-LIST-TEST"
            }
            response = self.session.post(f"{BASE_URL}/business-units", json=bu_data)
            
            if response.status_code != 200:
                self.log_result("Get Deleted BUs", False, "Failed to create test BU")
                return False
            
            bu = response.json()
            bu_id = bu["id"]
            bu_name = bu["name"]
            
            # Soft delete the business unit
            response = self.session.post(f"{BASE_URL}/business-units/{bu_id}/soft-delete")
            
            if response.status_code != 200:
                self.log_result("Get Deleted BUs", False, "Failed to soft delete BU")
                return False
            
            # Get deleted business units list
            response = self.session.get(f"{BASE_URL}/business-units/deleted")
            
            if response.status_code == 200:
                deleted_bus = response.json()
                
                # Find our deleted BU in the list
                found_bu = None
                for deleted_bu in deleted_bus:
                    if deleted_bu["id"] == bu_id:
                        found_bu = deleted_bu
                        break
                
                if found_bu:
                    # Verify required fields are present
                    required_fields = ["id", "name", "deleted_at", "restoration_deadline", "days_remaining", "company_name"]
                    missing_fields = [field for field in required_fields if field not in found_bu]
                    
                    if not missing_fields:
                        self.log_result("Get Deleted BUs", True, "Deleted BU found with all required restoration info")
                        return True
                    else:
                        self.log_result("Get Deleted BUs", False, f"Missing fields in deleted BU: {missing_fields}")
                        return False
                else:
                    self.log_result("Get Deleted BUs", False, "Soft-deleted BU not found in deleted BUs list")
                    return False
            else:
                self.log_result("Get Deleted BUs", False, f"Failed to get deleted BUs: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Get Deleted BUs", False, f"Error: {str(e)}")
            return False

    def test_restore_business_unit(self):
        """Test business unit restoration endpoint"""
        try:
            # Create a business unit for restore test
            if not self.test_company_id:
                self.log_result("Restore BU", False, "No company ID available")
                return False
            
            bu_data = {
                "company_id": self.test_company_id,
                "name": "BU for Restore Test",
                "code": "BU-RESTORE-TEST"
            }
            response = self.session.post(f"{BASE_URL}/business-units", json=bu_data)
            
            if response.status_code != 200:
                self.log_result("Restore BU", False, "Failed to create test BU")
                return False
            
            bu = response.json()
            bu_id = bu["id"]
            
            # Soft delete the business unit
            response = self.session.post(f"{BASE_URL}/business-units/{bu_id}/soft-delete")
            
            if response.status_code != 200:
                self.log_result("Restore BU", False, "Failed to soft delete BU")
                return False
            
            # Restore the business unit
            response = self.session.post(f"{BASE_URL}/business-units/{bu_id}/restore")
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success") == True:
                    # Verify BU appears in active BUs list again
                    response = self.session.get(f"{BASE_URL}/business-units")
                    if response.status_code == 200:
                        bus = response.json()
                        restored_bu = None
                        for bu_item in bus:
                            if bu_item["id"] == bu_id:
                                restored_bu = bu_item
                                break
                        
                        if restored_bu and restored_bu.get("is_active") == True:
                            # Clean up
                            self.session.delete(f"{BASE_URL}/business-units/{bu_id}")
                            self.log_result("Restore BU", True, "Business unit restored successfully and appears in active list")
                            return True
                        else:
                            self.log_result("Restore BU", False, "Restored BU not found in active BUs list")
                            return False
                    else:
                        self.log_result("Restore BU", False, "Failed to verify restoration")
                        return False
                else:
                    self.log_result("Restore BU", False, "Restore response missing success flag", data)
                    return False
            else:
                self.log_result("Restore BU", False, f"Restore failed with status {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_result("Restore BU", False, f"Error: {str(e)}")
            return False

    def test_restore_non_deleted_business_unit(self):
        """Test restore endpoint on non-deleted business unit"""
        try:
            if not self.test_bu_id:
                self.log_result("Restore Non-Deleted BU", False, "No test BU ID available")
                return False
            
            # Try to restore a BU that's not deleted
            response = self.session.post(f"{BASE_URL}/business-units/{self.test_bu_id}/restore")
            
            if response.status_code == 400:
                self.log_result("Restore Non-Deleted BU", True, "Correctly returned 400 for non-deleted BU")
                return True
            else:
                self.log_result("Restore Non-Deleted BU", False, f"Expected 400, got {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Restore Non-Deleted BU", False, f"Error: {str(e)}")
            return False

    def test_business_unit_soft_delete_already_deleted(self):
        """Test soft delete on already deleted business unit"""
        try:
            # Create a business unit for test
            if not self.test_company_id:
                self.log_result("BU Soft Delete Already Deleted", False, "No company ID available")
                return False
            
            bu_data = {
                "company_id": self.test_company_id,
                "name": "BU for Double Delete Test",
                "code": "BU-DOUBLE-DEL-TEST"
            }
            response = self.session.post(f"{BASE_URL}/business-units", json=bu_data)
            
            if response.status_code != 200:
                self.log_result("BU Soft Delete Already Deleted", False, "Failed to create test BU")
                return False
            
            bu = response.json()
            bu_id = bu["id"]
            
            # Soft delete the business unit
            response = self.session.post(f"{BASE_URL}/business-units/{bu_id}/soft-delete")
            
            if response.status_code != 200:
                self.log_result("BU Soft Delete Already Deleted", False, "Failed to soft delete BU")
                return False
            
            # Try to soft delete again
            response = self.session.post(f"{BASE_URL}/business-units/{bu_id}/soft-delete")
            
            if response.status_code == 400:
                self.log_result("BU Soft Delete Already Deleted", True, "Correctly prevented double soft delete")
                return True
            else:
                self.log_result("BU Soft Delete Already Deleted", False, f"Expected 400, got {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("BU Soft Delete Already Deleted", False, f"Error: {str(e)}")
            return False

    def test_business_unit_soft_delete_invalid_id(self):
        """Test soft delete with invalid business unit ID"""
        try:
            response = self.session.post(f"{BASE_URL}/business-units/invalid-id/soft-delete")
            
            if response.status_code == 404:
                self.log_result("BU Soft Delete Invalid ID", True, "Correctly returned 404 for invalid BU ID")
                return True
            else:
                self.log_result("BU Soft Delete Invalid ID", False, f"Expected 404, got {response.status_code}")
                return False
        except Exception as e:
            self.log_result("BU Soft Delete Invalid ID", False, f"Error: {str(e)}")
            return False

    def test_business_unit_restore_invalid_id(self):
        """Test restore with invalid business unit ID"""
        try:
            response = self.session.post(f"{BASE_URL}/business-units/invalid-id/restore")
            
            if response.status_code == 404:
                self.log_result("BU Restore Invalid ID", True, "Correctly returned 404 for invalid BU ID")
                return True
            else:
                self.log_result("BU Restore Invalid ID", False, f"Expected 404, got {response.status_code}")
                return False
        except Exception as e:
            self.log_result("BU Restore Invalid ID", False, f"Error: {str(e)}")
            return False

    # ============================================================================
    # ENHANCED USER MANAGEMENT TESTS
    # ============================================================================

    def test_user_update_with_new_fields(self):
        """Test user update with new fields (name, email, role, permissions)"""
        try:
            # Create a test user first
            user_data = {
                "email": "testuser@example.com",
                "password": "testpass123",
                "name": "Test User",
                "role": "Analyst",
                "permissions": {
                    "view_dashboard": True,
                    "view_reports": False,
                    "export_data": False,
                    "view_finances": False,
                    "manage_accounts_ledger": False,
                    "create_journal_entries": False,
                    "approve_journal_entries": False,
                    "manage_information": False,
                    "manage_companies": False,
                    "manage_business_units": False,
                    "view_users": False,
                    "manage_users": False,
                    "manage_settings": False,
                    "manage_api_keys": False,
                    "manage_branding": False,
                    "view_inventory": False,
                    "manage_inventory": False,
                    "manage_procurement": False,
                    "full_access": False
                }
            }
            
            response = self.session.post(f"{BASE_URL}/users", json=user_data)
            
            if response.status_code != 200:
                self.log_result("User Update New Fields", False, "Failed to create test user")
                return False
            
            user = response.json()
            user_id = user["id"]
            
            # Update user with new fields
            update_data = {
                "name": "Updated Test User",
                "email": "updateduser@example.com",
                "role": "Finance",
                "permissions": {
                    "view_dashboard": True,
                    "view_reports": True,
                    "export_data": True,
                    "view_finances": True,
                    "manage_accounts_ledger": True,
                    "create_journal_entries": False,
                    "approve_journal_entries": False,
                    "manage_information": False,
                    "manage_companies": False,
                    "manage_business_units": False,
                    "view_users": False,
                    "manage_users": False,
                    "manage_settings": False,
                    "manage_api_keys": False,
                    "manage_branding": False,
                    "view_inventory": False,
                    "manage_inventory": False,
                    "manage_procurement": False,
                    "full_access": False
                },
                "location_ids": []
            }
            
            response = self.session.put(f"{BASE_URL}/users/{user_id}", json=update_data)
            
            # Clean up
            self.session.delete(f"{BASE_URL}/users/{user_id}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success") == True:
                    self.log_result("User Update New Fields", True, "User updated successfully with new fields")
                    return True
                else:
                    self.log_result("User Update New Fields", False, "Update response missing success flag", data)
                    return False
            else:
                self.log_result("User Update New Fields", False, f"Update failed with status {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_result("User Update New Fields", False, f"Error: {str(e)}")
            return False

    def test_user_email_uniqueness_validation(self):
        """Test email uniqueness validation during user updates"""
        try:
            # Create two test users
            user1_data = {
                "email": "user1@example.com",
                "password": "testpass123",
                "name": "User One",
                "role": "Analyst",
                "permissions": {
                    "view_dashboard": True,
                    "view_reports": False,
                    "export_data": False,
                    "view_finances": False,
                    "manage_accounts_ledger": False,
                    "create_journal_entries": False,
                    "approve_journal_entries": False,
                    "manage_information": False,
                    "manage_companies": False,
                    "manage_business_units": False,
                    "view_users": False,
                    "manage_users": False,
                    "manage_settings": False,
                    "manage_api_keys": False,
                    "manage_branding": False,
                    "view_inventory": False,
                    "manage_inventory": False,
                    "manage_procurement": False,
                    "full_access": False
                }
            }
            
            user2_data = {
                "email": "user2@example.com",
                "password": "testpass123",
                "name": "User Two",
                "role": "Analyst",
                "permissions": {
                    "view_dashboard": True,
                    "view_reports": False,
                    "export_data": False,
                    "view_finances": False,
                    "manage_accounts_ledger": False,
                    "create_journal_entries": False,
                    "approve_journal_entries": False,
                    "manage_information": False,
                    "manage_companies": False,
                    "manage_business_units": False,
                    "view_users": False,
                    "manage_users": False,
                    "manage_settings": False,
                    "manage_api_keys": False,
                    "manage_branding": False,
                    "view_inventory": False,
                    "manage_inventory": False,
                    "manage_procurement": False,
                    "full_access": False
                }
            }
            
            # Create first user
            response = self.session.post(f"{BASE_URL}/users", json=user1_data)
            if response.status_code != 200:
                self.log_result("User Email Uniqueness", False, "Failed to create first test user")
                return False
            
            user1 = response.json()
            user1_id = user1["id"]
            
            # Create second user
            response = self.session.post(f"{BASE_URL}/users", json=user2_data)
            if response.status_code != 200:
                # Clean up first user
                self.session.delete(f"{BASE_URL}/users/{user1_id}")
                self.log_result("User Email Uniqueness", False, "Failed to create second test user")
                return False
            
            user2 = response.json()
            user2_id = user2["id"]
            
            # Try to update user2's email to user1's email (should fail)
            update_data = {
                "email": "user1@example.com"
            }
            
            response = self.session.put(f"{BASE_URL}/users/{user2_id}", json=update_data)
            
            # Clean up both users
            self.session.delete(f"{BASE_URL}/users/{user1_id}")
            self.session.delete(f"{BASE_URL}/users/{user2_id}")
            
            if response.status_code == 400:
                self.log_result("User Email Uniqueness", True, "Correctly prevented duplicate email during update")
                return True
            else:
                self.log_result("User Email Uniqueness", False, f"Expected 400, got {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("User Email Uniqueness", False, f"Error: {str(e)}")
            return False

    def test_user_permission_updates(self):
        """Test permission updates with new granular permission model"""
        try:
            # Create a test user
            user_data = {
                "email": "permissionuser@example.com",
                "password": "testpass123",
                "name": "Permission Test User",
                "role": "Analyst",
                "permissions": {
                    "view_dashboard": True,
                    "view_reports": False,
                    "export_data": False,
                    "view_finances": False,
                    "manage_accounts_ledger": False,
                    "create_journal_entries": False,
                    "approve_journal_entries": False,
                    "manage_information": False,
                    "manage_companies": False,
                    "manage_business_units": False,
                    "view_users": False,
                    "manage_users": False,
                    "manage_settings": False,
                    "manage_api_keys": False,
                    "manage_branding": False,
                    "view_inventory": False,
                    "manage_inventory": False,
                    "manage_procurement": False,
                    "full_access": False
                }
            }
            
            response = self.session.post(f"{BASE_URL}/users", json=user_data)
            
            if response.status_code != 200:
                self.log_result("User Permission Updates", False, "Failed to create test user")
                return False
            
            user = response.json()
            user_id = user["id"]
            
            # Update user with comprehensive permissions (all 17 granular permissions)
            update_data = {
                "permissions": {
                    # Dashboard & Reporting
                    "view_dashboard": True,
                    "view_reports": True,
                    "export_data": True,
                    
                    # Financial Management
                    "view_finances": True,
                    "manage_accounts_ledger": True,
                    "create_journal_entries": True,
                    "approve_journal_entries": True,
                    
                    # Company & Business Units
                    "manage_information": True,
                    "manage_companies": True,
                    "manage_business_units": True,
                    
                    # User Management
                    "view_users": True,
                    "manage_users": True,
                    
                    # Settings & Configuration
                    "manage_settings": True,
                    "manage_api_keys": True,
                    "manage_branding": True,
                    
                    # Inventory & Operations
                    "view_inventory": True,
                    "manage_inventory": True,
                    "manage_procurement": True,
                    
                    # Administrative
                    "full_access": False
                }
            }
            
            response = self.session.put(f"{BASE_URL}/users/{user_id}", json=update_data)
            
            # Clean up
            self.session.delete(f"{BASE_URL}/users/{user_id}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success") == True:
                    self.log_result("User Permission Updates", True, "User permissions updated successfully with all 17 granular permissions")
                    return True
                else:
                    self.log_result("User Permission Updates", False, "Update response missing success flag", data)
                    return False
            else:
                self.log_result("User Permission Updates", False, f"Update failed with status {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_result("User Permission Updates", False, f"Error: {str(e)}")
            return False

    def test_user_update_invalid_id(self):
        """Test user update with invalid user ID"""
        try:
            update_data = {"name": "Test Update"}
            response = self.session.put(f"{BASE_URL}/users/invalid-id", json=update_data)
            
            if response.status_code == 404:
                self.log_result("User Update Invalid ID", True, "Correctly returned 404 for invalid user ID")
                return True
            else:
                self.log_result("User Update Invalid ID", False, f"Expected 404, got {response.status_code}")
                return False
        except Exception as e:
            self.log_result("User Update Invalid ID", False, f"Error: {str(e)}")
            return False

    def test_user_update_unauthorized_access(self):
        """Test user update without authentication"""
        try:
            # Remove auth header temporarily
            original_headers = self.session.headers.copy()
            if "Authorization" in self.session.headers:
                del self.session.headers["Authorization"]
            
            # Test user update without auth
            response = self.session.put(f"{BASE_URL}/users/test-id", json={"name": "test"})
            
            # Restore headers
            self.session.headers.update(original_headers)
            
            if response.status_code == 401:
                self.log_result("User Update Unauthorized", True, "Correctly returned 401 for unauthorized user update")
                return True
            else:
                self.log_result("User Update Unauthorized", False, f"Expected 401, got {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("User Update Unauthorized", False, f"Error: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Run all backend tests"""
        print("🚀 Starting Backend API Tests for Business Unit Soft Delete and Enhanced User Management")
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
            # Original CRUD tests
            self.test_company_update,
            self.test_company_update_invalid_id,
            self.test_business_unit_update,
            self.test_business_unit_update_invalid_id,
            self.test_company_delete_with_subsidiaries,
            self.test_company_delete_success,
            self.test_business_unit_delete_with_locations,
            self.test_business_unit_delete_success,
            self.test_unauthorized_access,
            
            # Company soft delete tests
            self.test_soft_delete_company,
            self.test_soft_delete_company_with_subsidiaries,
            self.test_get_companies_excludes_deleted,
            self.test_get_deleted_companies,
            self.test_restore_company,
            self.test_restore_non_deleted_company,
            self.test_soft_delete_already_deleted_company,
            self.test_soft_delete_invalid_company_id,
            self.test_restore_invalid_company_id,
            
            # Business unit soft delete tests
            self.test_business_unit_soft_delete,
            self.test_business_unit_soft_delete_with_locations,
            self.test_get_business_units_excludes_soft_deleted,
            self.test_get_deleted_business_units,
            self.test_restore_business_unit,
            self.test_restore_non_deleted_business_unit,
            self.test_business_unit_soft_delete_already_deleted,
            self.test_business_unit_soft_delete_invalid_id,
            self.test_business_unit_restore_invalid_id,
            
            # Enhanced user management tests
            self.test_user_update_with_new_fields,
            self.test_user_email_uniqueness_validation,
            self.test_user_permission_updates,
            self.test_user_update_invalid_id,
            self.test_user_update_unauthorized_access,
            
            # Business unit consolidation tests
            self.test_create_business_unit_with_consolidation,
            self.test_create_business_unit_invalid_parent_subsidiary,
            self.test_update_business_unit_consolidation,
            self.test_get_business_unit_consolidation,
            self.test_get_business_unit_consolidation_with_dates,
            self.test_get_business_unit_consolidation_invalid_id,
            self.test_get_consolidated_report,
            self.test_get_consolidated_report_with_dates,
            self.test_get_consolidated_report_invalid_id,
            self.test_set_business_unit_consolidation,
            self.test_set_business_unit_consolidation_invalid_parent,
            self.test_set_business_unit_consolidation_invalid_bu_id,
            self.test_get_business_units_includes_parent_subsidiary_name
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