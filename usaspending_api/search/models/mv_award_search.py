from usaspending_api.search.models.base_award_search import BaseAwardSearchModel
from django.db import models
from usaspending_api.awards.models import FinancialAccountsByAwards
from django.contrib.contenttypes.fields import GenericForeignKey


class AwardSearchMatview(BaseAwardSearchModel):

    # award = models.OneToOneField(FinancialAccountsByAwards, on_delete=models.DO_NOTHING, to_field="award_id", related_name="account_award", primary_key=True)
    # account_award = GenericForeignKey('content_type', 'object_id')
    award = models.OneToOneField(
        FinancialAccountsByAwards,
        on_delete=models.DO_NOTHING,
        related_name="account_award",
        to_field="award_id",
        db_constraint=False
    )
    # account_award = models.ForeignKey(FinancialAccountsByAwards, on_delete=models.DO_NOTHING, related_name="account_award", to_field="award_id")

    class Meta:
        managed = False
        db_table = "mv_award_search"
