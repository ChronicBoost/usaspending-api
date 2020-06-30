from django.utils.functional import cached_property
from rest_framework.views import APIView

from usaspending_api.awards.v2.lookups.lookups import award_type_mapping
from usaspending_api.common.data_classes import Pagination
from usaspending_api.common.validator import customize_pagination_with_sort_columns, TinyShield
from usaspending_api.references.models import DisasterEmergencyFundCode
from usaspending_api.submissions.helpers import get_last_closed_submission_date


class DisasterBase(APIView):
    required_filters = ["def_codes"]
    reporting_period_min = "2018-04-01"

    @cached_property
    def filters(self):
        all_def_codes = sorted(list(DisasterEmergencyFundCode.objects.values_list("code", flat=True)))
        object_keys_lookup = {
            "def_codes": {
                "key": "filter|def_codes",
                "name": "def_codes",
                "type": "array",
                "array_type": "enum",
                "enum_values": all_def_codes,
                "allow_nulls": False,
                "optional": False,
            },
            "query": {
                "key": "filter|query",
                "name": "query",
                "type": "text",
                "text_type": "search",
                "allow_nulls": True,
                "optional": True,
            },
            "award_type_codes": {
                "key": "filter|award_type_codes",
                "name": "award_type_codes",
                "type": "array",
                "array_type": "enum",
                "enum_values": list(award_type_mapping.keys()),
                "allow_nulls": True,
                "optional": True,
            },
        }
        model = [object_keys_lookup[key] for key in self.required_filters]
        json_request = TinyShield(model).block(self.request.data)
        return json_request["filter"]

    @property
    def def_codes(self):
        return self.filters["def_codes"]

    @cached_property
    def last_closed_monthly_submission_dates(self):
        return get_last_closed_submission_date(is_quarter=False)

    @cached_property
    def last_closed_quarterly_submission_dates(self):
        return get_last_closed_submission_date(is_quarter=True)


class SpendingMixin:
    required_filters = ["def_codes", "query"]

    @property
    def query(self):
        return self.filters.get("query")

    @cached_property
    def spending_type(self):
        model = [
            {
                "key": "spending_type",
                "name": "spending_type",
                "type": "enum",
                "enum_values": ["total", "award"],
                "allow_nulls": False,
                "optional": False,
            }
        ]

        return TinyShield(model).block(self.request.data)["spending_type"]


class LoansMixin:
    required_filters = ["def_codes", "query"]

    @property
    def query(self):
        return self.filters.get("query")


class _BasePaginationMixin:
    def pagination(self):
        """pass"""

    def run_models(self, columns):
        default_sort_column = "id"
        model = customize_pagination_with_sort_columns(columns, default_sort_column)
        request_data = TinyShield(model).block(self.request.data.get("pagination", {}))
        return Pagination(
            page=request_data["page"],
            limit=request_data["limit"],
            lower_limit=(request_data["page"] - 1) * request_data["limit"],
            upper_limit=(request_data["page"] * request_data["limit"]),
            sort_key=request_data.get("sort", "obligated_amount"),
            sort_order=request_data["order"],
        )


class PaginationMixin(_BasePaginationMixin):
    @cached_property
    def pagination(self):
        sortable_columns = ["id", "code", "description", "obligation", "outlay", "total_budgetary_resources", "count"]
        return self.run_models(sortable_columns)


class LoansPaginationMixin(_BasePaginationMixin):
    @cached_property
    def pagination(self):
        sortable_columns = ["id", "code", "description", "count", "face_value_of_loan"]
        return self.run_models(sortable_columns)
