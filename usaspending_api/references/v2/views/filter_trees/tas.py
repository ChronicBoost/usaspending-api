from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from usaspending_api.common.cache_decorator import cache_response
from usaspending_api.common.validator.tinyshield import TinyShield

from usaspending_api.accounts.models import TreasuryAppropriationAccount, FederalAccount
from usaspending_api.references.v2.views.filter_trees.filter_tree import FilterTree


class TASViewSet(APIView):
    """

    """

    endpoint_doc = ""

    @cache_response()
    def get(self, request: Request, tier1: str = None, tier2: str = None, tier3: str = None) -> Response:
        filter_tree = TASFilterTree()
        if tier3:
            return Response(f"{filter_tree.basic_search(tier1,tier2,tier3).account_title}")
        elif tier2:
            return Response(f"{[tas.tas_rendering_label for tas in filter_tree.basic_search(tier1,tier2,tier3)]}")
        elif tier1:
            return Response(f"{[fa.federal_account_code for fa in filter_tree.basic_search(tier1,tier2,tier3)]}")
        else:
            return Response(
                f"{[agency['agency_identifier'] for agency in filter_tree.basic_search(tier1,tier2,tier3)]}"
            )


class TASFilterTree(FilterTree):
    def toptier_search(self):
        return FederalAccount.objects.values("agency_identifier").distinct()

    def tier_one_search(self, agency):
        return FederalAccount.objects.filter(agency_identifier=agency)

    def tier_two_search(self, fed_account):
        return TreasuryAppropriationAccount.objects.filter(federal_account__federal_account_code=fed_account)

    def tier_three_search(self, tas_code):
        return TreasuryAppropriationAccount.objects.filter(tas_rendering_label=tas_code).first()
