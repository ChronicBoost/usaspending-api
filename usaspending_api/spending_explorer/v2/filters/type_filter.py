from datetime import datetime, timezone
from django.db.models import Sum
from usaspending_api.awards.models import FinancialAccountsByAwards
from usaspending_api.common.exceptions import InvalidParameterException
from usaspending_api.financial_activities.models import FinancialAccountsByProgramActivityObjectClass
from usaspending_api.references.models import GTASSF133Balances
from usaspending_api.spending_explorer.v2.filters.explorer import Explorer
from usaspending_api.spending_explorer.v2.filters.spending_filter import spending_filter
from usaspending_api.submissions.models import DABSSubmissionWindowSchedule


UNREPORTED_DATA_NAME = "Unreported Data"
VALID_UNREPORTED_DATA_TYPES = ["agency", "budget_function", "object_class"]
VALID_UNREPORTED_FILTERS = ["fy", "quarter"]


def get_unreported_data_obj(
    queryset, filters, limit, spending_type, actual_total, fiscal_year, fiscal_period
) -> (list, float):
    """ Returns the modified list of result objects including the object corresponding to the unreported amount, only
        if applicable. If the unreported amount does not fit within the limit of results provided, it will not be added.

        Args:
            queryset: Django queryset with all necessary filters, etc already applied
            filters: filters provided in POST request to endpoint
            limit: number of results to limit to
            spending_type: spending explorer category
            actual_total: total calculated based on results in `queryset`
            fiscal_year: fiscal year from request
            fiscal_period: final fiscal period for fiscal quarter requested

        Returns:
            result_set: modified (if applicable) result set as a list
            expected_total: total calculated from GTAS
    """

    queryset = queryset[:limit] if type == "award" else queryset

    result_set = []
    result_keys = ["id", "code", "type", "name", "amount"]
    if spending_type == "federal_account":
        result_keys.append("account_number")
    for entry in queryset:
        condensed_entry = {}
        for key in result_keys:
            condensed_entry[key] = entry[key] if key != "id" else str(entry[key])
        result_set.append(condensed_entry)

    gtas = (
        GTASSF133Balances.objects.filter(fiscal_year=fiscal_year, fiscal_period=fiscal_period)
        .values("fiscal_year", "fiscal_period")
        .annotate(Sum("obligations_incurred_total_cpe"))
        .values("obligations_incurred_total_cpe__sum")
    )
    expected_total = gtas[0]["obligations_incurred_total_cpe__sum"] if gtas else None

    if spending_type in VALID_UNREPORTED_DATA_TYPES and set(filters.keys()) == set(VALID_UNREPORTED_FILTERS):
        unreported_obj = {"id": None, "code": None, "type": spending_type, "name": UNREPORTED_DATA_NAME, "amount": None}

        # if both values are actually available, then calculate the amount, otherwise leave it as the default of None
        if not (actual_total is None or expected_total is None):
            unreported_obj["amount"] = expected_total - actual_total

            # Since the limit doesn't apply to anything except the awards category, always append the unreported object
            result_set.append(unreported_obj)

        result_set = sorted(result_set, key=lambda k: k["amount"], reverse=True)
    else:
        expected_total = actual_total

    return result_set, expected_total


