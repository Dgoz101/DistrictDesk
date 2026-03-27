"""Phase 8: error pages (DEBUG=False), pagination constant."""

from django.test import TestCase, override_settings

from accounts.views import UserListView
from devices.views import DeviceListView
from tickets.settings_views import PriorityLevelListView, TicketCategoryListView
from tickets.views import TicketListView


class Phase8PolishTests(TestCase):
    def test_list_views_paginate_by_25(self):
        self.assertEqual(TicketListView.paginate_by, 25)
        self.assertEqual(DeviceListView.paginate_by, 25)
        self.assertEqual(UserListView.paginate_by, 25)
        self.assertEqual(TicketCategoryListView.paginate_by, 25)
        self.assertEqual(PriorityLevelListView.paginate_by, 25)

    @override_settings(DEBUG=False)
    def test_custom_404_template(self):
        response = self.client.get('/this-url-should-not-exist-phase8/')
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, 'Page not found', status_code=404)
        self.assertContains(response, 'DistrictDesk', status_code=404)
