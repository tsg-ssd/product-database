"""
Test of the "browse products by vendor" view
"""
from tests.base.django_test_cases import DestructiveProductDbFunctionalTest
from selenium.webdriver.support.ui import Select
import os
import time


class BrowseProductsByVendor(DestructiveProductDbFunctionalTest):
    fixtures = ['default_vendors.yaml']

    def test_browse_product_list_view(self):
        expected_cisco_row = "C2960X-STACK Catalyst 2960-X FlexStack Plus Stacking Module 1195.00 USD"
        expected_juniper_row = "EX-SFP-1GE-LX SFP 1000Base-LX Gigabit Ethernet Optics, 1310nm for " \
                               "10km transmission on SMF 1000.00 USD"
        default_vendor = "Cisco Systems"

        # a user hits the browse product list url
        self.browser.get(self.server_url + "/productdb/vendor/")
        self.browser.implicitly_wait(3)

        # check that the user sees a table
        page_text = self.browser.find_element_by_tag_name('body').text
        self.assertIn("Vendor to display:", page_text)

        # the user sees a selection field, where the value "Cisco Systems" is selected
        pl_selection = self.browser.find_element_by_id("vendor_selection")
        self.assertIn(default_vendor, pl_selection.text)
        pl_selection = Select(pl_selection)

        # the table has three buttons: Copy, CSV and a PDF
        dt_buttons = self.browser.find_element_by_class_name("dt-buttons")

        self.assertEqual("PDF", dt_buttons.find_element_by_link_text("PDF").text)
        self.assertEqual("Copy", dt_buttons.find_element_by_link_text("Copy").text)
        self.assertEqual("CSV", dt_buttons.find_element_by_link_text("CSV").text)

        # the table shows 10 entries from the list (below the table, there is a string "Showing 1 to 10 of \d+ entries"
        dt_wrapper = self.browser.find_element_by_id("product_table_info")
        self.assertRegex(dt_wrapper.text, r".*Showing 1 to 10 of \d+ entries.*")

        # the page reloads and the table contains now the element "C2960X-STACK" as the first element of the table
        table = self.browser.find_element_by_id('product_table')
        rows = table.find_elements_by_tag_name('tr')
        self.assertIn(expected_cisco_row,
                      [row.text for row in rows])

        # the user chooses the list named "Juniper Networks" and press the button "view product list"
        pl_selection.select_by_visible_text("Juniper Networks")
        self.browser.find_element_by_id("submit").click()

        # the page reloads and the table contains now the element "EX-SFP-1GE-LX" as the first element of the table
        table = self.browser.find_element_by_id('product_table')
        rows = table.find_elements_by_tag_name('tr')

        match = False
        for i in range(0, 3):
            match = (expected_juniper_row,
                     [row.text for row in rows])
            if match:
                break
            time.sleep(3)
        if not match:
            self.fail("Element not found")

    def test_browse_product_list_view_csv_export(self):
        # a user hits the browse product list url
        self.browser.get(self.server_url + "/productdb/vendor/")
        self.browser.implicitly_wait(3)

        # the user sees a selection field, where the value "Cisco Systems" is selected
        vendor_name = "Cisco Systems"
        pl_selection = self.browser.find_element_by_id("vendor_selection")
        self.assertIn(vendor_name, pl_selection.text)

        # the user hits the button CSV
        dt_buttons = self.browser.find_element_by_class_name("dt-buttons")
        dt_buttons.find_element_by_link_text("CSV").click()

        # the file should download automatically (firefox is configured this way)

        # verify that the file is a CSV formatted field (with ";" as delimiter)
        file = os.path.join(self.download_dir, "vendor products - %s.csv" % vendor_name)
        f = open(file, "r+")
        self.assertEqual("product ID;description;list price;currency\n", f.readline())
        f.close()

    def test_search_function(self):
        # a user hits the browse product list url
        self.browser.get(self.server_url + "/productdb/vendor/")
        self.browser.implicitly_wait(3)

        # he enters a search term in the search box
        search_term = "WS-C2960X-24P"
        search_xpath = '//div[@id="product_table_wrapper"]/div[@id="product_table_filter"]/label/input[@type="search"]'
        search = self.browser.find_element_by_xpath(search_xpath)
        search.send_keys(search_term)
        time.sleep(3)

        # the table performs the search function and a defined amount of rows is displayed
        expected_table_content = """product ID description list price"""
        table_rows = [
            'WS-C2960X-24PD-L Catalyst 2960-X 24 GigE PoE 370W, 2 x 10G SFP+, LAN Base 4595.00 USD',
            'WS-C2960X-24PS-L Catalyst 2960-X 24 GigE PoE 370W, 4 x 1G SFP, LAN Base 3195.00 USD',
        ]

        table = self.browser.find_element_by_id('product_table')
        self.assertIn(expected_table_content, table.text)
        for r in table_rows:
            self.assertIn(r, table.text)