def type_filter(_type, filters, limit=None):
    _types = [
        "budget_function",
        "budget_subfunction",
        "federal_account",
        "program_activity",
        "object_class",
        "recipient",
        "award",
        "award_category",
        "agency",
        "agency_type",
        "agency_sub",
    ]

    # Validate explorer _type
    if _type is None:
        raise InvalidParameterException('Missing Required Request Parameter, "type": "type"')

    elif _type not in _types:
        raise InvalidParameterException(
            "Type does not have a valid value. "
            "Valid Types: budget_function, budget_subfunction, federal_account, program_activity,"
            "object_class, recipient, award, award_category agency, agency_type, agency_sub"
        )

    if filters is None:
        raise InvalidParameterException('Missing Required Request Parameter, "filters": { "filter_options" }')

    if "fy" not in filters:
        raise InvalidParameterException('Missing required parameter "fy".')

    if "quarter" not in filters:
        raise InvalidParameterException('Missing required parameter "quarter".')

    try:
        fiscal_year = int(filters["fy"])
        if fiscal_year < 1000 or fiscal_year > 9999:
            raise InvalidParameterException('Incorrect Fiscal Year Parameter, "fy": "YYYY"')
    except ValueError:
        raise InvalidParameterException('Incorrect or Missing Fiscal Year Parameter, "fy": "YYYY"')

    if filters["quarter"] not in ("1", "2", "3", "4", 1, 2, 3, 4):
        raise InvalidParameterException("Incorrect value provided for quarter parameter. Must be between 1 and 4")
    fiscal_quarter = int(filters["quarter"])

    submission_window = DABSSubmissionWindowSchedule.objects.filter(
        submission_fiscal_year=fiscal_year,
        submission_fiscal_quarter=fiscal_quarter,
        is_quarter=True,
        submission_reveal_date__lte=datetime.now(timezone.utc),
    ).first()
    if submission_window is None:
        return {"total": None}

    fiscal_date = submission_window.period_end_date
    fiscal_period = submission_window.submission_fiscal_month

    # transaction_obligated_amount is summed across all periods in the year up to and including the requested quarter.
    alt_set = FinancialAccountsByAwards.objects.filter(
        submission__reporting_fiscal_year=fiscal_year, submission__reporting_fiscal_quarter__lte=fiscal_quarter,
    ).annotate(amount=Sum("transaction_obligated_amount"))

    # obligations_incurred_by_program_object_class_cpe is picked from the final period of the quarter.
    queryset = FinancialAccountsByProgramActivityObjectClass.objects.filter(
        submission__reporting_fiscal_year=fiscal_year, submission__reporting_fiscal_period=fiscal_period,
    ).annotate(amount=Sum("obligations_incurred_by_program_object_class_cpe"))

    # Apply filters to queryset results
    alt_set, queryset = spending_filter(alt_set, queryset, filters, _type)

    if _type == "recipient" or _type == "award" or _type == "award_category" or _type == "agency_type":
        # Annotate and get explorer _type filtered results
        exp = Explorer(alt_set, queryset)

        if _type == "recipient":
            alt_set = exp.recipient()
        if _type == "award":
            alt_set = exp.award()
        if _type == "award_category":
            alt_set = exp.award_category()

        # Total value of filtered results
        actual_total = 0

        for award in alt_set:
            award["id"] = str(award["id"])
            if _type in ["award", "award_category"]:
                code = None
                for code_type in ("piid", "fain", "uri"):
                    if award[code_type]:
                        code = award[code_type]
                        break
                for code_type in ("piid", "fain", "uri"):
                    del award[code_type]
                award["code"] = code
                if _type == "award":
                    award["name"] = code
            actual_total += award["total"]

        alt_set = alt_set[:limit] if _type == "award" else alt_set

        results = {"total": actual_total, "end_date": fiscal_date, "results": alt_set}

    else:
        # Annotate and get explorer _type filtered results
        exp = Explorer(alt_set, queryset)

        if _type == "budget_function":
            queryset = exp.budget_function()
        if _type == "budget_subfunction":
            queryset = exp.budget_subfunction()
        if _type == "federal_account":
            queryset = exp.federal_account()
        if _type == "program_activity":
            queryset = exp.program_activity()
        if _type == "object_class":
            queryset = exp.object_class()
        if _type == "agency":
            queryset = exp.agency()

        # Actual total value of filtered results
        actual_total = queryset.aggregate(total=Sum("amount"))["total"]

        result_set, expected_total = get_unreported_data_obj(
            queryset=queryset,
            filters=filters,
            limit=limit,
            spending_type=_type,
            actual_total=actual_total,
            fiscal_year=fiscal_year,
            fiscal_period=fiscal_period,
        )

        results = {"total": expected_total, "end_date": fiscal_date, "results": result_set}

    return results
